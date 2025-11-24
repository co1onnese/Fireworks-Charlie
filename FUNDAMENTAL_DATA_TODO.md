# Fundamental Data Improvement - Detailed TODO List

## High Priority (Week 1)

### 1. Fix Point-in-Time Data Retrieval
**File**: `data_collection/data_orchestrator.py`
**Lines**: 605-631

**Current Code**:
```python
# Get latest fundamentals - use strict point-in-time (filing_date < as_of_date)
fundamentals = session.query(Fundamental).filter(
    Fundamental.ticker_id == ticker_obj.ticker_id,
    Fundamental.filing_date < as_of_date
).order_by(Fundamental.filing_date.desc()).first()
```

**Required Change**:
```python
# Get latest fundamentals - use inclusive point-in-time (filing_date <= as_of_date)
fundamentals = session.query(Fundamental).filter(
    Fundamental.ticker_id == ticker_obj.ticker_id,
    Fundamental.filing_date <= as_of_date
).order_by(Fundamental.filing_date.desc()).first()
```

**Testing**:
- [ ] Verify same-day filings are now included
- [ ] Test with various date scenarios
- [ ] Ensure no data leakage (future data)

### 2. Create Fundamental Data Backfill Script
**New File**: `scripts/backfill_fundamentals.py`

**Required Implementation**:
```python
#!/usr/bin/env python3
"""
Fundamental Data Backfill Script
Populates missing fundamental data for all active tickers
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from data_collection.database_manager import DatabaseManager
from data_collection.eodhd_client import EODHDClient
from data_collection.data_processor import DataProcessor
from orchestration.config_manager import ConfigManager

class FundamentalDataBackfill:
    def __init__(self, config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)
        self.eodhd_client = EODHDClient(config.EODHD_API_KEY)

    def get_active_tickers(self) -> List[str]:
        """Get list of active tickers from database"""
        session = self.db_manager.get_session()
        try:
            tickers = session.query(Ticker).filter(Ticker.is_active == True).all()
            return [t.symbol for t in tickers]
        finally:
            session.close()

    def get_missing_fundamentals_tickers(self) -> List[str]:
        """Identify tickers with missing recent fundamental data"""
        # Implementation needed
        pass

    def backfill_ticker(self, ticker: str, quarters: int = 4):
        """Backfill fundamental data for a specific ticker"""
        # Implementation needed
        pass

    def backfill_all_tickers(self):
        """Backfill fundamental data for all active tickers"""
        # Implementation needed
        pass

if __name__ == "__main__":
    config = ConfigManager()
    backfill = FundamentalDataBackfill(config)
    backfill.backfill_all_tickers()
```

**Features to Implement**:
- [ ] Get list of active tickers from database
- [ ] Identify tickers missing recent fundamental data
- [ ] Fetch fundamental data from EODHD API
- [ ] Process and insert into database
- [ ] Skip existing records to avoid duplicates
- [ ] Progress tracking and logging
- [ ] Error handling and retry logic

### 3. Add Data Freshness Monitoring
**File**: `data_collection/data_orchestrator.py`

**Required Changes**:
```python
def get_data_for_date(self, ticker: str, as_of_date: date) -> Dict[str, Any]:
    # ... existing code ...

    # Add data freshness check
    self._check_fundamental_data_freshness(ticker, as_of_date, fundamentals)

    return data

def _check_fundamental_data_freshness(self, ticker: str, as_of_date: date, fundamentals):
    """Check if fundamental data is stale and log warning"""
    if fundamentals:
        days_stale = (as_of_date - fundamentals.filing_date).days
        if days_stale > 90:
            logger.warning(
                f"Fundamental data for {ticker} is {days_stale} days stale "
                f"(latest filing: {fundamentals.filing_date})"
            )
    else:
        logger.warning(f"No fundamental data available for {ticker} on {as_of_date}")
```

**Testing**:
- [ ] Verify warnings are logged for stale data
- [ ] Test with various staleness scenarios
- [ ] Ensure no false positives

## Medium Priority (Week 2)

### 4. Improve EODHD API Integration
**File**: `data_collection/eodhd_client.py`

**Required Changes**:
```python
def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
    """Fetches Fundamental Data for Stocks, ETFs, Mutual Funds, Indices."""
    endpoint = f"fundamentals/{symbol}"
    # Add specific filters for quarterly data
    params = {
        "filter": "Financials::Balance_Sheet::quarterly,Financials::Income_Statement::quarterly,Financials::Cash_Flow::quarterly"
    }
    response = self._make_request(endpoint, params)
    if isinstance(response, dict):
        return response
    logger.error("Expected dict response for fundamentals, received list.")
    return {}
```

**Testing**:
- [ ] Verify API calls include quarterly filters
- [ ] Test response structure
- [ ] Ensure backward compatibility

### 5. Add Fundamental Data Validation
**File**: `data_collection/data_processor.py`

**Required Changes**:
```python
def process_fundamentals(self, raw_data: dict, symbol: str) -> list:
    # ... existing processing code ...

    # Add validation before returning records
    validated_records = []
    for record in processed_records:
        if self._validate_fundamental_record(record):
            validated_records.append(record)
        else:
            logger.warning(f"Skipping invalid fundamental record for {symbol}: {record}")

    return validated_records

def _validate_fundamental_record(self, record: Dict[str, Any]) -> bool:
    """Validate that fundamental record has required fields"""
    required_fields = ['market_cap', 'revenue', 'net_income', 'eps']

    for field in required_fields:
        if record.get(field) is None:
            return False

    return True
```

**Testing**:
- [ ] Test validation with complete/incomplete records
- [ ] Verify invalid records are skipped
- [ ] Ensure required fields are correctly identified

### 6. Implement Scheduled Updates
**New File**: `scripts/update_fundamentals.py`

**Required Implementation**:
```python
#!/usr/bin/env python3
"""
Scheduled Fundamental Data Update Script
Runs monthly to update fundamental data for all active tickers
"""

import logging
from datetime import datetime, timedelta
from data_collection.database_manager import DatabaseManager
from data_collection.eodhd_client import EODHDClient
from data_collection.data_processor import DataProcessor
from orchestration.config_manager import ConfigManager

class FundamentalDataUpdater:
    def __init__(self, config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)
        self.eodhd_client = EODHDClient(config.EODHD_API_KEY)

    def get_tickers_needing_update(self) -> List[str]:
        """Get tickers with fundamental data older than 30 days"""
        # Implementation needed
        pass

    def update_ticker_fundamentals(self, ticker: str):
        """Update fundamental data for a specific ticker"""
        # Implementation needed
        pass

    def update_all_tickers(self):
        """Update fundamental data for all tickers needing updates"""
        # Implementation needed
        pass

if __name__ == "__main__":
    config = ConfigManager()
    updater = FundamentalDataUpdater(config)
    updater.update_all_tickers()
```

**Features to Implement**:
- [ ] Identify tickers with stale fundamental data
- [ ] Fetch and process updated fundamental data
- [ ] Update database with new filings
- [ ] Log update statistics
- [ ] Error handling and retry logic

## Low Priority (Week 3)

### 7. Create Data Quality Dashboard
**New File**: `scripts/data_quality_report.py`

**Required Implementation**:
```python
#!/usr/bin/env python3
"""
Data Quality Dashboard Script
Generates comprehensive reports on fundamental data quality
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from data_collection.database_manager import DatabaseManager
from orchestration.config_manager import ConfigManager

class DataQualityReporter:
    def __init__(self, config):
        self.config = config
        self.db_manager = DatabaseManager(config.DB_URL)

    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate coverage report by ticker and date range"""
        # Implementation needed
        pass

    def generate_freshness_report(self) -> Dict[str, Any]:
        """Generate data freshness report"""
        # Implementation needed
        pass

    def generate_completeness_report(self) -> Dict[str, Any]:
        """Generate data completeness report"""
        # Implementation needed
        pass

    def generate_missing_data_report(self) -> Dict[str, Any]:
        """Generate report of missing fundamental data"""
        # Implementation needed
        pass

if __name__ == "__main__":
    config = ConfigManager()
    reporter = DataQualityReporter(config)

    coverage = reporter.generate_coverage_report()
    freshness = reporter.generate_freshness_report()
    completeness = reporter.generate_completeness_report()
    missing = reporter.generate_missing_data_report()

    # Print or save reports
```

### 8. Implement Fallback Data Sources
**Files**: Multiple - requires architectural changes

**Required Changes**:
- Add FMP client integration
- Add Yahoo Finance fallback
- Implement provider priority chain
- Add configuration for fallback providers

## Testing Checklist

### Unit Tests
- [ ] Point-in-time filtering logic
- [ ] Data validation functions
- [ ] API client methods
- [ ] Data processing logic

### Integration Tests
- [ ] Complete backfill workflow
- [ ] Data freshness monitoring
- [ ] Scheduled updates
- [ ] Fallback data sources

### End-to-End Tests
- [ ] Complete data collection pipeline
- [ ] Thesis generation with fundamental data
- [ ] Data quality reporting

## Deployment Checklist

### Pre-deployment
- [ ] Backup current database
- [ ] Test in staging environment
- [ ] Validate API quota limits
- [ ] Review logging and monitoring

### Deployment
- [ ] Deploy code changes in order of priority
- [ ] Run backfill script
- [ ] Verify data quality
- [ ] Monitor system performance

### Post-deployment
- [ ] Monitor for data gaps
- [ ] Review logs for warnings/errors
- [ ] Validate thesis generation quality
- [ ] Update documentation

## Monitoring and Maintenance

### Daily Checks
- [ ] Data freshness warnings
- [ ] API quota usage
- [ ] Error logs

### Weekly Tasks
- [ ] Run data quality reports
- [ ] Review coverage metrics
- [ ] Check for missing data

### Monthly Tasks
- [ ] Run scheduled updates
- [ ] Review and update configuration
- [ ] Performance optimization

---

*Last Updated: 2025-11-24*
*Status: Ready for Implementation*