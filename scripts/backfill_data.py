#!/usr/bin/env python3
"""
Data Backfill Script for Fireworks-Charlie

Backfills all required data for a ticker from EODHD API, FMP API, and FRED:
- Market data (OHLCV) with technical indicators (ATR, ADX, RSI, MACD, etc.)
- Fundamentals (quarterly financial statements)
- News articles with sentiment
- Analyst recommendations (historical grades) from FMP
- Macro indicators from FRED

Usage:
    python scripts/backfill_data.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-01-31

    # Backfill multiple tickers
    python scripts/backfill_data.py --tickers AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-01-31
"""
import sys
import os
import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from data_collection.eodhd_client import EODHDClient
from data_collection.fred_client import FREDClient
from data_collection.fmp_client import FMPClient
from data_collection.data_processor import DataProcessor
from data_collection.feature_engineering import FeatureEngineer
from orchestration.market_calendar import MarketCalendar

# Setup logging
def setup_logging():
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "data_backfill.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


def backfill_ticker(
    ticker: str,
    start_date: date,
    end_date: date,
    db_manager: DatabaseManager,
    eodhd_client: EODHDClient,
    fmp_client: FMPClient,
    fred_client: FREDClient,
    market_calendar: MarketCalendar
) -> Dict[str, Any]:
    """Backfill all data for a single ticker."""

    stats = {
        "ticker": ticker,
        "market_data": { "success": 0, "failed": 0 },
        "fundamentals": { "success": 0, "failed": 0 },
        "news": { "success": 0, "failed": 0 },
        "analyst_recs": { "success": 0, "failed": 0 },
        "macro": { "success": 0, "failed": 0 },
        "total_time_ms": 0
    }

    start_time = datetime.now()
    session = db_manager.get_session()

    try:
        logger.info(f"=" * 60)
        logger.info(f"Backfilling {ticker} from {start_date} to {end_date}")
        logger.info(f"=" * 60)

        # Get ticker_id once
        logger.info(f"Getting ticker_id for {ticker}...")
        ticker_obj = db_manager.insert_or_get_ticker(session, ticker, None, None, None, None)
        ticker_id = ticker_obj.ticker_id

        # 1. Get market data (OHLCV)
        logger.info(f"[1/5] Collecting market data...")
        try:
            market_data = eodhd_client.get_eod_data(ticker, start_date.isoformat(), end_date.isoformat())
            if market_data:
                processor = DataProcessor([ticker], start_date.isoformat(), end_date.isoformat())
                processed = processor.process_eod_data(market_data, ticker)

                # Insert into database
                db_manager.insert_market_data(session, ticker_id, processed)

                stats["market_data"]["success"] = len(processed)
                logger.info(f"✓ Inserted {len(processed)} market data records")

                # 2. Calculate and add technical indicators (ATR, ADX, etc.)
                logger.info(f"[2/5] Calculating technical indicators...")
                feature_engineer = FeatureEngineer(db_manager)
                feature_engineer._calculate_technical_indicators(session, ticker_id, start_date, end_date)

                stats["market_data"]["indicators"] = "calculated"
                logger.info(f"✓ Technical indicators calculated")
            else:
                logger.warning(f"No market data found for {ticker}")
                stats["market_data"]["failed"] = 1
        except Exception as e:
            logger.error(f"Error collecting market data: {e}", exc_info=True)
            stats["market_data"]["failed"] = 1

        # 3. Get fundamentals
        logger.info(f"[3/5] Collecting fundamentals...")
        try:
            fundamentals = eodhd_client.get_fundamentals(ticker)
            if fundamentals:
                processor = DataProcessor([ticker], start_date.isoformat(), end_date.isoformat())
                processed = processor.process_fundamentals(fundamentals, ticker)

                if processed:
                    db_manager.insert_fundamental_data(session, ticker_id, processed)

                    stats["fundamentals"]["success"] = len(processed)
                    logger.info(f"✓ Inserted {len(processed)} fundamental records")
            else:
                logger.warning(f"No fundamentals found for {ticker}")
                stats["fundamentals"]["failed"] = 1
        except Exception as e:
            logger.error(f"Error collecting fundamentals: {e}", exc_info=True)
            stats["fundamentals"]["failed"] = 1

        # 4. Get news
        logger.info(f"[4/5] Collecting news...")
        try:
            news = eodhd_client.get_news(ticker, start_date.isoformat(), end_date.isoformat())
            if news:
                processor = DataProcessor([ticker], start_date.isoformat(), end_date.isoformat())
                processed = processor.process_news(news, ticker)

                if processed:
                    db_manager.insert_news_data(session, ticker_id, processed)

                    stats["news"]["success"] = len(processed)
                    logger.info(f"✓ Inserted {len(processed)} news records")
            else:
                logger.warning(f"No news found for {ticker}")
                stats["news"]["failed"] = 1
        except Exception as e:
            logger.error(f"Error collecting news: {e}", exc_info=True)
            stats["news"]["failed"] = 1

        # 5. Get analyst recommendations (historical grades from FMP)
        logger.info(f"[5/5] Collecting analyst recommendations (historical grades) from FMP API...")
        try:
            # FMP historical-grades API doesn't support date filtering in query params
            # We'll fetch all available grades and filter client-side in the processor
            analyst_grades = fmp_client.get_historical_grades(symbol=ticker)

            if analyst_grades:
                processor = DataProcessor([ticker], start_date.isoformat(), end_date.isoformat())
                processed = processor.process_analyst_recommendations(analyst_grades, ticker)

                if processed:
                    db_manager.insert_analyst_recommendations(session, ticker_id, processed)

                    stats["analyst_recs"]["success"] = len(processed)
                    logger.info(f"✓ Inserted {len(processed)} analyst recommendation records")
            else:
                logger.warning(f"No analyst recommendations found for {ticker}")
                stats["analyst_recs"]["failed"] = 1
        except Exception as e:
            logger.error(f"Error collecting analyst recommendations: {e}", exc_info=True)
            stats["analyst_recs"]["failed"] = 1

        # Commit all changes
        session.commit()
        stats["total_time_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(f"=" * 60)
        logger.info(f"✓ Completed in {stats['total_time_ms']}ms")
        logger.info(f"=" * 60)

        return stats

    except Exception as e:
        logger.error(f"Critical error backfilling {ticker}: {e}", exc_info=True)
        session.rollback()
        return stats
    finally:
        session.close()


def backfill_macro_data(
    fred_client: FREDClient,
    db_manager: DatabaseManager,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """Backfill macroeconomic indicators."""

    stats = { "success": 0, "failed": 0, "series": [] }
    session = db_manager.get_session()

    try:
        logger.info(f"Backfilling macro data from {start_date} to {end_date}")

        # FRED series to collect
        fred_series = [
            "GDPC1",       # Real GDP
            "CPIAUCSL",    # CPI
            "PCEPI",       # PCE
            "UNRATE",      # Unemployment Rate
            "FEDFUNDS",    # Fed Funds Rate
            "DGS10",       # 10-Year Treasury
            "DGS2",        # 2-Year Treasury
            "INDPRO",      # Industrial Production
        ]

        for series_id in fred_series:
            try:
                logger.info(f"Collecting {series_id}...")

                # Get series info and observations
                series_info = fred_client.get_series_info(series_id)
                observations = fred_client.get_series_observations(
                    series_id,
                    start_date.isoformat(),
                    end_date.isoformat()
                )

                if observations:
                    processor = DataProcessor([], start_date.isoformat(), end_date.isoformat())
                    processed = processor.process_fred_series(observations, series_info, series_id)

                    if processed:
                        db_manager.insert_macroeconomic_indicators(session, processed)
                        stats["success"] += len(processed)
                        stats["series"].append(series_id)
                        logger.info(f"✓ Inserted {len(processed)} records for {series_id}")
                    else:
                        logger.warning(f"No observations for {series_id}")
                        stats["failed"] += 1

            except Exception as e:
                logger.error(f"Error collecting {series_id}: {e}", exc_info=True)
                stats["failed"] += 1

        # Calculate derived macro features
        logger.info("Calculating derived macro features...")
        try:
            feature_engineer = FeatureEngineer(db_manager)
            feature_engineer._process_macro_features(start_date.isoformat(), end_date.isoformat())
            stats["derived_features"] = "calculated"
            logger.info("✓ Derived macro features calculated")
        except Exception as e:
            logger.error(f"Error calculating macro features: {e}", exc_info=True)

        session.commit()
        return stats

    except Exception as e:
        logger.error(f"Critical error backfilling macro data: {e}", exc_info=True)
        session.rollback()
        return stats
    finally:
        session.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill all data for tickers from EODHD, FMP, and FRED"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="Single ticker to backfill"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers"
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
        help="End date (YYYY-MM-DD) - defaults to today"
    )
    parser.add_argument(
        "--skip-market",
        action="store_true",
        help="Skip market/technical data"
    )
    parser.add_argument(
        "--skip-fundamentals",
        action="store_true",
        help="Skip fundamental data"
    )
    parser.add_argument(
        "--skip-news",
        action="store_true",
        help="Skip news data"
    )
    parser.add_argument(
        "--skip-analyst",
        action="store_true",
        help="Skip analyst recommendations"
    )
    parser.add_argument(
        "--skip-macro",
        action="store_true",
        help="Skip macro data"
    )

    args = parser.parse_args()

    if args.ticker and args.tickers:
        logger.error("Use either --ticker or --tickers, not both")
        sys.exit(1)

    if not args.ticker and not args.tickers:
        logger.error("Must specify either --ticker or --tickers")
        sys.exit(1)

    tickers = [args.ticker] if args.ticker else [t.strip() for t in args.tickers.split(",")]
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date) if args.end_date else date.today()

    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config.DB_URL)
    market_calendar = MarketCalendar()

    # Verify API keys
    if not config.EODHD_API_KEY:
        logger.error("EODHD_API_KEY not configured")
        sys.exit(1)

    eodhd_client = EODHDClient(config.EODHD_API_KEY)

    fmp_client = None
    if not args.skip_analyst:
        if not config.FMP_API_KEY:
            logger.warning("FMP_API_KEY not configured, skipping analyst recommendations")
            args.skip_analyst = True
        else:
            fmp_client = FMPClient(config.FMP_API_KEY)

    fred_client = None
    if not args.skip_macro:
        if not config.FRED_API_KEY:
            logger.warning("FRED_API_KEY not configured, skipping macro data")
            args.skip_macro = True
        else:
            fred_client = FREDClient(config.FRED_API_KEY)

    # Backfill macro first (only once, not per ticker)
    if not args.skip_macro and fred_client:
        logger.info("\n" + "="*60)
        logger.info("BACKFILLING MACRO DATA")
        logger.info("="*60)
        macro_stats = backfill_macro_data(fred_client, db_manager, start_date, end_date)
        logger.info(f"✓ Macro data backfilled ({macro_stats['success']} records)")

    # Backfill each ticker
    for ticker in tickers:
        logger.info("\n" + "="*60)
        logger.info(f"BACKFILLING {ticker}")
        logger.info("="*60)

        stats = backfill_ticker(
            ticker,
            start_date,
            end_date,
            db_manager,
            eodhd_client,
            fmp_client,
            fred_client if args.skip_macro else None,  # Already collected
            market_calendar
        )

        # Log summary
        logger.info(f"\nSUMMARY for {ticker}:")
        if not args.skip_market:
            logger.info(f"  Market data: {stats['market_data']['success']} records")
        if not args.skip_fundamentals:
            logger.info(f"  Fundamentals: {stats['fundamentals']['success']} records")
        if not args.skip_news:
            logger.info(f"  News: {stats['news']['success']} records")
        if not args.skip_analyst and fmp_client:
            logger.info(f"  Analyst recs: {stats['analyst_recs']['success']} records")

    logger.info("\n" + "="*60)
    logger.info("✓ ALL BACKFILL TASKS COMPLETED")
    logger.info("="*60)


if __name__ == "__main__":
    main()
