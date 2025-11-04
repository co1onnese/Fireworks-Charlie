#!/usr/bin/env python3
"""
Validate Training Data

Production script to validate RLVR training data files.
Performs sanity checks before training.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger

logger = setup_logger(
    name="validate_training_data",
    log_file="logs/validate_training_data.log",
    log_level="INFO"
)


def validate_jsonl_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a JSONL training file

    Args:
        file_path: Path to JSONL file

    Returns:
        Dictionary with validation results
    """
    results = {
        "file": file_path,
        "exists": False,
        "readable": False,
        "valid_jsonl": False,
        "total_examples": 0,
        "issues": [],
        "warnings": []
    }

    path = Path(file_path)
    results["exists"] = path.exists()

    if not results["exists"]:
        results["issues"].append(f"File does not exist: {file_path}")
        return results

    results["readable"] = True

    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                results["total_examples"] += 1

                if line_num == 1 or line_num % 1000 == 0:
                    logger.info(f"  Validating line {line_num}...")

                # Parse JSON
                try:
                    example = json.loads(line)
                except json.JSONDecodeError as e:
                    results["issues"].append(
                        f"Line {line_num}: Invalid JSON - {str(e)}"
                    )
                    continue

                # Validate structure
                if "messages" not in example:
                    results["issues"].append(f"Line {line_num}: Missing 'messages' field")
                    continue

                if "metadata" not in example:
                    results["warnings"].append(f"Line {line_num}: Missing 'metadata' field")

                # Validate messages
                messages = example.get("messages", [])
                if not isinstance(messages, list) or len(messages) == 0:
                    results["issues"].append(f"Line {line_num}: Invalid 'messages' (not a list or empty)")
                    continue

                # Check for system and user messages
                has_system = any(m.get("role") == "system" for m in messages)
                has_user = any(m.get("role") == "user" for m in messages)

                if not has_system:
                    results["issues"].append(f"Line {line_num}: Missing system message")
                if not has_user:
                    results["issues"].append(f"Line {line_num}: Missing user message")

                # Check content is not empty
                for msg in messages:
                    if "content" not in msg or not msg["content"]:
                        results["issues"].append(
                            f"Line {line_num}: Message with empty content"
                        )
                        break

                # Basic sanity checks on metadata
                if "metadata" in example:
                    metadata = example["metadata"]
                    if "ticker" not in metadata:
                        results["warnings"].append(f"Line {line_num}: Missing ticker in metadata")
                    if "date" not in metadata:
                        results["warnings"].append(f"Line {line_num}: Missing date in metadata")

        results["valid_jsonl"] = True
        logger.info(f"✅ Validated {results['total_examples']} examples")

    except Exception as e:
        results["issues"].append(f"Error reading file: {str(e)}")

    return results


def check_data_leakage(train_file: str, dev_file: str) -> Dict[str, Any]:
    """
    Check for data leakage between train and dev sets

    Args:
        train_file: Path to training file
        dev_file: Path to dev file

    Returns:
        Dictionary with leakage check results
    """
    results = {
        "has_leakage": False,
        "leaked_examples": [],
        "total_dev": 0
    }

    # Load all ticker-date pairs from training set
    train_examples = set()
    with open(train_file, 'r') as f:
        for line in f:
            example = json.loads(line)
            metadata = example.get("metadata", {})
            ticker = metadata.get("ticker")
            date = metadata.get("date")
            if ticker and date:
                train_examples.add((ticker, date))

    # Check dev set for overlaps
    with open(dev_file, 'r') as f:
        for line in f:
            results["total_dev"] += 1
            example = json.loads(line)
            metadata = example.get("metadata", {})
            ticker = metadata.get("ticker")
            date = metadata.get("date")

            if ticker and date:
                if (ticker, date) in train_examples:
                    results["has_leakage"] = True
                    results["leaked_examples"].append((ticker, date))

    return results


def validate_training_data(train_file: str, dev_file: str) -> int:
    """
    Validate RLVR training data files

    Args:
        train_file: Path to training file
        dev_file: Path to dev file

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.info("=" * 80)
    logger.info("TRAINING DATA VALIDATION")
    logger.info("=" * 80)
    logger.info("")

    all_passed = True

    # Validate train file
    logger.info(f"Validating training file: {train_file}")
    train_results = validate_jsonl_file(train_file)
    logger.info(f"  Total examples: {train_results['total_examples']}")

    if train_results["issues"]:
        logger.error(f"  ❌ {len(train_results['issues'])} issues found")
        all_passed = False
    else:
        logger.info("  ✅ No issues found")

    if train_results["warnings"]:
        logger.warning(f"  ⚠️  {len(train_results['warnings'])} warnings")
    logger.info("")

    # Validate dev file
    logger.info(f"Validating dev file: {dev_file}")
    dev_results = validate_jsonl_file(dev_file)
    logger.info(f"  Total examples: {dev_results['total_examples']}")

    if dev_results["issues"]:
        logger.error(f"  ❌ {len(dev_results['issues'])} issues found")
        all_passed = False
    else:
        logger.info("  ✅ No issues found")

    if dev_results["warnings"]:
        logger.warning(f"  ⚠️  {len(dev_results['warnings'])} warnings")
    logger.info("")

    # Check for data leakage
    logger.info("Checking for data leakage between train and dev...")
    leakage_results = check_data_leakage(train_file, dev_file)

    if leakage_results["has_leakage"]:
        logger.error(f"  ❌ Data leakage detected: {len(leakage_results['leaked_examples'])} examples")
        for ticker, date in leakage_results["leaked_examples"]:
            logger.error(f"    {ticker} on {date}")
        all_passed = False
    else:
        logger.info("  ✅ No data leakage detected")
    logger.info("")

    # Print summary
    logger.info("=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Training examples: {train_results['total_examples']}")
    logger.info(f"Dev examples: {dev_results['total_examples']}")
    logger.info(f"Total examples: {train_results['total_examples'] + dev_results['total_examples']}")
    logger.info("")

    if all_passed:
        logger.info("✅ All validations passed!")
        logger.info("")
        logger.info("Training data is ready for use.")
        return 0
    else:
        logger.error("❌ Validation failed!")
        logger.error("")
        logger.error("Please fix the issues before using this training data.")
        return 1


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Validate RLVR training data")
    parser.add_argument("--train-file", type=str,
                       default="/opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl",
                       help="Training file path")
    parser.add_argument("--dev-file", type=str,
                       default="/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl",
                       help="Dev file path")

    args = parser.parse_args()

    exit_code = validate_training_data(args.train_file, args.dev_file)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
