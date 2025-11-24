# Thesis Regeneration Plan

## Overview
Clear existing LLM responses from the database and regenerate all theses using the new prompts, then regenerate RLVR datasets.

## Current State
- **Total Theses**: 21,451
- **Date Range**: 2023-10-24 to 2025-11-14
- **Tickers**: 105 unique tickers
- **Current Status**: All theses have assistant_response populated

## Configuration
This plan uses values from your `.env` file via `orchestration.config_manager`:
- **Tickers**: `TICKERS` environment variable (comma-separated)
- **Date Range**: `START_DATE` and `END_DATE` for thesis generation
- **Train/Dev Split**: `TRAIN_END_DATE` for dataset split date
- **Output Directory**: `RLVR_OUTPUT_DIR` for dataset files

Make sure your `.env` file is configured before running the regeneration.

## Strategy

### Phase 1: Clear LLM Responses
Clear the assistant_response and related fields from `thesis_generations` table while preserving:
- `system_prompt` and `user_prompt` (these will be regenerated with new prompts)
- `ticker_id` and `as_of_date` (to maintain the structure)
- `thesis_id` (primary key)

**Fields to Clear:**
- `assistant_response` (JSONB) → Set to NULL
- `predicted_action` → Set to NULL
- `reasoning` → Set to NULL
- `support` → Set to NULL
- `model_name` → Set to NULL
- `temperature` → Set to NULL
- `tokens_used` → Set to NULL
- `generation_time_ms` → Set to NULL
- `status` → Set to 'pending'
- `error_message` → Set to NULL
- `generated_at` → Keep or update to current timestamp

**Related Tables to Handle:**
- `positions` table has foreign key to `thesis_generations.thesis_id` with CASCADE delete
- Options:
  1. Delete all positions (they'll be regenerated with new theses)
  2. Clear position fields that depend on assistant_response
  3. Let CASCADE handle it if we delete theses (but we're not deleting, just clearing fields)

**Recommended Approach:**
- Clear assistant_response fields but keep thesis records
- Delete related positions (they'll be regenerated)
- Modify pipeline check to regenerate if `assistant_response IS NULL` or `status = 'pending'`

### Phase 2: Regenerate Prompts
The existing `scripts/regenerate_prompts.py` can regenerate prompts, but we want to:
1. Use the new prompt builder (already in place)
2. Regenerate system_prompt and user_prompt for all theses
3. Keep the thesis records (don't delete them)

### Phase 3: Regenerate LLM Responses
Run the main pipeline to generate new assistant_response for all theses:
- Pipeline will check for existing theses
- Need to modify check to also check if `assistant_response IS NULL`
- Or clear the thesis records entirely and regenerate from scratch

### Phase 4: Regenerate RLVR Datasets
Once new theses are generated, run:
```bash
python rlvr_main.py generate --train-split-date 2024-12-31 --output-dir storage/rlvr_datasets
```

## Implementation Options

### Option A: Clear Fields + Modify Pipeline (Recommended)
1. **Clear assistant_response fields** from all theses
2. **Delete positions** (they depend on assistant_response)
3. **Modify pipeline** to check `assistant_response IS NULL` in addition to existence check
4. **Regenerate prompts** using existing script
5. **Run pipeline** to generate new responses
6. **Regenerate datasets**

**Pros:**
- Preserves thesis_id and structure
- Can track which theses need regeneration
- Maintains referential integrity

**Cons:**
- Requires pipeline modification
- Need to handle positions separately

### Option B: Delete and Regenerate (Simpler)
1. **Delete all thesis_generations** (positions will CASCADE delete)
2. **Regenerate prompts** for all ticker/date combinations
3. **Run pipeline** to generate new theses from scratch
4. **Regenerate datasets**

**Pros:**
- Clean slate
- No pipeline modification needed
- Simpler logic

**Cons:**
- Loses thesis_id continuity
- Need to regenerate prompts first

### Option C: Update Pipeline to Force Regeneration
1. **Clear assistant_response** fields
2. **Modify pipeline** to always regenerate if `assistant_response IS NULL`
3. **Run pipeline** (it will regenerate prompts and responses)
4. **Regenerate datasets**

**Pros:**
- Single pipeline run
- Handles everything

**Cons:**
- Requires pipeline modification
- May be slower (regenerates prompts even if unchanged)

## Recommended Approach: Option A

### Step 1: Create Clear Script ✅ COMPLETED
Created `scripts/clear_thesis_responses.py` to:
- Clear assistant_response and related fields
- Set status to 'pending'
- Delete related positions
- Provide statistics

**Usage:**
```bash
# Dry run first
python scripts/clear_thesis_responses.py --dry-run

# Clear all theses
python scripts/clear_thesis_responses.py

# Clear specific tickers or date range
python scripts/clear_thesis_responses.py --tickers AAPL,MSFT --start-date 2024-01-01
```

### Step 2: Modify Pipeline Check ✅ COMPLETED
Modified `orchestration/main_pipeline.py` (lines 486-527) to:
- Check if thesis exists AND has assistant_response → skip
- Check if thesis exists BUT assistant_response is NULL → update it
- If thesis doesn't exist → create new

This allows regeneration when assistant_response is NULL while preserving thesis_id.

### Step 3: Regenerate Prompts (Optional)
If prompts have changed, run:
```bash
python scripts/regenerate_prompts.py --all
```

### Step 4: Run Pipeline
Run the main pipeline to generate new LLM responses:
```bash
python main.py --tickers <all_tickers> --start-date 2023-10-24 --end-date 2025-11-14
```

### Step 5: Regenerate Datasets
```bash
python rlvr_main.py generate --train-split-date 2024-12-31 --output-dir storage/rlvr_datasets
```

## Database Queries

### Clear Assistant Responses
```sql
UPDATE thesis_generations
SET 
    assistant_response = NULL,
    predicted_action = NULL,
    reasoning = NULL,
    support = NULL,
    model_name = NULL,
    temperature = NULL,
    tokens_used = NULL,
    generation_time_ms = NULL,
    status = 'pending',
    error_message = NULL,
    generated_at = CURRENT_TIMESTAMP
WHERE assistant_response IS NOT NULL;
```

### Delete Related Positions
```sql
DELETE FROM positions
WHERE thesis_id IN (
    SELECT thesis_id FROM thesis_generations WHERE assistant_response IS NULL
);
```

Or delete all positions (simpler):
```sql
TRUNCATE TABLE positions;
```

## Execution Plan

### Phase 1: Preparation ✅ COMPLETED
1. ✅ **Created clear script** (`scripts/clear_thesis_responses.py`)
2. ✅ **Modified pipeline** to regenerate when `assistant_response IS NULL`

### Phase 2: Clear Existing Responses
1. **Backup Database** (recommended)
   ```bash
   pg_dump -U fireworks_app fireworks_charlie > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Dry run to see what will be cleared**
   ```bash
   # Clear all theses (uses all tickers in database)
   python scripts/clear_thesis_responses.py --dry-run
   
   # Or filter by config tickers
   python scripts/clear_thesis_responses.py --dry-run --tickers $(python -c "from orchestration.config_manager import config; print(','.join(config.TICKERS))")
   ```

3. **Clear assistant_response fields and delete positions**
   ```bash
   # Clear all theses
   python scripts/clear_thesis_responses.py
   
   # Or filter by config tickers and date range
   python scripts/clear_thesis_responses.py \
     --tickers $(python -c "from orchestration.config_manager import config; print(','.join(config.TICKERS))") \
     --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") \
     --end-date $(python -c "from orchestration.config_manager import config; print(config.END_DATE)")
   ```
   This will:
   - Clear `assistant_response`, `predicted_action`, `reasoning`, `support`, and model metadata
   - Set `status = 'pending'`
   - Delete all positions (they'll be regenerated)

### Phase 3: Regenerate Prompts (Optional)
If prompts have changed and need to be regenerated:
```bash
python scripts/regenerate_prompts.py --all
```

### Phase 4: Verify Configuration
Before proceeding, verify your `.env` file has the correct values:
```bash
# Check current configuration
python -c "
from orchestration.config_manager import config
print(f'Tickers: {config.TICKERS}')
print(f'Start Date: {config.START_DATE}')
print(f'End Date: {config.END_DATE}')
print(f'Train End Date (split date): {config.TRAIN_END_DATE}')
print(f'Output Directory: {config.RLVR_OUTPUT_DIR}')
"
```

**Required .env variables:**
- `TICKERS` - Comma-separated list (e.g., `AAPL,NVDA,MSFT,AMZN,META`)
- `START_DATE` - Start date for thesis generation (e.g., `2023-10-24`)
- `END_DATE` - End date for thesis generation (e.g., `2025-11-14`)
- `TRAIN_END_DATE` - Train/dev split date for datasets (e.g., `2024-12-31`)
- `RLVR_OUTPUT_DIR` - Output directory for datasets (default: `/opt/Fireworks-Charlie/storage/rlvr_datasets`)

### Phase 5: Test on Small Subset (Optional)
Test the regeneration process on a small subset first:
```bash
# Clear responses for one ticker (using first ticker from config)
python -c "
from orchestration.config_manager import config
ticker = config.TICKERS[0] if config.TICKERS else 'AAPL'
print(f'Testing with ticker: {ticker}')
" && python scripts/clear_thesis_responses.py --tickers $(python -c "from orchestration.config_manager import config; print(config.TICKERS[0] if config.TICKERS else 'AAPL')") --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") --end-date $(python -c "from orchestration.config_manager import config; from datetime import datetime, timedelta; start = datetime.strptime(config.START_DATE, '%Y-%m-%d'); end = start + timedelta(days=10); print(end.strftime('%Y-%m-%d'))")

# Regenerate for that ticker (uses config defaults if not specified)
python main.py --tickers $(python -c "from orchestration.config_manager import config; print(config.TICKERS[0] if config.TICKERS else 'AAPL')") --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") --end-date $(python -c "from orchestration.config_manager import config; from datetime import datetime, timedelta; start = datetime.strptime(config.START_DATE, '%Y-%m-%d'); end = start + timedelta(days=10); print(end.strftime('%Y-%m-%d'))")

# Verify results
python -c "from data_collection.database_manager import DatabaseManager; from orchestration.config_manager import config; from sqlalchemy import text; db = DatabaseManager(config.DB_URL); s = db.get_session(); result = s.execute(text(\"SELECT COUNT(*) FROM thesis_generations WHERE assistant_response IS NOT NULL\")).scalar(); print(f'Theses with responses: {result}'); s.close()"
```

**Simpler test approach:**
```bash
# Test with first ticker only, first 10 days
python scripts/clear_thesis_responses.py --tickers $(python -c "from orchestration.config_manager import config; print(config.TICKERS[0])") --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") --end-date 2024-01-10

# Regenerate (main.py uses config defaults)
python main.py --tickers $(python -c "from orchestration.config_manager import config; print(config.TICKERS[0])") --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") --end-date 2024-01-10
```

### Phase 6: Full Regeneration
Once testing is successful, run full pipeline using config values:
```bash
# Uses TICKERS, START_DATE, END_DATE from .env
python main.py
```

Or explicitly specify (will override .env):
```bash
python main.py --start-date $(python -c "from orchestration.config_manager import config; print(config.START_DATE)") --end-date $(python -c "from orchestration.config_manager import config; print(config.END_DATE)")
```

This will:
- Use tickers from `config.TICKERS` (from .env)
- Use date range from `config.START_DATE` to `config.END_DATE` (from .env)
- Regenerate prompts using the new prompt builder
- Generate new LLM responses for all theses
- Create new positions

### Phase 7: Regenerate RLVR Datasets
Once all theses are regenerated, use the train split date from config:
```bash
# Uses TRAIN_END_DATE from .env as split date
python rlvr_main.py generate --train-split-date $(python -c "from orchestration.config_manager import config; print(config.TRAIN_END_DATE)") --output-dir $(python -c "from orchestration.config_manager import config; print(config.RLVR_OUTPUT_DIR)")
```

Or create a simple wrapper script:
```bash
# Create helper script
cat > regenerate_datasets.sh << 'EOF'
#!/bin/bash
python -c "
from orchestration.config_manager import config
import subprocess
import sys

split_date = config.TRAIN_END_DATE
output_dir = config.RLVR_OUTPUT_DIR

print(f'Using train split date: {split_date}')
print(f'Using output directory: {output_dir}')

cmd = ['python', 'rlvr_main.py', 'generate', 
       '--train-split-date', split_date,
       '--output-dir', output_dir]

sys.exit(subprocess.call(cmd))
"
EOF
chmod +x regenerate_datasets.sh
./regenerate_datasets.sh
```

### Phase 8: Validate
```bash
# Validate datasets
python rlvr_main.py qa \
    --train-file $(python -c "from orchestration.config_manager import config; print(config.RLVR_TRAIN_FILE)") \
    --dev-file $(python -c "from orchestration.config_manager import config; print(config.RLVR_DEV_FILE)")

# Check statistics
python rlvr_main.py stats
```

## Quick Start: All-in-One Script

For convenience, use the provided script that handles everything:
```bash
# Run complete regeneration using .env configuration
./scripts/regenerate_all.sh
```

This script will:
1. Load configuration from `.env` file
2. Clear existing LLM responses (with confirmation)
3. Regenerate all theses using the pipeline
4. Regenerate RLVR datasets
5. Validate the output

**Make sure your `.env` file is configured before running!**

## Estimated Time
- Clearing responses: < 1 minute
- Pipeline regeneration: ~hours (depends on API rate limits)
- Dataset generation: ~5-10 minutes

## Risk Mitigation
- Backup database before clearing
- Test on small subset first
- Monitor API rate limits
- Checkpoint/resume capability in pipeline
- Validate outputs at each step
