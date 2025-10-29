"""
Reward-kit Configuration Generator

This module generates YAML configuration files for reward-kit CLI evaluation
and provides utilities for testing the reward function locally.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def generate_run_eval_config(
    output_path: str = "conf/run_eval.yaml",
    dataset_path: str = "storage/rlvr_datasets/dev.jsonl",
    output_dir: str = "outputs/evaluations"
) -> str:
    """
    Generate YAML configuration for reward-kit CLI evaluation.
    
    Args:
        output_path: Path to save the YAML configuration file
        dataset_path: Path to the JSONL dataset file
        output_dir: Directory for evaluation outputs
        
    Returns:
        Path to the generated configuration file
    """
    config = {
        "dataset": {
            "path": dataset_path,
            "format": "jsonl"
        },
        "reward_function": {
            "module": "rlvr.reward_function",
            "function": "stock_prediction_reward"
        },
        "output": {
            "dir": output_dir,
            "format": "jsonl"
        },
        "evaluation": {
            "batch_size": 32,
            "max_workers": 4,
            "timeout": 300
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Write configuration file
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    logger.info(f"Generated reward-kit configuration: {output_path}")
    return output_path


def generate_train_config(
    output_path: str = "conf/train_config.yaml",
    train_dataset: str = "storage/rlvr_datasets/train.jsonl",
    dev_dataset: str = "storage/rlvr_datasets/dev.jsonl",
    model_name: str = "accounts/fireworks/models/deepseek-v3p1-terminus",
    output_dir: str = "outputs/training"
) -> str:
    """
    Generate YAML configuration for GRPO training.
    
    Args:
        output_path: Path to save the YAML configuration file
        train_dataset: Path to training dataset
        dev_dataset: Path to development dataset
        model_name: Fireworks model name
        output_dir: Directory for training outputs
        
    Returns:
        Path to the generated configuration file
    """
    config = {
        "model": {
            "name": model_name,
            "mode": "deepseek-chat"
        },
        "datasets": {
            "train": {
                "path": train_dataset,
                "format": "jsonl"
            },
            "dev": {
                "path": dev_dataset,
                "format": "jsonl"
            }
        },
        "training": {
            "algorithm": "grpo",
            "epochs": 1,
            "learning_rate": 0.0001,
            "lora_rank": 8,
            "batch_size": 32768,
            "n_responses": 4,
            "temperature": 0.7,
            "max_tokens": 2048
        },
        "reward_config": {
            "evaluator_id": "stock-prediction-evaluator",
            "evaluator_name": "Stock Prediction Verifiable Reward"
        },
        "output": {
            "dir": output_dir,
            "format": "jsonl"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Write configuration file
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    logger.info(f"Generated training configuration: {output_path}")
    return output_path


def create_sample_dataset(
    output_path: str = "storage/rlvr_datasets/sample.jsonl",
    num_examples: int = 5
) -> str:
    """
    Create a sample dataset for testing the reward function.
    
    Args:
        output_path: Path to save the sample dataset
        num_examples: Number of examples to generate
        
    Returns:
        Path to the generated dataset file
    """
    import json
    from datetime import datetime, timedelta
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    examples = []
    base_date = datetime(2024, 1, 1)
    
    # Test cases with different scenarios
    test_cases = [
        {
            "action": "buy",
            "actual_return": 2.5,
            "expected_score": 0.8,  # Correct direction
            "description": "Correct buy prediction"
        },
        {
            "action": "sell", 
            "actual_return": 3.0,
            "expected_score": 0.0,  # Incorrect direction
            "description": "Incorrect sell prediction"
        },
        {
            "action": "hold",
            "actual_return": 0.5,
            "expected_score": 0.8,  # Correct hold
            "description": "Correct hold prediction"
        },
        {
            "action": "strong_buy",
            "actual_return": -1.5,
            "expected_score": 0.0,  # Incorrect strong buy
            "description": "Incorrect strong buy prediction"
        },
        {
            "action": "strong_sell",
            "actual_return": -4.0,
            "expected_score": 0.8,  # Correct strong sell
            "description": "Correct strong sell prediction"
        }
    ]
    
    for i, case in enumerate(test_cases[:num_examples]):
        entry_date = base_date + timedelta(days=i)
        exit_date = entry_date + timedelta(days=3)
        
        # Generate historical returns
        historical_returns = [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
        
        example = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a senior financial analyst with expertise in stock market analysis. Provide investment recommendations based on comprehensive analysis of market data, company fundamentals, and economic indicators."
                },
                {
                    "role": "user", 
                    "content": f"=== COMPREHENSIVE INVESTMENT ANALYSIS FOR AAPL ===\\n\\nDate: {entry_date.strftime('%Y-%m-%d')}\\n\\nPlease analyze AAPL stock and provide your investment recommendation with detailed reasoning."
                },
                {
                    "role": "assistant",
                    "content": json.dumps({
                        "reasoning": f"Analysis for {case['description']} - Market conditions and company fundamentals suggest this action.",
                        "action": case["action"],
                        "support": f"Key supporting evidence: {case['description']} based on technical and fundamental analysis."
                    })
                }
            ],
            "ground_truth": {
                "actual_return_pct": case["actual_return"],
                "exit_date": exit_date.strftime("%Y-%m-%d"),
                "days_held": 3,
                "early_exit": False,
                "entry_price": 185.50,
                "exit_price": 185.50 * (1 + case["actual_return"] / 100)
            },
            "metadata": {
                "ticker": "AAPL",
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "historical_returns": historical_returns,
                "test_case": case["description"],
                "expected_score": case["expected_score"]
            }
        }
        
        examples.append(example)
    
    # Write examples to JSONL file
    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    logger.info(f"Generated sample dataset with {len(examples)} examples: {output_path}")
    return output_path


def validate_dataset_format(dataset_path: str) -> Dict[str, Any]:
    """
    Validate that a dataset file conforms to the expected format.
    
    Args:
        dataset_path: Path to the dataset file
        
    Returns:
        Dictionary with validation results
    """
    import json
    
    results = {
        "valid": True,
        "total_examples": 0,
        "errors": [],
        "warnings": []
    }
    
    try:
        with open(dataset_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    example = json.loads(line.strip())
                    results["total_examples"] += 1
                    
                    # Validate required fields
                    if "messages" not in example:
                        results["errors"].append(f"Line {line_num}: Missing 'messages' field")
                        results["valid"] = False
                    elif not isinstance(example["messages"], list):
                        results["errors"].append(f"Line {line_num}: 'messages' must be a list")
                        results["valid"] = False
                    else:
                        # Check for assistant message
                        has_assistant = any(msg.get("role") == "assistant" for msg in example["messages"])
                        if not has_assistant:
                            results["warnings"].append(f"Line {line_num}: No assistant message found")
                    
                    if "ground_truth" not in example:
                        results["errors"].append(f"Line {line_num}: Missing 'ground_truth' field")
                        results["valid"] = False
                    elif "actual_return_pct" not in example["ground_truth"]:
                        results["errors"].append(f"Line {line_num}: Missing 'actual_return_pct' in ground_truth")
                        results["valid"] = False
                    
                    if "metadata" not in example:
                        results["warnings"].append(f"Line {line_num}: Missing 'metadata' field")
                    
                except json.JSONDecodeError as e:
                    results["errors"].append(f"Line {line_num}: Invalid JSON - {str(e)}")
                    results["valid"] = False
                    
    except FileNotFoundError:
        results["errors"].append(f"Dataset file not found: {dataset_path}")
        results["valid"] = False
    except Exception as e:
        results["errors"].append(f"Error reading dataset: {str(e)}")
        results["valid"] = False
    
    return results


# Export functions
__all__ = [
    "generate_run_eval_config",
    "generate_train_config", 
    "create_sample_dataset",
    "validate_dataset_format"
]