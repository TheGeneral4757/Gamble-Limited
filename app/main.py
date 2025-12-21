"""
RNG-THING Main Application Entry Point
FastAPI-based gambling web application with WebSocket support.
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work when running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import orjson as json
import time
from collections import deque

from app.core.logger import init_logging, get_logger
from app.config import settings, PROJECT_ROOT
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import pages, api, admin
from app.routers.auth import router as auth_router, get_current_user
from app.core.websocket import ws_manager, normalize_ws_close_code
from app.core.scheduler import lottery_scheduler

# Initialize logging first
init_logging(
    level=settings.logging.level,
    log_to_file=settings.logging.log_to_file,
    formatter=settings.logging.formatter,
)
logger = get_logger("main")
ws_logger = get_logger("websocket")


# WebSocket Rate Limiting
WS_MAX_MESSAGES = 10  # Max messages per user
WS_RATE_LIMIT_SECONDS = 2  # In this time window
ws_rate_limiter = {}  # In-memory store: user_id -> deque of timestamps


# ==================== Security Headers Middleware ====================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy - allow WebSocket connections
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


# ==================== UVLoop Integration =====================

try:
    import uvloop

    uvloop.install()
    logger.info("uvloop installed and enabled.")
except ImportError:
    logger.info("uvloop not found, using default asyncio event loop.")

# ==================== Application Setup ====================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.server.name,
        docs_url="/docs" if settings.server.debug else None,
        redoc_url=None,
    )

    # Add slowapi rate limiter
    from app.routers.api import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS middleware (for development)
    if settings.server.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Static files
    static_path = PROJECT_ROOT / "app" / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    else:
        logger.warning(f"Static directory not found: {static_path}")

    # Include routers
    app.include_router(auth_router)
    app.include_router(pages.router)
    app.include_router(api.router, prefix="/api")
    app.include_router(admin.router, prefix="/admin")

    return app


app = create_app()


@app.on_event("shutdown")
def shutdown_event():
    lottery_scheduler.shutdown()


logger.info(f"Application '{settings.server.name}' initialized")
logger.info(f"Debug mode: {settings.server.debug}")
logger.info(f"Admin login path: {settings.security.admin_login_path}")


# ==================== WebSocket Endpoint ====================




@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    Supports:
    - Balance updates
    - Big win announcements
    - Global chat
    """
    # Get user info from secure cookie
    user = get_current_user(websocket)
    user_id = user["user_id"] if user else None
    username = user["username"] if user else "Guest"
    client_ip = websocket.client.host

    if user:
        user_id = user["user_id"]
        username = user["username"]
    else:
        # Deny connection if user is not authenticated
        ws_logger.warning(
            "WebSocket connection denied due to invalid auth",
            extra={"client_ip": client_ip},
        )
        await websocket.accept()
        await websocket.send_bytes(json.dumps({"type": "error", "message": "Authentication failed"}))
        await websocket.close()
        return

    await ws_manager.connect(websocket, user_id)
    ws_logger.info(
        "WebSocket connected", extra={"user_id": user_id, "client_ip": client_ip}
    )

    # Initialize rate limiter for the user
    if user_id not in ws_rate_limiter:
        ws_rate_limiter[user_id] = deque()

    try:
        while True:
            # Receive message
            data = await websocket.receive_bytes()

            # --- Game Warden: WebSocket Rate Limiting ---
            current_time = time.time()
            # FAIL-CLOSED: Use direct access. If user_id is missing, it's a server
            # error. The exception handler will catch the KeyError and disconnect.
            user_timestamps = ws_rate_limiter[user_id]

            # Remove old timestamps
            while (
                user_timestamps
                and user_timestamps[0] < current_time - WS_RATE_LIMIT_SECONDS
            ):
                user_timestamps.popleft()

            # Check if limit is exceeded
            if len(user_timestamps) >= WS_MAX_MESSAGES:
                ws_logger.warning(
                    "WebSocket rate limit exceeded",
                    extra={"user_id": user_id, "client_ip": client_ip},
                )
                # Silently drop the message by skipping the processing loop
                continue

            # Add current message timestamp
            user_timestamps.append(current_time)
            # --- End WebSocket Rate Limiting ---

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "chat" and username:
                    # Handle chat message
                    content = message.get("message", "").strip()
                    if content and len(content) <= 200:
                        await ws_manager.add_chat_message(username, content)

                elif msg_type == "ping":
                    # Keep-alive ping
                    await websocket.send_bytes(json.dumps({"type": "pong"}))

                elif msg_type == "subscribe":
                    topic = message.get("topic")
                    if topic:
                        await ws_manager.subscribe(websocket, topic)

                elif msg_type == "unsubscribe":
                    topic = message.get("topic")
                    if topic:
                        await ws_manager.unsubscribe(websocket, topic)

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect as e:
        ws_manager.disconnect(websocket, user_id)
        if user_id in ws_rate_limiter:
            del ws_rate_limiter[user_id]  # Clean up rate-limiter memory
        ws_logger.info(
            "WebSocket disconnected",
            extra={
                "user_id": user_id,
                "client_ip": client_ip,
                "ws_disconnect_code": e.code,
                "ws_disconnect_reason": normalize_ws_close_code(e.code),
            },
        )
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, user_id)
        if user_id in ws_rate_limiter:
            del ws_rate_limiter[user_id]  # Clean up rate-limiter memory
        ws_logger.error(
            "WebSocket error",
            extra={"user_id": user_id, "client_ip": client_ip, "error": str(e)},
        )


# ==================== Global Exception Handler ====================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if request.url.path.startswith("/api"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.server.debug else None,
            },
        )
    else:
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Error</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Something went wrong</h1>
                    <p>An unexpected error occurred. Please try again later.</p>
                    {"<pre>" + str(exc) + "</pre>" if settings.server.debug else ""}
                </body>
            </html>
            """,
            status_code=500,
        )


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RNG-THING Casino Server")
    parser.add_argument(
        "--test-friday",
        action="store_true",
        help="Enable Gamble Friday test mode (bypass day/time check)",
    )
    args = parser.parse_args()

    # Enable test Friday mode if flag is set
    if args.test_friday:
        from app.core.gamble_friday import set_test_friday_mode

        set_test_friday_mode(True)
        logger.info("*** GAMBLE FRIDAY TEST MODE ENABLED ***")

    logger.info(f"Starting server on {settings.server.host}:{settings.server.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.debug,
    )
