from fastapi import HTTPException, Depends, status, Request, Response
from app.config import settings
import bcrypt
import secrets
import uuid

# Simple in-memory session store: token -> username
SESSIONS = {}

def create_session(username: str, response: Response):
    token = str(uuid.uuid4())
    SESSIONS[token] = username
    # Session cookie expires when browser closes
    response.set_cookie(key="admin_session", value=token, httponly=True, samesite="lax")
    return token

def delete_session(response: Response):
    response.delete_cookie("admin_session")

def get_current_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token not in SESSIONS:
        return None
    return SESSIONS[token]

def verify_credentials(username, password):
    # Check username
    if not secrets.compare_digest(username, settings.security.admin_username):
        return False
    
    # Check password
    try:
        if bcrypt.checkpw(password.encode('utf-8'), settings.security.admin_password_hash.encode('utf-8')):
            return True
    except Exception:
        pass
    return False

def require_admin_api(admin: str = Depends(get_current_admin)):
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return admin
