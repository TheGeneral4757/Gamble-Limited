"""
Gamble Friday - Special Friday promotion checker
Fridays from 6:00 AM to 6:00 PM Chicago time:
- Increased winnings multiplier
- Higher max bets (3x)
- Slightly reduced win rates (except coinflip)
"""
from datetime import datetime
from typing import Optional
import os

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

from app.config import settings

# Environment variable for test mode (persists through uvicorn reload)
TEST_FRIDAY_ENV_VAR = "RNG_THING_TEST_FRIDAY"


def set_test_friday_mode(enabled: bool = True):
    """Enable or disable test Friday mode via environment variable."""
    os.environ[TEST_FRIDAY_ENV_VAR] = "1" if enabled else "0"


def is_test_friday_mode() -> bool:
    """Check if test Friday mode is enabled."""
    return os.environ.get(TEST_FRIDAY_ENV_VAR, "0") == "1"


def is_gamble_friday() -> bool:
    """
    Check if it's currently Gamble Friday.
    Returns True if:
    - It's Friday
    - Between start_hour and end_hour in Chicago timezone
    - Or test mode is enabled
    """
    # Test mode override (via environment variable)
    if is_test_friday_mode():
        return True
    
    # Check if feature is enabled
    if not hasattr(settings, 'gamble_friday') or not settings.gamble_friday.enabled:
        return False
    
    try:
        if PYTZ_AVAILABLE:
            tz = pytz.timezone(settings.gamble_friday.timezone)
            now = datetime.now(tz)
        else:
            # Fallback: use local time (may not be accurate)
            now = datetime.now()
        
        # Check if it's Friday (weekday 4)
        if now.weekday() != 4:
            return False
        
        # Check if within time window
        start_hour = settings.gamble_friday.start_hour
        end_hour = settings.gamble_friday.end_hour
        
        return start_hour <= now.hour < end_hour
        
    except Exception:
        return False


def get_friday_config() -> dict:
    """
    Get Gamble Friday configuration values.
    Returns defaults if not configured.
    """
    if not hasattr(settings, 'gamble_friday'):
        return {
            "winnings_multiplier": 1.0,
            "win_rate_reduction": 0.0,
            "max_bet_multiplier": 1
        }
    
    return {
        "winnings_multiplier": settings.gamble_friday.winnings_multiplier,
        "win_rate_reduction": settings.gamble_friday.win_rate_reduction,
        "max_bet_multiplier": settings.gamble_friday.max_bet_multiplier
    }


def get_adjusted_max_bet(base_max_bet: float) -> float:
    """Get max bet adjusted for Gamble Friday."""
    if is_gamble_friday():
        config = get_friday_config()
        return base_max_bet * config["max_bet_multiplier"]
    return base_max_bet


def get_winnings_multiplier() -> float:
    """Get winnings multiplier (1.0 normally, higher on Friday)."""
    if is_gamble_friday():
        config = get_friday_config()
        return config["winnings_multiplier"]
    return 1.0


def get_win_rate_adjustment(game: str = "") -> float:
    """
    Get win rate adjustment (0.0 normally, negative on Friday).
    Coinflip is exempt from reduction.
    """
    if game.lower() == "coinflip":
        return 0.0
    
    if is_gamble_friday():
        config = get_friday_config()
        return -config["win_rate_reduction"]  # Negative = reduce win rate
    return 0.0


# Singleton for easy import
gamble_friday = type('GambleFriday', (), {
    'is_active': staticmethod(is_gamble_friday),
    'get_config': staticmethod(get_friday_config),
    'get_adjusted_max_bet': staticmethod(get_adjusted_max_bet),
    'get_winnings_multiplier': staticmethod(get_winnings_multiplier),
    'get_win_rate_adjustment': staticmethod(get_win_rate_adjustment),
    'set_test_mode': staticmethod(set_test_friday_mode),
})()
