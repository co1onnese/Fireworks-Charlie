# Training Prompts Collection Plan
## For DeepSeek-V3-Terminus Base Model Fine-Tuning

**Date**: 2025-11-14  
**Goal**: Create a new collection of training prompts that collect comprehensive financial data and structure LLM responses into 5-7 sections for Fireworks-AI compatible JSON output.

---

## 1. REQUIREMENTS ANALYSIS

### 1.1 Required Data Collection

#### ✅ **Available in Database**:
1. **Financial Data (Fundamentals)**:
   - ✅ Balance sheet (quarterly) - `fundamentals` table: `total_assets`, `total_liabilities`, `stockholder_equity`, `cash_and_equivalents`, `total_debt`, `balance_sheet_json` (JSONB)
   - ✅ Income statement (quarterly) - `fundamentals` table: `revenue`, `gross_profit`, `operating_income`, `net_income`, `ebitda`, `income_statement_json` (JSONB)
   - ✅ Cash flow statement (quarterly) - `fundamentals` table: `operating_cash_flow`, `free_cash_flow`, `cash_flow_json` (JSONB)
   - ✅ SEC filings metadata - `fundamentals` table: `report_date`, `filing_date`
   - ✅ Financial metrics - `fundamentals` table: `pe_ratio`, `pb_ratio`, `ps_ratio`, `eps`, `market_cap`, `revenue_qoq_pct`, `revenue_yoy_pct`, `net_income_qoq_pct`, `net_income_yoy_pct`

2. **News Data**:
   - ✅ Recent news articles - `news` table with `published_at`, `headline`, `summary`, `content`, `source`
   - ✅ Sentiment analysis - `news` table: `sentiment_score`, `sentiment_label`, `sentiment_confidence`
   - ✅ News aggregation - `news_sentiment_features` table: `sentiment_7day_avg`, `sentiment_7day_count`, `daily_article_count`

3. **Market Data**:
   - ✅ Price history - `market_data` table: `date`, `open`, `high`, `low`, `close`, `adjusted_close`, `volume`
   - ✅ Technical indicators - `market_data` table:
     - ✅ RSI (14-period) - `rsi_14`
     - ✅ MACD - `macd`, `macd_signal`
     - ✅ EMA (20-period) - `ema_20`
     - ✅ SMA (20, 50-period) - `sma_20`, `sma_50`
     - ✅ Bollinger Bands - `bollinger_upper`, `bollinger_lower`
     - ❌ **ATR (Average True Range)** - NOT CURRENTLY CALCULATED
     - ❌ **ADX (Average Directional Index)** - NOT CURRENTLY CALCULATED

4. **Sentiment Data**:
   - ✅ Insider transactions - `insider_transactions` table: `transaction_date`, `owner_name`, `owner_title`, `transaction_code`, `shares`, `transaction_price`, `shares_owned_after`
   - ❌ **Analyst recommendations** - NOT CURRENTLY IN DATABASE

5. **Macro Data**:
   - ✅ Economic indicators - `macroeconomic_indicators` table: `series_id`, `indicator_name`, `date`, `value`, `unit`, `frequency`
   - ✅ Derived macro features - `macro_features` table: `yield_curve_10y_2y`, `yield_curve_10y_3m`, `cpi_monthly_pct`, `cpi_yoy_pct`, `pce_monthly_pct`, `pce_yoy_pct`, `gdp_qoq_pct`, `industrial_production_mom_pct`, `unemployment_rate`, `unemployment_rate_change`, `fed_funds_rate`

#### ❌ **Missing Data**:
1. **ATR (Average True Range)** - Need to calculate from OHLCV data
2. **ADX (Average Directional Index)** - Need to calculate from price data
3. **Analyst Recommendations** - Need to add data source (EODHD API may have this, or need alternative source)

### 1.2 Required Response Structure

The LLM response must be structured into **5-7 sections**:

1. **`fundamentals`** - Financial statements, balance sheet strength, income performance
2. **`technical`** - Price action, indicators, momentum
3. **`news`** - Recent developments, earnings, AI/cloud growth
4. **`valuation`** - Based on earnings and growth metrics
5. **`risk_assessment`** - Data center delays, regulatory risks
6. **`macro`** - Economic environment impact
7. **`conclusion`** - Final recommendation with 5-tier scale: **Strong Buy, Buy, Hold, Sell, Strong Sell**

---

## 2. DATA AVAILABILITY ASSESSMENT

### 2.1 Database Schema Review

**Current Database Tables**:
- ✅ `tickers` - Master ticker registry
- ✅ `market_data` - Daily OHLCV + technical indicators (partitioned by date)
- ✅ `fundamentals` - Quarterly financial statements with JSONB for full statements
- ✅ `news` - News articles with sentiment analysis
- ✅ `macroeconomic_indicators` - FRED economic data
- ✅ `macro_features` - Derived macro features
- ✅ `insider_transactions` - Insider trading data
- ✅ `news_sentiment_features` - Rolling news sentiment aggregates
- ✅ `ticker_event_features` - Time-since-event features

**Data Collection Capabilities**:
- ✅ EODHD API client exists (`eodhd_client.py`) - Can fetch fundamentals, news, insider transactions
- ✅ FRED API client exists (`fred_client.py`) - Can fetch economic indicators
- ✅ Feature engineering exists (`feature_engineering.py`) - Calculates technical indicators
- ✅ Data orchestrator exists (`data_orchestrator.py`) - Coordinates multi-source data collection

### 2.2 Data Gaps & Solutions

| Data Requirement | Status | Solution |
|-----------------|--------|----------|
| ATR (Average True Range) | ❌ Missing | Add calculation in `feature_engineering.py` using pandas-ta or manual calculation |
| ADX (Average Directional Index) | ❌ Missing | Add calculation in `feature_engineering.py` using pandas-ta or manual calculation |
| Analyst Recommendations | ❌ Missing | Check EODHD API for analyst data, or integrate alternative source (e.g., Finnhub, Alpha Vantage) |
| News time buckets (3 days, 4-10 days, 11-30 days) | ✅ Can query | Use SQL date filtering in prompt builder |
| Price history (last 11 trading days) | ✅ Available | Query `market_data` table with date filtering |
| Macro data (past 90 days) | ✅ Available | Query `macro_features` and `macroeconomic_indicators` with date filtering |

---

## 3. PROPOSED SOLUTION ARCHITECTURE

### 3.1 New Prompt Builder Module

**File**: `thesis_generation/structured_prompt_builder.py`

**Purpose**: Create a new prompt builder specifically for the 5-7 section structured response format.

**Key Features**:
1. **Data Collection**:
   - Query fundamentals (quarterly) with full JSONB statements
   - Query news in time buckets: last 3 days, 4-10 days, 11-30 days
   - Query price history (last 11 trading days) with all technical indicators
   - Query insider transactions (limited data)
   - Query macro indicators (past 90 days)
   - Query analyst recommendations (if available)

2. **Prompt Structure**:
   - System prompt: Instructs model to respond in 5-7 sections with specific JSON structure
   - User prompt: Organized data sections matching the required response structure

3. **Response Format**:
   - JSON structure with required sections: `fundamentals`, `technical`, `news`, `valuation`, `risk_assessment`, `macro`, `conclusion`
   - `conclusion` section must include 5-tier recommendation: Strong Buy, Buy, Hold, Sell, Strong Sell

### 3.2 Enhanced Feature Engineering

**File**: `data_collection/feature_engineering.py` (modify existing)

**Additions**:
1. **ATR Calculation**:
   ```python
   def _calculate_atr(self, high, low, close, period=14) -> pd.Series
   ```

2. **ADX Calculation**:
   ```python
   def _calculate_adx(self, high, low, close, period=14) -> Dict[str, pd.Series]
   ```

3. **Database Schema Update**:
   - Add `atr_14` column to `market_data` table
   - Add `adx_14` and `di_plus_14`, `di_minus_14` columns to `market_data` table

### 3.3 Analyst Recommendations Integration

**New File**: `data_collection/analyst_client.py` (if needed)

**Options**:
1. Check if EODHD API provides analyst recommendations
2. Integrate Finnhub API (if available in config)
3. Integrate Alpha Vantage API (if available)
4. Create new table: `analyst_recommendations` with fields: `ticker_id`, `date`, `analyst_firm`, `recommendation` (Strong Buy/Buy/Hold/Sell/Strong Sell), `target_price`, `rating_change`

### 3.4 Dataset Generator Adaptation

**File**: `rlvr/dataset_generator.py` (modify existing)

**Changes**:
1. Use new `structured_prompt_builder` instead of `enhanced_prompt_builder`
2. Validate response structure matches 5-7 section format
3. Ensure `conclusion` section contains valid 5-tier recommendation

### 3.5 JSON Formatter Updates

**File**: `rlvr/json_formatter.py` (modify existing)

**Changes**:
1. Add validation for new response structure (5-7 sections)
2. Validate `conclusion` section contains one of: Strong Buy, Buy, Hold, Sell, Strong Sell
3. Ensure Fireworks-AI compatibility for new format

---

## 4. IMPLEMENTATION PLAN

### Phase 1: Data Collection Enhancements

#### TODO 1.1: Add ATR and ADX Calculations
- [ ] Add ATR calculation method to `feature_engineering.py`
- [ ] Add ADX calculation method to `feature_engineering.py`
- [ ] Create database migration script to add `atr_14`, `adx_14`, `di_plus_14`, `di_minus_14` columns to `market_data` table
- [ ] Update `_calculate_technical_indicators()` to include ATR and ADX
- [ ] Test calculations with sample data

#### TODO 1.2: Add Analyst Recommendations Support
- [ ] Research EODHD API for analyst recommendations endpoint
- [ ] If available, add method to `eodhd_client.py` to fetch analyst recommendations
- [ ] If not available, research alternative APIs (Finnhub, Alpha Vantage)
- [ ] Create `analyst_recommendations` table schema
- [ ] Add data processor method for analyst recommendations
- [ ] Integrate into data orchestrator

### Phase 2: New Prompt Builder

#### TODO 2.1: Create Structured Prompt Builder
- [ ] Create `thesis_generation/structured_prompt_builder.py`
- [ ] Implement `StructuredPromptBuilder` class
- [ ] Implement `build_structured_prompt()` method that:
  - Queries fundamentals (quarterly) with full JSONB statements
  - Queries news in time buckets (3 days, 4-10 days, 11-30 days)
  - Queries price history (last 11 trading days) with all technical indicators
  - Queries insider transactions
  - Queries macro indicators (past 90 days)
  - Queries analyst recommendations (if available)
- [ ] Build system prompt with 5-7 section structure instructions
- [ ] Build user prompt organized by data sections
- [ ] Define JSON response format schema

#### TODO 2.2: Response Format Specification
- [ ] Define exact JSON schema for 5-7 section response:
  ```json
  {
    "fundamentals": "...",
    "technical": "...",
    "news": "...",
    "valuation": "...",
    "risk_assessment": "...",
    "macro": "...",
    "conclusion": {
      "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
      "reasoning": "...",
      "confidence": 0.0-1.0
    }
  }
  ```
- [ ] Add validation function for response structure
- [ ] Test with sample prompts

### Phase 3: Dataset Generation Updates

#### TODO 3.1: Update Dataset Generator
- [ ] Modify `rlvr/dataset_generator.py` to use `StructuredPromptBuilder`
- [ ] Update `_process_thesis_to_example()` to validate new response structure
- [ ] Ensure compatibility with existing reward function
- [ ] Test dataset generation with new format

#### TODO 3.2: Update JSON Formatter
- [ ] Add validation for 5-7 section response structure
- [ ] Add validation for `conclusion.recommendation` (must be one of 5 tiers)
- [ ] Update `validate_training_example()` and `validate_dev_example()`
- [ ] Ensure Fireworks-AI format compatibility

### Phase 4: Integration & Testing

#### TODO 4.1: Integration Testing
- [ ] Test data collection with new ATR/ADX calculations
- [ ] Test prompt generation with all data sources
- [ ] Test response generation with DeepSeek-V3-Terminus base model
- [ ] Validate JSON response structure
- [ ] Test dataset generation end-to-end

#### TODO 4.2: Base Model Response Collection
- [ ] Create script to generate prompts for all available tickers/dates
- [ ] Use DeepSeek-V3-Terminus base model (via Fireworks AI or direct API) to generate responses
- [ ] Store responses in database (new table or extend `thesis_generations`)
- [ ] Validate all responses match required structure
- [ ] Generate training dataset (train.jsonl, dev.jsonl) in Fireworks-AI format

### Phase 5: Documentation & Validation

#### TODO 5.1: Documentation
- [ ] Document new prompt structure
- [ ] Document response format schema
- [ ] Update `llms.txt` with new module information
- [ ] Create example prompts and responses

#### TODO 5.2: Validation
- [ ] Validate all required data is available in database
- [ ] Validate prompt generation works for all tickers
- [ ] Validate response structure matches requirements
- [ ] Validate Fireworks-AI compatibility

---

## 5. CODE REUSE STRATEGY

### 5.1 Existing Components to Reuse

1. **Database Manager** (`data_collection/database_manager.py`):
   - ✅ Reuse all existing models and query methods
   - ✅ Add new query methods for time-bucketed news queries
   - ✅ Add query methods for analyst recommendations (if new table created)

2. **Data Orchestrator** (`data_collection/data_orchestrator.py`):
   - ✅ Reuse `get_data_for_date()` method
   - ✅ Extend to support new data requirements (ATR, ADX, analyst recommendations)

3. **Feature Engineering** (`data_collection/feature_engineering.py`):
   - ✅ Reuse existing technical indicator calculations
   - ✅ Add ATR and ADX calculations

4. **JSON Formatter** (`rlvr/json_formatter.py`):
   - ✅ Reuse existing validation and formatting functions
   - ✅ Extend validation for new response structure

5. **Dataset Generator** (`rlvr/dataset_generator.py`):
   - ✅ Reuse existing dataset generation logic
   - ✅ Modify to use new prompt builder

### 5.2 New Components Needed

1. **Structured Prompt Builder** - New module
2. **ATR/ADX Calculations** - Extend existing feature engineering
3. **Analyst Recommendations Client** - New module (if needed)
4. **Response Validator** - Extend existing JSON formatter

---

## 6. QUESTIONS FOR CLARIFICATION

### 6.1 Data Collection
1. **Analyst Recommendations**: Do you have a preferred data source for analyst recommendations? (EODHD, Finnhub, Alpha Vantage, or another?)
2. **News Time Buckets**: Should news be grouped by calendar days or trading days? (Current system uses trading days)
3. **Price History**: "Last 11 trading days" - should this be exactly 11 days or at least 11 days (more if needed for context)?

### 6.2 Response Structure
1. **Section Content**: Should each section (fundamentals, technical, news, etc.) be:
   - Free-form text paragraphs?
   - Structured JSON with sub-sections?
   - A mix of both?
2. **Valuation Section**: Should this include specific metrics (P/E, P/S, PEG ratios) or just narrative analysis?
3. **Risk Assessment**: Should this be ticker-specific risks or general market risks, or both?

### 6.3 Training Data Generation
1. **Base Model**: Confirm we're using DeepSeek-V3-Terminus base model (not fine-tuned) for initial response collection?
2. **Response Collection**: Should we:
   - Generate responses for all existing thesis generations in database?
   - Generate responses for a specific date range?
   - Generate responses for specific tickers only?
3. **Reward Function**: Will the existing reward function work with the new 5-7 section structure, or does it need modification?

### 6.4 Output Format
1. **Fireworks-AI Compatibility**: Should the output format match the existing RLVR format (messages + ground_truth + metadata) or a different format?
2. **Response Storage**: Should structured responses be stored in:
   - Existing `thesis_generations.assistant_response` (JSONB)?
   - New table specifically for structured responses?
   - Both?

---

## 7. ESTIMATED EFFORT

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Data Collection | ATR/ADX calculations, Analyst recommendations | 4-6 hours |
| Phase 2: Prompt Builder | New structured prompt builder | 6-8 hours |
| Phase 3: Dataset Generation | Updates to generator and formatter | 3-4 hours |
| Phase 4: Integration & Testing | End-to-end testing | 4-6 hours |
| Phase 5: Documentation | Documentation and validation | 2-3 hours |
| **Total** | | **19-27 hours** |

---

## 8. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|------------|
| ATR/ADX calculations may be computationally expensive | Medium | Use efficient pandas-ta library or vectorized calculations |
| Analyst recommendations may not be available from APIs | High | Make analyst recommendations optional, use placeholder if unavailable |
| New response structure may not be compatible with existing reward function | High | Test reward function with new structure, modify if needed |
| DeepSeek-V3-Terminus may not consistently follow 5-7 section structure | Medium | Add strict validation, use few-shot examples in system prompt |
| Database migration for new columns may affect existing data | Low | Use ALTER TABLE with DEFAULT values, test on dev database first |

---

## 9. NEXT STEPS

1. **Review this plan** and answer clarification questions
2. **Approve the approach** or request modifications
3. **Begin implementation** starting with Phase 1 (Data Collection Enhancements)
4. **Iterate** based on testing results

---

## 10. APPENDIX: Example Response Structure

```json
{
  "fundamentals": {
    "balance_sheet_strength": "Strong balance sheet with $X in cash, debt-to-equity of Y",
    "income_performance": "Revenue growth of Z% YoY, net income margin of W%",
    "cash_flow": "Operating cash flow of $A, free cash flow of $B"
  },
  "technical": {
    "price_action": "Stock trading at $X, up Y% over last 11 days",
    "indicators": "RSI at Z (neutral), MACD bullish crossover, price above SMA20",
    "momentum": "Strong upward momentum with increasing volume"
  },
  "news": {
    "recent_3_days": "2 articles: positive earnings beat, new product launch",
    "recent_4_10_days": "5 articles: analyst upgrades, strong quarterly results",
    "recent_11_30_days": "12 articles: overall positive sentiment, sector growth"
  },
  "valuation": {
    "metrics": "P/E ratio of X, P/S ratio of Y, PEG ratio of Z",
    "assessment": "Trading at fair value relative to growth prospects"
  },
  "risk_assessment": {
    "key_risks": "Regulatory concerns, competitive pressure, market volatility",
    "mitigation": "Strong market position, diversified revenue streams"
  },
  "macro": {
    "economic_environment": "Positive yield curve, low unemployment, stable inflation",
    "impact": "Favorable macro environment supports growth stocks"
  },
  "conclusion": {
    "recommendation": "Buy",
    "reasoning": "Strong fundamentals, positive technical indicators, favorable macro environment",
    "confidence": 0.75,
    "target_price": "$X",
    "time_horizon": "3-6 months"
  }
}
```

---

**END OF PLAN**
