-- ============================================================================
-- Fireworks-Charlie Database Schema - Function Definitions
-- Stored Procedures for Position Tracking and Performance Calculation
-- ============================================================================

-- ============================================================================
-- FUNCTION 1: Calculate Position Return with Early Exit Logic
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_position_return(
    p_ticker_id INTEGER,
    p_entry_date DATE,
    p_entry_price NUMERIC,
    p_predicted_action VARCHAR,
    p_hold_days INTEGER DEFAULT 3
) RETURNS TABLE (
    exit_date DATE,
    exit_price NUMERIC,
    return_pct NUMERIC,
    days_held INTEGER,
    early_exit BOOLEAN,
    early_exit_reason VARCHAR
) AS $$
DECLARE
    v_current_date DATE;
    v_days_held INTEGER := 0;
    v_exit_price NUMERIC;
    v_exit_date DATE;
    v_early_exit BOOLEAN := false;
    v_exit_reason VARCHAR;
    v_next_action VARCHAR;
    v_found_exit BOOLEAN := false;
BEGIN
    -- Iterate through next trading days
    FOR v_current_date IN
        SELECT md.date
        FROM market_data md
        WHERE md.ticker_id = p_ticker_id
        AND md.date > p_entry_date
        ORDER BY md.date
        LIMIT p_hold_days
    LOOP
        v_days_held := v_days_held + 1;

        -- Get price for this day
        SELECT md.close INTO v_exit_price
        FROM market_data md
        WHERE md.ticker_id = p_ticker_id AND md.date = v_current_date;

        -- Check if recommendation changed on day 2 or 3 (early exit condition)
        IF v_days_held >= 2 THEN
            SELECT tg.predicted_action INTO v_next_action
            FROM thesis_generations tg
            WHERE tg.ticker_id = p_ticker_id
            AND tg.as_of_date = v_current_date
            AND tg.status = 'success';

            -- Early exit if signal changes from buy/strong_buy to hold/sell/strong_sell
            IF v_next_action IS NOT NULL THEN
                IF v_next_action IN ('hold', 'sell', 'strong_sell')
                   AND p_predicted_action IN ('buy', 'strong_buy') THEN
                    v_early_exit := true;
                    v_exit_reason := 'Signal changed to ' || v_next_action || ' on day ' || v_days_held;
                    v_exit_date := v_current_date;
                    v_found_exit := true;
                    EXIT;
                END IF;
            END IF;
        END IF;

        -- Normal 3-day hold exit
        IF v_days_held = p_hold_days THEN
            v_exit_date := v_current_date;
            v_found_exit := true;
            EXIT;
        END IF;
    END LOOP;

    -- If we don't have enough data (less than minimum required days), return NULL
    IF NOT v_found_exit OR v_exit_date IS NULL OR v_exit_price IS NULL THEN
        RETURN;
    END IF;

    -- Return result
    RETURN QUERY SELECT
        v_exit_date,
        v_exit_price,
        ((v_exit_price - p_entry_price) / NULLIF(p_entry_price, 0) * 100)::NUMERIC(10,4),
        v_days_held,
        v_early_exit,
        v_exit_reason;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION calculate_position_return IS 'Calculate return for a position with 3-day hold and early exit logic';

-- ============================================================================
-- FUNCTION 2: Check Directional Accuracy
-- ============================================================================

CREATE OR REPLACE FUNCTION check_directional_accuracy(
    p_action VARCHAR,
    p_actual_return NUMERIC
) RETURNS TABLE (
    is_correct BOOLEAN,
    accuracy_score NUMERIC,
    met_threshold BOOLEAN,
    threshold_value NUMERIC
) AS $$
DECLARE
    v_is_correct BOOLEAN;
    v_met_threshold BOOLEAN;
    v_threshold NUMERIC;
BEGIN
    -- Define expected thresholds based on action
    CASE p_action
        WHEN 'strong_buy' THEN
            v_threshold := 3.0;
            v_is_correct := (p_actual_return >= 0);
            v_met_threshold := (p_actual_return >= 3.0);
        WHEN 'buy' THEN
            v_threshold := 2.0;
            v_is_correct := (p_actual_return >= 0);
            v_met_threshold := (p_actual_return >= 2.0);
        WHEN 'hold' THEN
            v_threshold := 1.0;
            v_is_correct := (p_actual_return >= -1.0 AND p_actual_return <= 1.0);
            v_met_threshold := v_is_correct;
        WHEN 'sell' THEN
            v_threshold := -2.0;
            v_is_correct := (p_actual_return <= 0);
            v_met_threshold := (p_actual_return <= -2.0);
        WHEN 'strong_sell' THEN
            v_threshold := -3.0;
            v_is_correct := (p_actual_return <= 0);
            v_met_threshold := (p_actual_return <= -3.0);
        ELSE
            v_threshold := 0.0;
            v_is_correct := false;
            v_met_threshold := false;
    END CASE;

    RETURN QUERY SELECT
        v_is_correct,
        CASE WHEN v_is_correct THEN 1.0 ELSE 0.0 END,
        v_met_threshold,
        v_threshold;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION check_directional_accuracy IS 'Determine if prediction was directionally correct based on action thresholds';

-- ============================================================================
-- FUNCTION 3: Calculate Sharpe Ratio
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_sharpe_ratio(
    p_returns NUMERIC[],
    p_risk_free_rate NUMERIC DEFAULT 0.0
) RETURNS TABLE (
    mean_return NUMERIC,
    std_dev NUMERIC,
    sharpe_ratio NUMERIC,
    sharpe_score NUMERIC,
    num_periods INTEGER
) AS $$
DECLARE
    v_mean NUMERIC;
    v_stddev NUMERIC;
    v_sharpe NUMERIC;
    v_score NUMERIC;
    v_count INTEGER;
BEGIN
    v_count := array_length(p_returns, 1);

    -- Need at least 2 data points for standard deviation
    IF v_count IS NULL OR v_count < 2 THEN
        RETURN QUERY SELECT
            NULL::NUMERIC,
            NULL::NUMERIC,
            NULL::NUMERIC,
            0.0::NUMERIC,
            COALESCE(v_count, 0);
        RETURN;
    END IF;

    -- Calculate mean
    SELECT AVG(r) INTO v_mean FROM unnest(p_returns) r;

    -- Calculate standard deviation
    SELECT STDDEV(r) INTO v_stddev FROM unnest(p_returns) r;

    -- Handle edge case where all returns are the same (stddev = 0)
    IF v_stddev IS NULL OR v_stddev = 0 THEN
        IF v_mean > p_risk_free_rate THEN
            v_sharpe := 999.99;  -- Cap at high value
        ELSE
            v_sharpe := 0.0;
        END IF;
    ELSE
        v_sharpe := (v_mean - p_risk_free_rate) / v_stddev;
    END IF;

    -- Normalize to 0-1 score
    -- Sharpe < 1.0 → score = 0.0
    -- Sharpe >= 1.0 → scale up to 1.0 (using sigmoid-like function)
    IF v_sharpe < 1.0 THEN
        v_score := 0.0;
    ELSE
        -- Sigmoid scaling: score = 1 / (1 + exp(-k * (sharpe - 1)))
        -- Using k=1 for moderate scaling
        v_score := 1.0 / (1.0 + exp(-1.0 * (v_sharpe - 1.0)));
        -- Cap at 1.0
        v_score := LEAST(v_score, 1.0);
    END IF;

    RETURN QUERY SELECT
        ROUND(v_mean, 6),
        ROUND(v_stddev, 6),
        ROUND(v_sharpe, 6),
        ROUND(v_score, 4),
        v_count;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION calculate_sharpe_ratio IS 'Calculate Sharpe ratio and normalized score from array of returns';

-- ============================================================================
-- FUNCTION 4: Get Historical Returns for Ticker
-- ============================================================================

CREATE OR REPLACE FUNCTION get_historical_returns(
    p_ticker_id INTEGER,
    p_up_to_date DATE,
    p_lookback_count INTEGER DEFAULT 30
) RETURNS NUMERIC[] AS $$
DECLARE
    v_returns NUMERIC[];
BEGIN
    SELECT ARRAY_AGG(return_pct ORDER BY return_sequence)
    INTO v_returns
    FROM (
        SELECT return_pct, return_sequence
        FROM historical_returns
        WHERE ticker_id = p_ticker_id
        AND entry_date < p_up_to_date
        ORDER BY return_sequence DESC
        LIMIT p_lookback_count
    ) subq;

    RETURN COALESCE(v_returns, ARRAY[]::NUMERIC[]);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_historical_returns IS 'Get array of historical returns for Sharpe calculation';

-- ============================================================================
-- FUNCTION 5: Update Position Performance
-- ============================================================================

CREATE OR REPLACE FUNCTION update_position_performance(
    p_position_id BIGINT
) RETURNS BOOLEAN AS $$
DECLARE
    v_ticker_id INTEGER;
    v_entry_date DATE;
    v_entry_price NUMERIC;
    v_predicted_action VARCHAR;
    v_result RECORD;
    v_accuracy RECORD;
BEGIN
    -- Get position details
    SELECT ticker_id, entry_date, entry_price, predicted_action
    INTO v_ticker_id, v_entry_date, v_entry_price, v_predicted_action
    FROM positions
    WHERE position_id = p_position_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Position % not found', p_position_id;
    END IF;

    -- Calculate return
    SELECT * INTO v_result
    FROM calculate_position_return(
        v_ticker_id,
        v_entry_date,
        v_entry_price,
        v_predicted_action,
        3
    );

    -- If no result (insufficient data), mark as skipped
    IF v_result IS NULL THEN
        UPDATE positions
        SET status = 'skipped',
            updated_at = CURRENT_TIMESTAMP
        WHERE position_id = p_position_id;
        RETURN false;
    END IF;

    -- Check directional accuracy
    SELECT * INTO v_accuracy
    FROM check_directional_accuracy(v_predicted_action, v_result.return_pct);

    -- Update position
    UPDATE positions
    SET
        exit_date = v_result.exit_date,
        exit_price = v_result.exit_price,
        actual_return_pct = v_result.return_pct,
        days_held = v_result.days_held,
        early_exit = v_result.early_exit,
        early_exit_reason = v_result.early_exit_reason,
        directional_accuracy_score = v_accuracy.accuracy_score,
        met_threshold = v_accuracy.met_threshold,
        status = 'closed',
        updated_at = CURRENT_TIMESTAMP
    WHERE position_id = p_position_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_position_performance IS 'Calculate and update position performance metrics';

-- ============================================================================
-- FUNCTION 6: Batch Update Open Positions
-- ============================================================================

CREATE OR REPLACE FUNCTION update_all_open_positions()
RETURNS TABLE (
    processed_count INTEGER,
    closed_count INTEGER,
    skipped_count INTEGER,
    error_count INTEGER
) AS $$
DECLARE
    v_position RECORD;
    v_processed INTEGER := 0;
    v_closed INTEGER := 0;
    v_skipped INTEGER := 0;
    v_errors INTEGER := 0;
    v_success BOOLEAN;
BEGIN
    FOR v_position IN
        SELECT position_id
        FROM positions
        WHERE status = 'open'
        ORDER BY entry_date
    LOOP
        BEGIN
            v_success := update_position_performance(v_position.position_id);
            v_processed := v_processed + 1;

            IF v_success THEN
                v_closed := v_closed + 1;
            ELSE
                v_skipped := v_skipped + 1;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            v_errors := v_errors + 1;
            RAISE NOTICE 'Error updating position %: %', v_position.position_id, SQLERRM;

            UPDATE positions
            SET status = 'error',
                error_message = SQLERRM,
                updated_at = CURRENT_TIMESTAMP
            WHERE position_id = v_position.position_id;
        END;
    END LOOP;

    RETURN QUERY SELECT v_processed, v_closed, v_skipped, v_errors;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_all_open_positions IS 'Batch update all open positions with current market data';

-- ============================================================================
-- FUNCTION 7: Update Sequence Numbers for Historical Returns
-- ============================================================================

CREATE OR REPLACE FUNCTION update_return_sequences()
RETURNS INTEGER AS $$
DECLARE
    v_updated INTEGER := 0;
BEGIN
    -- Update return_sequence for efficient windowing
    WITH numbered AS (
        SELECT
            return_id,
            ROW_NUMBER() OVER (PARTITION BY ticker_id ORDER BY entry_date) as new_sequence
        FROM historical_returns
    )
    UPDATE historical_returns hr
    SET return_sequence = n.new_sequence
    FROM numbered n
    WHERE hr.return_id = n.return_id
    AND (hr.return_sequence IS NULL OR hr.return_sequence != n.new_sequence);

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_return_sequences IS 'Update sequence numbers for historical returns (run after bulk inserts)';

-- ============================================================================
-- FUNCTION 8: Cleanup Old Data
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_old_data(
    p_days_to_keep INTEGER DEFAULT 365
) RETURNS TABLE (
    table_name TEXT,
    rows_deleted INTEGER
) AS $$
DECLARE
    v_cutoff_date DATE := CURRENT_DATE - p_days_to_keep;
    v_deleted INTEGER;
BEGIN
    -- Clean old news
    DELETE FROM news WHERE published_at < v_cutoff_date - INTERVAL '90 days';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN QUERY SELECT 'news'::TEXT, v_deleted;

    -- Clean old data collection runs
    DELETE FROM data_collection_runs WHERE started_at < v_cutoff_date - INTERVAL '180 days';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN QUERY SELECT 'data_collection_runs'::TEXT, v_deleted;

    -- Clean old RLVR generation runs
    DELETE FROM rlvr_generation_runs WHERE started_at < v_cutoff_date - INTERVAL '180 days';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN QUERY SELECT 'rlvr_generation_runs'::TEXT, v_deleted;

    RAISE NOTICE 'Cleanup completed. Cutoff date: %', v_cutoff_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_data IS 'Remove old data to maintain database size (default: 365 days retention)';

-- ============================================================================
-- FUNCTION 9: Database Health Check
-- ============================================================================

CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Check 1: Active tickers
    RETURN QUERY
    SELECT
        'active_tickers'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'WARNING' END,
        'Active tickers: ' || COUNT(*)::TEXT
    FROM tickers WHERE is_active = true;

    -- Check 2: Recent market data
    RETURN QUERY
    SELECT
        'recent_market_data'::TEXT,
        CASE WHEN MAX(date) >= CURRENT_DATE - 7 THEN 'OK' ELSE 'WARNING' END,
        'Latest date: ' || COALESCE(MAX(date)::TEXT, 'No data')
    FROM market_data;

    -- Check 3: Thesis generation rate
    RETURN QUERY
    SELECT
        'thesis_generation'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'WARNING' END,
        'Recent theses: ' || COUNT(*)::TEXT
    FROM thesis_generations
    WHERE generated_at >= CURRENT_TIMESTAMP - INTERVAL '7 days';

    -- Check 4: Position status
    RETURN QUERY
    SELECT
        'open_positions'::TEXT,
        'INFO',
        'Open positions: ' || COUNT(*)::TEXT
    FROM positions WHERE positions.status = 'open';

    -- Check 5: RLVR examples
    RETURN QUERY
    SELECT
        'rlvr_examples'::TEXT,
        CASE WHEN COUNT(*) > 0 THEN 'OK' ELSE 'INFO' END,
        'Total examples: ' || COUNT(*)::TEXT || ' (train: ' ||
        COUNT(*) FILTER (WHERE dataset_split = 'train')::TEXT || ', test: ' ||
        COUNT(*) FILTER (WHERE dataset_split = 'test')::TEXT || ')'
    FROM rlvr_training_examples;

END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION database_health_check IS 'Run health checks on database and return status';

-- ============================================================================
-- Completion Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created 9 database functions';
    RAISE NOTICE 'Key functions: calculate_position_return, check_directional_accuracy, calculate_sharpe_ratio';
    RAISE NOTICE 'Management: update_position_performance, update_all_open_positions, cleanup_old_data';
    RAISE NOTICE 'Utilities: get_historical_returns, update_return_sequences, database_health_check';
END $$;
