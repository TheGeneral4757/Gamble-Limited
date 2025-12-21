"""
Economy system with dynamic market-based conversion rates.
Features:
- Global market events (spikes/crashes)
- Larger periodic price swings
- Friday bonus rates
- Price history tracking
"""

from app.core.database import db
from app.config import settings
from app.core.gamble_friday import is_gamble_friday
import time
import random
import math


class MarketState:
    """Tracks the global market state for exchange rates."""

    def __init__(self):
        self.base_rate = settings.economy.base_exchange_rate
        self.current_rate = self.base_rate
        self.last_update = 0
        self.trend = 0  # -1 to 1, affects direction of changes
        self.volatility = 0.1  # Base volatility
        self.event_active = False
        self.event_type = None
        self.event_end_time = 0
        self.price_history = []  # Last 10 rates

    def _trigger_random_event(self):
        """Randomly trigger market events (10% chance per update)."""
        if random.random() < 0.10 and not self.event_active:
            event_types = [
                ("boom", 1.5, 2.5),  # 50-150% rate increase
                ("crash", 0.3, 0.6),  # 40-70% rate decrease
                ("stable", 0.98, 1.02),  # Stable period
                ("volatile", 0.5, 2.0),  # Extreme swings
            ]
            self.event_type, self.event_min, self.event_max = random.choice(event_types)
            self.event_active = True
            self.event_end_time = time.time() + random.randint(30, 180)  # 30s-3mins
            return True
        return False

    def update_rate(self) -> float:
        """Update and return the current exchange rate."""
        current_time = time.time()

        # Check if event has ended
        if self.event_active and current_time >= self.event_end_time:
            self.event_active = False
            self.event_type = None

        # Update every 5 seconds for more dynamic feel
        if current_time - self.last_update < 5:
            return self.current_rate

        self.last_update = current_time

        # Try to trigger a random event
        self._trigger_random_event()

        # Calculate new rate
        if self.event_active:
            # Apply event-based multiplier
            event_mult = random.uniform(self.event_min, self.event_max)
            target_rate = self.base_rate * event_mult
        else:
            # Normal market behavior with aggressive swings
            # Update trend with strong momentum
            self.trend += random.uniform(-0.5, 0.5)
            self.trend = max(-1, min(1, self.trend))  # Clamp

            # Base change: ±25% normal fluctuation
            base_change = random.uniform(-0.25, 0.25)

            # Apply trend influence
            trend_change = self.trend * 0.15

            # Sinusoidal pattern for more natural fluctuation
            time_factor = math.sin(current_time / 60) * 0.1

            total_change = base_change + trend_change + time_factor
            target_rate = self.base_rate * (1 + total_change)

        # Fast transition to new rate
        rate_diff = target_rate - self.current_rate
        self.current_rate += rate_diff * 0.5  # Move 50% toward target

        # Clamp to reasonable bounds (10% - 500% of base)
        self.current_rate = max(
            self.base_rate * 0.1, min(self.base_rate * 5.0, self.current_rate)
        )

        # Track history
        self.price_history.append(round(self.current_rate, 2))
        if len(self.price_history) > 20:
            self.price_history.pop(0)

        return self.current_rate

    def reset_to_baseline(self):
        """Force reset rate to baseline (Weekly Reset)."""
        self.current_rate = self.base_rate
        self.trend = 0
        self.event_active = False
        self.price_history.append(self.base_rate)

    def get_rate_info(self) -> dict:
        """Get detailed rate information for display."""
        return {
            "current_rate": round(self.current_rate, 2),
            "base_rate": self.base_rate,
            "trend": (
                "rising"
                if self.trend > 0.2
                else "falling" if self.trend < -0.2 else "stable"
            ),
            "event_active": self.event_active,
            "event_type": self.event_type,
            "history": self.price_history,
        }


# Global market state
market = MarketState()


class EconomySystem:
    """Manages the virtual economy with dynamic rates."""

    def __init__(self):
        self._base_rate = settings.economy.base_exchange_rate

    def get_current_exchange_rate(self) -> float:
        """Get current global exchange rate."""
        # Get global market rate
        rate = market.update_rate()

        # Apply Friday bonus (10% better rates)
        if is_gamble_friday():
            rate *= 1.1

        return round(rate, 2)

    def get_rate_info(self) -> dict:
        """Get detailed rate info for UI."""
        info = market.get_rate_info()
        info["friday_bonus"] = is_gamble_friday()
        info["global_rate"] = self.get_current_exchange_rate()
        return info

    async def get_balance(self, user_id: int) -> dict:
        """Get current balance."""
        return await db.get_balance(user_id)

    async def has_sufficient_funds(
        self, user_id: int, amount: float, currency: str = "credits"
    ) -> bool:
        """Check if user has sufficient funds."""
        balance = await self.get_balance(user_id)
        if currency == "cash":
            return balance["cash"] >= amount
        return balance["credits"] >= amount

    async def place_bet(self, user_id: int, amount: float, game: str) -> dict:
        """Deduct bet from credits."""
        balance = await self.get_balance(user_id)

        if balance["credits"] < amount:
            return {"success": False, "error": "Insufficient credits"}

        new_balance = await db.update_balance(user_id, credits_delta=-amount)
        await db.log_transaction(user_id, "bet", -amount, new_balance["credits"], game=game)

        return {"success": True, "balance": new_balance}

    async def add_winnings(
        self, user_id: int, amount: float, game: str, bet: float = 0
    ) -> dict:
        """Add winnings to credits."""
        new_balance = await db.update_balance(user_id, credits_delta=amount)
        await db.log_transaction(
            user_id,
            "win",
            amount,
            new_balance["credits"],
            game=game,
            details=f"Bet: {bet}",
        )
        await db.record_game(user_id, game, bet, amount)

        return {"success": True, "balance": new_balance}

    async def do_exchange(self, user_id: int, from_currency: str, amount: float) -> dict:
        """Exchange between cash and credits with dynamic rate."""
        rate = self.get_current_exchange_rate()
        balance = await self.get_balance(user_id)

        if from_currency == "cash":
            if balance["cash"] < amount:
                return {"success": False, "error": "Insufficient cash"}

            credits_received = amount * rate
            new_balance = await db.update_balance(
                user_id, cash_delta=-amount, credits_delta=credits_received
            )
            await db.record_conversion(user_id, amount)
            await db.log_transaction(
                user_id,
                "exchange",
                amount,
                new_balance["credits"],
                currency="cash",
                details=f"Rate: {rate}",
            )

            return {
                "success": True,
                "received": round(credits_received, 2),
                "rate": rate,
                "balance": new_balance,
                "friday_bonus": is_gamble_friday(),
            }
        else:
            if balance["credits"] < amount:
                return {"success": False, "error": "Insufficient credits"}

            cash_received = amount / rate
            new_balance = await db.update_balance(
                user_id, cash_delta=cash_received, credits_delta=-amount
            )
            await db.record_conversion(user_id, amount)
            await db.log_transaction(
                user_id,
                "exchange",
                amount,
                new_balance["cash"],
                currency="credits",
                details=f"Rate: {rate}",
            )

            return {
                "success": True,
                "received": round(cash_received, 2),
                "rate": rate,
                "balance": new_balance,
                "friday_bonus": is_gamble_friday(),
            }


# Singleton
economy = EconomySystem()
