from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_admin_api
from app.core.database import db
from app.core.economy import economy
from app.config import settings
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()

# ==================== Request Models ====================

class GrantFundsRequest(BaseModel):
    user_id: str
    cash: float = 0
    credits: float = 0

class ResetUserRequest(BaseModel):
    user_id: str

# ==================== Admin Endpoints ====================

@router.get("/status")
async def admin_status(username: str = Depends(require_admin_api)):
    """Get admin panel status and basic stats."""
    stats = db.get_stats()
    return {
        "status": "active",
        "admin": username,
        "app_name": settings.server.name,
        "stats": stats
    }

@router.get("/users")
async def list_users(username: str = Depends(require_admin_api)):
    """List all users and their balances."""
    users = db.get_all_users()
    return {"users": users, "count": len(users)}

@router.get("/users/{user_id}")
async def get_user_details(user_id: str, username: str = Depends(require_admin_api)):
    """Get detailed info for a specific user."""
    balance = db.get_balance(user_id)
    transactions = db.get_transactions(user_id, limit=50)
    return {
        "user_id": user_id,
        "balance": balance,
        "transactions": transactions
    }

@router.post("/users/grant")
async def grant_funds(data: GrantFundsRequest, username: str = Depends(require_admin_api)):
    """Grant funds to a user."""
    new_balance = economy.grant_funds(data.user_id, data.cash, data.credits)
    return {
        "success": True,
        "user_id": data.user_id,
        "granted": {"cash": data.cash, "credits": data.credits},
        "new_balance": new_balance
    }

@router.post("/users/reset")
async def reset_user(data: ResetUserRequest, username: str = Depends(require_admin_api)):
    """Reset a user's balance to starting values."""
    new_balance = economy.reset_user(data.user_id)
    return {
        "success": True,
        "user_id": data.user_id,
        "new_balance": new_balance
    }

@router.post("/economy/clear")
async def clear_all_data(username: str = Depends(require_admin_api)):
    """Clear ALL user data from the database. Use with caution!"""
    result = db.clear_all_data()
    return {
        "success": True,
        "action": "database_cleared",
        "admin": username,
        **result
    }

@router.get("/stats")
async def get_stats(username: str = Depends(require_admin_api)):
    """Get detailed statistics."""
    stats = db.get_stats()
    exchange_rate = economy.get_current_exchange_rate()
    
    return {
        "stats": stats,
        "exchange_rate": exchange_rate,
        "game_config": settings.games.model_dump()
    }

@router.get("/transactions")
async def list_all_transactions(
    limit: int = 100,
    username: str = Depends(require_admin_api)
):
    """List recent transactions across all users."""
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.*, u.cash, u.credits 
        FROM transactions t
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC 
        LIMIT ?
    """, (limit,))
    
    transactions = [dict(row) for row in cursor.fetchall()]
    return {"transactions": transactions, "count": len(transactions)}
