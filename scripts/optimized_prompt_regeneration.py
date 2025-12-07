#!/usr/bin/env python3
"""
Optimized prompt regeneration that uses existing data without redundant API calls.

This script:
1. Uses existing database data (no API calls)
2. Generates prompts for all tickers and dates from config
3. Focuses on using the complete fundamental data we already have
"""
import sys
import argparse
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager, ThesisGeneration, Ticker, MarketData, Fundamental, News
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator
from sqlalchemy import select, and_

# Setup logging
def setup_logging():
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "optimized_prompt_regeneration.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class OptimizedPromptRegenerator:
    """Regenerates prompts efficiently using existing database data."""

    def __init__(self, config: Config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)
        self.data_orchestrator = DataOrchestrator(config)
        self.deduplicator = DataDeduplicator()
        self.prompt_builder = EnhancedCumulativePromptBuilder()
        self.stats = {
            "total_dates": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }

    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get trading days using existing market calendar logic."""
        from orchestration.market_calendar import MarketCalendar
        market_calendar = MarketCalendar()
        return market_calendar.get_trading_days(start_date, end_date)

    def get_data_for_date_from_db(self, ticker: str, as_of_date: date) -> Dict[str, Any]:
        """Get all data for a ticker on a specific date from existing database."""
        session = self.db_manager.get_session()
        try:
            # Get ticker_id
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker).first()
            if not ticker_obj:
                return {"error": f"Ticker {ticker} not found in database"}

            ticker_id = ticker_obj.ticker_id

            # Build data structure similar to what DataOrchestrator returns
            data = {
                "ticker": ticker,
                "date": as_of_date.isoformat(),
                "technical": {},
                "fundamental": {},
                "news": [],
                "macro": {}
            }

            # Get technical data
            technical_data = session.query(MarketData).filter(
                MarketData.ticker_id == ticker_id,
                MarketData.date == as_of_date
            ).first()

            if technical_data:
                data["technical"] = {
                    "open": technical_data.open,
                    "high": technical_data.high,
                    "low": technical_data.low,
                    "close": technical_data.close,
                    "volume": technical_data.volume,
                    "adjusted_close": technical_data.adjusted_close
                }

            # Get fundamental data (latest available up to as_of_date)
            fundamental_data = session.query(Fundamental).filter(
                Fundamental.ticker_id == ticker_id,
                Fundamental.filing_date <= as_of_date
            ).order_by(Fundamental.filing_date.desc()).first()

            if fundamental_data:
                data["fundamental"] = {
                    "filing_date": fundamental_data.filing_date.isoformat(),
                    "revenue": fundamental_data.revenue,
                    "net_income": fundamental_data.net_income,
                    "eps": fundamental_data.eps,
                    "total_assets": fundamental_data.total_assets,
                    "total_liabilities": fundamental_data.total_liabilities,
                    "operating_cash_flow": fundamental_data.operating_cash_flow,
                    "pe_ratio": fundamental_data.pe_ratio,
                    "pb_ratio": fundamental_data.pb_ratio
                }

            # Get news data
            news_data = session.query(News).filter(
                News.ticker_id == ticker_id,
                News.published_at >= as_of_date,
                News.published_at < as_of_date + timedelta(days=1)
            ).all()

            if news_data:
                data["news"] = [
                    {
                        "headline": news.headline,
                        "content": news.content,
                        "sentiment_score": news.sentiment_score,
                        "published_at": news.published_at.isoformat()
                    }
                    for news in news_data
                ]

            return data

        except Exception as e:
            logger.error(f"Error getting data for {ticker} on {as_of_date}: {e}")
            return {"error": str(e)}
        finally:
            session.close()

    def generate_prompt_for_ticker_date(self, ticker: str, as_of_date: date) -> Dict[str, Any]:
        """Generate prompt for a specific ticker and date."""
        result = {
            "ticker": ticker,
            "date": as_of_date,
            "success": False,
            "error": None,
        }

        session = self.db_manager.get_session()
        try:
            logger.info(f"Generating prompt for {ticker} on {as_of_date}")

            # Get cumulative data from existing database
            cumulative_data = []

            # Get trading days in the 90 days before as_of_date
            lookback_start = as_of_date - timedelta(days=90)
            trading_days = self.get_trading_days(lookback_start, as_of_date)

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

            # Build cumulative data from existing database
            for trading_day in sampled_days:
                if trading_day >= as_of_date:
                    continue  # Skip the prediction date itself

                day_data = self.get_data_for_date_from_db(ticker, trading_day)
                if isinstance(day_data, dict) and "error" not in day_data:
                    cumulative_data.append(day_data)

            if not cumulative_data:
                result["error"] = "No cumulative data available from database"
                return result

            # Deduplicate the data
            deduped_data = self.deduplicator.deduplicate_cumulative_data(ticker, cumulative_data)

            # Generate new prompts with the enhanced prompt builder
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

            # Get ticker_id
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker).first()
            if not ticker_obj:
                result["error"] = f"Ticker {ticker} not found"
                return result

            ticker_id = ticker_obj.ticker_id

            # Check if thesis already exists
            existing_thesis = session.query(ThesisGeneration).filter(
                ThesisGeneration.ticker_id == ticker_id,
                ThesisGeneration.as_of_date == as_of_date
            ).first()

            if existing_thesis:
                # Update existing thesis
                existing_thesis.system_prompt = system_prompt
                existing_thesis.user_prompt = user_prompt
                existing_thesis.generated_at = datetime.utcnow()
                logger.info(f"Updated existing thesis for {ticker} on {as_of_date}")
            else:
                # Create new thesis generation
                thesis_gen = ThesisGeneration(
                    ticker_id=ticker_id,
                    as_of_date=as_of_date,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    assistant_response={"cleared": True, "reasoning": "", "action": "hold", "support": ""},
                    predicted_action="hold",
                    generated_at=datetime.utcnow()
                )
                session.add(thesis_gen)
                logger.info(f"Created new thesis for {ticker} on {as_of_date}")

            session.commit()

            result["success"] = True
            logger.info(f"✓ Successfully generated prompt for {ticker} on {as_of_date}")

            return result

        except Exception as e:
            logger.error(f"Error generating prompt for {ticker} on {as_of_date}: {e}", exc_info=True)
            session.rollback()
            result["error"] = str(e)
            return result
        finally:
            session.close()

    def regenerate_all_prompts(self, tickers: List[str] = None, start_date: date = None, end_date: date = None,
                               batch_size: int = 50):
        """Regenerate prompts for all tickers and dates efficiently."""
        logger.info("=" * 80)
        logger.info("OPTIMIZED PROMPT REGENERATION")
        logger.info("=" * 80)
        logger.info(f"Tickers: {len(tickers) if tickers else 'all'}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info("=" * 80)

        # Use provided values or fall back to config
        tickers = tickers or self.config.TICKERS
        start_date = start_date or date.fromisoformat(self.config.START_DATE)
        end_date = end_date or date.fromisoformat(self.config.END_DATE)

        # Get trading days
        trading_days = self.get_trading_days(start_date, end_date)
        logger.info(f"Found {len(trading_days)} trading days to process")

        total_combinations = len(tickers) * len(trading_days)
        self.stats["total_dates"] = total_combinations
        logger.info(f"Total combinations to process: {total_combinations}")

        # Process all combinations
        processed_count = 0

        for ticker in tickers:
            logger.info(f"Processing ticker: {ticker}")

            for trading_day in trading_days:
                self.stats["processed"] += 1
                processed_count += 1

                try:
                    result = self.generate_prompt_for_ticker_date(ticker, trading_day)

                    if result["success"]:
                        self.stats["success"] += 1
                    else:
                        self.stats["failed"] += 1
                        self.stats["errors"].append({
                            "ticker": result["ticker"],
                            "date": result["date"],
                            "error": result["error"]
                        })
                        logger.warning(f"Failed to generate prompt for {result['ticker']} on {result['date']}: {result['error']}")

                except KeyboardInterrupt:
                    logger.warning("Interrupted by user")
                    raise
                except Exception as e:
                    self.stats["failed"] += 1
                    self.stats["errors"].append({
                        "ticker": ticker,
                        "date": trading_day,
                        "error": str(e)
                    })
                    logger.error(f"Unexpected error processing {ticker} on {trading_day}: {e}", exc_info=True)
                    continue

                # Log progress periodically
                if processed_count % 100 == 0:
                    logger.info(f"Progress: {self.stats['processed']}/{self.stats['total_dates']} "
                               f"({self.stats['success']} success, {self.stats['failed']} failed)")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print final summary."""
        logger.info("=" * 80)
        logger.info("OPTIMIZED REGENERATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total combinations: {self.stats['total_dates']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Success: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        if self.stats['errors']:
            logger.warning(f"Errors: {len(self.stats['errors'])}")
            logger.warning("First 10 errors:")
            for error in self.stats['errors'][:10]:
                logger.warning(f"  {error['ticker']} on {error['date']}: {error['error']}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Optimized prompt regeneration using existing database data"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to process (default: all from config)"
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
        default=50,
        help="Batch size for processing (default: 50)"
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
    regenerator = OptimizedPromptRegenerator(config)

    # Run regeneration
    try:
        regenerator.regenerate_all_prompts(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            batch_size=args.batch_size
        )
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()