#!/usr/bin/env python3
"""
Test EODHD Client and API Key
"""

import os
import sys
from datetime import datetime, date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collection.eodhd_client import EODHDClient
from orchestration.config_manager import Config

def test_eodhd_client():
    """Test EODHD client connectivity and API key"""

    print("=== EODHD CLIENT TEST ===\n")

    # Load configuration
    config = Config()

    print(f"1. CONFIGURATION CHECK:")
    print(f"   - EODHD_API_KEY present: {'Yes' if config.EODHD_API_KEY else 'No'}")
    print(f"   - API Key length: {len(config.EODHD_API_KEY) if config.EODHD_API_KEY else 0}")

    if not config.EODHD_API_KEY:
        print("\n❌ ERROR: EODHD_API_KEY not found in configuration")
        return False

    # Test client initialization
    try:
        client = EODHDClient(config.EODHD_API_KEY)
        print(f"   - Client initialized: Yes")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize EODHD client: {e}")
        return False

    # Test basic API call with a simple symbol
    print(f"\n2. API CONNECTIVITY TEST:")

    test_symbols = ["AAPL.US", "MSFT.US"]

    for symbol in test_symbols:
        try:
            print(f"\n   Testing symbol: {symbol}")

            # Test fundamentals endpoint
            fundamentals = client.get_fundamentals(symbol)

            if isinstance(fundamentals, dict) and fundamentals:
                print(f"   - Fundamentals: SUCCESS ({len(fundamentals)} keys)")

                # Check for expected sections
                expected_sections = ['General', 'Highlights', 'Financials']
                found_sections = [section for section in expected_sections if section in fundamentals]

                if found_sections:
                    print(f"   - Found sections: {', '.join(found_sections)}")

                    # Check for quarterly data
                    if 'Financials' in fundamentals:
                        financials = fundamentals['Financials']
                        quarterly_data = {}

                        for statement_type in ['Balance_Sheet', 'Income_Statement', 'Cash_Flow']:
                            if statement_type in financials and 'quarterly' in financials[statement_type]:
                                quarterly_count = len(fundamentals['Financials'][statement_type]['quarterly'])
                                quarterly_data[statement_type] = quarterly_count

                        if quarterly_data:
                            print(f"   - Quarterly data: {quarterly_data}")
                        else:
                            print(f"   - Quarterly data: None found")

                else:
                    print(f"   - WARNING: No expected sections found")

            else:
                print(f"   - Fundamentals: FAILED (empty response)")

        except Exception as e:
            print(f"   - ERROR: {e}")
            return False

    print(f"\n✅ EODHD CLIENT TEST COMPLETED SUCCESSFULLY")
    return True

if __name__ == "__main__":
    success = test_eodhd_client()
    sys.exit(0 if success else 1)