#!/usr/bin/env python3
"""
Test script to verify backfill setup before running full backfill
Tests database connection, API connections, and basic data insertion
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Try to load dotenv, but continue if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables directly.")
    # Load from .env manually
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value

print("=" * 60)
print("Backfill Setup Test")
print("=" * 60)

# Test 1: Database Connection
print("\n1. Testing Database Connection...")
try:
    from orchestration.config_manager import Config
    from data_collection.database_manager import DatabaseManager
    
    config = Config()
    print(f"   DB_URL: {config.DB_URL[:50]}...")
    
    db_manager = DatabaseManager(config.DB_URL)
    session = db_manager.get_session()
    result = session.execute("SELECT version()").scalar()
    print(f"   ✓ Database connection successful!")
    print(f"   PostgreSQL: {result.split(',')[0]}")
    
    # Check if tables exist
    table_count = session.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    """).scalar()
    print(f"   ✓ Found {table_count} tables in database")
    
    # Check for key tables
    key_tables = ['tickers', 'market_data', 'fundamentals', 'news', 'analyst_recommendations']
    for table in key_tables:
        exists = session.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = '{table}'
            )
        """).scalar()
        status = "✓" if exists else "✗"
        print(f"   {status} Table '{table}': {'exists' if exists else 'MISSING'}")
    
    session.close()
except Exception as e:
    print(f"   ✗ Database connection failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: EODHD API
print("\n2. Testing EODHD API...")
try:
    from data_collection.eodhd_client import EODHDClient
    
    api_key = config.EODHD_API_KEY if 'config' in locals() else os.environ.get('EODHD_API_KEY')
    if not api_key:
        print("   ✗ EODHD_API_KEY not found")
    else:
        client = EODHDClient(api_key)
        print(f"   API Key: {api_key[:10]}...")
        
        # Test market data
        market_data = client.get_eod_data("AAPL", "2024-10-24", "2024-10-31")
        print(f"   ✓ Market data: {len(market_data)} records")
        if market_data:
            print(f"      Sample: {market_data[0].get('date')} - Close: ${market_data[0].get('close')}")
        
        # Test fundamentals
        fundamentals = client.get_fundamentals("AAPL")
        print(f"   ✓ Fundamentals: {'Found' if fundamentals else 'None'}")
        
        # Test news
        news = client.get_news("AAPL", "2024-10-24", "2024-10-31")
        print(f"   ✓ News: {len(news)} articles")
        
        print("   ✓ EODHD API test successful!")
except Exception as e:
    print(f"   ✗ EODHD API error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: FMP API
print("\n3. Testing FMP API...")
try:
    from data_collection.fmp_client import FMPClient
    
    api_key = config.FMP_API_KEY if 'config' in locals() else os.environ.get('FMP_API_KEY')
    if not api_key:
        print("   ✗ FMP_API_KEY not found")
    else:
        client = FMPClient(api_key)
        print(f"   API Key: {api_key[:10]}...")
        
        grades = client.get_historical_grades("AAPL", limit=5)
        print(f"   ✓ Historical grades: {len(grades)} records")
        if grades:
            sample = grades[0]
            print(f"      Sample: {sample.get('date')} - Buy: {sample.get('analystRatingsBuy')}, Hold: {sample.get('analystRatingsHold')}")
        
        print("   ✓ FMP API test successful!")
except Exception as e:
    print(f"   ✗ FMP API error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Database Write Test
print("\n4. Testing Database Write Operations...")
try:
    session = db_manager.get_session()
    
    # Test ticker insertion
    ticker = db_manager.insert_or_get_ticker(session, "AAPL", "NASDAQ", "Apple Inc.", "Technology", "Consumer Electronics")
    print(f"   ✓ Ticker insertion: OK (ticker_id={ticker.ticker_id})")
    
    session.commit()
    session.close()
    print("   ✓ Database write test successful!")
except Exception as e:
    print(f"   ✗ Database write error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Setup Test Complete!")
print("=" * 60)
print("\nIf all tests passed, you can proceed with backfill:")
print("  python scripts/backfill_data.py --ticker AAPL --start-date 2024-10-24 --end-date 2024-10-31")
