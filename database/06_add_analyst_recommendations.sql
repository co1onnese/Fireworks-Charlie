-- ============================================================================
-- Create analyst_recommendations table for FMP API historical-grades
-- ============================================================================

CREATE TABLE IF NOT EXISTS analyst_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    firm VARCHAR(100) NOT NULL,
    firm_id VARCHAR(100),
    analyst_insight_id VARCHAR(100) UNIQUE,  -- FMP-generated unique ID (format: FMP_{symbol}_{date}_{firm})
    rating_id VARCHAR(100),  -- Benzinga rating ID
    action VARCHAR(50),  -- "Reiterates", "Upgrades", "Downgrades", "Maintains", "Initiates"
    rating VARCHAR(50),  -- "Buy", "Hold", "Sell", "Strong Buy", "Strong Sell", etc.
    target_price NUMERIC(18, 4),  -- From "pt" field
    analyst_insights TEXT,  -- Full insight text from "analyst_insights" field
    updated_timestamp BIGINT,  -- From "updated" field (Unix timestamp)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(ticker_id, date, firm_id, analyst_insight_id)
);

-- Add comments for documentation
COMMENT ON TABLE analyst_recommendations IS 'Analyst recommendations and insights from FMP API historical-grades';
COMMENT ON COLUMN analyst_recommendations.analyst_insight_id IS 'Unique FMP-generated ID (format: FMP_{symbol}_{date}_{firm}) - prevents duplicates';
COMMENT ON COLUMN analyst_recommendations.action IS 'Analyst action: Reiterates, Upgrades, Downgrades, Maintains, Initiates';
COMMENT ON COLUMN analyst_recommendations.rating IS 'Analyst rating: Buy, Hold, Sell, Strong Buy, Strong Sell, etc.';
COMMENT ON COLUMN analyst_recommendations.target_price IS 'Price target from analyst (from pt field)';
COMMENT ON COLUMN analyst_recommendations.analyst_insights IS 'Full detailed insight text from analyst';

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_analyst_recs_ticker_date ON analyst_recommendations(ticker_id, date);
CREATE INDEX IF NOT EXISTS idx_analyst_recs_date ON analyst_recommendations(date);
CREATE INDEX IF NOT EXISTS idx_analyst_recs_firm ON analyst_recommendations(firm);
CREATE INDEX IF NOT EXISTS idx_analyst_recs_rating ON analyst_recommendations(rating);
CREATE INDEX IF NOT EXISTS idx_analyst_recs_action ON analyst_recommendations(action);
