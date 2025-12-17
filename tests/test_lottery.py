import sys
from unittest.mock import MagicMock

# Mock sqlite3 before importing app modules that use it
sys.modules["sqlite3"] = MagicMock()

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

from app.core.games.lottery import LotterySystem, lottery_system
import app.core.database # Ensure database module is loaded for patching

class TestLotterySystem(unittest.TestCase):
    
    def setUp(self):
        self.lottery = LotterySystem()
        self.mock_config = {
            "ticket_price": 50.0,
            "max_tickets_per_user": 100,
            "numbers_to_pick": 6,
            "number_range_max": 49,
            "prize_tiers": {
                "6": "jackpot",
                "5": 5000,
                "4": 500,
                "3": 25,
                "2": "free_ticket"
            },
            "draw_hour": 12,
            "draw_minute": 0,
            "timezone": "America/Chicago",
            "initial_jackpot": 10000.0
        }
    
    def test_validate_numbers(self):
        # Valid numbers
        with patch.object(self.lottery, '_get_config', return_value=self.mock_config):
            result = self.lottery.validate_numbers([1, 2, 3, 4, 5, 6])
            self.assertTrue(result["valid"])
            
            # Invalid: Wrong count
            result = self.lottery.validate_numbers([1, 2, 3, 4, 5])
            self.assertFalse(result["valid"])
            self.assertIn("Must pick exactly", result["error"])
            
            # Invalid: Duplicates
            result = self.lottery.validate_numbers([1, 2, 3, 4, 5, 5])
            self.assertFalse(result["valid"])
            self.assertIn("Duplicate numbers", result["error"])
            
            # Invalid: Out of range
            result = self.lottery.validate_numbers([1, 2, 3, 4, 5, 50])
            self.assertFalse(result["valid"])
            self.assertIn("Numbers must be between", result["error"])

    def test_calculate_matches(self):
        # 6 matches
        matches = self.lottery.calculate_matches([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6])
        self.assertEqual(matches, 6)
        
        # 3 matches
        matches = self.lottery.calculate_matches([1, 2, 3, 10, 11, 12], [1, 2, 3, 4, 5, 6])
        self.assertEqual(matches, 3)
        
        # 0 matches
        matches = self.lottery.calculate_matches([7, 8, 9, 10, 11, 12], [1, 2, 3, 4, 5, 6])
        self.assertEqual(matches, 0)
        
    def test_calculate_prize_payouts(self):
        with patch.object(self.lottery, '_get_config', return_value=self.mock_config):
            # Jackpot (6 matches)
            prize = self.lottery.calculate_prize(6, 100000.0)
            self.assertEqual(prize["prize_type"], "jackpot")
            self.assertEqual(prize["amount"], 100000.0)
            
            # Cash prize (5 matches)
            prize = self.lottery.calculate_prize(5, 100000.0)
            self.assertEqual(prize["prize_type"], "cash")
            self.assertEqual(prize["amount"], 5000.0)
            
            # Free ticket (2 matches)
            prize = self.lottery.calculate_prize(2, 100000.0)
            self.assertEqual(prize["prize_type"], "free_ticket")
            self.assertEqual(prize["amount"], 0)
            
            # No prize (1 match) - using default config of 2 matches needed for prize
            prize = self.lottery.calculate_prize(1, 100000.0)
            self.assertEqual(prize["prize_type"], "none")
            self.assertEqual(prize["amount"], 0)

    @patch('app.core.database.db')
    def test_money_delivery(self, mock_db):
        """Test that money is correctly delivered for non-jackpot wins."""
        # Setup mocks
        mock_db.get_all_tickets_for_draw.return_value = [
            {"user_id": 1, "username": "user1", "id": 101, "numbers": [1, 2, 3, 4, 5, 7]},  # 5 matches -> $5000
            {"user_id": 2, "username": "user2", "id": 102, "numbers": [1, 2, 7, 8, 9, 10]}   # 2 matches -> free ticket
        ]
        mock_db.get_lottery_jackpot.return_value = {"current_amount": 100000.0, "no_winner_months": 0}
        mock_db.get_balance.return_value = {"cash": 500.0}
        
        # Mock winning numbers to [1, 2, 3, 4, 5, 6]
        with patch.object(self.lottery, 'generate_winning_numbers', return_value=[1, 2, 3, 4, 5, 6]):
            with patch.object(self.lottery, '_get_config', return_value=self.mock_config):
                
                results = self.lottery.perform_draw()
                
                # Check User 1: 5 matches -> $5000
                # db.update_balance check
                # We expect update_balance call for user 1 with 5000
                calls = mock_db.update_balance.call_args_list
                
                # Filter calls for user 1
                user1_calls = [c for c in calls if c[0][0] == 1]
                self.assertTrue(len(user1_calls) > 0, "User 1 should receive money")
                self.assertEqual(user1_calls[0].kwargs.get("cash_delta"), 5000, "User 1 should get $5000")
                
                # Check User 2: 2 matches -> Free ticket (cash equiv $50)
                user2_calls = [c for c in calls if c[0][0] == 2]
                self.assertTrue(len(user2_calls) > 0, "User 2 should receive money for free ticket")
                self.assertEqual(user2_calls[0].kwargs.get("cash_delta"), 50.0, "User 2 should get $50 (ticket price)")

    @patch('app.core.database.db')
    def test_multiple_jackpot_winners(self, mock_db):
        """Test behavior when multiple people win the jackpot."""
        # Two users with winning numbers
        mock_db.get_all_tickets_for_draw.return_value = [
            {"user_id": 1, "username": "winner1", "id": 101, "numbers": [1, 2, 3, 4, 5, 6]},
            {"user_id": 2, "username": "winner2", "id": 102, "numbers": [1, 2, 3, 4, 5, 6]}
        ]
        current_jackpot = 1000000.0 # 1 Million
        mock_db.get_lottery_jackpot.return_value = {"current_amount": current_jackpot, "no_winner_months": 0}
        
        # Mock winning numbers
        with patch.object(self.lottery, 'generate_winning_numbers', return_value=[1, 2, 3, 4, 5, 6]):
            with patch.object(self.lottery, '_get_config', return_value=self.mock_config):
                
                results = self.lottery.perform_draw()
                
                # Check winners list
                winners = results["winners"]
                jackpot_winners = [w for w in winners if w["prize_type"] == "jackpot"]
                
                self.assertEqual(len(jackpot_winners), 2, "Should be 2 jackpot winners")
                
                # Verify both are marked as jackpot winners with FULL amount (or however logic handles it)
                # Looking at code: it sets prize_type="jackpot" and amount=current_jackpot
                # It does NOT split it in the result dictionary. This is important to note for the user.
                for w in jackpot_winners:
                    self.assertEqual(w["amount"], current_jackpot)
                
                # Verify jackpot reset happen ONCE (or consistent state)
                # It should reset because winners exist
                mock_db.update_lottery_jackpot.assert_called()
                # Check arguments - should reset to initial
                call_args = mock_db.update_lottery_jackpot.call_args
                self.assertEqual(call_args.kwargs.get("amount"), 10000.0, "Jackpot should reset to initial")
                self.assertEqual(call_args.kwargs.get("no_winner_months"), 0)

if __name__ == '__main__':
    unittest.main()
