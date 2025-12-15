import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import settings

class TestApiRateLimit(unittest.TestCase):
    def setUp(self):
        # Create a new app instance for each test to ensure a clean state
        self.app = create_app()
        self.client = TestClient(self.app)

        # Ensure rate limiting is enabled for the test
        settings.rate_limit.enabled = True
        settings.rate_limit.game_requests = "5/second"

    @patch('app.core.economy.economy.get_balance')
    def test_rate_limit_applied_to_game_endpoints(self, mock_get_balance):
        # Mock the balance to ensure bet validation passes
        mock_get_balance.return_value = {"credits": 999999, "cash": 999999}

        endpoint = "/api/games/slots/spin"
        body = {"bet": 10}

        with TestClient(self.app) as client:
            client.cookies = {"user_id": "1"}
            # The first 5 requests should succeed
            for i in range(5):
                response = client.post(endpoint, json=body)
                self.assertNotEqual(
                    response.status_code, 429,
                    f"Request {i+1}/6 should have succeeded, but got 429."
                )

            # The 6th request should be rate-limited
            response = client.post(endpoint, json=body)
            self.assertEqual(
                response.status_code, 429,
                f"The 6th request should have been rate-limited (429), but got {response.status_code}."
            )

if __name__ == "__main__":
    unittest.main()
