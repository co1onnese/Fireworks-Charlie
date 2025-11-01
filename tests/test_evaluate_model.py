#!/usr/bin/env python3
"""
Unit tests for model evaluation script.

Tests all calculation logic without requiring API calls.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
import json
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from scripts.evaluate_model import ModelEvaluator


class TestDirectionalAccuracy:
    """Test directional accuracy calculation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_strong_buy_correct(self):
        """Test strong_buy prediction with >= 3% return."""
        assert self.evaluator.calculate_directional_accuracy("strong_buy", 3.5) is True
        assert self.evaluator.calculate_directional_accuracy("strong_buy", 3.0) is True
    
    def test_strong_buy_incorrect(self):
        """Test strong_buy prediction with < 3% return."""
        assert self.evaluator.calculate_directional_accuracy("strong_buy", 2.9) is False
        assert self.evaluator.calculate_directional_accuracy("strong_buy", 0.5) is False
    
    def test_buy_correct(self):
        """Test buy prediction with >= 2% return."""
        assert self.evaluator.calculate_directional_accuracy("buy", 2.5) is True
        assert self.evaluator.calculate_directional_accuracy("buy", 2.0) is True
    
    def test_buy_incorrect(self):
        """Test buy prediction with < 2% return."""
        assert self.evaluator.calculate_directional_accuracy("buy", 1.9) is False
        assert self.evaluator.calculate_directional_accuracy("buy", -1.0) is False
    
    def test_hold_correct(self):
        """Test hold prediction with return in [-2%, 2%] range."""
        assert self.evaluator.calculate_directional_accuracy("hold", 1.5) is True
        assert self.evaluator.calculate_directional_accuracy("hold", 0.0) is True
        assert self.evaluator.calculate_directional_accuracy("hold", -1.5) is True
        assert self.evaluator.calculate_directional_accuracy("hold", 2.0) is True
        assert self.evaluator.calculate_directional_accuracy("hold", -2.0) is True
    
    def test_hold_incorrect(self):
        """Test hold prediction with return outside [-2%, 2%] range."""
        assert self.evaluator.calculate_directional_accuracy("hold", 2.1) is False
        assert self.evaluator.calculate_directional_accuracy("hold", -2.1) is False
        assert self.evaluator.calculate_directional_accuracy("hold", 5.0) is False
    
    def test_sell_correct(self):
        """Test sell prediction with <= -2% return."""
        assert self.evaluator.calculate_directional_accuracy("sell", -2.5) is True
        assert self.evaluator.calculate_directional_accuracy("sell", -2.0) is True
    
    def test_sell_incorrect(self):
        """Test sell prediction with > -2% return."""
        assert self.evaluator.calculate_directional_accuracy("sell", -1.9) is False
        assert self.evaluator.calculate_directional_accuracy("sell", 1.0) is False
    
    def test_strong_sell_correct(self):
        """Test strong_sell prediction with <= -3% return."""
        assert self.evaluator.calculate_directional_accuracy("strong_sell", -3.5) is True
        assert self.evaluator.calculate_directional_accuracy("strong_sell", -3.0) is True
    
    def test_strong_sell_incorrect(self):
        """Test strong_sell prediction with > -3% return."""
        assert self.evaluator.calculate_directional_accuracy("strong_sell", -2.9) is False
        assert self.evaluator.calculate_directional_accuracy("strong_sell", 0.5) is False
    
    def test_case_insensitive(self):
        """Test that action matching is case-insensitive."""
        assert self.evaluator.calculate_directional_accuracy("BUY", 2.5) is True
        assert self.evaluator.calculate_directional_accuracy("Buy", 2.5) is True
        assert self.evaluator.calculate_directional_accuracy("STRONG_BUY", 3.5) is True


class TestPortfolioReturnStrategyB:
    """Test portfolio return calculation for Strategy B (Long/short)."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_buy_long_position(self):
        """Test that BUY signal takes long position."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("buy", 2.5)
        assert result == 2.5
    
    def test_strong_buy_long_position(self):
        """Test that STRONG_BUY signal takes long position."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("strong_buy", 3.5)
        assert result == 3.5
    
    def test_sell_short_position(self):
        """Test that SELL signal takes short position (inverted return)."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("sell", -2.5)
        assert result == 2.5  # Short benefits from negative return
    
    def test_strong_sell_short_position(self):
        """Test that STRONG_SELL signal takes short position (inverted return)."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("strong_sell", -3.5)
        assert result == 3.5  # Short benefits from negative return
    
    def test_hold_no_position(self):
        """Test that HOLD signal takes no position."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("hold", 1.5)
        assert result == 0.0
    
    def test_short_on_positive_return_loses_money(self):
        """Test that shorting on positive return loses money."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("sell", 2.5)
        assert result == -2.5  # Short loses when stock goes up
    
    def test_long_on_negative_return_loses_money(self):
        """Test that going long on negative return loses money."""
        result = self.evaluator.calculate_portfolio_return_strategy_b("buy", -2.5)
        assert result == -2.5  # Long loses when stock goes down
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        result1 = self.evaluator.calculate_portfolio_return_strategy_b("BUY", 2.5)
        result2 = self.evaluator.calculate_portfolio_return_strategy_b("buy", 2.5)
        result3 = self.evaluator.calculate_portfolio_return_strategy_b("SELL", 2.5)
        result4 = self.evaluator.calculate_portfolio_return_strategy_b("sell", 2.5)
        assert result1 == result2 == 2.5
        assert result3 == result4 == -2.5


class TestPortfolioReturnStrategyC:
    """Test portfolio return calculation for Strategy C (Weighted)."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_strong_buy_2x_leverage(self):
        """Test that STRONG_BUY uses 2x leverage."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("strong_buy", 3.5)
        assert result == 7.0  # 2 ? 3.5
    
    def test_buy_1x_position(self):
        """Test that BUY uses 1x position."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("buy", 2.5)
        assert result == 2.5  # 1 ? 2.5
    
    def test_hold_no_position(self):
        """Test that HOLD uses no position."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("hold", 1.5)
        assert result == 0.0  # 0 ? 1.5
    
    def test_sell_1x_short(self):
        """Test that SELL uses -1x position (short)."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("sell", -2.5)
        assert result == 2.5  # -1 ? -2.5 = 2.5
    
    def test_strong_sell_2x_short(self):
        """Test that STRONG_SELL uses -2x position (double short)."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("strong_sell", -3.5)
        assert result == 7.0  # -2 ? -3.5 = 7.0
    
    def test_strong_buy_on_negative_return(self):
        """Test that STRONG_BUY doubles losses on negative returns."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("strong_buy", -3.0)
        assert result == -6.0  # 2 ? -3.0
    
    def test_strong_sell_on_positive_return(self):
        """Test that STRONG_SELL doubles losses on positive returns."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("strong_sell", 3.0)
        assert result == -6.0  # -2 ? 3.0
    
    def test_sell_profits_from_decline(self):
        """Test that SELL profits when stock declines."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("sell", -2.0)
        assert result == 2.0  # -1 ? -2.0
    
    def test_all_weights(self):
        """Test all action weights with same return."""
        test_return = 2.0
        
        strong_buy = self.evaluator.calculate_portfolio_return_strategy_c("strong_buy", test_return)
        buy = self.evaluator.calculate_portfolio_return_strategy_c("buy", test_return)
        hold = self.evaluator.calculate_portfolio_return_strategy_c("hold", test_return)
        sell = self.evaluator.calculate_portfolio_return_strategy_c("sell", test_return)
        strong_sell = self.evaluator.calculate_portfolio_return_strategy_c("strong_sell", test_return)
        
        assert strong_buy == 4.0   # 2 ? 2.0
        assert buy == 2.0          # 1 ? 2.0
        assert hold == 0.0         # 0 ? 2.0
        assert sell == -2.0        # -1 ? 2.0
        assert strong_sell == -4.0 # -2 ? 2.0
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        result1 = self.evaluator.calculate_portfolio_return_strategy_c("STRONG_BUY", 2.0)
        result2 = self.evaluator.calculate_portfolio_return_strategy_c("strong_buy", 2.0)
        assert result1 == result2 == 4.0
    
    def test_unknown_action_returns_zero(self):
        """Test that unknown action returns zero."""
        result = self.evaluator.calculate_portfolio_return_strategy_c("unknown", 2.5)
        assert result == 0.0


class TestPortfolioReturnStrategyA:
    """Test portfolio return calculation for Strategy A (Long-only)."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_buy_takes_position(self):
        """Test that BUY signal takes full position."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("buy", 2.5)
        assert result == 2.5
    
    def test_strong_buy_takes_position(self):
        """Test that STRONG_BUY signal takes full position."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("strong_buy", 3.5)
        assert result == 3.5
    
    def test_hold_no_position(self):
        """Test that HOLD signal takes no position."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("hold", 1.5)
        assert result == 0.0
    
    def test_sell_no_position(self):
        """Test that SELL signal takes no position."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("sell", -2.5)
        assert result == 0.0
    
    def test_strong_sell_no_position(self):
        """Test that STRONG_SELL signal takes no position."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("strong_sell", -3.5)
        assert result == 0.0
    
    def test_negative_return_on_buy(self):
        """Test that negative returns are captured on BUY signals."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("buy", -1.5)
        assert result == -1.5
    
    def test_positive_return_on_sell_ignored(self):
        """Test that positive returns on SELL are ignored (no position)."""
        result = self.evaluator.calculate_portfolio_return_strategy_a("sell", 2.5)
        assert result == 0.0
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        result1 = self.evaluator.calculate_portfolio_return_strategy_a("BUY", 2.5)
        result2 = self.evaluator.calculate_portfolio_return_strategy_a("buy", 2.5)
        assert result1 == result2 == 2.5


class TestSharpeRatio:
    """Test Sharpe Ratio calculation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_positive_sharpe(self):
        """Test Sharpe ratio with positive returns."""
        returns = [2.0, 3.0, 1.5, 2.5, 3.5]
        sharpe = self.evaluator.calculate_sharpe_ratio(returns)
        
        # Manual calculation
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        expected_sharpe = mean_return / std_return
        
        assert abs(sharpe - expected_sharpe) < 0.0001
    
    def test_negative_sharpe(self):
        """Test Sharpe ratio with negative returns."""
        returns = [-2.0, -3.0, -1.5, -2.5, -3.5]
        sharpe = self.evaluator.calculate_sharpe_ratio(returns)
        
        # Should be negative
        assert sharpe < 0
    
    def test_mixed_returns(self):
        """Test Sharpe ratio with mixed positive/negative returns."""
        returns = [2.0, -1.0, 3.0, -0.5, 1.5]
        sharpe = self.evaluator.calculate_sharpe_ratio(returns)
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        expected_sharpe = mean_return / std_return
        
        assert abs(sharpe - expected_sharpe) < 0.0001
    
    def test_zero_std_returns_zero_sharpe(self):
        """Test that zero standard deviation returns zero Sharpe."""
        returns = [2.0, 2.0, 2.0, 2.0]
        sharpe = self.evaluator.calculate_sharpe_ratio(returns)
        assert sharpe == 0.0
    
    def test_empty_returns(self):
        """Test that empty returns list returns 0."""
        sharpe = self.evaluator.calculate_sharpe_ratio([])
        assert sharpe == 0.0
    
    def test_single_return(self):
        """Test that single return returns 0 (need >= 2 for std)."""
        sharpe = self.evaluator.calculate_sharpe_ratio([2.5])
        assert sharpe == 0.0
    
    def test_risk_free_rate(self):
        """Test Sharpe ratio with non-zero risk-free rate."""
        returns = [2.0, 3.0, 1.5, 2.5, 3.5]
        risk_free = 1.0
        sharpe = self.evaluator.calculate_sharpe_ratio(returns, risk_free)
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        expected_sharpe = (mean_return - risk_free) / std_return
        
        assert abs(sharpe - expected_sharpe) < 0.0001


class TestParsePrediction:
    """Test prediction parsing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_valid_prediction(self):
        """Test parsing valid prediction JSON."""
        json_str = json.dumps({
            "action": "buy",
            "reasoning": "Technical analysis shows upward trend",
            "support": "RSI at 65, moving averages bullish"
        })
        
        prediction = self.evaluator.parse_prediction(json_str)
        assert prediction is not None
        assert prediction['action'] == "buy"
        assert 'reasoning' in prediction
        assert 'support' in prediction
    
    def test_missing_action(self):
        """Test that missing action field returns None."""
        json_str = json.dumps({
            "reasoning": "Some reasoning",
            "support": "Some support"
        })
        
        prediction = self.evaluator.parse_prediction(json_str)
        assert prediction is None
    
    def test_invalid_json(self):
        """Test that invalid JSON returns None."""
        invalid_json = "This is not JSON"
        prediction = self.evaluator.parse_prediction(invalid_json)
        assert prediction is None
    
    def test_empty_string(self):
        """Test that empty string returns None."""
        prediction = self.evaluator.parse_prediction("")
        assert prediction is None
    
    def test_none_input(self):
        """Test that None input returns None."""
        prediction = self.evaluator.parse_prediction(None)
        assert prediction is None
    
    def test_extra_fields_preserved(self):
        """Test that extra fields are preserved."""
        json_str = json.dumps({
            "action": "buy",
            "reasoning": "Test",
            "support": "Test",
            "extra_field": "Extra data"
        })
        
        prediction = self.evaluator.parse_prediction(json_str)
        assert prediction is not None
        assert prediction['extra_field'] == "Extra data"


class TestActionStatistics:
    """Test action statistics calculation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_basic_statistics(self):
        """Test basic action statistics calculation."""
        results = [
            {"predicted_action": "buy", "correct": True, "portfolio_return": 2.5},
            {"predicted_action": "buy", "correct": False, "portfolio_return": -1.0},
            {"predicted_action": "sell", "correct": True, "portfolio_return": 0.0},
            {"predicted_action": "hold", "correct": True, "portfolio_return": 0.0},
        ]
        
        stats = self.evaluator._calculate_action_statistics(results)
        
        assert stats['buy']['count'] == 2
        assert stats['buy']['correct'] == 1
        assert stats['buy']['accuracy'] == 0.5
        assert stats['sell']['count'] == 1
        assert stats['sell']['correct'] == 1
        assert stats['sell']['accuracy'] == 1.0
    
    def test_error_handling(self):
        """Test that errors are excluded from statistics."""
        results = [
            {"predicted_action": "buy", "correct": True, "portfolio_return": 2.5},
            {"error": "Some error"},
            {"predicted_action": "sell", "correct": True, "portfolio_return": 0.0},
        ]
        
        stats = self.evaluator._calculate_action_statistics(results)
        
        assert stats['buy']['count'] == 1
        assert stats['sell']['count'] == 1
        assert len(stats) == 2  # Only 2 actions, error excluded
    
    def test_return_statistics_per_action(self):
        """Test that return statistics are calculated per action."""
        results = [
            {"predicted_action": "buy", "correct": True, "portfolio_return": 2.5},
            {"predicted_action": "buy", "correct": False, "portfolio_return": -1.0},
            {"predicted_action": "buy", "correct": True, "portfolio_return": 3.0},
        ]
        
        stats = self.evaluator._calculate_action_statistics(results)
        
        assert stats['buy']['count'] == 3
        mean_return = stats['buy']['mean_portfolio_return']
        expected_mean = (2.5 + (-1.0) + 3.0) / 3
        assert abs(mean_return - expected_mean) < 0.0001


class TestReturnStatistics:
    """Test return statistics calculation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def test_portfolio_statistics(self):
        """Test portfolio statistics calculation."""
        portfolio_returns = [2.0, -1.0, 3.0, 0.0, 1.5]
        actual_returns = [2.5, -1.5, 3.5, 0.5, 1.0]
        
        stats = self.evaluator._calculate_return_statistics(
            portfolio_returns, actual_returns
        )
        
        assert 'portfolio' in stats
        assert 'actual' in stats
        
        # Check portfolio stats
        assert abs(stats['portfolio']['mean'] - np.mean(portfolio_returns)) < 0.0001
        assert abs(stats['portfolio']['median'] - np.median(portfolio_returns)) < 0.0001
        assert stats['portfolio']['min'] == -1.0
        assert stats['portfolio']['max'] == 3.0
        assert stats['portfolio']['positive_count'] == 3
        assert stats['portfolio']['negative_count'] == 1
        assert stats['portfolio']['neutral_count'] == 1
    
    def test_total_return(self):
        """Test total return calculation."""
        portfolio_returns = [2.0, 3.0, 1.5]
        actual_returns = [2.5, 3.5, 1.0]
        
        stats = self.evaluator._calculate_return_statistics(
            portfolio_returns, actual_returns
        )
        
        expected_total = sum(portfolio_returns)
        assert abs(stats['portfolio']['total_return'] - expected_total) < 0.0001
    
    def test_empty_returns(self):
        """Test that empty returns list returns empty dict."""
        stats = self.evaluator._calculate_return_statistics([], [])
        assert stats == {}


class TestMockEvaluation:
    """Test full evaluation flow with mocked API calls."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.evaluator = ModelEvaluator("test-model")
    
    def create_mock_example(
        self,
        ticker: str = "AAPL",
        entry_date: str = "2025-01-01",
        actual_return: float = 2.5,
        days_held: int = 3
    ):
        """Create a mock evaluation example."""
        return {
            "messages": [
                {"role": "system", "content": "You are a financial analyst..."},
                {"role": "user", "content": "Analyze AAPL stock..."}
            ],
            "ground_truth": {
                "actual_return_pct": actual_return,
                "exit_date": "2025-01-04",
                "days_held": days_held,
                "entry_price": 150.0,
                "exit_price": 150.0 * (1 + actual_return / 100)
            },
            "metadata": {
                "ticker": ticker,
                "entry_date": entry_date,
                "thesis_id": 123,
                "position_id": "pos_1"
            }
        }
    
    @patch('scripts.evaluate_model.ModelEvaluator.query_model')
    def test_successful_evaluation(self, mock_query):
        """Test successful evaluation of an example."""
        # Mock API response
        mock_query.return_value = {
            "content": json.dumps({
                "action": "buy",
                "reasoning": "Technical analysis positive",
                "support": "Moving averages bullish"
            }),
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        }
        
        example = self.create_mock_example(actual_return=2.5)
        result = self.evaluator.evaluate_example(example, "test-model", "A")
        
        assert result['ticker'] == "AAPL"
        assert result['predicted_action'] == "buy"
        assert result['actual_return'] == 2.5
        assert result['portfolio_return'] == 2.5  # Buy signal takes position
        assert result['correct'] is True  # 2.5% >= 2% threshold
        assert 'error' not in result
    
    @patch('scripts.evaluate_model.ModelEvaluator.query_model')
    def test_api_error_handling(self, mock_query):
        """Test handling of API errors."""
        # Mock API error
        mock_query.return_value = {
            "error": "API rate limit exceeded",
            "finish_reason": "error"
        }
        
        example = self.create_mock_example()
        result = self.evaluator.evaluate_example(example, "test-model", "A")
        
        assert 'error' in result
        assert result['correct'] is False
        assert result['portfolio_return'] == 0.0
    
    @patch('scripts.evaluate_model.ModelEvaluator.query_model')
    def test_invalid_json_response(self, mock_query):
        """Test handling of invalid JSON responses."""
        # Mock invalid JSON response
        mock_query.return_value = {
            "content": "This is not valid JSON",
            "finish_reason": "stop"
        }
        
        example = self.create_mock_example()
        result = self.evaluator.evaluate_example(example, "test-model", "A")
        
        assert 'error' in result
        assert result['error'] == "Failed to parse prediction"
    
    @patch('scripts.evaluate_model.ModelEvaluator.query_model')
    def test_hold_signal_no_position(self, mock_query):
        """Test that HOLD signal results in no position."""
        mock_query.return_value = {
            "content": json.dumps({
                "action": "hold",
                "reasoning": "Wait and see",
                "support": "Uncertainty"
            }),
            "finish_reason": "stop"
        }
        
        example = self.create_mock_example(actual_return=1.5)
        result = self.evaluator.evaluate_example(example, "test-model", "A")
        
        assert result['predicted_action'] == "hold"
        assert result['portfolio_return'] == 0.0  # No position
        assert result['correct'] is True  # 1.5% in [-2%, 2%] range


class TestDatasetValidation:
    """Test dataset validation."""
    
    def test_dev_dataset_exists(self):
        """Test that dev dataset exists."""
        dev_path = Path("/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl")
        assert dev_path.exists(), "Dev dataset not found"
    
    def test_dev_dataset_not_empty(self):
        """Test that dev dataset is not empty."""
        dev_path = Path("/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl")
        
        with open(dev_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) > 0, "Dev dataset is empty"
    
    def test_dev_dataset_valid_json(self):
        """Test that dev dataset contains valid JSON."""
        dev_path = Path("/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl")
        
        with open(dev_path, 'r') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    example = json.loads(line)
                    assert 'messages' in example
                    assert 'ground_truth' in example
                    assert 'metadata' in example
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON on line {i}")
                
                # Only check first 10 lines for speed
                if i >= 10:
                    break
    
    def test_ground_truth_structure(self):
        """Test that ground_truth has required fields."""
        dev_path = Path("/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl")
        
        with open(dev_path, 'r') as f:
            line = f.readline().strip()
            example = json.loads(line)
        
        gt = example['ground_truth']
        assert 'actual_return_pct' in gt
        assert 'days_held' in gt
        assert isinstance(gt['actual_return_pct'], (int, float))
        assert isinstance(gt['days_held'], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
