#!/usr/bin/env python3
"""Test NFLX on multiple dates to verify consistency"""
import os
import sys
from datetime import date

sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator

def test_nflx_single(test_date):
    test_ticker = "NFLX"

    print(f"\n{'='*80}")
    print(f"Testing {test_ticker} on {test_date}")
    print('='*80)

    orchestrator = DataOrchestrator(config)
    data = orchestrator.get_data_for_date(test_ticker, test_date)

    has_fundamentals = data.get('fundamentals') is not None
    num_news = len(data.get('news', []))
    has_macro = data.get('macro_features') is not None
    num_technical = len(data.get('technical', []))

    print(f"Data retrieved:")
    print(f"  ✓ Technical: {num_technical} records")
    print(f"  {'✓' if has_fundamentals else '✗'} Fundamentals: {'Present' if has_fundamentals else 'None'}")
    print(f"  {'✓' if num_news > 0 else '✗'} News: {num_news} articles")
    print(f"  {'✓' if has_macro else '✗'} Macro: {'Present' if has_macro else 'None'}")

    # Build prompt
    cumulative_data = [data]
    deduplicator = DataDeduplicator()
    prompt_builder = CumulativePromptBuilder(deduplicator)

    system_prompt, user_prompt = prompt_builder.build_cumulative_prompt_messages(
        test_ticker,
        cumulative_data,
        response_format="json"
    )

    # Check prompt content
    has_fund_data = "Financial statements and metrics" in user_prompt
    has_news_data = "News coverage" in user_prompt or "No news articles" in user_prompt
    has_macro_data = "Key economic indicators" in user_prompt

    print(f"\nPrompt generated:")
    print(f"  Size: {len(user_prompt)} chars")
    print(f"  {'✓' if has_fund_data else '✗'} Includes fundamentals data")
    print(f"  {'✓' if has_news_data else '✗'} Includes news section")
    print(f"  {'✓' if has_macro_data else '✗'} Includes macro data")

    # Show sample data if present
    if has_fundamentals:
        fund = data['fundamentals']
        print(f"\n  Sample fundamentals:")
        print(f"    Filing: {fund['filing_date']}")
        print(f"    P/E: {fund['pe_ratio']}")
        print(f"    Revenue: ${fund['revenue']:,}")

    if has_macro:
        macro = data['macro_features']
        print(f"\n  Sample macro:")
        print(f"    Date: {macro['date']}")
        print(f"    Yield Curve: {macro.get('yield_curve_10y_2y', 'N/A')}")

    return has_fundamentals and has_macro

def main():
    print("NFLX DATA GATHERING & PROMPT GENERATION TEST")
    print("=" * 80)

    test_dates = [
        date(2024, 1, 15),   # Early 2024
        date(2024, 6, 1),    # Mid 2024
        date(2024, 8, 1),    # Late 2024
        date(2025, 1, 15),   # Early 2025
        date(2025, 7, 1),    # Mid 2025
    ]

    results = []
    for test_dt in test_dates:
        success = test_nflx_single(test_dt)
        results.append((test_dt, success))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_dt, success in results:
        status = "✅" if success else "✗"
        print(f"{status} {test_dt}")

    all_success = all(success for _, success in results)
    print(f"\n{'✅ ALL TESTS PASSED' if all_success else '❌ SOME TESTS FAILED'}")

if __name__ == "__main__":
    main()
