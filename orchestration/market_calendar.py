"""
Market calendar utilities for identifying trading days
"""
from datetime import date, datetime, timedelta
from typing import List, Set
import pandas as pd
import pandas_market_calendars as mcal
import logging

logger = logging.getLogger(__name__)

class MarketCalendar:
    """Handles market calendar operations for trading day detection"""
    
    def __init__(self, calendar_name: str = "NYSE"):
        """
        Initialize market calendar
        
        Args:
            calendar_name: Name of the market calendar (e.g., "NYSE", "NASDAQ", "LSE")
        """
        self.calendar_name = calendar_name
        try:
            self.calendar = mcal.get_calendar(calendar_name)
            logger.info(f"Initialized {calendar_name} market calendar")
        except Exception as e:
            logger.warning(f"Failed to load {calendar_name} calendar: {e}. Using simple weekday logic.")
            self.calendar = None
    
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """
        Get list of trading days between start and end dates (inclusive)
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of trading days
        """
        if self.calendar:
            try:
                # Get trading days from market calendar
                schedule = self.calendar.schedule(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                trading_days = [d.date() for d in schedule.index]
                logger.info(f"Found {len(trading_days)} trading days from {start_date} to {end_date}")
                return trading_days
            except Exception as e:
                logger.warning(f"Error getting trading days from calendar: {e}. Falling back to weekday logic.")
        
        # Fallback: simple weekday logic (Monday-Friday)
        trading_days = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        logger.info(f"Found {len(trading_days)} weekdays from {start_date} to {end_date}")
        return trading_days
    
    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if a specific date is a trading day
        
        Args:
            check_date: Date to check
            
        Returns:
            True if trading day, False otherwise
        """
        if self.calendar:
            try:
                schedule = self.calendar.schedule(
                    start_date=check_date.strftime('%Y-%m-%d'),
                    end_date=check_date.strftime('%Y-%m-%d')
                )
                return len(schedule) > 0
            except Exception as e:
                logger.warning(f"Error checking trading day: {e}")
        
        # Fallback to weekday check
        return check_date.weekday() < 5
    
    def get_previous_trading_day(self, from_date: date) -> date:
        """
        Get the previous trading day before the given date
        
        Args:
            from_date: Reference date
            
        Returns:
            Previous trading day
        """
        current_date = from_date - timedelta(days=1)
        while not self.is_trading_day(current_date):
            current_date -= timedelta(days=1)
        return current_date
    
    def get_next_trading_day(self, from_date: date) -> date:
        """
        Get the next trading day after the given date
        
        Args:
            from_date: Reference date
            
        Returns:
            Next trading day
        """
        current_date = from_date + timedelta(days=1)
        while not self.is_trading_day(current_date):
            current_date += timedelta(days=1)
        return current_date
    
    def get_major_holidays(self, year: int) -> Set[date]:
        """
        Get major market holidays for a given year
        
        Args:
            year: Year to get holidays for
            
        Returns:
            Set of holiday dates
        """
        if self.calendar:
            try:
                # Get all non-trading days for the year
                start = f"{year}-01-01"
                end = f"{year}-12-31"
                all_days = pd.date_range(start=start, end=end, freq='D')
                schedule = self.calendar.schedule(start_date=start, end_date=end)
                trading_days = set(d.date() for d in schedule.index)
                all_days_set = set(d.date() for d in all_days)
                
                # Holidays are weekdays that are not trading days
                holidays = set()
                for d in all_days_set - trading_days:
                    if d.weekday() < 5:  # Only weekdays
                        holidays.add(d)
                
                return holidays
            except Exception as e:
                logger.warning(f"Error getting holidays: {e}")
        
        # Return empty set if no calendar available
        return set()