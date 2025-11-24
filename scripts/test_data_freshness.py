#!/usr/bin/env python3
"""
Test Data Freshness Monitoring
"""

import os
import sys
from datetime import date, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collection.data_orchestrator import DataOrchestrator
from orchestration.config_manager import Config

def test_data_freshness():
    """Test the data freshness monitoring functionality"""

    print("=== DATA FRESHNESS MONITORING TEST ===\n")

    # Load configuration
    config = Config()
    orchestrator = DataOrchestrator(config)

    # Test with a few tickers
    test_tickers = ["AAPL", "MSFT", "ATVI", "TWTR"]
    test_date = date.today() - timedelta(days=1)  # Yesterday

    for ticker in test_tickers:
        print(f"\n--- Testing {ticker} on {test_date} ---")

        try:
            freshness_report = orchestrator.check_data_freshness(ticker, test_date)

            print(f"Fundamentals: {freshness_report['fundamentals']['status']}")
            if freshness_report['fundamentals']['latest_filing_date']:
                print(f"  - Latest filing: {freshness_report['fundamentals']['latest_filing_date']}")
                print(f"  - Days stale: {freshness_report['fundamentals']['days_stale']}")

            print(f"Market Data: {freshness_report['market_data']['status']}")
            if freshness_report['market_data']['latest_date']:
                print(f"  - Latest date: {freshness_report['market_data']['latest_date']}")
                print(f"  - Days stale: {freshness_report['market_data']['days_stale']}")

            print(f"News: {freshness_report['news']['status']}")
            if freshness_report['news']['latest_article_date']:
                print(f"  - Latest article: {freshness_report['news']['latest_article_date']}")
                print(f"  - Days stale: {freshness_report['news']['days_stale']}")

            if freshness_report['warnings']:
                print(f"\nWarnings:")
                for warning in freshness_report['warnings']:
                    print(f"  - {warning}")
            else:
                print(f"\n✅ All data is fresh")

        except Exception as e:
            print(f"❌ Error testing {ticker}: {e}")

    print(f"\n=== DATA FRESHNESS TEST COMPLETED ===")

if __name__ == "__main__":
    test_data_freshness()