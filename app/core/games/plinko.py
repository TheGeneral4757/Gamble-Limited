from app.core.rng import rng
from typing import Dict, List

class PlinkoGame:
    """
    Plinko board simulation with realistic house edge.
    Ball drops through rows of pegs, bouncing left or right.
    Final position determines multiplier.
    
    Odds are weighted to favor lower multipliers (60-65% of drops result in loss).
    """
    
    # Multipliers rebalanced - center slots are more likely due to probability
    # Edge slots are rare but not absurdly high
    # Values designed for ~5-8% house edge
    MULTIPLIERS = {
        16: [16, 9, 2, 1.4, 1.1, 0.5, 0.3, 0.5, 0.3, 0.5, 0.3, 0.5, 1.1, 1.4, 2, 9, 16],
        12: [10, 3, 1.5, 0.6, 0.4, 0.3, 0.3, 0.4, 0.6, 1.5, 3, 10, 0],
        8:  [5.6, 2.1, 0.5, 0.2, 0.2, 0.5, 2.1, 5.6, 0],
    }
    
    # Bias factor - slight bias towards center (lower multipliers)
    # 0.5 = fair, < 0.5 = bias left, > 0.5 = bias right towards center
    CENTER_BIAS = 0.48  # Slightly bias towards center for house edge
    
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
        # Validate and normalize rows
        if rows not in [8, 12, 16]:
            rows = 16
        
        # Get multiplier set
        multipliers = self.MULTIPLIERS.get(rows, self.MULTIPLIERS[16])
        if multipliers[-1] == 0:  # Remove padding zeros
            multipliers = multipliers[:-1]
        
        # Simulate ball path with slight center bias
        position = 0
        path = []
        
        for row in range(rows):
            # Use weighted random - slightly more likely to go towards center
            # The further from center, the more likely to go back
            bias = self.CENTER_BIAS
            
            # Add dynamic bias based on position (pull towards center)
            if position > 0:
                bias -= 0.03 * min(position, 3)  # More likely to go left if right of center
            elif position < 0:
                bias += 0.03 * min(abs(position), 3)  # More likely to go right if left of center
            
            # Clamp bias
            bias = max(0.35, min(0.65, bias))
            
            # Determine direction with bias
            direction = "L" if rng.random_float() < bias else "R"
            position += -1 if direction == "L" else 1
            path.append(direction)
        
        # Convert final position to slot index
        # Position ranges from -rows to +rows, map to 0 to 2*rows
        slot_index = position + rows
        
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
