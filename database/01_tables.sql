-- ============================================================================
-- Fireworks-Charlie Database Schema - Table Definitions
-- Optimized for RLVR Training Pipeline with GRPO
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- 1. Tickers - Master ticker registry
CREATE TABLE IF NOT EXISTS tickers (
    ticker_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL UNIQUE,
    exchange VARCHAR(10) NOT NULL DEFAULT 'US',
    company_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tickers IS 'Master registry of stock tickers';
COMMENT ON COLUMN tickers.symbol IS 'Ticker symbol (e.g., AAPL, MSFT)';
COMMENT ON COLUMN tickers.is_active IS 'Whether ticker is currently being tracked';

-- 2. Market Data - OHLCV + technical indicators (partitioned by date)
CREATE TABLE IF NOT EXISTS market_data (
    market_data_id BIGSERIAL,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    date DATE NOT NULL,

    -- OHLCV
    open NUMERIC(18, 4) NOT NULL,
    high NUMERIC(18, 4) NOT NULL,
    low NUMERIC(18, 4) NOT NULL,
    close NUMERIC(18, 4) NOT NULL,
    adjusted_close NUMERIC(18, 4),
    volume BIGINT NOT NULL,

    -- Technical Indicators
    sma_20 NUMERIC(18, 4),
    sma_50 NUMERIC(18, 4),
    ema_20 NUMERIC(18, 4),
    rsi_14 NUMERIC(18, 4),
    macd NUMERIC(18, 4),
    macd_signal NUMERIC(18, 4),
    bollinger_upper NUMERIC(18, 4),
    bollinger_lower NUMERIC(18, 4),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ticker_id, date)
) PARTITION BY RANGE (date);

COMMENT ON TABLE market_data IS 'Daily OHLCV data and technical indicators (partitioned by date)';

-- Create partitions for market_data
CREATE TABLE IF NOT EXISTS market_data_2023 PARTITION OF market_data
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE IF NOT EXISTS market_data_2024 PARTITION OF market_data
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS market_data_2025 PARTITION OF market_data
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS market_data_2026 PARTITION OF market_data
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- 3. Fundamentals - Quarterly financial statements
CREATE TABLE IF NOT EXISTS fundamentals (
    fundamental_id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,

    -- Dates
    report_date DATE NOT NULL,      -- Quarter end date
    filing_date DATE NOT NULL,      -- When it became public (SEC filing)

    -- Valuation Metrics
    market_cap BIGINT,
    pe_ratio NUMERIC(10, 4),
    pb_ratio NUMERIC(10, 4),
    ps_ratio NUMERIC(10, 4),
    eps NUMERIC(10, 4),

    -- Income Statement
    revenue BIGINT,
    gross_profit BIGINT,
    operating_income BIGINT,
    net_income BIGINT,
    ebitda BIGINT,

    -- Balance Sheet
    total_assets BIGINT,
    total_liabilities BIGINT,
    stockholder_equity BIGINT,
    cash_and_equivalents BIGINT,
    total_debt BIGINT,

    -- Cash Flow
    operating_cash_flow BIGINT,
    free_cash_flow BIGINT,

    -- Growth Rates (calculated)
    revenue_qoq_pct NUMERIC(10, 4),
    revenue_yoy_pct NUMERIC(10, 4),
    net_income_qoq_pct NUMERIC(10, 4),
    net_income_yoy_pct NUMERIC(10, 4),

    -- Raw JSON for full data
    income_statement_json JSONB,
    balance_sheet_json JSONB,
    cash_flow_json JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, report_date, filing_date)
);

COMMENT ON TABLE fundamentals IS 'Quarterly financial statements and metrics';
COMMENT ON COLUMN fundamentals.filing_date IS 'SEC filing date - when data became public';

-- 4. News - News articles with sentiment analysis
CREATE TABLE IF NOT EXISTS news (
    news_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,

    published_at TIMESTAMP NOT NULL,
    headline VARCHAR(512) NOT NULL,
    summary TEXT,
    content TEXT,
    url VARCHAR(2048) UNIQUE NOT NULL,
    source VARCHAR(100),

    -- Sentiment Analysis
    sentiment_score NUMERIC(5, 4),       -- -1 to 1
    sentiment_label VARCHAR(20),         -- positive/negative/neutral
    sentiment_confidence NUMERIC(5, 4),  -- 0 to 1

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE news IS 'News articles with sentiment analysis';
COMMENT ON COLUMN news.sentiment_score IS 'Sentiment polarity score from -1 (negative) to 1 (positive)';

-- 5. Macroeconomic Indicators - Economic time series from FRED
CREATE TABLE IF NOT EXISTS macroeconomic_indicators (
    macro_id SERIAL PRIMARY KEY,
    series_id VARCHAR(50) NOT NULL,      -- FRED series ID
    indicator_name VARCHAR(255) NOT NULL,
    country VARCHAR(50) DEFAULT 'USA',

    date DATE NOT NULL,
    value NUMERIC(20, 8) NOT NULL,

    unit VARCHAR(100),
    frequency VARCHAR(20),                -- daily, monthly, quarterly

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(series_id, date)
);

COMMENT ON TABLE macroeconomic_indicators IS 'Economic indicators from FRED API';
COMMENT ON COLUMN macroeconomic_indicators.series_id IS 'FRED series identifier (e.g., GDPC1, UNRATE)';

-- 6. Macro Features - Derived macroeconomic features
CREATE TABLE IF NOT EXISTS macro_features (
    feature_id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- Yield Curve
    yield_curve_10y_2y NUMERIC(8, 6),
    yield_curve_10y_3m NUMERIC(8, 6),

    -- Inflation
    cpi_monthly_pct NUMERIC(8, 6),
    cpi_yoy_pct NUMERIC(8, 6),
    pce_monthly_pct NUMERIC(8, 6),
    pce_yoy_pct NUMERIC(8, 6),

    -- Growth
    gdp_qoq_pct NUMERIC(8, 6),
    industrial_production_mom_pct NUMERIC(8, 6),

    -- Labor
    unemployment_rate NUMERIC(8, 6),
    unemployment_rate_change NUMERIC(8, 6),

    -- Rates
    fed_funds_rate NUMERIC(8, 6),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE macro_features IS 'Derived macroeconomic features (yield curve, inflation rates, etc.)';

-- 7. Insider Transactions - Insider trading activity
CREATE TABLE IF NOT EXISTS insider_transactions (
    transaction_id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,

    transaction_date DATE NOT NULL,
    filing_date DATE,

    owner_name VARCHAR(255) NOT NULL,
    owner_title VARCHAR(255),
    transaction_code VARCHAR(10) NOT NULL,  -- P, S, A, D, etc.

    shares BIGINT,
    transaction_price NUMERIC(18, 4),
    transaction_amount BIGINT,
    shares_owned_after BIGINT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, transaction_date, owner_name, transaction_code, shares)
);

COMMENT ON TABLE insider_transactions IS 'Insider trading transactions from SEC Form 4';
COMMENT ON COLUMN insider_transactions.transaction_code IS 'Transaction type: P=Purchase, S=Sale, A=Award, D=Disposition';

-- 7a. Ticker Event Features - Time since key events
CREATE TABLE IF NOT EXISTS ticker_event_features (
    event_feature_id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    date DATE NOT NULL,

    days_since_last_news INTEGER,
    days_since_last_insider_trade INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, date)
);

COMMENT ON TABLE ticker_event_features IS 'Derived features tracking number of days since last news and insider events';

-- 7b. News Sentiment Features - Rolling sentiment aggregates
CREATE TABLE IF NOT EXISTS news_sentiment_features (
    sentiment_feature_id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    date DATE NOT NULL,

    sentiment_7day_avg NUMERIC(10, 6),
    sentiment_7day_count INTEGER,
    daily_article_count INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, date)
);

COMMENT ON TABLE news_sentiment_features IS 'Rolling news sentiment aggregates for prompt generation and analytics';

-- ============================================================================
-- RLVR-SPECIFIC TABLES
-- ============================================================================

-- 8. Thesis Generations - AI-generated investment theses with prompts
CREATE TABLE IF NOT EXISTS thesis_generations (
    thesis_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,

    -- Date Information
    as_of_date DATE NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Prompts (for RLVR dataset generation)
    system_prompt TEXT NOT NULL,
    user_prompt TEXT NOT NULL,

    -- Response (JSON format)
    assistant_response JSONB NOT NULL,

    -- Extracted fields for easy querying
    predicted_action VARCHAR(20) NOT NULL,  -- strong_buy, buy, hold, sell, strong_sell
    reasoning TEXT,
    support TEXT,

    -- Model metadata
    model_name VARCHAR(100),
    temperature NUMERIC(3, 2),
    tokens_used INTEGER,
    generation_time_ms INTEGER,

    -- Status
    status VARCHAR(20) DEFAULT 'success',   -- success, error, invalid
    error_message TEXT,

    -- Cumulative data snapshot hash (for reproducibility)
    data_hash VARCHAR(64),

    UNIQUE(ticker_id, as_of_date)
);

COMMENT ON TABLE thesis_generations IS 'AI-generated investment theses with full prompts for RLVR';
COMMENT ON COLUMN thesis_generations.system_prompt IS 'System prompt sent to LLM';
COMMENT ON COLUMN thesis_generations.user_prompt IS 'User prompt with cumulative market data';
COMMENT ON COLUMN thesis_generations.assistant_response IS 'Full JSON response from LLM';

-- 9. Positions - 3-day position tracking with performance
CREATE TABLE IF NOT EXISTS positions (
    position_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    thesis_id BIGINT NOT NULL REFERENCES thesis_generations(thesis_id) ON DELETE CASCADE,

    -- Entry
    entry_date DATE NOT NULL,
    entry_price NUMERIC(18, 4) NOT NULL,
    predicted_action VARCHAR(20) NOT NULL,

    -- Exit
    exit_date DATE,
    exit_price NUMERIC(18, 4),
    actual_return_pct NUMERIC(10, 4),

    -- Position Details
    days_held INTEGER,
    early_exit BOOLEAN DEFAULT false,
    early_exit_reason VARCHAR(255),

    -- Performance Metrics
    directional_accuracy_score NUMERIC(5, 4),  -- 0.0 or 1.0
    met_threshold BOOLEAN,

    -- Status
    status VARCHAR(20) DEFAULT 'open',  -- open, closed, skipped, error

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, entry_date)
);

COMMENT ON TABLE positions IS 'Position tracking for 3-day hold periods with early exit logic';
COMMENT ON COLUMN positions.early_exit IS 'True if position exited before 3 days due to signal change';
COMMENT ON COLUMN positions.directional_accuracy_score IS 'Binary score: 1.0 if prediction matched direction, 0.0 otherwise';

-- 10. RLVR Training Examples - Complete examples ready for JSONL export
CREATE TABLE IF NOT EXISTS rlvr_training_examples (
    example_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    thesis_id BIGINT NOT NULL REFERENCES thesis_generations(thesis_id) ON DELETE CASCADE,
    position_id BIGINT NOT NULL REFERENCES positions(position_id) ON DELETE CASCADE,

    -- Dataset Assignment
    dataset_split VARCHAR(10) NOT NULL,  -- 'train' or 'test'

    -- Complete Example Data (denormalized for fast export)
    example_json JSONB NOT NULL,

    -- Ground Truth
    ground_truth JSONB NOT NULL,

    -- Metadata
    metadata JSONB NOT NULL,

    -- Performance Scores
    directional_score NUMERIC(5, 4),
    sharpe_score NUMERIC(5, 4),
    combined_score NUMERIC(5, 4),

    -- Historical Context (for Sharpe calculation)
    historical_returns JSONB,  -- Array of past returns
    historical_return_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, thesis_id)
);

COMMENT ON TABLE rlvr_training_examples IS 'Complete RLVR examples ready for JSONL export to Fireworks';
COMMENT ON COLUMN rlvr_training_examples.example_json IS 'Full JSONL example with messages array';
COMMENT ON COLUMN rlvr_training_examples.dataset_split IS 'train or test based on date ranges';

-- 11. Historical Returns - Efficient tracking for Sharpe ratio calculation
CREATE TABLE IF NOT EXISTS historical_returns (
    return_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    position_id BIGINT NOT NULL REFERENCES positions(position_id) ON DELETE CASCADE,

    entry_date DATE NOT NULL,
    exit_date DATE NOT NULL,
    return_pct NUMERIC(10, 4) NOT NULL,

    -- For efficient rolling window queries
    return_sequence INTEGER,  -- Sequence number for this ticker

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, position_id)
);

COMMENT ON TABLE historical_returns IS 'Historical returns for Sharpe ratio calculation';
COMMENT ON COLUMN historical_returns.return_sequence IS 'Chronological sequence number for efficient window queries';

-- 12. Sharpe Calculations - Cached Sharpe ratio calculations
CREATE TABLE IF NOT EXISTS sharpe_calculations (
    sharpe_id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,

    as_of_date DATE NOT NULL,
    lookback_periods INTEGER NOT NULL,  -- Number of historical positions used

    -- Statistics
    mean_return NUMERIC(10, 6),
    std_dev NUMERIC(10, 6),
    sharpe_ratio NUMERIC(10, 6),
    sharpe_score NUMERIC(5, 4),  -- Normalized 0-1 score

    -- For audit
    returns_used JSONB,  -- Array of returns used in calculation

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(ticker_id, as_of_date, lookback_periods)
);

COMMENT ON TABLE sharpe_calculations IS 'Cached Sharpe ratio calculations to avoid recomputation';

-- ============================================================================
-- METADATA & AUDIT TABLES
-- ============================================================================

-- 13. Data Collection Runs - Track data collection pipeline runs
CREATE TABLE IF NOT EXISTS data_collection_runs (
    run_id SERIAL PRIMARY KEY,

    run_type VARCHAR(50) NOT NULL,  -- 'full', 'incremental', 'backfill'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    tickers TEXT[],

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed

    records_collected INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,

    config_snapshot JSONB
);

COMMENT ON TABLE data_collection_runs IS 'Audit log of data collection pipeline executions';

-- 14. RLVR Generation Runs - Track RLVR dataset generation runs
CREATE TABLE IF NOT EXISTS rlvr_generation_runs (
    run_id SERIAL PRIMARY KEY,

    dataset_type VARCHAR(10) NOT NULL,  -- 'train', 'test', 'dev'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    tickers TEXT[],

    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed

    examples_generated INTEGER DEFAULT 0,
    examples_skipped INTEGER DEFAULT 0,
    skip_reasons JSONB,

    output_file VARCHAR(512),
    file_size_bytes BIGINT,

    config_snapshot JSONB
);

COMMENT ON TABLE rlvr_generation_runs IS 'Audit log of RLVR dataset generation runs';

-- ============================================================================
-- Completion Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created 14 tables for Fireworks-Charlie RLVR pipeline';
    RAISE NOTICE 'Tables: tickers, market_data (partitioned), fundamentals, news, macroeconomic_indicators,';
    RAISE NOTICE '        macro_features, insider_transactions, thesis_generations, positions,';
    RAISE NOTICE '        rlvr_training_examples, historical_returns, sharpe_calculations,';
    RAISE NOTICE '        data_collection_runs, rlvr_generation_runs';
END $$;
