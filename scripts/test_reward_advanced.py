#!/usr/bin/env python3
"""
Test the advanced reward function with comprehensive scenarios.

Demonstrates improvements over the simple version.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.reward_function_advanced import stock_prediction_reward


def test_strong_buy_large_gain():
    """Test STRONG_BUY with large gain - should score very high."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze NVDA stock."},
        {"role": "assistant", "content": '{"action": "strong_buy", "reasoning": "NVDA shows exceptional momentum with strong earnings growth of 45% YoY, expanding profit margins at 35%, and robust demand in AI sector. Technical indicators including RSI at 65 and price above all major moving averages confirm bullish trend.", "support": "Q3 earnings beat by 15%, data center revenue up 60%, GPU demand accelerating with $50B market opportunity"}'}
    ]
    
    ground_truth = {"actual_return_pct": 5.5}  # Strong gain matches strong_buy
    metadata = {
        "ticker": "NVDA",
        "historical_returns": [3.0, 4.0, 2.5, 3.5, 5.0, 4.5]  # Consistently positive
    }
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 1: STRONG_BUY with large gain + quality reasoning")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional: {result.metrics['directional_accuracy'].score:.2f}")
    print(f"  Magnitude: {result.metrics['magnitude_accuracy'].score:.2f}")
    print(f"  Calibration: {result.metrics['confidence_calibration'].score:.2f}")
    print(f"  Reasoning Quality: {result.metrics['reasoning_quality'].score:.2f}")
    assert result.score > 0.85, f"Expected >0.85, got {result.score}"
    print("  ? PASSED - High score for well-calibrated strong signal\n")


def test_strong_buy_small_gain():
    """Test STRONG_BUY with small gain - should penalize overconfidence."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze stock."},
        {"role": "assistant", "content": '{"action": "strong_buy", "reasoning": "Looks good", "support": "Going up"}'}
    ]
    
    ground_truth = {"actual_return_pct": 1.5}  # Small gain, not strong enough
    metadata = {"ticker": "XYZ", "historical_returns": [0.5, 1.0, -0.5, 1.5]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 2: STRONG_BUY with small gain (overconfident) + poor reasoning")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional: {result.metrics['directional_accuracy'].score:.2f} (wrong threshold)")
    print(f"  Calibration: {result.metrics['confidence_calibration'].score:.2f} (overconfident)")
    print(f"  Reasoning Quality: {result.metrics['reasoning_quality'].score:.2f} (poor)")
    assert result.score < 0.30, f"Expected <0.30, got {result.score}"
    print("  ? PASSED - Low score for overconfident poor prediction\n")


def test_buy_recommendation_crash():
    """Test BUY when stock crashes - should heavily penalize."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze LCID stock."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Company has potential for growth based on recent product launches and expanding market share in EV sector.", "support": "New model launch, increasing production capacity"}'}
    ]
    
    ground_truth = {"actual_return_pct": -8.0}  # Crash!
    metadata = {"ticker": "LCID", "historical_returns": [-2.0, -3.0, 1.0, -4.0, -1.5]}
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 3: BUY recommendation on crashing stock (downside penalty)")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional: {result.metrics['directional_accuracy'].score:.2f} (wrong)")
    print(f"  Downside Protection: {result.metrics['downside_protection'].score:.2f}")
    print(f"  Downside Penalty: {result.metrics['downside_protection'].reason}")
    assert result.score < 0.25, f"Expected <0.25, got {result.score}"
    print("  ? PASSED - Heavy penalty for recommending crashed stock\n")


def test_hold_volatile_correct():
    """Test HOLD during volatility - should reward caution."""
    messages = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze TSLA stock."},
        {"role": "assistant", "content": '{"action": "hold", "reasoning": "Stock showing mixed signals with high volatility. Technical indicators inconclusive with RSI near 50, price oscillating around 200-day MA. Earnings upcoming may cause significant movement. Best to wait for clearer direction before committing capital.", "support": "Historical volatility elevated at 45%, upcoming earnings in 2 weeks, no clear trend established"}'}
    ]
    
    ground_truth = {"actual_return_pct": 0.5}  # Small move, HOLD was right
    metadata = {
        "ticker": "TSLA",
        "historical_returns": [2.0, -3.0, 4.0, -2.5, 1.5, -1.0]  # Volatile
    }
    
    result = stock_prediction_reward(
        messages=messages,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 4: HOLD during uncertainty (appropriate caution)")
    print(f"  Score: {result.score:.3f}")
    print(f"  Reason: {result.reason}")
    print(f"  Directional: {result.metrics['directional_accuracy'].score:.2f} (correct)")
    print(f"  Magnitude: {result.metrics['magnitude_accuracy'].score:.2f}")
    print(f"  Calibration: {result.metrics['confidence_calibration'].score:.2f} (well-calibrated)")
    print(f"  Reasoning Quality: {result.metrics['reasoning_quality'].score:.2f}")
    assert result.score > 0.70, f"Expected >0.70, got {result.score}"
    print("  ? PASSED - Rewards appropriate caution\n")


def test_magnitude_accuracy_comparison():
    """Compare two BUY predictions with different magnitude accuracy."""
    messages_close = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze AAPL."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Moderate growth expected with iPhone sales steady and services revenue growing.", "support": "P/E ratio at 25, earnings growth projected at 8%"}'}
    ]
    
    messages_far = messages_close.copy()
    
    # Both predict BUY (~2.5% expected), but actual returns differ
    
    # Close prediction
    result_close = stock_prediction_reward(
        messages=messages_close,
        ground_truth={"actual_return_pct": 2.8},  # Close to expectation
        metadata={"ticker": "AAPL", "historical_returns": [2.0, 2.5, 3.0, 2.2]}
    )
    
    # Far prediction
    result_far = stock_prediction_reward(
        messages=messages_far,
        ground_truth={"actual_return_pct": 8.0},  # Way higher than expected
        metadata={"ticker": "AAPL", "historical_returns": [2.0, 2.5, 3.0, 2.2]}
    )
    
    print("Test 5: Magnitude accuracy comparison (both BUY, different actual returns)")
    print(f"  Close prediction (2.8% actual):")
    print(f"    Score: {result_close.score:.3f}")
    print(f"    Magnitude: {result_close.metrics['magnitude_accuracy'].score:.2f}")
    print(f"  Far prediction (8.0% actual):")
    print(f"    Score: {result_far.score:.3f}")
    print(f"    Magnitude: {result_far.metrics['magnitude_accuracy'].score:.2f}")
    
    # Close prediction should score higher due to magnitude accuracy
    print(f"  Difference: {result_close.score - result_far.score:+.3f}")
    assert result_close.score > result_far.score, "Close prediction should score higher"
    print("  ? PASSED - Rewards magnitude accuracy\n")


def test_reasoning_quality_impact():
    """Test impact of reasoning quality on score."""
    # Good reasoning
    messages_good = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze MSFT."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Microsoft demonstrates strong fundamentals with cloud revenue growth of 25% YoY, Azure gaining market share against AWS. P/E ratio of 28 is reasonable given 15% earnings growth. Technical analysis shows price consolidating above $350 support with RSI at healthy 58 level indicating room for upside.", "support": "Q2 earnings beat estimates by 8%, Azure revenue up 30%, $60B cloud market opportunity, dividend yield 0.8% provides downside protection"}'}
    ]
    
    # Poor reasoning
    messages_poor = [
        {"role": "system", "content": "You are a financial analyst."},
        {"role": "user", "content": "Analyze MSFT."},
        {"role": "assistant", "content": '{"action": "buy", "reasoning": "Good company", "support": "Price up"}'}
    ]
    
    # Same actual outcome
    ground_truth = {"actual_return_pct": 3.0}
    metadata = {"ticker": "MSFT", "historical_returns": [2.0, 3.0, 2.5, 3.5]}
    
    result_good = stock_prediction_reward(
        messages=messages_good,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    result_poor = stock_prediction_reward(
        messages=messages_poor,
        ground_truth=ground_truth,
        metadata=metadata
    )
    
    print("Test 6: Reasoning quality impact (same prediction & outcome)")
    print(f"  Good reasoning:")
    print(f"    Score: {result_good.score:.3f}")
    print(f"    Quality: {result_good.metrics['reasoning_quality'].score:.2f}")
    print(f"  Poor reasoning:")
    print(f"    Score: {result_poor.score:.3f}")
    print(f"    Quality: {result_poor.metrics['reasoning_quality'].score:.2f}")
    print(f"  Difference: {result_good.score - result_poor.score:+.3f}")
    
    # Good reasoning should provide 10-15% score boost
    assert result_good.score > result_poor.score + 0.08, "Good reasoning should provide significant boost"
    print("  ? PASSED - Rewards quality reasoning\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Advanced Reward Function")
    print("=" * 70)
    print()
    
    try:
        test_strong_buy_large_gain()
        test_strong_buy_small_gain()
        test_buy_recommendation_crash()
        test_hold_volatile_correct()
        test_magnitude_accuracy_comparison()
        test_reasoning_quality_impact()
        
        print("=" * 70)
        print("? All tests PASSED!")
        print("=" * 70)
        print()
        print("Advanced reward function improvements:")
        print("  ? Magnitude accuracy (not just direction)")
        print("  ? Confidence calibration (strong signals should be more accurate)")
        print("  ? Downside protection (extra penalty for large losses)")
        print("  ? Reasoning quality (rewards detailed analysis)")
        print("  ? Multi-metric evaluation (5 components)")
        print("  ? Hierarchical scoring (format ? reasonableness ? accuracy)")
        print()
        print("The advanced version provides much more nuanced feedback!")
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
