"""
Integration tests for the complete RLVR pipeline.
"""

import pytest
import json
import sys
import tempfile
import os
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.reward_function import stock_prediction_reward
from rlvr.json_formatter import (
    create_training_example,
    create_dev_example,
    write_jsonl_file,
    read_jsonl_file
)
from rlvr.reward_kit_config import (
    generate_run_eval_config,
    create_sample_dataset,
    validate_dataset_format
)


class TestIntegration:
    """Integration tests for the complete RLVR pipeline."""
    
    def test_end_to_end_reward_calculation(self):
        """Test complete end-to-end reward calculation pipeline."""
        # Create a development example
        system_prompt = "You are a senior financial analyst."
        user_prompt = "Analyze AAPL stock for investment recommendation."
        assistant_response = {
            "reasoning": "Strong fundamentals with consistent revenue growth and expanding market share.",
            "action": "buy",
            "support": "Q4 revenue up 15% YoY, iPhone sales strong, services revenue growing 20%+"
        }
        ground_truth = {
            "actual_return_pct": 2.5,
            "exit_date": "2024-01-05",
            "days_held": 3,
            "early_exit": False,
            "entry_price": 185.50,
            "exit_price": 190.14
        }
        metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        # Create development example
        dev_example = create_dev_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Validate the example
        validation_results = validate_dataset_format("temp_validation.jsonl")
        # Write example to temp file for validation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = f.name
            f.write(json.dumps(dev_example) + '\n')
        
        try:
            validation_results = validate_dataset_format(temp_file)
            assert validation_results["valid"], f"Dev example validation failed: {validation_results['errors']}"
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # Test reward function
        result = stock_prediction_reward(
            messages=dev_example["messages"],
            ground_truth=dev_example["ground_truth"],
            metadata=dev_example["metadata"]
        )
        
        # Verify result
        assert 0.0 <= result.score <= 1.0
        assert result.is_score_valid is True
        assert len(result.metrics) > 0
        
        # Check that directional accuracy is correct (buy with positive return)
        assert result.metrics["directional_accuracy"].score == 1.0
        assert "Correct" in result.metrics["directional_accuracy"].reason
    
    def test_training_vs_dev_example_differences(self):
        """Test that training and dev examples have correct structure differences."""
        system_prompt = "You are a financial analyst."
        user_prompt = "Analyze AAPL stock."
        assistant_response = {
            "reasoning": "Strong fundamentals",
            "action": "buy",
            "support": "Revenue growth"
        }
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
        
        # Create training example (no assistant message)
        training_example = create_training_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Create dev example (with assistant message)
        dev_example = create_dev_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Verify differences
        assert len(training_example["messages"]) == 2
        assert len(dev_example["messages"]) == 3
        
        # Training example should not have assistant message
        training_roles = [msg["role"] for msg in training_example["messages"]]
        assert "assistant" not in training_roles
        
        # Dev example should have assistant message
        dev_roles = [msg["role"] for msg in dev_example["messages"]]
        assert "assistant" in dev_roles
        
        # Both should have same ground_truth and metadata
        assert training_example["ground_truth"] == dev_example["ground_truth"]
        assert training_example["metadata"] == dev_example["metadata"]
    
    def test_dataset_generation_and_validation(self):
        """Test complete dataset generation and validation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate sample dataset
            dataset_path = os.path.join(temp_dir, "test_dataset.jsonl")
            create_sample_dataset(dataset_path, num_examples=5)
            
            # Verify file exists
            assert os.path.exists(dataset_path)
            
            # Read and validate dataset
            with open(dataset_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 5
            
            # Validate format
            validation_results = validate_dataset_format(dataset_path)
            assert validation_results["valid"]
            assert validation_results["total_examples"] == 5
            assert len(validation_results["errors"]) == 0
    
    def test_reward_function_with_different_actions(self):
        """Test reward function with various action types."""
        test_cases = [
            ("buy", 2.5, "correct buy"),
            ("sell", -1.0, "correct sell"),  # sell with negative return is correct
            ("hold", 0.5, "correct hold"),
            ("strong_buy", 3.5, "correct strong buy"),  # strong buy with positive return is correct
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
            
            # Verify basic properties
            assert 0.0 <= result.score <= 1.0, f"Score out of range for {description}"
            assert result.is_score_valid is True, f"Score should be valid for {description}"
            assert len(result.metrics) > 0, f"Should have metrics for {description}"
            
            # Verify directional accuracy makes sense
            directional_score = result.metrics["directional_accuracy"].score
            if "correct" in description:
                assert directional_score == 1.0, f"Correct prediction should have score 1.0: {description}"
            elif "incorrect" in description:
                assert directional_score == 0.0, f"Incorrect prediction should have score 0.0: {description}"
    
    def test_configuration_generation(self):
        """Test configuration file generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate evaluation config
            eval_config_path = os.path.join(temp_dir, "run_eval.yaml")
            generated_path = generate_run_eval_config(
                output_path=eval_config_path,
                dataset_path="test_dataset.jsonl",
                output_dir=temp_dir
            )
            
            assert generated_path == eval_config_path
            assert os.path.exists(eval_config_path)
            
            # Verify config content
            with open(eval_config_path, 'r') as f:
                config_content = f.read()
                assert "rlvr.reward_function" in config_content
                assert "stock_prediction_reward" in config_content
                assert "jsonl" in config_content
    
    def test_error_handling_throughout_pipeline(self):
        """Test error handling throughout the complete pipeline."""
        # Test with invalid JSON in assistant response
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
        
        result = stock_prediction_reward(
            messages=messages,
            ground_truth=ground_truth
        )
        
        # Should handle error gracefully
        assert result.score == 0.0
        assert result.is_score_valid is False
        assert "Invalid JSON" in result.reason
        
        # Test with missing ground truth
        messages_no_gt = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."},
            {"role": "assistant", "content": json.dumps({
                "reasoning": "Strong fundamentals",
                "action": "buy",
                "support": "Revenue growth"
            })}
        ]
        
        result = stock_prediction_reward(messages=messages_no_gt)
        assert result.score == 0.0
        assert result.is_score_valid is False
        assert "ground_truth" in result.reason
    
    def test_metrics_consistency(self):
        """Test that metrics are consistent across different examples."""
        base_messages = [
            {"role": "system", "content": "You are a financial analyst."},
            {"role": "user", "content": "Analyze AAPL stock."}
        ]
        
        base_metadata = {
            "ticker": "AAPL",
            "entry_date": "2024-01-02",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        }
        
        # Test multiple examples with same historical returns
        for i, (action, return_pct) in enumerate([("buy", 2.5), ("sell", -1.0), ("hold", 0.5)]):
            messages = base_messages + [{
                "role": "assistant",
                "content": json.dumps({
                    "reasoning": f"Analysis {i}",
                    "action": action,
                    "support": f"Evidence {i}"
                })
            }]
            
            ground_truth = {
                "actual_return_pct": return_pct,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            }
            
            result = stock_prediction_reward(
                messages=messages,
                ground_truth=ground_truth,
                metadata=base_metadata
            )
            
            # Sharpe score should be the same for all (same historical returns)
            sharpe_score = result.metrics["sharpe_score"].score
            assert sharpe_score == 0.0  # Based on our test data
            
            # Historical returns count should be the same
            returns_count = result.metrics["historical_returns_count"].score
            assert returns_count == 1.0  # 10 returns normalized to 1.0
    
    def test_performance_benchmarking(self):
        """Test performance of reward function with multiple examples."""
        import time
        
        # Create test data
        test_examples = []
        for i in range(10):
            messages = [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": f"Analyze stock {i}."},
                {"role": "assistant", "content": json.dumps({
                    "reasoning": f"Analysis {i}",
                    "action": "buy",
                    "support": f"Evidence {i}"
                })}
            ]
            
            ground_truth = {
                "actual_return_pct": 2.5 + i * 0.1,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            }
            
            metadata = {
                "ticker": f"STOCK{i}",
                "entry_date": "2024-01-02",
                "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
            }
            
            test_examples.append((messages, ground_truth, metadata))
        
        # Benchmark reward function
        start_time = time.time()
        
        results = []
        for messages, ground_truth, metadata in test_examples:
            result = stock_prediction_reward(
                messages=messages,
                ground_truth=ground_truth,
                metadata=metadata
            )
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(test_examples)
        
        # Verify performance (should be < 100ms per example)
        assert avg_time < 0.1, f"Average time per example too high: {avg_time:.3f}s"
        
        # Verify all results are valid
        for result in results:
            assert result.is_score_valid is True
            assert 0.0 <= result.score <= 1.0
        
        print(f"Performance: {avg_time:.3f}s per example ({len(test_examples)} examples)")


if __name__ == "__main__":
    pytest.main([__file__])