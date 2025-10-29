#!/usr/bin/env python3
"""
Test script to demonstrate thesis generation without full data collection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from thesis_generation.data_deduplicator import DataDeduplicator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.llm_client import DeepSeekClient
from thesis_generation.xml_thesis_generator import XMLThesisGenerator
from orchestration.config_manager import config

def create_sample_data():
    """Create sample data for testing"""
    return [
        {
            "date": date(2024, 1, 2),
            "technical": [{
                "date": date(2024, 1, 2),
                "open": 185.50,
                "high": 187.25,
                "low": 184.80,
                "close": 186.90,
                "volume": 45000000,
                "sma_20": 184.50,
                "ema_20": 185.20,
                "rsi_14": 58.5
            }],
            "fundamentals": {
                "report_date": date(2023, 12, 31),
                "filing_date": date(2024, 1, 15),
                "market_cap": 2950000000000,
                "pe_ratio": 28.5,
                "eps": 6.57,
                "revenue": 117154000000,
                "revenue_qoq_change": 2.1,
                "revenue_yoy_change": 5.5
            },
            "news": [
                {
                    "published_at": date(2024, 1, 2),
                    "headline": "Apple Reports Strong Holiday Sales",
                    "summary": "Apple Inc. reported better than expected holiday sales...",
                    "sentiment_score": 0.75,
                    "sentiment_label": "positive"
                }
            ],
            "macro_features": {
                "date": date(2024, 1, 2),
                "yield_curve_spread": 0.45,
                "cpi_monthly_change": 0.2,
                "gdp_quarterly_change": 2.1
            }
        },
        {
            "date": date(2024, 1, 3),
            "technical": [{
                "date": date(2024, 1, 3),
                "open": 186.90,
                "high": 188.50,
                "low": 186.50,
                "close": 187.80,
                "volume": 48000000,
                "sma_20": 185.10,
                "ema_20": 186.00,
                "rsi_14": 61.2
            }],
            "fundamentals": None,  # No new fundamentals
            "news": [
                {
                    "published_at": date(2024, 1, 3),
                    "headline": "Analysts Upgrade Apple Price Target",
                    "summary": "Multiple analysts raised their price targets for Apple...",
                    "sentiment_score": 0.82,
                    "sentiment_label": "positive"
                }
            ],
            "macro_features": None  # No changes
        }
    ]

def main():
    print("Testing Trainer-Charlie Thesis Generation")
    print("=" * 50)
    
    # Initialize components
    deduplicator = DataDeduplicator()
    prompt_builder = CumulativePromptBuilder(deduplicator)
    xml_generator = XMLThesisGenerator(config.THESIS_OUTPUT_DIR)
    
    # Create sample data
    ticker = "AAPL"
    sample_data = create_sample_data()
    
    # Test prompt building
    print("\nBuilding cumulative prompt...")
    prompt = prompt_builder.build_cumulative_prompt(ticker, sample_data)
    print(f"Prompt length: {len(prompt)} characters")
    print("\nFirst 500 characters of prompt:")
    print(prompt[:500])
    print("...")
    
    # Test XML generation with mock thesis
    print("\n\nTesting XML generation...")
    thesis_data = {
        "reasoning": "Based on the technical indicators showing RSI at 61.2 and positive momentum, combined with strong holiday sales and analyst upgrades, AAPL shows bullish signals.",
        "action": "buy",
        "support": "1) RSI trending up from 58.5 to 61.2, 2) Revenue growth of 5.5% YoY, 3) Positive analyst sentiment with price target upgrades"
    }
    
    success = xml_generator.append_thesis(
        ticker=ticker,
        as_of_date="2024-01-03",
        thesis_data=thesis_data
    )
    
    if success:
        print("✓ Successfully generated XML thesis")
        print(f"\nCheck output at: {config.THESIS_OUTPUT_DIR}/{ticker}_theses.xml")
    else:
        print("✗ Failed to generate XML thesis")
    
    # Test LLM if configured
    if config.DEEPSEEK_API_KEY and config.DEEPSEEK_API_KEY != "your_deepseek_key_here":
        print("\n\nTesting DeepSeek integration...")
        llm_client = DeepSeekClient(config.DEEPSEEK_API_KEY, config.DEEPSEEK_BASE_URL)
        
        if llm_client.test_connection():
            print("✓ DeepSeek connection successful")
            
            # Generate a real thesis
            print("\nGenerating thesis with LLM...")
            result = llm_client.generate_thesis(
                prompt=prompt,
                ticker=ticker,
                as_of_date="2024-01-03"
            )
            
            if result["status"] == "success":
                print("✓ LLM thesis generated successfully")
                print(f"Action: {result['action']}")
                print(f"Reasoning preview: {result['reasoning'][:200]}...")
            else:
                print(f"✗ LLM generation failed: {result.get('error')}")
        else:
            print("✗ DeepSeek connection failed")
    else:
        print("\n\nDeepSeek not configured - skipping LLM test")
    
    print("\n" + "=" * 50)
    print("Test completed")

if __name__ == "__main__":
    main()