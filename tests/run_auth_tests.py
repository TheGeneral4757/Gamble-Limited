import sys
import os
import asyncio
import time
import uvicorn
import threading
import traceback

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from tests.test_all import results

# ==================== Test Server ====================
TEST_PORT = 8123
TEST_HOST = "127.0.0.1"


class TestServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = None

    def run(self):
        config = uvicorn.Config(app, host=TEST_HOST, port=TEST_PORT, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()

    def shutdown(self):
        if self.server:
            self.server.should_exit = True


# ==================== Main Runner ====================
def run_focused_tests():
    """Import and run only the tests from tests.test_auth."""
    from tests.test_auth import (
        test_login_sets_signature,
        test_websocket_valid_signature,
        test_websocket_invalid_signature,
        test_websocket_missing_signature,
        test_websocket_tampered_cookie,
        test_websocket_rate_limiter,
    )

    print("\n🔐 Authentication & Authorization Tests")
    print("-" * 40)
    asyncio.run(test_login_sets_signature())
    asyncio.run(test_websocket_valid_signature())
    asyncio.run(test_websocket_invalid_signature())
    asyncio.run(test_websocket_missing_signature())
    asyncio.run(test_websocket_tampered_cookie())

    print("\n🛡️ Game Warden Anti-Cheat Tests")
    print("-" * 40)
    asyncio.run(test_websocket_rate_limiter())


if __name__ == "__main__":
    print("🧪 Starting focused test runner for auth tests...")
    server = TestServer()
    server.start()
    time.sleep(2)  # Give server time to start

    try:
        run_focused_tests()
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        traceback.print_exc()
        results["failed"] += 1
    finally:
        server.shutdown()
        server.join(timeout=2)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    total = results["passed"] + results["failed"]
    print(f"  Total tests run: {total}")
    print(f"  ✓ Passed: {results['passed']}")
    print(f"  ✗ Failed: {results['failed']}")

    if results["failed"] > 0:
        print("\n❌ Failed Tests:")
        for t in results["tests"]:
            if t["status"] != "PASS":
                print(f"  - {t['name']}: {t.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)

    sys.exit(0 if results["failed"] == 0 else 1)
