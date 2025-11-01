#!/usr/bin/env python3
"""
Database reset script - Empties and re-creates the database schema
"""
import os
import sys
import logging

sys.path.insert(0, '/opt/Fireworks-Charlie')

from sqlalchemy import create_engine, text, MetaData, inspect
from orchestration.config_manager import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def drop_all_tables(engine):
    """Drop all tables in the database"""
    logger.info("Dropping all existing tables...")

    # Get all table names
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    if not table_names:
        logger.info("No tables found in database")
        return

    logger.info(f"Found {len(table_names)} tables to drop")

    # Drop each table (CASCADE handles foreign keys)
    with engine.connect() as conn:
        for table_name in table_names:
            logger.info(f"  Dropping table: {table_name}")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'))

        conn.commit()

    logger.info("All tables dropped successfully")

def recreate_tables(engine):
    """Recreate all tables using SQLAlchemy models"""
    logger.info("Recreating database schema from models...")

    # Import all models to ensure they're registered
    from data_collection.database_manager import (
        Base, Ticker, MarketData, Fundamental, News,
        MacroeconomicIndicator, MacroFeature, TickerEventFeature,
        NewsSentimentFeature, InsiderTransaction, ThesisGeneration,
        Position, RLVRTrainingExample, HistoricalReturn,
        SharpeCalculation, DataCollectionRun, RLVRGenerationRun
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Verify tables were created
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    logger.info(f"✓ Schema recreated successfully ({len(table_names)} tables)")

    # List the tables
    logger.info("Tables created:")
    for table_name in sorted(table_names):
        logger.info(f"  ✓ {table_name}")

def verify_empty_database(engine):
    """Verify the database is empty and ready"""
    logger.info("\nVerifying database state...")

    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    # Check for data in each table
    with engine.connect() as conn:
        for table_name in table_names:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            count = result.scalar()
            logger.info(f"  {table_name}: {count} rows")

    # Verify critical tables exist
    required_tables = [
        'tickers', 'market_data', 'fundamentals', 'news',
        'macroeconomic_indicators', 'macro_features', 'thesis_generations'
    ]

    missing_tables = [t for t in required_tables if t not in table_names]
    if missing_tables:
        logger.error(f"Missing required tables: {missing_tables}")
        return False

    logger.info("✓ All required tables present")
    logger.info("✓ Database is empty and ready for fresh data")
    return True

def main():
    logger.info("=" * 80)
    logger.info("DATABASE RESET - Starting")
    logger.info("=" * 80)

    # Get database URL
    db_url = config.DB_URL
    logger.info(f"Database URL: {db_url[:50]}...")

    # Create engine
    engine = create_engine(db_url)

    try:
        # Step 1: Drop all tables
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: Dropping all tables and data")
        logger.info("=" * 80)
        drop_all_tables(engine)

        # Step 2: Recreate schema
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: Recreating database schema")
        logger.info("=" * 80)
        recreate_tables(engine)

        # Step 3: Verify
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: Verifying database state")
        logger.info("=" * 80)
        success = verify_empty_database(engine)

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ DATABASE RESET COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info("\nDatabase is now empty and ready for:")
            logger.info("  • Data collection (run: python main.py)")
            logger.info("  • Thesis generation")
            logger.info("  • RLVR dataset creation")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("\n" + "=" * 80)
            logger.error("❌ DATABASE VERIFICATION FAILED")
            logger.error("=" * 80)
            return 1

    except Exception as e:
        logger.error(f"\n❌ ERROR during database reset: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        engine.dispose()

if __name__ == "__main__":
    sys.exit(main())
