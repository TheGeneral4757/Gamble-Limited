from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.economy import economy
from app.core.database import db
from app.core.games.slots import slots_game
from app.core.games.blackjack import blackjack_game
from app.core.games.roulette import roulette_game
from app.core.games.plinko import plinko_game
from app.core.games.coinflip import coinflip_game
from app.config import settings

router = APIRouter()

# ==================== Request Models ====================

class BetRequest(BaseModel):
    bet: float

class BlackjackActionRequest(BaseModel):
    game_id: Optional[str] = None
    bet: Optional[float] = None

class RouletteRequest(BaseModel):
    bet: float
    bet_type: str
    bet_value: Optional[str] = ""

class PlinkoRequest(BaseModel):
    bet: float
    rows: Optional[int] = 16

class CoinflipRequest(BaseModel):
    bet: float
    choice: str

class ExchangeRequest(BaseModel):
    from_currency: str
    amount: float

# ==================== Helpers ====================

def get_user_id(request: Request) -> int:
    """Get user ID from cookie."""
    user_id = request.cookies.get("user_id")
    is_admin = request.cookies.get("is_admin") == "1"
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    return int(user_id) if user_id != "0" else 0, is_admin

def validate_bet(user_id: int, bet: float, game: str, is_admin: bool = False):
    """Validate bet amount and funds."""
    # Admin has infinite funds
    if is_admin:
        return {"valid": True}
    
    games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
    game_config = games_data.get(game, {})
    
    min_bet = game_config.get("min_bet", 1)
    max_bet = game_config.get("max_bet", 1000)
    
    if bet < min_bet or bet > max_bet:
        return {"valid": False, "error": f"Bet must be between {min_bet} and {max_bet}"}
    
    balance = economy.get_balance(user_id)
    if balance["credits"] < bet:
        return {"valid": False, "error": "Insufficient credits"}
    
    return {"valid": True}

# ==================== Economy Endpoints ====================

@router.get("/economy/rate")
async def get_exchange_rate(request: Request):
    user_id, _ = get_user_id(request)
    rate = economy.get_current_exchange_rate(user_id if user_id > 0 else None)
    return {"rate": rate}

@router.get("/economy/balance")
async def get_balance(request: Request):
    user_id, is_admin = get_user_id(request)
    
    if is_admin:
        return {"user_id": 0, "cash": 999999, "credits": 999999, "is_admin": True}
    
    balance = economy.get_balance(user_id)
    return {"user_id": user_id, **balance}

@router.post("/economy/exchange")
async def exchange_currency(request: Request, data: ExchangeRequest):
    user_id, is_admin = get_user_id(request)
    
    if is_admin:
        return {"success": True, "received": data.amount * 10, "rate": 10, 
                "balance": {"cash": 999999, "credits": 999999}}
    
    result = economy.do_exchange(user_id, data.from_currency, data.amount)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@router.get("/economy/transactions")
async def get_transactions(request: Request):
    user_id, is_admin = get_user_id(request)
    
    if is_admin:
        return {"transactions": []}
    
    transactions = db.get_transactions(user_id)
    return {"transactions": transactions}

# ==================== Game Endpoints ====================

@router.post("/games/slots/spin")
async def slots_spin(request: Request, data: BetRequest):
    user_id, is_admin = get_user_id(request)
    
    validation = validate_bet(user_id, data.bet, "slots", is_admin)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet (skip for admin)
    if not is_admin:
        economy.place_bet(user_id, data.bet, "slots")
    
    result = slots_game.spin(data.bet)
    
    # Add winnings
    if result["payout"] > 0 and not is_admin:
        economy.add_winnings(user_id, result["payout"], "slots", data.bet)
    elif not is_admin:
        db.record_game(user_id, "slots", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    
    return {**result, "balance": balance}

@router.post("/games/blackjack/deal")
async def blackjack_deal(request: Request, data: BlackjackActionRequest):
    user_id, is_admin = get_user_id(request)
    
    if not data.bet:
        raise HTTPException(status_code=400, detail="Bet amount required")
    
    validation = validate_bet(user_id, data.bet, "blackjack", is_admin)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_admin:
        economy.place_bet(user_id, data.bet, "blackjack")
    
    result = blackjack_game.deal(data.bet, user_id)
    
    if result.get("status") == "complete":
        if result["payout"] > 0 and not is_admin:
            economy.add_winnings(user_id, result["payout"], "blackjack", data.bet)
        elif not is_admin:
            db.record_game(user_id, "blackjack", data.bet, result["payout"])
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/blackjack/hit")
async def blackjack_hit(request: Request, data: BlackjackActionRequest):
    user_id, is_admin = get_user_id(request)
    
    if not data.game_id:
        raise HTTPException(status_code=400, detail="Game ID required")
    
    result = blackjack_game.hit(data.game_id, user_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid game"))
    
    if result.get("status") == "complete" and not is_admin:
        if result["payout"] > 0:
            economy.add_winnings(user_id, result["payout"], "blackjack", result.get("bet", 0))
        else:
            db.record_game(user_id, "blackjack", result.get("bet", 0), 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/blackjack/stand")
async def blackjack_stand(request: Request, data: BlackjackActionRequest):
    user_id, is_admin = get_user_id(request)
    
    if not data.game_id:
        raise HTTPException(status_code=400, detail="Game ID required")
    
    result = blackjack_game.stand(data.game_id, user_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid game"))
    
    if not is_admin:
        if result["payout"] > 0:
            economy.add_winnings(user_id, result["payout"], "blackjack", result.get("bet", 0))
        else:
            db.record_game(user_id, "blackjack", result.get("bet", 0), 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/roulette/spin")
async def roulette_spin(request: Request, data: RouletteRequest):
    user_id, is_admin = get_user_id(request)
    
    validation = validate_bet(user_id, data.bet, "roulette", is_admin)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_admin:
        economy.place_bet(user_id, data.bet, "roulette")
    
    result = roulette_game.spin(data.bet, data.bet_type, data.bet_value)
    
    if result["payout"] > 0 and not is_admin:
        economy.add_winnings(user_id, result["payout"], "roulette", data.bet)
    elif not is_admin:
        db.record_game(user_id, "roulette", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/plinko/drop")
async def plinko_drop(request: Request, data: PlinkoRequest):
    user_id, is_admin = get_user_id(request)
    
    validation = validate_bet(user_id, data.bet, "plinko", is_admin)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_admin:
        economy.place_bet(user_id, data.bet, "plinko")
    
    result = plinko_game.drop(data.bet, data.rows)
    
    if result["payout"] > 0 and not is_admin:
        economy.add_winnings(user_id, result["payout"], "plinko", data.bet)
    elif not is_admin:
        db.record_game(user_id, "plinko", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/coinflip/flip")
async def coinflip_flip(request: Request, data: CoinflipRequest):
    user_id, is_admin = get_user_id(request)
    
    validation = validate_bet(user_id, data.bet, "coinflip", is_admin)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_admin:
        economy.place_bet(user_id, data.bet, "coinflip")
    
    result = coinflip_game.flip(data.bet, data.choice)
    
    if result["payout"] > 0 and not is_admin:
        economy.add_winnings(user_id, result["payout"], "coinflip", data.bet)
    elif not is_admin:
        db.record_game(user_id, "coinflip", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}
