-- ============================================================================
-- Add ATR (Average True Range) and ADX (Average Directional Index) columns
-- to market_data table for enhanced technical analysis
-- ============================================================================

-- Add ATR and ADX columns to market_data table
ALTER TABLE market_data
    ADD COLUMN IF NOT EXISTS atr_14 NUMERIC(18, 4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS adx_14 NUMERIC(18, 4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS di_plus_14 NUMERIC(18, 4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS di_minus_14 NUMERIC(18, 4) DEFAULT NULL;

-- Add comments for documentation
COMMENT ON COLUMN market_data.atr_14 IS 'Average True Range (14-period) - measures volatility';
COMMENT ON COLUMN market_data.adx_14 IS 'Average Directional Index (14-period) - measures trend strength';
COMMENT ON COLUMN market_data.di_plus_14 IS 'Plus Directional Indicator (14-period) - part of ADX calculation';
COMMENT ON COLUMN market_data.di_minus_14 IS 'Minus Directional Indicator (14-period) - part of ADX calculation';

-- Note: No indexes needed as these are calculated fields, not frequently queried independently
-- The existing indexes on (ticker_id, date) are sufficient for lookups
