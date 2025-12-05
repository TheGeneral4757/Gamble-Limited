import json
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel

CONFIG_PATH = Path("config.json")

class ServerConfig(BaseModel):
    host: str
    port: int
    debug: bool
    name: str

class SecurityConfig(BaseModel):
    admin_username: str
    admin_password_hash: str
    secret_key: str

class EconomyConfig(BaseModel):
    starting_cash: float
    starting_credits: float
    base_exchange_rate: float
    fluctuation_range: float

class GameConfig(BaseModel):
    enabled: bool
    min_bet: float
    max_bet: float
    payout_rate: float = 0.0  # Optional, not all games use this

class GamesConfig(BaseModel):
    slots: GameConfig
    blackjack: GameConfig
    roulette: GameConfig
    plinko: GameConfig
    coinflip: GameConfig

class AppConfig(BaseModel):
    server: ServerConfig
    security: SecurityConfig
    economy: EconomyConfig
    games: GamesConfig

import bcrypt

def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    
    # Auto-hash password if it's not already hashed
    # Bcrypt hashes start with $2 and are 60 chars long
    current_pwd = data["security"]["admin_password_hash"]
    if not (current_pwd.startswith("$2") and len(current_pwd) == 60):
        print("Configuration: Detected plain text admin password. Hashing and updating config.json...")
        # bcrypt.hashpw returns bytes, so we decode to utf-8 for storage
        hashed_bytes = bcrypt.hashpw(current_pwd.encode('utf-8'), bcrypt.gensalt())
        hashed_pwd = hashed_bytes.decode('utf-8')
        data["security"]["admin_password_hash"] = hashed_pwd
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)
    
    return AppConfig(**data)

# Global config instance
settings = load_config()
