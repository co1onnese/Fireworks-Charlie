#!/usr/bin/env python3
"""
Test Fireworks API connection and model availability
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_fireworks_connection():
    """Test Fireworks API connection"""
    print("=== Fireworks API Connection Test ===\n")

    # Check API key
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    account_id = os.environ.get("FIREWORKS_ACCOUNT_ID", "")

    if not api_key:
        print("❌ FIREWORKS_API_KEY not found in environment")
        print("   Please set it in your .env file")
        return False

    if not account_id:
        print("⚠️  FIREWORKS_ACCOUNT_ID not found in environment")
        print("   (This may be optional depending on API usage)")

    print(f"✓ API Key found: {api_key[:10]}...")
    if account_id:
        print(f"✓ Account ID: {account_id}")

    # Test import
    try:
        import fireworks.client
        print("\n✓ fireworks-ai package imported successfully")
    except ImportError as e:
        print(f"\n❌ Failed to import fireworks-ai: {e}")
        print("   Run: pip install -e .")
        return False

    # Test API connection
    try:
        print("\n--- Testing API Connection ---")
        fireworks.client.api_key = api_key

        # Try to list available models
        from fireworks.client import Completion

        model_name = os.environ.get("MODEL_NAME", "accounts/fireworks/models/deepseek-v3p1-terminus")
        print(f"Testing model: {model_name}")

        # Simple test completion
        response = Completion.create(
            model=model_name,
            prompt="Hello, world!",
            max_tokens=10,
            temperature=0.7,
        )

        print("✓ API connection successful!")
        print(f"✓ Model response: {response.choices[0].text[:50]}...")
        return True

    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print("\nPossible issues:")
        print("  1. Invalid API key")
        print("  2. Model not accessible")
        print("  3. Network connectivity")
        return False


if __name__ == "__main__":
    success = test_fireworks_connection()
    sys.exit(0 if success else 1)
