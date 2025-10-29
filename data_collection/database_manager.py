import logging
import json
from typing import Any, Dict, Optional

import sqlalchemy
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.sql.sqltypes import DECIMAL, JSON

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


# Define the database models
class Ticker(Base):
    __tablename__ = "Tickers"
    ticker_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))

    technical_data: Mapped[list["TechnicalMarketData"]] = relationship(
        "TechnicalMarketData", back_populates="ticker"
    )
    fundamentals: Mapped[list["Fundamental"]] = relationship(
        "Fundamental", back_populates="ticker"
    )
    news: Mapped[list["News"]] = relationship("News", back_populates="ticker")
    insider_transactions: Mapped[list["InsiderTransaction"]] = relationship(
        "InsiderTransaction", back_populates="ticker"
    )


class TechnicalMarketData(Base):
    __tablename__ = "Technical_Market_Data"
    tech_data_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tickers.ticker_id"), nullable=False)
    date: Mapped[Any] = mapped_column(Date, nullable=False)
    timestamp: Mapped[Optional[Any]] = mapped_column(DateTime)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    open: Mapped[Any] = mapped_column(DECIMAL(18, 4), nullable=False)
    high: Mapped[Any] = mapped_column(DECIMAL(18, 4), nullable=False)
    low: Mapped[Any] = mapped_column(DECIMAL(18, 4), nullable=False)
    close: Mapped[Any] = mapped_column(DECIMAL(18, 4), nullable=False)
    adjusted_close: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Legacy fields (kept for compatibility)
    sma: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    ema: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    rsi: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    macd: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    # Specific period indicators for Trainer-Charlie
    sma_20: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    ema_20: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    rsi_14: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    days_since_last_insider_trade: Mapped[Optional[int]] = mapped_column(Integer)

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="technical_data")


class Fundamental(Base):
    __tablename__ = "Fundamentals"
    fundamental_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tickers.ticker_id"), nullable=False)
    report_date: Mapped[Any] = mapped_column(Date, nullable=False)  # Quarter end date
    filing_date: Mapped[Any] = mapped_column(Date, nullable=False)  # SEC filing date (when it became public)
    market_cap: Mapped[Optional[int]] = mapped_column(BigInteger)
    pe_ratio: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    eps: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    book_value: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))
    revenue: Mapped[Optional[int]] = mapped_column(BigInteger)  # Quarterly revenue
    net_income: Mapped[Optional[int]] = mapped_column(BigInteger)  # Quarterly net income
    total_assets: Mapped[Optional[int]] = mapped_column(BigInteger)  # From balance sheet
    total_liabilities: Mapped[Optional[int]] = mapped_column(BigInteger)  # From balance sheet
    stockholder_equity: Mapped[Optional[int]] = mapped_column(BigInteger)  # From balance sheet
    operating_income: Mapped[Optional[int]] = mapped_column(BigInteger)  # From income statement
    gross_profit: Mapped[Optional[int]] = mapped_column(BigInteger)  # From income statement
    balance_sheet_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Full quarterly data
    income_statement_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Full quarterly data
    cash_flow_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)  # Full quarterly data

    # QoQ changes (quarter-over-quarter)
    revenue_qoq_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    net_income_qoq_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    operating_income_qoq_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))

    # YoY changes (year-over-year)
    revenue_yoy_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    net_income_yoy_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))
    operating_income_yoy_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(10, 4))

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="fundamentals")


class News(Base):
    __tablename__ = "News"
    news_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tickers.ticker_id"), nullable=False)
    published_date: Mapped[Any] = mapped_column(DateTime, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50))
    sentiment_score: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 2))  # Sentiment polarity score
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(50))  # Label: positive/negative/neutral
    days_since_last_news: Mapped[Optional[int]] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="news")
    
    # Property aliases for Trainer-Charlie compatibility
    @property
    def published_at(self):
        return self.published_date
    
    @property
    def headline(self):
        return self.title
    
    @property
    def summary(self):
        return self.content
    
    @property
    def sentiment_polarity(self):
        return self.sentiment_score


class InsiderTransaction(Base):
    __tablename__ = "Insider_Transactions"
    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tickers.ticker_id"), nullable=False)
    transaction_date: Mapped[Any] = mapped_column(Date, nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    transaction_code: Mapped[str] = mapped_column(String(10), nullable=False)
    transaction_amount: Mapped[Optional[int]] = mapped_column(BigInteger)  # Can be null per API data
    transaction_price: Mapped[Optional[Any]] = mapped_column(DECIMAL(18, 4))

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="insider_transactions")


class MacroeconomicIndicator(Base):
    __tablename__ = "Macroeconomic_Indicators"
    macro_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(50), nullable=False)  # FRED series ID (e.g., GDPC1, UNRATE)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[Any] = mapped_column(Date, nullable=False)
    value: Mapped[Any] = mapped_column(DECIMAL(20, 4), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(100))  # Increased from 50 to 100 for longer unit names
    frequency: Mapped[Optional[str]] = mapped_column(String(20))  # Daily, Monthly, Quarterly, Annual, etc.

    # Unique constraint on series_id + date (one value per series per date)
    __table_args__ = (
        sqlalchemy.UniqueConstraint('series_id', 'date', name='uix_series_date'),
    )


class NewsFeatures(Base):
    """Rolling window features for news sentiment analysis."""
    __tablename__ = "News_Features"
    feature_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("Tickers.ticker_id"), nullable=False)
    date: Mapped[Any] = mapped_column(Date, nullable=False)
    sentiment_7day_avg: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 2))
    sentiment_7day_count: Mapped[int] = mapped_column(Integer, default=0)

    ticker: Mapped["Ticker"] = relationship("Ticker")


class MacroFeatures(Base):
    """Derived macroeconomic indicators and changes."""
    __tablename__ = "Macro_Features"
    feature_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[Any] = mapped_column(Date, nullable=False, unique=True)

    # Yield curve
    yield_curve_spread: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))  # 10Y - 2Y

    # Inflation measures
    cpi_monthly_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))
    cpi_annualized_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))
    pce_monthly_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))
    pce_annualized_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))

    # Economic growth
    gdp_quarterly_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))
    industrial_production_monthly_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))

    # Labor market
    unemployment_rate_change: Mapped[Optional[Any]] = mapped_column(DECIMAL(5, 4))


class DatabaseManager:
    """
    Manages database connections and data insertion for Charlie-TR1-DB.
    Uses SQLAlchemy for ORM capabilities.
    """

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)  # Create tables if they don't exist
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        """Returns a new SQLAlchemy session."""
        return self.Session()

    def insert_ticker(
        self,
        session,
        symbol: str,
        exchange: str,
        company_name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> Ticker:
        ticker = session.query(Ticker).filter_by(symbol=symbol).first()
        if not ticker:
            ticker = Ticker(
                symbol=symbol,
                exchange=exchange,
                company_name=company_name,
                sector=sector,
                industry=industry,
            )
            session.add(ticker)
            session.flush()  # Flush to get ticker_id
            logger.info(f"Inserted new ticker: {symbol}")
        else:
            logger.debug(f"Ticker {symbol} already exists, skipping insertion.")
        return ticker

    def insert_technical_market_data(self, session, data: list):
        for item in data:
            ticker = session.query(Ticker).filter_by(symbol=item["symbol"]).first()
            if ticker:
                # Check for existing entry to prevent duplicates based on ticker_id, date, and interval
                existing = (
                    session.query(TechnicalMarketData)
                    .filter_by(
                        ticker_id=ticker.ticker_id,
                        date=item["date"],
                        interval=item["interval"],
                    )
                    .first()
                )
                if not existing:
                    tech_data = TechnicalMarketData(
                        ticker_id=ticker.ticker_id,
                        date=item["date"],
                        timestamp=item.get("timestamp"),
                        interval=item["interval"],
                        open=item["open"],
                        high=item["high"],
                        low=item["low"],
                        close=item["close"],
                        adjusted_close=item.get("adjusted_close"),
                        volume=item["volume"],
                        sma=item.get("sma"),
                        ema=item.get("ema"),
                        rsi=item.get("rsi"),
                        macd=item.get("macd"),
                    )
                    session.add(tech_data)
                else:
                    logger.debug(
                        f"Technical data for {item['symbol']} on {item['date']} ({item['interval']}) already exists, skipping."
                    )
            else:
                logger.warning(
                    f"Ticker {item['symbol']} not found for technical market data insertion."
                )

    def insert_fundamentals(self, session, data_list: list):
        """
        Insert fundamental records. Now accepts a list of records (one per quarter).
        Each record should have symbol, report_date, filing_date, and financial metrics.
        """
        if not data_list:
            return

        # Handle both list and single dict for backward compatibility
        if isinstance(data_list, dict):
            data_list = [data_list]

        for data in data_list:
            ticker = session.query(Ticker).filter_by(symbol=data["symbol"]).first()
            if not ticker:
                logger.warning(
                    f"Ticker {data['symbol']} not found for fundamentals insertion."
                )
                continue

            # Check for existing entry to prevent duplicates
            # Now using both report_date AND filing_date for uniqueness
            existing = (
                session.query(Fundamental)
                .filter_by(
                    ticker_id=ticker.ticker_id,
                    report_date=data["report_date"],
                    filing_date=data["filing_date"]
                )
                .first()
            )

            if not existing:
                fundamental = Fundamental(
                    ticker_id=ticker.ticker_id,
                    report_date=data["report_date"],
                    filing_date=data["filing_date"],
                    market_cap=data.get("market_cap"),
                    pe_ratio=data.get("pe_ratio"),
                    eps=data.get("eps"),
                    book_value=data.get("book_value"),
                    revenue=data.get("revenue"),
                    net_income=data.get("net_income"),
                    total_assets=data.get("total_assets"),
                    total_liabilities=data.get("total_liabilities"),
                    stockholder_equity=data.get("stockholder_equity"),
                    operating_income=data.get("operating_income"),
                    gross_profit=data.get("gross_profit"),
                    balance_sheet_json=data.get("balance_sheet_json"),
                    income_statement_json=data.get("income_statement_json"),
                    cash_flow_json=data.get("cash_flow_json"),
                )
                session.add(fundamental)
                logger.debug(
                    f"Inserted fundamental for {data['symbol']} quarter {data['report_date']} filed {data['filing_date']}"
                )
            else:
                logger.debug(
                    f"Fundamentals for {data['symbol']} quarter {data['report_date']} (filed {data['filing_date']}) already exists, skipping."
                )

    def insert_news(self, session, data: list):
        for item in data:
            ticker = session.query(Ticker).filter_by(symbol=item["symbol"]).first()
            if ticker:
                # Check for existing entry to prevent duplicates based on URL
                existing = session.query(News).filter_by(url=item["url"]).first()
                if not existing:
                    news_item = News(
                        ticker_id=ticker.ticker_id,
                        published_date=item["published_date"],
                        title=item["title"],
                        content=item["content"],
                        sentiment=item.get("sentiment"),
                        sentiment_score=item.get("sentiment_score"),
                        sentiment_label=item.get("sentiment_label"),
                        url=item["url"],
                    )
                    session.add(news_item)
                else:
                    logger.debug(
                        f"News item with URL {item['url']} already exists, skipping."
                    )
            else:
                logger.warning(f"Ticker {item['symbol']} not found for news insertion.")

    def insert_insider_transactions(self, session, data: list):
        for item in data:
            ticker = session.query(Ticker).filter_by(symbol=item["symbol"]).first()
            if ticker:
                # Insider transactions don't always have a unique identifier other than all fields combined
                # For simplicity, we'll check for an exact match on key fields.
                existing = (
                    session.query(InsiderTransaction)
                    .filter_by(
                        ticker_id=ticker.ticker_id,
                        transaction_date=item["transaction_date"],
                        owner_name=item["owner_name"],
                        transaction_code=item["transaction_code"],
                        transaction_amount=item["transaction_amount"],
                    )
                    .first()
                )
                if not existing:
                    insider_tx = InsiderTransaction(
                        ticker_id=ticker.ticker_id,
                        transaction_date=item["transaction_date"],
                        owner_name=item["owner_name"],
                        transaction_code=item["transaction_code"],
                        transaction_amount=item["transaction_amount"],
                        transaction_price=item.get("transaction_price"),
                    )
                    session.add(insider_tx)
                else:
                    logger.debug(
                        f"Insider transaction for {item['symbol']} by {item['owner_name']} on {item['transaction_date']} already exists, skipping."
                    )
            else:
                logger.warning(
                    f"Ticker {item['symbol']} not found for insider transaction insertion."
                )

    def insert_macroeconomic_indicators(self, session, data: list):
        for item in data:
            # Check for existing entry to prevent duplicates based on series_id and date
            existing = (
                session.query(MacroeconomicIndicator)
                .filter_by(
                    series_id=item["series_id"],
                    date=item["date"],
                )
                .first()
            )
            if not existing:
                macro_indicator = MacroeconomicIndicator(
                    series_id=item["series_id"],
                    country=item["country"],
                    indicator_name=item["indicator_name"],
                    date=item["date"],
                    value=item["value"],
                    unit=item.get("unit"),
                    frequency=item.get("frequency"),
                )
                session.add(macro_indicator)
            else:
                logger.debug(
                    f"Macro indicator {item['indicator_name']} for {item['country']} on {item['date']} already exists, skipping."
                )


if __name__ == "__main__":
    # Example Usage
    # Use an in-memory SQLite database for demonstration
    DB_URL = "postgresql://charlie_user:charlie_password@localhost/charlie_tr1_db"  # PostgreSQL connection string

    db_manager = DatabaseManager(DB_URL)
    session = db_manager.get_session()

    try:
        # Insert a ticker
        aapl_ticker = db_manager.insert_ticker(
            session,
            symbol="AAPL",
            exchange="US",
            company_name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
        )
        msft_ticker = db_manager.insert_ticker(
            session,
            symbol="MSFT",
            exchange="US",
            company_name="Microsoft Corp.",
            sector="Technology",
            industry="Software",
        )
        session.commit()
        logger.info("Tickers inserted.")

        from datetime import date, datetime

        # Example Technical Market Data
        tech_data_aapl = [
            {
                "symbol": "AAPL",
                "date": date(2024, 1, 2),
                "timestamp": datetime(2024, 1, 2, 16, 0, 0),
                "interval": "1d",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "adjusted_close": 103.0,
                "volume": 100000,
                "sma": 102.0,
                "ema": 102.5,
                "rsi": 60.0,
                "macd": 1.5,
            },
            {
                "symbol": "AAPL",
                "date": date(2024, 1, 3),
                "timestamp": datetime(2024, 1, 3, 16, 0, 0),
                "interval": "1d",
                "open": 104.0,
                "high": 106.0,
                "low": 103.0,
                "close": 105.0,
                "adjusted_close": 104.0,
                "volume": 120000,
                "sma": 103.0,
                "ema": 103.5,
                "rsi": 65.0,
                "macd": 2.0,
            },
        ]
        db_manager.insert_technical_market_data(session, tech_data_aapl)
        session.commit()
        logger.info("Technical Market Data inserted.")

        # Example Fundamentals Data
        fundamentals_aapl = {
            "symbol": "AAPL",
            "report_date": date(2024, 3, 31),
            "market_cap": 3000000000000,
            "pe_ratio": 30.5,
            "eps": 6.0,
            "book_value": 15.0,
            "revenue": 200000000000,
            "net_income": 50000000000,
            "balance_sheet_json": json.dumps({"assets": 1000, "liabilities": 500}),
            "income_statement_json": json.dumps({"revenue": 200, "profit": 50}),
            "cash_flow_json": json.dumps({"operating_cash_flow": 60}),
        }
        db_manager.insert_fundamentals(session, fundamentals_aapl)
        session.commit()
        logger.info("Fundamentals Data inserted.")

        # Example News Data
        news_aapl = [
            {
                "symbol": "AAPL",
                "published_date": datetime(2024, 1, 5, 10, 0, 0),
                "title": "Apple stock surges on strong iPhone sales",
                "content": "Details about strong sales numbers...",
                "sentiment": "Positive",
                "url": "http://example.com/aapl-news-1",
            },
            {
                "symbol": "AAPL",
                "published_date": datetime(2024, 1, 6, 11, 30, 0),
                "title": "Analyst upgrades Apple target price",
                "content": "Investment bank raises forecast...",
                "sentiment": "Positive",
                "url": "http://example.com/aapl-news-2",
            },
        ]
        db_manager.insert_news(session, news_aapl)
        session.commit()
        logger.info("News Data inserted.")

        # Example Insider Transactions Data
        insider_tx_aapl = [
            {
                "symbol": "AAPL",
                "transaction_date": date(2024, 1, 10),
                "owner_name": "Tim Cook",
                "transaction_code": "P",
                "transaction_amount": 10000,
                "transaction_price": 170.50,
            },
            {
                "symbol": "AAPL",
                "transaction_date": date(2024, 1, 12),
                "owner_name": "Luca Maestri",
                "transaction_code": "S",
                "transaction_amount": 5000,
                "transaction_price": 172.00,
            },
        ]
        db_manager.insert_insider_transactions(session, insider_tx_aapl)
        session.commit()
        logger.info("Insider Transactions Data inserted.")

        # Example Macroeconomic Indicators Data
        macro_data_usa = [
            {
                "country": "USA",
                "indicator_name": "gdp_growth_annual",
                "date": date(2024, 3, 31),
                "value": 3.5,
                "unit": "%",
            },
            {
                "country": "USA",
                "indicator_name": "inflation_consumer_prices_annual",
                "date": date(2024, 3, 31),
                "value": 3.1,
                "unit": "%",
            },
        ]
        db_manager.insert_macroeconomic_indicators(session, macro_data_usa)
        session.commit()
        logger.info("Macroeconomic Indicators Data inserted.")

    except Exception as e:
        session.rollback()
        logger.error(f"An error occurred during database operations: {e}")
    finally:
        session.close()
        logger.info("Database session closed.")

    logger.info("DatabaseManager example completed.")
