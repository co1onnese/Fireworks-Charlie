#!/usr/bin/env python3
"""
Backfill Positions Script

This script creates position records for all existing thesis generations.
It calculates the 3-day position returns and stores them in the positions table.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
import os
import logging
from typing import Dict, List
from datetime import datetime, date
from decimal import Decimal

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.database_manager import DatabaseManager
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_thesis_without_positions(db_manager: DatabaseManager) -> List[Dict]:
    """
    Get all thesis generations that don't have corresponding position records.

    Returns:
        List of thesis records without positions
    """
    logger.info("Querying thesis generations without positions...")
    session = db_manager.get_session()

    try:
        query = text("""
            SELECT
                tg.thesis_id,
                tg.ticker_id,
                t.symbol,
                tg.as_of_date,
                tg.predicted_action,
                tg.generated_at
            FROM thesis_generations tg
            JOIN tickers t ON tg.ticker_id = t.ticker_id
            LEFT JOIN positions p ON (
                p.ticker_id = tg.ticker_id
                AND p.entry_date = tg.as_of_date
            )
            WHERE p.position_id IS NULL
              AND tg.predicted_action IS NOT NULL
              AND tg.status = 'success'
            ORDER BY tg.as_of_date, t.symbol
        """)

        result = session.execute(query).fetchall()
        theses = [dict(row._mapping) for row in result]

        logger.info(f"Found {len(theses)} thesis generations without positions")
        return theses

    finally:
        session.close()


def calculate_and_insert_position(
    db_manager: DatabaseManager,
    thesis_id: int,
    ticker_id: int,
    symbol: str,
    entry_date: date,
    predicted_action: str
) -> bool:
    """
    Calculate position return and insert into positions table.

    Args:
        db_manager: Database manager instance
        thesis_id: Thesis generation ID
        ticker_id: Ticker ID
        symbol: Ticker symbol
        entry_date: Position entry date
        predicted_action: Predicted action

    Returns:
        True if successful, False otherwise
    """
    session = db_manager.get_session()

    try:
        # Get entry price from market_data
        entry_price_query = session.execute(
            text("""
                SELECT close
                FROM market_data
                WHERE ticker_id = :ticker_id
                  AND date = :entry_date
            """),
            {"ticker_id": ticker_id, "entry_date": entry_date}
        ).fetchone()

        if not entry_price_query or not entry_price_query.close:
            logger.warning(f"No entry price for {symbol} on {entry_date}")
            return False

        entry_price = float(entry_price_query.close)

        # Calculate position return using database stored procedure
        result = session.execute(
            text("""
                SELECT * FROM calculate_position_return(
                    :ticker_id,
                    :entry_date,
                    :entry_price,
                    :predicted_action,
                    3
                )
            """),
            {
                "ticker_id": ticker_id,
                "entry_date": entry_date,
                "entry_price": entry_price,
                "predicted_action": predicted_action
            }
        ).fetchone()

        if not result:
            logger.debug(f"No position return calculated for {symbol} on {entry_date} (insufficient future data)")
            return False

        # Calculate directional accuracy
        return_pct = float(result.return_pct) if result.return_pct else 0.0

        accuracy_result = session.execute(
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
        insert_result = session.execute(
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
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING position_id
            """),
            {
                "ticker_id": ticker_id,
                "entry_date": entry_date,
                "entry_price": entry_price,
                "exit_date": result.exit_date,
                "exit_price": float(result.exit_price) if result.exit_price else None,
                "predicted_action": predicted_action,
                "actual_return_pct": return_pct,
                "days_held": result.days_held,
                "early_exit": result.early_exit,
                "early_exit_reason": result.early_exit_reason,
                "directional_accuracy_score": accuracy_score,
                "met_threshold": met_threshold,
                "thesis_id": thesis_id,
                "status": "closed"
            }
        )

        position_id = insert_result.fetchone()[0]
        session.commit()

        logger.debug(
            f"✓ Created position {position_id} for {symbol} on {entry_date}: "
            f"return={return_pct:.2f}%, accuracy={accuracy_score:.2f}, threshold={met_threshold}"
        )

        return True

    except Exception as e:
        logger.error(f"Error creating position for {symbol} on {entry_date}: {e}")
        session.rollback()
        return False

    finally:
        session.close()


def backfill_positions(
    db_manager: DatabaseManager,
    batch_size: int = 100,
    dry_run: bool = True
) -> Dict:
    """
    Backfill positions for all thesis generations.

    Args:
        db_manager: Database manager instance
        batch_size: Number of positions to process before committing
        dry_run: If True, only show what would be created

    Returns:
        Statistics dictionary
    """
    stats = {
        "total_theses": 0,
        "positions_created": 0,
        "skipped_no_price": 0,
        "skipped_no_future_data": 0,
        "errors": 0
    }

    # Get all theses without positions
    theses = get_thesis_without_positions(db_manager)
    stats["total_theses"] = len(theses)

    if not theses:
        logger.info("No theses found that need position backfill")
        return stats

    if dry_run:
        logger.info(f"DRY RUN MODE - Would process {len(theses)} theses")

        # Show sample
        logger.info("\nSample theses to process:")
        for thesis in theses[:10]:
            logger.info(
                f"  - {thesis['symbol']:6s} {thesis['as_of_date']} "
                f"action={thesis['predicted_action']}"
            )

        if len(theses) > 10:
            logger.info(f"  ... and {len(theses) - 10} more")

        logger.info("\nTo execute backfill, run with --execute flag")
        return stats

    # Process theses in batches
    logger.info(f"Processing {len(theses)} theses...")

    for i, thesis in enumerate(theses, 1):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(theses)} ({i*100//len(theses)}%)")

        success = calculate_and_insert_position(
            db_manager=db_manager,
            thesis_id=thesis['thesis_id'],
            ticker_id=thesis['ticker_id'],
            symbol=thesis['symbol'],
            entry_date=thesis['as_of_date'],
            predicted_action=thesis['predicted_action']
        )

        if success:
            stats["positions_created"] += 1
        else:
            # Could be either no price or no future data
            stats["skipped_no_future_data"] += 1

    logger.info(
        f"Backfill complete: {stats['positions_created']} positions created, "
        f"{stats['skipped_no_future_data']} skipped (no future data)"
    )

    return stats


def verify_backfill(db_manager: DatabaseManager) -> bool:
    """
    Verify that all thesis generations have corresponding positions.

    Returns:
        True if verification passes, False otherwise
    """
    logger.info("Verifying backfill...")
    session = db_manager.get_session()

    try:
        # Count theses without positions (excluding those without future data)
        query = text("""
            SELECT COUNT(*)
            FROM thesis_generations tg
            LEFT JOIN positions p ON (
                p.ticker_id = tg.ticker_id
                AND p.entry_date = tg.as_of_date
            )
            WHERE p.position_id IS NULL
              AND tg.predicted_action IS NOT NULL
              AND tg.status = 'success'
              AND tg.as_of_date < CURRENT_DATE - INTERVAL '3 days'
        """)

        result = session.execute(query).scalar()

        if result == 0:
            logger.info("✓ Verification passed - All eligible theses have positions")
            return True
        else:
            logger.warning(f"⚠ {result} theses still don't have positions")
            return False

    finally:
        session.close()


def main():
    """Main backfill function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backfill position records for existing thesis generations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (shows what would be created)
  python scripts/backfill_positions.py

  # Execute backfill
  python scripts/backfill_positions.py --execute

  # Skip confirmation
  python scripts/backfill_positions.py --execute --yes
        """
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the backfill (default is dry-run)'
    )

    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of positions to process before committing (default: 100)'
    )

    args = parser.parse_args()

    print("📊 Position Backfill Utility")
    print("="*80)

    # Initialize database
    db_manager = DatabaseManager(config.DB_URL)

    # Get count of theses without positions
    theses = get_thesis_without_positions(db_manager)

    print(f"\nFound {len(theses)} thesis generations without position records")

    if len(theses) == 0:
        print("✓ No backfill needed - all theses have positions")
        sys.exit(0)

    # Confirm if executing
    if args.execute and not args.yes:
        print("\n⚠️  This will create position records for all thesis generations")
        print("   - Position returns will be calculated using market data")
        print("   - This may take several minutes for large datasets")
        print()

        response = input(f"Create {len(theses)} position records? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Backfill cancelled")
            sys.exit(0)

    # Execute backfill
    stats = backfill_positions(
        db_manager=db_manager,
        batch_size=args.batch_size,
        dry_run=not args.execute
    )

    print("\n" + "="*80)
    print("BACKFILL STATISTICS")
    print("="*80)
    print(f"Total theses processed:    {stats['total_theses']}")
    print(f"Positions created:         {stats['positions_created']}")
    print(f"Skipped (no future data):  {stats['skipped_no_future_data']}")
    print(f"Errors:                    {stats['errors']}")
    print("="*80)

    # Verify if executed
    if args.execute:
        if verify_backfill(db_manager):
            print("\n✅ Position backfill completed successfully!")
        else:
            print("\n⚠️  Some theses still don't have positions")
            print("   This is normal for recent theses (last 3 days)")

    print()


if __name__ == "__main__":
    main()
