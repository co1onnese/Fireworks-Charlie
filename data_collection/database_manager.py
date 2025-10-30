"""
Optimized Database Manager for Fireworks-Charlie RLVR Pipeline
SQLAlchemy 2.0+ with comprehensive schema for training data generation
"""
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Numeric, Text,
    Boolean, TIMESTAMP, BigInteger, ForeignKey, UniqueConstraint,
    Index, ARRAY, func, and_
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.pool import NullPool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

Base = declarative_base()

# ============================================================================
# CORE MODELS
# ============================================================================

class Ticker(Base):
    """Master ticker registry"""
    __tablename__ = 'tickers'

    ticker_id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), unique=True, nullable=False)
    exchange = Column(String(10), nullable=False, default='US')
    company_name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    market_data = relationship("MarketData", back_populates="ticker", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamental", back_populates="ticker", cascade="all, delete-orphan")
    news = relationship("News", back_populates="ticker", cascade="all, delete-orphan")
    insider_transactions = relationship("InsiderTransaction", back_populates="ticker", cascade="all, delete-orphan")
    thesis_generations = relationship("ThesisGeneration", back_populates="ticker", cascade="all, delete-orphan")
    positions = relationship("Position", back_populates="ticker", cascade="all, delete-orphan")
    rlvr_examples = relationship("RLVRTrainingExample", back_populates="ticker", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Ticker(symbol='{self.symbol}', company='{self.company_name}')>"


class MarketData(Base):
    """Daily OHLCV data and technical indicators (partitioned by date)"""
    __tablename__ = 'market_data'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'date', name='uq_market_data_ticker_date'),
        Index('idx_market_data_date', 'date'),
        Index('idx_market_data_ticker_date', 'ticker_id', 'date'),
    )

    market_data_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)

    # OHLCV
    open = Column(Numeric(18, 4), nullable=False)
    high = Column(Numeric(18, 4), nullable=False)
    low = Column(Numeric(18, 4), nullable=False)
    close = Column(Numeric(18, 4), nullable=False)
    adjusted_close = Column(Numeric(18, 4))
    volume = Column(BigInteger, nullable=False)

    # Technical Indicators
    sma_20 = Column(Numeric(18, 4))
    sma_50 = Column(Numeric(18, 4))
    ema_20 = Column(Numeric(18, 4))
    rsi_14 = Column(Numeric(18, 4))
    macd = Column(Numeric(18, 4))
    macd_signal = Column(Numeric(18, 4))
    bollinger_upper = Column(Numeric(18, 4))
    bollinger_lower = Column(Numeric(18, 4))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="market_data")

    def __repr__(self):
        return f"<MarketData(ticker_id={self.ticker_id}, date={self.date}, close={self.close})>"


class Fundamental(Base):
    """Quarterly financial statements"""
    __tablename__ = 'fundamentals'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'report_date', 'filing_date', name='uq_fundamentals_ticker_dates'),
        Index('idx_fundamentals_ticker_filing', 'ticker_id', 'filing_date'),
    )

    fundamental_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)

    # Dates
    report_date = Column(Date, nullable=False)  # Quarter end
    filing_date = Column(Date, nullable=False)  # When public

    # Valuation Metrics
    market_cap = Column(BigInteger)
    pe_ratio = Column(Numeric(10, 4))
    pb_ratio = Column(Numeric(10, 4))
    ps_ratio = Column(Numeric(10, 4))
    eps = Column(Numeric(10, 4))

    # Income Statement
    revenue = Column(BigInteger)
    gross_profit = Column(BigInteger)
    operating_income = Column(BigInteger)
    net_income = Column(BigInteger)
    ebitda = Column(BigInteger)

    # Balance Sheet
    total_assets = Column(BigInteger)
    total_liabilities = Column(BigInteger)
    stockholder_equity = Column(BigInteger)
    cash_and_equivalents = Column(BigInteger)
    total_debt = Column(BigInteger)

    # Cash Flow
    operating_cash_flow = Column(BigInteger)
    free_cash_flow = Column(BigInteger)

    # Growth Rates
    revenue_qoq_pct = Column(Numeric(10, 4))
    revenue_yoy_pct = Column(Numeric(10, 4))
    net_income_qoq_pct = Column(Numeric(10, 4))
    net_income_yoy_pct = Column(Numeric(10, 4))

    # Raw JSON
    income_statement_json = Column(JSONB)
    balance_sheet_json = Column(JSONB)
    cash_flow_json = Column(JSONB)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="fundamentals")

    def __repr__(self):
        return f"<Fundamental(ticker_id={self.ticker_id}, report_date={self.report_date})>"


class News(Base):
    """News articles with sentiment analysis"""
    __tablename__ = 'news'
    __table_args__ = (
        Index('idx_news_ticker_published', 'ticker_id', 'published_at'),
        Index('idx_news_published_at', 'published_at'),
    )

    news_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)

    published_at = Column(TIMESTAMP, nullable=False)
    headline = Column(String(512), nullable=False)
    summary = Column(Text)
    content = Column(Text)
    url = Column(String(2048), unique=True, nullable=False)
    source = Column(String(100))

    # Sentiment Analysis
    sentiment_score = Column(Numeric(5, 4))  # -1 to 1
    sentiment_label = Column(String(20))  # positive/negative/neutral
    sentiment_confidence = Column(Numeric(5, 4))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="news")

    # Property aliases for backward compatibility
    @property
    def published_date(self):
        return self.published_at

    @property
    def title(self):
        return self.headline

    def __repr__(self):
        return f"<News(ticker_id={self.ticker_id}, headline='{self.headline[:50]}...')>"


class MacroeconomicIndicator(Base):
    """Economic indicators from FRED API"""
    __tablename__ = 'macroeconomic_indicators'
    __table_args__ = (
        UniqueConstraint('series_id', 'date', name='uq_macro_series_date'),
        Index('idx_macro_series_date', 'series_id', 'date'),
    )

    macro_id = Column(Integer, primary_key=True, autoincrement=True)
    series_id = Column(String(50), nullable=False)  # FRED series ID
    indicator_name = Column(String(255), nullable=False)
    country = Column(String(50), default='USA')

    date = Column(Date, nullable=False)
    value = Column(Numeric(20, 8), nullable=False)

    unit = Column(String(100))
    frequency = Column(String(20))  # daily, monthly, quarterly

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<MacroeconomicIndicator(series='{self.series_id}', date={self.date})>"


class MacroFeature(Base):
    """Derived macroeconomic features"""
    __tablename__ = 'macro_features'

    feature_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True)

    # Yield Curve
    yield_curve_10y_2y = Column(Numeric(8, 6))
    yield_curve_10y_3m = Column(Numeric(8, 6))

    # Inflation
    cpi_monthly_pct = Column(Numeric(8, 6))
    cpi_yoy_pct = Column(Numeric(8, 6))
    pce_monthly_pct = Column(Numeric(8, 6))
    pce_yoy_pct = Column(Numeric(8, 6))

    # Growth
    gdp_qoq_pct = Column(Numeric(8, 6))
    industrial_production_mom_pct = Column(Numeric(8, 6))

    # Labor
    unemployment_rate = Column(Numeric(8, 6))
    unemployment_rate_change = Column(Numeric(8, 6))

    # Rates
    fed_funds_rate = Column(Numeric(8, 6))

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<MacroFeature(date={self.date})>"


class TickerEventFeature(Base):
    """Gap features describing time since key events"""
    __tablename__ = 'ticker_event_features'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'date', name='uq_event_feature_ticker_date'),
        Index('idx_event_features_ticker_date', 'ticker_id', 'date'),
    )

    event_feature_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)

    days_since_last_news = Column(Integer)
    days_since_last_insider_trade = Column(Integer)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<TickerEventFeature(ticker_id={self.ticker_id}, date={self.date}, "
            f"news_gap={self.days_since_last_news}, insider_gap={self.days_since_last_insider_trade})>"
        )


class NewsSentimentFeature(Base):
    """Rolling news sentiment aggregates"""
    __tablename__ = 'news_sentiment_features'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'date', name='uq_news_sentiment_ticker_date'),
        Index('idx_news_sentiment_ticker_date', 'ticker_id', 'date'),
    )

    sentiment_feature_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)

    sentiment_7day_avg = Column(Numeric(10, 6))
    sentiment_7day_count = Column(Integer)
    daily_article_count = Column(Integer)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<NewsSentimentFeature(ticker_id={self.ticker_id}, date={self.date}, "
            f"avg={self.sentiment_7day_avg})>"
        )


class InsiderTransaction(Base):
    """Insider trading transactions"""
    __tablename__ = 'insider_transactions'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'transaction_date', 'owner_name', 'transaction_code', 'shares',
                        name='uq_insider_transaction'),
        Index('idx_insider_ticker_date', 'ticker_id', 'transaction_date'),
    )

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)

    transaction_date = Column(Date, nullable=False)
    filing_date = Column(Date)

    owner_name = Column(String(255), nullable=False)
    owner_title = Column(String(255))
    transaction_code = Column(String(10), nullable=False)  # P, S, A, D

    shares = Column(BigInteger)
    transaction_price = Column(Numeric(18, 4))
    transaction_amount = Column(BigInteger)
    shares_owned_after = Column(BigInteger)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="insider_transactions")

    def __repr__(self):
        return f"<InsiderTransaction(ticker_id={self.ticker_id}, owner='{self.owner_name}', code='{self.transaction_code}')>"


# ============================================================================
# RLVR-SPECIFIC MODELS
# ============================================================================

class ThesisGeneration(Base):
    """AI-generated investment theses with full prompts"""
    __tablename__ = 'thesis_generations'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'as_of_date', name='uq_thesis_ticker_date'),
        Index('idx_thesis_ticker_date', 'ticker_id', 'as_of_date'),
        Index('idx_thesis_as_of_date', 'as_of_date'),
    )

    thesis_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)

    # Date Information
    as_of_date = Column(Date, nullable=False)
    generated_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Prompts (for RLVR)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)

    # Response (JSON)
    assistant_response = Column(JSONB, nullable=False)

    # Extracted fields
    predicted_action = Column(String(20), nullable=False)
    reasoning = Column(Text)
    support = Column(Text)

    # Model metadata
    model_name = Column(String(100))
    temperature = Column(Numeric(3, 2))
    tokens_used = Column(Integer)
    generation_time_ms = Column(Integer)

    # Status
    status = Column(String(20), default='success')
    error_message = Column(Text)
    data_hash = Column(String(64))

    # Relationships
    ticker = relationship("Ticker", back_populates="thesis_generations")
    position = relationship("Position", back_populates="thesis", uselist=False)

    def __repr__(self):
        return f"<ThesisGeneration(ticker_id={self.ticker_id}, date={self.as_of_date}, action='{self.predicted_action}')>"


class Position(Base):
    """3-day position tracking with performance"""
    __tablename__ = 'positions'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'entry_date', name='uq_position_ticker_entry'),
        Index('idx_positions_ticker_entry', 'ticker_id', 'entry_date'),
        Index('idx_positions_status', 'status'),
    )

    position_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    thesis_id = Column(BigInteger, ForeignKey('thesis_generations.thesis_id', ondelete='CASCADE'), nullable=False)

    # Entry
    entry_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(18, 4), nullable=False)
    predicted_action = Column(String(20), nullable=False)

    # Exit
    exit_date = Column(Date)
    exit_price = Column(Numeric(18, 4))
    actual_return_pct = Column(Numeric(10, 4))

    # Position Details
    days_held = Column(Integer)
    early_exit = Column(Boolean, default=False)
    early_exit_reason = Column(String(255))

    # Performance
    directional_accuracy_score = Column(Numeric(5, 4))
    met_threshold = Column(Boolean)

    # Status
    status = Column(String(20), default='open')  # open, closed, skipped, error

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="positions")
    thesis = relationship("ThesisGeneration", back_populates="position")
    rlvr_example = relationship("RLVRTrainingExample", back_populates="position", uselist=False)
    historical_return = relationship("HistoricalReturn", back_populates="position", uselist=False)

    def __repr__(self):
        return f"<Position(ticker_id={self.ticker_id}, entry={self.entry_date}, action='{self.predicted_action}', status='{self.status}')>"


class RLVRTrainingExample(Base):
    """Complete RLVR examples ready for JSONL export"""
    __tablename__ = 'rlvr_training_examples'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'thesis_id', name='uq_rlvr_ticker_thesis'),
        Index('idx_rlvr_dataset_split', 'dataset_split'),
        Index('idx_rlvr_combined_score', 'combined_score'),
    )

    example_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    thesis_id = Column(BigInteger, ForeignKey('thesis_generations.thesis_id', ondelete='CASCADE'), nullable=False)
    position_id = Column(BigInteger, ForeignKey('positions.position_id', ondelete='CASCADE'), nullable=False)

    # Dataset Assignment
    dataset_split = Column(String(10), nullable=False)  # train or test

    # Complete Example Data (denormalized)
    example_json = Column(JSONB, nullable=False)
    ground_truth = Column(JSONB, nullable=False)
    example_metadata = Column(JSONB, nullable=False)

    # Performance Scores
    directional_score = Column(Numeric(5, 4))
    sharpe_score = Column(Numeric(5, 4))
    combined_score = Column(Numeric(5, 4))

    # Historical Context
    historical_returns = Column(JSONB)  # Array of past returns
    historical_return_count = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    ticker = relationship("Ticker", back_populates="rlvr_examples")
    thesis = relationship("ThesisGeneration")
    position = relationship("Position", back_populates="rlvr_example")

    def __repr__(self):
        return f"<RLVRExample(example_id={self.example_id}, split='{self.dataset_split}', score={self.combined_score})>"


class HistoricalReturn(Base):
    """Historical returns for Sharpe ratio calculation"""
    __tablename__ = 'historical_returns'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'position_id', name='uq_historical_ticker_position'),
        Index('idx_historical_ticker_seq', 'ticker_id', 'return_sequence'),
    )

    return_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)
    position_id = Column(BigInteger, ForeignKey('positions.position_id', ondelete='CASCADE'), nullable=False)

    entry_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=False)
    return_pct = Column(Numeric(10, 4), nullable=False)

    # For efficient windowing
    return_sequence = Column(Integer)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    position = relationship("Position", back_populates="historical_return")

    def __repr__(self):
        return f"<HistoricalReturn(ticker_id={self.ticker_id}, return={self.return_pct}%)>"


class SharpeCalculation(Base):
    """Cached Sharpe ratio calculations"""
    __tablename__ = 'sharpe_calculations'
    __table_args__ = (
        UniqueConstraint('ticker_id', 'as_of_date', 'lookback_periods', name='uq_sharpe_calculation'),
        Index('idx_sharpe_ticker_date', 'ticker_id', 'as_of_date'),
    )

    sharpe_id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id = Column(Integer, ForeignKey('tickers.ticker_id', ondelete='CASCADE'), nullable=False)

    as_of_date = Column(Date, nullable=False)
    lookback_periods = Column(Integer, nullable=False)

    # Statistics
    mean_return = Column(Numeric(10, 6))
    std_dev = Column(Numeric(10, 6))
    sharpe_ratio = Column(Numeric(10, 6))
    sharpe_score = Column(Numeric(5, 4))

    # Audit
    returns_used = Column(JSONB)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<SharpeCalc(ticker_id={self.ticker_id}, date={self.as_of_date}, sharpe={self.sharpe_ratio})>"


# ============================================================================
# AUDIT MODELS
# ============================================================================

class DataCollectionRun(Base):
    """Audit log for data collection runs"""
    __tablename__ = 'data_collection_runs'

    run_id = Column(Integer, primary_key=True, autoincrement=True)

    run_type = Column(String(50), nullable=False)  # full, incremental, backfill
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    tickers = Column(ARRAY(Text))

    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    status = Column(String(20), default='running')

    records_collected = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSONB)

    config_snapshot = Column(JSONB)

    def __repr__(self):
        return f"<DataCollectionRun(run_id={self.run_id}, type='{self.run_type}', status='{self.status}')>"


class RLVRGenerationRun(Base):
    """Audit log for RLVR dataset generation runs"""
    __tablename__ = 'rlvr_generation_runs'

    run_id = Column(Integer, primary_key=True, autoincrement=True)

    dataset_type = Column(String(10), nullable=False)  # train, test, dev
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    tickers = Column(ARRAY(Text))

    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    status = Column(String(20), default='running')

    examples_generated = Column(Integer, default=0)
    examples_skipped = Column(Integer, default=0)
    skip_reasons = Column(JSONB)

    output_file = Column(String(512))
    file_size_bytes = Column(BigInteger)

    config_snapshot = Column(JSONB)

    def __repr__(self):
        return f"<RLVRRun(run_id={self.run_id}, type='{self.dataset_type}', status='{self.status}')>"


# ============================================================================
# ALIASES FOR BACKWARD COMPATIBILITY
# ============================================================================

# Alias for backward compatibility
MacroFeatures = MacroeconomicIndicator


# ============================================================================
# DATABASE MANAGER CLASS
# ============================================================================

class DatabaseManager:
    """
    Enhanced database manager for Fireworks-Charlie RLVR pipeline
    """

    def __init__(self, db_url: str, echo: bool = False):
        """
        Initialize database manager

        Args:
            db_url: PostgreSQL connection string
            echo: Whether to echo SQL statements (for debugging)
        """
        self.engine = create_engine(
            db_url,
            echo=echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_size=5,  # Maximum number of permanent connections
            max_overflow=5,  # Maximum number of temporary connections (total max = 10)
            pool_timeout=30,  # Timeout for getting connection from pool
        )
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"DatabaseManager initialized with engine: {db_url.split('@')[1] if '@' in db_url else 'configured'}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.Session()

    def create_all_tables(self):
        """Create all tables (use init SQL scripts instead for production)"""
        Base.metadata.create_all(self.engine)
        logger.info("All tables created")

    def drop_all_tables(self):
        """Drop all tables (DANGER: use with caution!)"""
        Base.metadata.drop_all(self.engine)
        logger.warning("All tables dropped")

    # ========================================================================
    # TICKER OPERATIONS
    # ========================================================================

    def insert_or_get_ticker(
        self,
        session: Session,
        symbol: str,
        exchange: str = 'US',
        company_name: str = None,
        sector: str = None,
        industry: str = None
    ) -> Ticker:
        """Insert or get existing ticker"""
        ticker = session.query(Ticker).filter_by(symbol=symbol).first()

        if not ticker:
            ticker = Ticker(
                symbol=symbol,
                exchange=exchange,
                company_name=company_name or symbol,
                sector=sector,
                industry=industry
            )
            session.add(ticker)
            session.flush()
            logger.info(f"Inserted new ticker: {symbol}")
        else:
            # Update if new info provided
            if company_name and ticker.company_name != company_name:
                ticker.company_name = company_name
            if sector and ticker.sector != sector:
                ticker.sector = sector
            if industry and ticker.industry != industry:
                ticker.industry = industry
            ticker.updated_at = datetime.utcnow()
            logger.debug(f"Ticker {symbol} already exists")

        return ticker

    def get_ticker_id(self, session: Session, symbol: str) -> Optional[int]:
        """Get ticker_id for a given symbol"""
        ticker = session.query(Ticker).filter_by(symbol=symbol).first()
        return ticker.ticker_id if ticker else None

    def insert_ticker(
        self,
        session: Session,
        symbol: str,
        exchange: str = 'US',
        company_name: str = None,
        sector: str = None,
        industry: str = None
    ) -> Ticker:
        """Insert or get existing ticker (alias for insert_or_get_ticker)"""
        return self.insert_or_get_ticker(
            session, symbol, exchange, company_name, sector, industry
        )

    def insert_macroeconomic_indicators(
        self,
        session: Session,
        indicators: List[Dict[str, Any]]
    ) -> None:
        """Insert macroeconomic indicators"""
        for indicator in indicators:
            # Check if indicator already exists for this date
            existing = session.query(MacroeconomicIndicator).filter(
                MacroeconomicIndicator.series_id == indicator['series_id'],
                MacroeconomicIndicator.date == indicator['date']
            ).first()
            
            if not existing:
                macro_indicator = MacroeconomicIndicator(
                    series_id=indicator['series_id'],
                    indicator_name=indicator.get('indicator_name', indicator['series_id']),
                    country=indicator.get('country', 'USA'),
                    date=indicator['date'],
                    value=indicator['value'],
                    unit=indicator.get('unit'),
                    frequency=indicator.get('frequency')
                )
                session.add(macro_indicator)
                logger.debug(f"Inserted macro indicator: {indicator['series_id']} for {indicator['date']}")
            else:
                logger.debug(f"Macro indicator {indicator['series_id']} for {indicator['date']} already exists")

    def insert_market_data(
        self,
        session: Session,
        ticker_id: int,
        market_data: List[Dict[str, Any]]
    ) -> None:
        """Insert market data for a ticker"""
        for data_point in market_data:
            # Check if data already exists for this date
            existing = session.query(MarketData).filter(
                MarketData.ticker_id == ticker_id,
                MarketData.date == data_point['date']
            ).first()
            
            if not existing:
                market_record = MarketData(
                    ticker_id=ticker_id,
                    date=data_point['date'],
                    open=data_point['open'],
                    high=data_point['high'],
                    low=data_point['low'],
                    close=data_point['close'],
                    adjusted_close=data_point.get('adjusted_close'),
                    volume=data_point['volume'],
                    sma_20=data_point.get('sma_20'),
                    sma_50=data_point.get('sma_50'),
                    ema_20=data_point.get('ema_20'),
                    rsi_14=data_point.get('rsi_14'),
                    macd=data_point.get('macd'),
                    macd_signal=data_point.get('macd_signal'),
                    bollinger_upper=data_point.get('bollinger_upper'),
                    bollinger_lower=data_point.get('bollinger_lower')
                )
                session.add(market_record)
                logger.debug(f"Inserted market data for ticker {ticker_id} on {data_point['date']}")
            else:
                logger.debug(f"Market data for ticker {ticker_id} on {data_point['date']} already exists")

    def insert_news_data(
        self,
        session: Session,
        ticker_id: int,
        news_data: List[Dict[str, Any]]
    ) -> None:
        """Insert news data for a ticker"""
        for news_item in news_data:
            # Check if news already exists by URL (since URL has unique constraint)
            # or by ticker_id + headline + date combination
            url = news_item.get('url')
            existing = None

            if url:
                # First check if URL already exists (most reliable check)
                existing = session.query(News).filter(News.url == url).first()

            if not existing:
                # Also check by ticker + headline + date (for articles without URL)
                existing = session.query(News).filter(
                    News.ticker_id == ticker_id,
                    News.headline == news_item['headline'],
                    News.published_at == news_item['published_at']
                ).first()

            if not existing:
                news_record = News(
                    ticker_id=ticker_id,
                    headline=news_item['headline'],
                    summary=news_item.get('summary'),
                    content=news_item.get('content'),
                    url=url,
                    published_at=news_item['published_at'],
                    source=news_item.get('source'),
                    sentiment_score=news_item.get('sentiment_score')
                )
                session.add(news_record)
                logger.debug(f"Inserted news for ticker {ticker_id}: {news_item['headline'][:50]}...")
            else:
                logger.debug(f"News already exists (URL or headline duplicate): {news_item['headline'][:50]}...")

    def insert_fundamental_data(
        self,
        session: Session,
        ticker_id: int,
        fundamental_data: List[Dict[str, Any]]
    ) -> None:
        """Insert fundamental data for a ticker"""
        for fund_data in fundamental_data:
            # Check if fundamental data already exists for this period
            # Use report_date and filing_date as per the ORM model
            existing = session.query(Fundamental).filter(
                Fundamental.ticker_id == ticker_id,
                Fundamental.report_date == fund_data['report_date'],
                Fundamental.filing_date == fund_data['filing_date']
            ).first()

            if not existing:
                fundamental_record = Fundamental(
                    ticker_id=ticker_id,
                    report_date=fund_data['report_date'],
                    filing_date=fund_data['filing_date'],
                    revenue=fund_data.get('revenue'),
                    net_income=fund_data.get('net_income'),
                    total_assets=fund_data.get('total_assets'),
                    total_liabilities=fund_data.get('total_liabilities'),
                    stockholder_equity=fund_data.get('stockholder_equity'),
                    eps=fund_data.get('eps'),
                    pe_ratio=fund_data.get('pe_ratio'),
                    market_cap=fund_data.get('market_cap'),
                    # Additional fields from the model
                    operating_income=fund_data.get('operating_income'),
                    gross_profit=fund_data.get('gross_profit'),
                    ebitda=fund_data.get('ebitda'),
                    cash_and_equivalents=fund_data.get('cash_and_equivalents'),
                    total_debt=fund_data.get('total_debt'),
                    operating_cash_flow=fund_data.get('operating_cash_flow'),
                    free_cash_flow=fund_data.get('free_cash_flow'),
                    # Raw JSON data
                    income_statement_json=fund_data.get('income_statement_json'),
                    balance_sheet_json=fund_data.get('balance_sheet_json'),
                    cash_flow_json=fund_data.get('cash_flow_json')
                )
                session.add(fundamental_record)
                logger.debug(f"Inserted fundamental data for ticker {ticker_id} for {fund_data['report_date']}")
            else:
                logger.debug(f"Fundamental data for ticker {ticker_id} for {fund_data['report_date']} already exists")

    def insert_insider_transactions(
        self,
        session: Session,
        ticker_id: int,
        insider_data: List[Dict[str, Any]]
    ) -> None:
        """Insert insider transaction data for a ticker"""
        for insider_item in insider_data:
            owner_name = insider_item.get('owner_name')
            transaction_code = insider_item.get('transaction_code')
            transaction_date = insider_item.get('transaction_date')

            if not owner_name or not transaction_code or not transaction_date:
                logger.debug("Skipping insider record with missing key fields")
                continue

            existing = session.query(InsiderTransaction).filter(
                InsiderTransaction.ticker_id == ticker_id,
                InsiderTransaction.transaction_date == transaction_date,
                InsiderTransaction.owner_name == owner_name,
                InsiderTransaction.transaction_code == transaction_code,
                InsiderTransaction.shares == insider_item.get('shares')
            ).first()

            if not existing:
                insider_record = InsiderTransaction(
                    ticker_id=ticker_id,
                    transaction_date=transaction_date,
                    filing_date=insider_item.get('filing_date'),
                    owner_name=owner_name,
                    owner_title=insider_item.get('owner_title'),
                    transaction_code=transaction_code,
                    shares=insider_item.get('shares'),
                    transaction_price=insider_item.get('transaction_price'),
                    transaction_amount=insider_item.get('transaction_amount'),
                    shares_owned_after=insider_item.get('shares_owned_after')
                )
                session.add(insider_record)
                logger.debug(f"Inserted insider transaction for ticker {ticker_id}: {owner_name}")
            else:
                logger.debug(f"Insider transaction for ticker {ticker_id} already exists: {owner_name}")

    def insert_technical_market_data(
        self,
        session: Session,
        market_data: List[Dict[str, Any]]
    ) -> None:
        """Insert technical market data (alias for insert_market_data)"""
        # Group by ticker_id and call insert_market_data for each ticker
        ticker_groups = {}
        for data_point in market_data:
            ticker_id = data_point['ticker_id']
            if ticker_id not in ticker_groups:
                ticker_groups[ticker_id] = []
            ticker_groups[ticker_id].append(data_point)
        
        for ticker_id, data_list in ticker_groups.items():
            self.insert_market_data(session, ticker_id, data_list)

    def insert_fundamentals(
        self,
        session: Session,
        fundamental_data: List[Dict[str, Any]]
    ) -> None:
        """Insert fundamental data (alias for insert_fundamental_data)"""
        # Group by ticker_id and call insert_fundamental_data for each ticker
        ticker_groups = {}
        for fund_data in fundamental_data:
            ticker_id = fund_data['ticker_id']
            if ticker_id not in ticker_groups:
                ticker_groups[ticker_id] = []
            ticker_groups[ticker_id].append(fund_data)
        
        for ticker_id, data_list in ticker_groups.items():
            self.insert_fundamental_data(session, ticker_id, data_list)

    def insert_news(
        self,
        session: Session,
        news_data: List[Dict[str, Any]]
    ) -> None:
        """Insert news data (alias for insert_news_data)"""
        # Group by ticker_id and call insert_news_data for each ticker
        ticker_groups = {}
        for news_item in news_data:
            ticker_id = news_item['ticker_id']
            if ticker_id not in ticker_groups:
                ticker_groups[ticker_id] = []
            ticker_groups[ticker_id].append(news_item)
        
        for ticker_id, data_list in ticker_groups.items():
            self.insert_news_data(session, ticker_id, data_list)

    def insert_insider_transactions_batch(
        self,
        session: Session,
        insider_data: List[Dict[str, Any]]
    ) -> None:
        """Insert insider transaction data (alias for insert_insider_transactions)"""
        # Group by ticker_id and call insert_insider_transactions for each ticker
        ticker_groups = {}
        for insider_item in insider_data:
            ticker_id = insider_item['ticker_id']
            if ticker_id not in ticker_groups:
                ticker_groups[ticker_id] = []
            ticker_groups[ticker_id].append(insider_item)
        
        for ticker_id, data_list in ticker_groups.items():
            self.insert_insider_transactions(session, ticker_id, data_list)


if __name__ == "__main__":
    # Example usage
    db_url = "postgresql://fireworks_app:password@localhost/fireworks_charlie"

    db = DatabaseManager(db_url)
    session = db.get_session()

    try:
        # Test query
        ticker_count = session.query(Ticker).count()
        logger.info(f"Database contains {ticker_count} tickers")

    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
    finally:
        session.close()

    logger.info("DatabaseManager test completed")
