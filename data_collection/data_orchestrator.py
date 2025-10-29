"""
Data collection orchestrator for Fireworks-Charlie
Wraps data collection functionality for RLVR training
"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from .database_manager import DatabaseManager
from .data_processor import DataProcessor
from .eodhd_client import EODHDClient
from .fred_client import FREDClient
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
    
    def collect_data_for_ticker(self, ticker: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Collect all data for a single ticker over a date range
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            Dictionary with collected data status
        """
        logger.info(f"Collecting data for {ticker} from {start_date} to {end_date}")
        
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
            
            # 2. Fetch and process Technical Market Data
            if self.eodhd_client:
                eod_raw = self.eodhd_client.get_eod_data(
                    f"{ticker}.US", 
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d")
                )
                eod_processed = processor.process_eod_data(eod_raw, f"{ticker}.US")
                
                # Add ticker_id to each record for the insert method
                for record in eod_processed:
                    record["ticker_id"] = ticker_obj.ticker_id
                self.db_manager.insert_technical_market_data(session, eod_processed)
                session.commit()
                logger.info(f"Stored {len(eod_processed)} technical market records")
            
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
                news_raw = self.eodhd_client.get_news(
                    f"{ticker}.US", 
                    start_date.strftime("%Y-%m-%d"), 
                    end_date.strftime("%Y-%m-%d")
                )
                news_processed = processor.process_news(news_raw, f"{ticker}.US")
                
                # Add ticker_id to each article for the insert method
                for article in news_processed:
                    article["ticker_id"] = ticker_obj.ticker_id
                self.db_manager.insert_news(session, news_processed)
                session.commit()
                logger.info(f"Stored {len(news_processed)} news articles")
            
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
            
            return {
                "status": "success",
                "ticker": ticker,
                "ticker_id": ticker_obj.ticker_id,
                "records": {
                    "technical": len(eod_processed) if self.eodhd_client else 0,
                    "news": len(news_processed) if self.eodhd_client else 0,
                    "insider": len(insider_processed) if self.eodhd_client else 0,
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
        
        feature_engineer = FeatureEngineer(
            self.db_manager,
            max_workers=self.config.PARALLEL_WORKERS
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
            
            # Get technical data (expanded from 15 to 90 days)
            from .database_manager import MarketData
            technical_data = session.query(MarketData).filter(
                MarketData.ticker_id == ticker_obj.ticker_id,
                MarketData.date <= as_of_date
            ).order_by(
                MarketData.date.desc()
            ).limit(90).all()  # Get last 90 days
            
            # Get latest fundamentals
            from .database_manager import Fundamental, News, MacroFeatures
            fundamentals = session.query(Fundamental).filter(
                Fundamental.ticker_id == ticker_obj.ticker_id,
                Fundamental.filing_date <= as_of_date
            ).order_by(
                Fundamental.filing_date.desc()
            ).first()
            
            # Get news
            # Convert as_of_date to datetime for comparison with published_date
            as_of_datetime = datetime.combine(as_of_date, datetime.min.time()) if isinstance(as_of_date, date) and not isinstance(as_of_date, datetime) else as_of_date
            news = session.query(News).filter(
                News.ticker_id == ticker_obj.ticker_id,
                News.published_at <= as_of_datetime,
                News.published_at >= as_of_datetime - timedelta(days=60)
            ).order_by(
                News.published_at.desc()
            ).all()
            
            # Get macro features
            from .database_manager import MacroFeature
            macro_features = session.query(MacroFeature).filter(
                MacroFeature.date <= as_of_date
            ).order_by(
                MacroFeature.date.desc()
            ).first()
            
            # Get insider transactions (last 90 days)
            from .database_manager import InsiderTransaction
            insider_transactions = session.query(InsiderTransaction).filter(
                InsiderTransaction.ticker_id == ticker_obj.ticker_id,
                InsiderTransaction.transaction_date <= as_of_date
            ).order_by(
                InsiderTransaction.transaction_date.desc()
            ).limit(20).all()
            
            return {
                "ticker": ticker,
                "date": as_of_date,
                "technical": [self._serialize_technical(t) for t in technical_data],
                "fundamentals": self._serialize_fundamentals(fundamentals) if fundamentals else None,
                "news": [self._serialize_news(n) for n in news],
                "macro_features": self._serialize_macro_features(macro_features) if macro_features else None,
                "insider_transactions": [self._serialize_insider_transaction(t) for t in insider_transactions],
            }
            
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
            "revenue_qoq_change": float(fundamentals.revenue_qoq_change) if fundamentals.revenue_qoq_change else None,
            "revenue_yoy_change": float(fundamentals.revenue_yoy_change) if fundamentals.revenue_yoy_change else None,
        }
    
    def _serialize_news(self, news) -> Dict[str, Any]:
        """Serialize news record"""
        return {
            "published_at": news.published_at,
            "headline": news.headline,
            "summary": news.content,
            "sentiment_score": float(news.sentiment_score) if news.sentiment_score else None,
            "sentiment_label": news.sentiment_label if hasattr(news, 'sentiment_label') else news.sentiment,
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
            "price": float(insider.price) if insider.price else None,
            "amount": float(insider.amount) if insider.amount else None,
            "shares_owned_after": insider.shares_owned_after,
        }