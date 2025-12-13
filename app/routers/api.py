from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.economy import economy
from app.core.database import db
from app.core.games.slots import slots_game
from app.core.games.blackjack import blackjack_game
from app.core.games.roulette import roulette_game
from app.core.games.plinko import plinko_game
from app.core.games.coinflip import coinflip_game
from app.core.games.scratch_cards import scratch_cards_game
from app.core.games.highlow import highlow_game
from app.core.games.dice import dice_game
from app.core.games.number_guess import number_guess_game
from app.core.games.lottery import lottery_system
from app.config import settings
from app.core.logger import get_logger

# Rate limiting setup
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
    limiter = None

logger = get_logger("api")

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

class HighLowGuessRequest(BaseModel):
    game_id: str
    choice: str

class HighLowCashoutRequest(BaseModel):
    game_id: str

class DiceRequest(BaseModel):
    bet: float
    bet_type: str
    bet_value: Optional[str] = ""

class NumberGuessRequest(BaseModel):
    bet: float
    guess: int

class LotteryBuyRequest(BaseModel):
    numbers: List[int]

class CoinFlipResponseRequest(BaseModel):
    request_id: int
    agreed: bool


# ==================== Helpers ====================

def get_user_id(request: Request) -> tuple:
    """Get user ID, is_admin flag, and user_type from cookie."""
    user_id = request.cookies.get("user_id")
    is_admin = request.cookies.get("is_admin") == "1"
    user_type = request.cookies.get("user_type", "user")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    return int(user_id) if user_id != "0" else 0, is_admin, user_type

def validate_bet(user_id: int, bet: float, game: str, is_admin: bool = False, user_type: str = "user"):
    """Validate bet amount and funds."""
    # Only true admin (not house) has infinite funds
    if is_admin and user_type != "house":
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

def get_rate_limit():
    """Get rate limit string from config."""
    return settings.rate_limit.game_requests if settings.rate_limit.enabled else "1000/minute"

# ==================== Economy Endpoints ====================

@router.get("/economy/rate")
async def get_exchange_rate(request: Request):
    user_id, _, _ = get_user_id(request)
    rate = economy.get_current_exchange_rate()
    return {"rate": rate}

@router.get("/economy/balance")
async def get_balance(request: Request):
    user_id, is_admin, user_type = get_user_id(request)
    
    # Only true admin gets infinite - THE HOUSE has real balance
    if is_admin and user_type != "house":
        return {"user_id": 0, "cash": 999999, "credits": 999999, "is_admin": True}
    
    balance = economy.get_balance(user_id)
    return {"user_id": user_id, **balance, "user_type": user_type}

@router.post("/economy/exchange")
async def exchange_currency(request: Request, data: ExchangeRequest):
    user_id, is_admin, user_type = get_user_id(request)
    
    # Only true admin gets infinite
    if is_admin and user_type != "house":
        return {"success": True, "received": data.amount * 10, "rate": 10, 
                "balance": {"cash": 999999, "credits": 999999}}
    
    result = economy.do_exchange(user_id, data.from_currency, data.amount)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@router.get("/economy/transactions")
async def get_transactions(request: Request):
    user_id, is_admin, user_type = get_user_id(request)
    
    if is_admin and user_type != "house":
        return {"transactions": []}
    
    transactions = db.get_transactions(user_id)
    return {"transactions": transactions}

@router.post("/economy/daily")
async def claim_daily_bonus(request: Request):
    """Claim daily bonus credits."""
    user_id, is_admin, user_type = get_user_id(request)
    
    if is_admin and user_type != "house":
        return {"success": True, "amount": 0, "message": "Admin doesn't need daily bonus"}
    
    result = db.claim_daily_bonus(user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    logger.info(f"User {user_id} claimed daily bonus")
    return result

@router.post("/economy/daily-cash")
async def claim_daily_cash(request: Request):
    """Claim daily cash bonus (separate from credits)."""
    user_id, is_admin, user_type = get_user_id(request)
    
    if is_admin and user_type != "house":
        return {"success": True, "amount": 0, "message": "Admin doesn't need daily cash"}
    
    result = db.claim_daily_cash(user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    logger.info(f"User {user_id} claimed daily cash")
    return result

# ==================== Leaderboard ====================

@router.get("/leaderboard")
async def get_leaderboard():
    """Get public leaderboard data."""
    leaderboard = db.get_leaderboard(limit=10)
    return {"leaderboard": leaderboard}


# ==================== Game Endpoints ====================


@router.post("/games/slots/spin")
async def slots_spin(request: Request, data: BetRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "slots", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Deduct bet (skip only for true admin, not house)
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "slots")
        # House takes a cut of every bet
        db.add_house_cut(data.bet, "slots")
    
    result = slots_game.spin(data.bet)
    
    # Add winnings
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "slots", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "slots", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    
    return {**result, "balance": balance}

@router.post("/games/blackjack/deal")
async def blackjack_deal(request: Request, data: BlackjackActionRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    if not data.bet:
        raise HTTPException(status_code=400, detail="Bet amount required")
    
    validation = validate_bet(user_id, data.bet, "blackjack", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "blackjack")
        db.add_house_cut(data.bet, "blackjack")
    
    result = blackjack_game.deal(data.bet, user_id)
    
    if result.get("status") == "complete":
        if result["payout"] > 0 and not is_true_admin:
            economy.add_winnings(user_id, result["payout"], "blackjack", data.bet)
        elif not is_true_admin:
            db.record_game(user_id, "blackjack", data.bet, result["payout"])
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/blackjack/hit")
async def blackjack_hit(request: Request, data: BlackjackActionRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    if not data.game_id:
        raise HTTPException(status_code=400, detail="Game ID required")
    
    result = blackjack_game.hit(data.game_id, user_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid game"))
    
    if result.get("status") == "complete" and not is_true_admin:
        if result["payout"] > 0:
            economy.add_winnings(user_id, result["payout"], "blackjack", result.get("bet", 0))
        else:
            db.record_game(user_id, "blackjack", result.get("bet", 0), 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/blackjack/stand")
async def blackjack_stand(request: Request, data: BlackjackActionRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    if not data.game_id:
        raise HTTPException(status_code=400, detail="Game ID required")
    
    result = blackjack_game.stand(data.game_id, user_id)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid game"))
    
    if not is_true_admin:
        if result["payout"] > 0:
            economy.add_winnings(user_id, result["payout"], "blackjack", result.get("bet", 0))
        else:
            db.record_game(user_id, "blackjack", result.get("bet", 0), 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/roulette/spin")
async def roulette_spin(request: Request, data: RouletteRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "roulette", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "roulette")
        db.add_house_cut(data.bet, "roulette")
    
    result = roulette_game.spin(data.bet, data.bet_type, data.bet_value)
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "roulette", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "roulette", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/plinko/drop")
async def plinko_drop(request: Request, data: PlinkoRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "plinko", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "plinko")
        db.add_house_cut(data.bet, "plinko")
    
    result = plinko_game.drop(data.bet, data.rows)
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "plinko", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "plinko", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/coinflip/flip")
async def coinflip_flip(request: Request, data: CoinflipRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "coinflip", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "coinflip")
        db.add_house_cut(data.bet, "coinflip")
    
    result = coinflip_game.flip(data.bet, data.choice)
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "coinflip", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "coinflip", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

# ==================== New Game Endpoints ====================

@router.post("/games/scratch-cards/buy")
async def scratch_cards_buy(request: Request, data: BetRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "scratch_cards", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "scratch_cards")
        db.add_house_cut(data.bet, "scratch_cards")
    
    result = scratch_cards_game.buy(data.bet)
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "scratch_cards", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "scratch_cards", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/highlow/start")
async def highlow_start(request: Request, data: BetRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "highlow", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "highlow")
        db.add_house_cut(data.bet, "highlow")
    
    result = highlow_game.start(data.bet, user_id)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/highlow/guess")
async def highlow_guess(request: Request, data: HighLowGuessRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    result = highlow_game.guess(data.game_id, user_id, data.choice)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/highlow/cashout")
async def highlow_cashout(request: Request, data: HighLowCashoutRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    result = highlow_game.cashout(data.game_id, user_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Add winnings on successful cashout
    if result.get("payout", 0) > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "highlow", result.get("bet", 0))
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/dice/roll")
async def dice_roll(request: Request, data: DiceRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "dice", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "dice")
        db.add_house_cut(data.bet, "dice")
    
    result = dice_game.roll(data.bet, data.bet_type, data.bet_value)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "dice", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "dice", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}

@router.post("/games/number-guess/guess")
async def number_guess(request: Request, data: NumberGuessRequest):
    user_id, is_admin, user_type = get_user_id(request)
    is_true_admin = is_admin and user_type != "house"
    
    validation = validate_bet(user_id, data.bet, "number_guess", is_admin, user_type)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    if not is_true_admin:
        economy.place_bet(user_id, data.bet, "number_guess")
        db.add_house_cut(data.bet, "number_guess")
    
    result = number_guess_game.guess(data.bet, data.guess)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    if result["payout"] > 0 and not is_true_admin:
        economy.add_winnings(user_id, result["payout"], "number_guess", data.bet)
    elif not is_true_admin:
        db.record_game(user_id, "number_guess", data.bet, 0)
    
    balance = {"cash": 999999, "credits": 999999} if is_true_admin else economy.get_balance(user_id)
    return {**result, "balance": balance}


# ==================== Lottery Endpoints ====================

@router.get("/games/lottery/info")
async def lottery_info():
    jackpot = db.get_lottery_jackpot()["current_amount"]
    no_winner_months = db.get_lottery_jackpot()["no_winner_months"]
    return lottery_system.get_lottery_info(jackpot, no_winner_months)

@router.get("/games/lottery/tickets")
async def lottery_tickets(request: Request):
    user_id, _, _ = get_user_id(request)
    if not user_id:
        return []
    draw_id = lottery_system.get_current_draw_id()
    return db.get_user_lottery_tickets(user_id, draw_id)

@router.get("/games/lottery/history")
async def lottery_history():
    return db.get_lottery_history()

@router.post("/games/lottery/buy")
async def lottery_buy(request: Request, data: LotteryBuyRequest):
    user_id, _, user_type = get_user_id(request)
    
    # Check if lottery enabled
    settings_dict = lottery_system._get_config()
    if not settings_dict.get("enabled", True):
        raise HTTPException(400, "Lottery is currently disabled")

    # Validate numbers
    validation = lottery_system.validate_numbers(data.numbers)
    if not validation["valid"]:
        raise HTTPException(400, validation["error"])

    # Check ticket limit
    draw_id = lottery_system.get_current_draw_id()
    count = db.get_user_ticket_count(user_id, draw_id)
    limit = lottery_system.get_max_tickets()
    if count >= limit:
         raise HTTPException(400, f"You have reached the limit of {limit} tickets for this draw")

    # Pay for ticket (CASH, not credits)
    price = lottery_system.get_ticket_price()
    balance = economy.get_balance(user_id)
    if balance["cash"] < price:
        raise HTTPException(400, "Insufficient cash balance")
    
    # Deduct cash
    db.update_balance(user_id, cash_delta=-price)
    db.log_transaction(user_id, "lottery_buy", -price, balance["cash"] - price, 
                       game="lottery", currency="cash")
    
    # Add to jackpot (Contribution logic)
    contribution = price * 0.40
    db.update_lottery_jackpot(delta=contribution)
    
    # Issue ticket
    ticket = db.buy_lottery_ticket(user_id, data.numbers, draw_id)
    
    return ticket

@router.get("/games/lottery/coinflip/status")
async def lottery_coinflip_status(request: Request):
    user_id, _, _ = get_user_id(request)
    status = db.get_coin_flip_status(user_id)
    return status or {"status": "none"}

@router.post("/games/lottery/coinflip/respond")
async def lottery_coinflip_respond(request: Request, data: CoinFlipResponseRequest):
    user_id, _, _ = get_user_id(request)
    result = db.respond_to_coin_flip(data.request_id, user_id, data.agreed)
    return result

@router.post("/games/lottery/draw-admin")
async def lottery_draw_admin(request: Request):
    user_id, is_admin, user_type = get_user_id(request)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Force draw
    try:
        from app.core.games.lottery import lottery_system
        result = lottery_system.perform_draw()
        # Clean non-serializable objects effectively
        safe_result = {
            "winners": len(result.get("winners", [])),
            "numbers": result.get("numbers", []),
            "jackpot": result.get("jackpot", 0)
        }
        return {"success": True, "message": f"Draw triggered. Winners: {safe_result['winners']}", "result": safe_result}
    except Exception as e:
        logger.error(f"Manual draw failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


