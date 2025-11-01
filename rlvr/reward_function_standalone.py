"""
RLVR Reward Function - Standalone Version for Fireworks Deployment

This is a completely self-contained reward function that can be deployed to
Fireworks AI without any external dependencies beyond reward_kit.

All logic from PerformanceCalculator and config is inlined here.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import json
from typing import Dict, List, Optional, Any

from reward_kit import reward_function, EvaluateResult, MetricResult


# Constants (formerly from config)
DIRECTIONAL_ACCURACY_WEIGHT = 80.0  # 80% weight
SHARPE_RATIO_WEIGHT = 20.0          # 20% weight
STRONG_BUY_THRESHOLD = 3.0
BUY_THRESHOLD = 2.0
HOLD_THRESHOLD_LOW = -2.0
HOLD_THRESHOLD_HIGH = 2.0
SELL_THRESHOLD = -2.0
STRONG_SELL_THRESHOLD = -3.0


@reward_function
def stock_prediction_reward(
    messages: List[Dict[str, str]],
    original_messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
) -> EvaluateResult:
    """
    Reward function for stock prediction RLVR training.
    
    Evaluates stock prediction responses based on:
    1. Directional accuracy (80% weight) - Binary scoring for correct direction
    2. Sharpe ratio (20% weight) - Risk-adjusted performance metric
    
    Args:
        messages: List of conversation messages from the model
        original_messages: Original messages before any modifications
        **kwargs: Additional context including ground_truth and metadata
        
    Returns:
        EvaluateResult with score, metrics, and detailed breakdown
    """
    try:
        # Extract assistant response from messages
        assistant_response = _extract_assistant_response(messages)
        if not assistant_response or not assistant_response.strip():
            return _create_error_result("No assistant response found in messages or empty response")

        # Parse JSON response
        try:
            response_data = json.loads(assistant_response.strip())
        except json.JSONDecodeError as e:
            return _create_error_result(f"Invalid JSON in assistant response: {str(e)}")
        
        # Validate required fields
        if not _validate_response_data(response_data):
            return _create_error_result("Missing required fields (action, reasoning, support) in response")
        
        # Extract prediction data
        predicted_action = response_data.get("action", "").lower()
        
        # Get ground truth from kwargs
        ground_truth = kwargs.get("ground_truth", {})
        if not ground_truth:
            return _create_error_result("No ground_truth provided in context")
        
        # Extract ground truth data
        actual_return = ground_truth.get("actual_return_pct")
        if actual_return is None:
            return _create_error_result("Missing actual_return_pct in ground_truth")
        
        # Get metadata for historical returns
        metadata = kwargs.get("metadata", {})
        historical_returns = metadata.get("historical_returns", [])
        ticker = metadata.get("ticker", "UNKNOWN")
        
        # Calculate directional accuracy
        is_correct = _is_directionally_correct(predicted_action, actual_return)
        directional_score = 1.0 if is_correct else 0.0
        
        # Calculate Sharpe ratio score
        sharpe_ratio = _calculate_sharpe_ratio(historical_returns)
        sharpe_score = _normalize_sharpe_ratio(sharpe_ratio)
        
        # Calculate weighted reward score
        directional_weight = DIRECTIONAL_ACCURACY_WEIGHT / 100.0
        sharpe_weight = SHARPE_RATIO_WEIGHT / 100.0
        
        reward_score = (
            directional_score * directional_weight +
            sharpe_score * sharpe_weight
        )
        
        # Ensure score is in [0, 1]
        reward_score = max(0.0, min(1.0, reward_score))
        
        # Create detailed metrics
        metrics = {
            "directional_accuracy": MetricResult(
                score=directional_score,
                success=is_correct,
                reason=f"{'Correct' if is_correct else 'Incorrect'}: {predicted_action} vs {actual_return:+.2f}% return"
            ),
            "sharpe_score": MetricResult(
                score=sharpe_score,
                success=sharpe_score > 0.5,
                reason=f"Sharpe ratio: {sharpe_ratio:.3f} (based on {len(historical_returns)} returns)"
            ),
            "actual_return": MetricResult(
                score=min(1.0, max(0.0, (actual_return + 10.0) / 20.0)),  # Normalize -10% to +10% ? 0 to 1
                reason=f"Actual return: {actual_return:+.2f}%",
                success=actual_return >= 0.0
            ),
            "predicted_action": MetricResult(
                score=_action_confidence_score(predicted_action),
                reason=f"Predicted action: {predicted_action}",
                success=True  # Always successful if we got a valid action
            )
        }
        
        # Create reason for overall score
        directional_status = "? Correct" if is_correct else "? Incorrect"
        
        reason = (
            f"Reward: {reward_score:.3f} | "
            f"Dir: {directional_status} ({directional_score:.1f}) | "
            f"Sharpe: {sharpe_ratio:.3f} ({sharpe_score:.3f}) | "
            f"{predicted_action} ? {actual_return:+.2f}%"
        )
        
        return EvaluateResult(
            score=reward_score,
            reason=reason,
            metrics=metrics
        )
        
    except Exception as e:
        return _create_error_result(f"Internal error: {str(e)}")


def _extract_assistant_response(messages: List[Dict[str, str]]) -> Optional[str]:
    """Extract the assistant response from messages."""
    for message in reversed(messages):  # Check last message first
        if message.get("role") == "assistant":
            return message.get("content", "")
    return None


def _validate_response_data(response_data: Dict[str, Any]) -> bool:
    """Validate that response data has required fields."""
    required_fields = ["action", "reasoning", "support"]
    return all(field in response_data for field in required_fields)


def _is_directionally_correct(predicted_action: str, actual_return: float) -> bool:
    """
    Check if the predicted action is directionally correct based on actual return.
    
    Thresholds:
    - strong_buy: >= 3%
    - buy: >= 2%
    - hold: -2% to 2%
    - sell: <= -2%
    - strong_sell: <= -3%
    """
    action = predicted_action.lower()
    
    if action == "strong_buy":
        return actual_return >= STRONG_BUY_THRESHOLD
    elif action == "buy":
        return actual_return >= BUY_THRESHOLD
    elif action == "hold":
        return HOLD_THRESHOLD_LOW <= actual_return <= HOLD_THRESHOLD_HIGH
    elif action == "sell":
        return actual_return <= SELL_THRESHOLD
    elif action == "strong_sell":
        return actual_return <= STRONG_SELL_THRESHOLD
    else:
        return False


def _calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from a list of returns.
    
    Sharpe Ratio = (mean_return - risk_free_rate) / std_dev_return
    
    Args:
        returns: List of historical returns
        risk_free_rate: Risk-free rate (default 0%)
        
    Returns:
        Sharpe ratio, or 0.0 if cannot be calculated
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    # Calculate mean
    mean_return = sum(returns) / len(returns)
    
    # Calculate standard deviation
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    
    # Avoid division by zero
    if std_dev == 0:
        return 0.0
    
    sharpe = (mean_return - risk_free_rate) / std_dev
    return sharpe


def _normalize_sharpe_ratio(sharpe_ratio: float) -> float:
    """
    Normalize Sharpe ratio to a 0-1 score.
    
    Uses sigmoid-like normalization:
    - Sharpe < 0: Score approaches 0
    - Sharpe = 0: Score = 0.5
    - Sharpe = 1: Score ? 0.73
    - Sharpe = 2: Score ? 0.88
    - Sharpe > 3: Score approaches 1
    
    Formula: score = 1 / (1 + exp(-sharpe))
    """
    # Sigmoid normalization
    import math
    try:
        score = 1.0 / (1.0 + math.exp(-sharpe_ratio))
    except OverflowError:
        # Handle extreme values
        score = 1.0 if sharpe_ratio > 0 else 0.0
    
    return score


def _action_confidence_score(action: str) -> float:
    """
    Assign a confidence score based on action strength.
    
    Strong signals (strong_buy, strong_sell) get higher scores.
    """
    action = action.lower()
    confidence_map = {
        "strong_buy": 1.0,
        "buy": 0.75,
        "hold": 0.5,
        "sell": 0.75,
        "strong_sell": 1.0
    }
    return confidence_map.get(action, 0.5)


def _create_error_result(error_message: str) -> EvaluateResult:
    """Create an error result with score 0.0."""
    return EvaluateResult(
        score=0.0,
        reason=f"Error: {error_message}",
        metrics={
            "error": MetricResult(
                score=0.0,
                reason=error_message,
                success=False
            )
        }
    )


# Export the reward function
__all__ = ["stock_prediction_reward"]
