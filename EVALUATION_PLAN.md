# Evaluation Plan for Deployed Model on Fireworks AI

## Quick Reference

**Command to Run**:
```bash
python scripts/evaluate_baseline.py \
  --model accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h \
  --all-strategies \
  --dataset storage/rlvr_datasets/dev.jsonl \
  --output-dir outputs/evaluations
```

**What It Does**: Evaluates the deployed model on all 402 examples using all three trading strategies (A, B, C) and generates comprehensive performance reports.

**Expected Time**: ~90-180 minutes (30-60 minutes per strategy)

**Output Location**: `outputs/evaluations/`

---

## Evaluation Configuration (CONFIRMED)

- **Evaluation Type**: Standalone (baseline evaluation)
- **Trading Strategies**: All strategies (A, B, C)
- **Dataset Scope**: Full dataset (402 examples)
- **Base Model Comparison**: None (standalone evaluation)
- **Output Location**: `outputs/evaluations` (default)

## Model Information
- **Model Name**: `accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h`
- **Model Type**: Deployed fine-tuned model on Fireworks AI
- **Evaluation Date**: TBD

## Dataset Information
- **Primary Dataset**: `storage/rlvr_datasets/dev.jsonl`
- **Total Examples**: 402 examples
- **Format**: JSONL with messages (system + user prompts), ground_truth, and metadata
- **Purpose**: Development/validation set for model evaluation

## Evaluation Framework

**Script**: `scripts/evaluate_baseline.py`

**Purpose**: Evaluate the deployed model independently across all three trading strategies to establish comprehensive performance metrics.

**Command**:
```bash
python scripts/evaluate_baseline.py \
  --model accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h \
  --all-strategies \
  --dataset storage/rlvr_datasets/dev.jsonl \
  --output-dir outputs/evaluations
```

**What This Will Do**:
- Evaluate all 402 examples from dev.jsonl
- Test all three trading strategies (A, B, C)
- Generate comprehensive performance metrics for each strategy
- Create comparison report across strategies
- Save results to `outputs/evaluations/`

## Trading Strategies

### Strategy A: Long-Only (Default)
- **BUY/STRONG_BUY** → Take long position → Portfolio return = actual return
- **HOLD/SELL/STRONG_SELL** → No position → Portfolio return = 0%
- **Use Case**: Conservative strategy, only taking positions on bullish signals

### Strategy B: Long/Short
- **BUY/STRONG_BUY** → Long position → Portfolio return = +actual return
- **HOLD** → No position → Portfolio return = 0%
- **SELL/STRONG_SELL** → Short position → Portfolio return = -actual return
- **Use Case**: More aggressive, allows profiting from both directions

### Strategy C: Weighted Positions
- **STRONG_BUY** → 2x long → Portfolio return = 2 × actual return
- **BUY** → 1x long → Portfolio return = actual return
- **HOLD** → 0x → Portfolio return = 0%
- **SELL** → 1x short → Portfolio return = -actual return
- **STRONG_SELL** → 2x short → Portfolio return = -2 × actual return
- **Use Case**: Leverages confidence levels in predictions

## Execution Plan

### Single Command Execution

Since we're evaluating all strategies on the full dataset, this can be done in one command:

```bash
python scripts/evaluate_baseline.py \
  --model accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h \
  --all-strategies \
  --dataset storage/rlvr_datasets/dev.jsonl \
  --output-dir outputs/evaluations
```

**What Happens**:
1. Script evaluates Strategy A on all 402 examples
2. Script evaluates Strategy B on all 402 examples  
3. Script evaluates Strategy C on all 402 examples
4. Generates individual results for each strategy
5. Creates comparison report across all strategies

**Expected Output Files**:
- `outputs/evaluations/baseline_strategy_A_TIMESTAMP.json` - Strategy A results (JSON)
- `outputs/evaluations/baseline_strategy_A_TIMESTAMP_summary.txt` - Strategy A summary
- `outputs/evaluations/baseline_strategy_B_TIMESTAMP.json` - Strategy B results (JSON)
- `outputs/evaluations/baseline_strategy_B_TIMESTAMP_summary.txt` - Strategy B summary
- `outputs/evaluations/baseline_strategy_C_TIMESTAMP.json` - Strategy C results (JSON)
- `outputs/evaluations/baseline_strategy_C_TIMESTAMP_summary.txt` - Strategy C summary
- `outputs/evaluations/baseline_comparison_TIMESTAMP.txt` - Cross-strategy comparison report

**Total Execution Time**: ~90-180 minutes (30-60 minutes per strategy × 3 strategies)
- Progress logged every 10 examples
- Each strategy processes all 402 examples sequentially

### Optional: Quick Validation First

If you want to verify the setup before running the full evaluation:

```bash
# Quick test with 10 examples on Strategy A only
python scripts/evaluate_baseline.py \
  --model accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h \
  --strategy A \
  --max-examples 10 \
  --output-dir outputs/evaluations
```

This takes ~1-2 minutes and verifies:
- ✅ Model is accessible
- ✅ API connection works
- ✅ Predictions are valid JSON
- ✅ Results save correctly

## Performance Metrics Explained

### 1. Directional Accuracy
- **Definition**: Percentage of predictions that were directionally correct
- **Calculation**: Based on action thresholds:
  - `strong_buy`: Correct if actual return ≥ +3.0%
  - `buy`: Correct if actual return ≥ +2.0%
  - `hold`: Correct if -2.0% ≤ actual return ≤ +2.0%
  - `sell`: Correct if actual return ≤ -2.0%
  - `strong_sell`: Correct if actual return ≤ -3.0%

### 2. Portfolio Returns
- **Mean Return**: Average portfolio return per prediction
- **Total Return**: Cumulative return across all predictions
- **Std Dev**: Volatility of returns
- **Min/Max**: Best and worst single predictions

### 3. Sharpe Ratio
- **Definition**: Risk-adjusted return metric
- **Formula**: (Mean Return - Risk-Free Rate) / Std Dev
- **Interpretation**: Higher is better (measures return per unit of risk)
- **Note**: Not annualized, calculated over actual holding period

### 4. Buy-and-Hold Benchmark
- **Definition**: Performance of simply holding all positions
- **Purpose**: Compare model strategy to passive investment
- **Metrics**: Mean return, std dev, Sharpe ratio

## Output Files

### JSON Results File
- **Location**: `outputs/evaluations/baseline_strategy_X_TIMESTAMP.json`
- **Contents**:
  - Model information
  - Overall metrics (accuracy, returns, Sharpe)
  - Action-level statistics
  - Individual prediction results
  - Buy-and-hold benchmark

### Summary Text File
- **Location**: `outputs/evaluations/baseline_strategy_X_TIMESTAMP_summary.txt`
- **Contents**: Human-readable summary with:
  - Overall performance metrics
  - Portfolio performance breakdown
  - Action statistics
  - Comparison to benchmark
  - Assessment of model performance

### Comparison Report (if using --all-strategies)
- **Location**: `outputs/evaluations/baseline_comparison_TIMESTAMP.txt`
- **Contents**: Side-by-side comparison of all strategies

## Pre-Evaluation Checklist

Before running evaluation, verify:

- [ ] **Fireworks API Key**: Set in environment or `.env` file
  ```bash
  # Check if set
  echo $FIREWORKS_API_KEY
  ```

- [ ] **Dataset Exists**: Verify dev.jsonl is available
  ```bash
  ls -lh storage/rlvr_datasets/dev.jsonl
  ```

- [ ] **Model Access**: Verify model name is correct
  - Model: `accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h`
  - Should be accessible via Fireworks AI API

- [ ] **Output Directory**: Ensure output directory exists
  ```bash
  mkdir -p outputs/evaluations
  ```

- [ ] **Dependencies**: Verify required packages installed
  ```bash
  python -c "import openai; import numpy; import json"
  ```

## Execution Time Estimates

Based on 402 examples per strategy:
- **Single strategy (402 examples)**: ~30-60 minutes
- **All three strategies (3 × 402 = 1,206 total evaluations)**: ~90-180 minutes
  - Depends on API rate limits
  - Progress logged every 10 examples
  - Each strategy runs sequentially

## Troubleshooting

### Common Issues

1. **Model Not Found Error**
   - Verify model name is correct
   - Check Fireworks AI dashboard for exact model ID
   - Ensure model is deployed and accessible

2. **API Rate Limits**
   - Script handles rate limits automatically
   - May take longer if rate limited
   - Consider using `--max-examples` for initial testing

3. **JSON Parsing Errors**
   - Model may return invalid JSON
   - Check logs for specific error messages
   - Review model response format requirements

4. **Dataset Format Issues**
   - Verify dev.jsonl has correct structure
   - Check that messages and ground_truth fields exist
   - Ensure JSON is valid (one example per line)

## Metrics to Review

For each strategy, review:

### Overall Performance
- **Accuracy**: Directional correctness percentage
- **Mean Portfolio Return**: Average return per prediction
- **Total Return**: Cumulative return across all predictions
- **Sharpe Ratio**: Risk-adjusted performance
- **Std Dev**: Volatility of returns

### Action-Level Statistics
- **Action Distribution**: Count and accuracy for each action type (buy/sell/hold/strong_buy/strong_sell)
- **Action Returns**: Mean portfolio return per action type

### Benchmark Comparison
- **Buy-and-Hold Benchmark**: Comparison to passive investment strategy
  - Mean return
  - Std dev
  - Sharpe ratio

### Cross-Strategy Comparison
The comparison report will show:
- Best strategy by accuracy
- Best strategy by mean return
- Best strategy by Sharpe ratio
- Side-by-side metrics table

## Next Steps

1. **Complete Pre-Evaluation Checklist** (see below)
2. **Run the evaluation command** (single command for all strategies)
3. **Review individual strategy results** (JSON and summary files)
4. **Analyze comparison report** to identify best-performing strategy
5. **Document findings** for future reference

## Additional Resources

- **Evaluation Scripts**: `scripts/evaluate_baseline.py`, `scripts/evaluate_model.py`
- **Configuration**: `orchestration/config_manager.py`
- **Dataset Format**: See `llms.txt` section "JSONL DATA FORMATS"
- **Project Documentation**: `llms.txt`

---

**Created**: 2025-11-05
**Model**: `accounts/lstn/deployedModels/ft-mhkk2kzf-3w4yk-my7vo15h`
**Dataset**: `storage/rlvr_datasets/dev.jsonl` (402 examples)
