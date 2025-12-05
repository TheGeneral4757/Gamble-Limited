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

# Database file location
DB_PATH = Path("data/casino.db")

class Database:
    """Thread-safe SQLite database wrapper with user authentication."""
    
    _local = threading.local()
    
    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
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
        """)
        
        # Game stats per user
        cursor.execute("""
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
        """)
        
        # Admin settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Set default admin password if not exists
        cursor.execute("SELECT value FROM admin_settings WHERE key = 'admin_password'")
        if not cursor.fetchone():
            # Default password: "admin123" hashed
            default_hash = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("INSERT INTO admin_settings (key, value) VALUES ('admin_password', ?)", (default_hash,))
        
        conn.commit()
    
    # ==================== User Authentication ====================
    
    def create_user(self, username: str) -> Dict:
        """Create a new user with username."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if username exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return {"success": False, "error": "Username already taken"}
        
        from app.config import settings
        cursor.execute("""
            INSERT INTO users (username, cash, credits, last_active)
            VALUES (?, ?, ?, ?)
        """, (username, settings.economy.starting_cash, settings.economy.starting_credits, 
              datetime.now().isoformat()))
        conn.commit()
        
        return {
            "success": True,
            "user_id": cursor.lastrowid,
            "username": username,
            "cash": settings.economy.starting_cash,
            "credits": settings.economy.starting_credits
        }
    
    def login_user(self, username: str) -> Optional[Dict]:
        """Login existing user by username."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Update last active
        cursor.execute("UPDATE users SET last_active = ? WHERE id = ?",
                      (datetime.now().isoformat(), row["id"]))
        conn.commit()
        
        return dict(row)
    
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
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception:
                return False
        else:
            # Plain text comparison (shouldn't happen after first run)
            return password == stored_hash
    
    def set_admin_password(self, new_password: str):
        """Set new admin password in config.json."""
        import bcrypt
        import json
        from pathlib import Path
        
        config_path = Path("config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Hash with bcrypt
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
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
    
    def update_balance(self, user_id: int, cash_delta: float = 0, credits_delta: float = 0) -> Dict:
        """Update user balance by delta amounts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET cash = cash + ?, credits = credits + ?, last_active = ?
            WHERE id = ?
        """, (cash_delta, credits_delta, datetime.now().isoformat(), user_id))
        conn.commit()
        
        return self.get_balance(user_id)
    
    def set_balance(self, user_id: int, cash: float = None, credits: float = None) -> Dict:
        """Set user balance to specific values."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        current = self.get_balance(user_id)
        new_cash = cash if cash is not None else current["cash"]
        new_credits = credits if credits is not None else current["credits"]
        
        cursor.execute("""
            UPDATE users SET cash = ?, credits = ? WHERE id = ?
        """, (new_cash, new_credits, user_id))
        conn.commit()
        
        return self.get_balance(user_id)
    
    # ==================== Conversion Tracking ====================
    
    def record_conversion(self, user_id: int, amount: float):
        """Record a currency conversion for rate adjustment."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET total_converted = total_converted + ?, last_conversion_time = ?
            WHERE id = ?
        """, (abs(amount), datetime.now().isoformat(), user_id))
        conn.commit()
    
    def get_conversion_penalty(self, user_id: int) -> float:
        """Get rate penalty based on recent conversions (0-15% penalty)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_converted, last_conversion_time FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if not row or not row["last_conversion_time"]:
            return 0.0
        
        # Check if last conversion was within 5 minutes
        try:
            last_time = datetime.fromisoformat(row["last_conversion_time"])
            time_diff = (datetime.now() - last_time).total_seconds()
            
            if time_diff > 300:  # More than 5 minutes ago
                # Reset conversion tracking
                cursor.execute("UPDATE users SET total_converted = 0 WHERE id = ?", (user_id,))
                conn.commit()
                return 0.0
            
            # Calculate penalty: 1% per 100 converted, max 15%
            total = row["total_converted"]
            penalty = min(0.15, total / 10000)  # 15% max at 1500+ converted
            return penalty
            
        except:
            return 0.0
    
    # ==================== Game Stats ====================
    
    def record_game(self, user_id: int, game: str, bet: float, payout: float):
        """Record a game play."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        net = payout - bet
        is_win = payout > bet
        
        # Update user stats
        cursor.execute("""
            UPDATE users SET
                total_wagered = total_wagered + ?,
                total_won = total_won + CASE WHEN ? > 0 THEN ? ELSE 0 END,
                total_lost = total_lost + CASE WHEN ? < 0 THEN ABS(?) ELSE 0 END,
                games_played = games_played + 1,
                biggest_win = CASE WHEN ? > biggest_win THEN ? ELSE biggest_win END,
                last_active = ?
            WHERE id = ?
        """, (bet, net, net, net, net, payout if is_win else 0, payout if is_win else 0,
              datetime.now().isoformat(), user_id))
        
        # Update game-specific stats
        cursor.execute("""
            INSERT INTO user_game_stats (user_id, game, plays, total_wagered, total_won, biggest_win, last_played)
            VALUES (?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(user_id, game) DO UPDATE SET
                plays = plays + 1,
                total_wagered = total_wagered + excluded.total_wagered,
                total_won = total_won + excluded.total_won,
                biggest_win = CASE WHEN excluded.biggest_win > biggest_win THEN excluded.biggest_win ELSE biggest_win END,
                last_played = excluded.last_played
        """, (user_id, game, bet, payout if is_win else 0, payout if is_win else 0, datetime.now().isoformat()))
        
        conn.commit()
    
    def log_transaction(self, user_id: int, tx_type: str, amount: float, 
                       balance_after: float, game: str = None, 
                       currency: str = "credits", details: str = None):
        """Log a transaction."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions (user_id, type, game, currency, amount, balance_after, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, tx_type, game, currency, amount, balance_after, details))
        conn.commit()
    
    def get_transactions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get recent transactions."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM transactions WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Admin Functions ====================
    
    def get_all_users(self, limit: int = 100) -> List[Dict]:
        """Get all users."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users ORDER BY last_active DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def reset_user(self, user_id: int) -> Dict:
        """Reset user to default balance."""
        from app.config import settings
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET 
                cash = ?, credits = ?,
                total_wagered = 0, total_won = 0, total_lost = 0,
                games_played = 0, biggest_win = 0, total_converted = 0
            WHERE id = ?
        """, (settings.economy.starting_cash, settings.economy.starting_credits, user_id))
        
        # Clear their transactions
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_game_stats WHERE user_id = ?", (user_id,))
        
        conn.commit()
        return {"success": True, "user_id": user_id}
    
    def delete_user(self, user_id: int) -> Dict:
        """Delete a user completely."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_game_stats WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        return {"success": True}
    
    def get_stats(self) -> Dict:
        """Get platform statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as user_count,
                SUM(cash) as total_cash,
                SUM(credits) as total_credits,
                SUM(total_wagered) as platform_wagered,
                SUM(games_played) as total_games
            FROM users WHERE is_admin = 0
        """)
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
        cursor.execute("""
            SELECT id, username, total_won, total_wagered, biggest_win, games_played
            FROM users WHERE is_admin = 0
            ORDER BY total_won DESC LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_game_breakdown(self) -> List[Dict]:
        """Get statistics per game."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT game, 
                SUM(plays) as total_plays,
                SUM(total_wagered) as total_wagered,
                SUM(total_won) as total_won,
                MAX(biggest_win) as biggest_win,
                COUNT(DISTINCT user_id) as unique_players
            FROM user_game_stats
            GROUP BY game
            ORDER BY total_plays DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_game_stats(self, user_id: int) -> List[Dict]:
        """Get game stats for a specific user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT game, plays, total_wagered, total_won, biggest_win, last_played
            FROM user_game_stats WHERE user_id = ?
            ORDER BY plays DESC
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]


# Singleton instance
db = Database()
