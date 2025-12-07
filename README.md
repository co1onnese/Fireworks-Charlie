# Fireworks-Charlie RLVR Pipeline

Production-grade RLVR (Reinforcement Learning with Verifiable Rewards) training pipeline for financial market prediction. Collects multi-source financial data, generates investment theses using LLMs, tracks positions with verifiable outcomes, and produces JSONL datasets for GRPO fine-tuning on Fireworks AI.

**Architecture**: PostgreSQL + Fireworks AI + DeepSeek/Fireworks LLM providers → Point-in-time data → Hierarchical prompting → Position tracking → Multi-metric reward calculation → GRPO training → Model evaluation with 3 trading strategies.

---

## Quick Start

### 1. Setup

```bash
# Install dependencies
cp .env.example .env
source .venv/bin/activate
uv pip install -e ".[dev]"

# Configure API keys in .env
# Database, Fireworks AI, DeepSeek/Fireworks, EODHD, FRED

# Initialize database
psql -c "CREATE DATABASE fireworks_charlie;"
psql fireworks_charlie < database/01_tables.sql
psql fireworks_charlie < database/02_indexes.sql
psql fireworks_charlie < database/03_views.sql
psql fireworks_charlie < database/04_functions.sql

# Validate setup
python rlvr_main.py validate
```

### 2. Complete Workflow

```bash
# Phase 1: Data Collection & Thesis Generation
python main.py --tickers AAPL,MSFT,NFLX --start-date 2024-01-01 --end-date 2024-12-31

# Phase 2: Generate RLVR Datasets
python rlvr_main.py generate --tickers AAPL,MSFT,NFLX --output-dir storage/rlvr_datasets

# Phase 3: Start Evalprotocol Server
python rlvr/run_evalprotocol_server.py --reload

# Phase 4: Submit GRPO Training Job (via Fireworks Dashboard)
# Navigate to https://fireworks.ai/fine-tuning
# Select "Reinforcement" method
# Upload train.jsonl and dev.jsonl
# Select base model (llama-v3p1-8b-instruct recommended)
# Configure evaluator: Use HTTP endpoint http://localhost:8000/init
# Launch training job

# Phase 5: Monitor Training
python rlvr_main.py status --job-id YOUR_JOB_ID

# Phase 6: Evaluate Model (when deployment complete)
python scripts/evaluate_model.py --fine-tuned-model accounts/lstn/models/YOUR_MODEL_ID --strategy A
```

---

## System Architecture

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
                      │  3. Position Tracking (3-day)    │
                      │  4. Dataset Generation           │
                      │  5. Reward Deployment            │
                      │  6. Model Training               │
                      │  7. Model Evaluation (A/B/C)     │
                      └──────────────────────────────────┘
```

---

## 🚀 NEW: Evalprotocol Server (v2.1+)

**BREAKING CHANGE**: The reward function system has been completely redesigned to use the new evalprotocol HTTP API standard instead of the legacy reward-kit framework.

### Migration from Reward-Kit to Evalprotocol

**What Changed**:
- ❌ **Old**: `@reward_function` decorator with reward-kit deployment
- ✅ **New**: FastAPI HTTP server with POST `/init` endpoint
- ✅ **Maintained**: All existing reward calculation logic and metrics
- ✅ **Enhanced**: True "Ground Truth" evaluation with 3-day performance tracking

**Why the Change**:
Fireworks.ai updated their API requirements to use evalprotocol standards for better scalability, monitoring, and integration with their RLVR training infrastructure.

### Quick Start - Evalprotocol Server

#### 1. Install Evalprotocol Dependencies

```bash
# Install additional dependencies for evalprotocol server
pip install -r rlvr/requirements_evalprotocol.txt
```

#### 2. Start the Server (Development)

```bash
# Start with auto-reload for development
python rlvr/run_evalprotocol_server.py --reload --log-level debug

# Or with basic configuration
python rlvr/run_evalprotocol_server.py
```

Server starts on `http://localhost:8000`

#### 3. Start the Server (Production)

```bash
# Using Docker Compose (recommended)
cd rlvr
docker-compose -f docker-compose.evalprotocol.yml up -d

# Or using Gunicorn
gunicorn rlvr.evalprotocol_server:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

#### 4. Health Check

```bash
# Test server is running
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "service": "evalprotocol-server"}
```

#### 5. Stop the Server

```bash
# Development server: Ctrl+C

# Docker Compose:
docker-compose -f rlvr/docker-compose.evalprotocol.yml down

# Gunicorn: Kill the process or use process manager
```

### Evalprotocol Server Features

#### Ground Truth Stock Evaluation
The server evaluates stock predictions against **actual 3-day market performance**:

1. **Receives Prediction**: Stock analysis with buy/sell/hold recommendation
2. **Tracks Position**: Monitors actual stock price for 3 trading days
3. **Calculates Return**: Measures real performance: `(exit_price - entry_price) / entry_price × 100`
4. **Multi-Metric Scoring**: Uses sophisticated 6-component reward system
5. **Returns Evaluation**: Provides detailed score breakdown and reasoning

#### API Endpoints

**POST /init** - Main evaluation endpoint
```bash
curl -X POST http://localhost:8000/init \
  -H "Content-Type: application/json" \
  -d '{
    "completion_params": {"model": "gpt-4", "temperature": 0.7},
    "messages": [
      {"role": "user", "content": "Analyze AAPL stock"},
      {"role": "assistant", "content": "{\"action\": \"buy\", \"reasoning\": \"Strong fundamentals\", \"support\": \"Revenue growth\"}"}
    ],
    "tools": [],
    "model_base_url": "https://api.openai.com",
    "metadata": {"rollout_id": "test-123"},
    "api_key": "your-key"
  }'
```

**Response Format**:
```json
{
  "status": "success",
  "rollout_id": "test-123",
  "evaluation": {
    "score": 0.85,
    "reason": "R:0.850 | Dir:✓ | Mag:0.92 | Sharpe:0.65 | Cal:0.80 | buy→+2.3%",
    "metrics": {
      "directional_accuracy": {"score": 1.0, "success": true},
      "magnitude_accuracy": {"score": 0.92, "success": true},
      "sharpe_score": {"score": 0.65, "success": true},
      "confidence_calibration": {"score": 0.80, "success": true},
      "downside_protection": {"score": 0.95},
      "reasoning_quality": {"score": 0.75, "success": true}
    },
    "actual_return_pct": 2.3,
    "prediction": {"action": "buy", "symbol": "AAPL"}
  }
}
```

**GET /health** - Health check endpoint
```bash
curl http://localhost:8000/health
```

### Configuration Requirements

#### Environment Variables

```env
# Database Connection (required)
DATABASE_URL=postgresql://user:password@localhost:5432/fireworks_charlie

# Alternative database config
DB_HOST=localhost
DB_NAME=fireworks_charlie
DB_USER=your_user
DB_PASSWORD=your_password
DB_PORT=5432

# Server Configuration (optional)
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=info

# Fireworks Tracing (for production)
FIREWORKS_API_KEY=fw_xxx
```

#### Docker Environment

```bash
# Start complete environment with database
cd rlvr
docker-compose -f docker-compose.evalprotocol.yml up -d

# Services started:
# - evalprotocol-server (port 8000)
# - postgres (port 5432)
# - redis (port 6379)
```

### Testing the Evalprotocol Server

```bash
# Run comprehensive test suite
python rlvr/run_tests.py --verbose --coverage

# Run specific tests
pytest rlvr/tests/test_evalprotocol_server.py -v

# Test server manually
python -c "
import requests
response = requests.get('http://localhost:8000/health')
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
"
```

### Migration Guide

#### For Existing Users

1. **Update Dependencies**:
   ```bash
   pip install -r rlvr/requirements_evalprotocol.txt
   ```

2. **Start Evalprotocol Server**:
   ```bash
   python rlvr/run_evalprotocol_server.py
   ```

3. **Update Training Jobs**:
   - Use the new HTTP server endpoint instead of deployed reward functions
   - No changes needed to dataset format or training configuration
   - All existing reward calculation logic is preserved

#### Backward Compatibility

- ❌ **Old reward-kit deployment commands will not work**
- ✅ **All existing datasets remain compatible**
- ✅ **All reward calculation logic is preserved**
- ✅ **Database schema unchanged**

### Detailed Documentation

For complete implementation details, API specifications, and advanced configuration:

📖 **[Evalprotocol Server Documentation](rlvr/README_evalprotocol.md)**

---

## Configuration

### Required Environment Variables

```env
# Database
DB_URL=postgresql://user:password@localhost/fireworks_charlie

# LLM Provider (choose one for thesis generation)
LLM_PROVIDER=deepseek  # or "fireworks"

# DeepSeek (recommended)
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Fireworks AI (for GRPO training)
FIREWORKS_API_KEY=fw_xxx
FIREWORKS_ACCOUNT_ID=accounts/xxx
MODEL_NAME=llama-v3p1-8b-instruct

# Data Sources
EODHD_API_KEY=xxx
FRED_API_KEY=xxx

# Dataset Parameters
TICKERS=AAPL,MSFT,NFLX,HD,SBUX
START_DATE=2024-01-01
END_DATE=2024-12-31

# Reward Function Weights
DIRECTIONAL_ACCURACY_WEIGHT=80
SHARPE_RATIO_WEIGHT=20
```

### Reward Function Thresholds

| Action | Correct If Return |
|--------|------------------|
| STRONG_BUY | ≥ 3.0% |
| BUY | ≥ 2.0% |
| HOLD | -2.0% ≤ return ≤ 2.0% |
| SELL | ≤ -2.0% |
| STRONG_SELL | ≤ -3.0% |

**Advanced Reward Function (6 metrics)**:
- Directional Accuracy (40%)
- Magnitude Accuracy (25%)
- Sharpe Ratio (20%)
- Confidence Calibration (10%)
- Downside Protection (5%)
- Reasoning Quality (multiplier)

---

## Core Workflows

### Workflow 1: Initial Setup & Data Collection

**Generate Theses**:
```bash
python main.py \
  --tickers NFLX,XOM,MA,HD,SBUX \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

**What happens**:
1. Fetches market data (OHLCV, fundamentals, news) from EODHD
2. Fetches macroeconomic data from FRED
3. Calculates technical indicators (SMA, RSI, MACD, Bollinger Bands)
4. Generates investment theses using DeepSeek for each trading day
5. Creates position tracking records (3-day hold with early exit)
6. Saves everything to PostgreSQL

**Checkpoints**: Pipeline auto-resumes on failure. Skip with `--no-resume`.

**Performance**: ~2-4 hours for 5 tickers × 1 year (depends on API rate limits)

---

### Workflow 2: RLVR Dataset Generation

**Generate Training Data**:
```bash
python rlvr_main.py generate \
  --tickers NFLX,XOM,MA,HD,SBUX \
  --output-dir storage/rlvr_datasets
```

**Output**:
- `storage/rlvr_datasets/train.jsonl` - Training set (80%)
- `storage/rlvr_datasets/dev.jsonl` - Dev set (20%)

**Format**:
```json
{
  "messages": [
    {"role": "system", "content": "You are a financial analyst..."},
    {"role": "user", "content": "Complete data prompt..."}
  ],
  "ground_truth": {
    "actual_return_pct": 2.5,
    "exit_date": "2024-01-05",
    "days_held": 3,
    "early_exit": false,
    "entry_price": 100.0,
    "exit_price": 102.5
  },
  "metadata": {
    "ticker": "AAPL",
    "entry_date": "2024-01-02",
    "historical_returns": [1.2, -0.5, 3.1, ...],
    "thesis_id": 12345,
    "position_id": "pos_1_2024-01-02"
  }
}
```

**Performance**: ~5-10 seconds for 1000 examples

---

### Workflow 3: Evalprotocol Server Setup

**Start Development Server**:
```bash
python rlvr/run_evalprotocol_server.py --reload --log-level debug
```

**Start Production Server**:
```bash
cd rlvr
docker-compose -f docker-compose.evalprotocol.yml up -d
```

**Test Server**:
```bash
curl http://localhost:8000/health
```

**Expected Output**:
```json
{"status": "healthy", "service": "evalprotocol-server"}
```

**Server Features**:
- **Ground Truth Evaluation**: Real 3-day stock performance tracking
- **Multi-Metric Scoring**: 6 sophisticated evaluation components
- **HTTP API**: RESTful endpoint for RLVR training integration
- **Fireworks Tracing**: Integrated logging and status reporting

---

### Workflow 4: GRPO Training (Fireworks Dashboard)

**Step-by-Step**:

1. **Navigate to Fine-Tuning**
   - Go to https://fireworks.ai
   - Click "Fine-Tuning" → "Fine-tune a Model"

2. **Select Method**: "Reinforcement" (not Supervised!)

3. **Upload Datasets**
   - Training: `storage/rlvr_datasets/train.jsonl`
   - Evaluation: `storage/rlvr_datasets/dev.jsonl` (optional but recommended)

4. **Select Base Model**
   - Recommended: `accounts/fireworks/models/llama-v3p1-8b-instruct`

5. **Configure Evaluator**
   - **Method**: HTTP Endpoint
   - **URL**: `http://localhost:8000/init` (or your server URL)
   - **Critical**: Ensure evalprotocol server is running before training

6. **Configure Parameters**
   - Epochs: 1 (start with 1)
   - Learning Rate: 1e-4 (default)
   - LoRA Rank: 8
   - Max Context Length: 8192
   - Temperature: 0.7 (must be > 0 for exploration!)
   - N (choices): 4

7. **Launch Training Job**

**Expected Training Time**: 2-6 hours (depends on dataset size and GPU availability)

**Timeline**:
```
0-10 min:    Initialization
10 min-4h:   Training (generate → evaluate → update)
4h-4.5h:     Evaluation on dev set
4.5h-5h:     Finalization (save checkpoint, upload model)
```

---

### Workflow 5: Model Evaluation (3 Trading Strategies)

**Check Model Status**:
```bash
python scripts/check_model_status.py \
  --model-name accounts/lstn/models/YOUR_MODEL_ID
```

**Evaluate Strategies A, B, C**:
```bash
for strategy in A B C; do
  python scripts/evaluate_model.py \
    --fine-tuned-model accounts/lstn/models/YOUR_MODEL_ID \
    --strategy $strategy
done
```

**Performance**: ~2-3 hours for full evaluation

---

## Trading Strategies

### Strategy A: Long-Only (Conservative)
**Risk**: Low | **Leverage**: None | **Tested**: ✅

```
BUY/STRONG_BUY   → Long position  → Return = actual_return
HOLD/SELL        → No position    → Return = 0%
```

**When to use**: Conservative portfolios, long-only mandates, baseline testing

---

### Strategy B: Long/Short (Moderate)
**Risk**: Medium | **Leverage**: None | **Tested**: ✅

```
BUY/STRONG_BUY   → Long position   → Return = +actual_return
SELL/STRONG_SELL → Short position  → Return = -actual_return
HOLD             → No position     → Return = 0%
```

**When to use**: Profit from both directions, hedge fund strategies

---

### Strategy C: Weighted (Aggressive)
**Risk**: High | **Leverage**: 2x | **Tested**: ✅

```
STRONG_BUY   → 2x long position      → Return = 2 × actual_return
BUY          → 1x long position      → Return = actual_return
HOLD         → No position           → Return = 0%
SELL         → -1x short position    → Return = -actual_return
STRONG_SELL  → -2x short position    → Return = -2 × actual_return
```

**Warning**: Amplifies both gains AND losses by 2x!

---

## Position Tracking

**3-Day Hold Logic**:
- Entry: Thesis `as_of_date`, close price
- Hold: 3 trading days OR early exit if signal changes to hold/sell on day 2-3
- Exit: Close price at exit
- Return: `((exit_price - entry_price) / entry_price) × 100`

**Configuration**:
```env
POSITION_HOLD_DAYS=3
EARLY_EXIT_ON_SIGNAL_CHANGE=true
```

---

## CLI Reference

### Main Pipeline
```bash
python main.py [--tickers TICKERS] [--start-date DATE] [--end-date DATE] [--no-resume]
```

### RLVR Commands
```bash
python rlvr_main.py validate     # Validate setup
python rlvr_main.py generate     # Generate datasets
python rlvr_main.py train        # Submit training job
python rlvr_main.py status       # Check training status
python rlvr_main.py stats        # Show statistics
```

### Evalprotocol Server Commands
```bash
# Start development server
python rlvr/run_evalprotocol_server.py [--reload] [--log-level debug]

# Run tests
python rlvr/run_tests.py [--verbose] [--coverage]

# Docker deployment
docker-compose -f rlvr/docker-compose.evalprotocol.yml up -d
docker-compose -f rlvr/docker-compose.evalprotocol.yml down

# Health check
curl http://localhost:8000/health
```

### Utilities
```bash
# Cleanup database
python scripts/cleanup_database.py [--execute] [--yes]

# Backfill positions (for existing theses)
python scripts/backfill_positions.py [--execute] [--yes]

# Evaluate model
python scripts/evaluate_model.py \
  --fine-tuned-model MODEL_ID \
  --strategy A  # or B, or C

# Check model status
python scripts/check_model_status.py \
  --model-name MODEL_ID \
  [--monitor]
```

---

## Expected Results

### Training Metrics
- **Average Reward**: Should increase from ~0.5 to 0.6-0.8
- **Directional Accuracy**: 50-60% (vs 20% random)
- **Loss**: Should decrease over time

### Evaluation Metrics

| Quality | Accuracy | Sharpe Ratio | Mean Return |
|---------|----------|--------------|-------------|
| Random | ~20% | 0.0 | ~0% |
| Decent | 40-45% | 0.5-1.0 | Positive |
| **Good** | **50-55%** | **1.0-2.0** | **> Buy-and-hold** |
| Excellent | 60%+ | 2.0+ | >> Buy-and-hold |

### Strategy Performance (Typical)
- **Strategy A**: Sharpe 1.2-1.8 (conservative, baseline)
- **Strategy B**: Sharpe 1.5-2.2 (usually highest, profits both directions)
- **Strategy C**: Sharpe 1.0-2.5 (highest variance, 2x leverage)

---

## Database Schema

**14 Tables with partitioning and JSONB support**:

- **Ticker** - Master ticker registry
- **MarketData** - Daily OHLCV + technical indicators (partitioned by date)
- **Fundamental** - Quarterly financial statements
- **News** - News articles with sentiment
- **MacroeconomicIndicator** - Economic indicators from FRED
- **MacroFeature** - Derived macroeconomic features
- **TickerEventFeature** - Time-since-event features
- **NewsSentimentFeature** - Rolling news sentiment aggregates
- **InsiderTransaction** - Insider trading transactions
- **ThesisGeneration** - AI-generated investment theses
- **Position** - 3-day position tracking
- **RLVRTrainingExample** - Complete RLVR examples
- **HistoricalReturn** - Historical returns for Sharpe
- **SharpeCalculation** - Cached Sharpe calculations

**60+ indexes** for query optimization

---

## Performance Characteristics

- **Pipeline**: ~2-4 hours for 5 tickers × 1 year
- **Dataset Generation**: ~5-10 seconds for 1000 examples
- **Reward Function**: ~37ms per example
- **Training**: 2-6 hours (GRPO on Fireworks AI)
- **Evaluation**: 2-3 hours for full dataset
- **Storage**: ~1GB per ticker per year

---

## Common Issues & Solutions

### "No positions found"
**Cause**: Thesis generations exist but positions table is empty.

**Solution**:
```bash
python scripts/backfill_positions.py --execute --yes
```

### "Evalprotocol server not responding"
**Cause**: Server not started or misconfigured.

**Solution**:
```bash
# Check if server is running
curl http://localhost:8000/health

# Start server if not running
python rlvr/run_evalprotocol_server.py --reload

# Check logs for errors
python rlvr/run_evalprotocol_server.py --log-level debug
```

### "Insufficient future data"
**Cause**: Recent theses (last 3 days) can't create positions yet.

**Solution**: This is normal. Wait for more trading days or run pipeline for older dates.

### "Token budget exceeded"
**Cause**: Prompt too large (>120K tokens).

**Solution**: Enable compression in `.env`:
```env
ENABLE_AGGRESSIVE_COMPRESSION=true
MAX_DAYS_RECENT=7
MAX_DAYS_MEDIUM=30
```

### "Model not found (404)"
**Cause**: Model deployment not complete.

**Solution**:
```bash
python scripts/check_model_status.py \
  --model-name MODEL_ID --monitor
```

### "All reward scores = 0.0"
**Cause**: Dataset format issue or reward function erroring.

**Solution**:
1. Check dataset has `ground_truth` field
2. Verify evalprotocol server is running: `curl http://localhost:8000/health`
3. Test server manually with sample prediction
4. Check server logs for evaluation errors

### Training job fails immediately
**Error**: "ExecutionError: Connection refused" or "Evaluator endpoint unreachable"

**Solution**:
1. Ensure evalprotocol server is running and accessible
2. Verify server URL is correct in training job configuration
3. Check firewall/network settings if using remote server
4. Test endpoint manually: `curl -X POST http://localhost:8000/init`

### "Database connection failed"
**Cause**: Evalprotocol server cannot connect to PostgreSQL.

**Solution**:
```bash
# Check database connection
python -c "
from data_collection.database_manager import DatabaseManager
db = DatabaseManager()
print('Database connection: OK')
"

# Update DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/fireworks_charlie"
```

---

## Development

### Install
```bash
uv pip install -e ".[dev]"
```

### Run Tests
```bash
# All tests
pytest tests/ -v
pytest tests/test_evaluate_model.py -v  # 65 tests

# Evalprotocol server tests
python rlvr/run_tests.py --verbose --coverage
pytest rlvr/tests/test_evalprotocol_server.py -v
```

### Code Quality
```bash
black .
ruff check .
mypy .
```

**Standards**:
- Python: PEP 8, 120 char lines, type hints required
- SQL: UPPERCASE keywords, lowercase identifiers
- Docstrings: Google style

---

## Output Structure

### RLVR Datasets
```
storage/rlvr_datasets/
├── train.jsonl  (80%)
├── dev.jsonl    (20%)
└── README.txt
```

### Evaluation Results
```
outputs/evaluations/
├── eval_strategy_A_TIMESTAMP.json
├── eval_strategy_A_TIMESTAMP_summary.txt
├── eval_strategy_B_TIMESTAMP.json
├── eval_strategy_B_TIMESTAMP_summary.txt
├── eval_strategy_C_TIMESTAMP.json
└── eval_strategy_C_TIMESTAMP_summary.txt
```

### Training Logs
```
outputs/training/
└── manual_grpo_TIMESTAMP.json
```

---

## Key Components

**Module Hierarchy** (see `llms.txt` for complete documentation):

- **data_collection/** (11 files) - Multi-source data collection, feature engineering
- **thesis_generation/** (7 files) - LLM integration, hierarchical prompt building
- **orchestration/** (4 files) - Pipeline coordination, config, checkpoints
- **rlvr/** (9 files) - Position tracking, reward calculation, dataset generation
- **scripts/** (15+ files) - Deployment, training, evaluation utilities
- **tests/** (9 files) - Comprehensive test suite (65+ tests)

**Entry Points**:
- `rlvr_main.py` - Primary CLI for RLVR operations
- `main.py` - Data collection and thesis generation pipeline

---

## Version & Dependencies

- **Version**: 2.1 (**NEW**: Evalprotocol Server Support)
- **Python**: 3.10+
- **PostgreSQL**: 13+
- **Evalprotocol**: HTTP API standard (replaces reward-kit)

**Core Dependencies**:
- sqlalchemy (ORM)
- pandas, numpy (data)
- fireworks-ai (Fireworks client)
- trl, torch, transformers (GRPO training)
- ta (technical analysis)
- **NEW**: fastapi, uvicorn (evalprotocol server)
- **NEW**: eval-protocol (HTTP API standard)

---

## Support

### Documentation
- **Complete Code Reference**: `llms.txt` (1,200+ lines)
- **Evalprotocol Server**: `rlvr/README_evalprotocol.md` (detailed API docs)
- **Legacy Documentation**: `docs/` directory (for historical context only)

### Testing
```bash
# All tests
pytest tests/ -v

# Evaluate model tests (65 tests)
pytest tests/test_evaluate_model.py -v

# Reward function tests
python scripts/test_reward_advanced.py
```

### Getting Help
- Check troubleshooting section above
- Review logs in `outputs/` directory
- Use `python rlvr_main.py validate` to diagnose setup issues

---

## Summary

**Complete Workflow**:
1. ✅ Setup environment and database
2. ✅ Run `main.py` for data collection + thesis generation
3. ✅ Run `rlvr_main.py generate` to create RLVR datasets
4. ✅ **NEW**: Start evalprotocol server with `python rlvr/run_evalprotocol_server.py`
5. ✅ Submit GRPO training job via Fireworks dashboard (using HTTP evaluator)
6. ✅ Monitor with `rlvr_main.py status`
7. ✅ Evaluate model with `scripts/evaluate_model.py`
8. ✅ Compare strategies and choose best for production

**Everything needed to operate the complete pipeline is documented above.**

---

For comprehensive codebase documentation, see `llms.txt`.
