#!/usr/bin/env python3
"""
Regenerate all prompts in the database with the fixed analyst recommendations.

This script:
1. Queries all thesis generations from the database
2. For each thesis, regenerates the prompt using the fixed prompt builder
3. Updates the database with new system_prompt and user_prompt
4. Preserves all other fields (assistant_response, predicted_action, etc.)
"""
import sys
import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager, ThesisGeneration, Ticker
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator
from sqlalchemy import select, and_
from datetime import timedelta

# Setup logging
def setup_logging():
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "prompt_regeneration.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class PromptRegenerator:
    """Regenerates prompts for all thesis generations in the database."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)
        self.data_orchestrator = DataOrchestrator(config)
        self.deduplicator = DataDeduplicator()
        self.prompt_builder = EnhancedCumulativePromptBuilder()
        self.stats = {
            "total_theses": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
    
    def get_all_theses(self, tickers: List[str] = None, start_date: date = None, end_date: date = None) -> List[ThesisGeneration]:
        """Get all thesis generations from database, optionally filtered."""
        session = self.db_manager.get_session()
        try:
            query = session.query(ThesisGeneration).join(Ticker)
            
            if tickers:
                query = query.filter(Ticker.symbol.in_([t.upper() for t in tickers]))
            
            if start_date:
                query = query.filter(ThesisGeneration.as_of_date >= start_date)
            
            if end_date:
                query = query.filter(ThesisGeneration.as_of_date <= end_date)
            
            # Order by ticker and date for consistent processing
            query = query.order_by(Ticker.symbol, ThesisGeneration.as_of_date)
            
            theses = query.all()
            return theses
        finally:
            session.close()
    
    def regenerate_prompt_for_thesis(self, thesis: ThesisGeneration) -> Dict[str, Any]:
        """Regenerate prompt for a single thesis."""
        result = {
            "thesis_id": thesis.thesis_id,
            "success": False,
            "error": None,
        }
        
        session = self.db_manager.get_session()
        try:
            # Save thesis_id before reloading
            thesis_id = thesis.thesis_id
            # Reload thesis from this session to ensure we're working with the right object
            thesis = session.query(ThesisGeneration).filter(ThesisGeneration.thesis_id == thesis_id).first()
            if not thesis:
                result["error"] = f"Thesis {thesis_id} not found in database"
                return result
            
            # Get ticker symbol
            ticker_obj = session.query(Ticker).filter(Ticker.ticker_id == thesis.ticker_id).first()
            if not ticker_obj:
                result["error"] = f"Ticker not found for ticker_id {thesis.ticker_id}"
                return result
            
            ticker = ticker_obj.symbol
            as_of_date = thesis.as_of_date
            
            logger.info(f"Regenerating prompt for {ticker} on {as_of_date} (thesis_id: {thesis.thesis_id})")
            
            # Get cumulative data up to as_of_date
            # We need to build cumulative data like the pipeline does
            cumulative_data = []
            
            # Get data for the last 90 days before as_of_date to build cumulative context
            # The pipeline builds cumulative data day by day, but for regeneration we'll
            # get data for key dates to build a representative cumulative dataset
            from orchestration.market_calendar import MarketCalendar
            market_calendar = MarketCalendar()
            
            # Get trading days in the 90 days before as_of_date
            lookback_start = as_of_date - timedelta(days=90)
            trading_days = market_calendar.get_trading_days(lookback_start, as_of_date)
            
            # Build cumulative data: include all recent days (last 7), then sample older days
            if len(trading_days) <= 7:
                sampled_days = trading_days
            else:
                # Include all days from the last 7 trading days
                recent_days = trading_days[-7:]
                # Sample older days (every 3rd day)
                older_days = trading_days[:-7][::3]
                sampled_days = older_days + recent_days
                # Ensure sorted
                sampled_days = sorted(set(sampled_days))
            
            # Build cumulative data
            for trading_day in sampled_days:
                if trading_day >= as_of_date:
                    continue  # Skip the prediction date itself
                
                day_data = self.data_orchestrator.get_data_for_date(ticker, trading_day)
                if isinstance(day_data, dict) and "error" not in day_data:
                    cumulative_data.append(day_data)
            
            if not cumulative_data:
                result["error"] = "No cumulative data available"
                return result
            
            # Deduplicate the data
            deduped_data = self.deduplicator.deduplicate_cumulative_data(ticker, cumulative_data)
            
            # Generate new prompts with the fixed prompt builder (includes analyst recommendations)
            try:
                system_prompt, user_prompt = self.prompt_builder.build_comprehensive_prompt(
                    ticker,
                    deduped_data,
                    response_format="json"
                )
            except Exception as e:
                result["error"] = f"Error building prompt: {str(e)}"
                logger.error(f"Error building prompt for {ticker} on {as_of_date}: {e}", exc_info=True)
                return result
            
            # Update thesis in database
            thesis.system_prompt = system_prompt
            thesis.user_prompt = user_prompt
            thesis.generated_at = datetime.utcnow()  # Update timestamp
            
            session.commit()
            
            result["success"] = True
            logger.info(f"✓ Successfully regenerated prompt for {ticker} on {as_of_date}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error regenerating prompt for thesis_id {thesis.thesis_id}: {e}", exc_info=True)
            session.rollback()
            result["error"] = str(e)
            return result
        finally:
            session.close()
    
    def regenerate_all(self, tickers: List[str] = None, start_date: date = None, end_date: date = None, 
                       batch_size: int = 100, dry_run: bool = False):
        """Regenerate prompts for all theses."""
        logger.info("=" * 80)
        logger.info("PROMPT REGENERATION")
        logger.info("=" * 80)
        logger.info(f"Dry run: {dry_run}")
        if tickers:
            logger.info(f"Tickers: {', '.join(tickers)}")
        if start_date:
            logger.info(f"Start date: {start_date}")
        if end_date:
            logger.info(f"End date: {end_date}")
        logger.info("=" * 80)
        
        # Get all theses
        logger.info("Querying thesis generations from database...")
        all_theses = self.get_all_theses(tickers, start_date, end_date)
        self.stats["total_theses"] = len(all_theses)
        logger.info(f"Found {len(all_theses)} thesis generations to process")
        
        if dry_run:
            logger.info("DRY RUN - Would regenerate prompts for:")
            for thesis in all_theses[:10]:  # Show first 10
                ticker_obj = self.db_manager.get_session().query(Ticker).filter(
                    Ticker.ticker_id == thesis.ticker_id
                ).first()
                ticker = ticker_obj.symbol if ticker_obj else f"ticker_id_{thesis.ticker_id}"
                logger.info(f"  - {ticker} on {thesis.as_of_date} (thesis_id: {thesis.thesis_id})")
            if len(all_theses) > 10:
                logger.info(f"  ... and {len(all_theses) - 10} more")
            return
        
        # Process in batches
        for i in range(0, len(all_theses), batch_size):
            batch = all_theses[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} theses)")
            
            for thesis in batch:
                self.stats["processed"] += 1
                
                try:
                    result = self.regenerate_prompt_for_thesis(thesis)
                    
                    if result["success"]:
                        self.stats["success"] += 1
                    else:
                        self.stats["failed"] += 1
                        self.stats["errors"].append({
                            "thesis_id": result["thesis_id"],
                            "error": result["error"]
                        })
                        logger.warning(f"Failed to regenerate thesis_id {result['thesis_id']}: {result['error']}")
                
                except KeyboardInterrupt:
                    logger.warning("Interrupted by user")
                    raise
                except Exception as e:
                    self.stats["failed"] += 1
                    self.stats["errors"].append({
                        "thesis_id": thesis.thesis_id,
                        "error": str(e)
                    })
                    logger.error(f"Unexpected error processing thesis_id {thesis.thesis_id}: {e}", exc_info=True)
                    continue
            
            # Log progress
            logger.info(f"Progress: {self.stats['processed']}/{self.stats['total_theses']} "
                       f"({self.stats['success']} success, {self.stats['failed']} failed)")
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print final summary."""
        logger.info("=" * 80)
        logger.info("REGENERATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total theses: {self.stats['total_theses']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Success: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        if self.stats['errors']:
            logger.warning(f"Errors: {len(self.stats['errors'])}")
            logger.warning("First 10 errors:")
            for error in self.stats['errors'][:10]:
                logger.warning(f"  Thesis ID {error['thesis_id']}: {error['error']}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate all prompts in the database with fixed analyst recommendations"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to process (default: all)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date filter (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show what would be regenerated without making changes"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = None
    end_date = None
    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    
    # Parse tickers
    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Initialize
    config = Config()
    regenerator = PromptRegenerator(config)
    
    # Run regeneration
    try:
        regenerator.regenerate_all(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            batch_size=args.batch_size,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
