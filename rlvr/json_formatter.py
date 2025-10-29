"""
JSONL Formatters for RLVR Training Datasets

This module provides formatters for creating training and development datasets
in the JSONL format required by Fireworks AI for RLVR training.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def create_training_example(
    system_prompt: str,
    user_prompt: str,
    ground_truth: Dict[str, Any],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a training example (NO assistant message).
    
    Training examples are used for RLVR training where the model generates
    responses during training. The assistant message is not included.
    
    Args:
        system_prompt: System prompt for the model
        user_prompt: User prompt with the analysis request
        ground_truth: Ground truth data including actual_return_pct, exit_date, etc.
        metadata: Additional metadata including ticker, historical_returns, etc.
        
    Returns:
        Dictionary representing a training example in JSONL format
    """
    example = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ],
        "ground_truth": ground_truth,
        "metadata": metadata
    }
    
    return example


def create_dev_example(
    system_prompt: str,
    user_prompt: str,
    assistant_response: Dict[str, Any],
    ground_truth: Dict[str, Any],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a development example (WITH assistant message).
    
    Development examples include the assistant's response and are used for
    evaluation and validation of the reward function.
    
    Args:
        system_prompt: System prompt for the model
        user_prompt: User prompt with the analysis request
        assistant_response: Assistant's JSON response with reasoning, action, support
        ground_truth: Ground truth data including actual_return_pct, exit_date, etc.
        metadata: Additional metadata including ticker, historical_returns, etc.
        
    Returns:
        Dictionary representing a development example in JSONL format
    """
    example = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            },
            {
                "role": "assistant",
                "content": json.dumps(assistant_response)
            }
        ],
        "ground_truth": ground_truth,
        "metadata": metadata
    }
    
    return example


def validate_training_example(example: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a training example format.
    
    Args:
        example: Training example to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required top-level fields
    if "messages" not in example:
        errors.append("Missing 'messages' field")
    elif not isinstance(example["messages"], list):
        errors.append("'messages' must be a list")
    else:
        # Check message structure
        messages = example["messages"]
        if len(messages) != 2:
            errors.append(f"Expected 2 messages (system, user), got {len(messages)}")
        
        # Check system message
        if len(messages) > 0:
            if messages[0].get("role") != "system":
                errors.append("First message must be 'system' role")
            if not messages[0].get("content"):
                errors.append("System message content is empty")
        
        # Check user message
        if len(messages) > 1:
            if messages[1].get("role") != "user":
                errors.append("Second message must be 'user' role")
            if not messages[1].get("content"):
                errors.append("User message content is empty")
        
        # Ensure no assistant message
        for i, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                errors.append(f"Training example should not have assistant message at index {i}")
    
    # Check ground_truth
    if "ground_truth" not in example:
        errors.append("Missing 'ground_truth' field")
    else:
        gt = example["ground_truth"]
        required_gt_fields = ["actual_return_pct", "exit_date", "days_held"]
        for field in required_gt_fields:
            if field not in gt:
                errors.append(f"Missing '{field}' in ground_truth")
        
        # Validate actual_return_pct is numeric
        if "actual_return_pct" in gt and not isinstance(gt["actual_return_pct"], (int, float)):
            errors.append("'actual_return_pct' must be numeric")
    
    # Check metadata
    if "metadata" not in example:
        errors.append("Missing 'metadata' field")
    else:
        metadata = example["metadata"]
        if "ticker" not in metadata:
            errors.append("Missing 'ticker' in metadata")
        if "entry_date" not in metadata:
            errors.append("Missing 'entry_date' in metadata")
    
    return len(errors) == 0, errors


def validate_dev_example(example: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a development example format.
    
    Args:
        example: Development example to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required top-level fields
    if "messages" not in example:
        errors.append("Missing 'messages' field")
    elif not isinstance(example["messages"], list):
        errors.append("'messages' must be a list")
    else:
        # Check message structure
        messages = example["messages"]
        if len(messages) != 3:
            errors.append(f"Expected 3 messages (system, user, assistant), got {len(messages)}")
        
        # Check system message
        if len(messages) > 0:
            if messages[0].get("role") != "system":
                errors.append("First message must be 'system' role")
            if not messages[0].get("content"):
                errors.append("System message content is empty")
        
        # Check user message
        if len(messages) > 1:
            if messages[1].get("role") != "user":
                errors.append("Second message must be 'user' role")
            if not messages[1].get("content"):
                errors.append("User message content is empty")
        
        # Check assistant message
        if len(messages) > 2:
            if messages[2].get("role") != "assistant":
                errors.append("Third message must be 'assistant' role")
            if not messages[2].get("content"):
                errors.append("Assistant message content is empty")
            else:
                # Validate assistant response is valid JSON
                try:
                    assistant_data = json.loads(messages[2]["content"])
                    required_fields = ["reasoning", "action", "support"]
                    for field in required_fields:
                        if field not in assistant_data:
                            errors.append(f"Missing '{field}' in assistant response")
                except json.JSONDecodeError:
                    errors.append("Assistant response is not valid JSON")
    
    # Check ground_truth (same as training)
    if "ground_truth" not in example:
        errors.append("Missing 'ground_truth' field")
    else:
        gt = example["ground_truth"]
        required_gt_fields = ["actual_return_pct", "exit_date", "days_held"]
        for field in required_gt_fields:
            if field not in gt:
                errors.append(f"Missing '{field}' in ground_truth")
        
        # Validate actual_return_pct is numeric
        if "actual_return_pct" in gt and not isinstance(gt["actual_return_pct"], (int, float)):
            errors.append("'actual_return_pct' must be numeric")
    
    # Check metadata (same as training)
    if "metadata" not in example:
        errors.append("Missing 'metadata' field")
    else:
        metadata = example["metadata"]
        if "ticker" not in metadata:
            errors.append("Missing 'ticker' in metadata")
        if "entry_date" not in metadata:
            errors.append("Missing 'entry_date' in metadata")
    
    return len(errors) == 0, errors


def validate_fireworks_format(example: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that an example conforms to Fireworks AI format requirements.
    
    Args:
        example: Example to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check basic structure
    if not isinstance(example, dict):
        errors.append("Example must be a dictionary")
        return False, errors
    
    # Check messages field
    if "messages" not in example:
        errors.append("Missing 'messages' field")
    elif not isinstance(example["messages"], list):
        errors.append("'messages' must be a list")
    elif len(example["messages"]) == 0:
        errors.append("'messages' list cannot be empty")
    else:
        # Validate each message
        for i, message in enumerate(example["messages"]):
            if not isinstance(message, dict):
                errors.append(f"Message {i} must be a dictionary")
                continue
            
            if "role" not in message:
                errors.append(f"Message {i} missing 'role' field")
            elif message["role"] not in ["system", "user", "assistant"]:
                errors.append(f"Message {i} has invalid role: {message['role']}")
            
            if "content" not in message:
                errors.append(f"Message {i} missing 'content' field")
            elif not isinstance(message["content"], str):
                errors.append(f"Message {i} content must be a string")
    
    # Check ground_truth field
    if "ground_truth" not in example:
        errors.append("Missing 'ground_truth' field")
    elif not isinstance(example["ground_truth"], dict):
        errors.append("'ground_truth' must be a dictionary")
    
    # Check metadata field
    if "metadata" not in example:
        errors.append("Missing 'metadata' field")
    elif not isinstance(example["metadata"], dict):
        errors.append("'metadata' must be a dictionary")
    
    return len(errors) == 0, errors


def format_example_for_jsonl(example: Dict[str, Any]) -> str:
    """
    Format an example as a JSONL line.
    
    Args:
        example: Example dictionary to format
        
    Returns:
        JSONL line string
    """
    return json.dumps(example, ensure_ascii=False, separators=(',', ':'))


def write_jsonl_file(examples: List[Dict[str, Any]], filepath: str) -> None:
    """
    Write examples to a JSONL file.
    
    Args:
        examples: List of example dictionaries
        filepath: Path to write the JSONL file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(format_example_for_jsonl(example) + '\n')
    
    logger.info(f"Wrote {len(examples)} examples to {filepath}")


def read_jsonl_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Read examples from a JSONL file.
    
    Args:
        filepath: Path to the JSONL file
        
    Returns:
        List of example dictionaries
    """
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                example = json.loads(line)
                examples.append(example)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON on line {line_num}: {e}")
                raise
    
    logger.info(f"Read {len(examples)} examples from {filepath}")
    return examples


def create_sample_training_examples(num_examples: int = 3) -> List[Dict[str, Any]]:
    """
    Create sample training examples for testing.
    
    Args:
        num_examples: Number of examples to create
        
    Returns:
        List of training example dictionaries
    """
    examples = []
    
    system_prompt = "You are a senior financial analyst with expertise in stock market analysis. Provide investment recommendations based on comprehensive analysis of market data, company fundamentals, and economic indicators."
    
    test_cases = [
        {
            "ticker": "AAPL",
            "action": "buy",
            "actual_return": 2.5,
            "description": "Strong fundamentals and growth prospects"
        },
        {
            "ticker": "MSFT", 
            "action": "hold",
            "actual_return": 0.5,
            "description": "Stable performance with moderate growth"
        },
        {
            "ticker": "GOOGL",
            "action": "sell",
            "actual_return": -1.8,
            "description": "Market concerns and overvaluation"
        }
    ]
    
    for i, case in enumerate(test_cases[:num_examples]):
        user_prompt = f"""=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {case['ticker']} ===

Date: 2024-01-{i+1:02d}

Please analyze {case['ticker']} stock and provide your investment recommendation with detailed reasoning.

Consider:
- Technical indicators and price trends
- Company fundamentals and financial health
- Market conditions and economic factors
- Risk assessment and potential returns

Provide your recommendation as JSON with reasoning, action, and supporting evidence."""

        ground_truth = {
            "actual_return_pct": case["actual_return"],
            "exit_date": f"2024-01-{i+4:02d}",
            "days_held": 3,
            "early_exit": False,
            "entry_price": 100.0 + i * 10,
            "exit_price": (100.0 + i * 10) * (1 + case["actual_return"] / 100)
        }
        
        metadata = {
            "ticker": case["ticker"],
            "entry_date": f"2024-01-{i+1:02d}",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3],
            "test_case": case["description"]
        }
        
        example = create_training_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        examples.append(example)
    
    return examples


def create_sample_dev_examples(num_examples: int = 3) -> List[Dict[str, Any]]:
    """
    Create sample development examples for testing.
    
    Args:
        num_examples: Number of examples to create
        
    Returns:
        List of development example dictionaries
    """
    examples = []
    
    system_prompt = "You are a senior financial analyst with expertise in stock market analysis. Provide investment recommendations based on comprehensive analysis of market data, company fundamentals, and economic indicators."
    
    test_cases = [
        {
            "ticker": "AAPL",
            "action": "buy",
            "actual_return": 2.5,
            "reasoning": "Strong fundamentals with consistent revenue growth and expanding market share in key segments.",
            "support": "Q4 revenue up 15% YoY, iPhone sales strong, services revenue growing 20%+"
        },
        {
            "ticker": "MSFT",
            "action": "hold", 
            "actual_return": 0.5,
            "reasoning": "Stable performance with moderate growth prospects, but valuation is fair.",
            "support": "Azure growth slowing, Office 365 mature, but AI integration opportunities ahead"
        },
        {
            "ticker": "GOOGL",
            "action": "sell",
            "actual_return": -1.8,
            "reasoning": "Market concerns about AI competition and regulatory headwinds.",
            "support": "Search market share pressure, regulatory fines, high valuation multiples"
        }
    ]
    
    for i, case in enumerate(test_cases[:num_examples]):
        user_prompt = f"""=== COMPREHENSIVE INVESTMENT ANALYSIS FOR {case['ticker']} ===

Date: 2024-01-{i+1:02d}

Please analyze {case['ticker']} stock and provide your investment recommendation with detailed reasoning.

Consider:
- Technical indicators and price trends
- Company fundamentals and financial health
- Market conditions and economic factors
- Risk assessment and potential returns

Provide your recommendation as JSON with reasoning, action, and supporting evidence."""

        assistant_response = {
            "reasoning": case["reasoning"],
            "action": case["action"],
            "support": case["support"]
        }
        
        ground_truth = {
            "actual_return_pct": case["actual_return"],
            "exit_date": f"2024-01-{i+4:02d}",
            "days_held": 3,
            "early_exit": False,
            "entry_price": 100.0 + i * 10,
            "exit_price": (100.0 + i * 10) * (1 + case["actual_return"] / 100)
        }
        
        metadata = {
            "ticker": case["ticker"],
            "entry_date": f"2024-01-{i+1:02d}",
            "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3],
            "test_case": f"Dev example for {case['ticker']}"
        }
        
        example = create_dev_example(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            ground_truth=ground_truth,
            metadata=metadata
        )
        
        examples.append(example)
    
    return examples


# Export functions
__all__ = [
    "create_training_example",
    "create_dev_example", 
    "validate_training_example",
    "validate_dev_example",
    "validate_fireworks_format",
    "format_example_for_jsonl",
    "write_jsonl_file",
    "read_jsonl_file",
    "create_sample_training_examples",
    "create_sample_dev_examples"
]