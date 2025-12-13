"""
Dice Roll game - Bet on the outcome of 2 dice.
Multiple bet types: exact sum, ranges, doubles.
Supports Gamble Friday bonuses.
"""

from app.core.rng import rng
from app.core.gamble_friday import gamble_friday
from app.config import settings
from typing import Dict


class DiceGame:
    """
    Dice roll betting game with multiple bet types.
    Roll 2 six-sided dice.
    """
    
    # Bet types and their payouts
    # Exact sum payouts based on probability
    SUM_PAYOUTS = {
        2: 36,   # 1/36 chance
        3: 18,   # 2/36 chance
        4: 12,   # 3/36 chance
        5: 9,    # 4/36 chance
        6: 7.2,  # 5/36 chance
        7: 6,    # 6/36 chance (most common)
        8: 7.2,  # 5/36 chance
        9: 9,    # 4/36 chance
        10: 12,  # 3/36 chance
        11: 18,  # 2/36 chance
        12: 36,  # 1/36 chance
    }
    
    # Range payouts
    RANGE_PAYOUTS = {
        "low": 2.5,    # 2-6 (15/36 = ~42%)
        "mid": 6,      # 7 only (6/36 = ~17%)
        "high": 2.5,   # 8-12 (15/36 = ~42%)
    }
    
    # Special bets
    SPECIAL_PAYOUTS = {
        "any_double": 5,       # Any double (6/36 = ~17%)
        "specific_double": 30, # Specific double (1/36)
    }
    
    def _get_config(self) -> dict:
        """Get game configuration from settings."""
        try:
            games_data = settings.games.model_dump() if hasattr(settings.games, "model_dump") else settings.games.dict()
            return games_data.get("dice", {})
        except Exception:
            return {}
    
    def _roll_dice(self) -> tuple:
        """Roll 2 six-sided dice."""
        die1 = rng.random_int(1, 6)
        die2 = rng.random_int(1, 6)
        return die1, die2
    
    def roll(self, bet_amount: float, bet_type: str, bet_value: str = "") -> Dict:
        """
        Roll the dice and resolve the bet.
        
        Args:
            bet_amount: Amount wagered
            bet_type: "sum", "range", "any_double", "specific_double"
            bet_value: The specific value for the bet (e.g., "7" for sum, "low" for range)
            
        Returns:
            Dict with dice results, win status, and payout
        """
        # Roll the dice
        die1, die2 = self._roll_dice()
        total = die1 + die2
        is_double = die1 == die2
        
        # Determine win and multiplier based on bet type
        win = False
        multiplier = 0
        
        bet_type = bet_type.lower().strip()
        bet_value = bet_value.lower().strip()
        
        if bet_type == "sum":
            try:
                target_sum = int(bet_value)
                if target_sum in self.SUM_PAYOUTS:
                    if total == target_sum:
                        win = True
                        multiplier = self.SUM_PAYOUTS[target_sum]
                else:
                    return {"error": f"Invalid sum bet: {target_sum}. Must be 2-12."}
            except ValueError:
                return {"error": f"Invalid sum value: {bet_value}"}
        
        elif bet_type == "range":
            if bet_value == "low":
                win = 2 <= total <= 6
            elif bet_value == "mid":
                win = total == 7
            elif bet_value == "high":
                win = 8 <= total <= 12
            else:
                return {"error": f"Invalid range: {bet_value}. Must be 'low', 'mid', or 'high'."}
            
            if win:
                multiplier = self.RANGE_PAYOUTS[bet_value]
        
        elif bet_type == "any_double":
            win = is_double
            if win:
                multiplier = self.SPECIAL_PAYOUTS["any_double"]
        
        elif bet_type == "specific_double":
            try:
                target = int(bet_value)
                if 1 <= target <= 6:
                    win = is_double and die1 == target
                    if win:
                        multiplier = self.SPECIAL_PAYOUTS["specific_double"]
                else:
                    return {"error": f"Invalid double value: {target}. Must be 1-6."}
            except ValueError:
                return {"error": f"Invalid double value: {bet_value}"}
        
        else:
            return {"error": f"Invalid bet type: {bet_type}"}
        
        # Calculate payout with Gamble Friday bonus
        friday_mult = gamble_friday.get_winnings_multiplier()
        base_payout = bet_amount * multiplier if win else 0
        payout = base_payout * friday_mult if win else 0
        
        return {
            "dice": [die1, die2],
            "total": total,
            "is_double": is_double,
            "bet_type": bet_type,
            "bet_value": bet_value,
            "win": win,
            "multiplier": multiplier if win else 0,
            "payout": round(payout, 2),
            "bet": bet_amount,
            "is_friday": gamble_friday.is_active(),
            "friday_bonus": friday_mult if gamble_friday.is_active() and win else 1.0,
        }


# Singleton instance
dice_game = DiceGame()
