# GRPO Training Submission Guide

## Issue
The Fireworks API is returning 404 errors for both file upload and training job submission. This typically means either:
1. The API endpoints have changed
2. GRPO/RLVR training requires using the Fireworks CLI (`firectl`) instead of REST API
3. Different authentication or account setup is required

## Your Training Files Are Ready! ?

Your datasets have been generated successfully:
- **Training file**: `/opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl` (1,105 examples, 63 MB)
- **Dev file**: `/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl` (402 examples, 9 MB)
- **Date split**: Training (2023-10-24 to 2025-06-30), Dev (2025-07-01 to 2025-10-23)

## Training Configuration

From your `.env` file:
```yaml
Model: accounts/fireworks/models/deepseek-v3p1-terminus
Algorithm: GRPO (Group Relative Policy Optimization)
Evaluator ID: stock-prediction-evaluator

Hyperparameters:
  - Epochs: 1
  - Learning Rate: 0.0001
  - LoRA Rank: 8
  - Batch Size: 32,768 tokens
  - Num Responses (n_samples): 4
  - Temperature: 0.7
  - Top P: 1.0
  - Top K: 40
  - Max Tokens: 8,192
```

## Option 1: Use Fireworks CLI (Recommended)

### Install Fireworks CLI
```bash
pip install fireworks-ai[reward-kit]
```

### Upload Training Files
```bash
# Upload training file
firectl create dataset rlvr-stock-train \
    --file /opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl \
    --account lstn

# Upload dev file
firectl create dataset rlvr-stock-dev \
    --file /opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl \
    --account lstn
```

### Submit GRPO Training Job
```bash
firectl create fine-tuning-job \
    --base-model accounts/fireworks/models/deepseek-v3p1-terminus \
    --dataset rlvr-stock-train \
    --validation-dataset rlvr-stock-dev \
    --reward-evaluator stock-prediction-evaluator \
    --algorithm grpo \
    --n-samples 4 \
    --epochs 1 \
    --learning-rate 0.0001 \
    --lora-rank 8 \
    --batch-size 32768 \
    --temperature 0.7 \
    --account lstn
```

## Option 2: Use Fireworks Web Dashboard

1. **Go to Fireworks AI Dashboard**: https://fireworks.ai/
2. **Navigate to Fine-tuning**
3. **Upload Training Files**:
   - Click "Upload Dataset"
   - Upload `train.jsonl` (name it: `rlvr-stock-train`)
   - Upload `dev.jsonl` (name it: `rlvr-stock-dev`)

4. **Create Fine-tuning Job**:
   - Click "Create Fine-tuning Job"
   - Select algorithm: **GRPO**
   - Base model: `accounts/fireworks/models/deepseek-v3p1-terminus`
   - Training dataset: `rlvr-stock-train`
   - Validation dataset: `rlvr-stock-dev`
   - Reward evaluator: `stock-prediction-evaluator`
   
5. **Configure Hyperparameters**:
   ```
   Epochs: 1
   Learning rate: 0.0001
   LoRA rank: 8
   Batch size: 32768
   N samples: 4
   Temperature: 0.7
   Top P: 1.0
   Top K: 40
   ```

6. **Submit Job** and note the job ID

## Option 3: Python SDK (Direct API)

If you want to try the Python SDK directly:

```python
from fireworks.client import Fireworks

client = Fireworks(api_key="fw_3ZitG29LSUeoU6YogvVUj79b")

# Upload training file
with open("/opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl", "rb") as f:
    train_file = client.files.create(
        file=f,
        purpose="fine-tune"
    )

# Upload dev file
with open("/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl", "rb") as f:
    dev_file = client.files.create(
        file=f,
        purpose="fine-tune"
    )

# Submit GRPO training job
job = client.fine_tuning.jobs.create(
    model="accounts/fireworks/models/deepseek-v3p1-terminus",
    training_file=train_file.id,
    validation_file=dev_file.id,
    hyperparameters={
        "n_epochs": 1,
        "learning_rate": 0.0001,
        "lora_rank": 8,
        "batch_size": 32768,
        "algorithm": "grpo",
        "n_samples": 4,
        "temperature": 0.7,
        "top_p": 1.0,
        "top_k": 40,
        "max_tokens": 8192
    },
    reward_config={
        "evaluator_id": "stock-prediction-evaluator"
    }
)

print(f"Job ID: {job.id}")
print(f"Status: {job.status}")
```

## Check Training Status

### Using CLI
```bash
# List all jobs
firectl list fine-tuning-jobs --account lstn

# Check specific job
firectl get fine-tuning-job <job-id> --account lstn
```

### Using Python
```python
from fireworks.client import Fireworks

client = Fireworks(api_key="fw_3ZitG29LSUeoU6YogvVUj79b")

# List jobs
jobs = client.fine_tuning.jobs.list()
for job in jobs:
    print(f"{job.id}: {job.status}")

# Check specific job
job = client.fine_tuning.jobs.retrieve("<job-id>")
print(f"Status: {job.status}")
print(f"Progress: {job.trained_tokens}/{job.total_tokens} tokens")
```

### Using Our CLI
```bash
python rlvr_main.py status
python rlvr_main.py status --job-id <job-id>
```

## Before You Deploy the Reward Function

**IMPORTANT**: You need to deploy your reward function first!

```bash
python rlvr_main.py deploy
```

This will deploy `rlvr/reward_function.py` to Fireworks as evaluator `stock-prediction-evaluator`.

## Troubleshooting

### 1. Reward Function Not Found
**Error**: "Evaluator stock-prediction-evaluator not found"

**Solution**: Deploy the reward function first:
```bash
python rlvr_main.py deploy
```

### 2. API Authentication Issues
**Error**: 401 Unauthorized

**Solution**: Check your API key in `.env`:
```bash
grep FIREWORKS_API_KEY .env
```

### 3. File Format Issues
**Error**: "Invalid JSONL format"

**Solution**: Validate your files:
```bash
# Check format
head -1 storage/rlvr_datasets/train.jsonl | python3 -m json.tool

# Count lines
wc -l storage/rlvr_datasets/*.jsonl
```

### 4. API Endpoint Issues (Current Problem)
**Error**: 404 Not Found

**Possible Causes**:
- API endpoints may have changed
- Account not set up for RLVR/GRPO
- Need to use CLI instead of REST API

**Solution**: Use Fireworks CLI or Dashboard (Options 1 or 2 above)

## Next Steps After Training

1. **Monitor training progress** - Check dashboard or CLI regularly
2. **Evaluate model** - Once complete, download and test the fine-tuned model
3. **Compare performance** - Compare base model vs fine-tuned on your test set
4. **Iterate** - Adjust hyperparameters if needed and retrain

## Support

If you continue to have issues:
1. Check Fireworks AI documentation: https://docs.fireworks.ai/
2. Contact Fireworks support with your account ID: `lstn`
3. Check Fireworks Discord/community for RLVR/GRPO examples
