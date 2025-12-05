from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.core.security import get_current_admin, verify_credentials, create_session, delete_session
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Valid games for routing to specific templates
VALID_GAMES = {"slots", "blackjack", "roulette", "plinko", "coinflip"}

def get_or_set_user_id(request: Request, response: Response = None) -> str:
    """Get user ID from cookie or create a new one."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())[:12]
        if response:
            response.set_cookie("user_id", user_id, max_age=31536000)  # 1 year
    return user_id

@router.get("/")
async def home(request: Request):
    # Convert Pydantic model to dict for Jinja2 iteration
    games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
    
    response = templates.TemplateResponse("index.html", {
        "request": request,
        "app_name": settings.server.name,
        "games": games_data
    })
    
    # Ensure user has an ID
    if not request.cookies.get("user_id"):
        user_id = str(uuid.uuid4())[:12]
        response.set_cookie("user_id", user_id, max_age=31536000)
    
    return response

@router.get("/game/{game_name}")
async def game_page(request: Request, game_name: str):
    # Get game config
    games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
    game_config = games_data.get(game_name)
    
    # Check if game exists and is enabled
    if not game_config or not game_config.get("enabled", False):
        return RedirectResponse(url="/")
    
    # Use game-specific template if available
    template_name = f"{game_name}.html" if game_name in VALID_GAMES else "game.html"
    
    response = templates.TemplateResponse(template_name, {
        "request": request,
        "game_name": game_name,
        "app_name": settings.server.name,
        "min_bet": game_config.get("min_bet", 1),
        "max_bet": game_config.get("max_bet", 1000),
    })
    
    # Ensure user has an ID
    if not request.cookies.get("user_id"):
        user_id = str(uuid.uuid4())[:12]
        response.set_cookie("user_id", user_id, max_age=31536000)
    
    return response

@router.get("/exchange")
async def exchange_page(request: Request):
    """Currency conversion hub page."""
    response = templates.TemplateResponse("exchange.html", {
        "request": request,
        "app_name": settings.server.name,
    })
    
    # Ensure user has an ID
    if not request.cookies.get("user_id"):
        user_id = str(uuid.uuid4())[:12]
        response.set_cookie("user_id", user_id, max_age=31536000)
    
    return response

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "app_name": settings.server.name})

@router.post("/login")
async def login_submit(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    if verify_credentials(username, password):
        # Create session and set cookie
        redirect = RedirectResponse(url="/admin", status_code=303)
        create_session(username, redirect)
        return redirect
    else:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "app_name": settings.server.name,
            "error": "Invalid username or password"
        })

@router.get("/logout")
async def logout(response: Response):
    redirect = RedirectResponse(url="/", status_code=303)
    delete_session(redirect)
    return redirect

@router.get("/admin")
async def admin_page(request: Request):
    user = get_current_admin(request)
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "app_name": settings.server.name,
        "username": user
    })
