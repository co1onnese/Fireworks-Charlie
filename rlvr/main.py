"""
Entry point for stock prediction reward function deployment.

This file is required by reward-kit for Fireworks AI deployment.
"""
from typing import Dict, List, Optional
from reward_kit import EvaluateResult
from rlvr.reward_function import stock_prediction_reward

# Export the reward function as the main entry point
__all__ = ["evaluate"]


def evaluate(
    messages: List[Dict[str, str]],
    original_messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
) -> EvaluateResult:
    """
    Top-level evaluate function required by Fireworks AI.

    This wraps the stock_prediction_reward function for deployment.
    """
    return stock_prediction_reward(
        messages=messages,
        original_messages=original_messages,
        **kwargs
    )
