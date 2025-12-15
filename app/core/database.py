"""
Database module for persistent storage.
Uses SQLite for user balances, transaction history, and game statistics.
Enhanced with username-based login and admin system.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import threading
import hashlib

from app.core.logger import get_logger
from app.config import settings

# Get logger for this module
logger = get_logger("database")

# Database path from config (resolved relative to project root)
DB_PATH = settings.paths.get_db_path()


class Database:
    """Thread-safe SQLite database wrapper with user authentication."""

    _local = threading.local()

    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        logger.info(f"Initializing database at {DB_PATH}")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(DB_PATH), check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Users table - with password auth and daily bonus tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                is_admin INTEGER DEFAULT 0,
                cash REAL DEFAULT 1000.0,
                credits REAL DEFAULT 500.0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                total_lost REAL DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                biggest_win REAL DEFAULT 0,
                total_converted REAL DEFAULT 0,
                last_conversion_time TEXT,
                last_daily_claim TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Transactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                game TEXT,
                currency TEXT DEFAULT 'credits',
                amount REAL NOT NULL,
                balance_after REAL NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Game stats per user
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                plays INTEGER DEFAULT 0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                biggest_win REAL DEFAULT 0,
                last_played TEXT,
                UNIQUE(user_id, game),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Admin settings
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )

        # Lottery tickets
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                draw_id TEXT NOT NULL,
                numbers TEXT NOT NULL,
                purchased_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Lottery draws
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_id TEXT UNIQUE NOT NULL,
                draw_date TEXT,
                winning_numbers TEXT,
                jackpot_amount REAL DEFAULT 0,
                winners TEXT,
                payout_type TEXT,
                status TEXT DEFAULT 'pending',
                no_winner_streak INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Lottery jackpot tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_jackpot (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_amount REAL DEFAULT 10000.0,
                no_winner_months INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Initialize jackpot if not exists
        cursor.execute(
            "INSERT OR IGNORE INTO lottery_jackpot (id, current_amount) VALUES (1, 10000.0)"
        )

        # Lottery installments
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_installments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                draw_id TEXT NOT NULL,
                total_amount REAL NOT NULL,
                paid_amount REAL DEFAULT 0,
                per_payment REAL NOT NULL,
                payments_remaining INTEGER NOT NULL,
                next_payment_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Lottery coin flip requests for multiple winners
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lottery_coin_flips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_id TEXT NOT NULL,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                user1_agreed INTEGER DEFAULT 0,
                user2_agreed INTEGER DEFAULT 0,
                winner_id INTEGER,
                expires_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users(id),
                FOREIGN KEY (user2_id) REFERENCES users(id)
            )
        """
        )

        # Set default admin password if not exists
        cursor.execute("SELECT value FROM admin_settings WHERE key = 'admin_password'")
        if not cursor.fetchone():
            # Default password: "admin123" hashed
            default_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO admin_settings (key, value) VALUES ('admin_password', ?)",
                (default_hash,),
            )

        conn.commit()

        # Run migrations for schema upgrades
        self._migrate_schema()

    def _migrate_schema(self):
        """Handle schema migrations for existing databases."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check and add missing columns
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}

        if "password_hash" not in columns:
            logger.info("Migrating: Adding password_hash column")
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

        if "last_daily_claim" not in columns:
            logger.info("Migrating: Adding last_daily_claim column")
            cursor.execute("ALTER TABLE users ADD COLUMN last_daily_claim TEXT")

        if "last_daily_cash" not in columns:
            logger.info("Migrating: Adding last_daily_cash column")
            cursor.execute("ALTER TABLE users ADD COLUMN last_daily_cash TEXT")

        if "banned_until" not in columns:
            logger.info("Migrating: Adding banned_until column")
            cursor.execute("ALTER TABLE users ADD COLUMN banned_until TEXT")

        if "ban_reason" not in columns:
            logger.info("Migrating: Adding ban_reason column")
            cursor.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT")

        if "user_type" not in columns:
            logger.info("Migrating: Adding user_type column")
            cursor.execute("ALTER TABLE users ADD COLUMN user_type TEXT DEFAULT 'user'")

        # Ensure THE HOUSE user exists
        self._ensure_house_user(cursor)

        conn.commit()

    def _ensure_house_user(self, cursor):
        """Ensure THE HOUSE special user exists."""
        cursor.execute("SELECT id FROM users WHERE username = 'THE_HOUSE'")
        if not cursor.fetchone():
            logger.info("Creating THE HOUSE user")
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, cash, credits, user_type, is_admin)
                VALUES ('THE_HOUSE', NULL, 0, 0, 'house', 1)
            """
            )

    # ==================== User Authentication ====================

    def create_user(self, username: str, password: str = None) -> Dict:
        """Create a new user with username and optional password."""
        import bcrypt

        conn = self._get_connection()
        cursor = conn.cursor()

        # Sanitize and validate username
        username = self._sanitize_username(username)
        if not username:
            return {"success": False, "error": "Invalid username"}

        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return {"success": False, "error": "Username already taken"}

        # Hash password if provided
        password_hash = None
        if password:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users (username, password_hash, cash, credits, last_active)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                username,
                password_hash,
                settings.economy.starting_cash,
                settings.economy.starting_credits,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()

        logger.info(f"Created new user: {username}")

        return {
            "success": True,
            "user_id": cursor.lastrowid,
            "username": username,
            "cash": settings.economy.starting_cash,
            "credits": settings.economy.starting_credits,
        }

    def _sanitize_username(self, username: str) -> str:
        """Sanitize username - alphanumeric only, 3-20 chars."""
        import re

        if not username:
            return ""
        # Strip whitespace and limit to alphanumeric + underscore
        username = username.strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            return ""
        return username

    def login_user(self, username: str, password: str = None) -> Optional[Dict]:
        """Login existing user by username and password."""
        import bcrypt

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            return None

        user = dict(row)

        # Verify password if user has one set
        if user.get("password_hash"):
            if not password:
                return None  # Password required but not provided
            try:
                if not bcrypt.checkpw(
                    password.encode("utf-8"), user["password_hash"].encode("utf-8")
                ):
                    return None  # Wrong password
            except Exception:
                return None

        # Check if user is banned
        if user.get("banned_until"):
            try:
                ban_time = datetime.fromisoformat(user["banned_until"])
                if datetime.now() < ban_time:
                    # Still banned
                    return {
                        "banned": True,
                        "banned_until": user["banned_until"],
                        "ban_reason": user.get("ban_reason", "No reason specified"),
                    }
            except Exception:
                pass

        # Update last active
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE id = ?",
            (datetime.now().isoformat(), user["id"]),
        )
        conn.commit()

        return user

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

    # ==================== Admin Authentication ====================

    def verify_admin_password(self, password: str) -> bool:
        """Verify admin password using bcrypt against config.json."""
        import bcrypt
        from app.config import settings

        stored_hash = settings.security.admin_password_hash

        # Check if it's a bcrypt hash
        if stored_hash.startswith("$2"):
            try:
                return bcrypt.checkpw(
                    password.encode("utf-8"), stored_hash.encode("utf-8")
                )
            except Exception:
                return False
        else:
            # Plain text comparison (shouldn't happen after first run)
            return password == stored_hash

    def set_admin_password(self, new_password: str):
        """Set new admin password in config.json."""
        import bcrypt
        import json

        config_path = Path("config.json")
        with open(config_path, "r") as f:
            config = json.load(f)

        # Hash with bcrypt
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )
        config["security"]["admin_password_hash"] = hashed

        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

        # Reload settings
        from importlib import reload
        import app.config

        reload(app.config)

    # ==================== Balance Operations ====================

    def get_balance(self, user_id: int) -> Dict:
        """Get user's current balance."""
        user = self.get_user_by_id(user_id)
        if not user:
            return {"cash": 0, "credits": 0}
        return {"cash": user["cash"], "credits": user["credits"]}

    def update_balance(
        self, user_id: int, cash_delta: float = 0, credits_delta: float = 0
    ) -> Dict:
        """Update user balance by delta amounts."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users 
            SET cash = cash + ?, credits = credits + ?, last_active = ?
            WHERE id = ?
        """,
            (cash_delta, credits_delta, datetime.now().isoformat(), user_id),
        )
        conn.commit()

        return self.get_balance(user_id)

    def set_balance(
        self, user_id: int, cash: float = None, credits: float = None
    ) -> Dict:
        """Set user balance to specific values."""
        conn = self._get_connection()
        cursor = conn.cursor()

        current = self.get_balance(user_id)
        new_cash = cash if cash is not None else current["cash"]
        new_credits = credits if credits is not None else current["credits"]

        cursor.execute(
            """
            UPDATE users SET cash = ?, credits = ? WHERE id = ?
        """,
            (new_cash, new_credits, user_id),
        )
        conn.commit()

        return self.get_balance(user_id)

    # ==================== Daily Bonus ====================

    def claim_daily_bonus(self, user_id: int) -> Dict:
        """
        Claim daily bonus credits. Returns success/error with details.
        Cooldown and amount are configurable in config.json.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT last_daily_claim, credits FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "User not found"}

        last_claim = row["last_daily_claim"]
        cooldown_hours = settings.economy.daily_bonus_cooldown_hours
        bonus_amount = settings.economy.daily_bonus_amount

        # Check cooldown
        if last_claim:
            try:
                last_time = datetime.fromisoformat(last_claim)
                time_since = (datetime.now() - last_time).total_seconds()
                cooldown_seconds = cooldown_hours * 3600

                if time_since < cooldown_seconds:
                    remaining = cooldown_seconds - time_since
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    return {
                        "success": False,
                        "error": f"Daily bonus already claimed. Come back in {hours}h {minutes}m",
                        "remaining_seconds": int(remaining),
                    }
            except Exception as e:
                logger.warning(f"Error parsing last_daily_claim: {e}")

        # Grant bonus
        new_credits = row["credits"] + bonus_amount
        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE users SET credits = ?, last_daily_claim = ?, last_active = ?
            WHERE id = ?
        """,
            (new_credits, now, now, user_id),
        )
        conn.commit()

        # Log transaction
        self.log_transaction(
            user_id,
            "daily_bonus",
            bonus_amount,
            new_credits,
            currency="credits",
            details="Daily bonus claimed",
        )

        logger.info(f"User {user_id} claimed daily bonus: {bonus_amount} credits")

        return {
            "success": True,
            "amount": bonus_amount,
            "new_balance": new_credits,
            "next_claim_hours": cooldown_hours,
        }

    def claim_daily_cash(self, user_id: int) -> Dict:
        """
        Claim daily cash bonus. Separate from credits daily bonus.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT last_daily_cash, cash FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "User not found"}

        last_claim = row["last_daily_cash"]
        cooldown_hours = settings.economy.daily_cash_cooldown_hours
        bonus_amount = settings.economy.daily_cash_amount

        # Check cooldown
        if last_claim:
            try:
                last_time = datetime.fromisoformat(last_claim)
                time_since = (datetime.now() - last_time).total_seconds()
                cooldown_seconds = cooldown_hours * 3600

                if time_since < cooldown_seconds:
                    remaining = cooldown_seconds - time_since
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    return {
                        "success": False,
                        "error": f"Daily cash already claimed. Come back in {hours}h {minutes}m",
                        "remaining_seconds": int(remaining),
                    }
            except Exception as e:
                logger.warning(f"Error parsing last_daily_cash: {e}")

        # Grant cash bonus
        new_cash = row["cash"] + bonus_amount
        now = datetime.now().isoformat()

        cursor.execute(
            """
            UPDATE users SET cash = ?, last_daily_cash = ?, last_active = ?
            WHERE id = ?
        """,
            (new_cash, now, now, user_id),
        )
        conn.commit()

        # Log transaction
        self.log_transaction(
            user_id,
            "daily_cash",
            bonus_amount,
            new_cash,
            currency="cash",
            details="Daily cash bonus claimed",
        )

        logger.info(f"User {user_id} claimed daily cash: {bonus_amount}")

        return {
            "success": True,
            "amount": bonus_amount,
            "new_balance": new_cash,
            "currency": "cash",
            "next_claim_hours": cooldown_hours,
        }

    # ==================== House Balance ====================

    def add_house_cut(self, bet_amount: float, game: str = None) -> float:
        """
        Add house cut from a bet to THE HOUSE user's balance.
        Returns the cut amount.
        """
        cut_percent = settings.economy.house_cut_percent
        cut_amount = bet_amount * (cut_percent / 100)

        if cut_amount <= 0:
            return 0

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users SET credits = credits + ? WHERE username = 'THE_HOUSE'
        """,
            (cut_amount,),
        )
        conn.commit()

        # Log transaction for house
        cursor.execute("SELECT id, credits FROM users WHERE username = 'THE_HOUSE'")
        house = cursor.fetchone()
        if house:
            self.log_transaction(
                house["id"],
                "house_cut",
                cut_amount,
                house["credits"],
                game=game,
                details=f"{cut_percent}% cut from bet",
            )

        return cut_amount

    def get_house_balance(self) -> Dict:
        """Get THE HOUSE balance."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT cash, credits FROM users WHERE username = 'THE_HOUSE'")
        row = cursor.fetchone()

        if row:
            return {"cash": row["cash"], "credits": row["credits"]}
        return {"cash": 0, "credits": 0}

    def get_house_user(self) -> Optional[Dict]:
        """Get THE HOUSE user data."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = 'THE_HOUSE'")
        row = cursor.fetchone()
        return dict(row) if row else None

    # ==================== Conversion Tracking ====================

    def record_conversion(self, user_id: int, amount: float):
        """Record a currency conversion for rate adjustment."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users 
            SET total_converted = total_converted + ?, last_conversion_time = ?
            WHERE id = ?
        """,
            (abs(amount), datetime.now().isoformat(), user_id),
        )
        conn.commit()

    def get_conversion_penalty(self, user_id: int) -> float:
        """Get rate penalty based on recent conversions (0-15% penalty)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT total_converted, last_conversion_time FROM users WHERE id = ?
        """,
            (user_id,),
        )
        row = cursor.fetchone()

        if not row or not row["last_conversion_time"]:
            return 0.0

        # Check if last conversion was within 5 minutes
        try:
            last_time = datetime.fromisoformat(row["last_conversion_time"])
            time_diff = (datetime.now() - last_time).total_seconds()

            if time_diff > 300:  # More than 5 minutes ago
                # Reset conversion tracking
                cursor.execute(
                    "UPDATE users SET total_converted = 0 WHERE id = ?", (user_id,)
                )
                conn.commit()
                return 0.0

            # Calculate penalty: 1% per 100 converted, max 15%
            total = row["total_converted"]
            penalty = min(0.15, total / 10000)  # 15% max at 1500+ converted
            return penalty

        except Exception:
            return 0.0

    # ==================== Game Stats ====================

    def record_game(self, user_id: int, game: str, bet: float, payout: float):
        """Record a game play."""
        conn = self._get_connection()
        cursor = conn.cursor()

        net = payout - bet
        is_win = payout > bet

        # Update user stats
        cursor.execute(
            """
            UPDATE users SET
                total_wagered = total_wagered + ?,
                total_won = total_won + CASE WHEN ? > 0 THEN ? ELSE 0 END,
                total_lost = total_lost + CASE WHEN ? < 0 THEN ABS(?) ELSE 0 END,
                games_played = games_played + 1,
                biggest_win = CASE WHEN ? > biggest_win THEN ? ELSE biggest_win END,
                last_active = ?
            WHERE id = ?
        """,
            (
                bet,
                net,
                net,
                net,
                net,
                payout if is_win else 0,
                payout if is_win else 0,
                datetime.now().isoformat(),
                user_id,
            ),
        )

        # Update game-specific stats
        cursor.execute(
            """
            INSERT INTO user_game_stats (user_id, game, plays, total_wagered, total_won, biggest_win, last_played)
            VALUES (?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(user_id, game) DO UPDATE SET
                plays = plays + 1,
                total_wagered = total_wagered + excluded.total_wagered,
                total_won = total_won + excluded.total_won,
                biggest_win = CASE WHEN excluded.biggest_win > biggest_win THEN excluded.biggest_win ELSE biggest_win END,
                last_played = excluded.last_played
        """,
            (
                user_id,
                game,
                bet,
                payout if is_win else 0,
                payout if is_win else 0,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()

    def log_transaction(
        self,
        user_id: int,
        tx_type: str,
        amount: float,
        balance_after: float,
        game: str = None,
        currency: str = "credits",
        details: str = None,
    ):
        """Log a transaction."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO transactions (user_id, type, game, currency, amount, balance_after, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (user_id, tx_type, game, currency, amount, balance_after, details),
        )
        conn.commit()

    def get_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get recent transactions."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM transactions WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
        """,
            (user_id, limit),
        )

        return [dict(row) for row in cursor.fetchall()]

    # ==================== Admin Functions ====================

    def get_all_users(self, limit: int = 100) -> List[Dict]:
        """Get all users."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users ORDER BY last_active DESC LIMIT ?
        """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def reset_user(self, user_id: int) -> Dict:
        """Reset user to default balance."""
        from app.config import settings

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users SET 
                cash = ?, credits = ?,
                total_wagered = 0, total_won = 0, total_lost = 0,
                games_played = 0, biggest_win = 0, total_converted = 0
            WHERE id = ?
        """,
            (
                settings.economy.starting_cash,
                settings.economy.starting_credits,
                user_id,
            ),
        )

        # Clear their transactions
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_game_stats WHERE user_id = ?", (user_id,))

        conn.commit()
        return {"success": True, "user_id": user_id}

    def delete_user(self, user_id: int) -> Dict:
        """Delete a user completely - DEPRECATED, use ban_user instead."""
        return self.ban_user(
            user_id, hours=8760, reason="Account deleted"
        )  # 1 year ban

    def ban_user(
        self, user_id: int, hours: int = 24, reason: str = "Banned by admin"
    ) -> Dict:
        """Ban a user for a specified duration."""
        conn = self._get_connection()
        cursor = conn.cursor()

        banned_until = (datetime.now() + timedelta(hours=hours)).isoformat()

        cursor.execute(
            """
            UPDATE users SET banned_until = ?, ban_reason = ? WHERE id = ?
        """,
            (banned_until, reason, user_id),
        )
        conn.commit()

        logger.info(f"User {user_id} banned until {banned_until}: {reason}")
        return {"success": True, "banned_until": banned_until, "reason": reason}

    def unban_user(self, user_id: int) -> Dict:
        """Remove ban from a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET banned_until = NULL, ban_reason = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()

        logger.info(f"User {user_id} unbanned")
        return {"success": True}

    def get_stats(self) -> Dict:
        """Get platform statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                COUNT(*) as user_count,
                SUM(cash) as total_cash,
                SUM(credits) as total_credits,
                SUM(total_wagered) as platform_wagered,
                SUM(games_played) as total_games
            FROM users WHERE is_admin = 0
        """
        )
        user_stats = dict(cursor.fetchone())

        cursor.execute("SELECT COUNT(*) as tx_count FROM transactions")
        tx_stats = dict(cursor.fetchone())

        return {"users": user_stats, "transactions": tx_stats}

    def clear_all_data(self):
        """Clear all non-admin data."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM user_game_stats")
        cursor.execute("DELETE FROM users WHERE is_admin = 0")
        conn.commit()

        return {"status": "cleared"}

    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top players by various metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Top by total winnings
        cursor.execute(
            """
            SELECT id, username, total_won, total_wagered, biggest_win, games_played
            FROM users WHERE is_admin = 0
            ORDER BY total_won DESC LIMIT ?
        """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_game_breakdown(self) -> List[Dict]:
        """Get statistics per game."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT game, 
                SUM(plays) as total_plays,
                SUM(total_wagered) as total_wagered,
                SUM(total_won) as total_won,
                MAX(biggest_win) as biggest_win,
                COUNT(DISTINCT user_id) as unique_players
            FROM user_game_stats
            GROUP BY game
            ORDER BY total_plays DESC
        """
        )

        return [dict(row) for row in cursor.fetchall()]

    def get_user_game_stats(self, user_id: int) -> List[Dict]:
        """Get game stats for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT game, plays, total_wagered, total_won, biggest_win, last_played
            FROM user_game_stats WHERE user_id = ?
            ORDER BY plays DESC
        """,
            (user_id,),
        )

        return [dict(row) for row in cursor.fetchall()]

    # ==================== Lottery Functions ====================

    def get_lottery_jackpot(self) -> Dict:
        """Get current lottery jackpot info."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM lottery_jackpot WHERE id = 1")
        row = cursor.fetchone()

        if row:
            return {
                "current_amount": row["current_amount"],
                "no_winner_months": row["no_winner_months"],
                "last_updated": row["last_updated"],
            }
        return {"current_amount": 10000.0, "no_winner_months": 0, "last_updated": None}

    def update_lottery_jackpot(
        self, amount: float = None, delta: float = None, no_winner_months: int = None
    ) -> Dict:
        """Update lottery jackpot amount."""
        conn = self._get_connection()
        cursor = conn.cursor()

        current = self.get_lottery_jackpot()

        if delta is not None:
            new_amount = current["current_amount"] + delta
        elif amount is not None:
            new_amount = amount
        else:
            new_amount = current["current_amount"]

        new_months = (
            no_winner_months
            if no_winner_months is not None
            else current["no_winner_months"]
        )

        cursor.execute(
            """
            UPDATE lottery_jackpot 
            SET current_amount = ?, no_winner_months = ?, last_updated = ?
            WHERE id = 1
        """,
            (new_amount, new_months, datetime.now().isoformat()),
        )
        conn.commit()

        return self.get_lottery_jackpot()

    def buy_lottery_ticket(
        self, user_id: int, numbers: List[int], draw_id: str
    ) -> Dict:
        """
        Purchase a lottery ticket.

        Args:
            user_id: User buying the ticket
            numbers: List of chosen numbers (as JSON)
            draw_id: Draw identifier (YYYY-MM format)

        Returns:
            Dict with success status and ticket info
        """
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        # Store numbers as JSON
        numbers_json = json.dumps(sorted(numbers))

        cursor.execute(
            """
            INSERT INTO lottery_tickets (user_id, draw_id, numbers, purchased_at)
            VALUES (?, ?, ?, ?)
        """,
            (user_id, draw_id, numbers_json, datetime.now().isoformat()),
        )
        conn.commit()

        ticket_id = cursor.lastrowid

        logger.info(
            f"User {user_id} bought lottery ticket #{ticket_id} for draw {draw_id}"
        )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "numbers": sorted(numbers),
            "draw_id": draw_id,
        }

    def get_user_lottery_tickets(self, user_id: int, draw_id: str = None) -> List[Dict]:
        """Get user's lottery tickets, optionally filtered by draw."""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        if draw_id:
            cursor.execute(
                """
                SELECT * FROM lottery_tickets WHERE user_id = ? AND draw_id = ?
                ORDER BY purchased_at DESC
            """,
                (user_id, draw_id),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM lottery_tickets WHERE user_id = ?
                ORDER BY purchased_at DESC LIMIT 100
            """,
                (user_id,),
            )

        tickets = []
        for row in cursor.fetchall():
            ticket = dict(row)
            ticket["numbers"] = json.loads(ticket["numbers"])
            tickets.append(ticket)

        return tickets

    def get_user_ticket_count(self, user_id: int, draw_id: str) -> int:
        """Get number of tickets a user has for a specific draw."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) as count FROM lottery_tickets 
            WHERE user_id = ? AND draw_id = ?
        """,
            (user_id, draw_id),
        )

        return cursor.fetchone()["count"]

    def get_all_tickets_for_draw(self, draw_id: str) -> List[Dict]:
        """Get all tickets for a specific draw."""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT lt.*, u.username 
            FROM lottery_tickets lt
            JOIN users u ON lt.user_id = u.id
            WHERE lt.draw_id = ?
        """,
            (draw_id,),
        )

        tickets = []
        for row in cursor.fetchall():
            ticket = dict(row)
            ticket["numbers"] = json.loads(ticket["numbers"])
            tickets.append(ticket)

        return tickets

    def create_lottery_draw(self, draw_id: str) -> Dict:
        """Create a new lottery draw record."""
        conn = self._get_connection()
        cursor = conn.cursor()

        jackpot = self.get_lottery_jackpot()

        cursor.execute(
            """
            INSERT OR IGNORE INTO lottery_draws (draw_id, jackpot_amount, status)
            VALUES (?, ?, 'pending')
        """,
            (draw_id, jackpot["current_amount"]),
        )
        conn.commit()

        return {"draw_id": draw_id, "jackpot": jackpot["current_amount"]}

    def record_lottery_draw(
        self,
        draw_id: str,
        winning_numbers: List[int],
        winners: List[Dict],
        jackpot_amount: float,
        no_winner_streak: int = 0,
    ) -> Dict:
        """Record completed lottery draw results."""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE lottery_draws
            SET draw_date = ?, winning_numbers = ?, winners = ?, 
                jackpot_amount = ?, status = 'completed', no_winner_streak = ?
            WHERE draw_id = ?
        """,
            (
                datetime.now().isoformat(),
                json.dumps(winning_numbers),
                json.dumps(winners),
                jackpot_amount,
                no_winner_streak,
                draw_id,
            ),
        )
        conn.commit()

        return {"success": True, "draw_id": draw_id}

    def get_lottery_draw(self, draw_id: str) -> Optional[Dict]:
        """Get lottery draw info."""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM lottery_draws WHERE draw_id = ?", (draw_id,))
        row = cursor.fetchone()

        if not row:
            return None

        draw = dict(row)
        if draw["winning_numbers"]:
            draw["winning_numbers"] = json.loads(draw["winning_numbers"])
        if draw["winners"]:
            draw["winners"] = json.loads(draw["winners"])

        return draw

    def get_lottery_history(self, limit: int = 12) -> List[Dict]:
        """Get past lottery draws."""
        import json

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM lottery_draws 
            WHERE status = 'completed'
            ORDER BY draw_date DESC LIMIT ?
        """,
            (limit,),
        )

        draws = []
        for row in cursor.fetchall():
            draw = dict(row)
            if draw["winning_numbers"]:
                draw["winning_numbers"] = json.loads(draw["winning_numbers"])
            if draw["winners"]:
                draw["winners"] = json.loads(draw["winners"])
            draws.append(draw)

        return draws

    def create_lottery_installment(
        self, user_id: int, draw_id: str, total_amount: float, num_payments: int
    ) -> Dict:
        """Create installment payment plan for lottery winner."""
        conn = self._get_connection()
        cursor = conn.cursor()

        per_payment = total_amount / num_payments

        # Calculate next payment date (next Mon, Wed, or Fri at noon)
        now = datetime.now()
        days_ahead = {0: 0, 1: 1, 2: 0, 3: 1, 4: 0, 5: 2, 6: 1}  # Map to next M/W/F
        next_day = (now.weekday() + days_ahead.get(now.weekday(), 0)) % 7
        if next_day <= now.weekday():
            next_day += 7
        next_payment = now + timedelta(days=next_day - now.weekday())
        next_payment = next_payment.replace(hour=12, minute=0, second=0, microsecond=0)

        cursor.execute(
            """
            INSERT INTO lottery_installments 
            (user_id, draw_id, total_amount, per_payment, payments_remaining, next_payment_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                user_id,
                draw_id,
                total_amount,
                per_payment,
                num_payments,
                next_payment.isoformat(),
            ),
        )
        conn.commit()

        return {
            "success": True,
            "installment_id": cursor.lastrowid,
            "total_amount": total_amount,
            "per_payment": round(per_payment, 2),
            "payments_remaining": num_payments,
            "next_payment_date": next_payment.isoformat(),
        }

    def get_pending_installments(self) -> List[Dict]:
        """Get all installments due for payment."""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute(
            """
            SELECT li.*, u.username 
            FROM lottery_installments li
            JOIN users u ON li.user_id = u.id
            WHERE li.payments_remaining > 0 AND li.next_payment_date <= ?
        """,
            (now,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def process_installment_payment(self, installment_id: int) -> Dict:
        """Process a single installment payment."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM lottery_installments WHERE id = ?", (installment_id,)
        )
        row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "Installment not found"}

        installment = dict(row)

        if installment["payments_remaining"] <= 0:
            return {"success": False, "error": "No payments remaining"}

        # Pay the user
        self.update_balance(
            installment["user_id"], cash_delta=installment["per_payment"]
        )

        # Update installment record
        new_paid = installment["paid_amount"] + installment["per_payment"]
        new_remaining = installment["payments_remaining"] - 1

        # Calculate next payment date
        now = datetime.now()
        days_ahead = {0: 2, 1: 1, 2: 2, 3: 1, 4: 3, 5: 2, 6: 1}  # Days to next M/W/F
        next_payment = now + timedelta(days=days_ahead.get(now.weekday(), 1))
        next_payment = next_payment.replace(hour=12, minute=0, second=0, microsecond=0)

        cursor.execute(
            """
            UPDATE lottery_installments
            SET paid_amount = ?, payments_remaining = ?, next_payment_date = ?
            WHERE id = ?
        """,
            (
                new_paid,
                new_remaining,
                next_payment.isoformat() if new_remaining > 0 else None,
                installment_id,
            ),
        )
        conn.commit()

        # Log transaction
        self.log_transaction(
            installment["user_id"],
            "lottery_installment",
            installment["per_payment"],
            self.get_balance(installment["user_id"])["cash"],
            game="lottery",
            currency="cash",
            details=f"Installment payment {installment['payments_remaining'] - new_remaining} of {installment['payments_remaining']}",
        )

        logger.info(
            f"Processed lottery installment #{installment_id} for user {installment['user_id']}: ${installment['per_payment']}"
        )

        return {
            "success": True,
            "amount_paid": installment["per_payment"],
            "payments_remaining": new_remaining,
            "user_id": installment["user_id"],
        }

    def get_user_installments(self, user_id: int) -> List[Dict]:
        """Get user's lottery installment plans."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM lottery_installments WHERE user_id = ?
            ORDER BY created_at DESC
        """,
            (user_id,),
        )

        return [dict(row) for row in cursor.fetchall()]

    def create_coin_flip_request(
        self, draw_id: str, user1_id: int, user2_id: int, hours_to_agree: int = 24
    ) -> Dict:
        """Create a coin flip request for multiple lottery winners."""
        conn = self._get_connection()
        cursor = conn.cursor()

        expires_at = (datetime.now() + timedelta(hours=hours_to_agree)).isoformat()

        cursor.execute(
            """
            INSERT INTO lottery_coin_flips (draw_id, user1_id, user2_id, expires_at)
            VALUES (?, ?, ?, ?)
        """,
            (draw_id, user1_id, user2_id, expires_at),
        )
        conn.commit()

        return {
            "request_id": cursor.lastrowid,
            "draw_id": draw_id,
            "user1_id": user1_id,
            "user2_id": user2_id,
            "expires_at": expires_at,
        }

    def respond_to_coin_flip(self, request_id: int, user_id: int, agreed: bool) -> Dict:
        """User responds to coin flip request."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM lottery_coin_flips WHERE id = ?", (request_id,))
        row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "Request not found"}

        request = dict(row)

        if request["status"] != "pending":
            return {"success": False, "error": "Request already resolved"}

        # Check if expired
        if datetime.now() > datetime.fromisoformat(request["expires_at"]):
            cursor.execute(
                "UPDATE lottery_coin_flips SET status = 'expired' WHERE id = ?",
                (request_id,),
            )
            conn.commit()
            return {"success": False, "error": "Request expired"}

        # Update agreement
        if user_id == request["user1_id"]:
            cursor.execute(
                "UPDATE lottery_coin_flips SET user1_agreed = ? WHERE id = ?",
                (1 if agreed else -1, request_id),
            )
        elif user_id == request["user2_id"]:
            cursor.execute(
                "UPDATE lottery_coin_flips SET user2_agreed = ? WHERE id = ?",
                (1 if agreed else -1, request_id),
            )
        else:
            return {"success": False, "error": "User not part of this request"}

        conn.commit()

        # Check if both have responded
        cursor.execute("SELECT * FROM lottery_coin_flips WHERE id = ?", (request_id,))
        updated = dict(cursor.fetchone())

        if updated["user1_agreed"] != 0 and updated["user2_agreed"] != 0:
            # Both responded
            if updated["user1_agreed"] == 1 and updated["user2_agreed"] == 1:
                # Both agreed - execute coin flip
                from app.core.rng import rng

                winner_id = (
                    updated["user1_id"]
                    if rng.random_float() < 0.5
                    else updated["user2_id"]
                )
                cursor.execute(
                    """
                    UPDATE lottery_coin_flips SET status = 'completed', winner_id = ? WHERE id = ?
                """,
                    (winner_id, request_id),
                )
                conn.commit()

                logger.info(
                    f"Coin flip #{request_id} executed. Winner: user {winner_id}"
                )
                return {"success": True, "status": "completed", "winner_id": winner_id}
            else:
                # Someone declined - split the prize
                cursor.execute(
                    "UPDATE lottery_coin_flips SET status = 'declined' WHERE id = ?",
                    (request_id,),
                )
                conn.commit()
                return {
                    "success": True,
                    "status": "declined",
                    "message": "Prize will be split 50/50",
                }

        return {
            "success": True,
            "status": "pending",
            "message": "Waiting for other user",
        }

    def get_coin_flip_status(self, user_id: int) -> Optional[Dict]:
        """Get pending coin flip request for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM lottery_coin_flips 
            WHERE (user1_id = ? OR user2_id = ?) AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """,
            (user_id, user_id),
        )

        row = cursor.fetchone()
        return dict(row) if row else None


# Singleton instance
db = Database()
