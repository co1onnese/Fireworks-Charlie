"""
Data collection orchestrator for Fireworks-Charlie
Wraps data collection functionality for RLVR training
"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from sqlalchemy import func

from .database_manager import DatabaseManager
from .data_processor import DataProcessor
from .eodhd_client import EODHDClient
from .fred_client import FREDClient
from .fmp_client import FMPClient
from .feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)

class DataOrchestrator:
    """Orchestrates data collection for RLVR training"""
    
    def __init__(self, config):
        """
        Initialize data orchestrator
        
        Args:
            config: Configuration object with API keys and settings
        """
        self.config = config
        
        # Initialize components
        self.db_manager = DatabaseManager(config.DB_URL)
        self.eodhd_client = EODHDClient(config.EODHD_API_KEY) if config.EODHD_API_KEY else None
        self.fred_client = FREDClient(config.FRED_API_KEY) if config.FRED_API_KEY else None
        self.fmp_client = FMPClient(config.FMP_API_KEY) if config.FMP_API_KEY else None
        
        # FRED series to fetch
        self.fred_series = [
            "GDPC1",       # Real GDP
            "CPIAUCSL",    # CPI
            "PCEPI",       # PCE
            "UNRATE",      # Unemployment Rate
            "FEDFUNDS",    # Fed Funds Rate
            "DGS10",       # 10-Year Treasury
            "DGS2",        # 2-Year Treasury
            "INDPRO",      # Industrial Production
        ]
        
        logger.info("DataOrchestrator initialized")

    def get_existing_data_range(self, ticker: str, data_type: str) -> tuple:
        """
        Get the date range of existing data for a ticker

        Args:
            ticker: Stock ticker symbol
            data_type: 'technical', 'fundamental', 'news', or 'macro'

        Returns:
            tuple: (min_date, max_date, count) or (None, None, 0) if no data exists
        """
        from .database_manager import MarketData, Fundamental, News, MacroFeature, Ticker

        session = self.db_manager.get_session()
        try:
            # Get ticker object
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker).first()
            if not ticker_obj:
                logger.warning(f"Ticker {ticker} not found in database")
                return (None, None, 0)

            # Query based on data type
            if data_type == 'technical':
                result = session.query(
                    func.min(MarketData.date),
                    func.max(MarketData.date),
                    func.count(MarketData.market_data_id)
                ).filter(MarketData.ticker_id == ticker_obj.ticker_id).first()

            elif data_type == 'fundamental':
                result = session.query(
                    func.min(Fundamental.report_date),
                    func.max(Fundamental.report_date),
                    func.count(Fundamental.fundamental_id)
                ).filter(Fundamental.ticker_id == ticker_obj.ticker_id).first()

            elif data_type == 'news':
                result = session.query(
                    func.min(func.date(News.published_at)),
                    func.max(func.date(News.published_at)),
                    func.count(News.news_id)
                ).filter(News.ticker_id == ticker_obj.ticker_id).first()

            elif data_type == 'macro':
                result = session.query(
                    func.min(MacroFeature.date),
                    func.max(MacroFeature.date),
                    func.count(MacroFeature.feature_id)
                ).filter(MacroFeature.date.isnot(None)).first()

            else:
                raise ValueError(f"Unknown data_type: {data_type}")

            min_date, max_date, count = result
            return (min_date, max_date, count if count else 0)

        finally:
            session.close()

    def identify_data_gaps(self, ticker: str, start_date: date, end_date: date) -> dict:
        """
        Identify gaps in data coverage for a ticker

        Args:
            ticker: Stock ticker symbol
            start_date: Desired start date
            end_date: Desired end date

        Returns:
            Dict with gaps per data type:
            {
                'technical': [(gap_start1, gap_end1), (gap_start2, gap_end2)],
                'fundamental': [(gap_start, gap_end)],
                'news': [(gap_start, gap_end)],
                'macro': [(gap_start, gap_end)]
            }
        """
        from .database_manager import MarketData, Fundamental, News, MacroFeature, Ticker
        from sqlalchemy import and_, or_, distinct

        session = self.db_manager.get_session()
        try:
            ticker_obj = session.query(Ticker).filter(Ticker.symbol == ticker).first()
            if not ticker_obj:
                logger.warning(f"Ticker {ticker} not found in database")
                return {'technical': [], 'fundamental': [], 'news': [], 'macro': []}

            gaps = {
                'technical': [],
                'fundamental': [],
                'news': [],
                'macro': []
            }

            # Technical data gaps (daily data, check for missing dates)
            tech_min, tech_max, tech_count = self.get_existing_data_range(ticker, 'technical')

            if tech_min and tech_max:
                # Get all existing dates
                existing_dates = set()
                for row in session.query(MarketData.date).filter(
                    MarketData.ticker_id == ticker_obj.ticker_id,
                    MarketData.date >= max(start_date, tech_min),
                    MarketData.date <= min(end_date, tech_max)
                ).all():
                    existing_dates.add(row[0])

                # Find gaps by checking each date in range
                current_date = start_date
                gap_start = None
                while current_date <= end_date:
                    # Check if date is a trading day (Monday-Friday)
                    if current_date.weekday() < 5:  # 0=Monday, 6=Sunday
                        if current_date not in existing_dates:
                            # Found a gap
                            if gap_start is None:
                                gap_start = current_date
                        else:
                            # Gap ended
                            if gap_start is not None:
                                gaps['technical'].append((gap_start, current_date - timedelta(days=1)))
                                gap_start = None
                    current_date += timedelta(days=1)

                # Close final gap if it exists
                if gap_start is not None:
                    gaps['technical'].append((gap_start, end_date))

            # Fundamental data gaps (quarterly, simpler check)
            fund_min, fund_max, fund_count = self.get_existing_data_range(ticker, 'fundamental')

            if fund_count == 0:
                # No fundamentals at all
                gaps['fundamental'].append((start_date, end_date))
            elif fund_max and fund_max < end_date:
                # Gaps after last report
                gaps['fundamental'].append((fund_max + timedelta(days=1), end_date))

            # News data gaps (daily, check for missing dates)
            news_min, news_max, news_count = self.get_existing_data_range(ticker, 'news')

            if news_min and news_max:
                # Get existing news dates
                existing_news_dates = set()
                for row in session.query(distinct(func.date(News.published_at))).filter(
                    News.ticker_id == ticker_obj.ticker_id,
                    func.date(News.published_at) >= start_date,
                    func.date(News.published_at) <= end_date
                ).all():
                    existing_news_dates.add(row[0])

                # Find gaps
                current_date = start_date
                gap_start = None
                while current_date <= end_date:
                    if current_date not in existing_news_dates:
                        if gap_start is None:
                            gap_start = current_date
                    else:
                        if gap_start is not None:
                            gaps['news'].append((gap_start, current_date - timedelta(days=1)))
                            gap_start = None
                    current_date += timedelta(days=1)

                if gap_start is not None:
                    gaps['news'].append((gap_start, end_date))

            # Macro data gaps (global, check once)
            macro_min, macro_max, macro_count = self.get_existing_data_range(ticker, 'macro')

            if macro_count == 0:
                gaps['macro'].append((start_date, end_date))
            elif macro_max and macro_max < end_date:
                gaps['macro'].append((macro_max + timedelta(days=1), end_date))

            return gaps

        finally:
            session.close()

    def collect_data_for_ticker(self, ticker: str, start_date: date, end_date: date,
                                technical_lookback_days: int = 90,
                                fundamental_lookback_months: int = 12,
                                skip_existing: bool = True) -> Dict[str, Any]:
        """
        Collect all data for a single ticker over a date range

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for training data collection
            end_date: End date for data collection
            technical_lookback_days: Days to look back before start_date for technical data
                                    (default: 90 days to ensure 30 trading days + history for indicators)
            fundamental_lookback_months: Months to look back before start_date for fundamentals
                                        (default: 12 months to ensure recent quarterly reports)
            skip_existing: If True, only fetch missing data (skip existing). Default: True

        Returns:
            Dictionary with collected data status
        """
        # Calculate extended dates for different data types
        technical_start = start_date - timedelta(days=technical_lookback_days)
        fundamental_start = start_date - timedelta(days=fundamental_lookback_months * 30)

        logger.info(f"Collecting data for {ticker}")
        logger.info(f"  Training period: {start_date} to {end_date}")
        logger.info(f"  Technical data: {technical_start} to {end_date} (extended {technical_lookback_days} days)")
        logger.info(f"  Fundamental data: {fundamental_start} to {end_date} (extended {fundamental_lookback_months} months)")
        logger.info(f"  News/insider data: {start_date} to {end_date} (no extension)")
        
        session = self.db_manager.get_session()
        processor = DataProcessor([ticker], start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        try:
            # 1. Fetch and store ticker metadata
            if self.eodhd_client:
                fundamentals_raw = self.eodhd_client.get_fundamentals(f"{ticker}.US")
                if fundamentals_raw:
                    company_name = fundamentals_raw.get("General", {}).get("Name")
                    sector = fundamentals_raw.get("General", {}).get("Sector")
                    industry = fundamentals_raw.get("General", {}).get("Industry")
                else:
                    company_name, sector, industry = ticker, None, None
            else:
                company_name, sector, industry = ticker, None, None
            
            ticker_obj = self.db_manager.insert_ticker(
                session,
                symbol=ticker,
                exchange="US",
                company_name=company_name,
                sector=sector,
                industry=industry,
            )
            session.commit()
            logger.info(f"Ticker {ticker} metadata stored")
            
            # Initialize variables for return statement
            eod_processed = []
            news_processed = []
            insider_processed = []
            
            # 2. Fetch and process Technical Market Data (with extended lookback)
            if self.eodhd_client:
                eod_raw = self.eodhd_client.get_eod_data(
                    f"{ticker}.US",
                    technical_start.strftime("%Y-%m-%d"),  # Use extended start date
                    end_date.strftime("%Y-%m-%d")
                )
                eod_processed = processor.process_eod_data(eod_raw, f"{ticker}.US")

                # Add ticker_id to each record for the insert method
                for record in eod_processed:
                    record["ticker_id"] = ticker_obj.ticker_id
                self.db_manager.insert_technical_market_data(session, eod_processed)
                session.commit()
                logger.info(
                    f"Stored {len(eod_processed)} technical market records "
                    f"({technical_start} to {end_date}, includes {technical_lookback_days} day lookback)"
                )
            
            # 3. Fetch and process Fundamentals
            if self.eodhd_client and fundamentals_raw:
                fundamentals_processed = processor.process_fundamentals(
                    fundamentals_raw, 
                    f"{ticker}.US"
                )
                if fundamentals_processed:
                    # Add ticker_id to each record
                    for record in fundamentals_processed:
                        record["ticker_id"] = ticker_obj.ticker_id
                    self.db_manager.insert_fundamentals(session, fundamentals_processed)
                    session.commit()
                    logger.info("Fundamentals data stored")
            
            # 4. Fetch and process News
            if self.eodhd_client:
                logger.info(f"Fetching news for {ticker} from {start_date} to {end_date}")
                
                news_raw = self.eodhd_client.get_news(
                    f"{ticker}.US", 
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d"),
                    limit=1000  # Explicitly request up to 1000 articles (EODHD max)
                )
                
                if not news_raw:
                    logger.warning(
                        f"No news data returned from API for {ticker}. "
                        f"This could indicate: (1) No news published in period, "
                        f"(2) API returned empty response, or (3) Date range has no coverage."
                    )
                else:
                    logger.info(f"Raw news API returned {len(news_raw)} articles for {ticker}")
                
                news_processed = processor.process_news(news_raw or [], f"{ticker}.US")
                
                if news_processed:
                    logger.info(f"Processed {len(news_processed)} news articles after filtering for {ticker}")
                    
                    # Add ticker_id to each article for the insert method
                    for article in news_processed:
                        article["ticker_id"] = ticker_obj.ticker_id
                    
                    self.db_manager.insert_news(session, news_processed)
                    session.commit()
                    logger.info(f"Successfully stored {len(news_processed)} news articles in database for {ticker}")
                else:
                    logger.warning(f"No news articles passed filtering/processing for {ticker}")
            
            # 5. Fetch and process Insider Transactions
            if self.eodhd_client:
                insider_raw = self.eodhd_client.get_insider_transactions(
                    f"{ticker}.US", 
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d")
                )
                insider_processed = processor.process_insider_transactions(insider_raw, f"{ticker}.US")
                
                # Add ticker_id to each transaction for the insert method
                for transaction in insider_processed:
                    transaction["ticker_id"] = ticker_obj.ticker_id
                self.db_manager.insert_insider_transactions_batch(session, insider_processed)
                session.commit()
                logger.info(f"Stored {len(insider_processed)} insider transactions")
            
            # 6. Fetch and process Analyst Recommendations (FMP historical-grades API)
            analyst_processed = []
            if self.fmp_client:
                logger.info(f"Fetching analyst recommendations (historical grades) for {ticker} from FMP API")
                
                try:
                    # FMP historical-grades API doesn't support date filtering in query params
                    # We'll fetch all available grades and filter client-side
                    analyst_raw = self.fmp_client.get_historical_grades(symbol=ticker)
                    
                    if not analyst_raw:
                        logger.info(f"No analyst recommendations returned from FMP API for {ticker}")
                    else:
                        logger.info(f"Raw FMP API returned {len(analyst_raw)} historical grades for {ticker}")
                        
                        analyst_processed = processor.process_analyst_recommendations(analyst_raw, ticker)
                        
                        if analyst_processed:
                            logger.info(f"Processed {len(analyst_processed)} analyst recommendations after filtering for {ticker}")
                            
                            # Add ticker_id to each recommendation
                            for rec in analyst_processed:
                                rec["ticker_id"] = ticker_obj.ticker_id
                            
                            self.db_manager.insert_analyst_recommendations(session, ticker_obj.ticker_id, analyst_processed)
                            session.commit()
                            logger.info(f"Successfully stored {len(analyst_processed)} analyst recommendations in database for {ticker}")
                        else:
                            logger.info(f"No analyst recommendations passed filtering/processing for {ticker}")
                            
                except Exception as e:
                    logger.warning(f"Error fetching analyst recommendations for {ticker}: {e}")
                    # Don't fail the entire collection if analyst recommendations fail
            else:
                logger.debug("FMP client not available, skipping analyst recommendations")
            
            return {
                "status": "success",
                "ticker": ticker,
                "ticker_id": ticker_obj.ticker_id,
                "records": {
                    "technical": len(eod_processed) if self.eodhd_client else 0,
                    "news": len(news_processed) if self.eodhd_client else 0,
                    "insider": len(insider_processed) if self.eodhd_client else 0,
                    "analyst_recommendations": len(analyst_processed) if self.fmp_client else 0,
                }
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error collecting data for {ticker}: {e}")
            return {
                "status": "error",
                "ticker": ticker,
                "error": str(e)
            }
        finally:
            session.close()
    
    def collect_macro_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Collect macroeconomic data from FRED
        
        Args:
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            Dictionary with macro data collection status
        """
        if not self.fred_client:
            logger.warning("FRED client not available, skipping macro data")
            return {"status": "skipped", "reason": "No FRED API key"}
        
        logger.info(f"Collecting macro data from {start_date} to {end_date}")
        
        session = self.db_manager.get_session()
        processor = DataProcessor([], start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        try:
            total_records = 0
            
            for series_id in self.fred_series:
                logger.info(f"Fetching FRED series: {series_id}")
                
                # Get series metadata
                series_info = self.fred_client.get_series_info(series_id)
                if not series_info:
                    logger.warning(f"Could not fetch info for series {series_id}")
                    continue
                
                # Get series observations
                observations = self.fred_client.get_series_observations(
                    series_id,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if observations:
                    # Process and store
                    processed = processor.process_fred_series(
                        observations,
                        series_info,
                        series_id
                    )

                    self.db_manager.insert_macroeconomic_indicators(session, processed)

                    session.commit()
                    total_records += len(processed)
                    logger.info(f"Stored {len(processed)} records for {series_id}")
            
            return {
                "status": "success",
                "total_records": total_records,
                "series_count": len(self.fred_series)
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error collecting macro data: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            session.close()
    
    def run_feature_engineering(self, tickers: List[str], start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Run feature engineering for specified tickers
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with feature engineering status
        """
        logger.info(f"Running feature engineering for {len(tickers)} tickers")

        # Use dynamic worker allocation - cap at 4 to avoid overwhelming database
        num_workers = min(4, len(tickers))
        logger.info(f"Using {num_workers} workers for feature engineering")

        feature_engineer = FeatureEngineer(
            self.db_manager,
            max_workers=num_workers
        )
        
        try:
            feature_engineer.process_all_features(
                tickers,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            return {
                "status": "success",
                "tickers_processed": len(tickers)
            }
        except Exception as e:
            logger.error(f"Error in feature engineering: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_data_for_date(self, ticker: str, as_of_date: date) -> Dict[str, Any]:
        """
        Get all available data for a ticker as of a specific date
        
        Args:
            ticker: Stock ticker symbol
            as_of_date: Date to get data for
            
        Returns:
            Dictionary with all available data
        """
        session = self.db_manager.get_session()
        
        try:
            # Get ticker ID
            from .database_manager import Ticker
            ticker_obj = session.query(Ticker).filter_by(
                symbol=ticker
            ).first()
            
            if not ticker_obj:
                return {"error": f"Ticker {ticker} not found"}
            
            # Get technical data - STRICT point-in-time to prevent lookahead bias
            # We use date < as_of_date (not <=) to EXCLUDE the prediction date itself
            # This ensures we only use data that would have been available BEFORE making the prediction
            from .database_manager import MarketData
            technical_data = session.query(MarketData).filter(
                MarketData.ticker_id == ticker_obj.ticker_id,
                MarketData.date < as_of_date  # CRITICAL: < not <= to prevent lookahead bias
            ).order_by(
                MarketData.date.desc()
            ).limit(30).all()  # Get last 30 trading days (changed from 90 to match requirement)

            # Validate no lookahead bias
            if technical_data and len(technical_data) > 0:
                latest_tech_date = max(t.date for t in technical_data)
                if latest_tech_date >= as_of_date:
                    logger.error(
                        f"CRITICAL: Lookahead bias detected for {ticker} on {as_of_date}. "
                        f"Technical data includes {latest_tech_date} which is >= prediction date."
                    )
                    # Don't return data with lookahead bias
                    return {"error": f"Lookahead bias detected - data integrity compromised"}

                # Log data window for transparency
                earliest_tech_date = min(t.date for t in technical_data)
                logger.debug(
                    f"{ticker} on {as_of_date}: Technical data window is {earliest_tech_date} to {latest_tech_date} "
                    f"({len(technical_data)} trading days, excludes prediction date)"
                )

            # Warn if we have fewer than expected trading days
            if technical_data and len(technical_data) < 30:
                logger.warning(
                    f"{ticker} on {as_of_date}: Only {len(technical_data)} trading days available "
                    f"(expected 30). This may occur near data collection start date."
                )
            
            # Get latest fundamentals - use strict point-in-time (filing_date < as_of_date)
            # Fundamentals are filed AFTER quarter end, so using < ensures we only use
            # data that was publicly available BEFORE the prediction date
            from .database_manager import Fundamental, News, MacroFeature
            fundamentals = session.query(Fundamental).filter(
                Fundamental.ticker_id == ticker_obj.ticker_id,
                Fundamental.filing_date < as_of_date  # Strict < to prevent lookahead bias
            ).order_by(
                Fundamental.filing_date.desc()
            ).first()

            # Log fundamental data age for monitoring
            if fundamentals:
                data_age_days = (as_of_date - fundamentals.filing_date).days
                if data_age_days > 180:
                    logger.warning(
                        f"{ticker} on {as_of_date}: Fundamental data is {data_age_days} days old "
                        f"(filing_date: {fundamentals.filing_date}). Data may be stale."
                    )
                elif data_age_days > 120:
                    logger.debug(
                        f"{ticker} on {as_of_date}: Fundamental data is {data_age_days} days old "
                        f"(filing_date: {fundamentals.filing_date})"
                    )
            else:
                logger.warning(
                    f"{ticker} on {as_of_date}: No fundamental data available before prediction date"
                )
            
            # Get news - use strict point-in-time (published_at < as_of_date)
            # Convert as_of_date to datetime for comparison with published_date
            as_of_datetime = datetime.combine(as_of_date, datetime.min.time()) if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime) else as_of_date

            # Two-phase news query strategy:
            # Phase 1: Get ALL articles from most recent 3 days with articles (for full content)
            # Phase 2: Get older articles (4-30 days) with limits (for headlines + summaries)

            # Phase 1: Find most recent 3 days that have articles
            recent_days_query = session.query(
                func.date(News.published_at).label('article_date')
            ).filter(
                News.ticker_id == ticker_obj.ticker_id,
                News.published_at < as_of_datetime  # Strict < to prevent lookahead bias
            ).distinct().order_by(
                func.date(News.published_at).desc()
            ).limit(3)

            recent_dates = [row.article_date for row in recent_days_query.all()]

            # Get ALL articles from those 3 recent days (no limit for recent articles)
            recent_news = []
            if recent_dates:
                recent_news = session.query(News).filter(
                    News.ticker_id == ticker_obj.ticker_id,
                    func.date(News.published_at).in_(recent_dates),
                    News.published_at < as_of_datetime  # Strict < to prevent lookahead bias
                ).order_by(
                    News.published_at.desc()  # Most recent first within these days
                ).all()

            # Phase 2: Get older articles (4-30 days back), limit to 75, sorted by confidence if available
            oldest_recent_date = min(recent_dates) if recent_dates else as_of_date
            older_news = session.query(News).filter(
                News.ticker_id == ticker_obj.ticker_id,
                News.published_at < datetime.combine(oldest_recent_date, datetime.min.time()),  # Before recent period
                News.published_at >= as_of_datetime - timedelta(days=30)  # Within 30 days
            ).order_by(
                # Sort by confidence if available (for better quality older articles), then by date
                News.sentiment_confidence.desc().nullslast(),
                News.published_at.desc()
            ).limit(75).all()

            # Combine recent (unlimited) + older (limited) news
            news = recent_news + older_news

            # Get 7-day sentiment aggregates for trend context - strict point-in-time
            from .database_manager import NewsSentimentFeature
            sentiment_features = session.query(NewsSentimentFeature).filter(
                NewsSentimentFeature.ticker_id == ticker_obj.ticker_id,
                NewsSentimentFeature.date < as_of_date,  # Strict < to prevent lookahead bias
                NewsSentimentFeature.date >= as_of_date - timedelta(days=7)
            ).order_by(
                NewsSentimentFeature.date.desc()
            ).all()

            # Get macro features - strict point-in-time
            from .database_manager import MacroFeature
            macro_features = session.query(MacroFeature).filter(
                MacroFeature.date < as_of_date  # Strict < to prevent lookahead bias
            ).order_by(
                MacroFeature.date.desc()
            ).first()

            # Get insider transactions (last 90 days) - strict point-in-time
            from .database_manager import InsiderTransaction
            insider_transactions = session.query(InsiderTransaction).filter(
                InsiderTransaction.ticker_id == ticker_obj.ticker_id,
                InsiderTransaction.transaction_date < as_of_date  # Strict < to prevent lookahead bias
            ).order_by(
                InsiderTransaction.transaction_date.desc()
            ).limit(20).all()
            
            # Serialize news with metadata about recent vs older
            news_data = {
                "recent_articles": [self._serialize_news(n, include_full_content=True) for n in recent_news],
                "older_articles": [self._serialize_news(n, include_full_content=False) for n in older_news],
                "recent_dates": [d.isoformat() for d in recent_dates] if recent_dates else []
            }

            return {
                "ticker": ticker,
                "date": as_of_date,
                "technical": [self._serialize_technical(t) for t in technical_data],
                "fundamentals": self._serialize_fundamentals(fundamentals) if fundamentals else None,
                "news": news_data,  # New structured format
                "news_sentiment_features": self._serialize_sentiment_features(sentiment_features),
                "news_summary": self._build_news_summary(news, sentiment_features),
                "macro_features": self._serialize_macro_features(macro_features) if macro_features else None,
                "insider_transactions": [self._serialize_insider_transaction(t) for t in insider_transactions],
            }
            
        except Exception as e:
            logger.error(f"Error getting data for {ticker} on {as_of_date}: {e}", exc_info=True)
            return {"error": str(e)}
        finally:
            session.close()
    
    def _serialize_technical(self, technical) -> Dict[str, Any]:
        """Serialize technical data record with all available indicators"""
        return {
            "date": technical.date,
            "open": float(technical.open),
            "high": float(technical.high),
            "low": float(technical.low),
            "close": float(technical.close),
            "adjusted_close": float(technical.adjusted_close) if technical.adjusted_close else None,
            "volume": technical.volume,
            # Technical Indicators
            "sma_20": float(technical.sma_20) if technical.sma_20 else None,
            "sma_50": float(technical.sma_50) if technical.sma_50 else None,
            "ema_20": float(technical.ema_20) if technical.ema_20 else None,
            "rsi_14": float(technical.rsi_14) if technical.rsi_14 else None,
            "macd": float(technical.macd) if technical.macd else None,
            "macd_signal": float(technical.macd_signal) if technical.macd_signal else None,
            "bollinger_upper": float(technical.bollinger_upper) if technical.bollinger_upper else None,
            "bollinger_lower": float(technical.bollinger_lower) if technical.bollinger_lower else None,
        }
    
    def _serialize_fundamentals(self, fundamentals) -> Dict[str, Any]:
        """Serialize fundamentals record"""
        return {
            "report_date": fundamentals.report_date,
            "filing_date": fundamentals.filing_date,
            "market_cap": fundamentals.market_cap,
            "pe_ratio": float(fundamentals.pe_ratio) if fundamentals.pe_ratio else None,
            "eps": float(fundamentals.eps) if fundamentals.eps else None,
            "revenue": fundamentals.revenue,
            "net_income": fundamentals.net_income,
            "operating_income": fundamentals.operating_income,
            "total_assets": fundamentals.total_assets,
            "total_liabilities": fundamentals.total_liabilities,
            "stockholder_equity": fundamentals.stockholder_equity,
            "total_debt": fundamentals.total_debt,
            "cash_and_equivalents": fundamentals.cash_and_equivalents,
            "revenue_qoq_change": float(fundamentals.revenue_qoq_pct) if fundamentals.revenue_qoq_pct else None,
            "revenue_yoy_change": float(fundamentals.revenue_yoy_pct) if fundamentals.revenue_yoy_pct else None,
        }
    
    def _serialize_news(self, news, include_full_content: bool = False) -> Dict[str, Any]:
        """
        Serialize news record with conditional content inclusion

        Args:
            news: News database record
            include_full_content: If True, include full article content. If False, include only headline + summary

        Returns:
            Serialized news article with appropriate content level
        """
        article_data = {
            "published_at": news.published_at,
            "headline": news.headline,
            "source": news.source,
            "url": news.url,
            # ✅ Fix: Check 'is not None' to preserve 0 as valid value
            "sentiment_score": float(news.sentiment_score) if news.sentiment_score is not None else None,
            "sentiment_label": news.sentiment_label if hasattr(news, 'sentiment_label') else None,
            # ✅ Fix: Check 'is not None' to preserve 0 as valid value
            "sentiment_confidence": float(news.sentiment_confidence) if news.sentiment_confidence is not None else None,
        }

        # Conditionally include full content or summary based on recency
        if include_full_content:
            # For recent articles (3 most recent days): include full content
            article_data["content"] = news.content if news.content else news.summary
        else:
            # For older articles (4-30 days): include only summary (or first 200 chars of content)
            if news.summary:
                article_data["summary"] = news.summary
            elif news.content:
                article_data["summary"] = news.content[:200] + "..." if len(news.content) > 200 else news.content
            else:
                article_data["summary"] = None

        return article_data

    def _serialize_sentiment_features(self, features) -> List[Dict[str, Any]]:
        """Serialize sentiment aggregates for trend analysis"""
        return [
            {
                "date": f.date,
                "sentiment_7day_avg": float(f.sentiment_7day_avg) if f.sentiment_7day_avg else 0.0,
                "sentiment_7day_count": f.sentiment_7day_count,
                "daily_article_count": f.daily_article_count
            }
            for f in features
        ]

    def _build_news_summary(self, news_list, sentiment_features) -> Dict[str, Any]:
        """Build news sentiment summary for easy prompt inclusion"""
        if not news_list:
            return {
                "total_articles": 0,
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "avg_sentiment": 0.0,
                "avg_confidence": 0.0,
                "trend_direction": "neutral",
                "recent_sentiment": 0.0
            }

        # Calculate distribution
        positive = sum(1 for n in news_list if n.sentiment_label == "positive")
        negative = sum(1 for n in news_list if n.sentiment_label == "negative")
        neutral = sum(1 for n in news_list if n.sentiment_label == "neutral")

        # Calculate averages
        avg_sentiment = sum(float(n.sentiment_score) for n in news_list if n.sentiment_score) / len(news_list)
        avg_confidence = sum(float(n.sentiment_confidence or 0.5) for n in news_list) / len(news_list)

        # Determine trend from features
        trend_direction = "neutral"
        if len(sentiment_features) >= 2:
            recent_avg = float(sentiment_features[0].sentiment_7day_avg or 0)
            previous_avg = float(sentiment_features[1].sentiment_7day_avg or 0)
            if recent_avg > previous_avg + 0.05:
                trend_direction = "improving"
            elif recent_avg < previous_avg - 0.05:
                trend_direction = "declining"

        return {
            "total_articles": len(news_list),
            "sentiment_distribution": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            },
            "avg_sentiment": round(avg_sentiment, 3),
            "avg_confidence": round(avg_confidence, 3),
            "trend_direction": trend_direction,
            "recent_sentiment": float(sentiment_features[0].sentiment_7day_avg or 0) if sentiment_features else 0.0,
            "articles_last_7_days": sum(f.daily_article_count for f in sentiment_features) if sentiment_features else 0
        }

    def _serialize_macro_features(self, macro) -> Dict[str, Any]:
        """Serialize macro features record"""
        return {
            "date": macro.date,
            "yield_curve_10y_2y": float(macro.yield_curve_10y_2y) if macro.yield_curve_10y_2y else None,
            "cpi_monthly_pct": float(macro.cpi_monthly_pct) if macro.cpi_monthly_pct else None,
            "gdp_qoq_pct": float(macro.gdp_qoq_pct) if macro.gdp_qoq_pct else None,
            "unemployment_rate_change": float(macro.unemployment_rate_change) if macro.unemployment_rate_change else None,
        }
    
    def _serialize_insider_transaction(self, insider) -> Dict[str, Any]:
        """Serialize insider transaction record"""
        return {
            "transaction_date": insider.transaction_date,
            "owner_name": insider.owner_name,
            "transaction_code": insider.transaction_code,
            "shares": insider.shares,
            "transaction_price": float(insider.transaction_price) if insider.transaction_price else None,
            "transaction_amount": float(insider.transaction_amount) if insider.transaction_amount else None,
            "price": float(insider.transaction_price) if insider.transaction_price else None,  # Alias for backward compatibility
            "amount": float(insider.transaction_amount) if insider.transaction_amount else None,  # Alias for backward compatibility
            "shares_owned_after": insider.shares_owned_after,
        }