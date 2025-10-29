#!/bin/bash
# Run Trainer-Charlie pipeline

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "Trainer-Charlie Pipeline Runner"
echo "================================================"

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    cd "$PROJECT_DIR"
    uv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$PROJECT_DIR/.venv/bin/activate"

# Install dependencies if needed
if ! python3 -c "import pandas" 2>/dev/null; then
    echo "Installing dependencies..."
    cd "$PROJECT_DIR"
    uv pip install -e .
fi

# Check for .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure your API keys"
    exit 1
fi

# Run the pipeline
echo ""
echo "Starting pipeline..."
echo ""

cd "$PROJECT_DIR"
python3 -m main "$@"