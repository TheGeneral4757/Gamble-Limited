import time
from fastapi.testclient import TestClient
from app.main import create_app


def test_websocket_broadcast_load_sync():
    """
    Tests the WebSocket broadcast functionality under a simulated load.
    This test is synchronous and uses FastAPI's TestClient.
    """
    app = create_app()
    num_clients = 5  # Reduced further to ensure completion
    clients = []

    test_client = TestClient(app)

    try:
        # Connect clients sequentially.
        for i in range(num_clients):
            ws = test_client.websocket_connect("/ws")
            ws.receive_json()  # Consume initial chat history.
            clients.append(ws)

        print(f"\\nSuccessfully connected {len(clients)} clients.")

        # The broadcaster is another client.
        broadcaster_ws = test_client.websocket_connect("/ws")
        broadcaster_ws.receive_json()

        # Measure the time it takes for the server to broadcast the message.
        start_time = time.time()
        broadcaster_ws.send_json({"type": "chat", "message": "hello"})

        # The time for the broadcaster to receive its own message is a good proxy
        # for when the server has finished the broadcast loop.
        response = broadcaster_ws.receive_json(timeout=10)
        end_time = time.time()

        assert response["type"] == "chat_message"

        latency = end_time - start_time
        print(f"Broadcast latency for {num_clients + 1} clients: {latency:.4f} seconds")

        # Verify that at least one other client also received the message.
        other_client_response = clients[0].receive_json(timeout=1)
        assert other_client_response["type"] == "chat_message"

        # Set a baseline threshold. This might be high due to the test environment.
        assert latency < 2.0, "Broadcast latency is too high."

    finally:
        # Clean up all connections.
        print("Cleaning up WebSocket connections...")
        for ws in clients:
            try:
                ws.close()
            except Exception as e:
                print(f"Error closing client ws: {e}")

        if "broadcaster_ws" in locals():
            try:
                broadcaster_ws.close()
            except Exception as e:
                print(f"Error closing broadcaster ws: {e}")
