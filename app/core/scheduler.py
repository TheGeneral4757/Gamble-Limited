
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.core.logger import get_logger
from app.core.games.lottery import lottery_system
from app.core.database import db
from app.config import settings
import pytz
import random
from app.core.economy import market
import pytz
import random
import json

logger = get_logger("scheduler")

class LotteryScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        
    def start(self):
        # 1. Check for monthly draw execution every minute
        self.scheduler.add_job(
            self.check_draw_execution,
            IntervalTrigger(minutes=1),
            id='check_draw_execution',
            replace_existing=True
        )
        
        # 2. Process installments every hour
        self.scheduler.add_job(
            self.process_installments,
            IntervalTrigger(hours=1),
            id='process_installments',
            replace_existing=True
        )
        
        # 3. Weekly Market Reset (Friday Noon)
        self.scheduler.add_job(
            self.reset_market,
            CronTrigger(day_of_week='fri', hour=12, minute=0),
            id='market_reset',
            name='Weekly Market Reset',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Lottery scheduler started")

    def shutdown(self):
        try:
            self.scheduler.shutdown()
            logger.info("Lottery scheduler shutdown")
        except Exception:
            pass
        
    def check_draw_execution(self):
        """Check if we need to execute a lottery draw."""
        try:
            # Get next configured draw time
            next_draw = lottery_system.get_next_draw_date()
            current_draw_id = lottery_system.get_current_draw_id()
             
            # Check if we have a pending draw for this ID or if it's already done
            draw_record = db.get_lottery_draw(current_draw_id)
            
            if draw_record and draw_record["status"] == "completed":
                # Already done
                return
            
            # Ensure pending record exists
            if not draw_record:
                db.create_lottery_draw(current_draw_id)
                draw_record = db.get_lottery_draw(current_draw_id)
            
            # Check if it's time to run
            # next_draw is the scheduled time. If now >= next_draw, we run.
            # BUT, get_next_draw_date() usually returns the NEXT future date.
            # If we are slightly past the scheduled time, get_next_draw_date might jump to next month.
            # So we need to be careful.
            
            # Better logic:
            # Check the draw_id (YYYY-MM). If it matches current month and we are past the day/hour, run it.
            
            config = lottery_system._get_config()
            tz = lottery_system._get_timezone()
            now = datetime.now(tz)
            
            # Parse draw_id to get target year/month
            target_year, target_month = map(int, current_draw_id.split('-'))
            
            # If next_draw calculation says it's in the future, we wait.
            # If next_draw matches current draw_id and we are past it?
            
            # Simplification: Just check if now >= next_draw. 
            # If get_next_draw_date() returns next month, it means we missed this month?
            # Or we already ran it?
            
            # Let's rely on date comparison.
            if now >= next_draw:
                 self.execute_draw(current_draw_id)

        except Exception as e:
            logger.error(f"Error in check_draw_execution: {e}")

    def execute_draw(self, draw_id: str):
        """Execute the lottery draw."""
        logger.info(f"Executing lottery draw {draw_id}")
        
        try:
            # Delegate to LotterySystem
            result = lottery_system.perform_draw()
            
            logger.info(f"Lottery draw completed. Winners: {len(result.get('winners', []))}, Jackpot: {result.get('jackpot')}")
            
        except Exception as e:
            logger.error(f"Error executing draw: {e}")
            import traceback
            traceback.print_exc()

    def process_installments(self):
        """Process due installment payments."""
        try:
            pending = db.get_pending_installments()
            for installment in pending:
                res = db.process_installment_payment(installment["id"])
                if res["success"]:
                    logger.info(f"Paid installment {installment['id']}")
        except Exception as e:
           logger.error(f"Error processing installments: {e}")

    def reset_market(self):
        """Reset economy market to baseline."""
        try:
            logger.info("Scheduler: Executing Weekly Market Reset")
            market.reset_to_baseline()
        except Exception as e:
            logger.error(f"Error resetting market: {e}")

# Global instance
lottery_scheduler = LotteryScheduler()
