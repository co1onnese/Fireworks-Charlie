# Trainer-Charlie

A financial data collection and cumulative investment thesis generation system that combines data collection from Charlie-T1-DB with thesis generation capabilities to create comprehensive, XML-formatted investment analyses.

## Overview

Trainer-Charlie:
- Collects comprehensive market data using the Charlie-T1-DB pipeline
- Builds cumulative prompts with all historical data up to each trading day
- Generates investment theses using DeepSeek-V3 LLM
- Outputs structured XML files with one file per stock containing all daily theses
- Supports parallel processing and checkpoint-based recovery

## Features

- **Data Collection**: OHLCV, fundamentals, news, insider transactions, and macroeconomic data
- **Cumulative Analysis**: Each day's thesis incorporates all historical data
- **Intelligent Deduplication**: Removes repetitive news and macro data
- **XML Output**: Structured thesis format with reasoning, action, and support
- **Parallel Processing**: Process multiple stocks simultaneously
- **Checkpoint Recovery**: Resume processing from last successful date
- **Market Calendar**: Skips weekends and holidays automatically

## Installation

1. Clone the repository:
```bash
cd /opt/Trainer-Charlie
```

2. Create virtual environment:
```bash
uv venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
uv pip install -e .
```

4. Set up database:
```bash
# Create PostgreSQL database
createdb trainer_charlie

# Initialize schema
./scripts/init_db.sh
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

## Configuration

Key configuration in `.env`:

```env
# Database
DB_URL=postgresql://user:password@localhost/trainer_charlie

# API Keys
EODHD_API_KEY=your_key
FRED_API_KEY=your_key
DEEPSEEK_API_KEY=your_key

# Pipeline Settings
TICKERS=AAPL,NVDA,MSFT,AMZN,META
START_DATE=2024-01-01
END_DATE=2024-12-31
PARALLEL_WORKERS=2
```

## Usage

### Basic Usage

Run with default configuration:
```bash
./scripts/run_pipeline.sh
```

### Specific Tickers

Process specific stocks:
```bash
./scripts/run_pipeline.sh --tickers AAPL,MSFT,GOOGL
```

### Date Range

Specify custom date range:
```bash
./scripts/run_pipeline.sh --start-date 2024-01-01 --end-date 2024-03-31
```

### Test Mode

Quick test with limited data:
```bash
./scripts/run_pipeline.sh --test
```

### Fresh Start

Run without resuming from checkpoints:
```bash
./scripts/run_pipeline.sh --no-resume
```

## Output Format

Theses are saved as XML files in `storage/distilled_theses/`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<stock-theses ticker="AAPL" generated-by="Trainer-Charlie" version="1.0">
  <thesis>
    <as-of-date>2024-01-02</as-of-date>
    <reasoning>Comprehensive analysis based on cumulative data...</reasoning>
    <action>buy</action>
    <support>Key supporting evidence from the data...</support>
  </thesis>
  <thesis>
    <as-of-date>2024-01-03</as-of-date>
    <reasoning>Updated analysis with new data...</reasoning>
    <action>strong_buy</action>
    <support>Additional bullish signals...</support>
  </thesis>
  <!-- More thesis entries... -->
</stock-theses>
```

### Action Values
- `strong_buy`: Strong conviction to buy
- `buy`: Recommendation to buy
- `hold`: Maintain current position
- `sell`: Recommendation to sell
- `strong_sell`: Strong conviction to sell
- `error`: Failed to generate thesis

## Architecture

### Data Collection (from Charlie-T1-DB)
- **database_manager.py**: SQLAlchemy models and DB operations
- **data_processor.py**: Data transformation and normalization
- **eodhd_client.py**: EODHD API client
- **fred_client.py**: FRED API client
- **feature_engineering.py**: Technical indicators and features

### Thesis Generation
- **prompt_builder.py**: Builds cumulative prompts with deduplication
- **data_deduplicator.py**: Removes repetitive data
- **llm_client.py**: DeepSeek-V3 integration
- **xml_thesis_generator.py**: XML generation with validation

### Orchestration
- **main_pipeline.py**: Coordinates the entire pipeline
- **config_manager.py**: Centralized configuration
- **market_calendar.py**: Trading day detection
- **checkpoint_manager.py**: State persistence

## Monitoring

Check logs in real-time:
```bash
tail -f logs/trainer_charlie_$(date +%Y%m%d).log
```

View checkpoint status:
```bash
ls -la storage/checkpoints/
```

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check DB_URL in .env
- Ensure database exists and user has permissions

### API Issues
- Verify API keys are set in .env
- Check rate limits
- Monitor API status pages

### LLM Generation Failures
- Check DeepSeek API key and credits
- Monitor token usage
- Review error entries in XML files

### Resume from Checkpoint
If pipeline fails, it will automatically resume from the last successful date when rerun.

## Development

Run tests:
```bash
pytest tests/
```

Format code:
```bash
black .
ruff check .
```

## License

Proprietary - All rights reserved