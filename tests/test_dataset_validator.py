"""Tests for RLVR dataset validation utilities."""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from rlvr.dataset_validator import validate_dataset_file, validate_datasets
from rlvr.json_formatter import (
    create_sample_training_examples,
    create_sample_dev_examples,
    write_jsonl_file,
)


def _write_examples(base_dir: Path, filename: str, examples) -> Path:
    path = base_dir / filename
    write_jsonl_file(examples, str(path))
    return path


class TestDatasetValidator:
    """Test suite for dataset validation helpers."""

    def test_validate_dataset_file_train_success(self, tmp_path: Path) -> None:
        examples = create_sample_training_examples(3)
        dataset_path = _write_examples(tmp_path, "train.jsonl", examples)

        result = validate_dataset_file(dataset_path, "train", min_examples=3)

        assert result["success"]
        assert result["min_examples_met"]
        assert result["error_counts"]["json_decode"] == 0
        assert result["error_counts"]["fireworks_schema"] == 0
        assert result["error_counts"]["split_schema"] == 0

    def test_validate_dataset_file_detects_training_schema_error(self, tmp_path: Path) -> None:
        examples = create_sample_training_examples(1)
        # Inject invalid assistant message to violate training schema
        examples[0]["messages"].append({"role": "assistant", "content": "{}"})

        dataset_path = _write_examples(tmp_path, "train_invalid.jsonl", examples)

        result = validate_dataset_file(dataset_path, "train", min_examples=1)

        assert not result["success"]
        assert result["min_examples_met"]  # Still counted the example
        assert result["error_counts"]["split_schema"] > 0
        assert result["validation_errors"]

    def test_validate_datasets_bundle(self, tmp_path: Path) -> None:
        train_examples = create_sample_training_examples(3)
        dev_examples = create_sample_dev_examples(3)

        train_path = _write_examples(tmp_path, "train.jsonl", train_examples)
        dev_path = _write_examples(tmp_path, "dev.jsonl", dev_examples)

        result = validate_datasets(
            train_path,
            dev_path,
            min_train_examples=2,
            min_dev_examples=2,
            recommended_train_examples=3,
            recommended_dev_examples=2,
        )

        assert result["success"]
        assert result["train"]["recommended_examples_met"]
        assert result["dev"]["recommended_examples_met"]

        # Increase minimum requirement to trigger failure
        failing_result = validate_datasets(
            train_path,
            dev_path,
            min_train_examples=5,
            min_dev_examples=2,
        )

        assert not failing_result["success"]
        assert failing_result["train"]["min_examples_met"] is False

