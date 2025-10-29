# Fireworks-Charlie RLVR Implementation Plan

**Complete Implementation Roadmap for RLVR Training Pipeline with GRPO**

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Documentation References](#documentation-references)
3. [Implementation Timeline](#implementation-timeline)
4. [Phase 0: Database Setup](#phase-0-database-setup-completed-)
5. [Phase 1: Fireworks Foundation](#phase-1-fireworks-foundation)
6. [Phase 2: Reward Function & reward-kit](#phase-2-reward-function--reward-kit)
7. [Phase 3: Pipeline Integration](#phase-3-pipeline-integration)
8. [Phase 4: Documentation & Testing](#phase-4-documentation--testing)
9. [Technical Specifications](#technical-specifications)
10. [Success Criteria](#success-criteria)
11. [Risk Mitigation](#risk-mitigation)

---

## Project Overview

**Goal**: Transform Trainer-Charlie into a complete RLVR (Reinforcement Learning with Verifiable Rewards) training pipeline for Fireworks.ai using GRPO (Group Relative Policy Optimization).

**Key Changes**:
- Migrate from DeepSeek generic to **DeepSeek V3.1-Terminus** via Fireworks
- Implement **GRPO training** (no value model, multi-response generation)
- Create **verifiable reward function** (80% directional accuracy, 20% Sharpe ratio)
- Generate **JSONL datasets** in Fireworks format
- Support **3-day position tracking** with early exit logic
- Deploy reward function using **Fireworks reward-kit**

---

## Documentation References

### Primary Documentation
1. **Fireworks RLVR Blog Post**
   - URL: https://fireworks.ai/blog/reinforcement-learning-with-verifiable-reward
   - Key Topics: RLVR overview, GRPO vs PPO, verifiable rewards
   - Used For: Understanding GRPO architecture, reward function design

2. **Fireworks Evaluator Developer Guide**
   - URL: https://docs.fireworks.ai/evaluators/developer_guide/evaluation_workflows
   - Key Topics: @reward_function decorator, EvaluateResult, reward-kit CLI
   - Used For: Reward function implementation, local testing workflow

3. **Fireworks Reinforcement Fine-Tuning**
   - URL: https://fireworks.ai/docs/fine-tuning/reinforcement-fine-tuning-models
   - Key Topics: JSONL format, GRPO parameters, multi-response generation
   - Used For: Dataset format, training configuration, deployment

4. **DeepSeek V3.1-Terminus Model**
   - URL: https://fireworks.ai/models/deepseek-ai/deepseek-v3p1-terminus
   - Key Topics: Model specs, 128K context, thinking modes
   - Used For: Model selection and configuration

### Local Documentation
1. **Database Schema**: `/opt/Fireworks-Charlie/database/README.md`
2. **Project README**: `/opt/Fireworks-Charlie/README.md`
3. **Environment Config**: `/opt/Fireworks-Charlie/.env.example`

### Technical References
1. **SQLAlchemy 2.0 Documentation**: https://docs.sqlalchemy.org/en/20/
2. **PostgreSQL Partitioning**: https://www.postgresql.org/docs/current/ddl-partitioning.html
3. **JSONB in PostgreSQL**: https://www.postgresql.org/docs/current/datatype-json.html

---

## Implementation Timeline

**Total Estimated Duration**: 10-12 days

| Sprint | Days | Status | Description |
|--------|------|--------|-------------|
| Sprint 0 | 1 day | ✅ **COMPLETED** | Database infrastructure |
| Sprint 1 | 2-3 days | 🔲 Pending | Fireworks foundation |
| Sprint 2 | 2-3 days | 🔲 Pending | Reward function & reward-kit |
| Sprint 3 | 2-3 days | 🔲 Pending | Pipeline integration |
| Sprint 4 | 1 day | 🔲 Pending | Documentation & testing |

---

## Phase 0: Database Setup ✅ **COMPLETED**

### Objectives
- ✅ Design optimized PostgreSQL schema for RLVR pipeline
- ✅ Create 14 tables with proper indexing and partitioning
- ✅ Implement position tracking and Sharpe calculation functions
- ✅ Set up automated database initialization

### Deliverables Completed

#### 1. Database SQL Scripts
**Location**: `/opt/Fireworks-Charlie/database/`

- **01_tables.sql** ✅
  - 14 tables created
  - Core: tickers, market_data (partitioned), fundamentals, news, macro_indicators, macro_features, insider_transactions
  - RLVR: thesis_generations, positions, rlvr_training_examples, historical_returns, sharpe_calculations
  - Audit: data_collection_runs, rlvr_generation_runs
  - Features: JSONB columns, partitioning, constraints

- **02_indexes.sql** ✅
  - 60+ indexes created
  - B-tree indexes for common queries
  - GIN indexes for JSONB columns
  - Partial indexes for filtered queries
  - Composite indexes for RLVR export

- **03_views.sql** ✅
  - 7 standard views
  - 2 materialized views (mv_daily_rlvr_metrics, mv_ticker_summary)
  - refresh_all_materialized_views() function

- **04_functions.sql** ✅
  - 9 stored procedures:
    - `calculate_position_return()` - 3-day tracking with early exit
    - `check_directional_accuracy()` - Prediction validation
    - `calculate_sharpe_ratio()` - Sharpe from returns array
    - `get_historical_returns()` - Fetch historical data
    - `update_position_performance()` - Calculate metrics
    - `update_all_open_positions()` - Batch updates
    - `update_return_sequences()` - Sequence maintenance
    - `cleanup_old_data()` - Data retention
    - `database_health_check()` - Health monitoring

#### 2. Database Manager
**Location**: `/opt/Fireworks-Charlie/data_collection/database_manager.py`

- ✅ Completely rewritten with SQLAlchemy 2.0
- ✅ All 14 table models defined
- ✅ Proper relationships and cascades
- ✅ Property aliases for backward compatibility
- ✅ Connection pooling and health checks

#### 3. Setup Script
**Location**: `/opt/Fireworks-Charlie/scripts/setup_database.sh`

- ✅ Automated PostgreSQL installation
- ✅ Database and user creation
- ✅ SQL script execution
- ✅ Health check validation
- ✅ Colored output and error handling

#### 4. Configuration
**Location**: `/opt/Fireworks-Charlie/.env.example`

- ✅ Database configuration (host, port, user, password)
- ✅ Fireworks API configuration
- ✅ DeepSeek V3.1-Terminus settings
- ✅ GRPO training parameters
- ✅ RLVR dataset configuration
- ✅ Reward function weights (80/20)
- ✅ Position management settings
- ✅ Expected return thresholds

#### 5. Documentation
**Location**: `/opt/Fireworks-Charlie/database/README.md`

- ✅ Complete schema documentation
- ✅ Usage examples
- ✅ Maintenance procedures
- ✅ Troubleshooting guide

### Key Design Decisions

1. **Time-Series Partitioning**: `market_data` partitioned by year for scalability
2. **JSONB Storage**: Full prompts and responses stored as JSONB
3. **Position Tracking**: Stored procedure with early exit logic
4. **Denormalization**: RLVR examples denormalized for fast export
5. **Audit Trails**: Complete tracking with created_at/updated_at

---

## Phase 1: Fireworks Foundation

### Sprint 1: Fireworks Setup (Days 1-3)

#### Day 1: Configuration & SDK Setup

**Tasks**:
1. Update `orchestration/config_manager.py`
   - Add Fireworks configuration properties
   - Add GRPO training parameters
   - Add generation parameters
   - Add reward function configuration
   - Validate weights sum to 100%

2. Install Fireworks SDK
   ```bash
   pip install fireworks-ai>=0.15.0
   pip install trl>=0.8.0  # For TRL adapter integration
   ```

3. Update `pyproject.toml` / `requirements.txt`
   ```toml
   fireworks-ai = "^0.15.0"
   trl = "^0.8.0"
   ```

4. Test Fireworks API connection
   ```python
   from fireworks.client import Fireworks
   client = Fireworks(api_key=config.FIREWORKS_API_KEY)
   # Test connection
   ```

**Deliverables**:
- [ ] Updated `config_manager.py` with all Fireworks properties
- [ ] Fireworks SDK installed and tested
- [ ] API connection validated

#### Day 2: Model Client Migration

**Tasks**:
1. Create `thesis_generation/fireworks_client.py`
   - Rename from `llm_client.py` or create new
   - Implement `FireworksDeepSeekClient` class
   - Support DeepSeek V3.1-Terminus (671B params, 37B active)
   - Implement JSON response format (not XML)
   - Support both `deepseek-chat` and `deepseek-reasoner` modes

2. Update system prompt for JSON
   ```python
   system_prompt = """You are a senior financial analyst...

   Your response MUST be valid JSON in this exact format:
   {
     "reasoning": "Comprehensive analysis...",
     "action": "buy",  // one of: strong_buy, buy, hold, sell, strong_sell
     "support": "Key supporting evidence..."
   }
   """
   ```

3. Implement JSON parsing
   - Use `response_format={"type": "json_object"}` for Fireworks
   - Parse and validate response
   - Extract reasoning, action, support fields

4. Test with sample prompt
   - Generate test thesis
   - Verify JSON parsing
   - Check token usage (128K context support)

**Deliverables**:
- [ ] `FireworksDeepSeekClient` class implemented
- [ ] JSON response parsing working
- [ ] Test generation successful

**File**: `thesis_generation/fireworks_client.py`
```python
class FireworksDeepSeekClient:
    def __init__(self, api_key: str, account_id: str):
        self.client = OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=api_key
        )
        self.model = f"accounts/{account_id}/models/deepseek-v3p1-terminus"

    def generate_thesis_json(self, prompt, ticker, as_of_date, temperature=0.7):
        # Implementation
```

#### Day 3: Core RLVR Components

**Tasks**:
1. Create `rlvr/` directory
   ```bash
   mkdir -p /opt/Fireworks-Charlie/rlvr
   ```

2. Create `rlvr/position_tracker.py`
   - Implement `PositionTracker` class
   - Method: `calculate_position_return(ticker, entry_date, entry_action, all_daily_theses, price_data)`
   - Logic:
     - Start with entry_date close price
     - Iterate through next 3 trading days
     - Check for signal change on day 2/3 (early exit if changes to hold/sell/strong_sell)
     - Calculate return: `(exit_price - entry_price) / entry_price * 100`
   - Return: `{return_pct, exit_date, days_held, early_exit, early_exit_reason}`
   - Handle edge cases: insufficient data, market closures

3. Create `rlvr/performance_calculator.py`
   - Implement `PerformanceCalculator` class
   - Method: `calculate_directional_accuracy(action, actual_return)`
     - Map action to expected return using thresholds from config
     - Return 1.0 if correct direction, 0.0 otherwise
   - Method: `calculate_trailing_sharpe_ratio(historical_returns, risk_free_rate=0.0)`
     - Calculate: `(mean_return - risk_free_rate) / std_dev_returns`
     - Normalize to 0-1: Sharpe < 1.0 → 0.0, Sharpe >= 1.0 → sigmoid scaling
   - Method: `combine_scores(directional_score, sharpe_score, weights)`
     - Return weighted average based on config weights

4. Write unit tests
   - Test position tracking with various scenarios
   - Test early exit logic
   - Test directional accuracy calculation
   - Test Sharpe ratio calculation

**Deliverables**:
- [ ] `PositionTracker` class with early exit logic
- [ ] `PerformanceCalculator` class with scoring methods
- [ ] Unit tests passing

---

## Phase 2: Reward Function & reward-kit

### Sprint 2: Reward Function (Days 4-6)

#### Day 4: Reward Function Implementation

**Tasks**:
1. Create `rlvr/reward_function.py`
   - Use `@reward_function` decorator from Fireworks SDK
   - Implement `stock_prediction_reward()` function
   - Signature:
     ```python
     @reward_function
     def stock_prediction_reward(
         messages: List[Dict[str, str]],
         original_messages: Optional[List[Dict[str, str]]] = None,
         **kwargs
     ) -> EvaluateResult:
     ```
   - Extract assistant response from messages
   - Parse JSON prediction
   - Get ground_truth from kwargs
   - Calculate directional accuracy score
   - Calculate Sharpe score from historical_returns
   - Combine scores with weights (80/20)
   - Return EvaluateResult with score, reason, metrics

2. Implement error handling
   - Invalid JSON response → score=0.0, is_score_valid=False
   - Invalid action → score=0.0, is_score_valid=False
   - Missing ground_truth → score=0.0, is_score_valid=False

3. Add detailed metrics
   - `directional_accuracy`: MetricResult with value and reason
   - `sharpe_score`: MetricResult with value and reason
   - `actual_return`: MetricResult for tracking

**Deliverables**:
- [ ] Reward function with `@reward_function` decorator
- [ ] Proper EvaluateResult structure
- [ ] Comprehensive error handling

**Reference**: https://docs.fireworks.ai/evaluators/developer_guide/evaluation_workflows

#### Day 5: reward-kit Configuration

**Tasks**:
1. Create `rlvr/reward_kit_config.py`
   - Generate YAML config for reward-kit CLI
   - Function: `generate_run_eval_config(output_path)`
   - Config structure:
     ```yaml
     dataset:
       path: storage/rlvr_datasets/dev.jsonl
       format: jsonl
     reward_function:
       module: rlvr.reward_function
       function: stock_prediction_reward
     output:
       dir: ./outputs/evaluations
       format: jsonl
     ```

2. Create `conf/` directory
   ```bash
   mkdir -p /opt/Fireworks-Charlie/conf
   ```

3. Test reward-kit locally
   ```bash
   # Generate config
   python -c "from rlvr.reward_kit_config import generate_run_eval_config; generate_run_eval_config()"

   # Run evaluation
   python -m reward_kit.cli run \
     --config-path ./conf \
     --config-name run_eval.yaml

   # Preview results
   reward-kit preview \
     --samples ./outputs/evaluations/.../preview_input_output_pairs.jsonl
   ```

4. Create test script
   **File**: `scripts/test_reward_locally.sh`
   ```bash
   #!/bin/bash
   # Test reward function with reward-kit
   python -c "from rlvr.reward_kit_config import generate_run_eval_config; generate_run_eval_config()"
   python -m reward_kit.cli run --config-path ./conf --config-name run_eval.yaml
   reward-kit preview --samples ./outputs/evaluations/$(ls -t outputs/evaluations | head -1)/preview_input_output_pairs.jsonl
   ```

**Deliverables**:
- [ ] reward-kit YAML config generation
- [ ] Local testing workflow established
- [ ] Test script created

#### Day 6: JSON Formatter & Dataset Generation

**Tasks**:
1. Create `rlvr/json_formatter.py`
   - Implement `create_training_example()` - NO assistant message
     ```python
     {
         "messages": [
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}
         ],
         "ground_truth": {...},
         "metadata": {...}
     }
     ```
   - Implement `create_dev_example()` - WITH assistant message
     ```python
     {
         "messages": [
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt},
             {"role": "assistant", "content": json.dumps(assistant_response)}
         ],
         "ground_truth": {...},
         "metadata": {...}
     }
     ```

2. Validate Fireworks format
   - Ensure matches JSONL specification
   - Test JSON serialization
   - Verify all required fields present

3. Create `rlvr/rlvr_dataset_generator.py` (stub)
   - Will be completed in Sprint 3
   - Basic structure for dataset generation

**Deliverables**:
- [ ] JSON formatter for train/dev examples
- [ ] Format validation against Fireworks spec
- [ ] Dataset generator stub

---

## Phase 3: Pipeline Integration

### Sprint 3: Integration (Days 7-9)

#### Day 7: Pipeline Updates

**Tasks**:
1. Update `thesis_generation/prompt_builder.py`
   - Add method: `build_cumulative_prompt_messages(ticker, data_up_to_date)`
   - Return: `(system_prompt, user_prompt)` as separate strings
   - Keep existing `build_cumulative_prompt()` for backward compatibility

2. Update `orchestration/checkpoint_manager.py`
   - Extend checkpoint format to include prompts
   - New structure:
     ```python
     {
         "ticker": str,
         "last_processed_date": str,
         "cumulative_data": [...],
         "prompts": [
             {
                 "date": str,
                 "system_prompt": str,
                 "user_prompt": str,
                 "assistant_response": dict
             }
         ],
         "metadata": {...}
     }
     ```

3. Update `orchestration/main_pipeline.py`
   - Add RLVR mode branch
   - If `config.RLVR_MODE == True`:
     - Use FireworksDeepSeekClient
     - Generate JSON responses
     - Store prompts in checkpoints
     - Store in thesis_generations table
   - Maintain backward compatibility with XML mode

**Deliverables**:
- [ ] Prompt builder returns separate messages
- [ ] Checkpoints store prompts
- [ ] Pipeline supports RLVR mode

#### Day 8: RLVR Dataset Generator

**Tasks**:
1. Complete `rlvr/rlvr_dataset_generator.py`
   - Class: `RLVRDatasetGenerator`
   - Method: `generate_rlvr_datasets(tickers, train_dates, test_dates)`
   - Logic:
     1. For each ticker:
        - Query thesis_generations from database
        - For each thesis:
          - Calculate position return (3-day with early exit)
          - Skip if insufficient data or error action
          - Get historical returns for Sharpe
          - Format as training or dev example
          - Assign to train/test based on date
     2. Write JSONL files
     3. Generate statistics report

2. Implement position tracking integration
   - Use database function `calculate_position_return()`
   - Store results in `positions` table
   - Update `historical_returns` table

3. Implement Sharpe calculation
   - Query historical returns from database
   - Use database function `calculate_sharpe_ratio()`
   - Cache in `sharpe_calculations` table

4. Write to database
   - Insert into `rlvr_training_examples` table
   - Store complete example_json, ground_truth, metadata
   - Calculate and store scores

**Deliverables**:
- [ ] Complete dataset generator implementation
- [ ] Database integration for positions and Sharpe
- [ ] JSONL file export

#### Day 9: Deployment Scripts

**Tasks**:
1. Create `scripts/deploy_reward_function.py`
   ```python
   from rlvr.reward_function import stock_prediction_reward

   evaluation_id = stock_prediction_reward.deploy(
       name=config.EVALUATOR_ID,
       description=config.EVALUATOR_NAME,
       force=True
   )
   ```

2. Create `scripts/train_grpo_model.py`
   ```python
   from fireworks.client import Fireworks

   client = Fireworks(api_key=config.FIREWORKS_API_KEY)

   training_job = client.fine_tuning.create(
       model=config.MODEL_NAME,
       training_file=config.RLVR_TRAIN_FILE,
       validation_file=config.RLVR_DEV_FILE,
       hyperparameters={
           "n_epochs": config.GRPO_EPOCHS,
           "learning_rate": config.GRPO_LEARNING_RATE,
           "lora_rank": config.GRPO_LORA_RANK,
           "batch_size": config.GRPO_BATCH_SIZE,
           "algorithm": "grpo",
           "n_samples": config.GRPO_NUM_RESPONSES,
           "temperature": config.GEN_TEMPERATURE,
           ...
       },
       reward_config={"evaluator_id": config.EVALUATOR_ID}
   )
   ```

3. Create `rlvr_main.py` entry point
   - Modes: generate, test-local, deploy, train, validate, stats
   - Usage:
     ```bash
     python rlvr_main.py --mode generate --tickers AAPL,MSFT
     python rlvr_main.py --mode test-local
     python rlvr_main.py --mode deploy
     python rlvr_main.py --mode train
     ```

4. Test end-to-end workflow
   - Generate small dataset
   - Test reward function locally
   - Deploy reward function (dry run)
   - Submit training job (dry run)

**Deliverables**:
- [ ] Deployment scripts created
- [ ] Training submission script
- [ ] CLI entry point (rlvr_main.py)
- [ ] End-to-end workflow tested

---

## Phase 4: Documentation & Testing

### Sprint 4: Finalization (Day 10)

#### Documentation

**Tasks**:
1. Update `README.md`
   - Add RLVR mode section
   - Document Fireworks integration
   - Add workflow diagrams
   - Include usage examples

2. Create `docs/RLVR_GUIDE.md`
   - Architecture overview
   - Dataset format specification
   - Reward function design
   - Position tracking logic
   - GRPO training guide
   - Troubleshooting

3. Create `docs/REWARD_FUNCTION.md`
   - Mathematical formulation
   - Directional accuracy calculation
   - Sharpe ratio calculation
   - Weight tuning guide
   - Metrics explanation

4. Create `docs/FIREWORKS_WORKFLOW.md`
   - Step-by-step workflow
   - Local testing guide
   - Deployment guide
   - Monitoring guide

**Deliverables**:
- [ ] README.md updated
- [ ] RLVR_GUIDE.md created
- [ ] REWARD_FUNCTION.md created
- [ ] FIREWORKS_WORKFLOW.md created

#### Testing

**Tasks**:
1. Create test files
   - `tests/test_position_tracker.py`
   - `tests/test_performance_calculator.py`
   - `tests/test_reward_function.py`
   - `tests/test_json_formatter.py`
   - `tests/test_rlvr_dataset_generator.py`
   - `tests/test_fireworks_integration.py`
   - `tests/test_reward_kit.py`

2. Run full test suite
   ```bash
   pytest tests/ -v
   ```

3. Generate test datasets
   - Small dataset: 1 ticker, 10 days
   - Validate JSONL format
   - Test reward function evaluation

4. Integration testing
   - Full pipeline run
   - Dataset generation
   - Reward function deployment
   - Training job submission (dry run)

**Deliverables**:
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Test datasets generated
- [ ] End-to-end workflow validated

---

## Technical Specifications

### Dataset Format

#### Training Dataset (JSONL)
```json
{
  "messages": [
    {"role": "system", "content": "You are a senior financial analyst..."},
    {"role": "user", "content": "=== COMPREHENSIVE INVESTMENT ANALYSIS FOR AAPL ===\n..."}
  ],
  "ground_truth": {
    "actual_return_pct": 2.45,
    "exit_date": "2024-01-05",
    "days_held": 3,
    "early_exit": false,
    "entry_price": 185.50,
    "exit_price": 190.04
  },
  "metadata": {
    "ticker": "AAPL",
    "entry_date": "2024-01-02",
    "historical_returns": [1.2, -0.5, 3.1, ...]
  }
}
```

#### Dev Dataset (JSONL)
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "{\"reasoning\": \"...\", \"action\": \"buy\", \"support\": \"...\"}"}
  ],
  "ground_truth": {...},
  "metadata": {...}
}
```

### Reward Function Logic

```python
# Directional Accuracy (80%)
if action in ['strong_buy', 'buy'] and actual_return >= 0:
    directional_score = 1.0
elif action == 'hold' and -1.0 <= actual_return <= 1.0:
    directional_score = 1.0
elif action in ['sell', 'strong_sell'] and actual_return <= 0:
    directional_score = 1.0
else:
    directional_score = 0.0

# Sharpe Score (20%)
if len(historical_returns) < 2:
    sharpe_score = 0.0
else:
    mean_return = mean(historical_returns)
    std_return = std(historical_returns)
    sharpe_ratio = mean_return / std_return if std_return > 0 else 0

    if sharpe_ratio < 1.0:
        sharpe_score = 0.0
    else:
        sharpe_score = 1.0 / (1.0 + exp(-1.0 * (sharpe_ratio - 1.0)))

# Combined Score
final_score = 0.80 * directional_score + 0.20 * sharpe_score
```

### Position Tracking Logic

```python
# 3-day hold with early exit
for day in range(1, 4):
    current_date = trading_days[day]
    current_price = get_close_price(ticker, current_date)

    # Check for signal change on day 2 or 3
    if day >= 2:
        new_action = get_action(ticker, current_date)
        if new_action in ['hold', 'sell', 'strong_sell'] and \
           entry_action in ['buy', 'strong_buy']:
            # Early exit
            exit_date = current_date
            exit_price = current_price
            early_exit = True
            break

    # Normal exit on day 3
    if day == 3:
        exit_date = current_date
        exit_price = current_price
        early_exit = False

return_pct = ((exit_price - entry_price) / entry_price) * 100
```

### Expected Return Thresholds

| Action | Expected Return | Directional Correct If |
|--------|-----------------|------------------------|
| strong_buy | ≥ +3% | actual_return >= 0 |
| buy | ≥ +2% | actual_return >= 0 |
| hold | -1% to +1% | -1.0 <= actual_return <= 1.0 |
| sell | ≤ -2% | actual_return <= 0 |
| strong_sell | ≤ -3% | actual_return <= 0 |

### GRPO Training Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| n_responses | 4 | 2-8 | Responses per prompt |
| epochs | 1 | 1-10 | Training epochs |
| learning_rate | 0.0001 | 1e-5 to 5e-4 | Learning rate |
| lora_rank | 8 | 4-128 | LoRA rank |
| batch_size | 32768 | Hardware-dependent | Tokens per batch |
| temperature | 0.7 | 0.1-2.0 | Generation temperature |
| top_p | 1.0 | 0-1 | Nucleus sampling |
| top_k | 40 | 0-100 | Top-k sampling |
| max_tokens | 2048 | 16-16384 | Max response length |

---

## Success Criteria

### Technical Metrics
- ✅ Database initialized with all 14 tables
- [ ] 100% of valid theses converted to RLVR format
- [ ] <5% of examples skipped due to data issues
- [ ] Reward function execution time <100ms per example
- [ ] JSONL files validate with Fireworks schema
- [ ] reward-kit local evaluation passes
- [ ] Reward function successfully deployed to Fireworks
- [ ] GRPO training job submitted successfully

### Business Metrics
- [ ] Directional accuracy baseline: >55% (better than random)
- [ ] Trailing Sharpe ratio baseline: >0.5
- [ ] RFT training improves baseline by >10%
- [ ] Model generates diverse responses (n=4)

### Quality Metrics
- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Code reviewed and approved
- [ ] No breaking changes to existing XML pipeline

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| Fireworks API format changes | Medium | High | Version pin SDK; monitor docs regularly |
| Insufficient historical data | Low | Medium | Implement data collection backfill |
| Reward function misaligned | Medium | High | A/B test different weight configurations |
| GRPO training failures | Medium | High | Start with small dataset; validate format |
| Performance bottlenecks | Low | Low | Profile code; optimize database queries |
| Backward compatibility breaks | Low | Medium | Use feature flags; maintain dual modes |
| Database migration issues | Low | Medium | Test on staging; have rollback plan |

---

## Current Status

### Completed ✅

**Sprint 0: Database Setup**
- [x] Created 14-table PostgreSQL schema
- [x] Implemented 60+ optimized indexes
- [x] Created 9 views (7 standard + 2 materialized)
- [x] Implemented 9 stored procedures
- [x] Wrote automated setup script
- [x] Rewrote database_manager.py with SQLAlchemy 2.0
- [x] Updated .env.example with Fireworks config
- [x] Created database documentation

**Files Created**:
- database/01_tables.sql
- database/02_indexes.sql
- database/03_views.sql
- database/04_functions.sql
- database/README.md
- scripts/setup_database.sh
- data_collection/database_manager.py (rewritten)
- .env.example (updated)

### In Progress 🔄

**Sprint 1: Fireworks Foundation**
- [ ] Update config_manager.py
- [ ] Install Fireworks SDK
- [ ] Create FireworksDeepSeekClient
- [ ] Create PositionTracker
- [ ] Create PerformanceCalculator
- [ ] Write unit tests

### Upcoming 📋

**Sprint 2**: Reward function & reward-kit
**Sprint 3**: Pipeline integration
**Sprint 4**: Documentation & testing

---

## Quick Reference Commands

### Database Setup
```bash
cd /opt/Fireworks-Charlie
./scripts/setup_database.sh
```

### Database Connection
```bash
psql -h localhost -U fireworks_app -d fireworks_charlie
```

### Health Check
```sql
SELECT * FROM database_health_check();
```

### Dataset Generation
```bash
python rlvr_main.py --mode generate --tickers AAPL,MSFT
```

### Local Reward Testing
```bash
python rlvr_main.py --mode test-local
```

### Deploy Reward Function
```bash
python rlvr_main.py --mode deploy
```

### Submit GRPO Training
```bash
python rlvr_main.py --mode train
```

---

## Contact & Support

**Project**: Fireworks-Charlie RLVR Pipeline
**Version**: 1.0
**Last Updated**: 2025-10-29

**Key Files**:
- Implementation Plan: `/opt/Fireworks-Charlie/IMPLEMENTATION_PLAN.md`
- Database Schema: `/opt/Fireworks-Charlie/database/README.md`
- Environment Config: `/opt/Fireworks-Charlie/.env.example`

**External Documentation**:
- Fireworks RLVR: https://fireworks.ai/blog/reinforcement-learning-with-verifiable-reward
- Evaluator Guide: https://docs.fireworks.ai/evaluators/developer_guide/evaluation_workflows
- Fine-Tuning: https://fireworks.ai/docs/fine-tuning/reinforcement-fine-tuning-models

---

**End of Implementation Plan**
