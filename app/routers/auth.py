from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from app.core.database import db
from app.config import settings, PROJECT_ROOT
from app.core.logger import get_logger

logger = get_logger("auth")

router = APIRouter()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))

@router.get("/auth")
async def auth_page(request: Request, error: str = None, reg_error: str = None, is_admin: bool = False):
    """Show login/register page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": error,
        "reg_error": reg_error,
        "is_admin": is_admin,
        "is_house": False
    })

@router.post("/auth/login")
async def user_login(request: Request, username: str = Form(...), password: Optional[str] = Form(None)):
    """Login existing user with optional password."""
    user = db.login_user(username.strip(), password)
    
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "error": "Invalid username or password"
        })
    
    # Check if user is banned
    if isinstance(user, dict) and user.get("banned"):
        from datetime import datetime
        try:
            ban_time = datetime.fromisoformat(user["banned_until"])
            ban_str = ban_time.strftime("%Y-%m-%d %H:%M")
        except:
            ban_str = user["banned_until"]
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "error": f"You are banned until {ban_str}. Reason: {user.get('ban_reason', 'No reason specified')}"
        })
    
    logger.info(f"User logged in: {username}")
    
    # Set session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(user["id"]), max_age=31536000)
    response.set_cookie("username", user["username"], max_age=31536000)
    response.set_cookie("is_admin", "0", max_age=31536000)
    response.set_cookie("user_type", user.get("user_type", "user"), max_age=31536000)
    
    return response

@router.post("/auth/register")
async def user_register(
    request: Request, 
    username: str = Form(...), 
    password: Optional[str] = Form(None),
    password_confirm: Optional[str] = Form(None)
):
    """Create new user account with optional password."""
    username = username.strip()
    
    # Validate username length
    if len(username) < 3 or len(username) > 20:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "Username must be 3-20 characters"
        })
    
    # Validate username format
    if not username.replace("_", "").isalnum():
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "Username can only contain letters, numbers, and underscores"
        })
    
    # Reserved names
    if username.lower() in ["admin", "administrator", "system", "root", "moderator", "mod", "the_house", "thehouse", "house"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "That username is reserved"
        })
    
    # Validate password if provided
    if password:
        if len(password) < 6:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": "Password must be at least 6 characters"
            })
        
        if password != password_confirm:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "app_name": settings.server.name,
                "reg_error": "Passwords do not match"
            })
    
    result = db.create_user(username, password)
    
    if not result["success"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": result["error"]
        })
    
    logger.info(f"New user registered: {username}")
    
    # Login the new user
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(result["user_id"]), max_age=31536000)
    response.set_cookie("username", username, max_age=31536000)
    response.set_cookie("is_admin", "0", max_age=31536000)
    response.set_cookie("user_type", "user", max_age=31536000)
    
    return response

# Hidden admin login route - configurable in config.json
@router.get(settings.security.admin_login_path)
async def hidden_admin_page(request: Request, error: str = None):
    """Hidden admin login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": error,
        "is_admin": True,
        "is_house": False
    })

# Hidden HOUSE login route - configurable in config.json
@router.get(settings.security.house_login_path)
async def hidden_house_page(request: Request, error: str = None):
    """Hidden THE HOUSE login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": error,
        "is_admin": False,
        "is_house": True
    })

@router.post("/auth/admin-login")
async def admin_login(request: Request, password: str = Form(...)):
    """Admin login with password."""
    if db.verify_admin_password(password):
        logger.info("Admin logged in")
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie("user_id", "0", max_age=31536000)
        response.set_cookie("username", "Administrator", max_age=31536000)
        response.set_cookie("is_admin", "1", max_age=31536000)
        response.set_cookie("user_type", "admin", max_age=31536000)
        response.set_cookie("admin_session", "authenticated", max_age=3600)  # 1 hour
        return response
    
    logger.warning("Failed admin login attempt")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": "Invalid admin password",
        "is_admin": True
    })

@router.post("/auth/house-login")
async def house_login(request: Request, password: str = Form(...)):
    """THE HOUSE login with admin password."""
    if db.verify_admin_password(password):
        house_user = db.get_house_user()
        if not house_user:
            # Trigger migration to create house user
            db._migrate_schema()
            house_user = db.get_house_user()
        
        logger.info("THE HOUSE logged in")
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie("user_id", str(house_user["id"]) if house_user else "0", max_age=31536000)
        response.set_cookie("username", "THE HOUSE", max_age=31536000)
        response.set_cookie("is_admin", "1", max_age=31536000)
        response.set_cookie("user_type", "house", max_age=31536000)
        response.set_cookie("admin_session", "authenticated", max_age=3600)
        return response
    
    logger.warning("Failed HOUSE login attempt")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": "Invalid password",
        "is_house": True
    })

@router.get("/logout")
async def logout(request: Request):
    """Logout user."""
    response = RedirectResponse(url="/auth", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("is_admin")
    response.delete_cookie("admin_session")
    response.delete_cookie("user_type")
    return response

def get_current_user(request: Request) -> dict:
    """Get current user from cookies."""
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    is_admin = request.cookies.get("is_admin") == "1"
    user_type = request.cookies.get("user_type", "user")
    
    if not user_id:
        return None
    
    # Handle invalid/old format user IDs
    try:
        parsed_user_id = int(user_id) if user_id != "0" else 0
    except (ValueError, TypeError):
        return None
    
    return {
        "user_id": parsed_user_id,
        "username": username or "Guest",
        "is_admin": is_admin,
        "user_type": user_type,
        "is_house": user_type == "house"
    }

def require_login(request: Request):
    """Check if user is logged in, redirect if not."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    return user

def require_admin(request: Request):
    """Check if user is admin or house."""
    user = get_current_user(request)
    admin_session = request.cookies.get("admin_session")
    
    if not user or not user["is_admin"] or admin_session != "authenticated":
        return None
    return user

