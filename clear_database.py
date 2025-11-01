#!/usr/bin/env python3
"""
Database clear script - Deletes all data but keeps the schema
"""
import os
import sys
import logging

sys.path.insert(0, '/opt/Fireworks-Charlie')

from sqlalchemy import create_engine, text, inspect
from orchestration.config_manager import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_all_data(engine):
    """Delete all data from all tables"""
    logger.info("Clearing all data from tables...")

    # Order matters: delete from child tables first due to foreign keys
    table_order = [
        'rlvr_training_examples',
        'historical_returns',
        'sharpe_calculations',
        'positions',
        'thesis_generations',
        'news_sentiment_features',
        'ticker_event_features',
        'insider_transactions',
        'news',
        'macro_features',
        'market_data',
        'fundamentals',
        'macroeconomic_indicators',
        'data_collection_runs',
        'rlvr_generation_runs',
        'tickers',
    ]

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    total_deleted = 0

    with engine.connect() as conn:
        for table_name in table_order:
            if table_name in existing_tables:
                # Get row count before deletion
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                count_before = result.scalar()

                if count_before > 0:
                    logger.info(f"  Clearing {table_name}: {count_before} rows")
                    conn.execute(text(f'DELETE FROM "{table_name}"'))
                    total_deleted += count_before
                else:
                    logger.info(f"  {table_name}: already empty")

        conn.commit()

    logger.info(f"\n✓ Cleared {total_deleted} total rows from database")

def verify_empty_database(engine):
    """Verify the database is empty"""
    logger.info("\nVerifying database state...")

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    total_rows = 0

    with engine.connect() as conn:
        for table_name in table_names:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.scalar()
            if count > 0:
                logger.info(f"  {table_name}: {count} rows")
                total_rows += count

    if total_rows == 0:
        logger.info("✓ Database is completely empty")
        return True
    else:
        logger.warning(f"⚠ Database still has {total_rows} rows")
        return False

def main():
    logger.info("=" * 80)
    logger.info("DATABASE CLEAR - Starting")
    logger.info("=" * 80)

    # Get database URL
    db_url = config.DB_URL
    logger.info(f"Database URL: {db_url[:50]}...")

    # Create engine
    engine = create_engine(db_url)

    try:
        # Step 1: Clear all data
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Deleting all data (keeping schema)")
        logger.info("=" * 80)
        clear_all_data(engine)

        # Step 2: Verify
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Verifying database state")
        logger.info("=" * 80)
        success = verify_empty_database(engine)

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ DATABASE CLEARED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info("\nDatabase is now empty and ready for fresh data collection")
            logger.info("The schema is intact - you can now run:")
            logger.info("  python main.py --tickers NFLX,MA,HD,SBUX,XOM --start-date 2024-01-01")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ DATABASE VERIFICATION FAILED")
            logger.error("=" * 80)
            return 1

    except Exception as e:
        logger.error(f"\n❌ ERROR during database clear: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        engine.dispose()

if __name__ == "__main__":
    sys.exit(main())
