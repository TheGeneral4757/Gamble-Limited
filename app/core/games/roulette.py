from app.core.rng import rng
from typing import Dict


class RouletteGame:
    """
    European Roulette (37 pockets: 0-36).
    Supports multiple bet types with proper payouts.
    """

    # Red numbers on European roulette wheel
    RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

    # Payout multipliers (includes original bet return)
    PAYOUTS = {
        "straight": 36,  # Single number (35:1 + bet)
        "split": 18,  # Two numbers (17:1 + bet)
        "street": 12,  # Three numbers (11:1 + bet)
        "corner": 9,  # Four numbers (8:1 + bet)
        "line": 6,  # Six numbers (5:1 + bet)
        "dozen": 3,  # 12 numbers (2:1 + bet)
        "column": 3,  # 12 numbers (2:1 + bet)
        "red": 2,  # 18 numbers (1:1 + bet)
        "black": 2,  # 18 numbers (1:1 + bet)
        "odd": 2,  # 18 numbers (1:1 + bet)
        "even": 2,  # 18 numbers (1:1 + bet)
        "low": 2,  # 1-18 (1:1 + bet)
        "high": 2,  # 19-36 (1:1 + bet)
    }

    def _get_color(self, number: int) -> str:
        """Get the color of a roulette number."""
        if number == 0:
            return "green"
        elif number in self.RED_NUMBERS:
            return "red"
        else:
            return "black"

    def _check_win(self, number: int, bet_type: str, bet_value: str) -> bool:
        """Check if a bet wins based on the spin result."""

        if bet_type == "straight":
            return number == int(bet_value)

        elif bet_type == "red":
            return number in self.RED_NUMBERS

        elif bet_type == "black":
            return number in self.BLACK_NUMBERS

        elif bet_type == "odd":
            return number != 0 and number % 2 == 1

        elif bet_type == "even":
            return number != 0 and number % 2 == 0

        elif bet_type == "low":
            return 1 <= number <= 18

        elif bet_type == "high":
            return 19 <= number <= 36

        elif bet_type == "dozen":
            dozen = int(bet_value)
            if dozen == 1:
                return 1 <= number <= 12
            elif dozen == 2:
                return 13 <= number <= 24
            elif dozen == 3:
                return 25 <= number <= 36

        elif bet_type == "column":
            column = int(bet_value)
            # Column 1: 1,4,7,10... Column 2: 2,5,8,11... Column 3: 3,6,9,12...
            return number != 0 and number % 3 == column % 3

        return False

    def spin(self, bet_amount: float, bet_type: str, bet_value: str = "") -> Dict:
        """
        Spin the roulette wheel and resolve bets.

        Args:
            bet_amount: Amount wagered
            bet_type: Type of bet (straight, red, black, odd, even, etc.)
            bet_value: Specific value for the bet (number for straight, dozen number, etc.)

        Returns:
            Dict with spin result, win status, and payout
        """
        # Validate bet type
        bet_type = bet_type.lower()
        if bet_type not in self.PAYOUTS:
            return {"error": f"Invalid bet type: {bet_type}"}

        # Spin the wheel (0-36)
        result_number = rng.random_int(0, 36)
        result_color = self._get_color(result_number)

        # Check if the bet wins
        win = self._check_win(result_number, bet_type, bet_value)

        # Calculate payout
        if win:
            multiplier = self.PAYOUTS[bet_type]
            payout = bet_amount * multiplier
        else:
            multiplier = 0
            payout = 0

        return {
            "number": result_number,
            "color": result_color,
            "bet_type": bet_type,
            "bet_value": bet_value,
            "win": win,
            "payout": round(payout, 2),
            "multiplier": multiplier,
            "bet": bet_amount,
        }


# Singleton instance
roulette_game = RouletteGame()
