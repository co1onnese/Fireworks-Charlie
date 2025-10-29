#!/bin/bash
# Setup script for Fireworks-Charlie

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "Fireworks-Charlie Setup"
echo "================================================"

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    cd "$PROJECT_DIR"
    uv venv
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$PROJECT_DIR/.venv/bin/activate"

# Install dependencies
echo ""
echo "Installing dependencies..."
cd "$PROJECT_DIR"
uv pip install -e ".[dev]"

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure API keys"
echo "2. Initialize database with ./scripts/init_db.sh"
echo "3. Run pipeline with ./scripts/run_pipeline.sh"
echo ""