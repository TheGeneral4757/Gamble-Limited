from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from app.core.database import db
from app.config import settings
from app.routers.auth import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Request models
class UserActionRequest(BaseModel):
    user_id: int

class PasswordChangeRequest(BaseModel):
    new_password: str

class GrantFundsRequest(BaseModel):
    user_id: int
    cash: Optional[float] = 0
    credits: Optional[float] = 0

class SetBalanceRequest(BaseModel):
    user_id: int
    cash: float
    credits: float

@router.get("")
async def admin_panel(request: Request):
    """Admin dashboard."""
    user = require_admin(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    
    users = db.get_all_users()
    stats = db.get_stats()
    game_stats = db.get_game_breakdown()
    leaderboard = db.get_leaderboard()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "app_name": settings.server.name,
        "user": user,
        "users": users,
        "stats": stats,
        "game_stats": game_stats,
        "leaderboard": leaderboard
    })

@router.post("/api/reset-user")
async def reset_user(request: Request, data: UserActionRequest):
    """Reset a user to default balance."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    result = db.reset_user(data.user_id)
    return result

@router.post("/api/delete-user")
async def delete_user(request: Request, data: UserActionRequest):
    """Delete a user completely."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    result = db.delete_user(data.user_id)
    return result

@router.post("/api/grant-funds")
async def grant_funds(request: Request, data: GrantFundsRequest):
    """Grant cash/credits to a user."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    new_balance = db.update_balance(data.user_id, cash_delta=data.cash, credits_delta=data.credits)
    return {"success": True, "balance": new_balance}

@router.post("/api/set-balance")
async def set_balance(request: Request, data: SetBalanceRequest):
    """Set exact balance for a user."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    new_balance = db.set_balance(data.user_id, cash=data.cash, credits=data.credits)
    return {"success": True, "balance": new_balance}

@router.post("/api/clear-all")
async def clear_all_data(request: Request):
    """Clear all user data."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    result = db.clear_all_data()
    return result

@router.post("/api/change-password")
async def change_password(request: Request, data: PasswordChangeRequest):
    """Change admin password."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    if len(data.new_password) < 4:
        return {"success": False, "error": "Password too short"}
    
    db.set_admin_password(data.new_password)
    return {"success": True, "message": "Password updated. Server restart may be required."}

@router.get("/api/users")
async def get_users(request: Request):
    """Get all users list."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    users = db.get_all_users()
    return {"users": users}

@router.get("/api/user/{user_id}")
async def get_user_details(request: Request, user_id: int):
    """Get detailed user info."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        return {"success": False, "error": "User not found"}
    
    transactions = db.get_transactions(user_id, limit=20)
    game_stats = db.get_user_game_stats(user_id)
    
    return {
        "success": True,
        "user": user_data,
        "transactions": transactions,
        "game_stats": game_stats
    }

@router.get("/api/stats")
async def get_stats(request: Request):
    """Get platform statistics."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    stats = db.get_stats()
    return stats

@router.get("/api/leaderboard")
async def get_leaderboard(request: Request):
    """Get top players."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    leaderboard = db.get_leaderboard()
    return {"leaderboard": leaderboard}

@router.get("/api/game-stats")
async def get_game_stats(request: Request):
    """Get per-game statistics."""
    user = require_admin(request)
    if not user:
        return {"success": False, "error": "Unauthorized"}
    
    stats = db.get_game_breakdown()
    return {"game_stats": stats}
