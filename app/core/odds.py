"""
Odds configuration loader for dynamic game odds.
Loads from ODDS-CHANGER.json and supports real-time reloading.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logger import get_logger
from app.config import PROJECT_ROOT

logger = get_logger("odds")

ODDS_FILE = PROJECT_ROOT / "ODDS-CHANGER.json"

# Cache for loaded odds
_odds_cache: Optional[Dict] = None
_last_load_time: Optional[datetime] = None


def load_odds(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load game odds from ODDS-CHANGER.json.
    Caches the result and reloads if file has changed.

    Args:
        force_reload: Force reload even if cached

    Returns:
        Dict with all game odds configuration
    """
    global _odds_cache, _last_load_time

    # Check if we need to reload
    if _odds_cache is not None and not force_reload:
        # Check file modification time
        try:
            file_mtime = datetime.fromtimestamp(ODDS_FILE.stat().st_mtime)
            if _last_load_time and file_mtime <= _last_load_time:
                return _odds_cache
        except Exception:
            pass

    # Load from file
    try:
        with open(ODDS_FILE, "r", encoding="utf-8") as f:
            _odds_cache = json.load(f)
            _last_load_time = datetime.now()
            logger.info("Loaded game odds from ODDS-CHANGER.json")
    except FileNotFoundError:
        logger.warning("ODDS-CHANGER.json not found, using defaults")
        _odds_cache = get_default_odds()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ODDS-CHANGER.json: {e}")
        _odds_cache = get_default_odds()

    return _odds_cache


def get_default_odds() -> Dict[str, Any]:
    """Return default odds if file is missing or invalid."""
    return {
        "plinko": {
            "center_bias": 0.40,
            "multipliers": {
                "16": [8, 4, 2, 1, 0.5, 0.3, 0.2, 0.3, 0.3, 0.2, 0.3, 0.5, 1, 2, 4, 8],
                "12": [5, 2.5, 1.5, 0.7, 0.3, 0.2, 0.2, 0.3, 0.7, 1.5, 2.5, 5],
                "8": [3, 1.5, 0.5, 0.3, 0.3, 0.5, 1.5, 3],
            },
        },
        "slots": {
            "symbol_weights": {
                "🍒": 28,
                "🍋": 24,
                "🍊": 18,
                "🍇": 14,
                "🔔": 9,
                "💎": 5,
                "7️⃣": 2,
            },
            "payouts_3x": {
                "🍒": 4,
                "🍋": 6,
                "🍊": 10,
                "🍇": 15,
                "🔔": 25,
                "💎": 50,
                "7️⃣": 77,
            },
            "payouts_2x": {
                "🍒": 1,
                "🍋": 1.5,
                "🍊": 2,
                "🍇": 2.5,
                "🔔": 4,
                "💎": 8,
                "7️⃣": 15,
            },
        },
        "coinflip": {"player_odds": 0.50, "payout_multiplier": 2.0},
        "roulette": {
            "house_edge_enabled": True,
            "single_number_payout": 35,
            "color_payout": 2,
            "dozen_payout": 3,
        },
    }


def get_game_odds(game: str) -> Dict[str, Any]:
    """
    Get odds for a specific game.

    Args:
        game: Game name (plinko, slots, coinflip, roulette)

    Returns:
        Dict with game-specific odds
    """
    odds = load_odds()
    return odds.get(game, {})


def save_odds(odds_data: Dict[str, Any]) -> bool:
    """
    Save updated odds to ODDS-CHANGER.json.

    Args:
        odds_data: Complete odds configuration

    Returns:
        True if saved successfully
    """
    global _odds_cache, _last_load_time

    try:
        # Preserve comments/instructions
        current = load_odds()

        # Update with new data (preserve _comment and _instructions)
        for key in ["_comment", "_instructions"]:
            if key in current and key not in odds_data:
                odds_data[key] = current[key]

        with open(ODDS_FILE, "w", encoding="utf-8") as f:
            json.dump(odds_data, f, indent=4, ensure_ascii=False)

        # Update cache
        _odds_cache = odds_data
        _last_load_time = datetime.now()

        logger.info("Saved updated odds to ODDS-CHANGER.json")
        return True
    except Exception as e:
        logger.error(f"Failed to save odds: {e}")
        return False


def reload_odds() -> Dict[str, Any]:
    """Force reload odds from file."""
    return load_odds(force_reload=True)
