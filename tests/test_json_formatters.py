"""
Tests for JSON formatters.
"""

import pytest
import json
import sys
import tempfile
import os

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.json_formatter import (
    create_training_example,
    create_dev_example,
    validate_training_example,
    validate_dev_example,
    validate_fireworks_format,
    write_jsonl_file,
    read_jsonl_file,
    create_sample_training_examples,
    create_sample_dev_examples
)


class TestJSONFormatters:
    """Test cases for JSON formatters."""
    
    def test_create_training_example(self):
        """Test training example creation."""
        system_prompt = "You are a financial analyst."
        user_prompt = "Analyze AAPL stock."
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
        
        example = create_training_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Check structure
        assert "messages" in example
        assert len(example["messages"]) == 2
        assert example["messages"][0]["role"] == "system"
        assert example["messages"][1]["role"] == "user"
        assert example["messages"][0]["content"] == system_prompt
        assert example["messages"][1]["content"] == user_prompt
        assert example["ground_truth"] == ground_truth
        assert example["metadata"] == metadata
    
    def test_create_dev_example(self):
        """Test development example creation."""
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
        
        example = create_dev_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        # Check structure
        assert "messages" in example
        assert len(example["messages"]) == 3
        assert example["messages"][0]["role"] == "system"
        assert example["messages"][1]["role"] == "user"
        assert example["messages"][2]["role"] == "assistant"
        
        # Check assistant response is JSON string
        assistant_content = example["messages"][2]["content"]
        parsed_response = json.loads(assistant_content)
        assert parsed_response == assistant_response
    
    def test_validate_training_example_valid(self):
        """Test validation of valid training example."""
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "ground_truth": {
                "actual_return_pct": 2.5,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            },
            "metadata": {
                "ticker": "AAPL",
                "entry_date": "2024-01-02",
                "historical_returns": [1.2, -0.5, 3.1]
            }
        }
        
        is_valid, errors = validate_training_example(example)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_training_example_invalid(self):
        """Test validation of invalid training example."""
        # Missing ground_truth
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_training_example(example)
        assert not is_valid
        assert any("ground_truth" in error for error in errors)
        
        # Has assistant message (should not for training)
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."},
                {"role": "assistant", "content": '{"action": "buy"}'}
            ],
            "ground_truth": {"actual_return_pct": 2.5},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_training_example(example)
        assert not is_valid
        assert any("assistant message" in error.lower() for error in errors)
    
    def test_validate_dev_example_valid(self):
        """Test validation of valid development example."""
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."},
                {"role": "assistant", "content": '{"reasoning": "test", "action": "buy", "support": "test"}'}
            ],
            "ground_truth": {
                "actual_return_pct": 2.5,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            },
            "metadata": {
                "ticker": "AAPL",
                "entry_date": "2024-01-02",
                "historical_returns": [1.2, -0.5, 3.1]
            }
        }
        
        is_valid, errors = validate_dev_example(example)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_dev_example_invalid(self):
        """Test validation of invalid development example."""
        # Missing assistant message
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "ground_truth": {"actual_return_pct": 2.5},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_dev_example(example)
        assert not is_valid
        assert any("3 messages" in error for error in errors)
        
        # Invalid JSON in assistant response
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."},
                {"role": "assistant", "content": "Invalid JSON"}
            ],
            "ground_truth": {"actual_return_pct": 2.5},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_dev_example(example)
        assert not is_valid
        assert any("valid JSON" in error for error in errors)
    
    def test_validate_fireworks_format(self):
        """Test Fireworks format validation."""
        # Valid example
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "ground_truth": {"actual_return_pct": 2.5},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_fireworks_format(example)
        assert is_valid
        assert len(errors) == 0
        
        # Invalid example - empty messages
        example = {"messages": [], "ground_truth": {}, "metadata": {}}
        is_valid, errors = validate_fireworks_format(example)
        assert not is_valid
        assert any("empty" in error.lower() for error in errors)
        
        # Invalid example - wrong role
        example = {
            "messages": [{"role": "invalid", "content": "test"}],
            "ground_truth": {},
            "metadata": {}
        }
        is_valid, errors = validate_fireworks_format(example)
        assert not is_valid
        assert any("invalid role" in error.lower() for error in errors)
    
    def test_jsonl_file_operations(self):
        """Test JSONL file read/write operations."""
        examples = [
            {
                "messages": [
                    {"role": "system", "content": "You are a financial analyst."},
                    {"role": "user", "content": "Analyze AAPL stock."}
                ],
                "ground_truth": {"actual_return_pct": 2.5},
                "metadata": {"ticker": "AAPL"}
            },
            {
                "messages": [
                    {"role": "system", "content": "You are a financial analyst."},
                    {"role": "user", "content": "Analyze MSFT stock."}
                ],
                "ground_truth": {"actual_return_pct": 1.5},
                "metadata": {"ticker": "MSFT"}
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = f.name
        
        try:
            # Write examples
            write_jsonl_file(examples, temp_file)
            
            # Verify file exists and has content
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
            
            # Read examples back
            read_examples = read_jsonl_file(temp_file)
            assert len(read_examples) == 2
            assert read_examples[0]["metadata"]["ticker"] == "AAPL"
            assert read_examples[1]["metadata"]["ticker"] == "MSFT"
            
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_create_sample_examples(self):
        """Test sample example creation."""
        # Test training examples
        training_examples = create_sample_training_examples(3)
        assert len(training_examples) == 3
        
        for example in training_examples:
            is_valid, errors = validate_training_example(example)
            assert is_valid, f"Invalid training example: {errors}"
        
        # Test dev examples
        dev_examples = create_sample_dev_examples(3)
        assert len(dev_examples) == 3
        
        for example in dev_examples:
            is_valid, errors = validate_dev_example(example)
            assert is_valid, f"Invalid dev example: {errors}"
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with empty content
        example = {
            "messages": [
                {"role": "system", "content": ""},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "ground_truth": {"actual_return_pct": 2.5},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_training_example(example)
        assert not is_valid
        assert any("empty" in error.lower() for error in errors)
        
        # Test with non-numeric actual_return_pct
        example = {
            "messages": [
                {"role": "system", "content": "You are a financial analyst."},
                {"role": "user", "content": "Analyze AAPL stock."}
            ],
            "ground_truth": {"actual_return_pct": "not_a_number"},
            "metadata": {"ticker": "AAPL"}
        }
        
        is_valid, errors = validate_training_example(example)
        assert not is_valid
        assert any("numeric" in error.lower() for error in errors)


if __name__ == "__main__":
    pytest.main([__file__])