"""
RLVR Reward Function Implementation

This module implements the verifiable reward function for RLVR training using
Fireworks AI's reward-kit framework. The reward function combines directional
accuracy (80%) and Sharpe ratio (20%) to provide a comprehensive evaluation
of stock prediction performance.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from reward_kit import reward_function, EvaluateResult, MetricResult
from sqlalchemy.orm import Session

from rlvr.performance_calculator import PerformanceCalculator
from data_collection.database_manager import DatabaseManager
from orchestration.config_manager import config

# Configure logging
logger = logging.getLogger(__name__)


@reward_function(id="stock-prediction-evaluator")
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
        if not assistant_response:
            return _create_error_result("No assistant response found in messages")
        
        # Parse JSON response
        try:
            response_data = json.loads(assistant_response)
        except json.JSONDecodeError as e:
            return _create_error_result(f"Invalid JSON in assistant response: {str(e)}")
        
        # Validate required fields
        if not _validate_response_data(response_data):
            return _create_error_result("Missing required fields in response data")
        
        # Extract prediction data
        predicted_action = response_data.get("action", "").lower()
        reasoning = response_data.get("reasoning", "")
        support = response_data.get("support", "")
        
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
        
        # Initialize performance calculator
        db_manager = DatabaseManager(config.DB_URL)
        session = db_manager.get_session()
        
        try:
            calculator = PerformanceCalculator(
                db_session=session,
                directional_weight=config.DIRECTIONAL_ACCURACY_WEIGHT / 100.0,
                sharpe_weight=config.SHARPE_RATIO_WEIGHT / 100.0,
                strong_buy_threshold=config.STRONG_BUY_THRESHOLD,
                buy_threshold=config.BUY_THRESHOLD,
                hold_threshold_low=config.HOLD_THRESHOLD_LOW,
                hold_threshold_high=config.HOLD_THRESHOLD_HIGH,
                sell_threshold=config.SELL_THRESHOLD,
                strong_sell_threshold=config.STRONG_SELL_THRESHOLD
            )
            
            # Calculate reward score
            reward_data = calculator.calculate_reward_score(
                predicted_action=predicted_action,
                actual_return=actual_return,
                historical_returns=historical_returns
            )
            
            # Extract components
            reward_score = reward_data["reward_score"]
            directional_score = reward_data["directional_score"]
            sharpe_score = reward_data["sharpe_score"]
            is_correct = reward_data["is_correct"]
            sharpe_ratio = reward_data["sharpe_ratio"]
            
            # Create detailed metrics
            metrics = {
                "directional_accuracy": MetricResult(
                    score=directional_score,
                    reason=f"Directional accuracy: {'Correct' if is_correct else 'Incorrect'} "
                           f"({predicted_action} vs {actual_return:+.2f}% return)"
                ),
                "sharpe_score": MetricResult(
                    score=sharpe_score,
                    reason=f"Sharpe ratio: {sharpe_ratio:.3f} "
                           f"(based on {len(historical_returns)} historical returns)"
                ),
                "actual_return": MetricResult(
                    score=min(1.0, max(0.0, actual_return / 10.0)),  # Normalize return to 0-1
                    reason=f"Actual return: {actual_return:+.2f}%"
                ),
                "predicted_action": MetricResult(
                    score=1.0 if predicted_action in ['strong_buy', 'buy'] else 0.5 if predicted_action == 'hold' else 0.0,
                    reason=f"Predicted action: {predicted_action}"
                ),
                "historical_returns_count": MetricResult(
                    score=min(1.0, len(historical_returns) / 10.0),  # Normalize count to 0-1
                    reason=f"Historical returns available: {len(historical_returns)}"
                )
            }
            
            # Create reason for overall score
            reason = _create_score_reason(
                reward_score, directional_score, sharpe_score, 
                is_correct, predicted_action, actual_return, sharpe_ratio
            )
            
            return EvaluateResult(
                score=reward_score,
                is_score_valid=True,
                reason=reason,
                metrics=metrics
            )
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in reward function: {str(e)}", exc_info=True)
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


def _create_error_result(error_message: str) -> EvaluateResult:
    """Create an error result with score 0.0."""
    return EvaluateResult(
        score=0.0,
        is_score_valid=False,
        reason=f"Error: {error_message}",
        metrics={
            "error": MetricResult(
                score=0.0,
                reason=error_message
            )
        }
    )


def _create_score_reason(
    reward_score: float,
    directional_score: float,
    sharpe_score: float,
    is_correct: bool,
    predicted_action: str,
    actual_return: float,
    sharpe_ratio: float
) -> str:
    """Create a detailed reason for the reward score."""
    directional_status = "✓ Correct" if is_correct else "✗ Incorrect"
    sharpe_status = f"Sharpe {sharpe_ratio:.3f}" if sharpe_ratio > 0 else "No Sharpe data"
    
    return (
        f"Reward Score: {reward_score:.3f} | "
        f"Directional: {directional_status} ({directional_score:.1f}) | "
        f"Sharpe: {sharpe_status} ({sharpe_score:.3f}) | "
        f"Action: {predicted_action} | Return: {actual_return:+.2f}%"
    )


# Export the reward function for use in reward-kit
__all__ = ["stock_prediction_reward"]