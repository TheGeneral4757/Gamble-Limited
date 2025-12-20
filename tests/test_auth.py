"""
Authentication and Authorization Tests for RNG-THING
"""

import sys
import os
import asyncio
import json
import websockets
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import db
from tests.test_all import test, random_username, TEST_HOST, TEST_PORT

# Use a test-specific database
DB_PATH = "data/test_casino.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
db.DB_FILE = DB_PATH
db._init_db()


async def get_cookies(username, password):
    """Helper to login and get cookies."""
    transport = ASGITransport(app=app)
    # Loadout: Disable follow_redirects to capture the cookie from the initial 303 response
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        await db.create_user(username, password)
        response = await client.post(
            "/auth/login", data={"username": username, "password": password}
        )
        return {k: v for k, v in response.cookies.items()}


@test("Successful login sets session cookie")
async def test_login_sets_signature():
    """Verify that a successful login returns a `session` cookie."""
    cookies = await get_cookies(random_username(), "password123")
    assert "session" in cookies, "Session cookie not found"


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
        # Successful connection means the test passes, just close it.
        await ws.close()
    except Exception as e:
        assert False, f"WebSocket disconnected unexpectedly: {e}"


@test("WebSocket connection with invalid signature")
async def test_websocket_invalid_signature():
    """Test that a WebSocket connection is rejected with an invalid signature."""
    cookies = await get_cookies(random_username(), "password123")
    cookies["session"] = "invalid_signature"  # Tamper with the session cookie
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
    del cookies["session"]
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


@test("WebSocket rate limiter drops excess messages")
async def test_websocket_rate_limiter():
    """Verify that the WebSocket server drops messages that exceed the rate limit."""
    cookies = await get_cookies(random_username(), "password123")
    ws = await ws_connect_with_cookies(cookies)

    # The rate limit is 10 messages in 2 seconds.
    # We will send 15 messages in rapid succession.
    # The first 10 should be processed, the next 5 should be dropped.

    try:
        # Subscribe to a topic to get feedback
        await ws.send(json.dumps({"type": "subscribe", "topic": "chat"}))

        # Send a burst of messages
        for i in range(15):
            await ws.send(json.dumps({"type": "chat", "message": f"message {i}"}))

        # Wait a moment for messages to be processed
        await asyncio.sleep(0.1)

        # Check received messages
        received_count = 0
        try:
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                data = json.loads(response)
                if data.get("type") == "chat":
                    received_count += 1
        except asyncio.TimeoutError:
            # No more messages
            pass

        # The number of received messages should be exactly the limit
        # as the server should broadcast back the messages that were not dropped
        from app.main import WS_MAX_MESSAGES

        assert (
            received_count == WS_MAX_MESSAGES
        ), f"Expected {WS_MAX_MESSAGES} messages, but received {received_count}"

    finally:
        await ws.close()
