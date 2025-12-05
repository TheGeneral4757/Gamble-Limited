from fastapi import APIRouter, Request, Form, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.database import db
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/auth")
async def auth_page(request: Request, error: str = None, reg_error: str = None, is_admin: bool = False):
    """Show login/register page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": error,
        "reg_error": reg_error,
        "is_admin": is_admin
    })

@router.post("/auth/login")
async def user_login(request: Request, username: str = Form(...)):
    """Login existing user."""
    user = db.login_user(username.strip())
    
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "error": f"User '{username}' not found. Create a new account?"
        })
    
    # Set session cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(user["id"]), max_age=31536000)
    response.set_cookie("username", user["username"], max_age=31536000)
    response.set_cookie("is_admin", "0", max_age=31536000)
    
    return response

@router.post("/auth/register")
async def user_register(request: Request, username: str = Form(...)):
    """Create new user account."""
    username = username.strip()
    
    # Validate username
    if len(username) < 3:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "Username must be at least 3 characters"
        })
    
    if not username.replace("_", "").isalnum():
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "Username can only contain letters, numbers, and underscores"
        })
    
    # Reserved names
    if username.lower() in ["admin", "administrator", "system", "root"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": "That username is reserved"
        })
    
    result = db.create_user(username)
    
    if not result["success"]:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "app_name": settings.server.name,
            "reg_error": result["error"]
        })
    
    # Login the new user
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("user_id", str(result["user_id"]), max_age=31536000)
    response.set_cookie("username", username, max_age=31536000)
    response.set_cookie("is_admin", "0", max_age=31536000)
    
    return response

@router.post("/auth/admin-login")
async def admin_login(request: Request, password: str = Form(...)):
    """Admin login with password."""
    if db.verify_admin_password(password):
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie("user_id", "0", max_age=31536000)
        response.set_cookie("username", "Administrator", max_age=31536000)
        response.set_cookie("is_admin", "1", max_age=31536000)
        response.set_cookie("admin_session", "authenticated", max_age=3600)  # 1 hour
        return response
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.server.name,
        "error": "Invalid admin password",
        "is_admin": True
    })

@router.get("/logout")
async def logout(request: Request):
    """Logout user."""
    response = RedirectResponse(url="/auth", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("is_admin")
    response.delete_cookie("admin_session")
    return response

def get_current_user(request: Request) -> dict:
    """Get current user from cookies."""
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    is_admin = request.cookies.get("is_admin") == "1"
    
    if not user_id:
        return None
    
    # Handle invalid/old format user IDs
    try:
        parsed_user_id = int(user_id) if user_id != "0" else 0
    except (ValueError, TypeError):
        # Invalid user_id format (likely old UUID), return None to force re-login
        return None
    
    return {
        "user_id": parsed_user_id,
        "username": username or "Guest",
        "is_admin": is_admin
    }

def require_login(request: Request):
    """Check if user is logged in, redirect if not."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    return user

def require_admin(request: Request):
    """Check if user is admin."""
    user = get_current_user(request)
    admin_session = request.cookies.get("admin_session")
    
    if not user or not user["is_admin"] or admin_session != "authenticated":
        return None
    return user
