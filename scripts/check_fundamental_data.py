#!/usr/bin/env python3
"""
Fundamental Data Diagnostic Script
Quick check of current fundamental data state
"""

import os
import sys
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collection.database_manager import DatabaseManager, Ticker, Fundamental
from orchestration.config_manager import Config

def check_fundamental_data():
    """Run comprehensive fundamental data diagnostic"""

    config = Config()
    db_manager = DatabaseManager(config.DB_URL)

    session = db_manager.get_session()

    try:
        print("=== FUNDAMENTAL DATA DIAGNOSTIC REPORT ===\n")

        # 1. Overall statistics
        total_fundamentals = session.query(func.count(Fundamental.fundamental_id)).scalar()
        total_tickers = session.query(func.count(Ticker.ticker_id)).scalar()
        active_tickers = session.query(func.count(Ticker.ticker_id)).filter(Ticker.is_active == True).scalar()

        print(f"1. DATABASE OVERVIEW:")
        print(f"   - Total fundamental records: {total_fundamentals}")
        print(f"   - Total tickers: {total_tickers}")
        print(f"   - Active tickers: {active_tickers}")

        # 2. Data distribution by year
        year_distribution = session.query(
            func.extract('year', Fundamental.report_date).label('year'),
            func.count(Fundamental.fundamental_id).label('count')
        ).group_by('year').order_by('year').all()

        print(f"\n2. DATA DISTRIBUTION BY YEAR:")
        for year, count in year_distribution:
            print(f"   - {int(year)}: {count} records")

        # 3. Tickers with fundamental data
        tickers_with_fundamentals = session.query(
            Ticker.symbol,
            func.count(Fundamental.fundamental_id).label('count'),
            func.max(Fundamental.report_date).label('latest_report')
        ).join(Fundamental, Ticker.ticker_id == Fundamental.ticker_id)\
         .group_by(Ticker.symbol)\
         .order_by(func.count(Fundamental.fundamental_id).desc())\
         .limit(10).all()

        print(f"\n3. TOP 10 TICKERS BY FUNDAMENTAL DATA COUNT:")
        for symbol, count, latest in tickers_with_fundamentals:
            print(f"   - {symbol}: {count} records, latest: {latest}")

        # 4. Tickers without fundamental data
        tickers_without_fundamentals = session.query(Ticker.symbol)\
            .filter(
                Ticker.is_active == True,
                ~Ticker.ticker_id.in_(
                    session.query(Fundamental.ticker_id).distinct()
                )
            ).all()

        print(f"\n4. ACTIVE TICKERS WITHOUT FUNDAMENTAL DATA ({len(tickers_without_fundamentals)}):")
        if tickers_without_fundamentals:
            symbols = [t[0] for t in tickers_without_fundamentals]
            print(f"   - {', '.join(symbols[:10])}")
            if len(symbols) > 10:
                print(f"   - ... and {len(symbols) - 10} more")
        else:
            print("   - None (all active tickers have fundamental data)")

        # 5. Data freshness analysis
        today = date.today()
        stale_threshold = today - timedelta(days=90)

        stale_tickers = session.query(
            Ticker.symbol,
            func.max(Fundamental.filing_date).label('latest_filing')
        ).join(Fundamental, Ticker.ticker_id == Fundamental.ticker_id)\
         .group_by(Ticker.symbol)\
         .having(func.max(Fundamental.filing_date) < stale_threshold)\
         .all()

        print(f"\n5. STALE FUNDAMENTAL DATA (>90 days old):")
        if stale_tickers:
            for symbol, latest_filing in stale_tickers[:10]:
                days_stale = (today - latest_filing).days
                print(f"   - {symbol}: {latest_filing} ({days_stale} days old)")
            if len(stale_tickers) > 10:
                print(f"   - ... and {len(stale_tickers) - 10} more")
        else:
            print("   - None (all fundamental data is fresh)")

        # 6. Recent thesis generation analysis
        # Note: This requires ThesisGeneration import and proper SQL query
        # For now, we'll skip this section
        recent_theses = None

        if recent_theses and recent_theses[0] > 0:
            missing_pct = (recent_theses[1] / recent_theses[0]) * 100
            print(f"\n6. RECENT THESIS GENERATION ANALYSIS (last 30 days):")
            print(f"   - Total theses: {recent_theses[0]}")
            print(f"   - Missing fundamentals: {recent_theses[1]} ({missing_pct:.1f}%)")

        print(f"\n=== DIAGNOSTIC COMPLETE ===")

    finally:
        session.close()

if __name__ == "__main__":
    check_fundamental_data()