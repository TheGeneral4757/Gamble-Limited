from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.routers.auth import get_current_user, require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

VALID_GAMES = {"slots", "blackjack", "roulette", "plinko", "coinflip"}

@router.get("/")
async def home(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    
    games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": settings.server.name,
        "games": games_data,
        "user": user
    })

@router.get("/game/{game_name}")
async def game_page(request: Request, game_name: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    
    games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
    game_config = games_data.get(game_name)
    
    if not game_config or not game_config.get("enabled", False):
        return RedirectResponse(url="/")
    
    template_name = f"{game_name}.html" if game_name in VALID_GAMES else "game.html"
    
    return templates.TemplateResponse(template_name, {
        "request": request,
        "game_name": game_name,
        "app_name": settings.server.name,
        "min_bet": game_config.get("min_bet", 1),
        "max_bet": game_config.get("max_bet", 1000),
        "user": user
    })

@router.get("/exchange")
async def exchange_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    
    return templates.TemplateResponse("exchange.html", {
        "request": request,
        "app_name": settings.server.name,
        "user": user
    })
