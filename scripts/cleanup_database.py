#!/usr/bin/env python3
"""
Database Cleanup Script - Remove Test/Sample Tickers

This script safely removes test and sample tickers from the database,
keeping only the production tickers defined in .env (NFLX, XOM, MA, HD, SBUX).

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
import os
import logging
from typing import List, Dict
from datetime import datetime

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


# Production tickers from .env
PRODUCTION_TICKERS = ['NFLX', 'XOM', 'MA', 'HD', 'SBUX']

# Tickers to DELETE (based on analysis)
TICKERS_TO_DELETE = [
    'AAPL',      # ID 1  - Test data (4 theses, 139 news)
    'DIS',       # ID 3  - Test data (33 theses) ⚠️
    'JPM',       # ID 5  - Empty test data
    'NVDA',      # ID 7  - Empty test data
    'MSFT',      # ID 8  - Empty test data
    'AMZN',      # ID 9  - Empty test data
    'META',      # ID 10 - Empty test data
    'NFLX,XOM'   # ID 13 - Malformed ticker ⚠️
]


def verify_production_tickers(db_manager: DatabaseManager) -> bool:
    """
    Verify that all production tickers exist in the database.

    Returns:
        True if all production tickers exist, False otherwise
    """
    logger.info("Verifying production tickers...")
    session = db_manager.get_session()

    try:
        result = session.execute(
            text("SELECT symbol FROM tickers WHERE symbol = ANY(:symbols)"),
            {"symbols": PRODUCTION_TICKERS}
        ).fetchall()

        found_tickers = {row.symbol for row in result}
        missing_tickers = set(PRODUCTION_TICKERS) - found_tickers

        if missing_tickers:
            logger.error(f"❌ Missing production tickers: {missing_tickers}")
            return False

        logger.info(f"✓ All {len(PRODUCTION_TICKERS)} production tickers found")
        return True

    finally:
        session.close()


def get_ticker_statistics(db_manager: DatabaseManager) -> Dict:
    """
    Get detailed statistics for all tickers.

    Returns:
        Dictionary with ticker statistics
    """
    logger.info("Getting ticker statistics...")
    session = db_manager.get_session()

    try:
        query = text("""
            SELECT
                t.symbol,
                t.ticker_id,
                (SELECT COUNT(*) FROM market_data WHERE ticker_id = t.ticker_id) as market_data,
                (SELECT COUNT(*) FROM fundamentals WHERE ticker_id = t.ticker_id) as fundamentals,
                (SELECT COUNT(*) FROM news WHERE ticker_id = t.ticker_id) as news,
                (SELECT COUNT(*) FROM insider_transactions WHERE ticker_id = t.ticker_id) as insider_txns,
                (SELECT COUNT(*) FROM thesis_generations WHERE ticker_id = t.ticker_id) as theses,
                (SELECT COUNT(*) FROM positions WHERE ticker_id = t.ticker_id) as positions
            FROM tickers t
            ORDER BY t.symbol
        """)

        result = session.execute(query).fetchall()

        stats = {
            'tickers': [],
            'production': {'market_data': 0, 'fundamentals': 0, 'news': 0, 'theses': 0},
            'to_delete': {'market_data': 0, 'fundamentals': 0, 'news': 0, 'theses': 0}
        }

        for row in result:
            ticker_data = {
                'symbol': row.symbol,
                'ticker_id': row.ticker_id,
                'market_data': row.market_data,
                'fundamentals': row.fundamentals,
                'news': row.news,
                'insider_txns': row.insider_txns,
                'theses': row.theses,
                'positions': row.positions
            }
            stats['tickers'].append(ticker_data)

            # Categorize
            if row.symbol in PRODUCTION_TICKERS:
                stats['production']['market_data'] += row.market_data
                stats['production']['fundamentals'] += row.fundamentals
                stats['production']['news'] += row.news
                stats['production']['theses'] += row.theses
            elif row.symbol in TICKERS_TO_DELETE:
                stats['to_delete']['market_data'] += row.market_data
                stats['to_delete']['fundamentals'] += row.fundamentals
                stats['to_delete']['news'] += row.news
                stats['to_delete']['theses'] += row.theses

        return stats

    finally:
        session.close()


def print_statistics(stats: Dict):
    """Print formatted statistics."""
    print("\n" + "="*80)
    print("DATABASE CLEANUP ANALYSIS")
    print("="*80)

    print(f"\n{'Symbol':<12} {'ID':<5} {'Market Data':<12} {'Fundamentals':<13} {'News':<8} {'Theses':<8} {'Action'}")
    print("-"*80)

    for ticker in stats['tickers']:
        action = "KEEP" if ticker['symbol'] in PRODUCTION_TICKERS else "DELETE"
        marker = "✓" if action == "KEEP" else "✗"

        print(
            f"{marker} {ticker['symbol']:<10} "
            f"{ticker['ticker_id']:<5} "
            f"{ticker['market_data']:<12} "
            f"{ticker['fundamentals']:<13} "
            f"{ticker['news']:<8} "
            f"{ticker['theses']:<8} "
            f"{action}"
        )

    print("-"*80)
    print(f"\n{'KEEP (Production)':<20} "
          f"{stats['production']['market_data']:<12} "
          f"{stats['production']['fundamentals']:<13} "
          f"{stats['production']['news']:<8} "
          f"{stats['production']['theses']:<8}")

    print(f"{'DELETE (Test/Sample)':<20} "
          f"{stats['to_delete']['market_data']:<12} "
          f"{stats['to_delete']['fundamentals']:<13} "
          f"{stats['to_delete']['news']:<8} "
          f"{stats['to_delete']['theses']:<8}")

    print("="*80)


def cleanup_database(db_manager: DatabaseManager, dry_run: bool = True) -> bool:
    """
    Clean up database by removing test/sample tickers.

    Args:
        db_manager: Database manager instance
        dry_run: If True, only show what would be deleted (default: True)

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting database cleanup (dry_run={dry_run})...")
    session = db_manager.get_session()

    try:
        # Get ticker IDs to delete
        result = session.execute(
            text("SELECT ticker_id, symbol FROM tickers WHERE symbol = ANY(:symbols)"),
            {"symbols": TICKERS_TO_DELETE}
        ).fetchall()

        tickers_to_delete = [(row.ticker_id, row.symbol) for row in result]

        if not tickers_to_delete:
            logger.warning("No tickers found to delete")
            return True

        logger.info(f"Found {len(tickers_to_delete)} tickers to delete:")
        for ticker_id, symbol in tickers_to_delete:
            logger.info(f"  - {symbol} (ID: {ticker_id})")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("To execute cleanup, run with --execute flag")
            return True

        # Execute deletion in transaction
        logger.info("Executing deletion (CASCADE will remove all related data)...")

        # Delete tickers (CASCADE will handle related tables)
        ticker_ids = [tid for tid, _ in tickers_to_delete]
        result = session.execute(
            text("DELETE FROM tickers WHERE ticker_id = ANY(:ticker_ids)"),
            {"ticker_ids": ticker_ids}
        )

        deleted_count = result.rowcount
        logger.info(f"✓ Deleted {deleted_count} tickers")

        # Commit transaction
        session.commit()
        logger.info("✓ Transaction committed successfully")

        return True

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        session.rollback()
        logger.info("✓ Transaction rolled back")
        return False

    finally:
        session.close()


def verify_cleanup(db_manager: DatabaseManager) -> bool:
    """
    Verify that cleanup was successful.

    Returns:
        True if only production tickers remain, False otherwise
    """
    logger.info("Verifying cleanup...")
    session = db_manager.get_session()

    try:
        # Get all remaining tickers
        result = session.execute(
            text("SELECT symbol, ticker_id FROM tickers ORDER BY symbol")
        ).fetchall()

        remaining_tickers = {row.symbol for row in result}

        # Check if only production tickers remain
        if remaining_tickers == set(PRODUCTION_TICKERS):
            logger.info(f"✓ Cleanup verified - Only {len(PRODUCTION_TICKERS)} production tickers remain")
            return True
        else:
            unexpected = remaining_tickers - set(PRODUCTION_TICKERS)
            logger.error(f"❌ Unexpected tickers still in database: {unexpected}")
            return False

    finally:
        session.close()


def main():
    """Main cleanup function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean up database by removing test/sample tickers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (shows what would be deleted)
  python scripts/cleanup_database.py

  # Execute cleanup
  python scripts/cleanup_database.py --execute

  # Skip confirmation prompt
  python scripts/cleanup_database.py --execute --yes
        """
    )

    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the cleanup (default is dry-run)'
    )

    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    print("🧹 Database Cleanup Utility")
    print("="*80)
    print(f"Production tickers (KEEP): {', '.join(PRODUCTION_TICKERS)}")
    print(f"Test tickers (DELETE): {', '.join(TICKERS_TO_DELETE)}")
    print("="*80)

    # Initialize database
    db_manager = DatabaseManager(config.DB_URL)

    # Step 1: Verify production tickers exist
    if not verify_production_tickers(db_manager):
        print("\n❌ Production ticker verification failed!")
        sys.exit(1)

    # Step 2: Get and display statistics
    stats = get_ticker_statistics(db_manager)
    print_statistics(stats)

    # Step 3: Confirm deletion (if not dry run and not --yes)
    if args.execute and not args.yes:
        print("\n⚠️  WARNING: This will PERMANENTLY delete data!")
        print("   - All data from test tickers will be removed via CASCADE DELETE")
        print("   - This operation CANNOT be undone")
        print()

        response = input("Are you sure you want to proceed? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Cleanup cancelled")
            sys.exit(0)

    # Step 4: Execute cleanup
    success = cleanup_database(db_manager, dry_run=not args.execute)

    if not success:
        print("\n❌ Cleanup failed!")
        sys.exit(1)

    # Step 5: Verify (if executed)
    if args.execute:
        if verify_cleanup(db_manager):
            print("\n✅ Database cleanup completed successfully!")
            print(f"   - {len(PRODUCTION_TICKERS)} production tickers remain")
            print(f"   - {len(TICKERS_TO_DELETE)} test tickers removed")
        else:
            print("\n❌ Cleanup verification failed!")
            sys.exit(1)

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
