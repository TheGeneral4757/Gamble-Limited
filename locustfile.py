import httpx
from locust import User, task, between
from websocket import create_connection

class WebSocketUser(User):
    wait_time = between(1, 2)
    host = "http://127.0.0.1:8000"

    def on_start(self):
        """
        Called when a Locust user starts.
        Logs in the user and creates a websocket connection.
        """
        # Login to get session cookie. A successful login returns a 303 redirect.
        # We must disable redirects to capture the 'session' cookie from the first response.
        self.client = httpx.Client(base_url=self.host, follow_redirects=False)

        try:
            response = self.client.post("/auth/login", data={"username": "testuser", "password": "password"})
        except httpx.RequestError as e:
            print(f"Login request failed during connection: {e}")
            self.environment.runner.quit()
            return

        # A successful login MUST return a 303 redirect.
        if response.status_code != 303:
            print(f"Login failed. Expected status 303, but got {response.status_code}. Response: {response.text}")
            self.environment.runner.quit()
            return

        session_cookie = response.cookies.get("session")
        if not session_cookie:
            print("Failed to get session cookie from login response.")
            self.environment.runner.quit()
            return

        cookie_header = f"session={session_cookie}"

        # Establish WebSocket connection with cookie
        try:
            self.ws = create_connection(
                "ws://127.0.0.1:8000/ws",
                header={"Cookie": cookie_header}
            )
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
            self.environment.runner.quit()

    def on_stop(self):
        """
        Called when a Locust user stops.
        Closes the websocket connection and the httpx client.
        """
        if hasattr(self, 'ws'):
            self.ws.close()
        if hasattr(self, 'client'):
            self.client.close()

    @task
    def send_ping(self):
        """
        Sends a ping message to the websocket and waits for a pong response.
        """
        if not hasattr(self, 'ws'):
            return

        try:
            self.ws.send('{"type":"ping"}')
            result = self.ws.recv()
            # The orjson library used by the server sends bytes
            assert result == b'{"type":"pong"}'
        except Exception as e:
            # If the connection is broken, stop this user.
            print(f"WebSocket error during ping: {e}")
            self.environment.runner.stop()
