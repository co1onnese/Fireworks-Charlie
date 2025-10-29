# Fireworks-Charlie

**RLVR Training Pipeline for Stock Prediction with GRPO on Fireworks AI**

A comprehensive system for collecting financial data, generating investment theses using DeepSeek V3.1-Terminus, and creating RLVR (Reinforcement Learning with Verifiable Rewards) training datasets for GRPO (Group Relative Policy Optimization) fine-tuning on Fireworks AI.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [API Reference](#api-reference)
- [Advanced Topics](#advanced-topics)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Performance](#performance)
- [Contributing](#contributing)
- [License](#license)

## Overview

Fireworks-Charlie is a complete RLVR training pipeline that:

- **Collects** comprehensive market data (OHLCV, fundamentals, news, macro indicators)
- **Generates** investment theses using DeepSeek V3.1-Terminus via Fireworks AI
- **Tracks** 3-day positions with early exit logic
- **Calculates** verifiable rewards (80% directional accuracy + 20% Sharpe ratio)
- **Creates** JSONL datasets for GRPO fine-tuning
- **Deploys** reward functions and trains models on Fireworks AI

### Key Features

- **RLVR Training**: Complete pipeline for Reinforcement Learning with Verifiable Rewards
- **GRPO Support**: Group Relative Policy Optimization for multi-response generation
- **Position Tracking**: 3-day hold period with intelligent early exit logic
- **Reward Function**: Verifiable scoring based on directional accuracy and risk-adjusted returns
- **Database Integration**: PostgreSQL with optimized schema for time-series data
- **Parallel Processing**: Multi-ticker processing with checkpoint recovery
- **JSONL Export**: Fireworks AI compatible dataset format

### Use Cases

- **Quantitative Research**: Generate training data for financial prediction models
- **RLVR Fine-tuning**: Create custom models using verifiable rewards
- **Backtesting**: Historical analysis with realistic position tracking
- **Model Development**: Iterate on reward functions and training strategies

## Quick Start

### Prerequisites

- **Python**: 3.10+ (3.11+ recommended)
- **PostgreSQL**: 13+ with 8GB+ RAM
- **Memory**: 16GB+ RAM recommended
- **Storage**: 50GB+ for market data
- **API Keys**: Fireworks AI, EODHD, FRED

### 1-Minute Setup

```bash
# Clone and setup
cd /opt/Fireworks-Charlie
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Setup database
./scripts/setup_database.sh

# Verify installation
python rlvr_main.py validate
```

### Generate Your First Dataset

```bash
# Generate RLVR dataset for AAPL
python rlvr_main.py generate --tickers NFLX --start-date 2024-01-01 --end-date 2024-01-31

# Test reward function
python rlvr_main.py test-local --sample

# View statistics
python rlvr_main.py stats
```

## Installation & Setup

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (12+), Windows 10+
- **Python**: 3.10+ with pip/uv package manager
- **PostgreSQL**: 13+ with 8GB+ RAM
- **Memory**: 16GB+ RAM (32GB+ for large datasets)
- **Storage**: 50GB+ SSD (100GB+ for full historical data)
- **Network**: Stable internet for API calls

### Step 1: Install Dependencies

```bash
# Install Python dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install PostgreSQL (macOS)
brew install postgresql
brew services start postgresql
```

### Step 2: Database Setup

```bash
# Automated setup (recommended)
./scripts/setup_database.sh

# Manual setup
createdb fireworks_charlie
psql -d fireworks_charlie -f database/01_tables.sql
psql -d fireworks_charlie -f database/02_indexes.sql
psql -d fireworks_charlie -f database/03_views.sql
psql -d fireworks_charlie -f database/04_functions.sql
```

### Step 3: Environment Configuration

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Required API Keys:**
```env
# Fireworks AI (required for RLVR)
FIREWORKS_API_KEY=your_fireworks_key_here
FIREWORKS_ACCOUNT_ID=your_account_id_here

# EODHD (required for market data)
EODHD_API_KEY=your_eodhd_key_here

# FRED (required for macro data)
FRED_API_KEY=your_fred_key_here
```

### Step 4: Verification

```bash
# Test database connection
python rlvr_main.py validate

# Test Fireworks AI connection
python scripts/test_fireworks_connection.py

# Run health check
python -c "from data_collection.database_manager import DatabaseManager; db = DatabaseManager(); print(db.health_check())"
```

## Configuration

### Environment Variables

#### Database Configuration
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fireworks_charlie
DB_USER=fireworks_app
DB_PASSWORD=your_secure_password
DB_URL=postgresql://fireworks_app:password@localhost/fireworks_charlie
```

#### Fireworks AI Configuration
```env
FIREWORKS_API_KEY=your_fireworks_key_here
FIREWORKS_ACCOUNT_ID=your_account_id_here
MODEL_NAME=accounts/fireworks/models/deepseek-v3p1-terminus
MODEL_MODE=deepseek-chat
```

#### RLVR Training Parameters
```env
# GRPO Parameters
GRPO_NUM_RESPONSES=4
GRPO_EPOCHS=1
GRPO_LEARNING_RATE=0.0001
GRPO_LORA_RANK=8
GRPO_BATCH_SIZE=32768

# Reward Function Weights (must sum to 100%)
DIRECTIONAL_ACCURACY_WEIGHT=80
SHARPE_RATIO_WEIGHT=20

# Position Management
POSITION_HOLD_DAYS=3
EARLY_EXIT_ON_SIGNAL_CHANGE=true
```

#### Data Collection Settings
```env
# Tickers to process
TICKERS=AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA

# Date range
START_DATE=2024-01-01
END_DATE=2024-12-31

# Processing
PARALLEL_WORKERS=2
BATCH_SIZE=100
```

### Configuration Classes

The system uses `ConfigManager` for centralized configuration:

```python
from orchestration.config_manager import config

# Access configuration
print(config.FIREWORKS_API_KEY)
print(config.GRPO_NUM_RESPONSES)
print(config.DIRECTIONAL_ACCURACY_WEIGHT)

# Validate configuration
config.validate()
```

## Usage Guide

### Basic Workflow

1. **Data Collection**: Gather market data for specified tickers
2. **Thesis Generation**: Generate investment theses using DeepSeek V3.1-Terminus
3. **Position Tracking**: Track 3-day positions with early exit logic
4. **Reward Calculation**: Calculate verifiable rewards
5. **Dataset Creation**: Export JSONL datasets for GRPO training

### CLI Commands

#### Generate RLVR Datasets

```bash
# Generate for specific tickers
python rlvr_main.py generate --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-01-31

# Generate with custom train/dev split
python rlvr_main.py generate --tickers AAPL --start-date 2024-01-01 --end-date 2024-12-31 --train-split-date 2024-06-01

# Generate to custom output directory
python rlvr_main.py generate --tickers AAPL --output-dir ./custom_datasets
```

#### Test Reward Function

```bash
# Test with sample data
python rlvr_main.py test-local --sample

# Test with custom data
python rlvr_main.py test-local --input-file ./test_data.jsonl
```

#### Deploy and Train

```bash
# Deploy reward function to Fireworks AI
python rlvr_main.py deploy

# Submit GRPO training job
python rlvr_main.py train

# Validate setup
python rlvr_main.py validate

# View statistics
python rlvr_main.py stats
```

### Python API

#### Generate Datasets Programmatically

```python
from rlvr.dataset_generator import RLVRDatasetGenerator
from data_collection.database_manager import DatabaseManager

# Initialize
db = DatabaseManager()
session = db.get_session()
generator = RLVRDatasetGenerator(session)

# Generate datasets
generator.generate_rlvr_datasets(
    tickers=['AAPL', 'MSFT'],
    start_date='2024-01-01',
    end_date='2024-01-31'
)
```

#### Test Reward Function

```python
from rlvr.reward_function import stock_prediction_reward

# Test with sample data
messages = [
    {"role": "system", "content": "You are a financial analyst..."},
    {"role": "user", "content": "Analyze AAPL stock..."},
    {"role": "assistant", "content": '{"reasoning": "...", "action": "buy", "support": "..."}'}
]

ground_truth = {
    "actual_return_pct": 2.5,
    "exit_date": "2024-01-05",
    "days_held": 3,
    "early_exit": False
}

result = stock_prediction_reward(messages, ground_truth=ground_truth)
print(f"Reward Score: {result.score}")
print(f"Metrics: {result.metrics}")
```

#### Position Tracking

```python
from rlvr.position_tracker import PositionTracker

tracker = PositionTracker(session)

# Track a position
result = tracker.track_position(
    ticker_id=1,
    entry_date='2024-01-02',
    entry_price=185.50,
    predicted_action='buy'
)

print(f"Return: {result['return_pct']:.2f}%")
print(f"Days Held: {result['days_held']}")
print(f"Early Exit: {result['early_exit']}")
```

## API Reference

### CLI Commands

#### `rlvr_main.py generate`
Generate RLVR training datasets.

**Options:**
- `--tickers TICKERS`: Comma-separated list of tickers
- `--start-date START_DATE`: Start date (YYYY-MM-DD)
- `--end-date END_DATE`: End date (YYYY-MM-DD)
- `--train-split-date TRAIN_SPLIT_DATE`: Train/dev split date
- `--output-dir OUTPUT_DIR`: Output directory

**Example:**
```bash
python rlvr_main.py generate --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-01-31
```

#### `rlvr_main.py test-local`
Test reward function locally with sample data.

**Options:**
- `--sample`: Use built-in sample data
- `--input-file INPUT_FILE`: Custom input file

**Example:**
```bash
python rlvr_main.py test-local --sample
```

#### `rlvr_main.py deploy`
Deploy reward function to Fireworks AI.

**Example:**
```bash
python rlvr_main.py deploy
```

#### `rlvr_main.py train`
Submit GRPO training job to Fireworks AI.

**Example:**
```bash
python rlvr_main.py train
```

#### `rlvr_main.py validate`
Validate RLVR setup and configuration.

**Example:**
```bash
python rlvr_main.py validate
```

#### `rlvr_main.py stats`
Show RLVR statistics and database health.

**Example:**
```bash
python rlvr_main.py stats
```

### Python Classes

#### `RLVRDatasetGenerator`
Main class for generating RLVR datasets.

```python
class RLVRDatasetGenerator:
    def __init__(self, db_session)
    def generate_rlvr_datasets(self, tickers, start_date, end_date, train_split_date=None)
    def create_sample_datasets(self, output_dir="./storage/rlvr_datasets")
```

#### `PositionTracker`
Tracks positions and calculates returns.

```python
class PositionTracker:
    def __init__(self, db_session, hold_days=3, early_exit_enabled=True)
    def track_position(self, ticker_id, entry_date, entry_price, predicted_action)
    def track_positions_batch(self, positions)
    def update_all_open_positions(self)
```

#### `PerformanceCalculator`
Calculates performance metrics and rewards.

```python
class PerformanceCalculator:
    def __init__(self, db_session, directional_weight=0.80, sharpe_weight=0.20)
    def calculate_directional_accuracy(self, predicted_action, actual_return)
    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.0)
    def calculate_reward_score(self, predicted_action, actual_return, historical_returns)
```

### Database Functions

#### `calculate_position_return(ticker_id, entry_date, entry_price, predicted_action, hold_days)`
Calculates position return with early exit logic.

```sql
SELECT * FROM calculate_position_return(
    ticker_id := 1,
    entry_date := '2024-01-02',
    entry_price := 185.50,
    predicted_action := 'buy',
    hold_days := 3
);
```

#### `check_directional_accuracy(predicted_action, actual_return)`
Checks if prediction direction is correct.

```sql
SELECT * FROM check_directional_accuracy('buy', 2.5);
```

#### `calculate_sharpe_ratio(returns)`
Calculates Sharpe ratio from returns array.

```sql
SELECT * FROM calculate_sharpe_ratio(ARRAY[1.2, -0.5, 3.1, 0.8, -1.2]);
```

## Advanced Topics

### Custom Reward Functions

Extend the reward function for custom scoring:

```python
from reward_kit import reward_function, EvaluateResult, MetricResult

@reward_function
def custom_reward_function(messages, **kwargs):
    # Extract prediction and ground truth
    assistant_response = messages[-1]["content"]
    prediction = json.loads(assistant_response)
    ground_truth = kwargs.get("ground_truth", {})
    
    # Custom scoring logic
    custom_score = calculate_custom_score(prediction, ground_truth)
    
    return EvaluateResult(
        score=custom_score,
        is_score_valid=True,
        reason="Custom scoring applied",
        metrics={
            "custom_metric": MetricResult(score=custom_score, reason="Custom calculation")
        }
    )
```

### Database Schema Optimization

The database uses several optimization techniques:

#### Partitioning
```sql
-- market_data is partitioned by year
CREATE TABLE market_data_2024 PARTITION OF market_data
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

#### Indexes
```sql
-- Composite index for RLVR export
CREATE INDEX idx_rlvr_export ON thesis_generations(ticker_id, as_of_date, status);

-- GIN index for JSONB columns
CREATE INDEX idx_thesis_response_gin ON thesis_generations USING GIN(assistant_response);
```

#### Materialized Views
```sql
-- Refresh materialized views for performance
SELECT refresh_all_materialized_views();
```

### Performance Tuning

#### Memory Optimization
```python
# Adjust batch sizes for memory constraints
config.BATCH_SIZE = 50  # Reduce for limited memory
config.PARALLEL_WORKERS = 1  # Reduce for single-core systems
```

#### Database Optimization
```sql
-- Increase work_mem for complex queries
SET work_mem = '256MB';

-- Enable parallel queries
SET max_parallel_workers_per_gather = 4;
```

#### API Rate Limiting
```python
# Add delays between API calls
import time
time.sleep(0.1)  # 100ms delay between requests
```

### Monitoring and Logging

#### Log Configuration
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fireworks_charlie.log'),
        logging.StreamHandler()
    ]
)
```

#### Database Monitoring
```sql
-- Check database health
SELECT * FROM database_health_check();

-- View performance statistics
SELECT * FROM v_rlvr_dataset_stats;

-- Monitor slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

## Examples

### Complete Workflow Example

```bash
#!/bin/bash
# Complete RLVR workflow example

# 1. Setup
cd /opt/Fireworks-Charlie
source .venv/bin/activate

# 2. Validate setup
python rlvr_main.py validate

# 3. Generate datasets
python rlvr_main.py generate \
    --tickers AAPL,MSFT,GOOGL \
    --start-date 2024-01-01 \
    --end-date 2024-03-31 \
    --train-split-date 2024-02-15

# 4. Test reward function
python rlvr_main.py test-local --sample

# 5. Deploy reward function
python rlvr_main.py deploy

# 6. Submit training job
python rlvr_main.py train

# 7. View results
python rlvr_main.py stats
```

### Custom Configuration Example

```python
# custom_config.py
from orchestration.config_manager import config

# Override default settings
config.TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
config.START_DATE = '2024-01-01'
config.END_DATE = '2024-12-31'
config.PARALLEL_WORKERS = 4
config.BATCH_SIZE = 200

# Custom reward weights
config.DIRECTIONAL_ACCURACY_WEIGHT = 70
config.SHARPE_RATIO_WEIGHT = 30

# Validate configuration
config.validate()
```

### Database Query Examples

```sql
-- Get latest thesis for each ticker
SELECT t.symbol, tg.as_of_date, tg.assistant_response
FROM thesis_generations tg
JOIN tickers t ON tg.ticker_id = t.ticker_id
WHERE tg.as_of_date = (
    SELECT MAX(as_of_date) 
    FROM thesis_generations tg2 
    WHERE tg2.ticker_id = tg.ticker_id
);

-- Calculate position performance by action
SELECT 
    action,
    COUNT(*) as total_positions,
    AVG(return_pct) as avg_return,
    STDDEV(return_pct) as return_stddev
FROM positions 
WHERE status = 'closed'
GROUP BY action
ORDER BY avg_return DESC;

-- Get RLVR dataset statistics
SELECT * FROM v_rlvr_dataset_stats;
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo service postgresql status

# Test connection
psql -h localhost -U fireworks_app -d fireworks_charlie -c "SELECT 1;"

# Check logs
tail -f /var/log/postgresql/postgresql-*.log
```

**Solutions:**
- Verify PostgreSQL is running
- Check DB_URL in .env
- Ensure user has proper permissions
- Verify database exists

#### API Connection Issues
```bash
# Test Fireworks AI connection
python scripts/test_fireworks_connection.py

# Check API keys
python -c "from orchestration.config_manager import config; print(config.FIREWORKS_API_KEY[:10] + '...')"
```

**Solutions:**
- Verify API keys are correct
- Check account has sufficient credits
- Verify network connectivity
- Check API rate limits

#### Memory Issues
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Monitor during processing
htop
```

**Solutions:**
- Reduce BATCH_SIZE in configuration
- Decrease PARALLEL_WORKERS
- Increase system memory
- Use swap space as temporary solution

#### Dataset Generation Issues
```bash
# Check database health
python rlvr_main.py validate

# View detailed logs
tail -f logs/fireworks_charlie_$(date +%Y%m%d).log

# Test with single ticker
python rlvr_main.py generate --tickers AAPL --start-date 2024-01-01 --end-date 2024-01-02
```

**Solutions:**
- Verify ticker symbols are valid
- Check date ranges are reasonable
- Ensure sufficient historical data
- Verify database has required data

### Performance Issues

#### Slow Database Queries
```sql
-- Identify slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 5;

-- Check index usage
EXPLAIN ANALYZE SELECT * FROM thesis_generations WHERE ticker_id = 1;
```

**Solutions:**
- Add missing indexes
- Update table statistics (ANALYZE)
- Increase work_mem
- Consider partitioning

#### Slow API Calls
```python
# Add retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def api_call():
    # API call implementation
    pass
```

**Solutions:**
- Implement retry logic
- Add request timeouts
- Use connection pooling
- Implement rate limiting

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Run with debug output
python rlvr_main.py generate --tickers AAPL --start-date 2024-01-01 --end-date 2024-01-02
```

## Architecture

### System Overview

```
???????????????????    ???????????????????    ???????????????????
?   Data Sources  ?    ?  Fireworks AI   ?    ?   PostgreSQL    ?
?                 ?    ?                 ?    ?                 ?
? ? EODHD API     ?????? ? DeepSeek V3.1 ?????? ? Market Data   ?
? ? FRED API      ?    ? ? GRPO Training ?    ? ? Theses        ?
? ? News APIs     ?    ? ? Reward Func   ?    ? ? Positions     ?
???????????????????    ???????????????????    ???????????????????
         ?                       ?                       ?
         ?                       ?                       ?
???????????????????????????????????????????????????????????????????
?                    Fireworks-Charlie Pipeline                   ?
?                                                                 ?
?  ???????????????  ???????????????  ???????????????  ??????????? ?
?  ?   Data      ?  ?   Thesis    ?  ?  Position   ?  ? Reward  ? ?
?  ? Collection  ?  ? Generation  ?  ?  Tracking   ?  ?Function ? ?
?  ???????????????  ???????????????  ???????????????  ??????????? ?
?                                                                 ?
?  ??????????????????????????????????????????????????????????????? ?
?  ?              RLVR Dataset Generation                        ? ?
?  ?                                                             ? ?
?  ?  ???????????????  ???????????????  ???????????????        ? ?
?  ?  ?   Training  ?  ? Development ?  ?    Test     ?        ? ?
?  ?  ?   Dataset   ?  ?   Dataset   ?  ?   Dataset   ?        ? ?
?  ?  ???????????????  ???????????????  ???????????????        ? ?
?  ??????????????????????????????????????????????????????????????? ?
???????????????????????????????????????????????????????????????????
```

### Component Architecture

#### Data Collection Layer
- **DatabaseManager**: SQLAlchemy ORM and database operations
- **EODHDClient**: Market data API integration
- **FREDClient**: Macroeconomic data integration
- **FeatureEngineering**: Technical indicators and features

#### Thesis Generation Layer
- **FireworksDeepSeekClient**: DeepSeek V3.1-Terminus integration
- **PromptBuilder**: Cumulative prompt construction
- **DataDeduplicator**: Remove repetitive data

#### RLVR Processing Layer
- **PositionTracker**: 3-day position tracking with early exit
- **PerformanceCalculator**: Reward calculation and metrics
- **RewardFunction**: Fireworks AI reward function decorator
- **DatasetGenerator**: JSONL dataset creation

#### Orchestration Layer
- **MainPipeline**: End-to-end workflow coordination
- **ConfigManager**: Centralized configuration
- **CheckpointManager**: State persistence and recovery
- **MarketCalendar**: Trading day detection

### Data Flow

1. **Data Collection**: Market data ? PostgreSQL
2. **Thesis Generation**: Historical data ? DeepSeek V3.1-Terminus ? JSON theses
3. **Position Tracking**: Theses ? 3-day positions ? Performance metrics
4. **Reward Calculation**: Performance ? Verifiable rewards
5. **Dataset Creation**: All data ? JSONL datasets
6. **Model Training**: Datasets ? GRPO fine-tuning ? Deployed model

## Performance

### Benchmarks

#### Dataset Generation
- **Small Dataset** (1 ticker, 1 month): ~2 minutes
- **Medium Dataset** (5 tickers, 3 months): ~15 minutes
- **Large Dataset** (10 tickers, 1 year): ~2 hours

#### Reward Function
- **Single Example**: ~37ms average
- **Batch Processing** (100 examples): ~3.7 seconds
- **Memory Usage**: ~50MB per 1000 examples

#### Database Performance
- **Query Response**: <100ms for most queries
- **Index Usage**: 95%+ for RLVR queries
- **Storage**: ~1GB per year of data per ticker

### Optimization Tips

#### Memory Optimization
```python
# Reduce memory usage
config.BATCH_SIZE = 50
config.PARALLEL_WORKERS = 1

# Use generators for large datasets
def process_large_dataset():
    for batch in get_data_batches():
        yield process_batch(batch)
```

#### Database Optimization
```sql
-- Maintain statistics
ANALYZE;

-- Use appropriate indexes
CREATE INDEX CONCURRENTLY idx_optimized ON table_name(column);

-- Partition large tables
CREATE TABLE market_data_2025 PARTITION OF market_data
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

#### API Optimization
```python
# Implement connection pooling
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

## Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd Fireworks-Charlie

# Setup development environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/ -v

# Format code
black .
ruff check .
```

### Code Style

- **Python**: Follow PEP 8 with 120 character line limit
- **SQL**: Use UPPERCASE for keywords, lowercase for identifiers
- **Documentation**: Use Google-style docstrings
- **Type Hints**: Use type hints for all function parameters and returns

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_reward_function.py -v

# Run integration tests
pytest tests/test_integration.py -v
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run all tests and linting
5. Submit pull request with description
6. Address review feedback

## License

Proprietary - All rights reserved

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-29  
**Compatible With**: Fireworks AI, DeepSeek V3.1-Terminus, PostgreSQL 13+

For support or questions, please refer to the troubleshooting section or contact the development team.