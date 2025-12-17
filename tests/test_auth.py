"""
Authentication and Authorization Tests for RNG-THING
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import websockets
from httpx import AsyncClient, ASGITransport
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.core.database import db
from tests.test_all import test, random_username

# Use a test-specific database
DB_PATH = "data/test_casino.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
db.DB_FILE = DB_PATH
db._init_db()


async def get_cookies(username, password):
    """Helper to login and get cookies."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        db.create_user(username, password)
        response = await client.post(
            "/auth/login", data={"username": username, "password": password}
        )
        return {k: v for k, v in response.cookies.items()}


@test("Successful login sets signature cookie")
async def test_login_sets_signature():
    """Verify that a successful login returns a `signature` cookie."""
    cookies = await get_cookies(random_username(), "password123")
    assert "signature" in cookies, "Signature cookie not found"


from tests.test_all import TEST_HOST, TEST_PORT

async def ws_connect_with_cookies(cookies):
    """Connect to WebSocket with cookies."""
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    return await websockets.connect(
        f"ws://{TEST_HOST}:{TEST_PORT}/ws", extra_headers={"Cookie": cookie_str}
    )


@test("WebSocket connection with valid signature")
async def test_websocket_valid_signature():
    """Test that a WebSocket connection is accepted with a valid signature."""
    cookies = await get_cookies(random_username(), "password123")
    try:
        ws = await ws_connect_with_cookies(cookies)
        await ws.close()
    except websockets.exceptions.InvalidStatusCode as e:
        assert False, f"WebSocket disconnected unexpectedly: {e}"


@test("WebSocket connection with invalid signature")
async def test_websocket_invalid_signature():
    """Test that a WebSocket connection is rejected with an invalid signature."""
    cookies = await get_cookies(random_username(), "password123")
    cookies["signature"] = "invalid_signature"
    ws = await ws_connect_with_cookies(cookies)
    response = await ws.recv()
    data = json.loads(response)
    assert data["type"] == "error"
    assert data["message"] == "Authentication failed"
    await ws.close()


@test("WebSocket connection with missing signature")
async def test_websocket_missing_signature():
    """Test that a WebSocket connection is rejected if the signature is missing."""
    cookies = await get_cookies(random_username(), "password123")
    del cookies["signature"]
    ws = await ws_connect_with_cookies(cookies)
    response = await ws.recv()
    data = json.loads(response)
    assert data["type"] == "error"
    assert data["message"] == "Authentication failed"
    await ws.close()


@test("WebSocket connection with tampered user_id")
async def test_websocket_tampered_cookie():
    """Test rejection when user_id is changed but signature is not."""
    cookies = await get_cookies(random_username(), "password123")
    cookies["user_id"] = "999"  # Tamper with the user ID
    ws = await ws_connect_with_cookies(cookies)
    response = await ws.recv()
    data = json.loads(response)
    assert data["type"] == "error"
    assert data["message"] == "Authentication failed"
    await ws.close()
