from app.core.rng import rng
from typing import List, Dict, Tuple

class SlotsGame:
    """
    3-reel slot machine with weighted symbols and multiplier payouts.
    Odds are weighted heavily - most spins result in losses.
    House edge approximately 8-12%.
    """
    
    # Symbol definitions with weights (higher = more common)
    # Total weight: 100, distributed to favor lower-value symbols
    SYMBOLS = [
        ("🍒", 30),   # Cherry - most common, lowest payout
        ("🍋", 25),   # Lemon
        ("🍊", 18),   # Orange
        ("🍇", 12),   # Grape
        ("🔔", 8),    # Bell
        ("💎", 5),    # Diamond - rare
        ("7️⃣", 2),    # Seven - very rare, highest payout
    ]
    
    # Payout multipliers for 3 matching symbols (realistic casino odds)
    PAYOUTS_3X = {
        "🍒": 3,      # Common, low payout
        "🍋": 5,
        "🍊": 8,
        "🍇": 12,
        "🔔": 20,
        "💎": 40,
        "7️⃣": 77,     # Jackpot!
    }
    
    # Payout for 2 matching symbols (much smaller)
    PAYOUTS_2X = {
        "🍒": 1,      # Just returns bet
        "🍋": 1.5,
        "🍊": 2,
        "🍇": 2.5,
        "🔔": 4,
        "💎": 8,
        "7️⃣": 15,
    }
    
    def __init__(self):
        # Build weighted pool for selection
        self.symbol_pool = []
        for symbol, weight in self.SYMBOLS:
            self.symbol_pool.extend([symbol] * weight)
    
    def _spin_reel(self) -> str:
        """Spin a single reel and return the symbol."""
        index = rng.random_int(0, len(self.symbol_pool) - 1)
        return self.symbol_pool[index]
    
    def _calculate_payout(self, reels: List[str], bet: float) -> Tuple[float, float, str]:
        """
        Calculate payout based on reel results.
        Returns: (payout_amount, multiplier, win_type)
        """
        # Check for 3 of a kind (jackpot)
        if reels[0] == reels[1] == reels[2]:
            symbol = reels[0]
            multiplier = self.PAYOUTS_3X.get(symbol, 0)
            win_type = "jackpot" if symbol == "7️⃣" else "triple"
            return bet * multiplier, multiplier, win_type
        
        # Check for 2 of a kind - only first two or last two count
        # (not first and last - makes it harder to win)
        if reels[0] == reels[1]:
            multiplier = self.PAYOUTS_2X.get(reels[0], 0)
            return bet * multiplier, multiplier, "double"
        
        if reels[1] == reels[2]:
            multiplier = self.PAYOUTS_2X.get(reels[1], 0)
            return bet * multiplier, multiplier, "double"
        
        # No win - majority of spins end here
        return 0, 0, "lose"
    
    def spin(self, bet_amount: float) -> Dict:
        """
        Spin the slot machine.
        
        Args:
            bet_amount: Amount wagered
            
        Returns:
            Dict with reels, win status, payout, and multiplier
        """
        # Generate 3 reels
        reels = [self._spin_reel() for _ in range(3)]
        
        # Calculate payout
        payout, multiplier, win_type = self._calculate_payout(reels, bet_amount)
        
        return {
            "reels": reels,
            "win": payout > 0,
            "win_type": win_type,
            "payout": round(payout, 2),
            "multiplier": multiplier,
            "bet": bet_amount,
            "is_jackpot": win_type == "jackpot",
            "net": round(payout - bet_amount, 2),
        }


# Singleton instance
slots_game = SlotsGame()
