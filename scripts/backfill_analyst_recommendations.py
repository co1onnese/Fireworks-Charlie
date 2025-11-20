#!/usr/bin/env python3
"""
Backfill analyst recommendations from FMP API.

This script:
- Processes tickers sequentially from .env file
- Processes all tickers, only skipping dates that already have recommendations
- Fetches all available grades and filters by date range client-side
- Filters out dates that already exist in database before inserting
- Saves checkpoint after each ticker
- Stops immediately on API limit (429) error
- Can resume from checkpoint if interrupted

Usage:
    python scripts/backfill_analyst_recommendations.py --start-date 2024-10-24 --end-date 2025-11-14
    python scripts/backfill_analyst_recommendations.py --start-date 2024-10-24 --end-date 2025-11-14 --resume
"""
import sys
import argparse
import logging
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from data_collection.fmp_client import FMPClient, FMPAPILimitExceeded
from data_collection.data_processor import DataProcessor
import psycopg2

# Setup logging
def setup_logging():
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "analyst_recommendations_backfill.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class AnalystRecommendationsBackfiller:
    """Backfills analyst recommendations from FMP API."""
    
    def __init__(self, config: Config, checkpoint_file: Path):
        self.config = config
        self.checkpoint_file = checkpoint_file
        self.db_manager = DatabaseManager(config.DB_URL)
        self.fmp_client = FMPClient(config.FMP_API_KEY)
        self.checkpoint = self._load_checkpoint()
        self.stats = {
            "total_tickers": 0,
            "processed": 0,
            "skipped_existing": 0,
            "skipped_missing": 0,
            "success": 0,
            "failed": 0,
            "api_limit_hit": False,
            "records_inserted": 0,
            "start_time": datetime.now().isoformat(),
        }
        
    def _load_checkpoint(self) -> Dict:
        """Load progress checkpoint from file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {len(checkpoint.get('processed_tickers', []))} tickers already processed")
                return checkpoint
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}. Starting fresh.")
        return {
            "processed_tickers": [],
            "last_processed_ticker": None,
            "last_updated": None,
        }
    
    def _save_checkpoint(self, ticker: str, status: str):
        """Save progress checkpoint to file."""
        self.checkpoint["processed_tickers"].append(ticker)
        self.checkpoint["last_processed_ticker"] = ticker
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        self.checkpoint["status"] = status
        
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
            logger.debug(f"Saved checkpoint: {ticker} - {status}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _get_tickers_from_config(self) -> List[str]:
        """Get list of tickers from config."""
        # Config.TICKERS is already a list (parsed in config_manager.py)
        if not hasattr(self.config, 'TICKERS') or not self.config.TICKERS:
            logger.error("No TICKERS found in config")
            return []
        
        # TICKERS is already a list, just clean and deduplicate
        tickers = [t.strip().upper() for t in self.config.TICKERS if t and t.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)
        
        logger.info(f"Found {len(unique_tickers)} unique tickers in config")
        return unique_tickers
    
    def _ticker_exists_in_db(self, ticker: str) -> bool:
        """Check if ticker exists in database."""
        session = self.db_manager.get_session()
        try:
            from data_collection.database_manager import Ticker
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker.upper()).first()
            return ticker_obj is not None
        finally:
            session.close()
    
    def _get_existing_dates(self, ticker: str, start_date: date, end_date: date) -> Set[date]:
        """Get set of dates that already have recommendations for this ticker in the date range."""
        conn = psycopg2.connect(self.config.DB_URL)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT DISTINCT ar.date 
                FROM analyst_recommendations ar
                JOIN tickers t ON ar.ticker_id = t.ticker_id
                WHERE t.symbol = %s
                AND ar.date >= %s
                AND ar.date <= %s
            """, (ticker.upper(), start_date, end_date))
            
            existing_dates = {row[0] for row in cur.fetchall()}
            return existing_dates
        finally:
            cur.close()
            conn.close()
    
    def _get_ticker_id(self, ticker: str) -> Optional[int]:
        """Get ticker_id for a symbol, creating if needed."""
        session = self.db_manager.get_session()
        try:
            ticker_obj = self.db_manager.insert_or_get_ticker(
                session, ticker, None, None, None, None
            )
            session.commit()
            return ticker_obj.ticker_id
        except Exception as e:
            logger.error(f"Failed to get/create ticker {ticker}: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    def backfill_ticker(self, ticker: str, start_date: date, end_date: date) -> Dict:
        """Backfill recommendations for a single ticker."""
        result = {
            "ticker": ticker,
            "success": False,
            "records_inserted": 0,
            "error": None,
        }
        
        logger.info(f"=" * 60)
        logger.info(f"Processing ticker: {ticker}")
        logger.info(f"=" * 60)
        
        # Check if ticker exists in database
        if not self._ticker_exists_in_db(ticker):
            logger.warning(f"Ticker {ticker} not found in database. Skipping.")
            result["error"] = "Ticker not in database"
            self.stats["skipped_missing"] += 1
            return result
        
        # Get existing dates to avoid duplicates
        existing_dates = self._get_existing_dates(ticker, start_date, end_date)
        if existing_dates:
            logger.info(f"Ticker {ticker} already has recommendations for {len(existing_dates)} dates in range. Will backfill missing dates.")
        
        # Get ticker_id
        ticker_id = self._get_ticker_id(ticker)
        if not ticker_id:
            result["error"] = "Failed to get ticker_id"
            self.stats["failed"] += 1
            return result
        
        # Fetch historical grades from FMP API
        try:
            logger.info(f"Fetching historical grades from FMP API for {ticker}...")
            analyst_grades = self.fmp_client.get_historical_grades(symbol=ticker)
            
            if not analyst_grades:
                logger.warning(f"No analyst grades returned for {ticker}")
                result["error"] = "No data from API"
                self.stats["failed"] += 1
                return result
            
            logger.info(f"Fetched {len(analyst_grades)} grade records for {ticker}")
            
            # Process and filter by date range
            processor = DataProcessor([ticker], start_date.isoformat(), end_date.isoformat())
            processed = processor.process_analyst_recommendations(analyst_grades, ticker)
            
            if not processed:
                logger.warning(f"No processed recommendations for {ticker} in date range")
                result["error"] = "No data after processing"
                self.stats["failed"] += 1
                return result
            
            # Filter out dates that already exist in database
            if existing_dates:
                original_count = len(processed)
                processed = [rec for rec in processed if rec.get('date') not in existing_dates]
                filtered_count = original_count - len(processed)
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} recommendations for dates that already exist")
            
            if not processed:
                logger.info(f"All recommendations for {ticker} already exist in database. No new data to insert.")
                result["error"] = "All dates already exist"
                self.stats["skipped_existing"] += 1
                return result
            
            logger.info(f"Processed {len(processed)} new recommendations for {ticker}")
            
            # Insert into database
            session = self.db_manager.get_session()
            try:
                self.db_manager.insert_analyst_recommendations(session, ticker_id, processed)
                session.commit()
                
                result["success"] = True
                result["records_inserted"] = len(processed)
                self.stats["success"] += 1
                self.stats["records_inserted"] += len(processed)
                
                logger.info(f"✓ Successfully inserted {len(processed)} recommendations for {ticker}")
                
            except Exception as e:
                logger.error(f"Error inserting recommendations for {ticker}: {e}", exc_info=True)
                session.rollback()
                result["error"] = str(e)
                self.stats["failed"] += 1
            finally:
                session.close()
                
        except FMPAPILimitExceeded as e:
            logger.error(f"API limit exceeded while processing {ticker}: {e}")
            self.stats["api_limit_hit"] = True
            result["error"] = "API limit exceeded"
            raise  # Re-raise to stop processing
        except Exception as e:
            logger.error(f"Error fetching recommendations for {ticker}: {e}", exc_info=True)
            result["error"] = str(e)
            self.stats["failed"] += 1
        
        return result
    
    def run(self, start_date: date, end_date: date, resume: bool = False):
        """Main backfill loop."""
        logger.info("=" * 60)
        logger.info("ANALYST RECOMMENDATIONS BACKFILL")
        logger.info("=" * 60)
        logger.info(f"Start Date: {start_date}")
        logger.info(f"End Date: {end_date}")
        logger.info(f"Resume: {resume}")
        logger.info("=" * 60)
        
        # Get tickers from config
        all_tickers = self._get_tickers_from_config()
        if not all_tickers:
            logger.error("No tickers to process")
            return
        
        # Filter out already processed tickers if not resuming
        if resume:
            processed_tickers = set(self.checkpoint.get("processed_tickers", []))
            remaining_tickers = [t for t in all_tickers if t not in processed_tickers]
            logger.info(f"Resuming: {len(processed_tickers)} already processed, {len(remaining_tickers)} remaining")
        else:
            remaining_tickers = all_tickers
            self.checkpoint["processed_tickers"] = []
        
        self.stats["total_tickers"] = len(all_tickers)
        
        # Process each ticker
        for ticker in remaining_tickers:
            try:
                # Check if already processed (double-check)
                if ticker in self.checkpoint.get("processed_tickers", []):
                    logger.info(f"Skipping {ticker} (already processed)")
                    continue
                
                self.stats["processed"] += 1
                
                # Backfill ticker
                result = self.backfill_ticker(ticker, start_date, end_date)
                
                # Save checkpoint
                if result["success"]:
                    self._save_checkpoint(ticker, "success")
                elif result["error"] == "Already has recommendations":
                    self._save_checkpoint(ticker, "skipped_existing")
                elif result["error"] == "Ticker not in database":
                    self._save_checkpoint(ticker, "skipped_missing")
                else:
                    self._save_checkpoint(ticker, f"failed: {result['error']}")
                
            except FMPAPILimitExceeded:
                logger.error("=" * 60)
                logger.error("API LIMIT EXCEEDED - STOPPING BACKFILL")
                logger.error("=" * 60)
                self._save_checkpoint(ticker, "api_limit_hit")
                self.stats["api_limit_hit"] = True
                break
            except KeyboardInterrupt:
                logger.warning("Interrupted by user")
                self._save_checkpoint(ticker, "interrupted")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing {ticker}: {e}", exc_info=True)
                self._save_checkpoint(ticker, f"error: {str(e)}")
                continue
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print final summary statistics."""
        logger.info("=" * 60)
        logger.info("BACKFILL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total tickers: {self.stats['total_tickers']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"  - Success: {self.stats['success']}")
        logger.info(f"  - Failed: {self.stats['failed']}")
        logger.info(f"Skipped (existing): {self.stats['skipped_existing']}")
        logger.info(f"Skipped (missing): {self.stats['skipped_missing']}")
        logger.info(f"Records inserted: {self.stats['records_inserted']}")
        if self.stats['api_limit_hit']:
            logger.warning("API LIMIT HIT - Backfill stopped")
            logger.info(f"Checkpoint saved. Resume with --resume flag")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill analyst recommendations from FMP API"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--checkpoint-file",
        type=str,
        default="/opt/Fireworks-Charlie/storage/analyst_recs_backfill_checkpoint.json",
        help="Path to checkpoint file"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)
    
    # Initialize
    config = Config()
    
    if not config.FMP_API_KEY:
        logger.error("FMP_API_KEY not configured")
        sys.exit(1)
    
    checkpoint_file = Path(args.checkpoint_file)
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backfiller
    backfiller = AnalystRecommendationsBackfiller(config, checkpoint_file)
    
    # Run backfill
    try:
        backfiller.run(start_date, end_date, resume=args.resume)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
