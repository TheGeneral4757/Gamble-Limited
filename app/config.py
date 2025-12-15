"""
Configuration management for RNG-THING.
Supports config.json with environment variable overrides.
All paths are resolved relative to the project root.
"""

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars only

# Project root directory (parent of 'app' folder)
PROJECT_ROOT = Path(__file__).parent.parent


def get_env(key: str, default: str = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    val = os.environ.get(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


# ==================== Configuration Models ====================

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True
    name: str = "Gamble Limited"


class SecurityConfig(BaseModel):
    admin_username: str = "admin"
    admin_password_hash: str = ""
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION_PLEASE"
    admin_login_path: str = "/admin-portal"  # Hidden admin login URL
    house_login_path: str = "/the-house"  # Hidden house login URL


class EconomyConfig(BaseModel):
    starting_cash: float = 1000.0
    starting_credits: float = 500.0
    base_exchange_rate: float = 10.0
    fluctuation_range: float = 0.05
    daily_bonus_amount: float = 100.0
    daily_bonus_cooldown_hours: int = 24
    daily_cash_amount: float = 50.0
    daily_cash_cooldown_hours: int = 24
    house_cut_percent: float = 5.0  # Percent of bets that go to THE HOUSE


class GameConfig(BaseModel):
    enabled: bool = True
    min_bet: float = 1.0
    max_bet: float = 1000.0
    payout_rate: float = 0.95

    class Config:
        extra = "allow"  # Allow extra fields for game-specific configs


class GamesConfig(BaseModel):
    slots: GameConfig = Field(default_factory=GameConfig)
    blackjack: GameConfig = Field(default_factory=GameConfig)
    roulette: GameConfig = Field(default_factory=GameConfig)
    plinko: GameConfig = Field(default_factory=GameConfig)
    coinflip: GameConfig = Field(default_factory=GameConfig)
    scratch_cards: GameConfig = Field(default_factory=GameConfig)
    highlow: GameConfig = Field(default_factory=GameConfig)
    dice: GameConfig = Field(default_factory=GameConfig)
    number_guess: GameConfig = Field(default_factory=GameConfig)


class LotteryConfig(BaseModel):
    """Lottery game configuration."""
    enabled: bool = True
    ticket_price: float = 50.0
    max_tickets_per_user: int = 100
    numbers_to_pick: int = 6
    number_range_max: int = 49
    draw_schedule: str = "first_friday"
    draw_hour: int = 12
    draw_minute: int = 0
    timezone: str = "America/Chicago"
    initial_jackpot: float = 10000.0
    jackpot_contribution_percent: float = 70.0
    lump_sum_percent: float = 50.0
    installment_weeks: int = 52

    class Config:
        extra = "allow"


class RateLimitConfig(BaseModel):
    enabled: bool = True
    game_requests: str = "30/minute"  # For game actions like spins
    api_requests: str = "60/minute"   # For general API calls


class GambleFridayConfig(BaseModel):
    """Gamble Friday event configuration."""
    enabled: bool = True
    start_hour: int = 6   # 6 AM
    end_hour: int = 18    # 6 PM
    timezone: str = "America/Chicago"
    winnings_multiplier: float = 1.5  # 1.5x winnings
    win_rate_reduction: float = 0.05  # 5% reduction in win rates
    max_bet_multiplier: int = 3  # 3x max bets


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_to_file: bool = False
    formatter: str = "color"


class PathsConfig(BaseModel):
    """All paths are relative to PROJECT_ROOT."""
    config_file: str = "config.json"
    database: str = "data/casino.db"
    log_file: str = "data/app.log"
    
    def get_config_path(self) -> Path:
        return PROJECT_ROOT / self.config_file
    
    def get_db_path(self) -> Path:
        return PROJECT_ROOT / self.database
    
    def get_log_path(self) -> Path:
        return PROJECT_ROOT / self.log_file


class AppConfig(BaseModel):
    """Main application configuration."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    games: GamesConfig = Field(default_factory=GamesConfig)
    lottery: LotteryConfig = Field(default_factory=LotteryConfig)
    gamble_friday: GambleFridayConfig = Field(default_factory=GambleFridayConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


# ==================== Configuration Loading ====================

def load_config() -> AppConfig:
    """
    Load configuration from config.json with environment variable overrides.
    Environment variables take precedence over config.json values.
    """
    import bcrypt
    
    config_path = PROJECT_ROOT / "config.json"
    
    # Start with defaults
    data = {}
    
    # Load from config.json if it exists
    if config_path.exists():
        with open(config_path, "r") as f:
            data = json.load(f)
    
    # Add new config sections if not present
    if "rate_limit" not in data:
        data["rate_limit"] = {}
    if "logging" not in data:
        data["logging"] = {}
    if "paths" not in data:
        data["paths"] = {}
    
    # Add new economy fields if not present
    if "daily_bonus_amount" not in data.get("economy", {}):
        data.setdefault("economy", {})["daily_bonus_amount"] = 100.0
    if "daily_bonus_cooldown_hours" not in data.get("economy", {}):
        data.setdefault("economy", {})["daily_bonus_cooldown_hours"] = 24
    
    # Add admin_login_path if not present
    if "admin_login_path" not in data.get("security", {}):
        data.setdefault("security", {})["admin_login_path"] = "/admin-portal"
    
    # Apply environment variable overrides
    if get_env("SERVER_HOST"):
        data.setdefault("server", {})["host"] = get_env("SERVER_HOST")
    if get_env("SERVER_PORT"):
        data.setdefault("server", {})["port"] = get_env_int("SERVER_PORT", 8000)
    if get_env("DEBUG"):
        data.setdefault("server", {})["debug"] = get_env_bool("DEBUG")
    
    if get_env("SECRET_KEY"):
        data.setdefault("security", {})["secret_key"] = get_env("SECRET_KEY")
    if get_env("ADMIN_LOGIN_PATH"):
        data.setdefault("security", {})["admin_login_path"] = get_env("ADMIN_LOGIN_PATH")
    
    if get_env("DB_PATH"):
        data.setdefault("paths", {})["database"] = get_env("DB_PATH")
    
    if get_env("LOG_LEVEL"):
        data.setdefault("logging", {})["level"] = get_env("LOG_LEVEL")
    if get_env("LOG_TO_FILE"):
        data.setdefault("logging", {})["log_to_file"] = get_env_bool("LOG_TO_FILE")
    if get_env("LOG_FORMATTER"):
        data.setdefault("logging", {})["formatter"] = get_env("LOG_FORMATTER")
    
    if get_env("RATE_LIMIT_ENABLED"):
        data.setdefault("rate_limit", {})["enabled"] = get_env_bool("RATE_LIMIT_ENABLED", True)
    if get_env("RATE_LIMIT_GAME_REQUESTS"):
        data.setdefault("rate_limit", {})["game_requests"] = get_env("RATE_LIMIT_GAME_REQUESTS")
    if get_env("RATE_LIMIT_API_REQUESTS"):
        data.setdefault("rate_limit", {})["api_requests"] = get_env("RATE_LIMIT_API_REQUESTS")
    
    # Auto-hash password if it's not already hashed
    if "security" in data:
        current_pwd = data["security"].get("admin_password_hash", "")
        if current_pwd and not (current_pwd.startswith("$2") and len(current_pwd) == 60):
            try:
                print("Configuration: Detected plain text admin password. Hashing and updating config.json...")
                hashed_bytes = bcrypt.hashpw(current_pwd.encode('utf-8'), bcrypt.gensalt())
                hashed_pwd = hashed_bytes.decode('utf-8')
                data["security"]["admin_password_hash"] = hashed_pwd
                
                # Save updated config
                with open(config_path, "w") as f:
                    json.dump(data, f, indent=4)
            except (OSError, PermissionError):
                print("Configuration: Warning - Could not update config.json (Read-Only filesystem). Running with hashed password in memory only.")
                # We still update the in-memory data object so the app works for this session
                hashed_bytes = bcrypt.hashpw(current_pwd.encode('utf-8'), bcrypt.gensalt())
                data["security"]["admin_password_hash"] = hashed_bytes.decode('utf-8')
    
    return AppConfig(**data)


def save_config(config: AppConfig):
    """Save configuration to config.json."""
    config_path = PROJECT_ROOT / "config.json"
    
    # Convert to dict, excluding paths (they're computed)
    data = config.model_dump(exclude={"paths"})
    
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)


def update_config_value(section: str, key: str, value):
    """Update a single configuration value and save."""
    config_path = PROJECT_ROOT / "config.json"
    
    with open(config_path, "r") as f:
        data = json.load(f)
    
    if section not in data:
        data[section] = {}
    data[section][key] = value
    
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)
    
    # Reload global settings
    global settings
    settings = load_config()


# Global config instance
settings = load_config()
