#!/usr/bin/env python3
"""
Test script for structured prompt builder

This script tests the structured prompt builder to ensure it can:
1. Query data from the database
2. Build structured prompts
3. Validate responses
"""
import sys
import logging
from datetime import date, timedelta

from data_collection.database_manager import DatabaseManager
from thesis_generation.structured_prompt_builder import StructuredPromptBuilder
from rlvr.response_adapter import adapt_structured_response_to_legacy, validate_structured_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_structured_prompt_builder():
    """Test the structured prompt builder"""
    logger.info("Testing Structured Prompt Builder...")
    
    # Initialize components
    db_manager = DatabaseManager()
    prompt_builder = StructuredPromptBuilder(db_manager)
    
    # Test with a known ticker (use AAPL as default)
    test_ticker = "AAPL"
    test_date = date.today() - timedelta(days=1)
    
    logger.info(f"Building structured prompt for {test_ticker} as of {test_date}")
    
    try:
        # Build prompt
        system_prompt, user_prompt = prompt_builder.build_structured_prompt(test_ticker, test_date)
        
        logger.info("✓ Successfully built structured prompt")
        logger.info(f"System prompt length: {len(system_prompt)} characters")
        logger.info(f"User prompt length: {len(user_prompt)} characters")
        
        # Check that prompts contain expected sections
        assert "fundamentals" in system_prompt.lower() or "fundamental" in system_prompt.lower(), "System prompt should mention fundamentals"
        assert "technical" in system_prompt.lower(), "System prompt should mention technical"
        assert "conclusion" in system_prompt.lower(), "System prompt should mention conclusion"
        
        logger.info("✓ System prompt contains required sections")
        
        # Print a sample of the prompts
        logger.info("\n=== SYSTEM PROMPT (first 500 chars) ===")
        logger.info(system_prompt[:500] + "...")
        
        logger.info("\n=== USER PROMPT (first 500 chars) ===")
        logger.info(user_prompt[:500] + "...")
        
        return True
        
    except ValueError as e:
        logger.error(f"✗ Error: {e}")
        logger.error("This might mean the ticker is not in the database or there's no data for the date.")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        return False


def test_response_adapter():
    """Test the response adapter"""
    logger.info("\nTesting Response Adapter...")
    
    # Sample structured response
    sample_response = {
        "fundamentals": {
            "balance_sheet_strength": "Strong balance sheet with low debt",
            "income_performance": "Growing revenue and profits",
            "key_metrics": {
                "pe_ratio": 25.5,
                "revenue_growth_yoy": 12.5
            }
        },
        "technical": {
            "price_action": "Bullish trend with strong momentum",
            "indicators": {
                "rsi_14": 58.5,
                "macd": "bullish"
            }
        },
        "news": {
            "sentiment_summary": "Positive sentiment overall"
        },
        "valuation": {
            "assessment": "Fairly valued"
        },
        "risk_assessment": {
            "ticker_specific_risks": "Low risk profile"
        },
        "macro": {
            "impact": "Favorable macro environment"
        },
        "conclusion": {
            "recommendation": "Strong Buy",
            "reasoning": "Strong fundamentals and technical indicators support a buy recommendation",
            "confidence": 0.85,
            "target_price": "$150.00",
            "time_horizon": "3-6 months"
        }
    }
    
    # Validate structured response
    is_valid, errors = validate_structured_response(sample_response)
    if is_valid:
        logger.info("✓ Structured response validation passed")
    else:
        logger.error(f"✗ Structured response validation failed: {errors}")
        return False
    
    # Adapt to legacy format
    legacy_response = adapt_structured_response_to_legacy(sample_response)
    
    logger.info("✓ Successfully adapted structured response to legacy format")
    logger.info(f"Legacy action: {legacy_response['action']}")
    logger.info(f"Legacy reasoning length: {len(legacy_response['reasoning'])} characters")
    logger.info(f"Legacy support length: {len(legacy_response['support'])} characters")
    
    # Verify legacy format has required fields
    assert "action" in legacy_response, "Legacy response should have 'action'"
    assert "reasoning" in legacy_response, "Legacy response should have 'reasoning'"
    assert "support" in legacy_response, "Legacy response should have 'support'"
    assert legacy_response["action"] == "strong_buy", f"Expected 'strong_buy', got '{legacy_response['action']}'"
    
    logger.info("✓ Legacy format validation passed")
    
    return True


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Structured Prompts Test Suite")
    logger.info("=" * 60)
    
    success = True
    
    # Test response adapter (doesn't require database)
    if not test_response_adapter():
        success = False
    
    # Test prompt builder (requires database)
    logger.info("\n" + "=" * 60)
    if not test_structured_prompt_builder():
        success = False
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("✗ Some tests failed")
        sys.exit(1)
