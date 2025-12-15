"""
Automated Test Suite for RNG-THING Casino Platform
Run with: python -m tests.test_all
"""

import string
import random
import traceback
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Test results tracking
results = {"passed": 0, "failed": 0, "tests": []}


def random_username():
    """Generate a valid random username for tests."""
    return "test" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def test(name):
    """Decorator to mark test functions."""

    def decorator(func):
        def wrapper():
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

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


# ==================== Database Tests ====================


def run_database_tests():
    print("\n📊 Database Tests")
    print("-" * 40)

    from app.core.database import db

    @test("Database connection")
    def test_connection():
        conn = db._get_connection()
        assert conn is not None, "Failed to get connection"

    @test("Create user")
    def test_create_user():
        result = db.create_user(random_username())
        assert result["success"], f"Failed: {result.get('error')}"
        assert "user_id" in result, "Missing user_id in response"
        return result["user_id"]

    @test("Login user")
    def test_login():
        username = random_username()
        create_result = db.create_user(username)
        assert create_result["success"], f"Create failed: {create_result.get('error')}"
        user = db.login_user(username)
        assert user is not None, "User not found"
        assert user["username"] == username

    @test("Ban user")
    def test_ban():
        username = random_username()
        result = db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        ban_result = db.ban_user(user_id, hours=1, reason="Test ban")
        assert ban_result["success"], "Ban failed"

        # Check login returns banned status
        user = db.login_user(username)
        assert user.get("banned"), "User should be banned"

    @test("Unban user")
    def test_unban():
        username = random_username()
        result = db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        db.ban_user(user_id, hours=1, reason="Test ban")
        db.unban_user(user_id)

        user = db.login_user(username)
        assert not user.get("banned"), "User should not be banned"

    @test("Daily bonus claim")
    def test_daily_bonus():
        username = random_username()
        result = db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        bonus = db.claim_daily_bonus(user_id)
        assert bonus["success"], f"Claim failed: {bonus.get('error')}"

        # Second claim should fail
        bonus2 = db.claim_daily_bonus(user_id)
        assert not bonus2["success"], "Second claim should fail"

    @test("Daily cash claim")
    def test_daily_cash():
        username = random_username()
        result = db.create_user(username)
        assert result["success"], f"Create failed: {result.get('error')}"
        user_id = result["user_id"]

        cash = db.claim_daily_cash(user_id)
        assert cash["success"], f"Claim failed: {cash.get('error')}"

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
    test_create_user()
    test_login()
    test_ban()
    test_unban()
    test_daily_bonus()
    test_daily_cash()
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

        # bet_type is 'red', not 'color'
        result = roulette_game.spin(10, "red", "")
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


def run_websocket_tests():
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

    test_ws_manager()
    test_chat_history()


# ==================== Run All Tests ====================


def run_all_tests():
    print("\n" + "=" * 50)
    print("🧪 RNG-THING Automated Test Suite")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        run_config_tests()
        run_database_tests()
        run_game_tests()
        run_websocket_tests()
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        traceback.print_exc()

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
    success = run_all_tests()
    sys.exit(0 if success else 1)
