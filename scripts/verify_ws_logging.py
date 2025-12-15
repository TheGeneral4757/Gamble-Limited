import asyncio
import websockets
import json


async def verify_websocket_logging():
    """
    Connects to the WebSocket, sends a ping, and disconnects to verify logging.
    """
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connection established.")

            # Send a ping message
            await websocket.send(json.dumps({"type": "ping"}))
            print("Sent: ping")

            # Wait for pong response
            response = await websocket.recv()
            print(f"Received: {response}")

            print("WebSocket connection will be closed.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    print("Running WebSocket logging verification script...")
    asyncio.run(verify_websocket_logging())
    print("Verification script finished.")
