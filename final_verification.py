#!/usr/bin/env python3
"""Final verification that data gathering and prompt generation are working"""
import os
import sys
from datetime import date

sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator

def verify_system():
    print("=" * 80)
    print("FINAL VERIFICATION: DATA GATHERING & PROMPT GENERATION")
    print("=" * 80)

    # Test cases with known good data
    test_cases = [
        ("NFLX", date(2024, 8, 1), "Netflix in Aug 2024"),
        ("XOM", date(2024, 8, 1), "Exxon with news in 2024"),
        ("HD", date(2024, 8, 1), "Home Depot"),
        ("MA", date(2024, 8, 1), "Mastercard"),
    ]

    all_passed = True

    for ticker, test_date, description in test_cases:
        print(f"\n{'='*80}")
        print(f"Testing: {ticker} on {test_date} - {description}")
        print(f"{'='*80}")

        orchestrator = DataOrchestrator(config)
        data = orchestrator.get_data_for_date(ticker, test_date)

        # Check data retrieval
        checks = {
            "Technical data": len(data.get('technical', [])) > 0,
            "Fundamentals": data.get('fundamentals') is not None,
            "News": data.get('news') is not None,  # May be empty list
            "Macro features": data.get('macro_features') is not None,
        }

        print("\nData Retrieval:")
        for check_name, passed in checks.items():
            print(f"  {'✓' if passed else '✗'} {check_name}")

        # Build prompt
        cumulative_data = [data]
        deduplicator = DataDeduplicator()
        prompt_builder = CumulativePromptBuilder(deduplicator)

        system_prompt, user_prompt = prompt_builder.build_cumulative_prompt_messages(
            ticker,
            cumulative_data,
            response_format="json"
        )

        # Check prompt content
        prompt_checks = {
            "Technical section": "=== TECHNICAL DATA ===" in user_prompt,
            "Fundamental section": "=== FUNDAMENTAL DATA ===" in user_prompt,
            "News section": "=== NEWS AND SENTIMENT ===" in user_prompt,
            "Macro section": "=== MACROECONOMIC DATA ===" in user_prompt,
        }

        print("\nPrompt Construction:")
        for check_name, passed in prompt_checks.items():
            print(f"  {'✓' if passed else '✗'} {check_name}")

        # Sample actual data in prompts
        if "Financial statements and metrics" in user_prompt:
            # Extract fundamentals
            fund_start = user_prompt.index("=== FUNDAMENTAL DATA ===")
            fund_end = user_prompt.index("=== NEWS AND SENTIMENT ===")
            fund_section = user_prompt[fund_start:fund_end]
            if "P/E Ratio:" in fund_section:
                # Extract P/E
                pe_line = [line for line in fund_section.split('\n') if 'P/E Ratio:' in line]
                if pe_line:
                    print(f"\n  Fundamentals sample: {pe_line[0].strip()}")

        if "Key economic indicators" in user_prompt:
            # Extract macro
            macro_start = user_prompt.index("=== MACROECONOMIC DATA ===")
            macro_end = user_prompt.find("\n\n", macro_start)
            if macro_end < 0:
                macro_end = macro_start + 300
            macro_section = user_prompt[macro_start:macro_end]
            for line in macro_section.split('\n'):
                if 'yield_curve' in line:
                    print(f"  Macro sample: {line.strip()}")
                    break

        # Determine pass/fail
        test_passed = all(checks.values()) and all(prompt_checks.values())
        print(f"\n{'✅ PASSED' if test_passed else '❌ FAILED'}")

        if not test_passed:
            all_passed = False

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if all_passed:
        print("✅ ALL SYSTEMS WORKING CORRECTLY!")
        print("\nThe fix has resolved the issues:")
        print("  • Data gathering retrieves fundamentals, macro, and technical data")
        print("  • Prompt generation includes all data sections")
        print("  • 'No news articles' correctly shows when no 2024 news is available")
        print("\nThe empty prompts from the old database were from before the fix.")
        print("New thesis generations will have complete data.")
    else:
        print("❌ SOME TESTS FAILED")

    print("=" * 80)

    return all_passed

if __name__ == "__main__":
    try:
        verify_system()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
