from app.config import settings
from app.core.rng import rng
from app.core.database import db
from typing import Dict, Optional

class EconomySystem:
    """
    Economy system with database-backed user balances.
    Handles exchange rates, betting, and payouts.
    """
    
    def __init__(self):
        self.base_rate = settings.economy.base_exchange_rate
        self.fluctuation = settings.economy.fluctuation_range
        self._cached_rate = None
        self._rate_cache_time = 0
    
    def get_current_exchange_rate(self) -> float:
        """
        Calculates the current exchange rate with a small random fluctuation.
        Returns: Credits per 1 Cash.
        """
        import time
        current_time = time.time()
        
        # Cache rate for 30 seconds to reduce fluctuation spam
        if self._cached_rate and (current_time - self._rate_cache_time) < 30:
            return self._cached_rate
        
        # Fluctuation is a percentage, e.g., 0.05 means +/- 5%
        random_factor = (rng.random_float() * 2 * self.fluctuation) - self.fluctuation
        current_rate = self.base_rate * (1 + random_factor)
        
        self._cached_rate = round(current_rate, 2)
        self._rate_cache_time = current_time
        
        return self._cached_rate

    def convert_cash_to_credits(self, cash_amount: float) -> float:
        rate = self.get_current_exchange_rate()
        return round(cash_amount * rate, 2)

    def convert_credits_to_cash(self, credits_amount: float) -> float:
        rate = self.get_current_exchange_rate()
        return round(credits_amount / rate, 2)
    
    # ==================== User Balance Operations ====================
    
    def get_balance(self, user_id: str) -> Dict:
        """Get user's current balance from database."""
        return db.get_balance(user_id)
    
    def place_bet(self, user_id: str, amount: float, currency: str = "credits") -> Dict:
        """
        Deduct bet amount from user balance.
        
        Returns:
            Dict with success status and new balance
        """
        balance = db.get_balance(user_id)
        current = balance.get(currency, 0)
        
        if amount <= 0:
            return {"success": False, "error": "Bet must be positive"}
        
        if current < amount:
            return {"success": False, "error": f"Insufficient {currency}", "balance": balance}
        
        # Deduct bet
        delta = {f"{currency}_delta": -amount}
        if currency == "credits":
            new_balance = db.update_balance(user_id, credits_delta=-amount)
        else:
            new_balance = db.update_balance(user_id, cash_delta=-amount)
        
        return {"success": True, "balance": new_balance, "deducted": amount}
    
    def add_winnings(self, user_id: str, amount: float, currency: str = "credits", 
                     game: str = None) -> Dict:
        """Add winnings to user balance."""
        if currency == "credits":
            new_balance = db.update_balance(user_id, credits_delta=amount)
        else:
            new_balance = db.update_balance(user_id, cash_delta=amount)
        
        # Log transaction
        db.log_transaction(
            user_id=user_id,
            tx_type="win",
            amount=amount,
            balance_after=new_balance[currency],
            game=game
        )
        
        return {"success": True, "balance": new_balance, "added": amount}
    
    def grant_funds(self, user_id: str, cash: float = 0, credits: float = 0) -> Dict:
        """Admin function to grant funds to a user."""
        new_balance = db.update_balance(user_id, cash_delta=cash, credits_delta=credits)
        
        if cash > 0 or credits > 0:
            db.log_transaction(
                user_id=user_id,
                tx_type="admin_grant",
                amount=cash + credits,
                balance_after=new_balance["credits"],
                details=f"Granted ${cash} cash, {credits} credits"
            )
        
        return new_balance
    
    def reset_user(self, user_id: str) -> Dict:
        """Reset user to starting balance."""
        new_balance = db.set_balance(
            user_id,
            cash=settings.economy.starting_cash,
            credits=settings.economy.starting_credits
        )
        
        db.log_transaction(
            user_id=user_id,
            tx_type="reset",
            amount=0,
            balance_after=new_balance["credits"],
            details="Balance reset to starting values"
        )
        
        return new_balance
    
    def do_exchange(self, user_id: str, from_currency: str, amount: float) -> Dict:
        """Exchange between cash and credits."""
        rate = self.get_current_exchange_rate()
        balance = db.get_balance(user_id)
        
        if from_currency == "cash":
            if balance["cash"] < amount:
                return {"success": False, "error": "Insufficient cash"}
            
            credits_gained = self.convert_cash_to_credits(amount)
            new_balance = db.update_balance(user_id, cash_delta=-amount, credits_delta=credits_gained)
            
            return {
                "success": True,
                "exchanged": amount,
                "received": credits_gained,
                "rate": rate,
                "balance": new_balance
            }
        else:
            if balance["credits"] < amount:
                return {"success": False, "error": "Insufficient credits"}
            
            cash_gained = self.convert_credits_to_cash(amount)
            new_balance = db.update_balance(user_id, cash_delta=cash_gained, credits_delta=-amount)
            
            return {
                "success": True,
                "exchanged": amount,
                "received": cash_gained,
                "rate": rate,
                "balance": new_balance
            }


economy = EconomySystem()
