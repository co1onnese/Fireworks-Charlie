# Trainer-Charlie Database Backup

## Backup Details

**Created:** 2025-10-25 09:17:57
**Database:** trainer_charlie
**Database System:** PostgreSQL 16.10
**Backup Method:** pg_dump with --clean --create --if-exists flags

## Backup File

- **Filename:** trainer_charlie_backup_20251025_091757.sql
- **Location:** /opt/Trainer-Charlie/backups/
- **Size:** 372 KB
- **Format:** Plain SQL text file

## Database Contents

### Tables and Row Counts

| Table Name | Row Count | Description |
|-----------|-----------|-------------|
| News | 95 | News articles with sentiment analysis |
| Macroeconomic_Indicators | 16 | Economic data from FRED |
| Macro_Features | 8 | Derived macroeconomic indicators |
| Technical_Market_Data | 5 | Price and technical indicators |
| News_Features | 4 | Aggregated news sentiment features |
| Tickers | 1 | Stock ticker metadata (AAPL) |
| Insider_Transactions | 0 | Insider trading records |
| Fundamentals | 0 | Financial statements and metrics |

**Total Records:** 129 rows across 8 tables

### Schema Structure

The backup includes the following database objects:

1. **Tickers** - Stock ticker metadata
   - Stores ticker symbols, exchange, company name, sector, industry

2. **Technical_Market_Data** - Price and technical indicators
   - OHLCV data, SMA, EMA, RSI indicators

3. **Fundamentals** - Financial statements and metrics
   - Quarterly reports, income statements, balance sheets, cash flows

4. **News** - News articles with sentiment analysis
   - Article content, sentiment scores, publication dates

5. **News_Features** - Aggregated news sentiment features
   - 7-day sentiment averages and counts

6. **Insider_Transactions** - Insider trading records
   - Transaction dates, amounts, prices, owner names

7. **Macroeconomic_Indicators** - Economic data from FRED
   - GDP, CPI, unemployment, treasury yields, etc.

8. **Macro_Features** - Derived macroeconomic indicators
   - Yield curve spreads, inflation changes, etc.

## Restore Instructions

### Basic Restore

To restore this backup to a PostgreSQL database:

```bash
# Restore to the trainer_charlie database
PGPASSWORD=charlie_password psql -h localhost -U charlie_user < trainer_charlie_backup_20251025_091757.sql
```

### Restore to Different Database

```bash
# Restore to a different database or server
PGPASSWORD=your_password psql -h your_host -U your_user -d postgres < trainer_charlie_backup_20251025_091757.sql
```

### Restore Options

```bash
# Verbose output
PGPASSWORD=charlie_password psql -h localhost -U charlie_user -v ON_ERROR_STOP=1 < trainer_charlie_backup_20251025_091757.sql

# Restore only schema (no data)
grep -v "^COPY\|^\\\\\." trainer_charlie_backup_20251025_091757.sql | psql -h localhost -U charlie_user
```

## Backup Features

- **--clean**: Drops existing objects before recreating them
- **--create**: Includes CREATE DATABASE command
- **--if-exists**: Uses IF EXISTS clause when dropping objects (prevents errors)
- **Complete Schema**: All tables, indexes, constraints, and sequences
- **All Data**: Complete data dump from all tables
- **Permissions**: Database roles and permissions preserved

## Verification

To verify the backup integrity:

```bash
# Check file size
ls -lh trainer_charlie_backup_20251025_091757.sql

# View first 50 lines
head -50 trainer_charlie_backup_20251025_091757.sql

# Count tables
grep "^CREATE TABLE" trainer_charlie_backup_20251025_091757.sql | wc -l

# Count data copy statements
grep "^COPY" trainer_charlie_backup_20251025_091757.sql | wc -l
```

## Notes

- This backup includes the complete database structure and all data
- Database owner and permissions are preserved
- The backup is portable and can be restored on any PostgreSQL 12+ instance
- File is in plain SQL format for easy inspection and modification
- Contains data from the test run (AAPL, 2024-01-01 to 2024-01-08)

## Data Summary

**Test Data Period:** January 1-8, 2024
**Ticker Processed:** AAPL
**Trading Days:** 5 days
**Theses Generated:** 5
**News Articles:** 95
**Macro Indicators:** 16 observations across 8 series
