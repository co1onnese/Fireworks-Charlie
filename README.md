# Fireworks-Charlie

RLVR training pipeline for stock prediction. Collects financial data, generates investment theses using DeepSeek, tracks positions, and produces JSONL datasets for GRPO fine-tuning on Fireworks AI.

## Quick Start

```bash
# Setup
cp .env.example .env
# Add your API keys to .env

source .venv/bin/activate
uv pip install -e ".[dev]"

# Initialize database
psql -c "CREATE DATABASE fireworks_charlie;"
psql fireworks_charlie < database/01_tables.sql
psql fireworks_charlie < database/02_indexes.sql
psql fireworks_charlie < database/03_views.sql
psql fireworks_charlie < database/04_functions.sql

# Verify
python rlvr_main.py validate
```

## Complete Workflow

### 1. Collect Data & Generate Theses

```bash
python main.py \
  --tickers NFLX,XOM,MA,HD,SBUX \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

**What this does:**
- Fetches market data (OHLCV, fundamentals, news) from EODHD
- Fetches macroeconomic data from FRED
- Calculates technical indicators (SMA, RSI, MACD, Bollinger Bands)
- Generates investment theses using DeepSeek for each trading day
- **Automatically creates position records** (3-day hold with early exit)
- Saves everything to PostgreSQL

**Checkpoints:** Pipeline auto-resumes on failure. Skip with `--no-resume`.

### 2. Backfill Positions (One-Time)

If you have existing theses without positions:

```bash
# Preview what will be created
python scripts/backfill_positions.py

# Execute
python scripts/backfill_positions.py --execute --yes
```

### 3. Clean Database (Optional)

Remove test tickers before training:

```bash
# Preview deletions
python scripts/cleanup_database.py

# Execute (keeps only production tickers from .env)
python scripts/cleanup_database.py --execute --yes
```

### 4. Generate RLVR Datasets

```bash
python rlvr_main.py generate \
  --tickers NFLX,XOM,MA,HD,SBUX \
  --output-dir storage/rlvr_datasets
```

**Output:**
- `storage/rlvr_datasets/train.jsonl` - Training set (80%)
- `storage/rlvr_datasets/dev.jsonl` - Dev set (20%)

**Format:**
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "{\"reasoning\": \"...\", \"action\": \"buy\", \"support\": \"...\"}"}
  ],
  "ground_truth": {
    "actual_return_pct": 2.5,
    "exit_date": "2024-01-05",
    "days_held": 3,
    "early_exit": false
  },
  "metadata": {
    "ticker": "NFLX",
    "entry_date": "2024-01-02",
    "historical_returns": [1.2, -0.5, 3.1, ...],
    "thesis_id": 12345
  }
}
```

### 5. Test & Deploy Reward Function

```bash
# Test locally
python rlvr_main.py test-local --sample

# Deploy to Fireworks AI
python rlvr_main.py deploy
```

### 6. Train Model

```bash
# Submit GRPO training job
python rlvr_main.py train

# Check status
python rlvr_main.py status
```

## Configuration

### Required API Keys

```env
# Database
DB_URL=postgresql://user:password@localhost/fireworks_charlie

# Fireworks AI (required for RLVR training)
FIREWORKS_API_KEY=fw_xxx
FIREWORKS_ACCOUNT_ID=accounts/xxx

# LLM Provider (choose one for thesis generation)
LLM_PROVIDER=deepseek  # or "fireworks"

# DeepSeek (recommended - lower cost/latency)
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat

# Data Sources
EODHD_API_KEY=xxx  # Market data
FRED_API_KEY=xxx   # Macroeconomic data

# Tickers
TICKERS=NFLX,XOM,MA,HD,SBUX
START_DATE=2024-01-01
END_DATE=2024-12-31
```

### Reward Function Weights

```env
DIRECTIONAL_ACCURACY_WEIGHT=80  # Binary correctness
SHARPE_RATIO_WEIGHT=20          # Risk-adjusted return
```

**Directional Accuracy:** Binary scoring based on action thresholds
| Action | Correct If |
|--------|-----------|
| strong_buy | return ≥ 3.0% |
| buy | return ≥ 2.0% |
| hold | -1.0% ≤ return ≤ 1.0% |
| sell | return ≤ -2.0% |
| strong_sell | return ≤ -3.0% |

**Sharpe Score:** Normalized to [0, 1] using 30-day historical returns

### Position Tracking

```env
POSITION_HOLD_DAYS=3
EARLY_EXIT_ON_SIGNAL_CHANGE=true
```

**Logic:**
- Entry: Thesis `as_of_date`, close price
- Hold: 3 trading days OR early exit if signal changes to hold/sell on day 2-3
- Exit: Close price at exit
- Return: `((exit_price - entry_price) / entry_price) × 100`

## CLI Reference

```bash
# Main pipeline
python main.py [--tickers TICKERS] [--start-date DATE] [--end-date DATE] [--no-resume]

# RLVR commands
python rlvr_main.py generate    # Generate datasets
python rlvr_main.py test-local  # Test reward function
python rlvr_main.py deploy      # Deploy to Fireworks AI
python rlvr_main.py train       # Submit training job
python rlvr_main.py status      # Check training status
python rlvr_main.py stats       # Show statistics
python rlvr_main.py validate    # Validate setup

# Utilities
python scripts/cleanup_database.py [--execute] [--yes]
python scripts/backfill_positions.py [--execute] [--yes]
```

## Common Issues

### "No positions found"

**Cause:** Thesis generations exist but positions table is empty.

**Solution:**
```bash
python scripts/backfill_positions.py --execute --yes
```

### "Reward function deployment failed"

**Cause:** `reward-kit` not installed or misconfigured.

**Solution:**
```bash
uv pip install --upgrade 'fireworks-ai[reward-kit]'
python rlvr_main.py deploy
```

### "Insufficient future data"

**Cause:** Recent theses (last 3 days) can't create positions yet.

**Solution:** This is normal. Wait for more trading days or run pipeline for older dates.

### "Token budget exceeded"

**Cause:** Prompt too large (>120K tokens).

**Solution:** Enable compression in `.env`:
```env
ENABLE_AGGRESSIVE_COMPRESSION=true
MAX_DAYS_RECENT=7
MAX_DAYS_MEDIUM=30
```

### Database connection failed

**Solution:**
```bash
# Verify PostgreSQL is running
sudo service postgresql status

# Test connection
psql $DB_URL -c "SELECT 1;"

# Check credentials in .env
```

## Architecture

```
External APIs          Database              Fireworks AI
┌─────────────┐       ┌──────────────┐      ┌──────────────┐
│ EODHD       │──────▶│ PostgreSQL   │◀─────│ DeepSeek V3  │
│ FRED        │       │              │      │ GRPO Training│
│ News APIs   │       │ • Theses     │      │ Reward Func  │
└─────────────┘       │ • Positions  │      └──────────────┘
                      │ • Market Data│
                      └──────────────┘
                             │
                             ▼
                      ┌──────────────────────────────────┐
                      │   Fireworks-Charlie Pipeline     │
                      │                                  │
                      │  1. Data Collection              │
                      │  2. Thesis Generation            │
                      │  3. Position Tracking            │
                      │  4. Dataset Generation           │
                      │  5. Reward Deployment            │
                      │  6. Model Training               │
                      └──────────────────────────────────┘
```

**Key Components:**

- **Data Collection** (`data_collection/`) - Multi-source API clients, feature engineering
- **Thesis Generation** (`thesis_generation/`) - LLM integration, prompt building
- **RLVR Processing** (`rlvr/`) - Position tracking, reward calculation, dataset generation
- **Orchestration** (`orchestration/`) - Pipeline coordination, checkpoints, config

**Database Schema:** 14 tables with partitioning, JSONB support, 60+ indexes. See `database/` for DDL.

## Performance

- **Pipeline:** ~2-4 hours for 5 tickers × 1 year (depends on API rate limits)
- **Dataset Generation:** ~5-10 seconds for 1000 examples
- **Reward Function:** ~37ms per example
- **Storage:** ~1GB per ticker per year

## Documentation

- **Position Tracking:** `docs/POSITION_TRACKING.md`
- **Deployment Plan:** `POSITION_TRACKING_INTEGRATION_PLAN.md`
- **Database Schema:** `database/` directory
- **API Docs:** `llms.txt` (comprehensive codebase reference)

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black .
ruff check .

# Type check
mypy .
```

**Code Style:**
- Python: PEP 8, 120 char lines, type hints required
- SQL: UPPERCASE keywords, lowercase identifiers
- Docstrings: Google style

## Version

**Version:** 2.0.0
**Last Updated:** 2025-10-30
**Python:** 3.10+
**PostgreSQL:** 13+
**Fireworks AI:** reward-kit 1.0+

---

For detailed troubleshooting, see `docs/` directory. For questions, consult `llms.txt` for codebase reference.
