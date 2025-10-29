-- ============================================================================
-- Fireworks-Charlie Database Schema - Index Definitions
-- Optimized for RLVR Query Performance
-- ============================================================================

-- ============================================================================
-- TICKERS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_tickers_symbol
    ON tickers(symbol);

CREATE INDEX IF NOT EXISTS idx_tickers_sector
    ON tickers(sector) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_tickers_industry
    ON tickers(industry) WHERE is_active = true;

-- ============================================================================
-- MARKET DATA INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_market_data_date
    ON market_data(date);

CREATE INDEX IF NOT EXISTS idx_market_data_ticker_date
    ON market_data(ticker_id, date DESC);

-- For finding latest data quickly
CREATE INDEX IF NOT EXISTS idx_market_data_ticker_latest
    ON market_data(ticker_id, date DESC)
    WHERE date >= CURRENT_DATE - INTERVAL '30 days';

-- ============================================================================
-- FUNDAMENTALS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker_filing
    ON fundamentals(ticker_id, filing_date DESC);

CREATE INDEX IF NOT EXISTS idx_fundamentals_filing_date
    ON fundamentals(filing_date);

CREATE INDEX IF NOT EXISTS idx_fundamentals_report_date
    ON fundamentals(report_date);

-- JSONB index for fast JSON queries
CREATE INDEX IF NOT EXISTS idx_fundamentals_income_json
    ON fundamentals USING gin(income_statement_json);

-- ============================================================================
-- NEWS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_news_ticker_published
    ON news(ticker_id, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_news_published_at
    ON news(published_at DESC);

-- For deduplication checks
CREATE INDEX IF NOT EXISTS idx_news_url_hash
    ON news(md5(url));

-- For sentiment queries
CREATE INDEX IF NOT EXISTS idx_news_sentiment
    ON news(sentiment_score) WHERE sentiment_score IS NOT NULL;

-- Full-text search on headlines
CREATE INDEX IF NOT EXISTS idx_news_headline_trgm
    ON news USING gin(headline gin_trgm_ops);

-- ============================================================================
-- MACROECONOMIC INDICATORS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_macro_series_date
    ON macroeconomic_indicators(series_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_macro_date
    ON macroeconomic_indicators(date DESC);

CREATE INDEX IF NOT EXISTS idx_macro_series_id
    ON macroeconomic_indicators(series_id);

-- ============================================================================
-- MACRO FEATURES INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_macro_features_date
    ON macro_features(date DESC);

-- For range queries
CREATE INDEX IF NOT EXISTS idx_macro_features_date_range
    ON macro_features(date) WHERE date >= '2023-01-01';

-- ============================================================================
-- INSIDER TRANSACTIONS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_insider_ticker_date
    ON insider_transactions(ticker_id, transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_insider_transaction_date
    ON insider_transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_insider_owner
    ON insider_transactions(owner_name);

CREATE INDEX IF NOT EXISTS idx_insider_code
    ON insider_transactions(transaction_code);

-- ============================================================================
-- THESIS GENERATIONS INDEXES (Critical for RLVR)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_thesis_ticker_date
    ON thesis_generations(ticker_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_thesis_as_of_date
    ON thesis_generations(as_of_date);

CREATE INDEX IF NOT EXISTS idx_thesis_generated_at
    ON thesis_generations(generated_at DESC);

-- For finding errors/issues
CREATE INDEX IF NOT EXISTS idx_thesis_status
    ON thesis_generations(status) WHERE status != 'success';

-- For action distribution analysis
CREATE INDEX IF NOT EXISTS idx_thesis_action
    ON thesis_generations(predicted_action);

-- JSONB index for querying response fields
CREATE INDEX IF NOT EXISTS idx_thesis_response_json
    ON thesis_generations USING gin(assistant_response);

-- ============================================================================
-- POSITIONS INDEXES (Critical for RLVR)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_positions_ticker_entry
    ON positions(ticker_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_positions_entry_date
    ON positions(entry_date);

CREATE INDEX IF NOT EXISTS idx_positions_status
    ON positions(status);

CREATE INDEX IF NOT EXISTS idx_positions_thesis
    ON positions(thesis_id);

-- For finding closed positions
CREATE INDEX IF NOT EXISTS idx_positions_exit_date
    ON positions(exit_date) WHERE exit_date IS NOT NULL;

-- For performance analysis
CREATE INDEX IF NOT EXISTS idx_positions_accuracy
    ON positions(directional_accuracy_score) WHERE status = 'closed';

CREATE INDEX IF NOT EXISTS idx_positions_predicted_action
    ON positions(predicted_action);

-- Composite index for RLVR dataset generation queries
CREATE INDEX IF NOT EXISTS idx_positions_rlvr_export
    ON positions(ticker_id, entry_date, status)
    WHERE status = 'closed';

-- ============================================================================
-- RLVR TRAINING EXAMPLES INDEXES (Critical for Export)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_rlvr_dataset_split
    ON rlvr_training_examples(dataset_split);

CREATE INDEX IF NOT EXISTS idx_rlvr_ticker_split
    ON rlvr_training_examples(ticker_id, dataset_split);

-- For scoring analysis
CREATE INDEX IF NOT EXISTS idx_rlvr_combined_score
    ON rlvr_training_examples(combined_score DESC);

CREATE INDEX IF NOT EXISTS idx_rlvr_directional_score
    ON rlvr_training_examples(directional_score DESC);

CREATE INDEX IF NOT EXISTS idx_rlvr_sharpe_score
    ON rlvr_training_examples(sharpe_score DESC);

-- For fast bulk export by split
CREATE INDEX IF NOT EXISTS idx_rlvr_export_train
    ON rlvr_training_examples(example_id)
    WHERE dataset_split = 'train';

CREATE INDEX IF NOT EXISTS idx_rlvr_export_test
    ON rlvr_training_examples(example_id)
    WHERE dataset_split = 'test';

-- JSONB indexes for metadata queries
CREATE INDEX IF NOT EXISTS idx_rlvr_example_json
    ON rlvr_training_examples USING gin(example_json);

CREATE INDEX IF NOT EXISTS idx_rlvr_ground_truth
    ON rlvr_training_examples USING gin(ground_truth);

CREATE INDEX IF NOT EXISTS idx_rlvr_metadata
    ON rlvr_training_examples USING gin(metadata);

-- ============================================================================
-- HISTORICAL RETURNS INDEXES (For Sharpe Calculation)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_historical_ticker_seq
    ON historical_returns(ticker_id, return_sequence DESC);

CREATE INDEX IF NOT EXISTS idx_historical_entry_date
    ON historical_returns(ticker_id, entry_date DESC);

CREATE INDEX IF NOT EXISTS idx_historical_position
    ON historical_returns(position_id);

-- For rolling window queries
CREATE INDEX IF NOT EXISTS idx_historical_ticker_window
    ON historical_returns(ticker_id, return_sequence DESC)
    INCLUDE (return_pct);

-- ============================================================================
-- SHARPE CALCULATIONS INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_sharpe_ticker_date
    ON sharpe_calculations(ticker_id, as_of_date DESC);

CREATE INDEX IF NOT EXISTS idx_sharpe_lookback
    ON sharpe_calculations(lookback_periods);

CREATE INDEX IF NOT EXISTS idx_sharpe_ratio_value
    ON sharpe_calculations(sharpe_ratio DESC)
    WHERE sharpe_ratio IS NOT NULL;

-- ============================================================================
-- AUDIT TABLES INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_collection_runs_started
    ON data_collection_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collection_runs_status
    ON data_collection_runs(status);

CREATE INDEX IF NOT EXISTS idx_collection_runs_date_range
    ON data_collection_runs(start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_rlvr_runs_started
    ON rlvr_generation_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_rlvr_runs_status
    ON rlvr_generation_runs(status);

CREATE INDEX IF NOT EXISTS idx_rlvr_runs_dataset_type
    ON rlvr_generation_runs(dataset_type);

-- ============================================================================
-- STATISTICS REFRESH
-- ============================================================================

-- Analyze all tables to update statistics for query planner
ANALYZE tickers;
ANALYZE market_data;
ANALYZE fundamentals;
ANALYZE news;
ANALYZE macroeconomic_indicators;
ANALYZE macro_features;
ANALYZE insider_transactions;
ANALYZE thesis_generations;
ANALYZE positions;
ANALYZE rlvr_training_examples;
ANALYZE historical_returns;
ANALYZE sharpe_calculations;
ANALYZE data_collection_runs;
ANALYZE rlvr_generation_runs;

-- ============================================================================
-- Completion Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created all indexes for Fireworks-Charlie RLVR pipeline';
    RAISE NOTICE 'Total indexes created: ~60';
    RAISE NOTICE 'Includes: B-tree, GIN (JSONB), partial, and composite indexes';
    RAISE NOTICE 'Statistics refreshed for all tables';
END $$;
