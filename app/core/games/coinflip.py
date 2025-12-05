from app.core.rng import rng
from typing import Dict

class CoinflipGame:
    """
    Simple 50/50 coin flip with house edge.
    """
    
    # Payout multiplier (1.95x gives 2.5% house edge)
    PAYOUT_MULTIPLIER = 1.95
    
    def flip(self, bet_amount: float, choice: str) -> Dict:
        """
        Flip a coin and resolve the bet.
        
        Args:
            bet_amount: Amount wagered
            choice: Player's choice ("heads" or "tails")
            
        Returns:
            Dict with result, win status, and payout
        """
        # Normalize choice
        choice = choice.lower().strip()
        if choice not in ["heads", "tails"]:
            return {"error": f"Invalid choice: {choice}. Must be 'heads' or 'tails'."}
        
        # Flip the coin (50/50)
        result = "heads" if rng.random_float() < 0.5 else "tails"
        
        # Determine win
        win = choice == result
        payout = bet_amount * self.PAYOUT_MULTIPLIER if win else 0
        
        return {
            "result": result,
            "choice": choice,
            "win": win,
            "payout": round(payout, 2),
            "multiplier": self.PAYOUT_MULTIPLIER if win else 0,
            "bet": bet_amount,
        }


# Singleton instance
coinflip_game = CoinflipGame()
