"""
Number Guess game - Guess a number 1-100, payout based on distance.
Closer guess = better payout.
Supports Gamble Friday bonuses.
"""

from app.core.rng import rng
from app.core.gamble_friday import gamble_friday
from app.config import settings
from typing import Dict


class NumberGuessGame:
    """
    Number guessing game where payout depends on how close your guess is.
    """

    # Default payouts based on distance from target
    DEFAULT_PAYOUTS = {
        "exact": 50,  # Exact match - 50x
        "off_1": 10,  # Off by 1 - 10x
        "off_2_5": 5,  # Off by 2-5 - 5x
        "off_6_10": 2,  # Off by 6-10 - 2x
        "off_11_20": 1,  # Off by 11-20 - 1x (break even)
        # Off by 21+ = 0 (lose)
    }

    def _get_config(self) -> dict:
        """Get game configuration from settings."""
        try:
            games_data = (
                settings.games.model_dump()
                if hasattr(settings.games, "model_dump")
                else settings.games.dict()
            )
            return games_data.get("number_guess", {})
        except Exception:
            return {}

    def _get_payouts(self) -> dict:
        """Get payout configuration."""
        config = self._get_config()
        return config.get("payouts", self.DEFAULT_PAYOUTS)

    def _calculate_multiplier(self, distance: int) -> tuple:
        """
        Calculate multiplier based on distance from target.
        Returns (multiplier, tier_name)
        """
        payouts = self._get_payouts()

        if distance == 0:
            return payouts.get("exact", 50), "exact"
        elif distance == 1:
            return payouts.get("off_1", 10), "off_1"
        elif 2 <= distance <= 5:
            return payouts.get("off_2_5", 5), "off_2_5"
        elif 6 <= distance <= 10:
            return payouts.get("off_6_10", 2), "off_6_10"
        elif 11 <= distance <= 20:
            return payouts.get("off_11_20", 1), "off_11_20"
        else:
            return 0, "miss"

    def guess(self, bet_amount: float, player_guess: int) -> Dict:
        """
        Make a guess and determine the result.

        Args:
            bet_amount: Amount wagered
            player_guess: Player's guess (1-100)

        Returns:
            Dict with target number, distance, multiplier, and payout
        """
        # Validate guess
        if not isinstance(player_guess, int) or player_guess < 1 or player_guess > 100:
            return {"error": "Guess must be a number between 1 and 100"}

        # Generate target number
        target = rng.random_int(1, 100)

        # Calculate distance
        distance = abs(target - player_guess)

        # Get multiplier and tier
        multiplier, tier = self._calculate_multiplier(distance)

        # Calculate payout with Gamble Friday bonus
        friday_mult = gamble_friday.get_winnings_multiplier()
        base_payout = bet_amount * multiplier
        payout = base_payout * friday_mult if multiplier > 0 else 0

        win = payout > 0

        # Generate hint/feedback
        if distance == 0:
            message = "🎯 PERFECT! You got it exactly right!"
        elif distance == 1:
            message = "🔥 SO CLOSE! Off by just 1!"
        elif distance <= 5:
            message = "🌡️ HOT! Very close!"
        elif distance <= 10:
            message = "😊 WARM! Getting there!"
        elif distance <= 20:
            message = "❄️ COLD! But still a win!"
        else:
            message = "🥶 FREEZING! Too far off."

        return {
            "target": target,
            "guess": player_guess,
            "distance": distance,
            "tier": tier,
            "win": win,
            "multiplier": multiplier,
            "payout": round(payout, 2),
            "bet": bet_amount,
            "message": message,
            "is_friday": gamble_friday.is_active(),
            "friday_bonus": friday_mult if gamble_friday.is_active() and win else 1.0,
            "is_exact": distance == 0,
        }


# Singleton instance
number_guess_game = NumberGuessGame()
