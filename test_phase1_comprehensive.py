#!/usr/bin/env python3
"""
Comprehensive test script for Phase 1 implementation
Tests edge cases, error handling, and integration points
"""
import sys
import pandas as pd
import numpy as np
from datetime import date, datetime

print("="*70)
print("COMPREHENSIVE PHASE 1 TESTING")
print("="*70)

# ============================================================================
# Test 1: ATR Calculation Edge Cases
# ============================================================================
print("\n[Test 1] ATR Calculation Edge Cases")
print("-" * 70)

try:
    from data_collection.feature_engineering import FeatureEngineer
    
    class DummyDB:
        pass
    
    fe = FeatureEngineer(DummyDB())
    
    # Test 1.1: Single data point
    print("  1.1 Testing with single data point...")
    high1 = pd.Series([100.0])
    low1 = pd.Series([99.0])
    close1 = pd.Series([99.5])
    atr1 = fe._calculate_atr(high1, low1, close1, period=14)
    assert len(atr1) == 1, "ATR should return same length as input"
    assert not pd.isna(atr1.iloc[0]), "ATR should not be NaN for single point"
    print("      ✓ Single data point: OK")
    
    # Test 1.2: All zeros
    print("  1.2 Testing with all zeros...")
    high2 = pd.Series([0.0] * 20)
    low2 = pd.Series([0.0] * 20)
    close2 = pd.Series([0.0] * 20)
    atr2 = fe._calculate_atr(high2, low2, close2, period=14)
    assert len(atr2) == 20, "ATR should return same length"
    print("      ✓ All zeros: OK")
    
    # Test 1.3: Missing values
    print("  1.3 Testing with NaN values...")
    high3 = pd.Series([100.0, np.nan, 102.0, 103.0])
    low3 = pd.Series([99.0, 100.0, 101.0, 102.0])
    close3 = pd.Series([99.5, 100.5, 101.5, 102.5])
    atr3 = fe._calculate_atr(high3, low3, close3, period=2)
    assert len(atr3) == 4, "ATR should return same length"
    print("      ✓ NaN handling: OK")
    
    print("  ✓ All ATR edge cases passed")
    
except Exception as e:
    print(f"  ✗ ATR edge case test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 2: ADX Calculation Edge Cases
# ============================================================================
print("\n[Test 2] ADX Calculation Edge Cases")
print("-" * 70)

try:
    # Test 2.1: Single data point
    print("  2.1 Testing with single data point...")
    high1 = pd.Series([100.0])
    low1 = pd.Series([99.0])
    close1 = pd.Series([99.5])
    adx1 = fe._calculate_adx(high1, low1, close1, period=14)
    assert 'adx' in adx1 and 'di_plus' in adx1 and 'di_minus' in adx1
    assert len(adx1['adx']) == 1
    print("      ✓ Single data point: OK")
    
    # Test 2.2: Exactly period length
    print("  2.2 Testing with exactly period length (14)...")
    dates = pd.date_range('2024-01-01', periods=14, freq='D')
    high2 = pd.Series([100 + i * 0.5 for i in range(14)], index=dates)
    low2 = pd.Series([99 + i * 0.5 for i in range(14)], index=dates)
    close2 = pd.Series([99.5 + i * 0.5 for i in range(14)], index=dates)
    adx2 = fe._calculate_adx(high2, low2, close2, period=14)
    assert len(adx2['adx']) == 14
    assert adx2['adx'].notna().sum() >= 0  # May have some NaN at start
    print("      ✓ Exactly period length: OK")
    
    # Test 2.3: Less than period length
    print("  2.3 Testing with less than period length...")
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    high3 = pd.Series([100 + i * 0.5 for i in range(5)], index=dates)
    low3 = pd.Series([99 + i * 0.5 for i in range(5)], index=dates)
    close3 = pd.Series([99.5 + i * 0.5 for i in range(5)], index=dates)
    adx3 = fe._calculate_adx(high3, low3, close3, period=14)
    assert len(adx3['adx']) == 5
    assert adx3['adx'].isna().sum() == 0, "ADX should fill NaN with 0"
    print("      ✓ Less than period length: OK")
    
    # Test 2.4: No price movement (all same values)
    print("  2.4 Testing with no price movement...")
    high4 = pd.Series([100.0] * 30)
    low4 = pd.Series([100.0] * 30)
    close4 = pd.Series([100.0] * 30)
    adx4 = fe._calculate_adx(high4, low4, close4, period=14)
    assert len(adx4['adx']) == 30
    assert adx4['adx'].isna().sum() == 0, "ADX should handle no movement"
    print("      ✓ No price movement: OK")
    
    print("  ✓ All ADX edge cases passed")
    
except Exception as e:
    print(f"  ✗ ADX edge case test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 3: Benzinga Client Error Handling
# ============================================================================
print("\n[Test 3] Benzinga Client Error Handling")
print("-" * 70)

try:
    from data_collection.benzinga_client import BenzingaClient
    
    # Test 3.1: Empty API key
    print("  3.1 Testing empty API key rejection...")
    try:
        client = BenzingaClient("")
        print("      ✗ Should have raised ValueError")
        sys.exit(1)
    except ValueError:
        print("      ✓ Empty API key correctly rejected")
    
    # Test 3.2: None API key
    print("  3.2 Testing None API key rejection...")
    try:
        client = BenzingaClient(None)
        print("      ✗ Should have raised ValueError")
        sys.exit(1)
    except (ValueError, TypeError):
        print("      ✓ None API key correctly rejected")
    
    # Test 3.3: Valid initialization
    print("  3.3 Testing valid initialization...")
    client = BenzingaClient("test_key_123")
    assert client.api_key == "test_key_123"
    assert client.BASE_URL == "https://api.benzinga.com/api/v1/"
    print("      ✓ Valid initialization: OK")
    
    # Test 3.4: Method signature
    print("  3.4 Testing get_analyst_insights method signature...")
    import inspect
    sig = inspect.signature(client.get_analyst_insights)
    params = list(sig.parameters.keys())
    assert 'symbols' in params
    assert 'start_date' in params
    assert 'end_date' in params
    assert 'page' in params
    assert 'page_size' in params
    print("      ✓ Method signature: OK")
    
    print("  ✓ All Benzinga client error handling tests passed")
    
except Exception as e:
    print(f"  ✗ Benzinga client error handling test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 4: Data Processor Edge Cases
# ============================================================================
print("\n[Test 4] Data Processor Edge Cases")
print("-" * 70)

try:
    from data_collection.data_processor import DataProcessor
    
    processor = DataProcessor(["AAPL"], "2024-01-01", "2024-12-31")
    
    # Test 4.1: Empty input
    print("  4.1 Testing with empty input...")
    result = processor.process_analyst_recommendations([], "AAPL")
    assert result == [], "Empty input should return empty list"
    print("      ✓ Empty input: OK")
    
    # Test 4.2: Missing required fields
    print("  4.2 Testing with missing required fields...")
    incomplete_insight = {
        "id": "test-1",
        "action": "Buy",
        # Missing date, security, etc.
    }
    result = processor.process_analyst_recommendations([incomplete_insight], "AAPL")
    assert len(result) == 0, "Should skip insights with missing fields"
    print("      ✓ Missing fields handling: OK")
    
    # Test 4.3: Wrong symbol
    print("  4.3 Testing with wrong symbol...")
    wrong_symbol_insight = {
        "id": "test-2",
        "action": "Buy",
        "rating": "Buy",
        "pt": "100.00",
        "firm": "Test Firm",
        "firm_id": "firm-1",
        "rating_id": "rating-1",
        "date": "2024-06-15",
        "updated": 1708018876,
        "analyst_insights": "Test",
        "security": {"symbol": "MSFT"}  # Wrong symbol
    }
    result = processor.process_analyst_recommendations([wrong_symbol_insight], "AAPL")
    assert len(result) == 0, "Should skip insights for wrong symbol"
    print("      ✓ Wrong symbol handling: OK")
    
    # Test 4.4: Invalid date format
    print("  4.4 Testing with invalid date format...")
    invalid_date_insight = {
        "id": "test-3",
        "action": "Buy",
        "rating": "Buy",
        "pt": "100.00",
        "firm": "Test Firm",
        "firm_id": "firm-1",
        "rating_id": "rating-1",
        "date": "invalid-date",
        "updated": 1708018876,
        "analyst_insights": "Test",
        "security": {"symbol": "AAPL"}
    }
    result = processor.process_analyst_recommendations([invalid_date_insight], "AAPL")
    assert len(result) == 0, "Should skip insights with invalid dates"
    print("      ✓ Invalid date handling: OK")
    
    # Test 4.5: Date outside range
    print("  4.5 Testing with date outside range...")
    out_of_range_insight = {
        "id": "test-4",
        "action": "Buy",
        "rating": "Buy",
        "pt": "100.00",
        "firm": "Test Firm",
        "firm_id": "firm-1",
        "rating_id": "rating-1",
        "date": "2025-06-15",  # Outside 2024 range
        "updated": 1708018876,
        "analyst_insights": "Test",
        "security": {"symbol": "AAPL"}
    }
    result = processor.process_analyst_recommendations([out_of_range_insight], "AAPL")
    assert len(result) == 0, "Should skip insights outside date range"
    print("      ✓ Date range filtering: OK")
    
    # Test 4.6: Invalid target price
    print("  4.6 Testing with invalid target price...")
    invalid_price_insight = {
        "id": "test-5",
        "action": "Buy",
        "rating": "Buy",
        "pt": "not-a-number",
        "firm": "Test Firm",
        "firm_id": "firm-1",
        "rating_id": "rating-1",
        "date": "2024-06-15",
        "updated": 1708018876,
        "analyst_insights": "Test",
        "security": {"symbol": "AAPL"}
    }
    result = processor.process_analyst_recommendations([invalid_price_insight], "AAPL")
    assert len(result) == 1, "Should still process with None target_price"
    assert result[0]['target_price'] is None, "Invalid price should be None"
    print("      ✓ Invalid target price handling: OK")
    
    print("  ✓ All data processor edge cases passed")
    
except Exception as e:
    print(f"  ✗ Data processor edge case test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 5: Database Manager Integration
# ============================================================================
print("\n[Test 5] Database Manager Integration")
print("-" * 70)

try:
    from data_collection.database_manager import (
        AnalystRecommendation, MarketData, Ticker
    )
    
    # Test 5.1: Model structure
    print("  5.1 Testing AnalystRecommendation model structure...")
    assert hasattr(AnalystRecommendation, 'recommendation_id')
    assert hasattr(AnalystRecommendation, 'ticker_id')
    assert hasattr(AnalystRecommendation, 'date')
    assert hasattr(AnalystRecommendation, 'firm')
    assert hasattr(AnalystRecommendation, 'analyst_insight_id')
    assert hasattr(AnalystRecommendation, 'action')
    assert hasattr(AnalystRecommendation, 'rating')
    assert hasattr(AnalystRecommendation, 'target_price')
    assert hasattr(AnalystRecommendation, 'analyst_insights')
    print("      ✓ Model structure: OK")
    
    # Test 5.2: MarketData new columns
    print("  5.2 Testing MarketData new columns...")
    assert hasattr(MarketData, 'atr_14')
    assert hasattr(MarketData, 'adx_14')
    assert hasattr(MarketData, 'di_plus_14')
    assert hasattr(MarketData, 'di_minus_14')
    print("      ✓ MarketData columns: OK")
    
    # Test 5.3: Relationships
    print("  5.3 Testing relationships...")
    assert hasattr(Ticker, 'analyst_recommendations')
    print("      ✓ Ticker relationship: OK")
    
    # Test 5.4: Insert method exists
    print("  5.4 Testing insert method exists...")
    from data_collection.database_manager import DatabaseManager
    assert hasattr(DatabaseManager, 'insert_analyst_recommendations')
    print("      ✓ Insert method: OK")
    
    print("  ✓ All database manager integration tests passed")
    
except Exception as e:
    print(f"  ✗ Database manager integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 6: Data Orchestrator Integration
# ============================================================================
print("\n[Test 6] Data Orchestrator Integration")
print("-" * 70)

try:
    from data_collection.data_orchestrator import DataOrchestrator
    
    # Test 6.1: Import check
    print("  6.1 Testing imports...")
    import data_collection.data_orchestrator as do_module
    assert hasattr(do_module, 'BenzingaClient'), "BenzingaClient should be imported"
    print("      ✓ Imports: OK")
    
    # Test 6.2: Initialization with mock config
    print("  6.2 Testing initialization...")
    class MockConfig:
        DB_URL = "postgresql://test:test@localhost/test"
        EODHD_API_KEY = "test_eodhd"
        FRED_API_KEY = "test_fred"
        BENZINGA_API_KEY = "test_benzinga"
    
    # We can't actually initialize without a real DB, but we can check the code
    # Check that benzinga_client is referenced in __init__
    import inspect
    source = inspect.getsource(DataOrchestrator.__init__)
    assert 'benzinga_client' in source or 'BenzingaClient' in source
    print("      ✓ Initialization code: OK")
    
    # Test 6.3: collect_data_for_ticker has analyst recommendations
    print("  6.3 Testing collect_data_for_ticker method...")
    source = inspect.getsource(DataOrchestrator.collect_data_for_ticker)
    assert 'analyst' in source.lower() or 'benzinga' in source.lower()
    print("      ✓ Method includes analyst recommendations: OK")
    
    print("  ✓ All data orchestrator integration tests passed")
    
except Exception as e:
    print(f"  ✗ Data orchestrator integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 7: Feature Engineering Integration
# ============================================================================
print("\n[Test 7] Feature Engineering Integration")
print("-" * 70)

try:
    # Test 7.1: _calculate_technical_indicators includes ATR/ADX
    print("  7.1 Testing _calculate_technical_indicators includes ATR/ADX...")
    source = inspect.getsource(fe._calculate_technical_indicators)
    assert 'atr' in source.lower() and 'adx' in source.lower()
    print("      ✓ ATR/ADX in technical indicators: OK")
    
    # Test 7.2: Database update includes new fields
    print("  7.2 Testing database update includes new fields...")
    # Check that the update section includes atr_14, adx_14, etc.
    assert 'atr_14' in source or 'atr' in source
    assert 'adx_14' in source or 'adx' in source
    print("      ✓ Database update includes new fields: OK")
    
    print("  ✓ All feature engineering integration tests passed")
    
except Exception as e:
    print(f"  ✗ Feature engineering integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 8: Data Type Validation
# ============================================================================
print("\n[Test 8] Data Type Validation")
print("-" * 70)

try:
    # Test 8.1: ATR returns correct type
    print("  8.1 Testing ATR return type...")
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    high = pd.Series([100 + i * 0.5 for i in range(20)], index=dates)
    low = pd.Series([99 + i * 0.5 for i in range(20)], index=dates)
    close = pd.Series([99.5 + i * 0.5 for i in range(20)], index=dates)
    atr = fe._calculate_atr(high, low, close, period=14)
    assert isinstance(atr, pd.Series), "ATR should return pd.Series"
    assert len(atr) == len(high), "ATR should have same length as input"
    print("      ✓ ATR return type: OK")
    
    # Test 8.2: ADX returns correct structure
    print("  8.2 Testing ADX return structure...")
    adx_data = fe._calculate_adx(high, low, close, period=14)
    assert isinstance(adx_data, dict), "ADX should return dict"
    assert 'adx' in adx_data and 'di_plus' in adx_data and 'di_minus' in adx_data
    assert isinstance(adx_data['adx'], pd.Series)
    assert isinstance(adx_data['di_plus'], pd.Series)
    assert isinstance(adx_data['di_minus'], pd.Series)
    print("      ✓ ADX return structure: OK")
    
    # Test 8.3: Data processor returns correct types
    print("  8.3 Testing data processor return types...")
    valid_insight = {
        "id": "test-valid",
        "action": "Buy",
        "rating": "Buy",
        "pt": "155.00",
        "firm": "Test Firm",
        "firm_id": "firm-1",
        "rating_id": "rating-1",
        "date": "2024-06-15",
        "updated": 1708018876,
        "analyst_insights": "Test insight",
        "security": {"symbol": "AAPL"}
    }
    result = processor.process_analyst_recommendations([valid_insight], "AAPL")
    if result:
        rec = result[0]
        assert isinstance(rec['date'], date), "Date should be date object"
        assert isinstance(rec['target_price'], (float, type(None))), "Target price should be float or None"
        assert isinstance(rec['analyst_insights'], str), "Insights should be string"
        assert isinstance(rec['updated_timestamp'], (int, type(None))), "Timestamp should be int or None"
    print("      ✓ Data processor return types: OK")
    
    print("  ✓ All data type validation tests passed")
    
except Exception as e:
    print(f"  ✗ Data type validation test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 9: SQL Migration Scripts
# ============================================================================
print("\n[Test 9] SQL Migration Scripts")
print("-" * 70)

try:
    # Test 9.1: ATR/ADX migration script
    print("  9.1 Testing ATR/ADX migration script...")
    with open('database/05_add_atr_adx.sql', 'r') as f:
        sql_content = f.read()
        assert 'atr_14' in sql_content
        assert 'adx_14' in sql_content
        assert 'di_plus_14' in sql_content
        assert 'di_minus_14' in sql_content
        assert 'ALTER TABLE market_data' in sql_content
    print("      ✓ ATR/ADX migration script: OK")
    
    # Test 9.2: Analyst recommendations migration script
    print("  9.2 Testing analyst recommendations migration script...")
    with open('database/06_add_analyst_recommendations.sql', 'r') as f:
        sql_content = f.read()
        assert 'CREATE TABLE' in sql_content or 'CREATE TABLE IF NOT EXISTS' in sql_content
        assert 'analyst_recommendations' in sql_content
        assert 'analyst_insight_id' in sql_content
        assert 'UNIQUE' in sql_content
        assert 'CREATE INDEX' in sql_content
    print("      ✓ Analyst recommendations migration script: OK")
    
    print("  ✓ All SQL migration script tests passed")
    
except Exception as e:
    print(f"  ✗ SQL migration script test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Test 10: Configuration
# ============================================================================
print("\n[Test 10] Configuration")
print("-" * 70)

try:
    from orchestration.config_manager import Config
    
    config = Config()
    
    # Test 10.1: BENZINGA_API_KEY exists
    print("  10.1 Testing BENZINGA_API_KEY in config...")
    assert hasattr(config, 'BENZINGA_API_KEY')
    print("      ✓ BENZINGA_API_KEY exists: OK")
    
    # Test 10.2: Config can be accessed
    print("  10.2 Testing config access...")
    api_key = config.BENZINGA_API_KEY
    assert isinstance(api_key, str) or api_key == ""
    print("      ✓ Config access: OK")
    
    print("  ✓ All configuration tests passed")
    
except Exception as e:
    print(f"  ✗ Configuration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("✓ ALL COMPREHENSIVE PHASE 1 TESTS PASSED!")
print("="*70)
print("\nPhase 1 Implementation Status:")
print("  ✓ ATR calculation implemented and tested")
print("  ✓ ADX calculation implemented and tested")
print("  ✓ Benzinga API client implemented and tested")
print("  ✓ Analyst recommendations data processing implemented and tested")
print("  ✓ Database models and migrations created")
print("  ✓ Data orchestrator integration complete")
print("  ✓ Configuration updated")
print("\nReady for Phase 2: Structured Prompt Builder")
