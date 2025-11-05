"""Utilities for validating RLVR JSONL datasets before upload."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .json_formatter import (
    validate_fireworks_format,
    validate_training_example,
    validate_dev_example,
)


logger = logging.getLogger(__name__)


def _normalise_split(split: str) -> str:
    return split.lower().strip()


def validate_dataset_file(
    path: str | Path,
    split: str,
    *,
    min_examples: int = 3,
    recommended_examples: Optional[int] = None,
    max_examples: Optional[int] = None,
    max_errors: int = 25,
) -> Dict[str, Any]:
    """Validate a single RLVR dataset JSONL file.

    Args:
        path: Path to the JSONL file.
        split: Dataset split name ("train" or "dev").
        min_examples: Minimum number of examples required for this split.
        recommended_examples: Optional recommended example count (informational).
        max_examples: Optional ceiling for examples (Fireworks max = 3,000,000).
        max_errors: Maximum number of detailed errors to retain in the result.

    Returns:
        Dictionary with validation statistics and whether the file passed.
    """

    split_name = _normalise_split(split)
    path_obj = Path(path)

    result: Dict[str, Any] = {
        "split": split_name,
        "path": str(path_obj),
        "file_exists": path_obj.exists(),
        "total_lines": 0,
        "parsed_examples": 0,
        "empty_lines": 0,
        "error_counts": {
            "json_decode": 0,
            "fireworks_schema": 0,
            "split_schema": 0,
        },
        "min_examples_required": min_examples,
        "recommended_examples": recommended_examples,
        "max_examples": max_examples,
        "min_examples_met": False,
        "recommended_examples_met": None,
        "max_examples_exceeded": False,
        "validation_errors": [],
        "success": False,
    }

    if not result["file_exists"]:
        logger.warning("Dataset file missing for %s split: %s", split_name, path_obj)
        return result

    try:
        with path_obj.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                result["total_lines"] += 1

                line = raw_line.strip()
                if not line:
                    result["empty_lines"] += 1
                    continue

                try:
                    example = json.loads(line)
                except json.JSONDecodeError as exc:
                    result["error_counts"]["json_decode"] += 1
                    if len(result["validation_errors"]) < max_errors:
                        result["validation_errors"].append(
                            {
                                "line": line_number,
                                "type": "json_decode",
                                "error": str(exc),
                            }
                        )
                    continue

                result["parsed_examples"] += 1

                fireworks_ok, fireworks_errors = validate_fireworks_format(example)
                if not fireworks_ok:
                    result["error_counts"]["fireworks_schema"] += 1
                    if len(result["validation_errors"]) < max_errors:
                        result["validation_errors"].append(
                            {
                                "line": line_number,
                                "type": "fireworks_schema",
                                "error": "; ".join(fireworks_errors),
                            }
                        )

                if split_name == "train":
                    split_ok, split_errors = validate_training_example(example)
                elif split_name == "dev":
                    split_ok, split_errors = validate_dev_example(example)
                else:
                    split_ok, split_errors = False, [f"Unsupported split '{split}'"]

                if not split_ok:
                    result["error_counts"]["split_schema"] += 1
                    if len(result["validation_errors"]) < max_errors:
                        result["validation_errors"].append(
                            {
                                "line": line_number,
                                "type": "split_schema",
                                "error": "; ".join(split_errors),
                            }
                        )

    except OSError as exc:
        logger.error("Failed to read dataset file %s: %s", path_obj, exc)
        if len(result["validation_errors"]) < max_errors:
            result["validation_errors"].append(
                {
                    "line": None,
                    "type": "io_error",
                    "error": str(exc),
                }
            )
        return result

    parsed = result["parsed_examples"]
    result["min_examples_met"] = parsed >= min_examples

    if recommended_examples is not None:
        result["recommended_examples_met"] = parsed >= recommended_examples
    else:
        result["recommended_examples_met"] = None

    result["max_examples_exceeded"] = (
        max_examples is not None and parsed > max_examples
    )

    no_errors = all(count == 0 for count in result["error_counts"].values())
    result["success"] = (
        result["file_exists"]
        and no_errors
        and result["min_examples_met"]
        and not result["max_examples_exceeded"]
    )

    return result


def validate_datasets(
    train_file: str | Path,
    dev_file: str | Path,
    *,
    min_train_examples: int = 3,
    min_dev_examples: int = 3,
    recommended_train_examples: Optional[int] = None,
    recommended_dev_examples: Optional[int] = None,
    max_train_examples: Optional[int] = None,
    max_dev_examples: Optional[int] = None,
    max_errors: int = 25,
) -> Dict[str, Any]:
    """Validate train/dev datasets and return bundled results."""

    train_result = validate_dataset_file(
        train_file,
        "train",
        min_examples=min_train_examples,
        recommended_examples=recommended_train_examples,
        max_examples=max_train_examples,
        max_errors=max_errors,
    )

    dev_result = validate_dataset_file(
        dev_file,
        "dev",
        min_examples=min_dev_examples,
        recommended_examples=recommended_dev_examples,
        max_examples=max_dev_examples,
        max_errors=max_errors,
    )

    overall_success = train_result["success"] and dev_result["success"]

    summary = {
        "train_examples": train_result["parsed_examples"],
        "dev_examples": dev_result["parsed_examples"],
        "total_examples": train_result["parsed_examples"] + dev_result["parsed_examples"],
    }

    return {
        "success": overall_success,
        "train": train_result,
        "dev": dev_result,
        "summary": summary,
    }


__all__ = [
    "validate_dataset_file",
    "validate_datasets",
]

