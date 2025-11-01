#!/usr/bin/env python3
"""
Test the standalone reward function locally before deployment.

This ensures the reward function works correctly without any external dependencies.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.reward_function_standalone import stock_prediction_reward


def test_correct_buy_prediction():
    """Test a correct BUY prediction."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze AAPL stock."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Technical indicators positive", "support": "RSI and moving averages bullish"}'}
    ]
    
    ground_truth = {"actual_return_pct": 2.5}  # BUY threshold is 2%, so this is correct
    metadata = {"ticker": "AAPL", "historical_returns": [1.5, 2.0, -0.5, 1.0, 2.5]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 1: Correct BUY prediction")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional accuracy: {result.metrics['directional_accuracy'].score:.1f}")
    assert result.score > 0.7, f"Expected score > 0.7, got {result.score}"
    print("  ? PASSED\n")


def test_incorrect_sell_prediction():
    """Test an incorrect SELL prediction (stock went up)."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze TSLA stock."},
        {"role": "assistant", "content": '{"action": "sell", "reasoning": "Overvalued", "support": "P/E ratio too high"}'}
    ]
    
    ground_truth = {"actual_return_pct": 3.0}  # Stock went up, but we predicted SELL
    metadata = {"ticker": "TSLA", "historical_returns": [2.0, 1.5, -1.0, 0.5, 3.0]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 2: Incorrect SELL prediction")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional accuracy: {result.metrics['directional_accuracy'].score:.1f}")
    assert result.score < 0.3, f"Expected score < 0.3, got {result.score}"
    print("  ? PASSED\n")


def test_correct_hold_prediction():
    """Test a correct HOLD prediction."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze MSFT stock."},
        {"role": "assistant", "content": '{"action": "hold", "reasoning": "Consolidating", "support": "Sideways price action"}'}
    ]
    
    ground_truth = {"actual_return_pct": 1.0}  # Within HOLD range [-2%, 2%]
    metadata = {"ticker": "MSFT", "historical_returns": [0.5, -0.5, 1.0, -1.0, 1.5]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 3: Correct HOLD prediction")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional accuracy: {result.metrics['directional_accuracy'].score:.1f}")
    assert result.score > 0.7, f"Expected score > 0.7, got {result.score}"
    print("  ? PASSED\n")


def test_invalid_json():
    """Test handling of invalid JSON."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze GOOGL stock."},
        {"role": "assistant", "content": 'This is not valid JSON'}
    ]
    
    ground_truth = {"actual_return_pct": 2.5}
    metadata = {"ticker": "GOOGL", "historical_returns": [1.0, 2.0, 1.5]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 4: Invalid JSON response")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    assert result.score == 0.0, f"Expected score 0.0, got {result.score}"
    assert "error" in result.metrics
    print("  ? PASSED\n")


def test_missing_ground_truth():
    """Test handling of missing ground truth."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze NFLX stock."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Growth", "support": "Subscriber growth"}'}
    ]
    
    # No ground_truth provided
    result = stock_prediction_reward(
        messages=messages,
        metadata={"ticker": "NFLX"}
    )
    
    print("Test 5: Missing ground truth")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    assert result.score == 0.0, f"Expected score 0.0, got {result.score}"
    assert "ground_truth" in result.reason.lower()
    print("  ? PASSED\n")


def test_sharpe_ratio_calculation():
    """Test Sharpe ratio with good historical returns."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze AMZN stock."},
        {"role": "assistant", "content": '{"action": "strong_buy", "reasoning": "Momentum", "support": "Strong uptrend"}'}
    ]
    
    # Strong positive returns should give high Sharpe
    ground_truth = {"actual_return_pct": 4.0}
    metadata = {
        "ticker": "AMZN",
        "historical_returns": [3.0, 2.5, 3.5, 2.0, 4.0, 3.0, 2.5, 3.5]  # Consistent positive returns
    }
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 6: Good Sharpe ratio with consistent returns")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Sharpe score: {result.metrics['sharpe_score'].score:.3f}")
    assert result.score > 0.85, f"Expected score > 0.85, got {result.score}"
    assert result.metrics['sharpe_score'].score > 0.5
    print("  ? PASSED\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Standalone Reward Function")
    print("=" * 70)
    print()
    
    try:
        test_correct_buy_prediction()
        test_incorrect_sell_prediction()
        test_correct_hold_prediction()
        test_invalid_json()
        test_missing_ground_truth()
        test_sharpe_ratio_calculation()
        
        print("=" * 70)
        print("? All tests PASSED!")
        print("=" * 70)
        print()
        print("The standalone reward function is working correctly.")
        print("It can now be deployed to Fireworks AI.")
        return True
        
    except AssertionError as e:
        print(f"\n? Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n? Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
