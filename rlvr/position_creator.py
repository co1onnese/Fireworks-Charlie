"""
Position Creator for Pipeline Integration

This module provides utilities to create position records
during the thesis generation pipeline.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import logging
from typing import Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PositionCreator:
    """
    Creates position records in the database after thesis generation.

    This class is designed to be integrated into the main pipeline to
    automatically track positions as theses are generated.
    """

    def __init__(self, db_session: Session, hold_days: int = 3):
        """
        Initialize the position creator.

        Args:
            db_session: SQLAlchemy database session
            hold_days: Number of days to hold position (default: 3)
        """
        self.db_session = db_session
        self.hold_days = hold_days

        logger.debug(f"Initialized PositionCreator with {hold_days}-day hold")

    def _has_sufficient_future_data(self, ticker_id: int, entry_date: date) -> bool:
        """
        Check if we have enough future market data for position calculation.

        Args:
            ticker_id: The ticker ID
            entry_date: Position entry date

        Returns:
            True if sufficient future data exists, False otherwise
        """
        try:
            # Get latest market data date
            result = self.db_session.execute(
                text("SELECT MAX(date) FROM market_data")
            ).fetchone()

            if not result or not result[0]:
                logger.debug("No market data found - cannot create position")
                return False

            latest_market_date = result[0]
            required_end_date = entry_date + timedelta(days=self.hold_days)

            has_sufficient_data = required_end_date <= latest_market_date

            if not has_sufficient_data:
                logger.debug(
                    f"Insufficient future data for position: "
                    f"entry_date={entry_date}, required_end_date={required_end_date}, "
                    f"latest_market_date={latest_market_date}"
                )

            return has_sufficient_data

        except Exception as e:
            logger.error(f"Error checking future data availability: {e}")
            return False

    def create_position_for_thesis(
        self,
        thesis_id: int,
        ticker_id: int,
        entry_date: date,
        predicted_action: str,
        defer_commit: bool = False
    ) -> Optional[int]:
        """
        Create a position record for a thesis generation.

        This is designed to be called immediately after a thesis is saved.
        It calculates the position return and stores it in the positions table.

        Args:
            thesis_id: The thesis generation ID
            ticker_id: The ticker ID
            entry_date: Position entry date (same as thesis as_of_date)
            predicted_action: Predicted action from thesis
            defer_commit: If True, don't commit (let caller handle transaction)

        Returns:
            Position ID if successful, None otherwise
        """
        try:
            # Check if we have sufficient future data for position calculation
            if not self._has_sufficient_future_data(ticker_id, entry_date):
                logger.debug(
                    f"Skipping position creation for ticker_id={ticker_id}, "
                    f"entry_date={entry_date} - insufficient future data"
                )
                return None

            logger.debug(f"DEBUG: Position validation passed for ticker_id={ticker_id}, entry_date={entry_date}")

            # Get entry price from market_data
            entry_price_query = self.db_session.execute(
                text("""
                    SELECT close
                    FROM market_data
                    WHERE ticker_id = :ticker_id
                      AND date = :entry_date
                """),
                {"ticker_id": ticker_id, "entry_date": entry_date}
            ).fetchone()

            if not entry_price_query or not entry_price_query.close:
                logger.debug(
                    f"No entry price found for ticker_id={ticker_id}, "
                    f"entry_date={entry_date} - position not created"
                )
                return None

            entry_price = float(entry_price_query.close)

            # Calculate position return using database stored procedure
            logger.debug(f"DEBUG: Calling calculate_position_return for ticker_id={ticker_id}, entry_date={entry_date}")
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

            logger.debug(f"DEBUG: Database function result: {result}")

            if not result:
                logger.debug(
                    f"No position return calculated for ticker_id={ticker_id}, "
                    f"entry_date={entry_date} (likely insufficient future data)"
                )
                return None

            # Calculate directional accuracy
            return_pct = float(result.return_pct) if result and result.return_pct else 0.0

            accuracy_result = self.db_session.execute(
                text("""
                    SELECT * FROM check_directional_accuracy(
                        :action,
                        :actual_return
                    )
                """),
                {
                    "action": predicted_action,
                    "actual_return": return_pct
                }
            ).fetchone()

            accuracy_score = float(accuracy_result.accuracy_score) if accuracy_result else 0.0
            met_threshold = accuracy_result.met_threshold if accuracy_result else False

            # Insert position record
            insert_result = self.db_session.execute(
                text("""
                    INSERT INTO positions (
                        ticker_id,
                        entry_date,
                        entry_price,
                        exit_date,
                        exit_price,
                        predicted_action,
                        actual_return_pct,
                        days_held,
                        early_exit,
                        early_exit_reason,
                        directional_accuracy_score,
                        met_threshold,
                        thesis_id,
                        status,
                        created_at,
                        updated_at
                    ) VALUES (
                        :ticker_id,
                        :entry_date,
                        :entry_price,
                        :exit_date,
                        :exit_price,
                        :predicted_action,
                        :actual_return_pct,
                        :days_held,
                        :early_exit,
                        :early_exit_reason,
                        :directional_accuracy_score,
                        :met_threshold,
                        :thesis_id,
                        :status,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (ticker_id, entry_date) DO UPDATE
                    SET
                        exit_date = EXCLUDED.exit_date,
                        exit_price = EXCLUDED.exit_price,
                        actual_return_pct = EXCLUDED.actual_return_pct,
                        days_held = EXCLUDED.days_held,
                        early_exit = EXCLUDED.early_exit,
                        early_exit_reason = EXCLUDED.early_exit_reason,
                        directional_accuracy_score = EXCLUDED.directional_accuracy_score,
                        met_threshold = EXCLUDED.met_threshold,
                        thesis_id = EXCLUDED.thesis_id,
                        status = EXCLUDED.status,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING position_id
                """),
                {
                    "ticker_id": ticker_id,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": result.exit_date if result else None,
                    "exit_price": float(result.exit_price) if result and result.exit_price else None,
                    "predicted_action": predicted_action,
                    "actual_return_pct": return_pct,
                    "days_held": result.days_held if result else 0,
                    "early_exit": result.early_exit if result else False,
                    "early_exit_reason": result.early_exit_reason if result else None,
                    "directional_accuracy_score": accuracy_score,
                    "met_threshold": met_threshold,
                    "thesis_id": thesis_id,
                    "status": "closed"
                }
            )

            position_id = insert_result.fetchone()[0]

            if not defer_commit:
                self.db_session.commit()

            logger.debug(
                f"Created position {position_id} for thesis {thesis_id}: "
                f"return={return_pct:.2f}%, accuracy={accuracy_score:.2f}, threshold={met_threshold}"
            )

            return position_id

        except Exception as e:
            logger.error(
                f"Error creating position for thesis {thesis_id}: {e}",
                exc_info=True
            )
            if not defer_commit:
                self.db_session.rollback()
            return None


def create_position_after_thesis(
    db_session: Session,
    thesis_id: int,
    ticker_id: int,
    entry_date: date,
    predicted_action: str
) -> Optional[int]:
    """
    Standalone function to create a position after thesis generation.

    This is a convenience function that can be called directly from
    the pipeline without instantiating PositionCreator.

    Args:
        db_session: SQLAlchemy database session
        thesis_id: The thesis generation ID
        ticker_id: The ticker ID
        entry_date: Position entry date
        predicted_action: Predicted action from thesis

    Returns:
        Position ID if successful, None otherwise
    """
    creator = PositionCreator(db_session)
    return creator.create_position_for_thesis(
        thesis_id=thesis_id,
        ticker_id=ticker_id,
        entry_date=entry_date,
        predicted_action=predicted_action,
        defer_commit=False
    )


__all__ = ["PositionCreator", "create_position_after_thesis"]
