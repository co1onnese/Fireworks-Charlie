# Backfill Execution Plan V2
## Complete Database Setup and Data Backfill for Training Dataset Generation

**Date**: 2025-11-16  
**Goal**: Set up database and backfill all required data to generate training datasets for RLVR pipeline

---

## 1. PREREQUISITES CHECK

### 1.1 Environment Configuration
- [x] `.env` file exists with database credentials:
  - `DB_HOST=localhost`
  - `DB_PORT=5432`
  - `DB_NAME=fireworks_charlie`
  - `DB_USER=fireworks_app`
  - `DB_PASSWORD=changeme_secure_password`
- [x] API keys configured:
  - `EODHD_API_KEY` - Market data, fundamentals, news
  - `FMP_API_KEY` - Analyst recommendations (historical grades)
  - `FRED_API_KEY` - Macroeconomic indicators

### 1.2 Database Connection Test
All psql commands will use credentials from `.env`:
```bash
export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$DB_PASSWORD"
# Then use: psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
```

---

## 2. DATABASE SETUP

### 2.1 Verify Database Connection

```bash
cd /opt/Fireworks-Charlie

# Load environment variables
export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$DB_PASSWORD"

# Test connection
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT version();"

# Check if database exists
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "\l" | grep "$DB_NAME"
```

### 2.2 Create Database and User (if needed)

```bash
# Create database and user as postgres superuser
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

### 2.3 Run Database Schema Migrations

```bash
# Run migrations in order
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/01_tables.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/02_indexes.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/03_views.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/04_functions.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/05_add_atr_adx.sql
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f database/06_add_analyst_recommendations.sql
```

### 2.4 Verify Database Schema

```bash
# Check tables exist
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

# Check analyst_recommendations table
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d analyst_recommendations"

# Check market_data has ATR/ADX columns
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d market_data" | grep -E "atr_14|adx_14"
```

---

## 3. TEST RUN - SINGLE STOCK (AAPL)

### 3.1 Test API Connections

**Test EODHD API:**
```bash
cd /opt/Fireworks-Charlie
python3 << 'EOF'
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from data_collection.eodhd_client import EODHDClient

api_key = os.environ.get('EODHD_API_KEY')
if not api_key:
    print("ERROR: EODHD_API_KEY not found")
    sys.exit(1)

client = EODHDClient(api_key)
print("Testing EODHD API with AAPL...")

# Test market data
market_data = client.get_eod_data("AAPL", "2024-10-24", "2024-10-31")
print(f"✓ Market data: {len(market_data)} records")

# Test fundamentals
fundamentals = client.get_fundamentals("AAPL")
print(f"✓ Fundamentals: {'Found' if fundamentals else 'None'}")

# Test news
news = client.get_news("AAPL", "2024-10-24", "2024-10-31")
print(f"✓ News: {len(news)} articles")

print("\n✓ EODHD API test successful!")
EOF
```

**Test FMP API:**
```bash
python3 << 'EOF'
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from data_collection.fmp_client import FMPClient

api_key = os.environ.get('FMP_API_KEY')
if not api_key:
    print("ERROR: FMP_API_KEY not found")
    sys.exit(1)

client = FMPClient(api_key)
print("Testing FMP API with AAPL...")

grades = client.get_historical_grades("AAPL", limit=5)
print(f"✓ Historical grades: {len(grades)} records")
if grades:
    print(f"  Sample: {grades[0]}")

print("\n✓ FMP API test successful!")
EOF
```

### 3.2 Test Database Write Operations

```bash
# Test database connection and write
python3 << 'EOF'
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from orchestration.config_manager import Config
from data_collection.database_manager import DatabaseManager

config = Config()
db_manager = DatabaseManager(config.DB_URL)

# Test connection
session = db_manager.get_session()
try:
    result = session.execute("SELECT 1").scalar()
    print(f"✓ Database connection: OK (result={result})")
    
    # Test ticker insertion
    ticker = db_manager.insert_or_get_ticker(session, "AAPL", "NASDAQ", "Apple Inc.", "Technology", "Consumer Electronics")
    print(f"✓ Ticker insertion: OK (ticker_id={ticker.ticker_id})")
    session.commit()
except Exception as e:
    print(f"✗ Database error: {e}")
    session.rollback()
finally:
    session.close()
EOF
```

### 3.3 Full Test Backfill - Single Stock (AAPL)

```bash
# Test backfill with AAPL for a small date range
python scripts/backfill_data.py \
    --ticker AAPL \
    --start-date 2024-10-24 \
    --end-date 2024-10-31
```

### 3.4 Verify Test Data

```bash
export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$DB_PASSWORD"

# Check data was inserted
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Count records by type for AAPL
SELECT 
    'Market Data' as data_type,
    COUNT(*) as count
FROM market_data md
JOIN tickers t ON md.ticker_id = t.ticker_id
WHERE t.symbol = 'AAPL'
UNION ALL
SELECT 
    'Fundamentals',
    COUNT(*)
FROM fundamentals f
JOIN tickers t ON f.ticker_id = t.ticker_id
WHERE t.symbol = 'AAPL'
UNION ALL
SELECT 
    'News',
    COUNT(*)
FROM news n
JOIN tickers t ON n.ticker_id = t.ticker_id
WHERE t.symbol = 'AAPL'
UNION ALL
SELECT 
    'Analyst Recommendations',
    COUNT(*)
FROM analyst_recommendations ar
JOIN tickers t ON ar.ticker_id = t.ticker_id
WHERE t.symbol = 'AAPL';
EOF

unset PGPASSWORD
```

---

## 4. FULL BACKFILL EXECUTION

### 4.1 Determine Backfill Parameters

From `.env`:
- **Start Date**: `2024-10-24`
- **End Date**: `2025-11-14`
- **Tickers**: Start with small set, then expand

### 4.2 Backfill Execution Order

**Step 1: Backfill Macro Data (One-time)**
```bash
python scripts/backfill_data.py \
    --tickers AAPL \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --skip-market \
    --skip-fundamentals \
    --skip-news \
    --skip-analyst
```

**Step 2: Backfill Ticker Data**
```bash
# Start with small set
python scripts/backfill_data.py \
    --tickers AAPL,MSFT,NVDA \
    --start-date 2024-10-24 \
    --end-date 2025-11-14

# Then expand to more tickers
python scripts/backfill_data.py \
    --tickers GOOGL,META,AMZN \
    --start-date 2024-10-24 \
    --end-date 2025-11-14
```

---

## 5. VERIFICATION & MONITORING

### 5.1 Data Quality Checks

```bash
export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$DB_PASSWORD"

# Comprehensive data check
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

unset PGPASSWORD
```

### 5.2 Monitor Backfill Progress

```bash
# Watch logs
tail -f logs/data_backfill.log

# Check recent inserts
export $(grep -v '^#' .env | xargs)
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT COUNT(*) FROM market_data WHERE created_at > NOW() - INTERVAL '1 hour';"
unset PGPASSWORD
```

---

## 6. TROUBLESHOOTING

### Common Issues

1. **Database Connection Fails**
   - Verify credentials in `.env`
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Test connection manually

2. **API Rate Limits**
   - Backfill script handles rate limiting
   - If issues persist, add delays or reduce batch size

3. **Missing Data**
   - Some tickers may not have all data types
   - Check API responses in logs
   - Continue with available data

---

## 7. EXECUTION CHECKLIST

### Pre-Execution
- [ ] Load environment variables from `.env`
- [ ] Test database connection
- [ ] Test EODHD API
- [ ] Test FMP API
- [ ] Verify database schema is up to date

### Test Run
- [ ] Run test backfill with AAPL (small date range)
- [ ] Verify all data types collected
- [ ] Verify data in database
- [ ] Check for errors in logs

### Full Backfill
- [ ] Backfill macro data
- [ ] Backfill ticker data (start small, expand)
- [ ] Monitor progress
- [ ] Verify data quality

---

**END OF PLAN**
