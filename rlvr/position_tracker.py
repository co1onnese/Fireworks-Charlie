"""
Position tracking for RLVR reward calculation
Manages 3-day holds with early exit logic
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PositionTracker:
    """
    Tracks positions for RLVR reward function calculation

    Implements:
    - 3-trading-day hold period
    - Early exit if signal changes to hold/sell/strong_sell on day 2 or 3
    - Uses regular close price (not adjusted close)
    - Delegates to database stored procedure for calculations
    """

    def __init__(
        self,
        db_session: Session,
        hold_days: int = 3,
        early_exit_enabled: bool = True
    ):
        """
        Initialize position tracker

        Args:
            db_session: SQLAlchemy database session
            hold_days: Number of trading days to hold (default: 3)
            early_exit_enabled: Enable early exit on signal change (default: True)
        """
        self.db_session = db_session
        self.hold_days = hold_days
        self.early_exit_enabled = early_exit_enabled

        logger.info(
            f"Initialized PositionTracker: {hold_days}-day hold, "
            f"early_exit={'enabled' if early_exit_enabled else 'disabled'}"
        )

    def track_position(
        self,
        ticker_id: int,
        entry_date: date,
        entry_price: float,
        predicted_action: str
    ) -> Optional[Dict[str, Any]]:
        """
        Track a position and calculate its return using database stored procedure

        This method calls the PostgreSQL calculate_position_return() function which:
        1. Iterates through trading days starting from entry_date
        2. Checks for signal changes on days 2-3 (if early_exit_enabled)
        3. Calculates return using regular close prices
        4. Returns comprehensive position performance metrics

        Args:
            ticker_id: Database ticker ID
            entry_date: Position entry date
            entry_price: Entry price (regular close)
            predicted_action: Predicted action (strong_buy, buy, hold, sell, strong_sell)

        Returns:
            Dictionary with:
            - exit_date: Date position was exited
            - exit_price: Exit price (regular close)
            - return_pct: Percentage return
            - days_held: Actual days held (1-3)
            - early_exit: Boolean indicating if exited early
            - early_exit_reason: Reason for early exit (if applicable)
            - metadata: Additional tracking info

            Returns None if insufficient data (e.g., no trading days available)
        """
        try:
            # Call database stored procedure
            result = self.db_session.execute(
                text("""
                SELECT * FROM calculate_position_return(
                    :ticker_id,
                    :entry_date,
                    :entry_price,
                    :predicted_action,
                    :hold_days
                )
                """),
                {
                    "ticker_id": ticker_id,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "predicted_action": predicted_action,
                    "hold_days": self.hold_days
                }
            ).fetchone()

            if not result:
                logger.warning(
                    f"No position return calculated for ticker_id={ticker_id}, "
                    f"entry_date={entry_date}. Likely insufficient data."
                )
                return None

            # Convert result to dictionary
            position_data = {
                "exit_date": result.exit_date,
                "exit_price": float(result.exit_price) if result.exit_price else None,
                "return_pct": float(result.return_pct) if result.return_pct else None,
                "days_held": result.days_held,
                "early_exit": result.early_exit,
                "early_exit_reason": result.early_exit_reason,
                "metadata": result.metadata or {}
            }

            logger.debug(
                f"Position tracked: ticker_id={ticker_id}, entry={entry_date}, "
                f"exit={position_data['exit_date']}, return={position_data['return_pct']:.2f}%, "
                f"days_held={position_data['days_held']}, early_exit={position_data['early_exit']}"
            )

            return position_data

        except Exception as e:
            logger.error(
                f"Error tracking position for ticker_id={ticker_id}, "
                f"entry_date={entry_date}: {e}"
            )
            return None

    def track_positions_batch(
        self,
        positions: List[Dict[str, Any]]
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Track multiple positions in batch

        Args:
            positions: List of dictionaries with keys:
                - ticker_id: int
                - entry_date: date
                - entry_price: float
                - predicted_action: str

        Returns:
            List of position tracking results (same order as input)
            None entries indicate positions that couldn't be tracked
        """
        results = []

        for i, position in enumerate(positions):
            logger.debug(f"Tracking position {i+1}/{len(positions)}")

            result = self.track_position(
                ticker_id=position["ticker_id"],
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                predicted_action=position["predicted_action"]
            )

            results.append(result)

        successful = sum(1 for r in results if r is not None)
        logger.info(
            f"Batch position tracking complete: {successful}/{len(positions)} successful"
        )

        return results

    def update_all_open_positions(self) -> Dict[str, Any]:
        """
        Update all open positions using database stored procedure

        Calls the update_all_open_positions() database function to:
        1. Find all positions that need updates
        2. Calculate their current performance
        3. Update the positions table

        Returns:
            Dictionary with update statistics:
            - positions_updated: Number of positions updated
            - positions_closed: Number of positions closed
            - errors: Number of errors encountered
        """
        try:
            result = self.db_session.execute(
                text("SELECT * FROM update_all_open_positions()")
            ).fetchone()

            stats = {
                "positions_updated": result.positions_updated,
                "positions_closed": result.positions_closed,
                "errors": result.errors
            }

            logger.info(
                f"Updated open positions: {stats['positions_updated']} updated, "
                f"{stats['positions_closed']} closed, {stats['errors']} errors"
            )

            return stats

        except Exception as e:
            logger.error(f"Error updating open positions: {e}")
            return {
                "positions_updated": 0,
                "positions_closed": 0,
                "errors": 1,
                "error_message": str(e)
            }

    def get_position_performance(
        self,
        ticker_id: int,
        entry_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing position performance from database

        Args:
            ticker_id: Database ticker ID
            entry_date: Position entry date

        Returns:
            Dictionary with position data from database, or None if not found
        """
        try:
            result = self.db_session.execute(
                text("""
                SELECT
                    entry_price,
                    exit_date,
                    exit_price,
                    predicted_action,
                    actual_return,
                    days_held,
                    early_exit,
                    early_exit_reason,
                    directional_accuracy,
                    metadata
                FROM positions
                WHERE ticker_id = :ticker_id
                  AND entry_date = :entry_date
                """),
                {"ticker_id": ticker_id, "entry_date": entry_date}
            ).fetchone()

            if not result:
                return None

            return {
                "entry_price": float(result.entry_price),
                "exit_date": result.exit_date,
                "exit_price": float(result.exit_price) if result.exit_price else None,
                "predicted_action": result.predicted_action,
                "actual_return": float(result.actual_return) if result.actual_return else None,
                "days_held": result.days_held,
                "early_exit": result.early_exit,
                "early_exit_reason": result.early_exit_reason,
                "directional_accuracy": result.directional_accuracy,
                "metadata": result.metadata or {}
            }

        except Exception as e:
            logger.error(
                f"Error getting position performance for ticker_id={ticker_id}, "
                f"entry_date={entry_date}: {e}"
            )
            return None

    def validate_position_data(
        self,
        ticker_id: int,
        entry_date: date,
        entry_price: float,
        predicted_action: str
    ) -> bool:
        """
        Validate position input data

        Args:
            ticker_id: Database ticker ID
            entry_date: Entry date
            entry_price: Entry price
            predicted_action: Predicted action

        Returns:
            True if valid, False otherwise
        """
        valid_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell"]

        if ticker_id <= 0:
            logger.error(f"Invalid ticker_id: {ticker_id}")
            return False

        if entry_price <= 0:
            logger.error(f"Invalid entry_price: {entry_price}")
            return False

        if predicted_action not in valid_actions:
            logger.error(
                f"Invalid predicted_action: {predicted_action}. "
                f"Must be one of: {', '.join(valid_actions)}"
            )
            return False

        return True
