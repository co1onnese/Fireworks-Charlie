# Dataset Generation Fix Summary

## Problem
When running `python rlvr_main.py generate`, all examples were being placed in `dev.jsonl` (1507 examples) and NONE in `train.jsonl` (0 examples).

## Root Causes

### 1. Invalid Date in `.env`
- **Issue**: `TRAIN_END_DATE=2025-06-31` (June only has 30 days!)
- **Fix**: Changed to `TRAIN_END_DATE=2025-06-30`

### 2. Field Name Mismatch in `dataset_generator.py`
- **Issue**: Code was looking for `generation_date` field which doesn't exist in database query results
- **Database returns**: `as_of_date` and `generated_at`
- **Fix**: Updated to use `as_of_date` as primary field, with `generated_at` as fallback

### 3. Type Mismatch in Date Comparison
- **Issue**: `thesis_date` (datetime.date object) was being compared to `train_split_date` (string)
- **Error**: `'<' not supported between instances of 'datetime.date' and 'str'`
- **Fix**: Added type conversion to ensure both are date objects before comparison

### 4. Off-by-One Error in Date Split
- **Issue**: Examples on split date (2025-06-30) were going to dev instead of training
- **Fix**: Changed comparison from `<` to `<=` to include split date in training data

### 5. Incorrect Example Format Logic
- **Issue**: ALL examples were created as dev examples (with assistant message) because query filtered for `assistant_response IS NOT NULL`
- **Fix**: Changed logic to determine training vs dev based on date split, creating:
  - **Training examples**: 2 messages (system, user) - NO assistant message
  - **Dev examples**: 3 messages (system, user, assistant) - WITH assistant message

## Changes Made

### `/opt/Fireworks-Charlie/.env`
```diff
- TRAIN_END_DATE=2025-06-31
+ TRAIN_END_DATE=2025-06-30
```

### `/opt/Fireworks-Charlie/rlvr/dataset_generator.py`

#### 1. Fixed field name references (2 locations)
```python
# OLD:
thesis_date = thesis.get('generation_date', thesis.get('created_at'))

# NEW:
thesis_date = thesis.get('as_of_date', thesis.get('generated_at'))
```

#### 2. Added type conversion for split date
```python
# Convert train_split_date to date object if it's a string
if isinstance(train_split_date, str):
    train_split_date = datetime.strptime(train_split_date, "%Y-%m-%d").date()
```

#### 3. Fixed date comparison to use <=
```python
# Training includes dates up to and including the split date
is_training = thesis_date and thesis_date <= train_split_date
```

#### 4. Refactored example creation logic
```python
# Determine training vs dev BEFORE processing
is_training = thesis_date and thesis_date <= train_split_date

# Process with appropriate format
example = self._process_thesis_to_example(thesis, is_training=is_training)

# In _process_thesis_to_example:
if is_training:
    # Training example (no assistant response - model generates during training)
    example = create_training_example(...)
else:
    # Development example (with assistant response for evaluation)
    example = create_dev_example(...)
```

## Results

### Before Fix
```
Training examples: 0
Dev examples: 1507
Skipped: 15
```

### After Fix
```
Training examples: 1105
Dev examples: 402
Skipped: 15

Training date range: 2023-10-24 to 2025-06-30
Dev date range: 2025-07-01 to 2025-10-23

? Date split is PERFECT!
```

## Verification

### Training Examples Format (train.jsonl)
- ? 2 messages: system, user (NO assistant message)
- ? Has ground_truth with actual returns
- ? Has metadata with ticker, entry_date, historical_returns
- ? Dates: 2023-10-24 to 2025-06-30

### Dev Examples Format (dev.jsonl)
- ? 3 messages: system, user, assistant
- ? Assistant message contains JSON with reasoning, action, support
- ? Has ground_truth with actual returns
- ? Has metadata with ticker, entry_date, historical_returns
- ? Dates: 2025-07-01 to 2025-10-23

## Usage

Generate datasets with fixed code:
```bash
source .venv/bin/activate

python rlvr_main.py generate \
    --tickers NFLX,XOM,MA,HD,SBUX \
    --train-split-date 2025-06-30 \
    --output-dir storage/rlvr_datasets
```

Or use environment variable defaults:
```bash
python rlvr_main.py generate \
    --train-split-date $(grep TRAIN_END_DATE .env | cut -d= -f2) \
    --output-dir storage/rlvr_datasets
```

## Next Steps

You can now:

1. **Deploy the reward function**:
   ```bash
   python rlvr_main.py deploy
   ```

2. **Submit GRPO training job**:
   ```bash
   python rlvr_main.py train
   ```

3. **Check training status**:
   ```bash
   python rlvr_main.py status
   ```

## Notes

- The 15 skipped examples are expected - they're from the most recent dates (Oct 24-28) that don't have 3 days of future market data for position calculation
- Training examples don't include assistant messages because the model generates them during GRPO training
- Dev examples include assistant messages for evaluation and validation of the reward function
