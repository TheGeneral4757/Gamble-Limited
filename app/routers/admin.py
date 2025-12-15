from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.database import db
from app.config import settings, PROJECT_ROOT
from app.core.odds import load_odds, save_odds, reload_odds
from app.core.logger import get_logger
from app.routers.auth import require_admin, admin_user
import json

logger = get_logger("admin")

router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


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


class OddsUpdateRequest(BaseModel):
    odds_data: Dict[str, Any]


class BanUserRequest(BaseModel):
    user_id: int
    hours: int = 24
    reason: str = "Banned by admin"


class SetJackpotRequest(BaseModel):
    amount: float


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
    current_odds = load_odds()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "user": user,
            "users": users,
            "stats": stats,
            "game_stats": game_stats,
            "leaderboard": leaderboard,
            "current_odds": json.dumps(current_odds, indent=2, ensure_ascii=False),
        },
    )


@router.post("/api/reset-user")
async def reset_user(data: UserActionRequest, user: dict = Depends(admin_user)):
    """Reset a user to default balance."""
    logger.info(f"Admin reset user {data.user_id}")
    result = db.reset_user(data.user_id)
    return result


@router.post("/api/delete-user")
async def delete_user(data: UserActionRequest, user: dict = Depends(admin_user)):
    """Ban a user (delete is now ban)."""
    logger.info(f"Admin banned user {data.user_id}")
    result = db.ban_user(
        data.user_id, hours=8760, reason="Account banned by admin"
    )  # 1 year
    return result


@router.post("/api/ban-user")
async def ban_user(data: BanUserRequest, user: dict = Depends(admin_user)):
    """Ban a user for specified duration."""
    logger.info(f"Admin banned user {data.user_id} for {data.hours}h: {data.reason}")
    result = db.ban_user(data.user_id, hours=data.hours, reason=data.reason)
    return result


@router.post("/api/unban-user")
async def unban_user(data: UserActionRequest, user: dict = Depends(admin_user)):
    """Unban a user."""
    logger.info(f"Admin unbanned user {data.user_id}")
    result = db.unban_user(data.user_id)
    return result


@router.post("/api/grant-funds")
async def grant_funds(data: GrantFundsRequest, user: dict = Depends(admin_user)):
    """Grant cash/credits to a user and send WebSocket notification."""
    # Determine gifter name
    gifter = (
        "THE HOUSE"
        if user.get("is_house") or user.get("user_type") == "house"
        else "Administrator"
    )

    logger.info(
        f"{gifter} granted funds to user {data.user_id}: cash={data.cash}, credits={data.credits}"
    )
    new_balance = db.update_balance(
        data.user_id, cash_delta=data.cash, credits_delta=data.credits
    )

    # Send WebSocket notification
    try:
        from app.core.websocket import ws_manager
        import asyncio

        gift_msg = []
        if data.cash > 0:
            gift_msg.append(f"${data.cash:.2f} cash")
        if data.credits > 0:
            gift_msg.append(f"{data.credits:.2f} credits")

        asyncio.create_task(
            ws_manager.send_personal(
                data.user_id,
                {
                    "type": "gift_notification",
                    "gifter": gifter,
                    "message": f"You received {' and '.join(gift_msg)} from {gifter}!",
                    "cash": data.cash,
                    "credits": data.credits,
                },
            )
        )
    except Exception as e:
        logger.warning(f"Failed to send gift notification: {e}")

    return {"success": True, "balance": new_balance, "gifter": gifter}


@router.post("/api/set-balance")
async def set_balance(data: SetBalanceRequest, user: dict = Depends(admin_user)):
    """Set exact balance for a user."""
    logger.info(
        f"Admin set balance for user {data.user_id}: cash={data.cash}, credits={data.credits}"
    )
    new_balance = db.set_balance(data.user_id, cash=data.cash, credits=data.credits)
    return {"success": True, "balance": new_balance}


@router.post("/api/clear-all")
async def clear_all_data(user: dict = Depends(admin_user)):
    """Clear all user data."""
    logger.warning("Admin cleared all data")
    result = db.clear_all_data()
    return result


@router.post("/api/lottery/set-jackpot")
async def set_jackpot(data: SetJackpotRequest, user: dict = Depends(admin_user)):
    """Set the lottery jackpot amount manually."""
    logger.info(f"Admin set lottery jackpot to {data.amount}")
    result = db.update_lottery_jackpot(amount=data.amount)
    return {"success": True, "jackpot": result}


@router.post("/api/change-password")
async def change_password(
    data: PasswordChangeRequest, user: dict = Depends(admin_user)
):
    """Change admin password."""
    if len(data.new_password) < 4:
        return {"success": False, "error": "Password too short"}

    db.set_admin_password(data.new_password)
    logger.info("Admin password changed")
    return {
        "success": True,
        "message": "Password updated. Server restart may be required.",
    }


@router.get("/api/users")
async def get_users(user: dict = Depends(admin_user)):
    """Get all users list."""
    users = db.get_all_users()
    return {"users": users}


@router.get("/api/user/{user_id}")
async def get_user_details(user_id: int, user: dict = Depends(admin_user)):
    """Get detailed user info."""
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        return {"success": False, "error": "User not found"}

    transactions = db.get_transactions(user_id, limit=20)
    game_stats = db.get_user_game_stats(user_id)

    return {
        "success": True,
        "user": user_data,
        "transactions": transactions,
        "game_stats": game_stats,
    }


@router.get("/api/stats")
async def get_stats(user: dict = Depends(admin_user)):
    """Get platform statistics."""
    stats = db.get_stats()
    return stats


@router.get("/api/leaderboard")
async def get_leaderboard(user: dict = Depends(admin_user)):
    """Get top players."""
    leaderboard = db.get_leaderboard()
    return {"leaderboard": leaderboard}


@router.get("/api/game-stats")
async def get_game_stats(user: dict = Depends(admin_user)):
    """Get per-game statistics."""
    stats = db.get_game_breakdown()
    return {"game_stats": stats}


# ==================== Odds Management ====================


@router.get("/api/odds")
async def get_odds(user: dict = Depends(admin_user)):
    """Get current game odds configuration."""
    odds = load_odds()
    return {"success": True, "odds": odds}


@router.post("/api/odds")
async def update_odds(data: OddsUpdateRequest, user: dict = Depends(admin_user)):
    """Update game odds (writes to ODDS-CHANGER.json)."""
    success = save_odds(data.odds_data)
    if success:
        logger.info("Admin updated game odds")
        return {"success": True, "message": "Odds updated and active immediately"}
    else:
        return {"success": False, "error": "Failed to save odds"}


@router.post("/api/odds/reload")
async def reload_odds_endpoint(user: dict = Depends(admin_user)):
    """Force reload odds from file."""
    odds = reload_odds()
    logger.info("Admin reloaded game odds")
    return {"success": True, "odds": odds}


# ==================== Logs ====================


@router.get("/api/logs")
async def get_logs(
    lines: int = 100, level: str = "all", user: dict = Depends(admin_user)
):
    """Get recent application logs."""
    log_file = PROJECT_ROOT / "data" / "app.log"
    logs = []

    try:
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()

                # Filter by level if specified
                if level != "all":
                    level_upper = level.upper()
                    all_lines = [l for l in all_lines if level_upper in l]

                # Get last N lines
                logs = all_lines[-lines:]
                logs = [l.strip() for l in logs]
        else:
            logs = [
                "Log file not found. Enable file logging in config: logging.log_to_file = true"
            ]

    except Exception as e:
        logs = [f"Error reading logs: {e}"]

    return {"success": True, "logs": logs, "count": len(logs)}
