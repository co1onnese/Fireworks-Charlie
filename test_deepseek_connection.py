#!/usr/bin/env python3
"""
Test script to verify DeepSeek API connection
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestration.config_manager import config
from thesis_generation.llm_factory import create_llm_client


def test_deepseek_connection():
    """Test DeepSeek API connection and basic generation"""
    print("=" * 70)
    print("DeepSeek API Connection Test")
    print("=" * 70)

    # Show configuration
    print(f"\n1. Configuration:")
    print(f"   LLM Provider: {config.LLM_PROVIDER}")
    print(f"   DeepSeek Model: {config.DEEPSEEK_MODEL}")
    print(f"   Base URL: {config.DEEPSEEK_BASE_URL}")
    print(f"   API Key: {config.DEEPSEEK_API_KEY[:10]}..." if config.DEEPSEEK_API_KEY else "   API Key: NOT SET")
    print(f"   Timeout: {config.API_TIMEOUT}s")

    # Check if API key is set
    if not config.DEEPSEEK_API_KEY:
        print("\n❌ ERROR: DEEPSEEK_API_KEY not found in .env file")
        print("   Please add your DeepSeek API key to .env:")
        print("   DEEPSEEK_API_KEY=sk-your-key-here")
        return False

    # Create client
    print(f"\n2. Creating LLM client...")
    try:
        client = create_llm_client(config.LLM_PROVIDER, config)
        print(f"   ✓ Client created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        return False

    # Test connection
    print(f"\n3. Testing API connection...")
    try:
        connection_ok = client.test_connection()
        if connection_ok:
            print(f"   ✓ Connection test passed")
        else:
            print(f"   ❌ Connection test failed")
            return False
    except Exception as e:
        print(f"   ❌ Connection test error: {e}")
        return False

    # Test simple generation
    print(f"\n4. Testing simple thesis generation...")
    test_prompt = """You are analyzing stock AAPL as of 2024-01-15.
Recent price: $185.50
Market trend: Bullish
Provide a brief trading recommendation."""

    try:
        result = client.generate_thesis(
            prompt=test_prompt,
            ticker="AAPL",
            as_of_date="2024-01-15"
        )

        if result["status"] == "success":
            print(f"   ✓ Generation successful")
            print(f"\n   Response preview:")
            print(f"   Action: {result.get('action', 'N/A')}")
            print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
            print(f"   Model: {result.get('model', 'N/A')}")
            print(f"   Tokens: {result.get('total_tokens', 'N/A')}")
        else:
            print(f"   ❌ Generation failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"   ❌ Generation error: {e}")
        import traceback
        print(f"\n   Traceback:")
        print(traceback.format_exc())
        return False

    # Success
    print("\n" + "=" * 70)
    print("✓ All tests passed! DeepSeek API is working correctly.")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_deepseek_connection()
    sys.exit(0 if success else 1)
