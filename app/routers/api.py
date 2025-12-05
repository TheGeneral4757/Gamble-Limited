from fastapi import APIRouter, HTTPException, Request, Cookie
from app.core.economy import economy
from app.core.rng import rng
from app.core.database import db
from app.core.games import slots_game, blackjack_game, roulette_game, plinko_game, coinflip_game
from app.config import settings
from pydantic import BaseModel, Field
from typing import Optional
import uuid

router = APIRouter()

# ==================== Request/Response Models ====================

class BetRequest(BaseModel):
    bet: float = Field(..., gt=0, description="Bet amount")

class CoinflipRequest(BaseModel):
    bet: float = Field(..., gt=0)
    choice: str = Field(..., pattern="^(heads|tails)$")

class RouletteRequest(BaseModel):
    bet: float = Field(..., gt=0)
    bet_type: str
    bet_value: str = ""

class PlinkoRequest(BaseModel):
    bet: float = Field(..., gt=0)
    rows: int = Field(default=16, ge=8, le=16)

class BlackjackActionRequest(BaseModel):
    game_id: str

class ExchangeRequest(BaseModel):
    from_currency: str = Field(..., pattern="^(cash|credits)$")
    amount: float = Field(..., gt=0)

class ExchangeRateResponse(BaseModel):
    rate: float

# ==================== Helper Functions ====================

def get_user_id(request: Request) -> str:
    """Get or create user ID from cookie/session."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())[:12]
    return user_id

def validate_bet(user_id: str, bet: float, game: str) -> dict:
    """Validate bet amount against game limits and user balance."""
    game_config = getattr(settings.games, game, None)
    
    if not game_config or not game_config.enabled:
        return {"valid": False, "error": f"Game '{game}' is not available"}
    
    if bet < game_config.min_bet:
        return {"valid": False, "error": f"Minimum bet is {game_config.min_bet}"}
    
    if bet > game_config.max_bet:
        return {"valid": False, "error": f"Maximum bet is {game_config.max_bet}"}
    
    # Check balance
    balance = economy.get_balance(user_id)
    if balance["credits"] < bet:
        return {"valid": False, "error": "Insufficient credits", "balance": balance}
    
    return {"valid": True}

# ==================== Economy Endpoints ====================

@router.get("/economy/rate", response_model=ExchangeRateResponse)
async def get_exchange_rate():
    return {"rate": economy.get_current_exchange_rate()}

@router.get("/economy/balance")
async def get_balance(request: Request):
    user_id = get_user_id(request)
    balance = economy.get_balance(user_id)
    return {"user_id": user_id, **balance}

@router.post("/economy/exchange")
async def exchange_currency(request: Request, data: ExchangeRequest):
    user_id = get_user_id(request)
    result = economy.do_exchange(user_id, data.from_currency, data.amount)
    return result

@router.get("/economy/transactions")
async def get_transactions(request: Request, limit: int = 20):
    user_id = get_user_id(request)
    transactions = db.get_transactions(user_id, limit)
    return {"transactions": transactions}

# ==================== RNG Test Endpoint ====================

@router.get("/rng/test")
async def test_rng():
    return {
        "float": rng.random_float(),
        "int_1_100": rng.random_int(1, 100)
    }

# ==================== Slots ====================

@router.post("/games/slots/spin")
async def slots_spin(request: Request, data: BetRequest):
    user_id = get_user_id(request)
    
    # Validate bet
    validation = validate_bet(user_id, data.bet, "slots")
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet
    bet_result = economy.place_bet(user_id, data.bet)
    if not bet_result["success"]:
        raise HTTPException(status_code=400, detail=bet_result["error"])
    
    # Play game
    result = slots_game.spin(data.bet)
    
    # Add winnings
    if result["payout"] > 0:
        economy.add_winnings(user_id, result["payout"], game="slots")
    
    # Get updated balance
    result["balance"] = economy.get_balance(user_id)
    result["user_id"] = user_id
    
    return result

# ==================== Blackjack ====================

@router.post("/games/blackjack/deal")
async def blackjack_deal(request: Request, data: BetRequest):
    user_id = get_user_id(request)
    
    # Validate bet
    validation = validate_bet(user_id, data.bet, "blackjack")
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet
    bet_result = economy.place_bet(user_id, data.bet)
    if not bet_result["success"]:
        raise HTTPException(status_code=400, detail=bet_result["error"])
    
    # Deal cards
    result = blackjack_game.deal(data.bet)
    
    # If immediate blackjack, add winnings
    if result.get("status") == "complete" and result.get("payout", 0) > 0:
        economy.add_winnings(user_id, result["payout"], game="blackjack")
    
    result["balance"] = economy.get_balance(user_id)
    result["user_id"] = user_id
    
    return result

@router.post("/games/blackjack/hit")
async def blackjack_hit(request: Request, data: BlackjackActionRequest):
    user_id = get_user_id(request)
    
    result = blackjack_game.hit(data.game_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # If bust or complete, no winnings to add
    if result.get("status") == "complete" and result.get("payout", 0) > 0:
        economy.add_winnings(user_id, result["payout"], game="blackjack")
    
    result["balance"] = economy.get_balance(user_id)
    
    return result

@router.post("/games/blackjack/stand")
async def blackjack_stand(request: Request, data: BlackjackActionRequest):
    user_id = get_user_id(request)
    
    result = blackjack_game.stand(data.game_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add winnings if won
    if result.get("payout", 0) > 0:
        economy.add_winnings(user_id, result["payout"], game="blackjack")
    
    result["balance"] = economy.get_balance(user_id)
    
    return result

# ==================== Roulette ====================

@router.post("/games/roulette/spin")
async def roulette_spin(request: Request, data: RouletteRequest):
    user_id = get_user_id(request)
    
    # Validate bet
    validation = validate_bet(user_id, data.bet, "roulette")
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet
    bet_result = economy.place_bet(user_id, data.bet)
    if not bet_result["success"]:
        raise HTTPException(status_code=400, detail=bet_result["error"])
    
    # Play game
    result = roulette_game.spin(data.bet, data.bet_type, data.bet_value)
    
    if "error" in result:
        # Refund bet on invalid bet type
        economy.add_winnings(user_id, data.bet, game="roulette")
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add winnings
    if result["payout"] > 0:
        economy.add_winnings(user_id, result["payout"], game="roulette")
    
    result["balance"] = economy.get_balance(user_id)
    result["user_id"] = user_id
    
    return result

# ==================== Plinko ====================

@router.post("/games/plinko/drop")
async def plinko_drop(request: Request, data: PlinkoRequest):
    user_id = get_user_id(request)
    
    # Validate bet
    validation = validate_bet(user_id, data.bet, "plinko")
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet
    bet_result = economy.place_bet(user_id, data.bet)
    if not bet_result["success"]:
        raise HTTPException(status_code=400, detail=bet_result["error"])
    
    # Play game
    result = plinko_game.drop(data.bet, data.rows)
    
    # Add winnings (plinko always pays something)
    if result["payout"] > 0:
        economy.add_winnings(user_id, result["payout"], game="plinko")
    
    result["balance"] = economy.get_balance(user_id)
    result["user_id"] = user_id
    
    return result

# ==================== Coinflip ====================

@router.post("/games/coinflip/flip")
async def coinflip_flip(request: Request, data: CoinflipRequest):
    user_id = get_user_id(request)
    
    # Validate bet
    validation = validate_bet(user_id, data.bet, "coinflip")
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet
    bet_result = economy.place_bet(user_id, data.bet)
    if not bet_result["success"]:
        raise HTTPException(status_code=400, detail=bet_result["error"])
    
    # Play game
    result = coinflip_game.flip(data.bet, data.choice)
    
    if "error" in result:
        # Refund bet
        economy.add_winnings(user_id, data.bet, game="coinflip")
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add winnings
    if result["payout"] > 0:
        economy.add_winnings(user_id, result["payout"], game="coinflip")
    
    result["balance"] = economy.get_balance(user_id)
    result["user_id"] = user_id
    
    return result
