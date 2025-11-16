#!/usr/bin/env python3
"""
Test script for Phase 1 implementation:
- ATR and ADX calculations
- Benzinga client
- Data processor for analyst recommendations
- Database manager integration
"""
import sys
import pandas as pd
import numpy as np
from datetime import date, datetime

# Test ATR calculation
print("Testing ATR calculation...")
try:
    from data_collection.feature_engineering import FeatureEngineer
    from data_collection.database_manager import DatabaseManager
    
    # Create dummy data
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    high = pd.Series([100 + i * 0.5 + np.random.randn() for i in range(30)], index=dates)
    low = pd.Series([99 + i * 0.5 + np.random.randn() for i in range(30)], index=dates)
    close = pd.Series([99.5 + i * 0.5 + np.random.randn() for i in range(30)], index=dates)
    
    # Create a dummy FeatureEngineer (we need db_manager but won't use it for this test)
    class DummyDB:
        pass
    
    fe = FeatureEngineer(DummyDB())
    
    # Test ATR
    atr = fe._calculate_atr(high, low, close, period=14)
    print(f"✓ ATR calculation: OK (length={len(atr)}, first_valid={atr.notna().sum()})")
    
    # Test ADX
    adx_data = fe._calculate_adx(high, low, close, period=14)
    print(f"✓ ADX calculation: OK")
    print(f"  - ADX length: {len(adx_data['adx'])}")
    print(f"  - DI+ length: {len(adx_data['di_plus'])}")
    print(f"  - DI- length: {len(adx_data['di_minus'])}")
    print(f"  - ADX has valid values: {adx_data['adx'].notna().sum() > 0}")
    
except Exception as e:
    print(f"✗ ATR/ADX calculation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test Benzinga client structure
print("\nTesting Benzinga client...")
try:
    from data_collection.benzinga_client import BenzingaClient
    
    # Test initialization (without API key - should raise ValueError)
    try:
        client = BenzingaClient("")
        print("✗ BenzingaClient should reject empty API key")
        sys.exit(1)
    except ValueError:
        print("✓ BenzingaClient correctly rejects empty API key")
    
    # Test with dummy key
    client = BenzingaClient("test_key")
    print("✓ BenzingaClient initialization: OK")
    print(f"  - Base URL: {client.BASE_URL}")
    print(f"  - Request interval: {client.REQUEST_INTERVAL}s")
    
except Exception as e:
    print(f"✗ Benzinga client error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test data processor
print("\nTesting data processor for analyst recommendations...")
try:
    from data_collection.data_processor import DataProcessor
    
    # Sample Benzinga API response
    sample_insights = [
        {
            "id": "test-uuid-1",
            "action": "Upgrades",
            "rating": "Buy",
            "pt": "155.00",
            "analyst_insights": "Test insight text",
            "firm": "Test Firm",
            "firm_id": "firm-123",
            "rating_id": "rating-456",
            "date": "2024-02-15",
            "updated": 1708018876,
            "security": {"symbol": "AAPL"}
        },
        {
            "id": "test-uuid-2",
            "action": "Reiterates",
            "rating": "Hold",
            "pt": "140.00",
            "analyst_insights": "Another test insight",
            "firm": "Another Firm",
            "firm_id": "firm-789",
            "rating_id": "rating-012",
            "date": "2024-02-14",
            "updated": 1707932476,
            "security": {"symbol": "AAPL"}
        }
    ]
    
    processor = DataProcessor(
        ["AAPL"],
        "2024-02-01",
        "2024-02-28"
    )
    
    processed = processor.process_analyst_recommendations(sample_insights, "AAPL")
    print(f"✓ Processed {len(processed)} analyst recommendations")
    
    if processed:
        rec = processed[0]
        print(f"  - First record keys: {list(rec.keys())}")
        print(f"  - Has analyst_insight_id: {'analyst_insight_id' in rec}")
        print(f"  - Has action: {'action' in rec}")
        print(f"  - Has rating: {'rating' in rec}")
        print(f"  - Target price type: {type(rec.get('target_price'))}")
        print(f"  - Date type: {type(rec.get('date'))}")
        
        # Verify required fields
        required_fields = ['symbol', 'date', 'firm', 'analyst_insight_id', 'action', 'rating']
        missing = [f for f in required_fields if f not in rec]
        if missing:
            print(f"✗ Missing required fields: {missing}")
            sys.exit(1)
        else:
            print("✓ All required fields present")
    
except Exception as e:
    print(f"✗ Data processor error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test database manager model
print("\nTesting database manager models...")
try:
    from data_collection.database_manager import AnalystRecommendation, MarketData
    
    # Check that AnalystRecommendation model exists
    print(f"✓ AnalystRecommendation model: {AnalystRecommendation.__name__}")
    print(f"  - Table name: {AnalystRecommendation.__tablename__}")
    
    # Check MarketData has new columns
    market_data_columns = [col.name for col in MarketData.__table__.columns]
    required_columns = ['atr_14', 'adx_14', 'di_plus_14', 'di_minus_14']
    missing_columns = [col for col in required_columns if col not in market_data_columns]
    
    if missing_columns:
        print(f"✗ Missing MarketData columns: {missing_columns}")
        sys.exit(1)
    else:
        print(f"✓ All required MarketData columns present: {required_columns}")
    
except Exception as e:
    print(f"✗ Database manager error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test config manager
print("\nTesting config manager...")
try:
    from orchestration.config_manager import Config
    
    config = Config()
    if hasattr(config, 'BENZINGA_API_KEY'):
        print("✓ BENZINGA_API_KEY in config")
    else:
        print("✗ BENZINGA_API_KEY missing from config")
        sys.exit(1)
    
except Exception as e:
    print(f"✗ Config manager error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test data orchestrator integration
print("\nTesting data orchestrator integration...")
try:
    from data_collection.data_orchestrator import DataOrchestrator
    
    # Check that benzinga_client is imported
    import data_collection.data_orchestrator as do_module
    if hasattr(do_module, 'BenzingaClient'):
        print("✓ BenzingaClient imported in data_orchestrator")
    else:
        print("✗ BenzingaClient not imported in data_orchestrator")
        sys.exit(1)
    
    # Check that DataOrchestrator has benzinga_client attribute
    # We can't instantiate without real config, but we can check the class
    if 'benzinga_client' in DataOrchestrator.__init__.__code__.co_names:
        print("✓ benzinga_client referenced in DataOrchestrator.__init__")
    else:
        # Check source code instead
        import inspect
        source = inspect.getsource(DataOrchestrator.__init__)
        if 'benzinga_client' in source:
            print("✓ benzinga_client found in DataOrchestrator.__init__ source")
        else:
            print("✗ benzinga_client not found in DataOrchestrator")
            sys.exit(1)
    
except Exception as e:
    print(f"✗ Data orchestrator error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✓ All Phase 1 tests passed!")
print("="*60)
