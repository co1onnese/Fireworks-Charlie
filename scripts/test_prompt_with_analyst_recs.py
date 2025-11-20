#!/usr/bin/env python3
"""
Test script to verify analyst recommendations are included in prompts.

This script:
1. Queries database for analyst recommendations for a ticker/date
2. Gets data using get_data_for_date
3. Generates a prompt using enhanced_prompt_builder
4. Checks if analyst recommendations are in the prompt
"""
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
import psycopg2

def check_analyst_recs_in_db(ticker: str, as_of_date: date, config: Config):
    """Check if analyst recommendations exist in database for this ticker/date."""
    conn = psycopg2.connect(config.DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*), MIN(ar.date), MAX(ar.date)
            FROM analyst_recommendations ar
            JOIN tickers t ON ar.ticker_id = t.ticker_id
            WHERE t.symbol = %s
            AND ar.date < %s
            AND ar.date >= %s - INTERVAL '90 days'
        """, (ticker.upper(), as_of_date, as_of_date))
        
        result = cur.fetchone()
        count, min_date, max_date = result
        return count, min_date, max_date
    finally:
        cur.close()
        conn.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test prompt generation with analyst recommendations")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Ticker symbol")
    parser.add_argument("--date", type=str, default="2025-01-15", help="Date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    config = Config()
    db_manager = DatabaseManager(config.DB_URL)
    data_orchestrator = DataOrchestrator(config)
    prompt_builder = EnhancedCumulativePromptBuilder()
    
    ticker = args.ticker.upper()
    as_of_date = date.fromisoformat(args.date)
    
    print("=" * 80)
    print(f"TESTING PROMPT GENERATION WITH ANALYST RECOMMENDATIONS")
    print("=" * 80)
    print(f"Ticker: {ticker}")
    print(f"Date: {as_of_date}")
    print()
    
    # Step 1: Check database for analyst recommendations
    print("Step 1: Checking database for analyst recommendations...")
    count, min_date, max_date = check_analyst_recs_in_db(ticker, as_of_date, config)
    print(f"  Found {count} analyst recommendations in database")
    if count > 0:
        print(f"  Date range: {min_date} to {max_date}")
    print()
    
    # Step 2: Get data using get_data_for_date
    print("Step 2: Getting data using get_data_for_date...")
    day_data = data_orchestrator.get_data_for_date(ticker, as_of_date)
    
    if "error" in day_data:
        print(f"  ERROR: {day_data['error']}")
        return
    
    analyst_recs = day_data.get('analyst_recommendations', [])
    print(f"  Analyst recommendations in day_data: {len(analyst_recs)}")
    if analyst_recs:
        print(f"  Sample recommendation:")
        sample = analyst_recs[0]
        print(f"    Date: {sample.get('date')}")
        print(f"    Firm: {sample.get('firm')}")
        print(f"    Rating: {sample.get('rating')}")
        print(f"    Action: {sample.get('action')}")
    print()
    
    # Step 3: Build cumulative data (simulate what pipeline does)
    print("Step 3: Building cumulative data...")
    cumulative_data = [day_data]  # In real pipeline, this would have multiple days
    print(f"  Cumulative data entries: {len(cumulative_data)}")
    
    # Count analyst recs in cumulative data
    total_recs = sum(len(d.get('analyst_recommendations', [])) for d in cumulative_data)
    print(f"  Total analyst recommendations in cumulative data: {total_recs}")
    print()
    
    # Step 4: Generate prompt
    print("Step 4: Generating prompt...")
    try:
        system_prompt, user_prompt = prompt_builder.build_comprehensive_prompt(
            ticker, cumulative_data, response_format="json"
        )
        print(f"  System prompt length: {len(system_prompt)} chars")
        print(f"  User prompt length: {len(user_prompt)} chars")
        print()
        
        # Step 5: Check if analyst recommendations are in prompt
        print("Step 5: Checking if analyst recommendations are in prompt...")
        has_analyst_section = "ANALYST RECOMMENDATIONS" in user_prompt.upper()
        has_analyst_data = any(keyword in user_prompt for keyword in [
            "analyst", "recommendation", "rating", "firm", "consensus"
        ])
        
        print(f"  Has 'ANALYST RECOMMENDATIONS' section: {has_analyst_section}")
        print(f"  Contains analyst-related keywords: {has_analyst_data}")
        print()
        
        if has_analyst_section:
            # Extract analyst section
            import re
            pattern = r'\*\*ANALYST RECOMMENDATIONS.*?\*\*(.*?)(?=\*\*|$)'
            match = re.search(pattern, user_prompt, re.DOTALL | re.IGNORECASE)
            if match:
                analyst_section = match.group(1).strip()
                print("  Analyst Recommendations Section Found:")
                print("  " + "-" * 76)
                for line in analyst_section.split('\n')[:20]:  # First 20 lines
                    print(f"  {line}")
                lines_count = len(analyst_section.split('\n'))
                if lines_count > 20:
                    remaining = lines_count - 20
                    print(f"  ... ({remaining} more lines)")
        else:
            print("  WARNING: Analyst recommendations section NOT found in prompt!")
            print()
            print("  Searching for any analyst-related content...")
            lines_with_analyst = [line for line in user_prompt.split('\n') 
                                if any(kw in line.lower() for kw in ['analyst', 'recommendation', 'rating'])]
            if lines_with_analyst:
                print(f"  Found {len(lines_with_analyst)} lines with analyst keywords:")
                for line in lines_with_analyst[:5]:
                    print(f"    {line[:100]}")
            else:
                print("  No analyst-related content found in prompt!")
        
    except Exception as e:
        print(f"  ERROR generating prompt: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
