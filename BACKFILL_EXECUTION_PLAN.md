# Backfill Execution Plan
## Complete Database Setup and Data Backfill for Training Dataset Generation

**Date**: 2025-11-16  
**Goal**: Set up database and backfill all required data to generate training datasets for RLVR pipeline

---

## 1. PREREQUISITES CHECK

### 1.1 Environment Configuration
- [ ] Verify `.env` file exists and contains all required API keys:
  - `EODHD_API_KEY` - Market data, fundamentals, news
  - `FMP_API_KEY` - Analyst recommendations (historical grades)
  - `FRED_API_KEY` - Macroeconomic indicators
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database credentials

### 1.2 Database Credentials from .env
```bash
# Extract from .env file
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fireworks_charlie
DB_USER=fireworks_app
DB_PASSWORD=changeme_secure_password
```

### 1.3 PostgreSQL Installation
- [ ] PostgreSQL 14+ installed and running
- [ ] PostgreSQL service is accessible
- [ ] User has permissions to create databases/users (or use existing)

---

## 2. DATABASE SETUP

### 2.1 Initial Database Setup

**Step 1: Load environment variables and verify database connection**

```bash
cd /opt/Fireworks-Charlie

# Load .env variables
source .env  # or use: export $(grep -v '^#' .env | xargs)

# Verify database credentials
echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT"
echo "DB_NAME: $DB_NAME"
echo "DB_USER: $DB_USER"
echo "DB_PASSWORD: [hidden]"
```

**Step 2: Test database connection**

```bash
# Test connection using credentials from .env
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT version();"
unset PGPASSWORD
```

**Step 3: Create database and user (if needed)**

```bash
# Create database and user as postgres superuser
export PGPASSWORD="$DB_PASSWORD"  # For subsequent commands

# If database doesn't exist, create it
sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'Created user: $DB_USER';
    ELSE
        RAISE NOTICE 'User already exists: $DB_USER';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
```

**Step 4: Run database schema migrations**

```bash
# Set PGPASSWORD for non-interactive authentication
export PGPASSWORD="$DB_PASSWORD"

# Run migrations in order
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/01_tables.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/02_indexes.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/03_views.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/04_functions.sql

# Run additional migrations
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/05_add_atr_adx.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/06_add_analyst_recommendations.sql

# Unset PGPASSWORD for security
unset PGPASSWORD
```

**Step 5: Verify database setup**

```bash
export PGPASSWORD="$DB_PASSWORD"

# Check tables exist
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

# Check analyst_recommendations table exists
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d analyst_recommendations"

# Check market_data has ATR/ADX columns
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d market_data" | grep -E "atr_14|adx_14"

unset PGPASSWORD
```

---

## 3. DATA BACKFILL EXECUTION

### 3.1 Determine Backfill Parameters

From `.env` file:
- **Start Date**: `2024-10-24`
- **End Date**: `2025-11-14`
- **Tickers**: Check `.env` for `TICKERS` variable (currently commented out)

**Recommended tickers for initial backfill** (from .env):
- Start with a small set: `AAPL,MSFT,NVDA,GOOGL,META`
- Or use the full list if commented in .env

### 3.2 Backfill Execution Order

**Phase 1: Macro Data (One-time, not per ticker)**
```bash
cd /opt/Fireworks-Charlie

# Backfill macro data first (only needs to be done once)
python scripts/backfill_data.py \
    --tickers AAPL \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --skip-market \
    --skip-fundamentals \
    --skip-news \
    --skip-analyst
```

**Phase 2: Per-Ticker Data Collection**

For each ticker (or batch of tickers):

```bash
# Example: Single ticker
python scripts/backfill_data.py \
    --ticker AAPL \
    --start-date 2024-10-24 \
    --end-date 2025-11-14

# Example: Multiple tickers
python scripts/backfill_data.py \
    --tickers AAPL,MSFT,NVDA,GOOGL,META \
    --start-date 2024-10-24 \
    --end-date 2025-11-14
```

### 3.3 Backfill Process Details

The backfill script collects:
1. **Market Data (OHLCV)** - Daily price and volume data
2. **Technical Indicators** - ATR, ADX, RSI, MACD, SMA, EMA, Bollinger Bands
3. **Fundamentals** - Quarterly financial statements
4. **News** - News articles with sentiment analysis
5. **Analyst Recommendations** - FMP historical grades (consensus ratings)
6. **Macro Indicators** - FRED economic data (collected once)

### 3.4 Monitoring Backfill Progress

```bash
# Check backfill logs
tail -f logs/data_backfill.log

# Check database records
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Count records by type
SELECT 'Market Data', COUNT(*) FROM market_data;
SELECT 'Fundamentals', COUNT(*) FROM fundamentals;
SELECT 'News', COUNT(*) FROM news;
SELECT 'Analyst Recommendations', COUNT(*) FROM analyst_recommendations;
SELECT 'Macro Indicators', COUNT(*) FROM macroeconomic_indicators;
EOF
unset PGPASSWORD
```

---

## 4. VERIFICATION & VALIDATION

### 4.1 Data Quality Checks

```bash
export PGPASSWORD="$DB_PASSWORD"

# Check data coverage by ticker
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT 
    t.symbol,
    COUNT(DISTINCT md.date) as market_data_days,
    COUNT(DISTINCT f.report_date) as fundamental_quarters,
    COUNT(DISTINCT n.news_id) as news_articles,
    COUNT(DISTINCT ar.recommendation_id) as analyst_recs_count
FROM tickers t
LEFT JOIN market_data md ON t.ticker_id = md.ticker_id
LEFT JOIN fundamentals f ON t.ticker_id = f.ticker_id
LEFT JOIN news n ON t.ticker_id = n.ticker_id
LEFT JOIN analyst_recommendations ar ON t.ticker_id = ar.ticker_id
GROUP BY t.symbol
ORDER BY t.symbol;
EOF

# Check date ranges
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT 
    'Market Data' as data_type,
    MIN(date) as min_date,
    MAX(date) as max_date,
    COUNT(*) as records
FROM market_data
UNION ALL
SELECT 
    'Analyst Recommendations',
    MIN(date),
    MAX(date),
    COUNT(*)
FROM analyst_recommendations;
EOF

unset PGPASSWORD
```

### 4.2 Technical Indicators Verification

```bash
export PGPASSWORD="$DB_PASSWORD"

# Check ATR/ADX columns exist and have data
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT 
    COUNT(*) as total_records,
    COUNT(atr_14) as records_with_atr,
    COUNT(adx_14) as records_with_adx,
    COUNT(di_plus_14) as records_with_di_plus,
    COUNT(di_minus_14) as records_with_di_minus
FROM market_data;
EOF

unset PGPASSWORD
```

---

## 5. TROUBLESHOOTING

### 5.1 Common Issues

**Issue: Database connection fails**
```bash
# Verify credentials
echo "DB_HOST: $DB_HOST"
echo "DB_USER: $DB_USER"
echo "DB_NAME: $DB_NAME"

# Test connection
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;"
unset PGPASSWORD
```

**Issue: Missing tables**
- Re-run schema migrations (Step 2.1, Step 4)
- Check migration logs for errors

**Issue: API rate limits**
- Backfill script handles rate limiting automatically
- If issues persist, backfill in smaller batches or add delays

**Issue: Missing data for specific tickers**
- Some tickers may not have all data types available
- Check API responses in logs
- Continue with available data

### 5.2 Partial Backfill Recovery

If backfill fails partway through:
- The script commits after each ticker
- Re-run with same parameters to continue (won't duplicate due to unique constraints)
- Use `--skip-*` flags to skip already-collected data types

---

## 6. POST-BACKFILL STEPS

### 6.1 Feature Engineering

After backfill, run feature engineering to calculate:
- Rolling sentiment features
- Time-since-event features
- Macro feature aggregations

```bash
# Feature engineering is typically run automatically during data collection
# But can be run separately if needed
python -c "
from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager
from data_collection.feature_engineering import FeatureEngineer
from datetime import date

config = Config()
db_manager = DatabaseManager(config.DB_URL)
feature_engineer = FeatureEngineer(db_manager)

# Run feature engineering for date range
feature_engineer.process_all_features(
    tickers=['AAPL', 'MSFT'],  # Your tickers
    start_date=date(2024, 10, 24),
    end_date=date(2025, 11, 14)
)
"
```

### 6.2 Generate Training Dataset

Once backfill is complete:

```bash
# Generate RLVR training dataset
python rlvr_main.py generate \
    --tickers AAPL,MSFT,NVDA \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --train-split-date 2025-08-01 \
    --output-dir storage/rlvr_datasets
```

---

## 7. EXECUTION CHECKLIST

### Pre-Execution
- [ ] Verify `.env` file has all API keys configured
- [ ] Verify database credentials in `.env`
- [ ] PostgreSQL is running and accessible
- [ ] Database user has required permissions

### Database Setup
- [ ] Load environment variables from `.env`
- [ ] Test database connection using `.env` credentials
- [ ] Create database and user (if needed)
- [ ] Run all schema migrations (01-06)
- [ ] Verify all tables exist
- [ ] Verify ATR/ADX columns exist in market_data
- [ ] Verify analyst_recommendations table exists

### Data Backfill
- [ ] Backfill macro data (one-time)
- [ ] Backfill market data for all tickers
- [ ] Backfill fundamentals for all tickers
- [ ] Backfill news for all tickers
- [ ] Backfill analyst recommendations for all tickers
- [ ] Verify data quality and coverage

### Post-Backfill
- [ ] Run feature engineering
- [ ] Verify technical indicators calculated
- [ ] Generate training dataset
- [ ] Validate dataset format

---

## 8. QUICK START COMMANDS

### Complete Setup and Backfill (Single Command Sequence)

```bash
cd /opt/Fireworks-Charlie

# 1. Load environment variables
source .env  # or: export $(grep -v '^#' .env | xargs)

# 2. Setup database (if not already done)
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -f database/01_tables.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/02_indexes.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/03_views.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/04_functions.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/05_add_atr_adx.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/06_add_analyst_recommendations.sql
unset PGPASSWORD

# 3. Backfill macro data
python scripts/backfill_data.py \
    --tickers AAPL \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --skip-market --skip-fundamentals --skip-news --skip-analyst

# 4. Backfill ticker data
python scripts/backfill_data.py \
    --tickers AAPL,MSFT,NVDA \
    --start-date 2024-10-24 \
    --end-date 2025-11-14

# 5. Verify data
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM market_data;"
unset PGPASSWORD
```

---

## 9. ESTIMATED TIME

| Phase | Task | Estimated Time |
|-------|------|----------------|
| Database Setup | Schema creation, migrations | 5-10 minutes |
| Macro Data | FRED indicators (one-time) | 2-5 minutes |
| Per Ticker | Market + Fundamentals + News + Analyst | 5-10 minutes per ticker |
| **Total (10 tickers)** | Complete backfill | **1-2 hours** |

---

## 10. NOTES

- All psql commands use credentials from `.env` file via `$DB_HOST`, `$DB_USER`, `$DB_PASSWORD`
- Database setup only needs to be done once
- Macro data only needs to be collected once (not per ticker)
- Backfill can be run incrementally - re-running won't duplicate data
- Use `--skip-*` flags to skip already-collected data types
- Monitor logs in `logs/data_backfill.log` for progress and errors

---

**END OF PLAN**
