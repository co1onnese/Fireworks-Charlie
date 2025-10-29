#!/bin/bash
# Verify Fireworks-Charlie setup

set -e

echo "================================================"
echo "Fireworks-Charlie Setup Verification"
echo "================================================"

# Check Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    echo "✓ $(python3 --version)"
else
    echo "✗ Python not found"
    exit 1
fi

# Check uv
echo -n "Checking uv... "
if command -v uv &> /dev/null; then
    echo "✓ Found"
else
    echo "✗ Not found - please install uv"
    exit 1
fi

# Check PostgreSQL client
echo -n "Checking PostgreSQL client... "
if command -v psql &> /dev/null; then
    echo "✓ $(psql --version | head -n1)"
else
    echo "✗ Not found - please install PostgreSQL client"
fi

# Check directory structure
echo ""
echo "Checking directory structure..."
DIRS=(
    "data_collection"
    "thesis_generation"
    "orchestration"
    "utils"
    "scripts"
    "storage/distilled_theses"
    "storage/checkpoints"
)

for dir in "${DIRS[@]}"; do
    if [ -d "/opt/Trainer-Charlie/$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir missing"
    fi
done

# Check key files
echo ""
echo "Checking key files..."
FILES=(
    "main.py"
    "pyproject.toml"
    ".env.example"
    "README.md"
)

for file in "${FILES[@]}"; do
    if [ -f "/opt/Trainer-Charlie/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file missing"
    fi
done

# Check .env
echo ""
if [ -f "/opt/Trainer-Charlie/.env" ]; then
    echo "✓ .env file exists"
    
    # Check for required variables (without showing values)
    echo ""
    echo "Checking required environment variables..."
    source /opt/Trainer-Charlie/.env
    
    REQUIRED_VARS=(
        "DB_URL"
        "DEEPSEEK_API_KEY"
        "START_DATE"
        "END_DATE"
        "TICKERS"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -n "${!var}" ]; then
            echo "  ✓ $var is set"
        else
            echo "  ✗ $var is not set"
        fi
    done
else
    echo "✗ .env file not found"
    echo "  Please copy .env.example to .env and configure"
fi

echo ""
echo "================================================"
echo "Setup verification complete"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Configure .env file with your API keys"
echo "2. Initialize database: ./scripts/init_db.sh"
echo "3. Run pipeline: ./scripts/run_pipeline.sh"
echo ""