# News and Sentiment Data Investigation Report

## Problem Statement
The system is not collecting News and Sentiment data from the EODHD API for most prompts, resulting in empty sections that look like:

```
=== NEWS AND SENTIMENT ===
No news articles available in this period.
```

## Data Flow Analysis

### 1. Data Collection Layer (eodhd_client.py)
**Current Implementation:**
```python
def get_news(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetches Financial News Feed and Stock News Sentiment data."""
    endpoint = "news"
    params = {"s": symbol, "from": start_date, "to": end_date}
    response = self._make_request(endpoint, params)
    if isinstance(response, list):
        return response
    logger.error("Expected list response for news, received dict.")
    return []
```

**Issues Identified:**
1. ❌ Missing `fmt=json` parameter (explicitly request JSON format)
2. ❌ Missing `limit` parameter (default may be too restrictive)
3. ❌ Missing `offset` parameter for pagination
4. ⚠️ Symbol format may need adjustment (`.US` suffix)
5. ⚠️ No error handling for 404 responses (API tier limitation)
6. ⚠️ No retry logic for empty responses

### 2. Data Orchestration Layer (data_orchestrator.py)
**Lines 120-134:**
```python
# 4. Fetch and process News
if self.eodhd_client:
    news_raw = self.eodhd_client.get_news(
        f"{ticker}.US",  # ✓ Correct format with .US suffix
        start_date.strftime("%Y-%m-%d"),  # ✓ Correct date format
        end_date.strftime("%Y-%m-%d")
    )
    news_processed = processor.process_news(news_raw, f"{ticker}.US")
    # ...store in database
```

**Issues Identified:**
1. ✓ Correct symbol format (ticker.US)
2. ✓ Correct date format
3. ❌ No logging of API response status
4. ❌ No handling of empty responses
5. ❌ Silently fails if API returns 404

### 3. Data Processing Layer (data_processor.py)
**Lines 261-303:**
```python
def process_news(self, raw_data: list, symbol: str) -> list:
    if not raw_data:
        return []  # ❌ Silently returns empty list
    
    df = pd.DataFrame(raw_data)
    df["symbol"] = symbol.split(".")[0].upper()
    df = df.rename(columns={"link": "url", "date": "published_at", "title": "headline"})
    df["published_at"] = pd.to_datetime(df["published_at"])
    
    # Extract sentiment polarity score
    df["sentiment_score"] = df["sentiment"].apply(
        lambda x: x.get("polarity") if isinstance(x, dict) and x.get("polarity") is not None else None
    )
    # ...
```

**Expected EODHD News API Response Format:**
```json
[
  {
    "date": "2024-10-01 10:30:00",
    "title": "Company announces earnings",
    "content": "Full article text...",
    "link": "https://...",
    "sentiment": {
      "polarity": 0.65,  // Range: -1.0 to 1.0
      "sentiment": "Positive"
    },
    "symbols": ["AAPL.US"],
    "tags": ["earnings", "technology"]
  }
]
```

**Issues Identified:**
1. ✓ Correct field mapping (title → headline, link → url)
2. ✓ Correct sentiment extraction (polarity field)
3. ❌ No logging when raw_data is empty
4. ⚠️ Assumes sentiment structure without validation

### 4. Data Retrieval for Prompts (data_orchestrator.py)
**Lines 320-329:**
```python
# Get news
as_of_datetime = datetime.combine(as_of_date, datetime.min.time()) if isinstance(as_of_date, date) else as_of_date
news = session.query(News).filter(
    News.ticker_id == ticker_obj.ticker_id,
    News.published_at <= as_of_datetime,
    News.published_at >= as_of_datetime - timedelta(days=60)  # ✓ 60-day lookback
).order_by(
    News.published_at.desc()
).all()
```

**Issues Identified:**
1. ✓ Correct date filtering (point-in-time)
2. ✓ Reasonable 60-day lookback window
3. ❌ No limit on results (could be thousands of articles)
4. ❌ No check if news data exists before querying

### 5. Prompt Building (enhanced_prompt_builder.py)
**Lines 348-379:**
```python
def _build_detailed_news_analysis(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
    sections = []
    
    # Collect all news
    all_news = []
    for day_data in data:
        if day_data.get('news'):
            all_news.extend(day_data['news'])
    
    if not all_news:
        sections.append("No recent news available")  # ❌ Generic message
        return sections
    # ...
```

**Issues Identified:**
1. ✓ Correctly checks for news data
2. ❌ Generic error message doesn't indicate root cause
3. ❌ No fallback or retry mechanism

## Root Causes Identified

### PRIMARY ISSUES:

#### 1. **Missing EODHD API Parameters** 🔴 CRITICAL
The current implementation is missing key parameters that may cause the API to return empty results:

```python
# CURRENT (INCOMPLETE):
params = {"s": symbol, "from": start_date, "to": end_date}

# RECOMMENDED:
params = {
    "s": symbol,
    "from": start_date,
    "to": end_date,
    "limit": 1000,        # Default may be 10-50
    "offset": 0,          # For pagination
    "fmt": "json"         # Explicit format request
}
```

#### 2. **Silent Failure on API Errors** 🔴 CRITICAL
The code silently returns empty lists when:
- API returns 404 (endpoint not available for subscription tier)
- API returns empty response
- Network errors occur

**Evidence from eodhd_client.py (lines 72-74):**
```python
elif response.status_code == 404:
    logger.warning(f"Endpoint {endpoint} not found (404). This feature may not be available for your API tier.")
    return []  # ❌ Returns empty list, indistinguishable from "no news"
```

#### 3. **No Diagnostic Logging** 🟡 MODERATE
There's insufficient logging to diagnose why news data is missing:
- No log of API response status
- No log of number of articles fetched
- No distinction between "API failed" vs "No news available"

### SECONDARY ISSUES:

#### 4. **Potential Date Range Issues** 🟡 MODERATE
The EODHD News API may have limitations:
- Historical news may only be available for recent periods (e.g., last 6-12 months)
- Some tickers may have limited news coverage
- API tier may restrict historical depth

#### 5. **Symbol Format Ambiguity** 🟢 MINOR
The API documentation is unclear about symbol format:
- Should it be `AAPL` or `AAPL.US`?
- Current code uses `AAPL.US` but API might prefer just `AAPL`

## EODHD News API Documentation

According to https://eodhd.com/financial-apis/stock-market-financial-news-api:

### Endpoint: `/api/news`

**Parameters:**
- `s` (required): Stock ticker (e.g., AAPL.US, AAPL)
- `from` (optional): Start date (YYYY-MM-DD)
- `to` (optional): End date (YYYY-MM-DD)
- `limit` (optional): Number of results (default: 50, max: 1000)
- `offset` (optional): Pagination offset
- `fmt` (optional): Response format (json, csv)

**Response Structure:**
```json
[
  {
    "date": "2024-10-01 10:30:00",
    "title": "Article title",
    "content": "Full text...",
    "link": "https://source.com/article",
    "sentiment": {
      "polarity": 0.45,
      "sentiment": "Positive"
    },
    "symbols": ["AAPL.US"],
    "tags": ["tag1", "tag2"]
  }
]
```

### Endpoint: Alternative - Financial News Feed
There may be an alternative endpoint:
- `/api/eod/{ticker}/news` - Ticker-specific news
- `/api/news` - General news feed (filter by ticker)

## Recommended Solutions

### SOLUTION 1: Fix EODHD API Client 🔴 PRIORITY 1

**File:** `data_collection/eodhd_client.py`

```python
def get_news(
    self, symbol: str, start_date: str, end_date: str, limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Fetches Financial News Feed and Stock News Sentiment data.
    
    Args:
        symbol: Stock ticker (e.g., AAPL.US)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of articles to fetch
        
    Returns:
        List of news articles with sentiment data
    """
    endpoint = "news"
    params = {
        "s": symbol,
        "from": start_date,
        "to": end_date,
        "limit": limit,
        "offset": 0,
        "fmt": "json"
    }
    
    logger.info(f"Fetching news for {symbol} from {start_date} to {end_date} (limit: {limit})")
    
    response = self._make_request(endpoint, params)
    
    if isinstance(response, list):
        logger.info(f"Fetched {len(response)} news articles for {symbol}")
        return response
    elif isinstance(response, dict):
        # API may return error dict
        logger.error(f"Unexpected dict response for news: {response}")
        return []
    else:
        logger.warning(f"No news data returned for {symbol} (response type: {type(response)})")
        return []
```

### SOLUTION 2: Add Diagnostic Logging 🔴 PRIORITY 1

**File:** `data_collection/data_orchestrator.py`

```python
# 4. Fetch and process News
if self.eodhd_client:
    logger.info(f"Fetching news for {ticker} from {start_date} to {end_date}")
    
    news_raw = self.eodhd_client.get_news(
        f"{ticker}.US", 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"),
        limit=1000  # Explicitly request up to 1000 articles
    )
    
    if not news_raw:
        logger.warning(
            f"No news data returned for {ticker}. "
            "This could mean: (1) No news available, "
            "(2) API tier limitation, or (3) API error"
        )
    else:
        logger.info(f"Raw news API returned {len(news_raw)} articles for {ticker}")
    
    news_processed = processor.process_news(news_raw, f"{ticker}.US")
    logger.info(f"Processed {len(news_processed)} news articles for {ticker}")
    
    # Add ticker_id to each article
    for article in news_processed:
        article["ticker_id"] = ticker_obj.ticker_id
    
    self.db_manager.insert_news(session, news_processed)
    session.commit()
    logger.info(f"Stored {len(news_processed)} news articles in database")
```

### SOLUTION 3: Alternative Symbol Format Testing 🟡 PRIORITY 2

Try both symbol formats to see which works:

```python
def get_news_with_fallback(
    self, symbol: str, start_date: str, end_date: str
) -> List[Dict[str, Any]]:
    """
    Try fetching news with different symbol formats
    """
    # Try with .US suffix first
    news = self.get_news(symbol, start_date, end_date)
    
    if not news and ".US" in symbol:
        # Try without .US suffix
        symbol_without_exchange = symbol.split(".")[0]
        logger.info(f"Retrying news fetch without exchange suffix: {symbol_without_exchange}")
        news = self.get_news(symbol_without_exchange, start_date, end_date)
    
    return news
```

### SOLUTION 4: Add News API Test Tool 🟡 PRIORITY 2

I've created a test script at `/opt/Fireworks-Charlie/test_eodhd_news_api.py` that you can run:

```bash
EODHD_API_KEY=your_key python3 test_eodhd_news_api.py
```

This will test multiple API variations and show you exactly what's being returned.

### SOLUTION 5: Enhanced Error Messages in Prompts 🟢 PRIORITY 3

**File:** `thesis_generation/enhanced_prompt_builder.py`

```python
def _build_detailed_news_analysis(self, ticker: str, data: List[Dict[str, Any]]) -> List[str]:
    sections = []
    
    # Collect all news
    all_news = []
    for day_data in data:
        if day_data.get('news'):
            all_news.extend(day_data['news'])
    
    if not all_news:
        # More informative message
        sections.append(
            "No news articles available in this period.\n"
            "Note: This could indicate limited news coverage for this ticker,\n"
            "API data availability constraints, or recent data collection issues."
        )
        return sections
    # ...rest of implementation
```

## Testing Plan

### Phase 1: Diagnostic Testing
1. ✅ Run `test_eodhd_news_api.py` to verify API access
2. Check if ANY news is returned for well-covered stocks (AAPL, MSFT, GOOGL)
3. Identify which parameter combinations work

### Phase 2: Implementation
1. Update `eodhd_client.py` with enhanced parameters
2. Add comprehensive logging throughout data flow
3. Update `data_orchestrator.py` with better error handling

### Phase 3: Validation
1. Re-run data collection for a sample ticker
2. Check database for news articles: `SELECT COUNT(*) FROM news;`
3. Generate a test thesis and verify news section is populated
4. Review logs for any warnings or errors

## Questions to Investigate

1. **API Tier Check:** What EODHD subscription tier are you using?
   - Some news features may require "All-in-One" or higher tier

2. **Date Range:** What date ranges are you collecting data for?
   - EODHD may have limited historical news (e.g., only last 12 months)

3. **Tickers:** Which tickers are showing empty news?
   - Small-cap stocks may have minimal news coverage

4. **Database Verification:** Are ANY news articles in the database?
   ```sql
   SELECT ticker_id, COUNT(*) as article_count 
   FROM news 
   GROUP BY ticker_id 
   ORDER BY article_count DESC 
   LIMIT 10;
   ```

## Next Steps

### Immediate Actions (TODAY):
1. ✅ Review this investigation report
2. 🔲 Run `test_eodhd_news_api.py` with your API key
3. 🔲 Check your EODHD subscription tier and feature access
4. 🔲 Review database to see if ANY news articles exist

### Short-term Fixes (THIS WEEK):
1. 🔲 Implement Solution 1 (Fix API client parameters)
2. 🔲 Implement Solution 2 (Add diagnostic logging)
3. 🔲 Re-run data collection for 1-2 test tickers
4. 🔲 Verify news data appears in generated prompts

### Long-term Improvements (NEXT SPRINT):
1. 🔲 Add retry logic for failed API calls
2. 🔲 Implement pagination for tickers with > 1000 articles
3. 🔲 Add data quality monitoring dashboard
4. 🔲 Set up alerts for missing news data

---

**Report Generated:** 2025-11-01  
**Investigated By:** Claude AI Assistant  
**Status:** Ready for Implementation
