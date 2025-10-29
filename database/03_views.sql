-- ============================================================================
-- Fireworks-Charlie Database Schema - View Definitions
-- Materialized and Standard Views for Common Queries
-- ============================================================================

-- ============================================================================
-- VIEW 1: Latest Market Data Per Ticker
-- ============================================================================

CREATE OR REPLACE VIEW v_latest_market_data AS
SELECT DISTINCT ON (ticker_id)
    t.symbol,
    t.company_name,
    t.sector,
    md.ticker_id,
    md.date,
    md.close,
    md.volume,
    md.sma_20,
    md.sma_50,
    md.ema_20,
    md.rsi_14,
    md.macd
FROM market_data md
JOIN tickers t USING (ticker_id)
WHERE t.is_active = true
ORDER BY ticker_id, date DESC;

COMMENT ON VIEW v_latest_market_data IS 'Most recent market data for each active ticker';

-- ============================================================================
-- VIEW 2: Position Performance Summary
-- ============================================================================

CREATE OR REPLACE VIEW v_position_performance AS
SELECT
    t.symbol,
    t.company_name,
    p.predicted_action,
    COUNT(*) as total_positions,
    COUNT(*) FILTER (WHERE p.status = 'closed') as closed_positions,
    COUNT(*) FILTER (WHERE p.directional_accuracy_score = 1.0) as correct_predictions,
    COUNT(*) FILTER (WHERE p.directional_accuracy_score = 0.0) as incorrect_predictions,

    -- Accuracy metrics
    ROUND(
        COUNT(*) FILTER (WHERE p.directional_accuracy_score = 1.0)::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE p.status = 'closed'), 0) * 100,
        2
    ) as accuracy_pct,

    -- Return metrics
    ROUND(AVG(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as avg_return_pct,
    ROUND(STDDEV(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as std_return_pct,
    ROUND(MIN(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as min_return_pct,
    ROUND(MAX(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as max_return_pct,

    -- Early exit metrics
    COUNT(*) FILTER (WHERE p.early_exit = true) as early_exits,
    ROUND(
        COUNT(*) FILTER (WHERE p.early_exit = true)::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE p.status = 'closed'), 0) * 100,
        2
    ) as early_exit_pct,

    -- Threshold metrics
    COUNT(*) FILTER (WHERE p.met_threshold = true) as met_threshold_count,

    -- Date range
    MIN(p.entry_date) as first_position_date,
    MAX(p.entry_date) as last_position_date

FROM positions p
JOIN tickers t USING (ticker_id)
GROUP BY t.symbol, t.company_name, p.predicted_action;

COMMENT ON VIEW v_position_performance IS 'Aggregate performance metrics per ticker and action type';

-- ============================================================================
-- VIEW 3: RLVR Dataset Statistics
-- ============================================================================

CREATE OR REPLACE VIEW v_rlvr_dataset_stats AS
SELECT
    dataset_split,
    COUNT(*) as total_examples,
    COUNT(DISTINCT ticker_id) as unique_tickers,

    -- Score distributions
    ROUND(AVG(combined_score), 4) as avg_combined_score,
    ROUND(AVG(directional_score), 4) as avg_directional_score,
    ROUND(AVG(sharpe_score), 4) as avg_sharpe_score,

    ROUND(STDDEV(combined_score), 4) as std_combined_score,
    ROUND(MIN(combined_score), 4) as min_combined_score,
    ROUND(MAX(combined_score), 4) as max_combined_score,

    -- Date range from metadata
    MIN((metadata->>'entry_date')::DATE) as earliest_date,
    MAX((metadata->>'entry_date')::DATE) as latest_date,

    -- Historical return statistics
    ROUND(AVG(historical_return_count), 1) as avg_historical_count,

    -- Example size estimation (approx JSON size)
    ROUND(AVG(length(example_json::text)) / 1024.0, 2) as avg_example_size_kb

FROM rlvr_training_examples
GROUP BY dataset_split;

COMMENT ON VIEW v_rlvr_dataset_stats IS 'Statistics summary for RLVR training and test datasets';

-- ============================================================================
-- VIEW 4: Thesis Generation Success Rate
-- ============================================================================

CREATE OR REPLACE VIEW v_thesis_generation_stats AS
SELECT
    t.symbol,
    COUNT(*) as total_attempts,
    COUNT(*) FILTER (WHERE tg.status = 'success') as successful,
    COUNT(*) FILTER (WHERE tg.status = 'error') as errors,
    COUNT(*) FILTER (WHERE tg.status = 'invalid') as invalid,

    ROUND(
        COUNT(*) FILTER (WHERE tg.status = 'success')::NUMERIC /
        NULLIF(COUNT(*), 0) * 100,
        2
    ) as success_rate_pct,

    -- Action distribution (for successful theses)
    COUNT(*) FILTER (WHERE tg.predicted_action = 'strong_buy') as strong_buy_count,
    COUNT(*) FILTER (WHERE tg.predicted_action = 'buy') as buy_count,
    COUNT(*) FILTER (WHERE tg.predicted_action = 'hold') as hold_count,
    COUNT(*) FILTER (WHERE tg.predicted_action = 'sell') as sell_count,
    COUNT(*) FILTER (WHERE tg.predicted_action = 'strong_sell') as strong_sell_count,

    -- Performance metrics
    ROUND(AVG(tokens_used) FILTER (WHERE tg.status = 'success'), 0) as avg_tokens,
    ROUND(AVG(generation_time_ms) FILTER (WHERE tg.status = 'success'), 0) as avg_time_ms,

    MIN(as_of_date) as first_thesis_date,
    MAX(as_of_date) as last_thesis_date

FROM thesis_generations tg
JOIN tickers t USING (ticker_id)
GROUP BY t.symbol;

COMMENT ON VIEW v_thesis_generation_stats IS 'Success rates and action distribution for thesis generation';

-- ============================================================================
-- VIEW 5: Action Performance Comparison
-- ============================================================================

CREATE OR REPLACE VIEW v_action_performance AS
SELECT
    predicted_action,
    COUNT(*) as total_positions,

    -- Accuracy
    COUNT(*) FILTER (WHERE directional_accuracy_score = 1.0) as correct,
    ROUND(
        COUNT(*) FILTER (WHERE directional_accuracy_score = 1.0)::NUMERIC /
        NULLIF(COUNT(*), 0) * 100,
        2
    ) as accuracy_pct,

    -- Returns
    ROUND(AVG(actual_return_pct), 4) as avg_return_pct,
    ROUND(STDDEV(actual_return_pct), 4) as std_return_pct,

    -- Sharpe-like ratio
    ROUND(
        AVG(actual_return_pct) / NULLIF(STDDEV(actual_return_pct), 0),
        4
    ) as return_to_volatility_ratio,

    -- Early exits
    COUNT(*) FILTER (WHERE early_exit = true) as early_exits,

    -- Threshold achievement
    COUNT(*) FILTER (WHERE met_threshold = true) as met_threshold

FROM positions
WHERE status = 'closed'
GROUP BY predicted_action
ORDER BY
    CASE predicted_action
        WHEN 'strong_buy' THEN 1
        WHEN 'buy' THEN 2
        WHEN 'hold' THEN 3
        WHEN 'sell' THEN 4
        WHEN 'strong_sell' THEN 5
    END;

COMMENT ON VIEW v_action_performance IS 'Performance comparison across all action types';

-- ============================================================================
-- VIEW 6: Recent News Summary
-- ============================================================================

CREATE OR REPLACE VIEW v_recent_news AS
SELECT
    t.symbol,
    t.company_name,
    n.published_at,
    n.headline,
    n.sentiment_score,
    n.sentiment_label,
    n.source,
    n.url,
    CASE
        WHEN n.published_at >= NOW() - INTERVAL '3 days' THEN 'recent'
        WHEN n.published_at >= NOW() - INTERVAL '10 days' THEN 'medium'
        ELSE 'older'
    END as recency_bucket
FROM news n
JOIN tickers t USING (ticker_id)
WHERE n.published_at >= NOW() - INTERVAL '30 days'
ORDER BY n.published_at DESC;

COMMENT ON VIEW v_recent_news IS 'Recent news articles with sentiment (last 30 days)';

-- ============================================================================
-- VIEW 7: Sharpe Ratio Trends
-- ============================================================================

CREATE OR REPLACE VIEW v_sharpe_trends AS
SELECT
    t.symbol,
    sc.as_of_date,
    sc.lookback_periods,
    sc.mean_return,
    sc.std_dev,
    sc.sharpe_ratio,
    sc.sharpe_score,

    -- Trend indicators
    LAG(sc.sharpe_ratio) OVER (PARTITION BY sc.ticker_id ORDER BY sc.as_of_date) as prev_sharpe_ratio,
    sc.sharpe_ratio - LAG(sc.sharpe_ratio) OVER (PARTITION BY sc.ticker_id ORDER BY sc.as_of_date) as sharpe_change

FROM sharpe_calculations sc
JOIN tickers t USING (ticker_id)
ORDER BY t.symbol, sc.as_of_date DESC;

COMMENT ON VIEW v_sharpe_trends IS 'Sharpe ratio trends over time with change indicators';

-- ============================================================================
-- MATERIALIZED VIEW 1: Daily RLVR Metrics (Refresh Daily)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_rlvr_metrics AS
SELECT
    DATE_TRUNC('day', p.entry_date) as trading_day,
    COUNT(*) as positions_entered,
    COUNT(*) FILTER (WHERE p.status = 'closed') as positions_closed,

    -- Accuracy
    ROUND(
        AVG(p.directional_accuracy_score) FILTER (WHERE p.status = 'closed'),
        4
    ) as avg_directional_accuracy,

    -- Returns
    ROUND(AVG(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as avg_return,
    ROUND(STDDEV(p.actual_return_pct) FILTER (WHERE p.status = 'closed'), 4) as std_return,

    -- Action distribution
    COUNT(*) FILTER (WHERE p.predicted_action = 'strong_buy') as strong_buy_count,
    COUNT(*) FILTER (WHERE p.predicted_action = 'buy') as buy_count,
    COUNT(*) FILTER (WHERE p.predicted_action = 'hold') as hold_count,
    COUNT(*) FILTER (WHERE p.predicted_action = 'sell') as sell_count,
    COUNT(*) FILTER (WHERE p.predicted_action = 'strong_sell') as strong_sell_count

FROM positions p
WHERE p.entry_date >= '2023-01-01'
GROUP BY DATE_TRUNC('day', p.entry_date)
ORDER BY trading_day DESC;

CREATE UNIQUE INDEX ON mv_daily_rlvr_metrics(trading_day);

COMMENT ON MATERIALIZED VIEW mv_daily_rlvr_metrics IS 'Daily aggregated RLVR metrics (refresh after data updates)';

-- ============================================================================
-- MATERIALIZED VIEW 2: Ticker Summary (Refresh Daily)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_ticker_summary AS
SELECT
    t.ticker_id,
    t.symbol,
    t.company_name,
    t.sector,
    t.industry,

    -- Latest market data
    (SELECT close FROM market_data md WHERE md.ticker_id = t.ticker_id ORDER BY date DESC LIMIT 1) as latest_price,
    (SELECT date FROM market_data md WHERE md.ticker_id = t.ticker_id ORDER BY date DESC LIMIT 1) as latest_date,

    -- Thesis counts
    (SELECT COUNT(*) FROM thesis_generations tg WHERE tg.ticker_id = t.ticker_id) as total_theses,
    (SELECT COUNT(*) FROM thesis_generations tg WHERE tg.ticker_id = t.ticker_id AND tg.status = 'success') as successful_theses,

    -- Position counts
    (SELECT COUNT(*) FROM positions p WHERE p.ticker_id = t.ticker_id) as total_positions,
    (SELECT COUNT(*) FROM positions p WHERE p.ticker_id = t.ticker_id AND p.status = 'closed') as closed_positions,

    -- RLVR example counts
    (SELECT COUNT(*) FROM rlvr_training_examples r WHERE r.ticker_id = t.ticker_id AND r.dataset_split = 'train') as train_examples,
    (SELECT COUNT(*) FROM rlvr_training_examples r WHERE r.ticker_id = t.ticker_id AND r.dataset_split = 'test') as test_examples,

    -- Performance
    (SELECT ROUND(AVG(p.actual_return_pct), 4) FROM positions p WHERE p.ticker_id = t.ticker_id AND p.status = 'closed') as avg_return,
    (SELECT ROUND(AVG(p.directional_accuracy_score), 4) FROM positions p WHERE p.ticker_id = t.ticker_id AND p.status = 'closed') as avg_accuracy

FROM tickers t
WHERE t.is_active = true;

CREATE UNIQUE INDEX ON mv_ticker_summary(ticker_id);
CREATE INDEX ON mv_ticker_summary(symbol);

COMMENT ON MATERIALIZED VIEW mv_ticker_summary IS 'Comprehensive ticker summary with counts and performance (refresh daily)';

-- ============================================================================
-- Refresh Functions for Materialized Views
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_rlvr_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_ticker_summary;

    RAISE NOTICE 'Refreshed all materialized views successfully';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_all_materialized_views IS 'Refresh all materialized views (call after data updates)';

-- ============================================================================
-- Completion Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created 7 views and 2 materialized views';
    RAISE NOTICE 'Standard views: v_latest_market_data, v_position_performance, v_rlvr_dataset_stats,';
    RAISE NOTICE '               v_thesis_generation_stats, v_action_performance, v_recent_news, v_sharpe_trends';
    RAISE NOTICE 'Materialized views: mv_daily_rlvr_metrics, mv_ticker_summary';
    RAISE NOTICE 'Use: SELECT refresh_all_materialized_views(); to refresh materialized views';
END $$;
