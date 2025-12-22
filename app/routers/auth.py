import json
import hmac
import hashlib
import asyncio
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from itsdangerous import TimestampSigner, SignatureExpired, BadTimeSignature
from datetime import timedelta
from app.core.database import db
from app.config import settings, PROJECT_ROOT
from app.core.logger import get_logger
from app.routers.api import limiter

logger = get_logger("auth")

# Create a signer for secure cookies
signer = TimestampSigner(settings.security.secret_key)

router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


def create_signature(user_id: str, username: str, user_type: str) -> str:
    """Create a secure signature for user cookie data."""
    message = f"{user_id}|{username}|{user_type}"
    return hmac.new(
        settings.security.secret_key.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


@router.get("/auth")
async def auth_page(
    request: Request, error: str = None, reg_error: str = None, is_admin: bool = False
):
    """Show login/register page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "error": error,
            "reg_error": reg_error,
            "is_admin": is_admin,
            "is_house": False,
        },
    )


@router.post("/auth/login")
@limiter.limit("10/minute")
async def user_login(
    request: Request, username: str = Form(...), password: Optional[str] = Form(None)
):
    """Login existing user with optional password."""
    user = await db.login_user(username.strip(), password)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "error": "Invalid username or password",
            },
        )

    # Check if user is banned
    if isinstance(user, dict) and user.get("banned"):
        from datetime import datetime

        try:
            ban_time = datetime.fromisoformat(user["banned_until"])
            ban_str = ban_time.strftime("%Y-%m-%d %H:%M")
        except Exception:
            ban_str = user["banned_until"]

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "error": f"You are banned until {ban_str}. Reason: {user.get('ban_reason', 'No reason specified')}",
            },
        )

    logger.info(f"User logged in: {username}")

    # Create session data
    session_data = {
        "user_id": user["id"],
        "username": user["username"],
        "is_admin": False,
        "user_type": user.get("user_type", "user"),
    }

    # Create a secure, signed cookie
    response = RedirectResponse(url="/", status_code=303)
    session_cookie = signer.sign(json.dumps(session_data).encode("utf-8"))
    response.set_cookie(
        "session",
        session_cookie.decode("utf-8"),
        max_age=int(timedelta(days=30).total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not settings.server.debug,  # Use Secure cookies in production
    )
    return response


@router.post("/auth/register")
@limiter.limit("10/minute")
async def user_register(
    request: Request,
    username: str = Form(...),
    password: Optional[str] = Form(None),
    password_confirm: Optional[str] = Form(None),
):
    """Create new user account with optional password."""
    username = username.strip()

    # Validate username length
    if len(username) < 3 or len(username) > 20:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": "Username must be 3-20 characters",
            },
        )

    # Validate username format
    if not username.replace("_", "").isalnum():
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": "Username can only contain letters, numbers, and underscores",
            },
        )

    # Reserved names
    if username.lower() in [
        "admin",
        "administrator",
        "system",
        "root",
        "moderator",
        "mod",
        "the_house",
        "thehouse",
        "house",
    ]:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": "That username is reserved",
            },
        )

    # Validate password if provided
    if password:
        if len(password) < 6:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "app_name": settings.server.name,
                    "reg_error": "Password must be at least 6 characters",
                },
            )

        if password != password_confirm:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "app_name": settings.server.name,
                    "reg_error": "Passwords do not match",
                },
            )

    result = await db.create_user(username, password)

    if not result["success"]:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": result["error"],
            },
        )

    logger.info(f"New user registered: {username}")

    # Create session data
    session_data = {
        "user_id": result["user_id"],
        "username": username,
        "is_admin": False,
        "user_type": "user",
    }

    # Login the new user
    response = RedirectResponse(url="/", status_code=303)
    session_cookie = signer.sign(json.dumps(session_data).encode("utf-8"))
    response.set_cookie(
        "session",
        session_cookie.decode("utf-8"),
        max_age=int(timedelta(days=30).total_seconds()),
        httponly=True,
        samesite="Lax",
        secure=not settings.server.debug,
    )

    return response


# Hidden admin login route - configurable in config.json
@router.get(settings.security.admin_login_path)
async def hidden_admin_page(request: Request, error: str = None):
    """Hidden admin login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "error": error,
            "is_admin": True,
            "is_house": False,
        },
    )


# Hidden HOUSE login route - configurable in config.json
@router.get(settings.security.house_login_path)
async def hidden_house_page(request: Request, error: str = None):
    """Hidden THE HOUSE login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "error": error,
            "is_admin": False,
            "is_house": True,
        },
    )


@router.post("/auth/admin-login")
@limiter.limit("10/minute")
async def admin_login(request: Request, password: str = Form(...)):
    """Admin login with password."""
    if await db.verify_admin_password(password):
        logger.info("Admin logged in")

        # Create session data for admin
        session_data = {
            "user_id": 0,
            "username": "Administrator",
            "is_admin": True,
            "user_type": "admin",
        }

        response = RedirectResponse(url="/admin", status_code=303)
        session_cookie = signer.sign(json.dumps(session_data).encode("utf-8"))
        response.set_cookie(
            "session",
            session_cookie.decode("utf-8"),
            max_age=int(
                timedelta(hours=1).total_seconds()
            ),  # Shorter session for admin
            httponly=True,
            samesite="Strict",  # More restrictive for admin
            secure=not settings.server.debug,
        )
        return response

    logger.warning("Failed admin login attempt")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "error": "Invalid admin password",
            "is_admin": True,
        },
    )


@router.post("/auth/house-login")
async def house_login(request: Request, password: str = Form(...)):
    """THE HOUSE login with admin password."""
    if await db.verify_admin_password(password):
        house_user = db.get_house_user()
        if not house_user:
            # Trigger migration to create house user
            db._migrate_schema()
            house_user = db.get_house_user()

        logger.info("THE HOUSE logged in")

        session_data = {
            "user_id": house_user["id"] if house_user else 0,
            "username": "THE HOUSE",
            "is_admin": True,
            "user_type": "house",
        }

        response = RedirectResponse(url="/admin", status_code=303)
        session_cookie = signer.sign(json.dumps(session_data).encode("utf-8"))
        response.set_cookie(
            "session",
            session_cookie.decode("utf-8"),
            max_age=int(timedelta(hours=1).total_seconds()),
            httponly=True,
            samesite="Strict",
            secure=not settings.server.debug,
        )
        return response

    logger.warning("Failed HOUSE login attempt")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.server.name,
            "error": "Invalid password",
            "is_house": True,
        },
    )


@router.get("/logout")
async def logout(request: Request):
    """Logout user."""
    response = RedirectResponse(url="/auth", status_code=303)
    response.delete_cookie("session")
    return response


async def get_current_user(request: Request) -> dict:
    """Get current user from a secure, signed cookie."""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None

    try:
        # Verify the cookie signature and timestamp (max_age = 30 days)
        max_age_seconds = int(timedelta(days=30).total_seconds())

        # Loadout: Move CPU-bound crypto to a thread to avoid blocking event loop
        data = await asyncio.to_thread(
            signer.unsign, session_cookie.encode("utf-8"), max_age_seconds
        )
        session_data = json.loads(data.decode("utf-8"))

        # Add 'is_house' for convenience
        session_data["is_house"] = session_data.get("user_type") == "house"

        return session_data

    except (SignatureExpired, BadTimeSignature, json.JSONDecodeError):
        # Invalid or expired cookie
        return None


async def require_login(request: Request):
    """Check if user is logged in, redirect if not."""
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    return user


async def require_admin(request: Request):
    """Check if user is admin or house."""
    user = await get_current_user(request)

    if not user or not user["is_admin"]:
        return None
    return user


async def admin_user(user: dict = Depends(require_admin)):
    """Dependency to require admin user."""
    if not user:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user
