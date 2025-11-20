#!/usr/bin/env python3
"""
Check current status of analyst recommendations in database.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
import psycopg2

def main():
    config = Config()
    
    # Get tickers from config
    tickers_str = config.TICKERS if hasattr(config, 'TICKERS') else ''
    tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]

    print(f"Total tickers in config: {len(tickers)}")
    print(f"\nChecking analyst recommendations status...")

    # Connect directly with psycopg2 for queries
    conn = psycopg2.connect(config.DB_URL)
    cur = conn.cursor()

    # Query analyst recommendations status
    cur.execute("""
        SELECT 
            t.symbol,
            COUNT(DISTINCT ar.date) as dates_with_recs,
            COUNT(ar.recommendation_id) as total_recs,
            MIN(ar.date) as earliest_date,
            MAX(ar.date) as latest_date
        FROM tickers t
        LEFT JOIN analyst_recommendations ar ON t.ticker_id = ar.ticker_id
        WHERE t.symbol = ANY(%s)
        GROUP BY t.symbol
        ORDER BY t.symbol;
    """, (tickers,))

    results = cur.fetchall()
    print(f"\nTickers with analyst recommendations: {len([r for r in results if r[1] > 0])}")
    print("\nSymbol | Dates with Recs | Total Recs | Earliest | Latest")
    print("-" * 70)

    for row in results:
        symbol, dates, total, earliest, latest = row
        print(f"{symbol:6} | {dates:15} | {total:10} | {earliest or 'N/A':8} | {latest or 'N/A':8}")

    # Summary
    cur.execute("""
        SELECT 
            COUNT(DISTINCT t.ticker_id) as total_tickers,
            COUNT(DISTINCT ar.ticker_id) as tickers_with_recs,
            COUNT(ar.recommendation_id) as total_recommendations
        FROM tickers t
        LEFT JOIN analyst_recommendations ar ON t.ticker_id = ar.ticker_id
        WHERE t.symbol = ANY(%s);
    """, (tickers,))

    summary = cur.fetchone()
    print(f"\nSUMMARY:")
    print(f"  Total tickers: {summary[0]}")
    print(f"  Tickers with recommendations: {summary[1]}")
    print(f"  Total recommendations: {summary[2]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
