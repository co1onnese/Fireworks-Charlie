# Structured Training Prompts Collection Plan
## For DeepSeek-V3-Terminus Base Model Fine-Tuning

**Date**: 2025-11-14  
**Goal**: Create a new collection of training prompts that collect comprehensive financial data and structure LLM responses into 5-7 sections for Fireworks-AI compatible JSON output compatible with GRPO training.

---

## EXECUTIVE SUMMARY

This plan outlines the strategy to create a new training prompt collection system that:
1. Collects comprehensive financial data (fundamentals, news, market, sentiment, macro)
2. Structures LLM responses into 5-7 sections (fundamentals, technical, news, valuation, risk_assessment, macro, conclusion)
3. Generates Fireworks-AI compatible JSONL datasets for GRPO fine-tuning
4. Uses DeepSeek-V3-Terminus base model to generate initial responses
5. Ensures compatibility with existing reward function

---

## 1. DATA REQUIREMENTS ANALYSIS

### 1.1 Required Data Collection

#### ✅ **Available in Database**:

1. **Financial Data (Fundamentals)** - ✅ **FULLY AVAILABLE**
   - Balance sheet (quarterly): `fundamentals` table
     - Fields: `total_assets`, `total_liabilities`, `stockholder_equity`, `cash_and_equivalents`, `total_debt`
     - Full JSONB: `balance_sheet_json` (contains complete balance sheet)
   - Income statement (quarterly): `fundamentals` table
     - Fields: `revenue`, `gross_profit`, `operating_income`, `net_income`, `ebitda`
     - Full JSONB: `income_statement_json` (contains complete income statement)
   - Cash flow statement (quarterly): `fundamentals` table
     - Fields: `operating_cash_flow`, `free_cash_flow`
     - Full JSONB: `cash_flow_json` (contains complete cash flow statement)
   - SEC filings metadata: `fundamentals` table
     - Fields: `report_date` (quarter end), `filing_date` (when public)
   - Financial metrics: `fundamentals` table
     - Fields: `pe_ratio`, `pb_ratio`, `ps_ratio`, `eps`, `market_cap`
     - Growth: `revenue_qoq_pct`, `revenue_yoy_pct`, `net_income_qoq_pct`, `net_income_yoy_pct`

2. **News Data** - ✅ **FULLY AVAILABLE**
   - Recent news articles: `news` table
     - Fields: `published_at`, `headline`, `summary`, `content`, `source`, `url`
   - Sentiment analysis: `news` table
     - Fields: `sentiment_score` (-1 to 1), `sentiment_label` (positive/negative/neutral), `sentiment_confidence`
   - News aggregation: `news_sentiment_features` table
     - Fields: `sentiment_7day_avg`, `sentiment_7day_count`, `daily_article_count`
   - **Time Buckets** (using trading days, consistent with existing system):
     - Last 3 trading days: Query using market calendar
     - 4-10 trading days: Query using market calendar
     - 11-30 trading days: Query using market calendar

3. **Market Data** - ✅ **MOSTLY AVAILABLE**
   - Price history: `market_data` table
     - Fields: `date`, `open`, `high`, `low`, `close`, `adjusted_close`, `volume`
     - **Exactly 11 trading days**: Query exactly 11 trading days (not calendar days) using market calendar
   - Technical indicators: `market_data` table
     - ✅ RSI (14-period): `rsi_14`
     - ✅ MACD: `macd`, `macd_signal`
     - ✅ EMA (20-period): `ema_20`
     - ✅ SMA (20, 50-period): `sma_20`, `sma_50`
     - ✅ Bollinger Bands: `bollinger_upper`, `bollinger_lower`
     - ❌ **ATR (Average True Range)** - NOT CURRENTLY CALCULATED
     - ❌ **ADX (Average Directional Index)** - NOT CURRENTLY CALCULATED

4. **Sentiment Data** - ⚠️ **PARTIALLY AVAILABLE**
   - ✅ Insider transactions: `insider_transactions` table
     - Fields: `transaction_date`, `owner_name`, `owner_title`, `transaction_code`, `shares`, `transaction_price`, `shares_owned_after`
   - ❌ **Analyst recommendations** - NOT CURRENTLY IN DATABASE

5. **Macro Data** - ✅ **FULLY AVAILABLE**
   - Economic indicators: `macroeconomic_indicators` table
     - Fields: `series_id`, `indicator_name`, `date`, `value`, `unit`, `frequency`
   - Derived macro features: `macro_features` table
     - Fields: `yield_curve_10y_2y`, `yield_curve_10y_3m`, `cpi_monthly_pct`, `cpi_yoy_pct`, `pce_monthly_pct`, `pce_yoy_pct`, `gdp_qoq_pct`, `industrial_production_mom_pct`, `unemployment_rate`, `unemployment_rate_change`, `fed_funds_rate`
   - **Past 90 days**: Can query with date filtering

### 1.2 Missing Data & Solutions

| Data Requirement | Status | Solution |
|-----------------|--------|----------|
| ATR (Average True Range) | ❌ Missing | Add calculation in `feature_engineering.py` using pandas-ta library |
| ADX (Average Directional Index) | ❌ Missing | Add calculation in `feature_engineering.py` using pandas-ta library |
| Analyst Recommendations | ❌ Missing | **DECISION: Integrate Benzinga API** - Create `benzinga_client.py`, add `analyst_recommendations` table, integrate into data orchestrator |

---

## 2. RESPONSE STRUCTURE REQUIREMENTS

### 2.1 Required 5-7 Section Structure

The LLM response must be structured into **5-7 sections**:

1. **`fundamentals`** - Financial statements, balance sheet strength, income performance
2. **`technical`** - Price action, indicators, momentum
3. **`news`** - Recent developments, earnings, AI/cloud growth
4. **`valuation`** - Based on earnings and growth metrics
5. **`risk_assessment`** - Data center delays, regulatory risks
6. **`macro`** - Economic environment impact
7. **`conclusion`** - Final recommendation with 5-tier scale: **Strong Buy, Buy, Hold, Sell, Strong Sell**

### 2.2 JSON Response Format Schema

```json
{
  "fundamentals": {
    "balance_sheet_strength": "Analysis text describing balance sheet health...",
    "income_performance": "Analysis text describing income statement trends...",
    "cash_flow": "Analysis text describing cash flow position...",
    "key_metrics": {
      "pe_ratio": 25.5,
      "pb_ratio": 8.2,
      "ps_ratio": 5.3,
      "debt_to_equity": 0.3,
      "revenue_growth_yoy": 12.5,
      "net_income_margin": 18.2
    }
  },
  "technical": {
    "price_action": "Analysis text describing recent price movements...",
    "indicators": {
      "rsi_14": 58.5,
      "macd": "bullish",
      "macd_signal": "positive",
      "bollinger_position": "upper_band",
      "atr_14": 2.5,
      "adx_14": 28.3,
      "sma_20": 150.0,
      "sma_50": 145.0,
      "ema_20": 151.0
    },
    "momentum": "Analysis text describing momentum indicators..."
  },
  "news": {
    "recent_3_days": "Summary of last 3 trading days news with key developments...",
    "recent_4_10_days": "Summary of 4-10 trading days news with trends...",
    "recent_11_30_days": "Summary of 11-30 trading days news with broader context...",
    "sentiment_summary": "Overall sentiment analysis across all time buckets...",
    "analyst_recommendations": {
      "recent_upgrades": [
        {
          "firm": "HC Wainwright & Co.",
          "action": "Upgrades",
          "rating": "Buy",
          "target_price": "$155.00",
          "date": "2024-02-15"
        }
      ],
      "recent_downgrades": [
        {
          "firm": "Goldman Sachs",
          "action": "Downgrades",
          "rating": "Hold",
          "target_price": "$140.00",
          "date": "2024-02-14"
        }
      ],
      "recent_maintains": [
        {
          "firm": "Morgan Stanley",
          "action": "Reiterates",
          "rating": "Buy",
          "target_price": "$160.00",
          "date": "2024-02-13"
        }
      ],
      "consensus": "Buy (12 Buy, 5 Hold, 2 Sell)",
      "average_target_price": "$155.00",
      "recommendation_summary": "Overall analyst sentiment is positive with recent upgrades. Key insights include advancing clinical pipeline and positive valuation model.",
      "key_insights": [
        "HC Wainwright & Co. reiterated Buy rating with $5.00 target, citing advancing clinical pipeline for CYB003 and CYB004 programs.",
        "Goldman Sachs downgraded to Hold, expressing concerns about regulatory timeline and market competition."
      ]
    }
  },
  "valuation": {
    "metrics": {
      "pe_ratio": 25.5,
      "ps_ratio": 5.3,
      "peg_ratio": 1.2,
      "pb_ratio": 8.2,
      "ev_ebitda": 15.0
    },
    "assessment": "Fair value, overvalued, or undervalued analysis...",
    "comparison": "Comparison vs peers and vs market averages..."
  },
  "risk_assessment": {
    "ticker_specific_risks": "Company-specific risks (regulatory, competitive, operational)...",
    "market_risks": "General market risks (economic downturn, sector headwinds)...",
    "mitigation": "Risk mitigation factors and company strengths...",
    "regulatory": "Regulatory concerns and compliance status..."
  },
  "macro": {
    "economic_environment": "Current economic conditions summary...",
    "impact": "How macro environment affects this specific stock...",
    "key_indicators": {
      "yield_curve_10y_2y": "+0.5%",
      "cpi_yoy": "2.1%",
      "unemployment_rate": "3.7%",
      "fed_funds_rate": "5.25%",
      "gdp_growth": "2.5%"
    }
  },
  "conclusion": {
    "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
    "reasoning": "Summary reasoning synthesizing all sections...",
    "confidence": 0.75,
    "target_price": "$150.00",
    "time_horizon": "3-6 months"
  }
}
```

### 2.3 Reward Function Compatibility

**Current Reward Function** (`reward_function_advanced.py`) expects:
- `action` (string): "strong_buy", "buy", "hold", "sell", "strong_sell"
- `reasoning` (string): Text reasoning
- `support` (string): Supporting evidence

**Solution**: Extract from new structure:
- `action` → `conclusion.recommendation` (convert "Strong Buy" → "strong_buy")
- `reasoning → Combine all section analyses or use `conclusion.reasoning`
- `support` → Combine key points from all sections

**Action Required**: Create adapter function to convert new format to old format for reward function compatibility.

---

## 3. PROPOSED SOLUTION ARCHITECTURE

### 3.1 New Structured Prompt Builder Module

**File**: `thesis_generation/structured_prompt_builder.py`

**Purpose**: Create prompts specifically for the 5-7 section structured response format.

**Key Features**:
1. **Data Collection Methods**:
   - `_query_fundamentals()` - Query quarterly fundamentals with full JSONB statements
   - `_query_news_by_buckets()` - Query news in time buckets (3 days, 4-10 days, 11-30 days)
   - `_query_price_history()` - Query last 11 trading days with all technical indicators
   - `_query_insider_transactions()` - Query recent insider transactions
   - `_query_macro_indicators()` - Query macro indicators (past 90 days)
   - `_query_analyst_recommendations()` - Query analyst recommendations (if available)

2. **Prompt Structure**:
   - System prompt: Instructs model to respond in 5-7 sections with specific JSON structure
   - User prompt: Organized data sections matching the required response structure
   - Includes few-shot examples of desired format

3. **Response Format**:
   - JSON schema validation
   - Section-by-section validation
   - Conclusion validation (must be one of 5 tiers)

### 3.2 Enhanced Feature Engineering

**File**: `data_collection/feature_engineering.py` (modify existing)

**Additions**:
1. **ATR Calculation**:
   ```python
   def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series
   ```
   - Use pandas-ta library: `ta.volatility.AverageTrueRange()`
   - Or manual calculation: `TR = max(high - low, abs(high - prev_close), abs(low - prev_close))`

2. **ADX Calculation**:
   ```python
   def _calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]
   ```
   - Use pandas-ta library: `ta.trend.ADXIndicator()`
   - Returns: `{"adx": adx_series, "di_plus": di_plus_series, "di_minus": di_minus_series}`

3. **Database Schema Update**:
   - Migration script: `database/05_add_atr_adx.sql`
   - Add columns to `market_data` table:
     - `atr_14 NUMERIC(18, 4)`
     - `adx_14 NUMERIC(18, 4)`
     - `di_plus_14 NUMERIC(18, 4)`
     - `di_minus_14 NUMERIC(18, 4)`

4. **Update Technical Indicators Method**:
   - Modify `_calculate_technical_indicators()` to include ATR and ADX calculations
   - Ensure backward compatibility with existing data

### 3.3 Analyst Recommendations Integration

**DECISION: Integrate Benzinga API**

Analyst recommendations will be integrated using Benzinga API:
- **API Documentation**: https://docs.benzinga.com/benzinga-apis/analyst-insights/get-analyst-insights
- **API Endpoint**: `GET https://api.benzinga.com/api/v1/analyst/insights`
- **Authentication**: `token` query parameter (not header)
- **API Key**: `BENZINGA_API_KEY` (already added to .env config file)
- **Query Parameters**:
  - `symbols` (CSV): Ticker symbols to query
  - `page` (integer): Pagination page number
  - `pageSize` (integer): Items per page (max 100)
- **Response Fields**:
  - `action`: "Reiterates", "Upgrades", "Downgrades", "Maintains", "Initiates"
  - `rating`: "Buy", "Hold", "Sell", "Strong Buy", "Strong Sell", etc.
  - `pt`: Price target (string)
  - `analyst_insights`: Detailed insight text
  - `firm`: Firm name
  - `firm_id`: Firm identifier
  - `date`: Date of insight
  - `id`: Unique insight ID (UUID)
- **New Client**: Create `data_collection/benzinga_client.py` similar to `eodhd_client.py`
- **Database Table**: Create `analyst_recommendations` table to store recommendations
- **Data Processing**: Add processor method in `data_processor.py` to map API response to database schema
- **Integration**: Add to data orchestrator for collection

### 3.4 Response Format Adapter

**File**: `rlvr/response_adapter.py` (new)

**Purpose**: Convert new 5-7 section format to old format for reward function compatibility.

**Function**:
```python
def adapt_structured_response_to_legacy(structured_response: Dict) -> Dict:
    """
    Convert 5-7 section structured response to legacy format.
    
    Args:
        structured_response: New format with fundamentals, technical, etc.
        
    Returns:
        Legacy format: {"action": "...", "reasoning": "...", "support": "..."}
    """
    conclusion = structured_response.get("conclusion", {})
    recommendation = conclusion.get("recommendation", "hold")
    
    # Convert "Strong Buy" → "strong_buy"
    action_map = {
        "Strong Buy": "strong_buy",
        "Buy": "buy",
        "Hold": "hold",
        "Sell": "sell",
        "Strong Sell": "strong_sell"
    }
    action = action_map.get(recommendation, "hold")
    
    # Combine reasoning from all sections
    reasoning_parts = []
    if structured_response.get("fundamentals"):
        reasoning_parts.append("Fundamentals: " + str(structured_response["fundamentals"]))
    if structured_response.get("technical"):
        reasoning_parts.append("Technical: " + str(structured_response["technical"]))
    if structured_response.get("news"):
        reasoning_parts.append("News: " + str(structured_response["news"]))
    reasoning = "\n\n".join(reasoning_parts)
    
    # Extract support from conclusion
    support = conclusion.get("reasoning", "") + "\n" + conclusion.get("confidence", "")
    
    return {
        "action": action,
        "reasoning": reasoning,
        "support": support
    }
```

### 3.5 Dataset Generator Updates

**File**: `rlvr/dataset_generator.py` (modify existing)

**Changes**:
1. Add option to use `StructuredPromptBuilder` instead of `EnhancedCumulativePromptBuilder`
2. Update `_process_thesis_to_example()` to:
   - Validate new response structure (5-7 sections)
   - Use adapter to convert to legacy format for reward function
   - Store both formats in metadata
3. Ensure Fireworks-AI JSONL format compatibility

### 3.6 JSON Formatter Updates

**File**: `rlvr/json_formatter.py` (modify existing)

**Changes**:
1. Add validation for new response structure:
   ```python
   def validate_structured_response(response: Dict) -> Tuple[bool, List[str]]:
       """Validate 5-7 section response structure"""
       errors = []
       required_sections = ["fundamentals", "technical", "news", "valuation", "risk_assessment", "macro", "conclusion"]
       # ... validation logic
   ```

2. Validate `conclusion.recommendation`:
   - Must be one of: "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"

3. Update `validate_training_example()` and `validate_dev_example()` to support both formats

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Data Collection Enhancements

#### TODO 1.1: Add ATR and ADX Calculations
- [ ] Install/verify pandas-ta library dependency
- [ ] Add `_calculate_atr()` method to `feature_engineering.py`
- [ ] Add `_calculate_adx()` method to `feature_engineering.py`
- [ ] Create database migration script: `database/05_add_atr_adx.sql`
  - Add `atr_14`, `adx_14`, `di_plus_14`, `di_minus_14` columns to `market_data` table
  - Use `ALTER TABLE` with `DEFAULT NULL` for backward compatibility
- [ ] Update `_calculate_technical_indicators()` to include ATR and ADX
- [ ] Test calculations with sample data
- [ ] Run backfill for existing market_data records (optional)

#### TODO 1.2: Analyst Recommendations Integration (Benzinga API)
- [ ] Review Benzinga API documentation: https://docs.benzinga.com/benzinga-apis/analyst-insights/get-analyst-insights
- [ ] Create `data_collection/benzinga_client.py`:
  - Implement `BenzingaClient` class similar to `EODHDClient`
  - **Base URL**: `https://api.benzinga.com/api/v1/`
  - **Authentication**: Use `token` query parameter (not header)
  - **Endpoint**: `analyst/insights`
  - Add `get_analyst_insights(symbols: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None, page: int = 1, page_size: int = 100)` method
    - Query parameter: `symbols` (CSV string of ticker symbols)
    - Query parameter: `token` (API key)
    - Query parameter: `page` (for pagination)
    - Query parameter: `pageSize` (max items per page, default 10, max 100)
    - **Note**: API may not support date filtering in query params - filter by `date` field in response after fetching
    - Handle pagination to fetch all results (loop through pages until no more results)
    - Filter results by `date` field if `start_date` or `end_date` provided
  - Handle rate limiting and error handling
  - Use `BENZINGA_API_KEY` from config
- [ ] Add `BENZINGA_API_KEY` to `config_manager.py`:
  - Add to API Keys section: `self.BENZINGA_API_KEY = os.environ.get("BENZINGA_API_KEY", "")`
  - (API key already added to .env file)
- [ ] Create `analyst_recommendations` table schema:
  ```sql
  CREATE TABLE analyst_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    ticker_id INTEGER REFERENCES tickers(ticker_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    firm VARCHAR(100) NOT NULL,
    firm_id VARCHAR(100),
    analyst_insight_id VARCHAR(100) UNIQUE,  -- Benzinga insight ID (UUID)
    rating_id VARCHAR(100),  -- Benzinga rating ID
    action VARCHAR(50),  -- "Reiterates", "Upgrades", "Downgrades", "Maintains", "Initiates"
    rating VARCHAR(50),  -- "Buy", "Hold", "Sell", "Strong Buy", "Strong Sell", etc.
    target_price NUMERIC(18, 4),  -- From "pt" field
    analyst_insights TEXT,  -- Full insight text from "analyst_insights" field
    updated_timestamp BIGINT,  -- From "updated" field (Unix timestamp)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker_id, date, firm_id, analyst_insight_id)
  );
  CREATE INDEX idx_analyst_recs_ticker_date ON analyst_recommendations(ticker_id, date);
  CREATE INDEX idx_analyst_recs_date ON analyst_recommendations(date);
  ```
- [ ] Add data processor method in `data_processor.py`:
  - `process_analyst_recommendations(raw_data: List[Dict], symbol: str)` method
  - Map Benzinga API response fields:
    - `id` → `analyst_insight_id`
    - `firm` → `firm`
    - `firm_id` → `firm_id`
    - `rating` → `rating`
    - `rating_id` → `rating_id`
    - `action` → `action` (determines rating_change logic)
    - `pt` → `target_price` (convert string to numeric)
    - `analyst_insights` → `analyst_insights`
    - `date` → `date` (parse date string)
    - `updated` → `updated_timestamp`
    - `security.symbol` → validate matches ticker
  - Determine `rating_change` from `action` field:
    - "Upgrades" → "upgrade"
    - "Downgrades" → "downgrade"
    - "Reiterates" or "Maintains" → "maintain"
    - "Initiates" → "initiate"
- [ ] Integrate into `data_orchestrator.py`:
  - Add analyst recommendations collection to `collect_data_for_ticker()`
  - Call `benzinga_client.get_analyst_insights([symbol], start_date, end_date)`
  - Process results through `data_processor.process_analyst_recommendations()`
  - Store in database via database manager
- [ ] Add to `database_manager.py`:
  - Create `AnalystRecommendation` SQLAlchemy model class matching schema above
  - Add `insert_analyst_recommendations(session, ticker_id, recommendations: List[Dict])` method
  - Add `get_analyst_recommendations(ticker_id, as_of_date, lookback_days=90)` query method
  - Handle deduplication based on `analyst_insight_id` (unique constraint)

### Phase 2: New Structured Prompt Builder

#### TODO 2.1: Create Structured Prompt Builder
- [ ] Create `thesis_generation/structured_prompt_builder.py`
- [ ] Implement `StructuredPromptBuilder` class
- [ ] Implement data query methods:
  - [ ] `_query_fundamentals(ticker_id, as_of_date)` - Query quarterly fundamentals
  - [ ] `_query_news_by_buckets(ticker_id, as_of_date)` - Query news in time buckets (3, 4-10, 11-30 trading days)
  - [ ] `_query_price_history(ticker_id, as_of_date, days=11)` - Query exactly 11 trading days (use market calendar)
  - [ ] `_query_insider_transactions(ticker_id, as_of_date)` - Query recent insider trades
  - [ ] `_query_macro_indicators(as_of_date, days=90)` - Query macro indicators
  - [ ] `_query_analyst_recommendations(ticker_id, as_of_date)` - Query analyst recommendations from `analyst_recommendations` table (last 90 days)
- [ ] Implement `build_structured_prompt(ticker, as_of_date)` method
- [ ] Build system prompt with:
  - Instructions for 5-7 section structure
  - JSON schema specification
  - Few-shot examples
- [ ] Build user prompt organized by data sections

#### TODO 2.2: Response Format Specification
- [ ] Define exact JSON schema for 5-7 section response (see Section 2.2)
- [ ] Create Pydantic model or JSON schema validator (optional)
- [ ] Add validation function for response structure
- [ ] Test with sample prompts and DeepSeek-V3-Terminus base model

### Phase 3: Response Adapter & Dataset Generation

#### TODO 3.1: Create Response Adapter
- [ ] Create `rlvr/response_adapter.py`
- [ ] Implement `adapt_structured_response_to_legacy()` function
- [ ] Test adapter with sample structured responses
- [ ] Ensure reward function compatibility

#### TODO 3.2: Update Dataset Generator
- [ ] Modify `rlvr/dataset_generator.py` to support structured prompts
- [ ] Add configuration option: `USE_STRUCTURED_PROMPTS = True/False`
- [ ] Update `_process_thesis_to_example()` to:
  - Use `StructuredPromptBuilder` when enabled
  - Validate new response structure
  - Use adapter to convert for reward function
  - Store both formats in metadata
- [ ] Test dataset generation with new format

#### TODO 3.3: Update JSON Formatter
- [ ] Add `validate_structured_response()` function
- [ ] Add validation for `conclusion.recommendation` (must be one of 5 tiers)
- [ ] Update `validate_training_example()` and `validate_dev_example()` to support both formats
- [ ] Ensure Fireworks-AI format compatibility

### Phase 4: Base Model Response Collection

#### TODO 4.1: Create Response Collection Script
- [ ] Create `scripts/collect_structured_responses.py`
- [ ] Script should:
  - Query all available tickers/dates from database (or accept --tickers, --start-date, --end-date flags)
  - Generate structured prompts using `StructuredPromptBuilder`
  - Call DeepSeek-V3-Terminus base model (via Fireworks AI or direct API)
  - Store responses in existing `thesis_generations.assistant_response` (JSONB column)
  - Mark with special flag/metadata to distinguish from legacy format
  - Validate all responses match required structure
  - Generate training dataset (train.jsonl, dev.jsonl) in Fireworks-AI format (messages + ground_truth + metadata)

#### TODO 4.2: Integration Testing
- [ ] Test data collection with new ATR/ADX calculations
- [ ] Test prompt generation with all data sources
- [ ] Test response generation with DeepSeek-V3-Terminus base model
- [ ] Validate JSON response structure
- [ ] Test adapter conversion to legacy format
- [ ] Test reward function with adapted responses
- [ ] Test dataset generation end-to-end

### Phase 5: Documentation & Validation

#### TODO 5.1: Documentation
- [ ] Document new prompt structure in `llms.txt`
- [ ] Document response format schema
- [ ] Create example prompts and responses
- [ ] Update `README.md` with new workflow
- [ ] Document adapter function usage

#### TODO 5.2: Validation
- [ ] Validate all required data is available in database
- [ ] Validate prompt generation works for all tickers
- [ ] Validate response structure matches requirements
- [ ] Validate Fireworks-AI compatibility
- [ ] Validate reward function compatibility via adapter

---

## 5. CODE REUSE STRATEGY

### 5.1 Existing Components to Reuse

1. **Database Manager** (`data_collection/database_manager.py`):
   - ✅ Reuse all existing models and query methods
   - ✅ Add new query methods for time-bucketed news queries
   - ✅ Add query methods for analyst recommendations (new table)

2. **Data Orchestrator** (`data_collection/data_orchestrator.py`):
   - ✅ Reuse `get_data_for_date()` method
   - ✅ Extend to support new data requirements (ATR, ADX, analyst recommendations via Benzinga)

3. **Feature Engineering** (`data_collection/feature_engineering.py`):
   - ✅ Reuse existing technical indicator calculations
   - ✅ Add ATR and ADX calculations

4. **JSON Formatter** (`rlvr/json_formatter.py`):
   - ✅ Reuse existing validation and formatting functions
   - ✅ Extend validation for new response structure

5. **Dataset Generator** (`rlvr/dataset_generator.py`):
   - ✅ Reuse existing dataset generation logic
   - ✅ Modify to use new prompt builder when configured

6. **LLM Clients** (`thesis_generation/fireworks_client.py`, `deepseek_client.py`):
   - ✅ Reuse existing LLM client infrastructure
   - ✅ Use for generating structured responses from base model

### 5.2 New Components Needed

1. **Structured Prompt Builder** - New module (`thesis_generation/structured_prompt_builder.py`)
2. **ATR/ADX Calculations** - Extend existing feature engineering
3. **Benzinga Client** - New module (`data_collection/benzinga_client.py`)
   - Base URL: `https://api.benzinga.com/api/v1/`
   - Endpoint: `analyst/insights`
   - Authentication via `token` query parameter
   - Pagination support (page/pageSize)
   - Query by `symbols` parameter
4. **Analyst Recommendations Table** - New database schema
   - Fields: `analyst_insight_id` (unique), `action`, `rating`, `target_price`, `analyst_insights`, `firm`, `firm_id`, `date`, `updated_timestamp`
5. **Response Adapter** - New module (`rlvr/response_adapter.py`)
6. **Response Collection Script** - New script (`scripts/collect_structured_responses.py`)
7. **Database Migrations** - New migration scripts:
   - `database/05_add_atr_adx.sql` - Add ATR/ADX columns
   - `database/06_add_analyst_recommendations.sql` - Create analyst_recommendations table

---

## 6. DESIGN DECISIONS

### 6.1 Data Collection Decisions

1. **Analyst Recommendations**: 
   - **DECISION: Integrate Benzinga API** - Full data source integration
   - API Endpoint: `GET https://api.benzinga.com/api/v1/analyst/insights`
   - Authentication: `token` query parameter (API key)
   - Query by `symbols` (CSV) parameter for ticker filtering
   - Response includes: `action` (Upgrades/Downgrades/Reiterates), `rating` (Buy/Hold/Sell), `pt` (price target), `analyst_insights` (detailed text), `firm`, `date`
   - API Key: `BENZINGA_API_KEY` (already in .env config)
   - Create `benzinga_client.py` similar to `eodhd_client.py` with pagination support
   - Create `analyst_recommendations` database table with fields matching API response
   - Integrate into data collection pipeline

2. **News Time Buckets**: 
   - **DECISION: Use trading days** (consistent with existing system)
   - Last 3 trading days, 4-10 trading days, 11-30 trading days
   - Use `market_calendar.py` to determine trading days

3. **Price History**: 
   - **DECISION: Exactly 11 trading days** (not calendar days)
   - Use market calendar to get exactly 11 trading days
   - Ensures consistent data window regardless of weekends/holidays

### 6.2 Response Structure Decisions

1. **Section Content**: 
   - **DECISION: Mix of text and structured metrics**
   - Each section contains:
     - Narrative text analysis (free-form paragraphs)
     - Structured key metrics (JSON sub-objects with numeric values)
   - Provides both human-readable analysis and machine-parseable data

2. **Valuation Section**: 
   - **DECISION: Include specific metrics**
   - Must include: P/E, P/S, PEG ratios, P/B ratio, EV/EBITDA
   - Plus narrative assessment: "Fair value", "Overvalued", "Undervalued"
   - Plus comparison: vs peers, vs market averages

3. **Risk Assessment**: 
   - **DECISION: Both ticker-specific and general market risks**
   - `ticker_specific_risks`: Company-specific risks (regulatory, competitive, operational)
   - `market_risks`: General market risks (economic downturn, sector headwinds)
   - `mitigation`: Risk mitigation factors
   - `regulatory`: Regulatory concerns

### 6.3 Training Data Generation Decisions

1. **Base Model**: 
   - **DECISION: DeepSeek-V3-Terminus base model** (not fine-tuned)
   - Use for initial response collection to gather training data
   - Via Fireworks AI API or direct DeepSeek API

2. **Response Collection**: 
   - **DECISION: Generate for all available data** (with optional filtering)
   - Script accepts optional flags: `--tickers`, `--start-date`, `--end-date`
   - Default: Generate for all tickers/dates in database
   - Allows flexibility for targeted collection

3. **Reward Function**: 
   - **DECISION: Use adapter approach** (convert new format to old format)
   - Safer approach - maintains compatibility with existing reward function
   - No changes needed to reward function code
   - Adapter extracts `action`, `reasoning`, `support` from structured format

### 6.4 Output Format Decisions

1. **Fireworks-AI Compatibility**: 
   - **DECISION: Match existing RLVR format**
   - Format: `messages` (system + user prompts) + `ground_truth` + `metadata`
   - Compatible with existing GRPO training pipeline
   - No changes needed to training workflow

2. **Response Storage**: 
   - **DECISION: Use existing `thesis_generations.assistant_response` (JSONB)**
   - Store structured response in existing JSONB column
   - Add metadata flag to distinguish from legacy format
   - No new table required - simpler implementation

---

## 7. ESTIMATED EFFORT

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Data Collection | ATR/ADX calculations, Benzinga API integration for analyst recommendations | 6-8 hours |
| Phase 2: Prompt Builder | New structured prompt builder | 6-8 hours |
| Phase 3: Adapter & Dataset | Response adapter, dataset generator updates | 4-5 hours |
| Phase 4: Response Collection | Collection script, integration testing | 5-7 hours |
| Phase 5: Documentation | Documentation and validation | 2-3 hours |
| **Total** | | **23-31 hours** |

---

## 8. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| ATR/ADX calculations may be computationally expensive | Medium | Use efficient pandas-ta library or vectorized calculations |
| Benzinga API may have rate limits or data availability issues | Medium | Implement proper rate limiting, error handling, pagination support, and graceful degradation if API unavailable. Handle pagination (page/pageSize) to fetch all results. |
| New response structure may not be compatible with existing reward function | High | Use adapter function to convert new format to old format (tested approach) |
| DeepSeek-V3-Terminus may not consistently follow 5-7 section structure | Medium | Add strict validation, use few-shot examples in system prompt, implement retry logic |
| Database migration for new columns may affect existing data | Low | Use ALTER TABLE with DEFAULT NULL, test on dev database first |
| Token budget may be exceeded with comprehensive data | Medium | Use hierarchical summarization (reuse existing approach from EnhancedCumulativePromptBuilder) |

---

## 9. NEXT STEPS

1. **Review this revised plan** with all design decisions finalized (Section 6)
2. **Approve the approach** to proceed with implementation
3. **Begin implementation** starting with Phase 1 (Data Collection Enhancements)
4. **Iterate** based on testing results

---

## 10. APPENDIX: Example Response Structure

See Section 2.2 for the complete JSON schema example.

---

**END OF PLAN**

**Status**: Revised with all design decisions finalized - Ready for implementation approval

**Key Decisions Made**:
- ✅ Analyst recommendations: **Benzinga API integration** (full data source integration)
- ✅ News time buckets: Trading days (consistent with existing system)
- ✅ Price history: Exactly 11 trading days
- ✅ Section content: Mix of text and structured metrics
- ✅ Valuation: Include specific metrics (P/E, P/S, PEG, etc.)
- ✅ Risk assessment: Both ticker-specific and market risks
- ✅ Base model: DeepSeek-V3-Terminus base model
- ✅ Response collection: All available data (with optional filtering)
- ✅ Reward function: Adapter approach (maintains compatibility)
- ✅ Output format: Existing RLVR format (messages + ground_truth + metadata)
- ✅ Response storage: Existing `thesis_generations.assistant_response` (JSONB)
