"""
High/Low card game - Guess if the next card is higher or lower.
Build a streak for increasing multipliers, cash out anytime.
Supports Gamble Friday bonuses.
"""

from app.core.rng import rng
from app.core.gamble_friday import gamble_friday
from app.config import settings
from typing import Dict, Optional
import uuid
import time


class HighLowGame:
    """
    High/Low card guessing game with streak multipliers.
    Cash out anytime or lose on wrong guess.
    """
    
    # Default streak multipliers (index = streak count)
    DEFAULT_STREAK_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
    
    # Active games storage (game_id -> game state)
    _active_games: Dict[str, dict] = {}
    
    # Card values: 1-9 (1=1, 9=9)
    CARD_VALUES = list(range(1, 10))
    CARD_NAMES = {
        1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 
        8: "8", 9: "9"
    }
    
    def _get_config(self) -> dict:
        """Get game configuration from settings."""
        try:
            games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
            return games_data.get("highlow", {})
        except Exception:
            return {}
    
    def _get_streak_multipliers(self) -> list:
        """Get streak multipliers from config."""
        config = self._get_config()
        return config.get("streak_multipliers", self.DEFAULT_STREAK_MULTIPLIERS)
    
    def _draw_card(self) -> int:
        """Draw a random card (2-14)."""
        idx = rng.random_int(0, len(self.CARD_VALUES) - 1)
        return self.CARD_VALUES[idx]
    
    def _card_display(self, value: int) -> str:
        """Get display name for card value."""
        return self.CARD_NAMES.get(value, str(value))
    
    def _cleanup_old_games(self):
        """Remove games older than 1 hour."""
        current_time = time.time()
        expired = [gid for gid, g in self._active_games.items() 
                   if current_time - g.get("started", 0) > 3600]
        for gid in expired:
            del self._active_games[gid]
    
    def start(self, bet_amount: float, user_id: int) -> Dict:
        """
        Start a new High/Low game.
        
        Args:
            bet_amount: Initial bet amount
            user_id: Player's user ID
            
        Returns:
            Dict with game_id, current card, and potential multipliers
        """
        self._cleanup_old_games()
        
        game_id = str(uuid.uuid4())[:8]
        current_card = self._draw_card()
        
        game_state = {
            "user_id": user_id,
            "bet": bet_amount,
            "current_card": current_card,
            "streak": 0,
            "started": time.time(),
            "status": "active",
        }
        
        self._active_games[game_id] = game_state
        
        multipliers = self._get_streak_multipliers()
        
        return {
            "game_id": game_id,
            "current_card": current_card,
            "current_card_display": self._card_display(current_card),
            "streak": 0,
            "current_multiplier": multipliers[0] if multipliers else 1.0,
            "next_multiplier": multipliers[1] if len(multipliers) > 1 else multipliers[0],
            "can_cashout": False,  # Can't cash out on first card
            "bet": bet_amount,
            "potential_payout": round(bet_amount * multipliers[0], 2),
        }
    
    def guess(self, game_id: str, user_id: int, choice: str) -> Dict:
        """
        Make a guess (higher or lower).
        
        Args:
            game_id: Active game ID
            user_id: Player's user ID
            choice: "higher" or "lower"
            
        Returns:
            Dict with result, new card, streak, or game over info
        """
        if game_id not in self._active_games:
            return {"error": "Game not found or expired"}
        
        game = self._active_games[game_id]
        
        if game["user_id"] != user_id:
            return {"error": "This is not your game"}
        
        if game["status"] != "active":
            return {"error": "Game already ended"}
        
        choice = choice.lower().strip()
        if choice not in ["higher", "lower"]:
            return {"error": "Choice must be 'higher' or 'lower'"}
        
        old_card = game["current_card"]
        new_card = self._draw_card()
        
        # Determine if guess was correct
        # Tie goes to the house (loss)
        if choice == "higher":
            correct = new_card > old_card
        else:
            correct = new_card < old_card
        
        multipliers = self._get_streak_multipliers()
        
        if correct:
            # Streak continues
            game["streak"] += 1
            game["current_card"] = new_card
            
            streak_idx = min(game["streak"], len(multipliers) - 1)
            current_mult = multipliers[streak_idx]
            next_mult = multipliers[min(streak_idx + 1, len(multipliers) - 1)]
            
            # Apply Gamble Friday bonus to potential payout
            friday_mult = gamble_friday.get_winnings_multiplier()
            potential_payout = game["bet"] * current_mult * friday_mult
            
            return {
                "game_id": game_id,
                "correct": True,
                "old_card": old_card,
                "old_card_display": self._card_display(old_card),
                "new_card": new_card,
                "new_card_display": self._card_display(new_card),
                "choice": choice,
                "streak": game["streak"],
                "current_multiplier": current_mult,
                "next_multiplier": next_mult,
                "can_cashout": True,
                "potential_payout": round(potential_payout, 2),
                "status": "active",
                "is_friday": gamble_friday.is_active(),
            }
        else:
            # Wrong guess - game over, lose bet
            game["status"] = "lost"
            del self._active_games[game_id]
            
            return {
                "game_id": game_id,
                "correct": False,
                "old_card": old_card,
                "old_card_display": self._card_display(old_card),
                "new_card": new_card,
                "new_card_display": self._card_display(new_card),
                "choice": choice,
                "streak": game["streak"],
                "payout": 0,
                "status": "lost",
                "message": f"Wrong! The card was {self._card_display(new_card)}.",
            }
    
    def cashout(self, game_id: str, user_id: int) -> Dict:
        """
        Cash out current winnings.
        
        Args:
            game_id: Active game ID
            user_id: Player's user ID
            
        Returns:
            Dict with final payout
        """
        if game_id not in self._active_games:
            return {"error": "Game not found or expired"}
        
        game = self._active_games[game_id]
        
        if game["user_id"] != user_id:
            return {"error": "This is not your game"}
        
        if game["status"] != "active":
            return {"error": "Game already ended"}
        
        if game["streak"] == 0:
            return {"error": "Cannot cash out before first guess"}
        
        multipliers = self._get_streak_multipliers()
        streak_idx = min(game["streak"], len(multipliers) - 1)
        base_multiplier = multipliers[streak_idx]
        
        # Apply Gamble Friday bonus
        friday_mult = gamble_friday.get_winnings_multiplier()
        final_multiplier = base_multiplier * friday_mult
        payout = game["bet"] * final_multiplier
        
        # End game
        game["status"] = "cashed_out"
        del self._active_games[game_id]
        
        return {
            "game_id": game_id,
            "status": "cashed_out",
            "streak": game["streak"],
            "base_multiplier": base_multiplier,
            "friday_bonus": friday_mult if gamble_friday.is_active() else 1.0,
            "final_multiplier": final_multiplier,
            "payout": round(payout, 2),
            "bet": game["bet"],
            "is_friday": gamble_friday.is_active(),
        }
    
    def get_game_state(self, game_id: str, user_id: int) -> Optional[Dict]:
        """Get current state of an active game."""
        if game_id not in self._active_games:
            return None
        
        game = self._active_games[game_id]
        if game["user_id"] != user_id:
            return None
        
        multipliers = self._get_streak_multipliers()
        streak_idx = min(game["streak"], len(multipliers) - 1)
        
        return {
            "game_id": game_id,
            "current_card": game["current_card"],
            "current_card_display": self._card_display(game["current_card"]),
            "streak": game["streak"],
            "current_multiplier": multipliers[streak_idx],
            "status": game["status"],
            "bet": game["bet"],
        }


# Singleton instance
highlow_game = HighLowGame()
