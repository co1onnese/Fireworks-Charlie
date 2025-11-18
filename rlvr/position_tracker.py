"""
Position Tracker for RLVR Training Pipeline

Handles 3-day position tracking with early exit logic for measuring
actual returns on stock predictions.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session
from data_collection.database_manager import Position, MarketData, Ticker
from orchestration.market_calendar import MarketCalendar

logger = logging.getLogger(__name__)


class PositionTracker:
    """
    3-day position tracking with early exit logic.

    Tracks stock positions from entry to exit (3 trading days by default,
    or earlier if early exit conditions are met).

    Logic:
    1. Entry: entry_date + entry_price (regular close)
    2. Hold: 3 trading days OR early exit if signal changes
    3. Exit: exit_date + exit_price (regular close)
    4. Return: (exit_price - entry_price) / entry_price × 100
    """

    def __init__(self, db_session: Session, hold_days: int = 3, early_exit_enabled: bool = True):
        """
        Initialize position tracker.

        Args:
            db_session: SQLAlchemy database session
            hold_days: Number of trading days to hold position (default: 3)
            early_exit_enabled: Whether to enable early exit logic (default: True)
        """
        self.db_session = db_session
        self.hold_days = hold_days
        self.early_exit_enabled = early_exit_enabled
        self.market_calendar = MarketCalendar()
        self.logger = logging.getLogger(__name__)

    def track_position(
        self,
        ticker_id: int,
        entry_date: date,
        entry_price: float,
        predicted_action: str
    ) -> Optional[Dict[str, Any]]:
        """
        Track a single position from entry to exit.

        Args:
            ticker_id: Ticker ID from database
            entry_date: Date position was entered
            entry_price: Price at entry
            predicted_action: Predicted action (buy/sell/hold/etc.)

        Returns:
            Dictionary with position data, or None if tracking failed
        """
        try:
            # Validate inputs
            if not self.validate_position_data(ticker_id, entry_date, entry_price, predicted_action):
                self.logger.error(f"Invalid position data for ticker_id {ticker_id}, entry_date {entry_date}")
                return None

            # Get ticker symbol for logging
            ticker = self.db_session.query(Ticker).filter_by(ticker_id=ticker_id).first()
            if not ticker:
                self.logger.error(f"Ticker ID {ticker_id} not found")
                return None

            symbol = ticker.symbol

            # Calculate exit date (3 trading days later, or adjusted for early exit)
            target_exit_date = self.market_calendar.get_next_trading_day(entry_date)
            for _ in range(self.hold_days - 1):  # Already got next day
                target_exit_date = self.market_calendar.get_next_trading_day(target_exit_date)

            # Get market data for exit
            exit_data = self.db_session.query(MarketData).filter(
                MarketData.ticker_id == ticker_id,
                MarketData.date == target_exit_date
            ).first()

            if not exit_data:
                self.logger.warning(f"No market data for {symbol} on exit date {target_exit_date}")
                return None

            exit_price = float(exit_data.close)
            actual_return_pct = ((exit_price - entry_price) / entry_price) * 100.0

            # Check for early exit
            early_exit = False
            early_exit_reason = None

            if self.early_exit_enabled:
                # Early exit if return exceeds strong thresholds
                if actual_return_pct >= 5.0:  # Strong positive
                    early_exit = True
                    early_exit_reason = f"Strong profit ({actual_return_pct:.2f}%)"
                elif actual_return_pct <= -5.0:  # Strong negative
                    early_exit = True
                    early_exit_reason = f"Strong loss ({actual_return_pct:.2f}%)"

            # Calculate performance metrics
            days_held = (target_exit_date - entry_date).days

            position_result = {
                "ticker_id": ticker_id,
                "ticker": symbol,
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_date": target_exit_date,
                "exit_price": exit_price,
                "actual_return_pct": actual_return_pct,
                "predicted_action": predicted_action,
                "days_held": days_held,
                "early_exit": early_exit,
                "early_exit_reason": early_exit_reason,
                "status": "completed"
            }

            self.logger.info(
                f"Position tracked for {symbol}: {predicted_action} "
                f"from {entry_date} to {target_exit_date} = {actual_return_pct:.2f}% "
                f"{'(early exit)' if early_exit else ''}"
            )

            return position_result

        except Exception as e:
            self.logger.error(f"Error tracking position: {e}", exc_info=True)
            return None

    def track_positions_batch(self, positions: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
        """
        Track multiple positions in batch.

        Args:
            positions: List of position dictionaries with keys:
                      ticker_id, entry_date, entry_price, predicted_action

        Returns:
            List of position results (same order as input)
        """
        results = []

        for pos in positions:
            result = self.track_position(
                ticker_id=pos["ticker_id"],
                entry_date=pos["entry_date"],
                entry_price=pos["entry_price"],
                predicted_action=pos["predicted_action"]
            )
            results.append(result)

        return results

    def update_all_open_positions(self) -> Dict[str, Any]:
        """
        Update all open positions in the database.

        Returns:
            Dictionary with update statistics
        """
        try:
            # Query all open positions
            open_positions = self.db_session.query(Position).filter(
                Position.exit_date.is_(None)
            ).all()

            if not open_positions:
                return {"updated": 0, "skipped": 0, "errors": 0}

            updated = 0
            errors = 0

            for position in open_positions:
                try:
                    # Track the position and update
                    result = self.track_position(
                        ticker_id=position.ticker_id,
                        entry_date=position.entry_date,
                        entry_price=position.entry_price,
                        predicted_action=position.predicted_action
                    )

                    if result:
                        # Update position record
                        position.exit_date = result["exit_date"]
                        position.exit_price = result["exit_price"]
                        position.actual_return_pct = result["actual_return_pct"]
                        position.days_held = result["days_held"]
                        position.early_exit = result["early_exit"]
                        position.early_exit_reason = result["early_exit_reason"]
                        position.status = "closed"
                        updated += 1
                    else:
                        errors += 1

                except Exception as e:
                    self.logger.error(f"Error updating position {position.position_id}: {e}")
                    errors += 1

            self.db_session.commit()

            return {
                "updated": updated,
                "total_processed": len(open_positions),
                "errors": errors
            }

        except Exception as e:
            self.logger.error(f"Error updating all open positions: {e}", exc_info=True)
            self.db_session.rollback()
            return {"updated": 0, "skipped": 0, "errors": 1}

    def get_position_performance(self, ticker_id: int, entry_date: date) -> Optional[Dict[str, Any]]:
        """
        Get performance data for a specific position.

        Args:
            ticker_id: Ticker ID
            entry_date: Entry date

        Returns:
            Position performance dictionary or None if not found
        """
        position = self.db_session.query(Position).filter_by(
            ticker_id=ticker_id,
            entry_date=entry_date
        ).first()

        if not position:
            return None

        return {
            "position_id": position.position_id,
            "ticker_id": position.ticker_id,
            "entry_date": position.entry_date,
            "entry_price": float(position.entry_price),
            "exit_date": position.exit_date,
            "exit_price": float(position.exit_price) if position.exit_price else None,
            "predicted_action": position.predicted_action,
            "actual_return_pct": float(position.actual_return_pct) if position.actual_return_pct else None,
            "days_held": position.days_held,
            "early_exit": position.early_exit,
            "early_exit_reason": position.early_exit_reason,
            "status": position.status
        }

    def validate_position_data(
        self,
        ticker_id: int,
        entry_date: date,
        entry_price: float,
        predicted_action: str
    ) -> bool:
        """
        Validate position tracking inputs.

        Args:
            ticker_id: Ticker ID
            entry_date: Entry date
            entry_price: Entry price
            predicted_action: Predicted action

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(ticker_id, int) or ticker_id <= 0:
            self.logger.error(f"Invalid ticker_id: {ticker_id}")
            return False

        if not isinstance(entry_date, date):
            self.logger.error(f"Invalid entry_date type: {type(entry_date)}")
            return False

        if not isinstance(entry_price, (int, float)) or entry_price <= 0:
            self.logger.error(f"Invalid entry_price: {entry_price}")
            return False

        if not predicted_action or not isinstance(predicted_action, str):
            self.logger.error(f"Invalid predicted_action: {predicted_action}")
            return False

        return True
