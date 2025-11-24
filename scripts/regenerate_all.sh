#!/bin/bash
#
# Regenerate all theses and datasets using configuration from .env file
#
# This script:
# 1. Clears existing LLM responses
# 2. Regenerates theses using the pipeline
# 3. Regenerates RLVR datasets
#
# Make sure your .env file is configured with:
# - TICKERS (comma-separated)
# - START_DATE, END_DATE (for thesis generation)
# - TRAIN_END_DATE (for dataset split)
# - RLVR_OUTPUT_DIR (for dataset output)
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Thesis Regeneration Script"
echo "=========================================="
echo ""

# Load config values
echo "Loading configuration from .env..."
TICKERS=$(python -c "from orchestration.config_manager import config; print(','.join(config.TICKERS))")
START_DATE=$(python -c "from orchestration.config_manager import config; print(config.START_DATE)")
END_DATE=$(python -c "from orchestration.config_manager import config; print(config.END_DATE)")
TRAIN_END_DATE=$(python -c "from orchestration.config_manager import config; print(config.TRAIN_END_DATE)")
OUTPUT_DIR=$(python -c "from orchestration.config_manager import config; print(config.RLVR_OUTPUT_DIR)")

echo "Configuration:"
echo "  Tickers: $TICKERS"
echo "  Date Range: $START_DATE to $END_DATE"
echo "  Train Split Date: $TRAIN_END_DATE"
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Phase 1: Clear existing responses
echo "=========================================="
echo "Phase 1: Clearing existing LLM responses"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will clear all assistant_response data!"
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

python scripts/clear_thesis_responses.py \
    --tickers "$TICKERS" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE"

echo ""
echo "✓ Phase 1 complete"
echo ""

# Phase 2: Regenerate theses
echo "=========================================="
echo "Phase 2: Regenerating theses"
echo "=========================================="
echo ""
echo "This will regenerate all theses using the pipeline."
echo "This may take several hours depending on API rate limits."
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

python main.py \
    --start-date "$START_DATE" \
    --end-date "$END_DATE"

echo ""
echo "✓ Phase 2 complete"
echo ""

# Phase 3: Regenerate datasets
echo "=========================================="
echo "Phase 3: Regenerating RLVR datasets"
echo "=========================================="
echo ""

python rlvr_main.py generate \
    --train-split-date "$TRAIN_END_DATE" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "✓ Phase 3 complete"
echo ""

# Phase 4: Validate
echo "=========================================="
echo "Phase 4: Validating datasets"
echo "=========================================="
echo ""

python rlvr_main.py qa \
    --train-file "$OUTPUT_DIR/train.jsonl" \
    --dev-file "$OUTPUT_DIR/dev.jsonl"

echo ""
echo "=========================================="
echo "✓ Regeneration complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  Train file: $OUTPUT_DIR/train.jsonl"
echo "  Dev file: $OUTPUT_DIR/dev.jsonl"
echo ""
echo "Next steps:"
echo "  1. Review the generated datasets"
echo "  2. Deploy reward function if needed: python rlvr_main.py deploy"
echo "  3. Submit training job: python rlvr_main.py train"
echo ""
