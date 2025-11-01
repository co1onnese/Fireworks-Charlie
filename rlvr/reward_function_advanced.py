"""
Advanced RLVR Reward Function - Sophisticated Multi-Metric Evaluation

This reward function implements a hierarchical, multi-metric evaluation system
that goes beyond simple directional accuracy to provide nuanced feedback.

Evaluation Components:
1. Directional Accuracy (40%) - Is the direction correct?
2. Magnitude Accuracy (25%) - How close is the prediction to actual return?
3. Risk-Adjusted Performance (20%) - Sharpe ratio consideration
4. Confidence Calibration (10%) - Are strong signals more accurate?
5. Downside Protection (5%) - Extra penalty for large losses

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import json
import math
from typing import Dict, List, Optional, Any

from reward_kit import reward_function, EvaluateResult, MetricResult


# Constants
DIRECTIONAL_WEIGHT = 0.40
MAGNITUDE_WEIGHT = 0.25
SHARPE_WEIGHT = 0.20
CALIBRATION_WEIGHT = 0.10
DOWNSIDE_WEIGHT = 0.05

# Action thresholds
STRONG_BUY_THRESHOLD = 3.0
BUY_THRESHOLD = 2.0
HOLD_THRESHOLD_LOW = -2.0
HOLD_THRESHOLD_HIGH = 2.0
SELL_THRESHOLD = -2.0
STRONG_SELL_THRESHOLD = -3.0

# Confidence levels by action
ACTION_CONFIDENCE = {
    'strong_buy': 1.0,
    'strong_sell': 1.0,
    'buy': 0.75,
    'sell': 0.75,
    'hold': 0.5
}


@reward_function
def stock_prediction_reward(
    messages: List[Dict[str, str]],
    original_messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
) -> EvaluateResult:
    """
    Advanced reward function with multi-metric hierarchical evaluation.
    
    Evaluation Hierarchy:
    Level 1: Format validation (pass/fail)
    Level 2: Action reasonableness (0.0-1.0)
    Level 3: Directional accuracy (0.0-1.0)
    Level 4: Magnitude accuracy (0.0-1.0)
    Level 5: Risk and calibration (0.0-1.0)
    
    Args:
        messages: Conversation messages
        original_messages: Original messages (unused)
        **kwargs: ground_truth and metadata
        
    Returns:
        EvaluateResult with detailed component scores
    """
    try:
        # Level 1: Format Validation
        assistant_response = _extract_assistant_response(messages)
        if not assistant_response:
            return _create_error_result("No assistant response found")
        
        try:
            response_data = json.loads(assistant_response)
        except json.JSONDecodeError as e:
            return _create_error_result(f"Invalid JSON: {str(e)}")
        
        if not _validate_response_data(response_data):
            return _create_error_result("Missing required fields (action, reasoning, support)")
        
        # Extract data
        predicted_action = response_data.get("action", "").lower()
        reasoning = response_data.get("reasoning", "")
        support = response_data.get("support", "")
        
        ground_truth = kwargs.get("ground_truth", {})
        if not ground_truth:
            return _create_error_result("No ground_truth provided")
        
        actual_return = ground_truth.get("actual_return_pct")
        if actual_return is None:
            return _create_error_result("Missing actual_return_pct")
        
        metadata = kwargs.get("metadata", {})
        historical_returns = metadata.get("historical_returns", [])
        
        # Level 2: Action Reasonableness
        reasonableness_score = _evaluate_action_reasonableness(
            predicted_action, reasoning, support
        )
        
        # Level 3: Directional Accuracy
        is_correct = _is_directionally_correct(predicted_action, actual_return)
        directional_score = 1.0 if is_correct else 0.0
        
        # Level 4: Magnitude Accuracy
        magnitude_score = _calculate_magnitude_accuracy(
            predicted_action, actual_return
        )
        
        # Level 5: Risk-Adjusted and Calibration
        sharpe_ratio = _calculate_sharpe_ratio(historical_returns)
        sharpe_score = _normalize_sharpe_ratio(sharpe_ratio)
        
        calibration_score = _calculate_confidence_calibration(
            predicted_action, actual_return, is_correct
        )
        
        downside_penalty = _calculate_downside_penalty(
            predicted_action, actual_return
        )
        
        # Combine scores with weights
        component_scores = {
            'directional': directional_score * DIRECTIONAL_WEIGHT,
            'magnitude': magnitude_score * MAGNITUDE_WEIGHT,
            'sharpe': sharpe_score * SHARPE_WEIGHT,
            'calibration': calibration_score * CALIBRATION_WEIGHT,
            'downside': (1.0 - downside_penalty) * DOWNSIDE_WEIGHT
        }
        
        # Calculate final reward
        reward_score = sum(component_scores.values())
        
        # Apply reasonableness multiplier (0.5-1.0)
        reward_score *= (0.5 + 0.5 * reasonableness_score)
        
        # Ensure in [0, 1]
        reward_score = max(0.0, min(1.0, reward_score))
        
        # Create detailed metrics
        metrics = {
            "directional_accuracy": MetricResult(
                score=directional_score,
                reason=f"{'? Correct' if is_correct else '? Incorrect'}: {predicted_action} vs {actual_return:+.2f}%",
                success=is_correct
            ),
            "magnitude_accuracy": MetricResult(
                score=magnitude_score,
                reason=f"Magnitude error: {_calculate_prediction_error(predicted_action, actual_return):.2f}%",
                success=magnitude_score >= 0.7
            ),
            "sharpe_score": MetricResult(
                score=sharpe_score,
                reason=f"Sharpe ratio: {sharpe_ratio:.3f} ({len(historical_returns)} returns)",
                success=sharpe_score >= 0.5
            ),
            "confidence_calibration": MetricResult(
                score=calibration_score,
                reason=f"Calibration: {'well-calibrated' if calibration_score > 0.7 else 'needs improvement'}",
                success=calibration_score >= 0.7
            ),
            "downside_protection": MetricResult(
                score=1.0 - downside_penalty,
                reason=f"Downside risk: {downside_penalty:.2%} penalty"
            ),
            "reasoning_quality": MetricResult(
                score=reasonableness_score,
                reason=f"Reasoning: {len(reasoning)} chars, support: {len(support)} chars",
                success=reasonableness_score >= 0.6
            )
        }
        
        # Create comprehensive reason
        reason = _create_detailed_reason(
            reward_score, predicted_action, actual_return, is_correct,
            magnitude_score, sharpe_ratio, calibration_score
        )
        
        return EvaluateResult(
            score=reward_score,
            reason=reason,
            metrics=metrics
        )
        
    except Exception as e:
        return _create_error_result(f"Internal error: {str(e)}")


def _extract_assistant_response(messages: List[Dict[str, str]]) -> Optional[str]:
    """Extract assistant response from messages."""
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return message.get("content", "")
    return None


def _validate_response_data(response_data: Dict[str, Any]) -> bool:
    """Validate required fields."""
    return all(field in response_data for field in ["action", "reasoning", "support"])


def _evaluate_action_reasonableness(
    action: str,
    reasoning: str,
    support: str
) -> float:
    """
    Evaluate if the action seems reasonable based on reasoning quality.
    
    This is a basic heuristic check, not a full NLP analysis.
    """
    score = 0.0
    
    # Check reasoning length (should be substantial)
    if len(reasoning) >= 100:
        score += 0.3
    elif len(reasoning) >= 50:
        score += 0.15
    
    # Check support length
    if len(support) >= 50:
        score += 0.2
    elif len(support) >= 25:
        score += 0.1
    
    # Check for key financial terms
    financial_terms = [
        'price', 'trend', 'momentum', 'support', 'resistance',
        'volume', 'rsi', 'moving average', 'earnings', 'revenue',
        'growth', 'valuation', 'p/e', 'fundamental', 'technical'
    ]
    
    combined_text = (reasoning + " " + support).lower()
    term_count = sum(1 for term in financial_terms if term in combined_text)
    
    if term_count >= 3:
        score += 0.3
    elif term_count >= 2:
        score += 0.2
    elif term_count >= 1:
        score += 0.1
    
    # Check for specific data references (numbers, percentages)
    import re
    if re.search(r'\d+\.?\d*%', combined_text):  # Has percentage
        score += 0.1
    if re.search(r'\$\d+', combined_text):  # Has dollar amount
        score += 0.1
    
    return min(1.0, score)


def _is_directionally_correct(predicted_action: str, actual_return: float) -> bool:
    """Check if prediction is directionally correct."""
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


def _calculate_magnitude_accuracy(predicted_action: str, actual_return: float) -> float:
    """
    Calculate how close the predicted magnitude is to actual return.
    
    Maps predicted action to expected return range, then calculates error.
    """
    # Map action to expected return
    action = predicted_action.lower()
    
    if action == "strong_buy":
        predicted_return = 4.0  # Expect strong gains
    elif action == "buy":
        predicted_return = 2.5  # Expect moderate gains
    elif action == "hold":
        predicted_return = 0.0  # Expect neutral
    elif action == "sell":
        predicted_return = -2.5  # Expect moderate losses
    elif action == "strong_sell":
        predicted_return = -4.0  # Expect strong losses
    else:
        predicted_return = 0.0
    
    # Calculate error
    error = abs(predicted_return - actual_return)
    
    # Score using exponential decay (error of 0 = score 1.0, larger errors decay)
    # Score = exp(-error / 5)
    # At error=5%, score ? 0.37; at error=10%, score ? 0.14
    score = math.exp(-error / 5.0)
    
    return score


def _calculate_prediction_error(predicted_action: str, actual_return: float) -> float:
    """Calculate absolute prediction error for display."""
    action = predicted_action.lower()
    
    action_expectations = {
        "strong_buy": 4.0,
        "buy": 2.5,
        "hold": 0.0,
        "sell": -2.5,
        "strong_sell": -4.0
    }
    
    predicted_return = action_expectations.get(action, 0.0)
    return abs(predicted_return - actual_return)


def _calculate_confidence_calibration(
    predicted_action: str,
    actual_return: float,
    is_correct: bool
) -> float:
    """
    Evaluate if model's confidence (action strength) is calibrated.
    
    Strong signals (strong_buy/strong_sell) should be more accurate than
    weak signals (buy/sell), and hold should be for uncertain cases.
    """
    action = predicted_action.lower()
    confidence = ACTION_CONFIDENCE.get(action, 0.5)
    
    # If correct and high confidence: good calibration
    # If correct and low confidence: acceptable
    # If incorrect and high confidence: bad calibration (overconfident)
    # If incorrect and low confidence: acceptable (appropriately uncertain)
    
    if is_correct:
        # Reward high confidence when correct
        return 0.5 + 0.5 * confidence
    else:
        # Penalize high confidence when wrong
        return 1.0 - confidence


def _calculate_downside_penalty(predicted_action: str, actual_return: float) -> float:
    """
    Calculate penalty for predictions that led to large losses.
    
    Extra penalty if we predicted BUY but stock crashed, or predicted
    SELL/HOLD but missed a huge gain.
    """
    action = predicted_action.lower()
    penalty = 0.0
    
    # Penalty for recommending BUY on a stock that crashed
    if action in ['buy', 'strong_buy'] and actual_return < -5.0:
        penalty = min(1.0, abs(actual_return) / 10.0)  # Cap at 1.0
    
    # Smaller penalty for missing huge gains (FOMO penalty)
    elif action in ['sell', 'strong_sell'] and actual_return > 5.0:
        penalty = min(0.5, actual_return / 20.0)  # Cap at 0.5, half as severe
    
    # Moderate penalty for holding through extremes
    elif action == 'hold':
        if abs(actual_return) > 5.0:
            penalty = min(0.3, abs(actual_return) / 30.0)  # Smaller penalty
    
    return penalty


def _calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from returns."""
    if not returns or len(returns) < 2:
        return 0.0
    
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    
    if std_dev == 0:
        return 0.0
    
    return (mean_return - risk_free_rate) / std_dev


def _normalize_sharpe_ratio(sharpe_ratio: float) -> float:
    """Normalize Sharpe ratio to [0, 1] using sigmoid."""
    try:
        return 1.0 / (1.0 + math.exp(-sharpe_ratio))
    except OverflowError:
        return 1.0 if sharpe_ratio > 0 else 0.0


def _create_detailed_reason(
    reward: float,
    action: str,
    actual_return: float,
    is_correct: bool,
    magnitude_score: float,
    sharpe: float,
    calibration: float
) -> str:
    """Create detailed reason string."""
    status = "?" if is_correct else "?"
    
    return (
        f"R:{reward:.3f} | "
        f"Dir:{status} | "
        f"Mag:{magnitude_score:.2f} | "
        f"Sharpe:{sharpe:.2f} | "
        f"Cal:{calibration:.2f} | "
        f"{action}?{actual_return:+.2f}%"
    )


def _create_error_result(error_message: str) -> EvaluateResult:
    """Create error result."""
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


__all__ = ["stock_prediction_reward"]
