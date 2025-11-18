# Training Dataset Generation Plan
## Complete Plan for RLVR Training Dataset Generation

**Date**: 2025-11-16  
**Goal**: Generate training and development datasets for RLVR/GRPO training using all tickers and dates from `.env`

---

## 1. PREREQUISITES CHECK

### 1.1 Data Requirements

The RLVR dataset generator requires:
- ✅ **Market Data**: OHLCV data with technical indicators (ATR, ADX, RSI, MACD, etc.)
- ✅ **Thesis Generations**: AI-generated investment theses with prompts and responses
- ✅ **Positions**: 3-day position tracking with calculated returns
- ✅ **Historical Returns**: For Sharpe ratio calculation
- ✅ **Fundamentals**: Quarterly financial statements
- ✅ **News**: News articles with sentiment
- ✅ **Analyst Recommendations**: Historical analyst grades
- ✅ **Macro Indicators**: FRED economic data

### 1.2 Configuration from `.env`

```bash
# Data Collection Range (already backfilled)
START_DATE=2024-10-24
END_DATE=2025-11-14

# Training Dataset Split
TRAIN_START_DATE=2023-10-24  # Note: May need adjustment based on actual data
TRAIN_END_DATE=2024-12-31
TEST_START_DATE=2025-01-01
TEST_END_DATE=2025-12-31

# Tickers (87 unique tickers)
TICKERS=AAPL,TSLA,AMZN,MSFT,NVDA,GOOGL,META,NFLX,JPM,V,BAC,AMD,PYPL,DIS,T,PFE,COST,INTC,KO,TGT,NKE,SPY,BA,BABA,XOM,WMT,GE,CSCO,VZ,JNJ,CVX,PLTR,SQ,SHOP,SBUX,SOFI,HOOD,RBLX,SNAP,AMD,UBER,FDX,ABBV,ETSY,MRNA,LMT,GM,F,RIVN,LCID,CCL,DAL,UAL,AAL,TSM,SONY,ET,NOK,MRO,COIN,RIVN,SIRI,SOFI,RIOT,CPRX,PYPL,TGT,VWO,SPYG,NOK,ROKU,HOOD,VIAC,ATVI,BIDU,DOCU,ZM,PINS,TLRY,WBA,VIAC,MGM,NFLX,NIO,C,GS,WFC,ADBE,PEP,UNH,CARR,FUBO,HCA,TWTR,BILI,SIRI,VIAC,FUBO,RKT
```

---

## 2. CURRENT STATUS ASSESSMENT

### 2.1 Data Availability Check

**Market Data:**
- ✅ 102 tickers with market data
- ✅ Date range: 2024-10-24 to 2025-11-14
- ✅ 26,392 market data records
- ✅ Technical indicators calculated (ATR, ADX, RSI, MACD, etc.)

**Thesis Generations:**
- ⚠️ 8,767 total thesis generations
- ⚠️ 1,444 in training/test date range
- ⚠️ Only 12/87 expected tickers have theses
- ❌ **CRITICAL**: 75 tickers missing thesis generations

**Positions:**
- ✅ 8,752 positions calculated
- ✅ Position returns computed

**Other Data:**
- ✅ 195,246 news records
- ✅ 1,030 analyst recommendations
- ✅ 374 fundamentals records
- ✅ 581 macro indicators

### 2.2 Gap Analysis

**Missing Components:**
1. **Thesis Generations**: Need to generate theses for 75 missing tickers
2. **Date Range Coverage**: May need to verify coverage for TRAIN_START_DATE (2023-10-24)
3. **Position Coverage**: Verify all theses have corresponding positions

---

## 3. TRAINING DATASET GENERATION WORKFLOW

### 3.1 Step 1: Verify Data Completeness

```bash
cd /opt/Fireworks-Charlie
source .venv/bin/activate

# Check thesis coverage
python3 << 'EOF'
from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from sqlalchemy import text
import os

config = Config()
db = DatabaseManager(config.DB_URL)
session = db.get_session()

# Get expected tickers
tickers_str = os.environ.get('TICKERS', '')
tickers = sorted(list(set([t.strip().upper() for t in tickers_str.split(',') if t.strip()])))

# Check thesis coverage
thesis_tickers = session.execute(text("""
    SELECT DISTINCT t.symbol
    FROM thesis_generations tg
    JOIN tickers t ON tg.ticker_id = t.ticker_id
    WHERE tg.assistant_response IS NOT NULL
    AND tg.as_of_date >= :train_start
    AND tg.as_of_date <= :test_end
"""), {
    "train_start": os.environ.get('TRAIN_START_DATE', '2023-10-24'),
    "test_end": os.environ.get('TEST_END_DATE', '2025-12-31')
}).fetchall()

thesis_set = {row[0] for row in thesis_tickers}
missing = sorted(set(tickers) - thesis_set)

print(f"Tickers with theses: {len(thesis_set)}/{len(tickers)}")
print(f"Missing: {len(missing)}")
if missing:
    print(f"Missing tickers: {', '.join(missing[:20])}...")

session.close()
EOF
```

### 3.2 Step 2: Generate Missing Thesis Generations (if needed)

**Option A: Use Existing Pipeline**
```bash
# Run main pipeline to generate theses for missing tickers
python main.py \
    --tickers MISSING_TICKERS \
    --start-date TRAIN_START_DATE \
    --end-date TEST_END_DATE
```

**Option B: Use Structured Response Collection**
```bash
# Use collect_structured_responses script
python scripts/collect_structured_responses.py \
    --tickers MISSING_TICKERS \
    --start-date TRAIN_START_DATE \
    --end-date TEST_END_DATE
```

**Note**: If thesis generation is not required (using existing theses), skip to Step 3.

### 3.3 Step 3: Verify Position Coverage

```bash
# Check that all theses have positions
python3 << 'EOF'
from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from sqlalchemy import text
import os

config = Config()
db = DatabaseManager(config.DB_URL)
session = db.get_session()

# Find theses without positions
missing_positions = session.execute(text("""
    SELECT COUNT(*)
    FROM thesis_generations tg
    LEFT JOIN positions p ON (
        p.ticker_id = tg.ticker_id
        AND p.entry_date = tg.as_of_date
    )
    WHERE tg.assistant_response IS NOT NULL
    AND tg.as_of_date >= :train_start
    AND tg.as_of_date <= :test_end
    AND p.position_id IS NULL
"""), {
    "train_start": os.environ.get('TRAIN_START_DATE', '2023-10-24'),
    "test_end": os.environ.get('TEST_END_DATE', '2025-12-31')
}).scalar()

print(f"Theses without positions: {missing_positions}")

if missing_positions > 0:
    print("Run: python scripts/backfill_positions.py")

session.close()
EOF
```

### 3.4 Step 4: Generate Training Datasets

```bash
cd /opt/Fireworks-Charlie
source .venv/bin/activate

# Generate datasets using rlvr_main.py
python rlvr_main.py generate \
    --start-date "$TRAIN_START_DATE" \
    --end-date "$TEST_END_DATE" \
    --train-split-date "$TRAIN_END_DATE" \
    --output-dir storage/rlvr_datasets

# Or use all tickers from .env
python rlvr_main.py generate \
    --tickers "$(echo $TICKERS | tr ' ' ',')" \
    --start-date "$TRAIN_START_DATE" \
    --end-date "$TEST_END_DATE" \
    --train-split-date "$TRAIN_END_DATE" \
    --output-dir storage/rlvr_datasets
```

### 3.5 Step 5: Validate Generated Datasets

```bash
# Run QA validation
python rlvr_main.py qa \
    --train-file storage/rlvr_datasets/train.jsonl \
    --dev-file storage/rlvr_datasets/dev.jsonl \
    --min-train-examples 100 \
    --min-dev-examples 10 \
    --recommended-train-examples 1000 \
    --recommended-dev-examples 100
```

---

## 4. DETAILED EXECUTION PLAN

### 4.1 Pre-Generation Checklist

- [ ] Verify database connection
- [ ] Check market data coverage for all tickers in date range
- [ ] Verify thesis generations exist (or plan to generate)
- [ ] Check position coverage
- [ ] Verify database functions exist:
  - `calculate_position_return()`
  - `get_historical_returns()`
- [ ] Check output directory exists: `storage/rlvr_datasets/`

### 4.2 Generation Steps

**Step 1: Load Environment Variables**
```bash
cd /opt/Fireworks-Charlie
source .venv/bin/activate
export $(grep -E '^(TRAIN_START_DATE|TRAIN_END_DATE|TEST_START_DATE|TEST_END_DATE|TICKERS)=' .env | xargs)
```

**Step 2: Verify Prerequisites**
```bash
python3 << 'EOF'
# Run verification script (see Step 3.1 above)
EOF
```

**Step 3: Generate Missing Theses (if needed)**
```bash
# Only if thesis generation is required
# See Step 3.2 above
```

**Step 4: Backfill Positions (if needed)**
```bash
# Only if positions are missing
python scripts/backfill_positions.py
```

**Step 5: Generate Datasets**
```bash
python rlvr_main.py generate \
    --start-date "$TRAIN_START_DATE" \
    --end-date "$TEST_END_DATE" \
    --train-split-date "$TRAIN_END_DATE" \
    --output-dir storage/rlvr_datasets
```

**Step 6: Validate Datasets**
```bash
python rlvr_main.py qa \
    --train-file storage/rlvr_datasets/train.jsonl \
    --dev-file storage/rlvr_datasets/dev.jsonl
```

---

## 5. EXPECTED OUTPUTS

### 5.1 Generated Files

- `storage/rlvr_datasets/train.jsonl` - Training examples (no assistant response)
- `storage/rlvr_datasets/dev.jsonl` - Development examples (with assistant response)

### 5.2 Dataset Statistics

Expected based on current data:
- **Training Examples**: ~1,155 (80% of 1,444 theses)
- **Dev Examples**: ~289 (20% of 1,444 theses)
- **Total Examples**: ~1,444

**Note**: Actual numbers depend on:
- Number of valid thesis generations
- Position return calculations
- Data validation results

---

## 6. TROUBLESHOOTING

### Common Issues

1. **No Thesis Generations Found**
   - **Solution**: Run thesis generation pipeline first
   - **Command**: `python main.py --tickers TICKER_LIST --start-date START --end-date END`

2. **Insufficient Data for Position Calculation**
   - **Cause**: Missing market data for future dates
   - **Solution**: Ensure market data extends beyond `TEST_END_DATE` by at least 3 trading days

3. **Validation Errors**
   - **Check**: Run `python rlvr_main.py qa` to see detailed errors
   - **Common fixes**: Ensure assistant_response has required fields (reasoning, action, support)

4. **Database Function Errors**
   - **Verify**: Check that `calculate_position_return()` and `get_historical_returns()` exist
   - **Location**: `database/04_functions.sql`

---

## 7. EXECUTION COMMANDS

### Quick Start (Using Existing Data)

```bash
cd /opt/Fireworks-Charlie
source .venv/bin/activate

# Load env vars
export $(grep -E '^(TRAIN_START_DATE|TRAIN_END_DATE|TEST_START_DATE|TEST_END_DATE)=' .env | xargs)

# Generate datasets
python rlvr_main.py generate \
    --start-date "$TRAIN_START_DATE" \
    --end-date "$TEST_END_DATE" \
    --train-split-date "$TRAIN_END_DATE" \
    --output-dir storage/rlvr_datasets

# Validate
python rlvr_main.py qa \
    --train-file storage/rlvr_datasets/train.jsonl \
    --dev-file storage/rlvr_datasets/dev.jsonl
```

### Full Pipeline (With Thesis Generation)

```bash
# 1. Generate missing theses (if needed)
python main.py --tickers ALL_TICKERS --start-date TRAIN_START --end-date TEST_END

# 2. Backfill positions
python scripts/backfill_positions.py

# 3. Generate datasets
python rlvr_main.py generate --start-date TRAIN_START --end-date TEST_END --train-split-date TRAIN_END

# 4. Validate
python rlvr_main.py qa
```

---

## 8. MONITORING & VERIFICATION

### Check Generation Progress

```bash
# Watch log file
tail -f logs/rlvr_dataset_generation.log

# Check database
python rlvr_main.py stats
```

### Verify Dataset Quality

```bash
# Count examples
wc -l storage/rlvr_datasets/train.jsonl
wc -l storage/rlvr_datasets/dev.jsonl

# Sample examples
head -1 storage/rlvr_datasets/train.jsonl | jq .
head -1 storage/rlvr_datasets/dev.jsonl | jq .
```

---

## 9. NEXT STEPS AFTER GENERATION

1. **Review Dataset Statistics**
   - Check example counts
   - Verify train/dev split
   - Review validation results

2. **Prepare for Training**
   - Upload datasets to Fireworks AI
   - Deploy reward function: `python rlvr_main.py deploy`
   - Submit training job: `python rlvr_main.py train`

3. **Monitor Training**
   - Check job status: `python rlvr_main.py status`
   - Review training metrics

---

**END OF PLAN**
