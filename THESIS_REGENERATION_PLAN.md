# Thesis Regeneration Plan
## Regenerate Theses with Current Prompts and New Data

**Date**: 2025-11-16  
**Issue**: Existing theses (1,444) were generated with OLD prompts/data structure  
**Solution**: Delete old theses and regenerate with current prompts using new backfilled data

---

## 1. CURRENT SITUATION

- **Existing theses**: 1,444 in training/test date range
- **Generation dates**: 2025-11-01 to 2025-11-03 (OLD prompts)
- **Date range needed**: 2024-10-24 to 2025-11-14
- **Tickers**: 21 tickers with existing theses
- **Problem**: These use old prompt structure and may not include all new data

---

## 2. REGENERATION STRATEGY

### Option A: Delete and Regenerate (Recommended)
1. Delete old theses in date range (and associated positions)
2. Run main pipeline to regenerate with current prompts
3. Backfill positions for new theses
4. Regenerate datasets

### Option B: Mark and Regenerate (Safer)
1. Mark old theses as "deprecated" 
2. Generate new theses (will create duplicates)
3. Switch dataset generation to use new theses
4. Clean up old ones later

**We'll use Option A** - clean deletion and regeneration.

---

## 3. EXECUTION PLAN

### Step 1: Backup Current State
```bash
# Export current theses (just in case)
python3 << 'EOF'
# Backup script
EOF
```

### Step 2: Delete Old Theses and Positions
```sql
-- Delete positions first (foreign key constraint)
DELETE FROM positions 
WHERE thesis_id IN (
    SELECT thesis_id 
    FROM thesis_generations 
    WHERE as_of_date >= '2024-10-24' 
    AND as_of_date <= '2025-11-14'
);

-- Delete old theses
DELETE FROM thesis_generations 
WHERE as_of_date >= '2024-10-24' 
AND as_of_date <= '2025-11-14';
```

### Step 3: Regenerate Theses
```bash
# Run main pipeline for all tickers in date range
python main.py \
    --tickers ALL_TICKERS \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --skip-existing false  # Force regeneration
```

### Step 4: Verify New Theses
- Check prompt structure matches current format
- Verify data includes all new fields
- Confirm DeepSeek API was used

### Step 5: Backfill Positions
```bash
python scripts/backfill_positions.py --execute --yes
```

### Step 6: Regenerate Datasets
```bash
python rlvr_main.py generate \
    --start-date 2024-10-24 \
    --end-date 2025-11-14 \
    --train-split-date 2025-08-01
```

---

## 4. SAFETY CONSIDERATIONS

1. **Backup first**: Export current theses before deletion
2. **Test with one ticker**: Regenerate one ticker first to verify
3. **Monitor API usage**: DeepSeek API calls will be significant
4. **Checkpoint management**: Pipeline uses checkpoints - may need cleanup
5. **Time estimate**: ~1,444 API calls - could take hours

---

## 5. VERIFICATION CHECKLIST

- [ ] Old theses deleted
- [ ] New theses generated with current prompts
- [ ] Prompts include all new data fields
- [ ] DeepSeek API was used (not Fireworks)
- [ ] Positions created for new theses
- [ ] Datasets regenerated
- [ ] QA validation passes

---

**END OF PLAN**
