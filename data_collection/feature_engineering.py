"""
Feature Engineering Module for Charlie-TR1-DB

This module provides feature engineering capabilities for time-series forecasting,
including technical indicators, news sentiment aggregation, fundamental changes,
and macroeconomic derived features.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .database_manager import (
    DatabaseManager, Ticker, TechnicalMarketData, Fundamental,
    News, InsiderTransaction, MacroeconomicIndicator,
    NewsFeatures, MacroFeatures
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Feature engineering class for calculating derived features for time-series forecasting.
    """

    def __init__(self, db_manager: DatabaseManager, max_workers: int = 2):
        """
        Initialize the feature engineer.

        Args:
            db_manager: Database manager instance
            max_workers: Maximum number of threads for parallel processing
        """
        self.db_manager = db_manager
        self.max_workers = max_workers

    def process_all_features(self, tickers: List[str], start_date: str, end_date: str) -> None:
        """
        Process all features for given tickers and date range using parallel processing.

        Args:
            tickers: List of ticker symbols
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
        """
        logger.info(f"Starting feature engineering for {len(tickers)} tickers with {self.max_workers} threads")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit feature engineering tasks
            future_to_ticker = {}
            for ticker in tickers:
                future = executor.submit(self._process_ticker_features, ticker, start_date, end_date)
                future_to_ticker[future] = ticker

            # Collect results
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    future.result()
                    logger.info(f"Completed feature engineering for {ticker}")
                except Exception as e:
                    logger.error(f"Feature engineering failed for {ticker}: {e}")

        # Process global features (macro, rolling aggregations)
        logger.info("Processing global features...")
        self._process_macro_features(start_date, end_date)
        self._process_rolling_news_features(tickers, start_date, end_date)

    def _process_ticker_features(self, ticker: str, start_date: str, end_date: str) -> None:
        """Process all features for a single ticker."""
        session = self.db_manager.get_session()
        try:
            # Get ticker ID
            ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
            if not ticker_obj:
                logger.warning(f"Ticker {ticker} not found in database")
                return

            ticker_id = ticker_obj.ticker_id

            # Calculate technical indicators
            self._calculate_technical_indicators(session, ticker_id, start_date, end_date)

            # Calculate fundamental changes
            self._calculate_fundamental_changes(session, ticker_id)

            # Calculate event-based features
            self._calculate_event_features(session, ticker_id, start_date, end_date)

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error processing features for {ticker}: {e}")
            raise
        finally:
            session.close()

    def _calculate_technical_indicators(self, session, ticker_id: int, start_date: str, end_date: str) -> None:
        """
        Calculate technical indicators: SMA(20), EMA(20), RSI(14)
        """
        # Get technical data sorted by date
        tech_data = session.query(TechnicalMarketData)\
            .filter(
                TechnicalMarketData.ticker_id == ticker_id,
                TechnicalMarketData.date >= start_date,
                TechnicalMarketData.date <= end_date
            )\
            .order_by(TechnicalMarketData.date)\
            .all()

        if not tech_data:
            return

        # Convert to DataFrame for calculations
        df = pd.DataFrame([{
            'tech_data_id': td.tech_data_id,
            'date': td.date,
            'close': float(td.close)
        } for td in tech_data])

        # Calculate indicators
        df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)

        # Update database
        for _, row in df.iterrows():
            tech_record = session.query(TechnicalMarketData)\
                .filter_by(tech_data_id=row['tech_data_id'])\
                .first()

            if tech_record:
                # Update legacy fields
                tech_record.sma = row['sma_20']
                tech_record.ema = row['ema_20']
                tech_record.rsi = row['rsi_14']
                # Update specific period fields for Trainer-Charlie
                tech_record.sma_20 = row['sma_20']
                tech_record.ema_20 = row['ema_20']
                tech_record.rsi_14 = row['rsi_14']

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_fundamental_changes(self, session, ticker_id: int) -> None:
        """
        Calculate QoQ and YoY changes for fundamental metrics.
        """
        fundamentals = session.query(Fundamental)\
            .filter_by(ticker_id=ticker_id)\
            .order_by(Fundamental.report_date)\
            .all()

        if len(fundamentals) < 2:
            return

        # Create DataFrame for calculations
        df = pd.DataFrame([{
            'fundamental_id': f.fundamental_id,
            'report_date': f.report_date,
            'revenue': f.revenue,
            'net_income': f.net_income,
            'operating_income': f.operating_income
        } for f in fundamentals])

        df['report_date'] = pd.to_datetime(df['report_date'])

        # Calculate QoQ changes
        df['revenue_qoq'] = df['revenue'].pct_change()
        df['net_income_qoq'] = df['net_income'].pct_change()
        df['operating_income_qoq'] = df['operating_income'].pct_change()

        # Calculate YoY changes (compare to same quarter previous year)
        df['quarter'] = df['report_date'].dt.quarter
        df['year'] = df['report_date'].dt.year

        for idx, row in df.iterrows():
            # Find same quarter previous year
            prev_year = row['year'] - 1
            prev_year_data = df[(df['year'] == prev_year) & (df['quarter'] == row['quarter'])]

            if not prev_year_data.empty:
                prev_row = prev_year_data.iloc[0]
                df.at[idx, 'revenue_yoy'] = (row['revenue'] - prev_row['revenue']) / abs(prev_row['revenue']) if prev_row['revenue'] else None
                df.at[idx, 'net_income_yoy'] = (row['net_income'] - prev_row['net_income']) / abs(prev_row['net_income']) if prev_row['net_income'] else None
                df.at[idx, 'operating_income_yoy'] = (row['operating_income'] - prev_row['operating_income']) / abs(prev_row['operating_income']) if prev_row['operating_income'] else None

        # Update database
        for _, row in df.iterrows():
            fund_record = session.query(Fundamental)\
                .filter_by(fundamental_id=row['fundamental_id'])\
                .first()

            if fund_record:
                fund_record.revenue_qoq_change = row.get('revenue_qoq')
                fund_record.net_income_qoq_change = row.get('net_income_qoq')
                fund_record.operating_income_qoq_change = row.get('operating_income_qoq')
                fund_record.revenue_yoy_change = row.get('revenue_yoy')
                fund_record.net_income_yoy_change = row.get('net_income_yoy')
                fund_record.operating_income_yoy_change = row.get('operating_income_yoy')

    def _calculate_event_features(self, session, ticker_id: int, start_date: str, end_date: str) -> None:
        """
        Calculate event-based features: days since last news/insider trade.
        """
        # Get technical data dates
        tech_dates = session.query(TechnicalMarketData.date)\
            .filter(
                TechnicalMarketData.ticker_id == ticker_id,
                TechnicalMarketData.date >= start_date,
                TechnicalMarketData.date <= end_date
            )\
            .order_by(TechnicalMarketData.date)\
            .all()

        tech_dates = [td[0] for td in tech_dates]

        if not tech_dates:
            return

        # Get news and insider trade dates
        news_dates = session.query(News.published_date)\
            .filter(News.ticker_id == ticker_id)\
            .order_by(News.published_date)\
            .all()
        news_dates = [nd[0].date() for nd in news_dates]

        insider_dates = session.query(InsiderTransaction.transaction_date)\
            .filter(InsiderTransaction.ticker_id == ticker_id)\
            .order_by(InsiderTransaction.transaction_date)\
            .all()
        insider_dates = [id[0] for id in insider_dates]

        # Calculate days since last events for each technical data date
        for tech_date in tech_dates:
            # Days since last news
            news_before = [d for d in news_dates if d <= tech_date]
            days_since_news = (tech_date - max(news_before)).days if news_before else None

            # Days since last insider trade
            insider_before = [d for d in insider_dates if d <= tech_date]
            days_since_insider = (tech_date - max(insider_before)).days if insider_before else None

            # Update technical record
            tech_record = session.query(TechnicalMarketData)\
                .filter_by(ticker_id=ticker_id, date=tech_date)\
                .first()

            if tech_record:
                tech_record.days_since_last_insider_trade = days_since_insider

            # Update news records with days since last news
            # Convert tech_date (date) to datetime for comparison
            tech_datetime = datetime.combine(tech_date, datetime.min.time())
            news_records = session.query(News)\
                .filter(News.ticker_id == ticker_id, News.published_date >= tech_datetime)\
                .all()

            for news_record in news_records:
                news_record.days_since_last_news = days_since_news

    def _process_macro_features(self, start_date: str, end_date: str) -> None:
        """
        Calculate macroeconomic derived features.
        """
        session = self.db_manager.get_session()

        try:
            # Get date range
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()

            current_date = start
            while current_date <= end:
                self._calculate_macro_features_for_date(session, current_date)
                current_date += timedelta(days=1)

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error processing macro features: {e}")
            raise
        finally:
            session.close()

    def _calculate_macro_features_for_date(self, session, date):
        """
        Calculate macro features for a specific date.
        """
        # Get macro indicators for this date and recent history
        macro_data = session.query(MacroeconomicIndicator)\
            .filter(MacroeconomicIndicator.date <= date)\
            .order_by(MacroeconomicIndicator.date.desc())\
            .limit(100)\
            .all()

        if not macro_data:
            return

        # Group by indicator
        indicators = {}
        for m in macro_data:
            if m.indicator_name not in indicators:
                indicators[m.indicator_name] = []
            indicators[m.indicator_name].append((m.date, float(m.value)))

        # Calculate features
        features = {
            'date': date,
            'yield_curve_spread': self._calculate_yield_spread(indicators, date),
            'cpi_monthly_change': self._calculate_cpi_change(indicators, date, 'monthly'),
            'cpi_annualized_change': self._calculate_cpi_change(indicators, date, 'annualized'),
            'pce_monthly_change': self._calculate_pce_change(indicators, date, 'monthly'),
            'pce_annualized_change': self._calculate_pce_change(indicators, date, 'annualized'),
            'gdp_quarterly_change': self._calculate_gdp_change(indicators, date),
            'industrial_production_monthly_change': self._calculate_industrial_production_change(indicators, date),
            'unemployment_rate_change': self._calculate_unemployment_change(indicators, date)
        }

        # Upsert to database
        existing = session.query(MacroFeatures).filter_by(date=date).first()
        if existing:
            for key, value in features.items():
                if key != 'date':
                    setattr(existing, key, value)
        else:
            session.add(MacroFeatures(**features))

    def _calculate_yield_spread(self, indicators: Dict, date) -> Optional[float]:
        """Calculate 10Y - 2Y Treasury yield spread."""
        try:
            treasury_10y = indicators.get('Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Quoted on an Investment Basis', [])
            treasury_2y = indicators.get('Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity, Quoted on an Investment Basis', [])

            # Find most recent values on or before the date
            yield_10y = next((v for d, v in treasury_10y if d <= date), None)
            yield_2y = next((v for d, v in treasury_2y if d <= date), None)

            return yield_10y - yield_2y if yield_10y is not None and yield_2y is not None else None
        except:
            return None

    def _calculate_cpi_change(self, indicators: Dict, date, change_type: str) -> Optional[float]:
        """Calculate CPI changes (monthly or annualized)."""
        try:
            cpi_data = indicators.get('Consumer Price Index for All Urban Consumers: All Items in U.S. City Average', [])

            if len(cpi_data) < 2:
                return None

            # Get current and previous values
            current = next((v for d, v in cpi_data if d <= date), None)
            prev_monthly = next((v for d, v in cpi_data if d <= date - timedelta(days=30)), None)

            if current is None or prev_monthly is None:
                return None

            monthly_change = (current - prev_monthly) / prev_monthly

            if change_type == 'monthly':
                return monthly_change
            else:  # annualized
                return monthly_change * 12

        except:
            return None

    def _calculate_pce_change(self, indicators: Dict, date, change_type: str) -> Optional[float]:
        """Calculate PCE changes (monthly or annualized)."""
        try:
            pce_data = indicators.get('Personal Consumption Expenditures: Chain-type Price Index', [])

            if len(pce_data) < 2:
                return None

            current = next((v for d, v in pce_data if d <= date), None)
            prev_monthly = next((v for d, v in pce_data if d <= date - timedelta(days=30)), None)

            if current is None or prev_monthly is None:
                return None

            monthly_change = (current - prev_monthly) / prev_monthly

            if change_type == 'monthly':
                return monthly_change
            else:  # annualized
                return monthly_change * 12

        except:
            return None

    def _calculate_gdp_change(self, indicators: Dict, date) -> Optional[float]:
        """Calculate quarterly GDP change."""
        try:
            gdp_data = indicators.get('Real Gross Domestic Product', [])

            if len(gdp_data) < 2:
                return None

            # Find current quarter and previous quarter
            current_quarter = next((v for d, v in gdp_data if d <= date), None)

            # Approximate previous quarter (about 90 days ago)
            prev_quarter = next((v for d, v in gdp_data if d <= date - timedelta(days=90)), None)

            if current_quarter is None or prev_quarter is None:
                return None

            return (current_quarter - prev_quarter) / abs(prev_quarter)

        except:
            return None

    def _calculate_industrial_production_change(self, indicators: Dict, date) -> Optional[float]:
        """Calculate monthly industrial production change."""
        try:
            ip_data = indicators.get('Industrial Production: Total Index', [])

            if len(ip_data) < 2:
                return None

            current = next((v for d, v in ip_data if d <= date), None)
            prev_monthly = next((v for d, v in ip_data if d <= date - timedelta(days=30)), None)

            if current is None or prev_monthly is None:
                return None

            return (current - prev_monthly) / prev_monthly

        except:
            return None

    def _calculate_unemployment_change(self, indicators: Dict, date) -> Optional[float]:
        """Calculate unemployment rate change."""
        try:
            unemployment_data = indicators.get('Unemployment Rate', [])

            if len(unemployment_data) < 2:
                return None

            current = next((v for d, v in unemployment_data if d <= date), None)
            prev_monthly = next((v for d, v in unemployment_data if d <= date - timedelta(days=30)), None)

            if current is None or prev_monthly is None:
                return None

            return current - prev_monthly  # Absolute change in percentage points

        except:
            return None

    def _process_rolling_news_features(self, tickers: List[str], start_date: str, end_date: str) -> None:
        """
        Calculate rolling window news sentiment features.
        """
        session = self.db_manager.get_session()

        try:
            for ticker in tickers:
                ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
                if not ticker_obj:
                    continue

                self._calculate_rolling_sentiment(session, ticker_obj.ticker_id, start_date, end_date)

            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error processing rolling news features: {e}")
            raise
        finally:
            session.close()

    def _calculate_rolling_sentiment(self, session, ticker_id: int, start_date: str, end_date: str) -> None:
        """
        Calculate 7-day rolling sentiment averages.
        """
        # Get all news for this ticker in date range
        news_data = session.query(News)\
            .filter(
                News.ticker_id == ticker_id,
                News.published_date >= start_date,
                News.published_date <= end_date
            )\
            .order_by(News.published_date)\
            .all()

        if not news_data:
            return

        # Create DataFrame
        df = pd.DataFrame([{
            'date': n.published_date.date(),
            'sentiment_score': float(n.sentiment_score) if n.sentiment_score else 0.0  # Fill neutral for missing
        } for n in news_data])

        # Group by date and calculate daily averages
        daily_sentiment = df.groupby('date')['sentiment_score'].agg(['mean', 'count']).reset_index()
        daily_sentiment.columns = ['date', 'daily_avg', 'daily_count']

        # Calculate 7-day rolling averages
        daily_sentiment = daily_sentiment.sort_values('date')
        daily_sentiment['sentiment_7day_avg'] = daily_sentiment['daily_avg'].rolling(window=7, min_periods=1).mean()
        daily_sentiment['sentiment_7day_count'] = daily_sentiment['daily_count'].rolling(window=7, min_periods=1).sum()

        # Upsert to database
        for _, row in daily_sentiment.iterrows():
            existing = session.query(NewsFeatures)\
                .filter_by(ticker_id=ticker_id, date=row['date'])\
                .first()

            if existing:
                existing.sentiment_7day_avg = row['sentiment_7day_avg']
                existing.sentiment_7day_count = row['sentiment_7day_count']
            else:
                session.add(NewsFeatures(
                    ticker_id=ticker_id,
                    date=row['date'],
                    sentiment_7day_avg=row['sentiment_7day_avg'],
                    sentiment_7day_count=row['sentiment_7day_count']
                ))