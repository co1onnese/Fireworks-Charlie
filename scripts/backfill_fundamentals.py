#!/usr/bin/env python3
"""
Fundamental Data Backfill Script
Populates missing fundamental data for all active tickers
"""

import logging
import sys
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from data_collection.database_manager import DatabaseManager, Ticker, Fundamental
from data_collection.eodhd_client import EODHDClient
from data_collection.data_processor import DataProcessor
from orchestration.config_manager import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FundamentalDataBackfill:
    """Backfill fundamental data for missing tickers"""

    def __init__(self, config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)
        self.eodhd_client = EODHDClient(config.EODHD_API_KEY)

    def get_tickers_without_fundamentals(self) -> List[str]:
        """Get list of active tickers that have no fundamental data"""
        session = self.db_manager.get_session()
        try:
            # Get tickers that are active but have no fundamental data
            tickers = session.query(Ticker.symbol).filter(
                Ticker.is_active == True,
                ~Ticker.ticker_id.in_(
                    session.query(Fundamental.ticker_id).distinct()
                )
            ).all()

            return [ticker[0] for ticker in tickers]
        finally:
            session.close()

    def get_tickers_with_stale_fundamentals(self, days_stale: int = 90) -> List[str]:
        """Get tickers with fundamental data older than specified days"""
        session = self.db_manager.get_session()
        try:
            stale_threshold = date.today() - timedelta(days=days_stale)

            tickers = session.query(Ticker.symbol).filter(
                Ticker.is_active == True,
                Ticker.ticker_id.in_(
                    session.query(Fundamental.ticker_id)
                    .group_by(Fundamental.ticker_id)
                    .having(func.max(Fundamental.filing_date) < stale_threshold)
                )
            ).all()

            return [ticker[0] for ticker in tickers]
        finally:
            session.close()

    def backfill_ticker(self, ticker: str) -> bool:
        """Backfill fundamental data for a specific ticker"""
        logger.info(f"Backfilling fundamental data for {ticker}")

        session = self.db_manager.get_session()
        try:
            # Get ticker object
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker).first()
            if not ticker_obj:
                logger.error(f"Ticker {ticker} not found in database")
                return False

            # Fetch fundamental data from EODHD
            symbol_with_exchange = f"{ticker}.US"
            fundamentals_raw = self.eodhd_client.get_fundamentals(symbol_with_exchange)

            if not fundamentals_raw:
                logger.warning(f"No fundamental data returned for {ticker}")
                return False

            # Process the data
            # Use a wide date range to capture all available data
            processor = DataProcessor([ticker], "2020-01-01", "2025-12-31")
            fundamentals_processed = processor.process_fundamentals(fundamentals_raw, symbol_with_exchange)

            if not fundamentals_processed:
                logger.warning(f"No fundamental data processed for {ticker}")
                return False

            # Convert symbol to ticker_id for database insertion
            for record in fundamentals_processed:
                record['ticker_id'] = ticker_obj.ticker_id
                # Remove the symbol field since database expects ticker_id
                if 'symbol' in record:
                    del record['symbol']

            # Insert into database
            self.db_manager.insert_fundamentals(session, fundamentals_processed)

            # Commit the transaction to persist changes
            session.commit()

            # Count the number of records that were processed
            inserted_count = len(fundamentals_processed)

            if inserted_count > 0:
                logger.info(f"Successfully inserted {inserted_count} fundamental records for {ticker}")
                return True
            else:
                logger.warning(f"No new fundamental records inserted for {ticker} (may already exist)")
                return False

        except Exception as e:
            logger.error(f"Error backfilling fundamental data for {ticker}: {e}")
            return False
        finally:
            session.close()

    def backfill_all_missing_tickers(self) -> Dict[str, Any]:
        """Backfill fundamental data for all tickers missing data"""
        logger.info("Starting fundamental data backfill for missing tickers")

        # Get tickers without fundamental data
        missing_tickers = self.get_tickers_without_fundamentals()

        if not missing_tickers:
            logger.info("No tickers missing fundamental data")
            return {"status": "success", "message": "No missing tickers found"}

        logger.info(f"Found {len(missing_tickers)} tickers without fundamental data: {', '.join(missing_tickers)}")

        results = {
            "total_tickers": len(missing_tickers),
            "successful": 0,
            "failed": 0,
            "failed_tickers": []
        }

        for ticker in missing_tickers:
            success = self.backfill_ticker(ticker)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failed_tickers"].append(ticker)

        logger.info(f"Backfill completed: {results['successful']} successful, {results['failed']} failed")

        if results["failed_tickers"]:
            logger.warning(f"Failed tickers: {', '.join(results['failed_tickers'])}")

        return results

    def update_stale_tickers(self, days_stale: int = 90) -> Dict[str, Any]:
        """Update fundamental data for tickers with stale data"""
        logger.info(f"Updating fundamental data for tickers with data older than {days_stale} days")

        stale_tickers = self.get_tickers_with_stale_fundamentals(days_stale)

        if not stale_tickers:
            logger.info("No tickers with stale fundamental data")
            return {"status": "success", "message": "No stale tickers found"}

        logger.info(f"Found {len(stale_tickers)} tickers with stale fundamental data: {', '.join(stale_tickers)}")

        results = {
            "total_tickers": len(stale_tickers),
            "successful": 0,
            "failed": 0,
            "failed_tickers": []
        }

        for ticker in stale_tickers:
            success = self.backfill_ticker(ticker)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failed_tickers"].append(ticker)

        logger.info(f"Update completed: {results['successful']} successful, {results['failed']} failed")

        if results["failed_tickers"]:
            logger.warning(f"Failed tickers: {', '.join(results['failed_tickers'])}")

        return results


def main():
    """Main execution function"""
    logger.info("=== FUNDAMENTAL DATA BACKFILL STARTED ===")

    try:
        config = Config()
        backfill = FundamentalDataBackfill(config)

        # First, backfill tickers with no fundamental data
        logger.info("\n1. BACKFILLING TICKERS WITH NO FUNDAMENTAL DATA")
        missing_results = backfill.backfill_all_missing_tickers()

        # Then, update tickers with stale data
        logger.info("\n2. UPDATING TICKERS WITH STALE FUNDAMENTAL DATA")
        stale_results = backfill.update_stale_tickers(days_stale=90)

        # Summary
        logger.info("\n=== BACKFILL SUMMARY ===")
        logger.info(f"Missing data backfill: {missing_results.get('successful', 0)} successful, {missing_results.get('failed', 0)} failed")
        logger.info(f"Stale data update: {stale_results.get('successful', 0)} successful, {stale_results.get('failed', 0)} failed")

        total_successful = missing_results.get('successful', 0) + stale_results.get('successful', 0)
        total_failed = missing_results.get('failed', 0) + stale_results.get('failed', 0)

        logger.info(f"TOTAL: {total_successful} successful, {total_failed} failed")

        if total_failed == 0:
            logger.info("✅ All backfill operations completed successfully")
        else:
            logger.warning("⚠️ Some backfill operations failed - check logs for details")

    except Exception as e:
        logger.error(f"❌ Backfill failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()