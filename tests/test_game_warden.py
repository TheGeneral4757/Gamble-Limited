"""
Game Warden Anti-Cheat & Abuse Mitigation Tests
"""

import asyncio
import websockets
from .test_auth import get_cookies, TEST_HOST, TEST_PORT, random_username
from .test_all import test


@test("WebSocket rejects oversized message")
async def test_websocket_rejects_oversized_message():
    """Verify that the server disconnects a client sending a message that exceeds the size limit."""
    username = random_username()
    password = "password123"
    cookies = await get_cookies(username, password)
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])

    uri = f"ws://{TEST_HOST}:{TEST_PORT}/ws"
    try:
        async with websockets.connect(
            uri, extra_headers=[("Cookie", cookie_header)]
        ) as websocket:
            # Message size limit is 4KB (4096 bytes). Create a payload larger than that.
            oversized_payload = b"a" * 5000

            await websocket.send(oversized_payload)

            # The server should disconnect us. We expect to receive a close frame.
            # If we try to receive after sending, it should raise a ConnectionClosed exception.
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                # We should not get here. If we do, the server didn't close the connection.
                assert (
                    False
                ), f"Server did not disconnect client. Got response: {response}"
            except websockets.exceptions.ConnectionClosed as e:
                # This is the expected outcome.
                assert (
                    e.code == 1009
                ), f"Expected close code 1009 (Message Too Big), but got {e.code}"
            except asyncio.TimeoutError:
                assert False, "Test timed out waiting for server to close connection."

    except Exception as e:
        assert False, f"Test failed with an unexpected exception: {e}"
