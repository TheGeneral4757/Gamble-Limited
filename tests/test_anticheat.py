import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app, WS_MAX_MESSAGES

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

async def test_websocket_rate_limit_exploit(client):
    """
    Test that the WebSocket endpoint is not vulnerable to a rate-limit bypass attack.
    This test will attempt to flood the WebSocket with messages of various types
    and assert that the server correctly drops messages exceeding the defined rate limit.
    """
    # Create a test user and log in to get a valid session cookie
    client.post("/register", data={"username": "rate_limit_tester", "password": "password"})
    response = client.post("/login", data={"username": "rate_limit_tester", "password": "password"})
    cookies = response.cookies

    cookies = {"session_id": response.cookies.get("session_id")}
    with client.websocket_connect("/ws", cookies=cookies) as websocket:
        # Send a flood of messages, including types that were previously ignored by the rate limiter
        for i in range(20):
            websocket.send_json({"type": "ping"})
            websocket.send_json({"type": "subscribe", "topic": "test"})
            websocket.send_json({"type": "chat", "message": f"test message {i}"})

        # Give the server a moment to process the messages
        await asyncio.sleep(0.1)

        # The server should only process the first 10 messages and then drop the rest
        # We will check that we don't receive more than 10 'pong' responses
        pong_count = 0
        while True:
            try:
                response = websocket.receive_json()
                if response.get("type") == "pong":
                    pong_count += 1
            except Exception:
                break

    # The server should have dropped most of the messages
    assert pong_count <= WS_MAX_MESSAGES, "Server did not drop messages exceeding the rate limit"
