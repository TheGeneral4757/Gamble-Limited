from app.core.rng import rng
from app.core.odds import get_game_odds
from typing import List, Dict, Tuple


class SlotsGame:
    """
    3-reel slot machine with configurable symbols and payouts.
    Odds are loaded from ODDS-CHANGER.json for real-time adjustments.
    """

    # Default symbol definitions with weights
    DEFAULT_SYMBOLS = [
        ("🍒", 28),
        ("🍋", 24),
        ("🍊", 18),
        ("🍇", 14),
        ("🔔", 9),
        ("💎", 5),
        ("7️⃣", 2),
    ]

    DEFAULT_PAYOUTS_3X = {
        "🍒": 4,
        "🍋": 6,
        "🍊": 10,
        "🍇": 15,
        "🔔": 25,
        "💎": 50,
        "7️⃣": 77,
    }

    DEFAULT_PAYOUTS_2X = {
        "🍒": 1,
        "🍋": 1.5,
        "🍊": 2,
        "🍇": 2.5,
        "🔔": 4,
        "💎": 8,
        "7️⃣": 15,
    }

    def __init__(self):
        self._symbol_pool = None
        self._last_weights = None

    def _get_odds(self) -> tuple:
        """Get current odds from config file."""
        config = get_game_odds("slots")

        symbol_weights = config.get(
            "symbol_weights", {sym: w for sym, w in self.DEFAULT_SYMBOLS}
        )
        payouts_3x = config.get("payouts_3x", self.DEFAULT_PAYOUTS_3X)
        payouts_2x = config.get("payouts_2x", self.DEFAULT_PAYOUTS_2X)

        return symbol_weights, payouts_3x, payouts_2x

    def _build_symbol_pool(self, weights: Dict[str, int]) -> List[str]:
        """Build weighted symbol pool for random selection."""
        # Check if we need to rebuild
        if self._symbol_pool and self._last_weights == weights:
            return self._symbol_pool

        pool = []
        for symbol, weight in weights.items():
            pool.extend([symbol] * weight)

        self._symbol_pool = pool
        self._last_weights = weights
        return pool

    def _spin_reel(self, pool: List[str]) -> str:
        """Spin a single reel and return the symbol."""
        index = rng.random_int(0, len(pool) - 1)
        return pool[index]

    def _calculate_payout(
        self, reels: List[str], bet: float, payouts_3x: Dict, payouts_2x: Dict
    ) -> Tuple[float, float, str]:
        """
        Calculate payout based on reel results.
        Returns: (payout_amount, multiplier, win_type)
        """
        # Check for 3 of a kind (jackpot)
        if reels[0] == reels[1] == reels[2]:
            symbol = reels[0]
            multiplier = payouts_3x.get(symbol, 0)
            win_type = "jackpot" if symbol == "7️⃣" else "triple"
            return bet * multiplier, multiplier, win_type

        # Check for 2 of a kind - first two or last two
        if reels[0] == reels[1]:
            multiplier = payouts_2x.get(reels[0], 0)
            return bet * multiplier, multiplier, "double"

        if reels[1] == reels[2]:
            multiplier = payouts_2x.get(reels[1], 0)
            return bet * multiplier, multiplier, "double"

        # No win
        return 0, 0, "lose"

    def spin(self, bet_amount: float) -> Dict:
        """
        Spin the slot machine.

        Args:
            bet_amount: Amount wagered

        Returns:
            Dict with reels, win status, payout, and multiplier
        """
        # Load current odds
        symbol_weights, payouts_3x, payouts_2x = self._get_odds()

        # Build symbol pool
        pool = self._build_symbol_pool(symbol_weights)

        # Generate 3 reels
        reels = [self._spin_reel(pool) for _ in range(3)]

        # Calculate payout
        payout, multiplier, win_type = self._calculate_payout(
            reels, bet_amount, payouts_3x, payouts_2x
        )

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
