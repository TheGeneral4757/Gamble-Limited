from app.core.rng import rng
from app.core.odds import get_game_odds
from typing import Dict, List

class PlinkoGame:
    """
    Plinko board simulation with configurable odds.
    Ball drops through rows of pegs, bouncing left or right.
    Final position determines multiplier.
    
    Odds are loaded from ODDS-CHANGER.json for real-time adjustments.
    """
    
    # Default multipliers (used if config fails)
    DEFAULT_MULTIPLIERS = {
        16: [8, 4, 2, 1.5, 1, 0.5, 0.3, 0.5, 0.5, 0.3, 0.5, 1, 1.5, 2, 4, 8],
        12: [5, 2.5, 1.5, 0.7, 0.3, 0.2, 0.2, 0.3, 0.7, 1.5, 2.5, 5],
        8:  [3, 1.5, 0.5, 0.3, 0.3, 0.5, 1.5, 3],
    }
    
    DEFAULT_CENTER_BIAS = 0.40
    
    def _get_odds(self) -> tuple:
        """Get current odds from config file."""
        config = get_game_odds("plinko")
        
        center_bias = config.get("center_bias", self.DEFAULT_CENTER_BIAS)
        multipliers_config = config.get("multipliers", {})
        
        # Convert string keys to int
        multipliers = {}
        for rows, mults in multipliers_config.items():
            multipliers[int(rows)] = mults
        
        # Merge with defaults
        for rows, defaults in self.DEFAULT_MULTIPLIERS.items():
            if rows not in multipliers:
                multipliers[rows] = defaults
        
        return center_bias, multipliers
    
    def drop(self, bet_amount: float, rows: int = 16, risk: str = "medium") -> Dict:
        """
        Simulate a ball drop on the Plinko board.
        
        Args:
            bet_amount: Amount wagered
            rows: Number of peg rows (8, 12, or 16)
            risk: Risk level affects multiplier scaling
            
        Returns:
            Dict with path, final slot, multiplier, and payout
        """
        # Load current odds
        center_bias, all_multipliers = self._get_odds()
        
        # Validate and normalize rows
        if rows not in [8, 12, 16]:
            rows = 16
        
        # Get multiplier set
        multipliers = all_multipliers.get(rows, self.DEFAULT_MULTIPLIERS[16])
        
        # Simulate ball path with configurable center bias
        position = 0
        path = []
        
        for row in range(rows):
            # Use weighted random - adjust based on position
            bias = center_bias
            
            # Add dynamic bias based on position (pull towards center)
            if position > 0:
                bias -= 0.03 * min(position, 3)  # More likely to go left if right of center
            elif position < 0:
                bias += 0.03 * min(abs(position), 3)  # More likely to go right if left of center
            
            # Clamp bias
            bias = max(0.30, min(0.70, bias))
            
            # Determine direction with bias
            direction = "L" if rng.random_float() < bias else "R"
            position += -1 if direction == "L" else 1
            path.append(direction)
        
        # Convert final position to slot index
        # Position ranges from -rows to +rows, map to 0 to len(multipliers)
        center_slot = len(multipliers) // 2
        slot_index = center_slot + position
        
        # Clamp to valid range
        slot_index = max(0, min(slot_index, len(multipliers) - 1))
        
        multiplier = multipliers[slot_index]
        payout = bet_amount * multiplier
        
        # Determine if this is a "win" (got more than bet back)
        is_win = payout > bet_amount
        is_big_win = multiplier >= 3
        
        return {
            "path": path,
            "final_slot": slot_index,
            "multiplier": multiplier,
            "payout": round(payout, 2),
            "bet": bet_amount,
            "rows": rows,
            "win": is_win,
            "big_win": is_big_win,
            "net": round(payout - bet_amount, 2),
        }


# Singleton instance
plinko_game = PlinkoGame()
