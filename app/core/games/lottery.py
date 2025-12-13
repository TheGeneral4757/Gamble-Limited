"""
Lottery System - Monthly draw with cash prizes.
Features:
- First Friday of each month draw at noon CT
- Pick 6 numbers from 1-49
- Progressive jackpot with rollover
- Multiple ticket purchases
- Lump sum (50%) or installment (100%) payout options
- Multiple winner handling with coin flip option

NOTE: Lottery is NOT affected by Gamble Friday.
"""

from app.core.rng import rng
from app.config import settings
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False


class LotterySystem:
    """
    Full lottery system with monthly draws and cash prizes.
    """
    
    def _get_config(self) -> dict:
        """Get lottery configuration from settings."""
        try:
            if hasattr(settings, 'lottery'):
                return settings.lottery.model_dump() if hasattr(settings.lottery, "model_dump") else settings.lottery.dict()
            return {}
        except Exception:
            return {}
    
    def _get_timezone(self):
        """Get configured timezone."""
        config = self._get_config()
        tz_name = config.get("timezone", "America/Chicago")
        if PYTZ_AVAILABLE:
            return pytz.timezone(tz_name)
        return None
    
    def get_ticket_price(self) -> float:
        """Get current ticket price (cash)."""
        config = self._get_config()
        return config.get("ticket_price", 50.0)
    
    def get_max_tickets(self) -> int:
        """Get max tickets per user per draw."""
        config = self._get_config()
        return config.get("max_tickets_per_user", 100)
    
    def get_numbers_config(self) -> Tuple[int, int]:
        """Get (numbers_to_pick, max_number)."""
        config = self._get_config()
        return (
            config.get("numbers_to_pick", 6),
            config.get("number_range_max", 49)
        )
    
    def get_prize_tiers(self) -> dict:
        """Get prize tier configuration."""
        config = self._get_config()
        return config.get("prize_tiers", {
            "6": "jackpot",
            "5": 5000,
            "4": 500,
            "3": 25,
            "2": "free_ticket"
        })
    
    def get_lump_sum_percent(self) -> float:
        """Get lump sum payout percentage."""
        config = self._get_config()
        return config.get("lump_sum_percent", 50.0)
    
    def get_installment_config(self) -> dict:
        """Get installment payout configuration."""
        config = self._get_config()
        return {
            "weeks": config.get("installment_weeks", 52),
            "days": config.get("installment_days", ["monday", "wednesday", "friday"]),
            "hour": config.get("installment_hour", 12),
            "minute": config.get("installment_minute", 0)
        }
    
    def get_progressive_config(self) -> dict:
        """Get progressive odds configuration."""
        config = self._get_config()
        return config.get("progressive_odds", {
            "enabled": True,
            "force_winner_after_months": 2,
            "month_1_no_winner_boost": 0.5,
            "month_2_guaranteed": True
        })
    
    def get_next_draw_date(self) -> datetime:
        """Calculate the next draw date (first Friday of month at noon CT)."""
        tz = self._get_timezone()
        config = self._get_config()
        
        if tz:
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        draw_hour = config.get("draw_hour", 12)
        draw_minute = config.get("draw_minute", 0)
        
        # Find first Friday of current month
        first_day = now.replace(day=1, hour=draw_hour, minute=draw_minute, second=0, microsecond=0)
        days_until_friday = (4 - first_day.weekday()) % 7  # Friday = 4
        first_friday = first_day + timedelta(days=days_until_friday)
        
        # If we've passed this month's draw, get next month's first Friday
        if now >= first_friday:
            # Move to next month
            if now.month == 12:
                next_month = first_day.replace(year=now.year + 1, month=1)
            else:
                next_month = first_day.replace(month=now.month + 1)
            
            days_until_friday = (4 - next_month.weekday()) % 7
            first_friday = next_month + timedelta(days=days_until_friday)
        
        return first_friday
    
    def get_current_draw_id(self) -> str:
        """Get the draw ID for the current/upcoming draw (YYYY-MM format)."""
        next_draw = self.get_next_draw_date()
        return next_draw.strftime("%Y-%m")
    
    def validate_numbers(self, numbers: List[int]) -> Dict:
        """
        Validate a set of lottery numbers.
        
        Args:
            numbers: List of chosen numbers
            
        Returns:
            Dict with valid status and error if invalid
        """
        pick_count, max_num = self.get_numbers_config()
        
        if len(numbers) != pick_count:
            return {"valid": False, "error": f"Must pick exactly {pick_count} numbers"}
        
        if len(set(numbers)) != len(numbers):
            return {"valid": False, "error": "Duplicate numbers not allowed"}
        
        for num in numbers:
            if not isinstance(num, int) or num < 1 or num > max_num:
                return {"valid": False, "error": f"Numbers must be between 1 and {max_num}"}
        
        return {"valid": True}
    
    def generate_winning_numbers(self) -> List[int]:
        """Generate winning lottery numbers."""
        pick_count, max_num = self.get_numbers_config()
        
        numbers = []
        available = list(range(1, max_num + 1))
        
        for _ in range(pick_count):
            idx = rng.random_int(0, len(available) - 1)
            numbers.append(available.pop(idx))
        
        return sorted(numbers)
    
    def calculate_matches(self, ticket_numbers: List[int], winning_numbers: List[int]) -> int:
        """Count how many numbers match."""
        return len(set(ticket_numbers) & set(winning_numbers))
    
    def calculate_prize(self, matches: int, jackpot_amount: float) -> Dict:
        """
        Calculate prize for a given number of matches.
        
        Returns:
            Dict with prize_type (jackpot/cash/free_ticket/none) and amount
        """
        tiers = self.get_prize_tiers()
        tier_key = str(matches)
        
        if tier_key not in tiers:
            return {"prize_type": "none", "amount": 0}
        
        prize = tiers[tier_key]
        
        if prize == "jackpot":
            return {"prize_type": "jackpot", "amount": jackpot_amount}
        elif prize == "free_ticket":
            return {"prize_type": "free_ticket", "amount": 0}
        else:
            return {"prize_type": "cash", "amount": float(prize)}
    
    def calculate_lump_sum(self, jackpot: float) -> float:
        """Calculate lump sum payout (percentage of jackpot)."""
        percent = self.get_lump_sum_percent()
        return jackpot * (percent / 100.0)
    
    def calculate_installment_details(self, jackpot: float) -> Dict:
        """
        Calculate installment payment details.
        
        Returns:
            Dict with total, per_payment, num_payments, schedule_days
        """
        config = self.get_installment_config()
        weeks = config["weeks"]
        payment_days = config["days"]  # e.g., ["monday", "wednesday", "friday"]
        
        # Calculate number of payments
        payments_per_week = len(payment_days)
        total_payments = weeks * payments_per_week
        
        per_payment = jackpot / total_payments
        
        return {
            "total": jackpot,
            "per_payment": round(per_payment, 2),
            "num_payments": total_payments,
            "schedule_days": payment_days,
            "weeks": weeks
        }
    
    def should_force_winner(self, no_winner_months: int) -> Tuple[bool, float]:
        """
        Check if we should force a winner based on progressive odds.
        
        Args:
            no_winner_months: Number of consecutive months without a jackpot winner
            
        Returns:
            Tuple of (should_force, force_probability)
        """
        config = self.get_progressive_config()
        
        if not config.get("enabled", True):
            return False, 0.0
        
        max_months = config.get("force_winner_after_months", 2)
        
        if no_winner_months >= max_months:
            # Guaranteed winner
            return True, 1.0
        elif no_winner_months == 1:
            # First month without winner - boosted probability
            return True, config.get("month_1_no_winner_boost", 0.5)
        
        return False, 0.0
    
    def get_lottery_info(self, jackpot: float = None, no_winner_months: int = 0) -> Dict:
        """
        Get comprehensive lottery information for display.
        
        Args:
            jackpot: Current jackpot amount (optional, will show default if not provided)
            no_winner_months: Consecutive months without winner
            
        Returns:
            Dict with all lottery info
        """
        config = self._get_config()
        next_draw = self.get_next_draw_date()
        pick_count, max_num = self.get_numbers_config()
        
        # Calculate time until draw
        tz = self._get_timezone()
        if tz:
            now = datetime.now(tz)
        else:
            now = datetime.now()
        
        time_until = next_draw - now
        
        return {
            "enabled": config.get("enabled", True),
            "ticket_price": self.get_ticket_price(),
            "max_tickets": self.get_max_tickets(),
            "numbers_to_pick": pick_count,
            "number_range": f"1-{max_num}",
            "jackpot": jackpot or config.get("initial_jackpot", 10000.0),
            "next_draw": next_draw.isoformat(),
            "next_draw_formatted": next_draw.strftime("%B %d, %Y at %I:%M %p CT"),
            "time_until_draw": {
                "days": time_until.days,
                "hours": time_until.seconds // 3600,
                "minutes": (time_until.seconds % 3600) // 60
            },
            "draw_id": self.get_current_draw_id(),
            "prize_tiers": self.get_prize_tiers(),
            "lump_sum_percent": self.get_lump_sum_percent(),
            "installment_weeks": self.get_installment_config()["weeks"],
            "no_winner_months": no_winner_months,
            "progressive_active": no_winner_months > 0,
        }

    def get_next_draw_time_str(self) -> str:
        """Get formatted next draw time string."""
        return self.get_next_draw_date().strftime("%B %d, %Y at %I:%M %p CT")

    def perform_draw(self) -> Dict:
        """
        Execute the lottery draw logic.
        Returns dict with results: {winners: [], numbers: [], jackpot: float}
        """
        # Import db here to avoid circular imports if any
        from app.core.database import db
        import random
        
        draw_id = self.get_current_draw_id()
        
        # 1. Get all tickets
        tickets = db.get_all_tickets_for_draw(draw_id)
        
        # 2. Generate numbers
        winning_numbers = self.generate_winning_numbers()
        
        # 3. Check winners
        jackpot_info = db.get_lottery_jackpot()
        current_jackpot = jackpot_info["current_amount"]
        no_winner_months = jackpot_info["no_winner_months"]
        
        winners = []
        jackpot_winners = []
        
        for ticket in tickets:
            matches = self.calculate_matches(ticket["numbers"], winning_numbers)
            prize_info = self.calculate_prize(matches, current_jackpot)
            
            if prize_info["prize_type"] != "none":
                winner_data = {
                    "user_id": ticket["user_id"],
                    "username": ticket["username"],
                    "ticket_id": ticket["id"],
                    "matches": matches,
                    "prize_type": prize_info["prize_type"],
                    "amount": prize_info["amount"]
                }
                winners.append(winner_data)
                
                if prize_info["prize_type"] == "jackpot":
                    jackpot_winners.append(ticket["user_id"])
                elif prize_info["amount"] > 0:
                    # Pay immediate cash prizes
                    db.update_balance(ticket["user_id"], cash_delta=prize_info["amount"])
                    db.log_transaction(ticket["user_id"], "lottery_win", prize_info["amount"],
                                     db.get_balance(ticket["user_id"])["cash"],
                                     game="lottery", currency="cash", 
                                     details=f"Lottery win: {matches} matches")
                elif prize_info["prize_type"] == "free_ticket":
                    # Give cash equivalent of ticket price
                    ticket_price = self.get_ticket_price()
                    db.update_balance(ticket["user_id"], cash_delta=ticket_price)
                    db.log_transaction(ticket["user_id"], "lottery_win", ticket_price,
                                     db.get_balance(ticket["user_id"])["cash"],
                                     game="lottery", currency="cash", 
                                     details="Free ticket prize (cash equivalent)")

        # 4. Handle Jackpot Progressive / Forced Winner
        should_force, force_prob = self.should_force_winner(no_winner_months)
        
        # If no organic winner but forced winner needed
        if not jackpot_winners and should_force and tickets:
            if random.random() < force_prob:
                # Pick random ticket as winner
                forced_ticket = random.choice(tickets)
                
                winner_data = {
                    "user_id": forced_ticket["user_id"],
                    "username": forced_ticket["username"],
                    "ticket_id": forced_ticket["id"],
                    "matches": 6, # Treated as jackpot win
                    "prize_type": "jackpot",
                    "amount": current_jackpot,
                    "note": "Progressive guaranteed win"
                }
                winners.append(winner_data)
                jackpot_winners.append(forced_ticket["user_id"])
        
        if jackpot_winners:
            # We have winners. Jackpot reset.
            config = self._get_config()
            initial = config.get("initial_jackpot", 10000.0)
            db.update_lottery_jackpot(amount=initial, no_winner_months=0)
        else:
            # No winner, rollover
            new_streak = no_winner_months + 1
            db.update_lottery_jackpot(no_winner_months=new_streak)
        
        # Record draw
        db.record_lottery_draw(draw_id, winning_numbers, winners, current_jackpot, 
                              no_winner_streak=no_winner_months if not jackpot_winners else 0)
        
        return {
            "winners": winners,
            "numbers": winning_numbers,
            "jackpot": current_jackpot
        }


# Singleton instance
lottery_system = LotterySystem()
