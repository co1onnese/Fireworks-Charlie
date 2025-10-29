"""
Tests for the reward function implementation.
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.reward_function import stock_prediction_reward


class TestRewardFunction:
    """Test cases for the reward function."""
    
    def test_correct_buy_prediction(self):
        """Test reward function with correct buy prediction."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Strong fundamentals",
                "action": "buy",
                "support": "Revenue growth"
            })}
        ]
        
        ground_truth = {
            "actual_return_pct": 2.5,
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        assert result.score > 0.7  # Should be high for correct prediction
        assert result.is_score_valid is True
        assert "Correct" in result.reason
        assert len(result.metrics) > 0
    
    def test_incorrect_sell_prediction(self):
        """Test reward function with incorrect sell prediction."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Market concerns",
                "action": "sell",
                "support": "Overvaluation"
            })}
        ]
        
        ground_truth = {
            "actual_return_pct": 3.0,  # Positive return (incorrect sell)
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        assert result.score < 0.3  # Should be low for incorrect prediction
        assert result.is_score_valid is True
        assert "Incorrect" in result.reason
    
    def test_invalid_json_response(self):
        """Test reward function with invalid JSON response."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": "Invalid JSON response"}
        ]
        
        ground_truth = {
            "actual_return_pct": 2.5,
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        assert result.score == 0.0
        assert result.is_score_valid is False
        assert "Invalid JSON" in result.reason
    
    def test_missing_ground_truth(self):
        """Test reward function with missing ground truth."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Strong fundamentals",
                "action": "buy",
                "support": "Revenue growth"
            })}
        ]
        
        result = stock_prediction_reward(messages=messages)
        
        assert result.score == 0.0
        assert result.is_score_valid is False
        assert "ground_truth" in result.reason
    
    def test_missing_assistant_response(self):
        """Test reward function with no assistant response."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."}
        ]
        
        ground_truth = {
            "actual_return_pct": 2.5,
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth
        )
        
        assert result.score == 0.0
        assert result.is_score_valid is False
        assert "No assistant response" in result.reason
    
    def test_hold_prediction_with_small_return(self):
        """Test reward function with correct hold prediction."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Stable performance",
                "action": "hold",
                "support": "Moderate growth"
            })}
        ]
        
        ground_truth = {
            "actual_return_pct": 0.5,  # Small return (correct hold)
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        assert result.score > 0.7  # Should be high for correct hold
        assert result.is_score_valid is True
        assert "Correct" in result.reason
    
    def test_strong_sell_prediction_with_negative_return(self):
        """Test reward function with correct strong sell prediction."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Market downturn",
                "action": "strong_sell",
                "support": "Economic concerns"
            })}
        ]
        
        ground_truth = {
            "actual_return_pct": -4.0,  # Large negative return (correct strong sell)
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        assert result.score > 0.7  # Should be high for correct strong sell
        assert result.is_score_valid is True
        assert "Correct" in result.reason
    
    def test_metrics_structure(self):
        """Test that metrics are properly structured."""
        messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Strong fundamentals",
                "action": "buy",
                "support": "Revenue growth"
            })}
        ]
        
        ground_truth = {
            "actual_return_pct": 2.5,
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False
        }
        
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Check metrics structure
        assert isinstance(result.metrics, dict)
        assert "directional_accuracy" in result.metrics
        assert "sharpe_score" in result.metrics
        assert "actual_return" in result.metrics
        assert "predicted_action" in result.metrics
        assert "historical_returns_count" in result.metrics
        
        # Check metric values are in valid range
        for name, metric in result.metrics.items():
            assert 0.0 <= metric.score <= 1.0, f"Metric {name} score out of range: {metric.score}"
            assert isinstance(metric.reason, str), f"Metric {name} reason should be string"
    
    def test_score_range(self):
        """Test that scores are in valid range [0.0, 1.0]."""
        test_cases = [
            ("buy", 2.5, "correct buy"),
            ("sell", 3.0, "incorrect sell"),
            ("hold", 0.5, "correct hold"),
            ("strong_buy", -1.5, "incorrect strong buy"),
            ("strong_sell", -4.0, "correct strong sell")
        ]
        
        for action, return_pct, description in test_cases:
            messages = [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."},
                {"role": "assistant", "content": json.dumps({
                    "reasoning": f"Analysis for {description}",
                    "action": action,
                    "support": f"Evidence for {description}"
                })}
            ]
            
            ground_truth = {
                "actual_return_pct": return_pct,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            }
            
            metadata = {
                "ticker": "AAPL",
                "entry_date": "2024-01-02",
                "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
            }
            
            result = stock_prediction_reward(
                messages=messages,
                ground_truth=ground_truth,
                metadata=metadata
            )
            
            assert 0.0 <= result.score <= 1.0, f"Score out of range for {description}: {result.score}"
            assert result.is_score_valid is True, f"Score should be valid for {description}"


if __name__ == "__main__":
    pytest.main([__file__])