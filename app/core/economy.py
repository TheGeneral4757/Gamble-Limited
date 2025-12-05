"""
Economy system with dynamic conversion rates.
"""

from app.core.database import db
from app.config import settings
import time

class EconomySystem:
    """Manages the virtual economy with dynamic rates."""
    
    def __init__(self):
        self._rate_cache = None
        self._rate_cache_time = 0
        self._base_rate = settings.economy.base_exchange_rate
    
    def get_current_exchange_rate(self, user_id: int = None) -> float:
        """Get current exchange rate with user-specific adjustments."""
        current_time = time.time()
        
        # Refresh base rate every 30 seconds with ±5% variance
        if current_time - self._rate_cache_time > 30:
            import random
            variance = random.uniform(-0.05, 0.05)
            self._rate_cache = self._base_rate * (1 + variance)
            self._rate_cache_time = current_time
        
        rate = self._rate_cache
        
        # Apply user-specific penalty if converting too much
        if user_id:
            penalty = db.get_conversion_penalty(user_id)
            rate = rate * (1 - penalty)  # Worse rate for frequent converters
        
        return round(rate, 2)
    
    def get_balance(self, user_id: int) -> dict:
        """Get current balance."""
        return db.get_balance(user_id)
    
    def has_sufficient_funds(self, user_id: int, amount: float, currency: str = "credits") -> bool:
        """Check if user has sufficient funds."""
        balance = self.get_balance(user_id)
        if currency == "cash":
            return balance["cash"] >= amount
        return balance["credits"] >= amount
    
    def place_bet(self, user_id: int, amount: float, game: str) -> dict:
        """Deduct bet from credits."""
        balance = self.get_balance(user_id)
        
        if balance["credits"] < amount:
            return {"success": False, "error": "Insufficient credits"}
        
        new_balance = db.update_balance(user_id, credits_delta=-amount)
        db.log_transaction(user_id, "bet", -amount, new_balance["credits"], game=game)
        
        return {"success": True, "balance": new_balance}
    
    def add_winnings(self, user_id: int, amount: float, game: str, bet: float = 0) -> dict:
        """Add winnings to credits."""
        new_balance = db.update_balance(user_id, credits_delta=amount)
        db.log_transaction(user_id, "win", amount, new_balance["credits"], 
                          game=game, details=f"Bet: {bet}")
        db.record_game(user_id, game, bet, amount)
        
        return {"success": True, "balance": new_balance}
    
    def do_exchange(self, user_id: int, from_currency: str, amount: float) -> dict:
        """Exchange between cash and credits with dynamic rate."""
        rate = self.get_current_exchange_rate(user_id)
        balance = self.get_balance(user_id)
        
        if from_currency == "cash":
            if balance["cash"] < amount:
                return {"success": False, "error": "Insufficient cash"}
            
            credits_received = amount * rate
            new_balance = db.update_balance(user_id, cash_delta=-amount, credits_delta=credits_received)
            db.record_conversion(user_id, amount)
            db.log_transaction(user_id, "exchange", amount, new_balance["credits"],
                              currency="cash", details=f"Rate: {rate}")
            
            return {
                "success": True,
                "received": credits_received,
                "rate": rate,
                "balance": new_balance
            }
        else:
            if balance["credits"] < amount:
                return {"success": False, "error": "Insufficient credits"}
            
            cash_received = amount / rate
            new_balance = db.update_balance(user_id, cash_delta=cash_received, credits_delta=-amount)
            db.record_conversion(user_id, amount)
            db.log_transaction(user_id, "exchange", amount, new_balance["cash"],
                              currency="credits", details=f"Rate: {rate}")
            
            return {
                "success": True,
                "received": cash_received,
                "rate": rate,
                "balance": new_balance
            }


# Singleton
economy = EconomySystem()
