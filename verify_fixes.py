#!/usr/bin/env python3
"""
Verification script to check that all fixes are in place
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_database_schema():
    """Verify database schema has required fields"""
    from data_collection.database_manager import TechnicalMarketData, News
    
    print("Checking database schema...")
    
    # Check TechnicalMarketData has new fields
    tech_fields = ['sma_20', 'ema_20', 'rsi_14']
    for field in tech_fields:
        if hasattr(TechnicalMarketData, field):
            print(f"  ✓ TechnicalMarketData.{field} exists")
        else:
            print(f"  ✗ TechnicalMarketData.{field} MISSING")
            return False
    
    # Check News has sentiment_label
    if hasattr(News, 'sentiment_label'):
        print(f"  ✓ News.sentiment_label exists")
    else:
        print(f"  ✗ News.sentiment_label MISSING")
        return False
    
    # Check News property aliases
    news_properties = ['published_at', 'headline', 'summary']
    has_properties = all(hasattr(News, prop) for prop in news_properties)
    if has_properties:
        print(f"  ✓ News property aliases exist")
    else:
        print(f"  ✗ News property aliases MISSING")
        return False
    
    return True

def verify_imports():
    """Verify all modules can be imported"""
    print("\nChecking module imports...")
    
    try:
        from data_collection import DatabaseManager, DataProcessor
        print("  ✓ data_collection modules import correctly")
    except Exception as e:
        print(f"  ✗ data_collection import error: {e}")
        return False
    
    try:
        from thesis_generation import DataDeduplicator, CumulativePromptBuilder
        print("  ✓ thesis_generation modules import correctly")
    except Exception as e:
        print(f"  ✗ thesis_generation import error: {e}")
        return False
    
    try:
        from orchestration import main_pipeline, config_manager
        print("  ✓ orchestration modules import correctly")
    except Exception as e:
        print(f"  ✗ orchestration import error: {e}")
        return False
    
    return True

def verify_feature_engineering():
    """Verify feature engineering updates"""
    print("\nChecking feature engineering...")
    
    try:
        from data_collection.feature_engineering import FeatureEngineer
        from data_collection.database_manager import DatabaseManager
        
        # Check that FeatureEngineer accepts correct parameters
        import inspect
        sig = inspect.signature(FeatureEngineer.__init__)
        params = list(sig.parameters.keys())
        
        if 'db_manager' in params and 'max_workers' in params:
            print("  ✓ FeatureEngineer signature is correct")
        else:
            print(f"  ✗ FeatureEngineer signature incorrect: {params}")
            return False
        
        # Check for process_all_features method
        if hasattr(FeatureEngineer, 'process_all_features'):
            print("  ✓ FeatureEngineer.process_all_features exists")
        else:
            print("  ✗ FeatureEngineer.process_all_features MISSING")
            return False
        
    except Exception as e:
        print(f"  ✗ Feature engineering check error: {e}")
        return False
    
    return True

def verify_data_processor():
    """Verify data processor updates"""
    print("\nChecking data processor...")
    
    try:
        # Check that process_news includes sentiment_label in output
        with open('data_collection/data_processor.py', 'r') as f:
            content = f.read()
            if 'sentiment_label' in content and '"sentiment_label"' in content:
                print("  ✓ process_news includes sentiment_label")
            else:
                print("  ✗ process_news missing sentiment_label")
                return False
    except Exception as e:
        print(f"  ✗ Data processor check error: {e}")
        return False
    
    return True

def verify_scripts():
    """Verify required scripts exist and are executable"""
    print("\nChecking scripts...")
    
    scripts = [
        'scripts/reset_database.sh',
        'scripts/setup.sh',
        'scripts/run_pipeline.sh',
        'scripts/verify_setup.sh'
    ]
    
    for script in scripts:
        path = os.path.join(os.path.dirname(__file__), script)
        if os.path.exists(path) and os.access(path, os.X_OK):
            print(f"  ✓ {script} exists and is executable")
        else:
            print(f"  ✗ {script} missing or not executable")
            return False
    
    return True

def main():
    print("=" * 60)
    print("Trainer-Charlie Fixes Verification")
    print("=" * 60)
    
    all_passed = True
    
    # Run all checks
    all_passed &= verify_database_schema()
    all_passed &= verify_imports()
    all_passed &= verify_feature_engineering()
    all_passed &= verify_data_processor()
    all_passed &= verify_scripts()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All verification checks passed!")
        print("\nThe system is ready for testing.")
        print("\nNext step: Run a test with:")
        print("  ./scripts/run_pipeline.sh --test")
        return 0
    else:
        print("✗ Some verification checks failed!")
        print("\nPlease review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())