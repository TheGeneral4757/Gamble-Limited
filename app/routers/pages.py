from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import settings, PROJECT_ROOT
from app.routers.auth import get_current_user
from app.core.gamble_friday import gamble_friday

router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))

VALID_GAMES = {
    "slots",
    "blackjack",
    "roulette",
    "coinflip",
    "scratch_cards",
    "highlow",
    "dice",
    "number_guess",
    "lottery",
}


def get_base_context(request: Request, user=None) -> dict:
    """Get base context with Friday status for all templates."""
    is_friday = gamble_friday.is_active()
    config = gamble_friday.get_config()
    return {
        "request": request,
        "app_name": settings.server.name,
        "user": user,
        "gamble_friday_active": is_friday,
        "gamble_friday_multiplier": config["winnings_multiplier"] if is_friday else 1.0,
    }


@router.get("/")
async def home(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    games_data = (
        settings.games.model_dump()
        if hasattr(settings.games, "model_dump")
        else settings.games.dict()
    )

    ctx = get_base_context(request, user)
    # Add lottery info to context
    lottery_conf = (
        settings.lottery.model_dump()
        if hasattr(settings.lottery, "model_dump")
        else settings.lottery.dict()
    )

    # Get current jackpot and next draw from DB/System
    # We need to import db and scheduler or access via some helper
    from app.core.database import db
    from app.core.games.lottery import lottery_system

    jackpot_info = db.get_lottery_jackpot()
    # next draw is managed by scheduler but we can estimate or fetch from system
    # For now, let's just get it from the system helper if possible or DB

    ctx.update(
        {
            "games": games_data,
            "daily_bonus_credits": settings.economy.daily_bonus_amount,
            "daily_bonus_cash": settings.economy.daily_cash_amount,
            "lottery_enabled": lottery_conf.get("enabled", True),
            "lottery_jackpot": f"{jackpot_info['current_amount']:,.2f}",
            "next_draw": lottery_system.get_next_draw_time_str(),
        }
    )

    user_stats = db.get_user_by_id(user["user_id"])
    if not user_stats:
        return RedirectResponse(url="/logout", status_code=303)

    ctx["user_stats"] = user_stats
    return templates.TemplateResponse("index.html", ctx)


@router.get("/game/{game_name}")
async def game_page(request: Request, game_name: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    games_data = (
        settings.games.model_dump()
        if hasattr(settings.games, "model_dump")
        else settings.games.dict()
    )
    game_config = games_data.get(game_name)

    # Special handling for lottery
    if game_name == "lottery":
        lottery_conf = (
            settings.lottery.model_dump()
            if hasattr(settings.lottery, "model_dump")
            else settings.lottery.dict()
        )
        if lottery_conf.get("enabled", True):
            game_config = {"enabled": True, "min_bet": 0, "max_bet": 0}

    if not game_config or not game_config.get("enabled", False):
        return RedirectResponse(url="/")

    template_name = f"{game_name}.html" if game_name in VALID_GAMES else "game.html"

    # Adjust max bet for Gamble Friday
    max_bet = game_config.get("max_bet", 1000)
    if gamble_friday.is_active():
        max_bet = gamble_friday.get_adjusted_max_bet(max_bet)

    ctx = get_base_context(request, user)
    ctx.update(
        {
            "game_name": game_name,
            "min_bet": game_config.get("min_bet", 1),
            "max_bet": max_bet,
        }
    )
    return templates.TemplateResponse(template_name, ctx)


@router.get("/exchange")
async def exchange_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    return templates.TemplateResponse("exchange.html", get_base_context(request, user))


@router.get("/history")
async def history_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    return templates.TemplateResponse("history.html", get_base_context(request, user))


@router.get("/leaderboard")
async def leaderboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    return templates.TemplateResponse(
        "leaderboard.html", get_base_context(request, user)
    )


@router.get("/tos")
async def tos_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("tos.html", get_base_context(request, user))


@router.get("/privacy")
async def privacy_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("privacy.html", get_base_context(request, user))
