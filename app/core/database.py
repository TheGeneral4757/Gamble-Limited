"""
Database module for persistent storage.
Uses SQLite for user balances, transaction history, and game statistics.
Enhanced with proper user profiles and better data management.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import threading
import json

# Database file location
DB_PATH = Path("data/casino.db")

class Database:
    """Thread-safe SQLite database wrapper with enhanced user management."""
    
    _local = threading.local()
    
    def __init__(self):
        # Ensure data directory exists
        DB_PATH.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table with enhanced profile data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                display_name TEXT,
                cash REAL DEFAULT 1000.0,
                credits REAL DEFAULT 500.0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                total_lost REAL DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                biggest_win REAL DEFAULT 0,
                favorite_game TEXT,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table with more details
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                game TEXT,
                currency TEXT DEFAULT 'credits',
                amount REAL NOT NULL,
                balance_before REAL,
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
                user_id TEXT NOT NULL,
                game TEXT NOT NULL,
                plays INTEGER DEFAULT 0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                biggest_win REAL DEFAULT 0,
                biggest_multiplier REAL DEFAULT 0,
                last_played TEXT,
                UNIQUE(user_id, game),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Global stats table for analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_stats (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sessions table for better tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
    
    # ==================== User Management ====================
    
    def get_or_create_user(self, user_id: str, username: str = None) -> Dict:
        """Get user by ID or create with default balance."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            # Update last active
            cursor.execute("UPDATE users SET last_active = ? WHERE id = ?", 
                          (datetime.now().isoformat(), user_id))
            conn.commit()
            return dict(row)
        
        # Create new user with default balance
        from app.config import settings
        display_name = username or f"Player_{user_id[:6]}"
        
        cursor.execute("""
            INSERT INTO users (id, username, display_name, cash, credits) 
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, display_name, 
              settings.economy.starting_cash, settings.economy.starting_credits))
        conn.commit()
        
        return {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "cash": settings.economy.starting_cash,
            "credits": settings.economy.starting_credits,
            "total_wagered": 0,
            "total_won": 0,
            "total_lost": 0,
            "games_played": 0,
        }
    
    def get_balance(self, user_id: str) -> Dict:
        """Get user's current balance."""
        user = self.get_or_create_user(user_id)
        return {"cash": user["cash"], "credits": user["credits"]}
    
    def update_balance(self, user_id: str, cash_delta: float = 0, credits_delta: float = 0) -> Dict:
        """Update user balance by delta amounts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Ensure user exists
        self.get_or_create_user(user_id)
        
        cursor.execute("""
            UPDATE users 
            SET cash = cash + ?, credits = credits + ?, 
                updated_at = ?, last_active = ?
            WHERE id = ?
        """, (cash_delta, credits_delta, datetime.now().isoformat(), 
              datetime.now().isoformat(), user_id))
        
        conn.commit()
        return self.get_balance(user_id)
    
    def set_balance(self, user_id: str, cash: float = None, credits: float = None) -> Dict:
        """Set user balance to specific values."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Ensure user exists
        current = self.get_or_create_user(user_id)
        
        new_cash = cash if cash is not None else current["cash"]
        new_credits = credits if credits is not None else current["credits"]
        
        cursor.execute("""
            UPDATE users 
            SET cash = ?, credits = ?, updated_at = ?
            WHERE id = ?
        """, (new_cash, new_credits, datetime.now().isoformat(), user_id))
        
        conn.commit()
        return self.get_balance(user_id)
    
    def update_user_profile(self, user_id: str, **kwargs) -> Dict:
        """Update user profile fields."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['username', 'display_name', 'favorite_game']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if updates:
            values.append(datetime.now().isoformat())
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        return self.get_or_create_user(user_id)
    
    # ==================== Game Stats ====================
    
    def record_game(self, user_id: str, game: str, bet: float, payout: float, 
                    multiplier: float = 0, details: str = None):
        """Record a game play with stats update."""
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
                updated_at = ?,
                last_active = ?
            WHERE id = ?
        """, (bet, net, net, net, net, payout if is_win else 0, payout if is_win else 0,
              datetime.now().isoformat(), datetime.now().isoformat(), user_id))
        
        # Update game-specific stats
        cursor.execute("""
            INSERT INTO user_game_stats (user_id, game, plays, total_wagered, total_won, biggest_win, biggest_multiplier, last_played)
            VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, game) DO UPDATE SET
                plays = plays + 1,
                total_wagered = total_wagered + excluded.total_wagered,
                total_won = total_won + excluded.total_won,
                biggest_win = CASE WHEN excluded.biggest_win > biggest_win THEN excluded.biggest_win ELSE biggest_win END,
                biggest_multiplier = CASE WHEN excluded.biggest_multiplier > biggest_multiplier THEN excluded.biggest_multiplier ELSE biggest_multiplier END,
                last_played = excluded.last_played
        """, (user_id, game, bet, payout if is_win else 0, 
              payout if is_win else 0, multiplier, datetime.now().isoformat()))
        
        conn.commit()
    
    def get_user_game_stats(self, user_id: str) -> List[Dict]:
        """Get per-game statistics for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_game_stats WHERE user_id = ? ORDER BY plays DESC
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Transactions ====================
    
    def log_transaction(self, user_id: str, tx_type: str, amount: float, 
                       balance_after: float, game: str = None, 
                       currency: str = "credits", details: str = None,
                       balance_before: float = None):
        """Log a transaction for history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transactions 
            (user_id, type, game, currency, amount, balance_before, balance_after, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, tx_type, game, currency, amount, balance_before, balance_after, details))
        
        conn.commit()
    
    def get_transactions(self, user_id: str, limit: int = 50, game: str = None) -> List[Dict]:
        """Get recent transactions for a user, optionally filtered by game."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if game:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? AND game = ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, game, limit))
        else:
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== Admin Functions ====================
    
    def clear_all_data(self):
        """Clear all user data (admin function)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM user_game_stats")
        cursor.execute("DELETE FROM sessions")
        cursor.execute("DELETE FROM users")
        
        conn.commit()
        return {"status": "cleared", "message": "All user data has been cleared"}
    
    def get_all_users(self, limit: int = 100, order_by: str = "last_active") -> List[Dict]:
        """Get all users (admin function)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        valid_orders = ["last_active", "total_wagered", "games_played", "created_at"]
        if order_by not in valid_orders:
            order_by = "last_active"
        
        cursor.execute(f"""
            SELECT * FROM users ORDER BY {order_by} DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_full_profile(self, user_id: str) -> Dict:
        """Get complete user profile with all stats."""
        user = self.get_or_create_user(user_id)
        game_stats = self.get_user_game_stats(user_id)
        recent_txs = self.get_transactions(user_id, limit=20)
        
        return {
            "profile": user,
            "game_stats": game_stats,
            "recent_transactions": recent_txs,
        }
    
    def ban_user(self, user_id: str, reason: str = None) -> Dict:
        """Ban a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET is_banned = 1, ban_reason = ?, updated_at = ?
            WHERE id = ?
        """, (reason, datetime.now().isoformat(), user_id))
        
        conn.commit()
        return {"success": True, "user_id": user_id, "banned": True}
    
    def unban_user(self, user_id: str) -> Dict:
        """Unban a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET is_banned = 0, ban_reason = NULL, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id))
        
        conn.commit()
        return {"success": True, "user_id": user_id, "banned": False}
    
    def get_stats(self) -> Dict:
        """Get aggregate statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as user_count, 
                SUM(cash) as total_cash, 
                SUM(credits) as total_credits,
                SUM(total_wagered) as platform_wagered,
                SUM(total_won) as platform_won,
                SUM(games_played) as total_games
            FROM users
        """)
        user_stats = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT COUNT(*) as tx_count, SUM(amount) as total_volume 
            FROM transactions
        """)
        tx_stats = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT game, SUM(plays) as total_plays, SUM(total_wagered) as wagered
            FROM user_game_stats 
            GROUP BY game 
            ORDER BY total_plays DESC
        """)
        game_popularity = [dict(row) for row in cursor.fetchall()]
        
        # Active users (last 24 hours - simplified)
        cursor.execute("""
            SELECT COUNT(*) as active_count FROM users 
            WHERE last_active > datetime('now', '-1 day')
        """)
        active = cursor.fetchone()
        
        return {
            "users": user_stats,
            "transactions": tx_stats,
            "game_popularity": game_popularity,
            "active_users_24h": active["active_count"] if active else 0,
        }
    
    def get_leaderboard(self, stat: str = "total_won", limit: int = 10) -> List[Dict]:
        """Get leaderboard for various stats."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        valid_stats = ["total_won", "total_wagered", "biggest_win", "games_played"]
        if stat not in valid_stats:
            stat = "total_won"
        
        cursor.execute(f"""
            SELECT id, display_name, {stat} as value
            FROM users 
            WHERE is_banned = 0
            ORDER BY {stat} DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


# Singleton instance
db = Database()
