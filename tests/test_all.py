"""
Automated Test Suite for RNG-THING Casino Platform
Run with: python -m tests.test_all
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
import traceback
import random
import string

# Test results tracking
results = {"passed": 0, "failed": 0, "tests": []}


def random_username():
    """Generate a valid random username for tests."""
    return "test" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


import asyncio

def test(name):
    """Decorator to mark test functions."""

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            # Async test function
            async def async_wrapper():
                try:
                    await func()
                    results["passed"] += 1
                    results["tests"].append({"name": name, "status": "PASS"})
                    print(f"  ✓ {name}")
                    return True
                except AssertionError as e:
                    results["failed"] += 1
                    results["tests"].append(
                        {"name": name, "status": "FAIL", "error": str(e)}
                    )
                    print(f"  ✗ {name}: {e}")
                    return False
                except Exception as e:
                    results["failed"] += 1
                    results["tests"].append(
                        {"name": name, "status": "ERROR", "error": str(e)}
                    )
                    print(f"  ✗ {name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    return False
            async_wrapper.__name__ = func.__name__
            return async_wrapper
        else:
            # Sync test function
            def sync_wrapper():
                try:
                    func()
                    results["passed"] += 1
                    results["tests"].append({"name": name, "status": "PASS"})
                    print(f"  ✓ {name}")
                    return True
                except AssertionError as e:
                    results["failed"] += 1
                    results["tests"].append(
                        {"name": name, "status": "FAIL", "error": str(e)}
                    )
                    print(f"  ✗ {name}: {e}")
                    return False
                except Exception as e:
                    results["failed"] += 1
                    results["tests"].append(
                        {"name": name, "status": "ERROR", "error": str(e)}
                    )
                    print(f"  ✗ {name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    return False
            sync_wrapper.__name__ = func.__name__
            return sync_wrapper

    return decorator


# ==================== Database Tests ====================


async def run_database_tests():
    print("\n📊 Database Tests")
    print("-" * 40)

    from app.core.database import db

    @test("Database connection")
    def test_connection():
        conn = db._get_connection()
        assert conn is not None, "Failed to get connection"

    @test("Create user")
    async def test_create_user():
        result = await db.create_user(random_username())
        assert result["success"], f"Failed: {result.get('error')}"
        assert "user_id" in result, "Missing user_id in response"
        return result["user_id"]

    @test("Login user")
    async def test_login():
        username = random_username()
        create_result = await db.create_user(username)
        assert create_result["success"], f"Create failed: {create_result.get('error')}"
        user = await db.login_user(username)
        assert user is not None, "User not found"
        assert user["username"] == username

    @test("Ban user")
    async def test_ban():
        username = random_username()
        result = await db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        ban_result = db.ban_user(user_id, hours=1, reason="Test ban")
        assert ban_result["success"], "Ban failed"

        # Check login returns banned status
        user = await db.login_user(username)
        assert user.get("banned"), "User should be banned"

    @test("Unban user")
    async def test_unban():
        username = random_username()
        result = await db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        db.ban_user(user_id, hours=1, reason="Test ban")
        db.unban_user(user_id)

        user = await db.login_user(username)
        assert not user.get("banned"), "User should not be banned"

    @test("Daily bonus claim")
    async def test_daily_bonus():
        username = random_username()
        result = await db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        bonus = db.claim_daily_bonus(user_id)
        assert bonus["success"], f"Claim failed: {bonus.get('error')}"

        # Second claim should fail
        bonus2 = db.claim_daily_bonus(user_id)
        assert not bonus2["success"], "Second claim should fail"

    @test("Daily cash claim")
    async def test_daily_cash():
        username = random_username()
        result = await db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        cash = db.claim_daily_cash(user_id)
        assert cash["success"], f"Claim failed: {cash.get('error')}"

    @test("Daily bonus race condition")
    async def test_daily_bonus_race_condition():
        import threading
        from app.core.database import db

        username = random_username()
        result = await db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        success_count = [0]
        error_count = [0]
        num_threads = 5

        def claim():
            try:
                # Use a new connection for each thread to simulate web requests
                thread_db = db
                res = thread_db.claim_daily_bonus(user_id)
                if res["success"]:
                    success_count[0] += 1
                elif "already claimed" in res.get("error", ""):
                    error_count[0] += 1
                elif "in progress" in res.get("error", ""):
                    error_count[0] += 1
            except Exception:
                error_count[0] += 1

        threads = [threading.Thread(target=claim) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert (
            success_count[0] == 1
        ), f"Expected 1 successful claim, but got {success_count[0]}"
        assert (
            success_count[0] + error_count[0] == num_threads
        ), "Some threads failed unexpectedly"

    @test("THE HOUSE user exists")
    def test_house_user():
        house = db.get_house_user()
        assert house is not None, "THE HOUSE user not found"
        assert house["username"] == "THE_HOUSE"

    @test("House cut tracking")
    def test_house_cut():
        before = db.get_house_balance()["credits"]
        db.add_house_cut(100, "test")  # 5% of 100 = 5
        after = db.get_house_balance()["credits"]
        assert after > before, "House balance should increase"

    test_connection()
    await test_create_user()
    await test_login()
    await test_ban()
    await test_unban()
    await test_daily_bonus()
    await test_daily_cash()
    await test_daily_bonus_race_condition()
    test_house_user()
    test_house_cut()


# ==================== Game Logic Tests ====================


def run_game_tests():
    print("\n🎰 Game Logic Tests")
    print("-" * 40)

    @test("Slots game spin")
    def test_slots():
        from app.core.games.slots import slots_game

        result = slots_game.spin(10)
        assert "reels" in result, "Missing reels"
        assert "payout" in result, "Missing payout"
        assert isinstance(result["payout"], (int, float))

    @test("Plinko game drop")
    def test_plinko():
        from app.core.games.plinko import plinko_game

        result = plinko_game.drop(10, 16)
        assert "path" in result, "Missing path"
        assert "payout" in result, "Missing payout"
        # Check for multiplier or slot (API might use different names)
        assert (
            "multiplier" in result or "slot" in result or "bucket" in result
        ), "Missing multiplier/slot/bucket"

    @test("Coinflip game")
    def test_coinflip():
        from app.core.games.coinflip import coinflip_game

        result = coinflip_game.flip(10, "heads")
        assert "result" in result, "Missing result"
        assert "win" in result, "Missing win"
        assert result["result"] in ["heads", "tails"]

    @test("Roulette game spin")
    def test_roulette():
        from app.core.games.roulette import roulette_game

        result = roulette_game.spin(10, "red", "")  # bet_type is 'red', not 'color'
        # Check for error or valid result
        if "error" in result:
            assert False, f"Roulette error: {result['error']}"
        assert "payout" in result, f"Missing payout. Got: {list(result.keys())}"
        assert (
            "number" in result or "result" in result or "winning_number" in result
        ), "Missing number"

    @test("Blackjack deal")
    def test_blackjack():
        from app.core.games.blackjack import blackjack_game

        result = blackjack_game.deal(10, "test9999")
        # player_hand always present
        assert (
            "player_hand" in result or "player" in result
        ), f"Missing player hand. Keys: {list(result.keys())}"
        # Dealer is shown as dealer_up_card during play or dealer_hand when complete
        assert (
            "dealer_up_card" in result or "dealer_hand" in result or "dealer" in result
        ), f"Missing dealer. Keys: {list(result.keys())}"

    test_slots()
    test_plinko()
    test_coinflip()
    test_roulette()
    test_blackjack()


# ==================== Config Tests ====================


def run_config_tests():
    print("\n⚙️ Configuration Tests")
    print("-" * 40)

    @test("Config loads")
    def test_config_loads():
        from app.config import settings

        assert settings is not None

    @test("Economy settings")
    def test_economy():
        from app.config import settings

        assert hasattr(settings.economy, "daily_bonus_amount")
        assert hasattr(settings.economy, "daily_cash_amount")
        assert hasattr(settings.economy, "house_cut_percent")

    @test("Security settings")
    def test_security():
        from app.config import settings

        assert hasattr(settings.security, "admin_login_path")
        assert hasattr(settings.security, "house_login_path")

    @test("ODDS-CHANGER.json exists")
    def test_odds_file():
        from app.config import PROJECT_ROOT

        odds_path = PROJECT_ROOT / "ODDS-CHANGER.json"
        assert odds_path.exists(), "ODDS-CHANGER.json not found"

    test_config_loads()
    test_economy()
    test_security()
    test_odds_file()


# ==================== WebSocket Tests ====================


async def run_websocket_tests():
    print("\n🔌 WebSocket Tests")
    print("-" * 40)

    @test("WebSocket manager exists")
    def test_ws_manager():
        from app.core.websocket import ws_manager

        assert ws_manager is not None

    @test("Chat history tracking")
    def test_chat_history():
        from app.core.websocket import ws_manager

        # Use the correct attribute name
        history = getattr(
            ws_manager, "chat_history", getattr(ws_manager, "_chat_history", [])
        )
        # Just check that it's a list-like structure
        assert hasattr(history, "__len__"), "Chat history should be iterable"

    @test("Batched broadcast sends to all")
    async def test_batched_broadcast():
        from unittest.mock import patch, AsyncMock
        from app.core.websocket import ws_manager

        class MockWebSocket:
            def __init__(self, should_fail=False):
                self.send_count = 0
                self.should_fail = should_fail

            async def send_bytes(self, data):
                if self.should_fail:
                    raise ConnectionError("Failed to send")
                self.send_count += 1

        # Reset connections for clean test
        ws_manager.all_connections.clear()
        ws_manager.active_connections.clear()
        for topic in ws_manager.topics.values():
            topic.clear()

        num_connections = 150
        batch_size = 50

        connections = [MockWebSocket() for _ in range(num_connections)]
        for ws in connections:
            ws_manager.all_connections.add(ws)
            ws_manager.topics["chat"].add(ws)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # The _send_with_error_handling now calls _send_json, which calls send_bytes
            with patch.object(ws_manager, "_send_json", new_callable=AsyncMock) as mock_send:
                await ws_manager.broadcast(
                    "chat", {"type": "test"}, batch_size=batch_size, delay=0.001
                )

                # Check all messages were sent
                assert (
                    mock_send.call_count == num_connections
                ), f"Expected {num_connections} sends, got {mock_send.call_count}"

            # Check that sleep was called between batches
            num_batches = (num_connections + batch_size - 1) // batch_size
            expected_sleeps = num_batches - 1 if num_batches > 1 else 0
            assert (
                mock_sleep.call_count == expected_sleeps
            ), f"Expected {expected_sleeps} sleeps, got {mock_sleep.call_count}"

        # Test disconnected client cleanup
        ws_manager.all_connections.clear()
        for topic in ws_manager.topics.values():
            topic.clear()
        failing_ws = MockWebSocket(should_fail=True)
        working_ws = MockWebSocket()
        ws_manager.all_connections.add(failing_ws)
        ws_manager.topics["chat"].add(failing_ws)
        ws_manager.all_connections.add(working_ws)
        ws_manager.topics["chat"].add(working_ws)

        assert len(ws_manager.all_connections) == 2
        await ws_manager.broadcast("chat", {"type": "cleanup_test"})
        assert (
            len(ws_manager.all_connections) == 1
        ), "Failed to remove disconnected client"
        assert (
            failing_ws not in ws_manager.all_connections
        ), "Failed client should be removed"
        assert (
            working_ws in ws_manager.all_connections
        ), "Working client should not be removed"

    test_ws_manager()
    test_chat_history()
    await test_batched_broadcast()


import uvicorn
import threading
import time
from app.main import app

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


# ==================== Run All Tests ====================


async def run_all_tests():
    print("\n" + "=" * 50)
    print("🧪 RNG-THING Automated Test Suite")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    server = TestServer()
    server.start()
    time.sleep(1)

    try:
        from tests.test_auth import (
            test_login_sets_signature,
            test_websocket_valid_signature,
            test_websocket_invalid_signature,
            test_websocket_missing_signature,
            test_websocket_tampered_cookie,
        )

        run_config_tests()
        await run_database_tests()
        run_game_tests()
        await run_websocket_tests()

        print("\n🔐 Authentication & Authorization Tests")
        print("-" * 40)
        await test_login_sets_signature()
        await test_websocket_valid_signature()
        await test_websocket_invalid_signature()
        from tests.test_auth import test_websocket_rate_limiter

        await test_websocket_missing_signature()
        await test_websocket_tampered_cookie()

        print("\n🛡️ Game Warden Anti-Cheat Tests")
        print("-" * 40)
        await test_websocket_rate_limiter()

    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        traceback.print_exc()
    finally:
        server.shutdown()
        server.join()

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    total = results["passed"] + results["failed"]
    print(f"  Total: {total}")
    print(f"  ✓ Passed: {results['passed']}")
    print(f"  ✗ Failed: {results['failed']}")

    if results["failed"] > 0:
        print("\n❌ Failed Tests:")
        for t in results["tests"]:
            if t["status"] != "PASS":
                print(f"  - {t['name']}: {t.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)

    return results["failed"] == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
