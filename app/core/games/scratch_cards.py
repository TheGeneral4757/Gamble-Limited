"""
Scratch Cards game - Buy a card, reveal prizes.
Match 3 of the same multiplier to win that payout.
Supports Gamble Friday bonuses.
"""

from app.core.rng import rng
from app.core.gamble_friday import gamble_friday
from app.config import settings
from typing import Dict, List


class ScratchCardsGame:
    """
    Scratch card game with configurable prize weights.
    9 cells, match 3 of same multiplier to win.
    """

    # Default prize multipliers and their weights (higher weight = more common)
    DEFAULT_PRIZE_WEIGHTS = {
        "0": 40,  # No prize (most common)
        "0.5": 25,  # Half bet back
        "1": 20,  # Break even
        "2": 10,  # 2x
        "5": 3,  # 5x
        "10": 1.5,  # 10x
        "50": 0.5,  # 50x (rare)
    }

    def _get_config(self) -> dict:
        """Get game configuration from settings."""
        try:
            games_data = (
                settings.games.model_dump()
                if hasattr(settings.games, "model_dump")
                else settings.games.dict()
            )
            return games_data.get("scratch_cards", {})
        except Exception:
            return {}

    def _get_prize_weights(self) -> Dict[str, float]:
        """Get prize weights, applying Gamble Friday adjustments."""
        config = self._get_config()
        weights = config.get("prize_weights", self.DEFAULT_PRIZE_WEIGHTS)

        # On Gamble Friday, slightly reduce win rates (more 0s)
        if gamble_friday.is_active():
            adjustment = gamble_friday.get_win_rate_adjustment("scratch_cards")
            if adjustment < 0:
                # Increase weight of 0 prize
                weights = dict(weights)
                weights["0"] = weights.get("0", 40) * (1 - adjustment)

        return weights

    def _generate_card(self) -> List[str]:
        """Generate 9 cells for the scratch card."""
        weights = self._get_prize_weights()

        # Build weighted pool
        pool = []
        for prize, weight in weights.items():
            pool.extend([prize] * int(weight * 10))  # Scale for precision

        # Generate 9 cells
        cells = []
        for _ in range(9):
            idx = rng.random_int(0, len(pool) - 1)
            cells.append(pool[idx])

        return cells

    def _check_win(self, cells: List[str]) -> tuple:
        """
        Check if there's a winning combination (3 of same).
        Returns (winning_multiplier, positions) or (0, [])
        """
        # Count occurrences
        counts = {}
        positions = {}
        for i, cell in enumerate(cells):
            if cell not in counts:
                counts[cell] = 0
                positions[cell] = []
            counts[cell] += 1
            positions[cell].append(i)

        # Find highest winning multiplier with 3+ matches
        best_win = 0
        best_positions = []

        for prize, count in counts.items():
            if count >= 3 and float(prize) > best_win:
                best_win = float(prize)
                # First 3 matching positions
                best_positions = positions[prize][:3]

        return best_win, best_positions

    def buy(self, bet_amount: float) -> Dict:
        """
        Buy and reveal a scratch card.

        Args:
            bet_amount: Amount wagered (cost of card)

        Returns:
            Dict with cells, win status, payout, and winning positions
        """
        # Generate the card
        cells = self._generate_card()

        # Check for wins
        multiplier, winning_positions = self._check_win(cells)

        # Calculate payout with Gamble Friday bonus
        base_payout = bet_amount * multiplier
        friday_multiplier = gamble_friday.get_winnings_multiplier()
        payout = base_payout * friday_multiplier

        win = payout > 0

        return {
            "cells": cells,
            "win": win,
            "multiplier": multiplier,
            "payout": round(payout, 2),
            "winning_positions": winning_positions,
            "bet": bet_amount,
            "is_friday": gamble_friday.is_active(),
            "friday_bonus": friday_multiplier if gamble_friday.is_active() else 1.0,
        }


# Singleton instance
scratch_cards_game = ScratchCardsGame()
