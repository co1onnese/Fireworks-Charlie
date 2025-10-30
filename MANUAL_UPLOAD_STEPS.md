# Manual Training Job Submission - Step by Step

## Current Status

? **Your datasets are ready and validated:**
- Training file: `/opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl` (1,105 examples)
- Dev file: `/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl` (402 examples)

? **API file upload is failing** - All tested endpoints return 404

## Solution: Use Fireworks Web Dashboard

### Step 1: Access Fireworks Dashboard

1. Go to: https://fireworks.ai/
2. Log in with your account (`lstn`)
3. Navigate to **Fine-tuning** section

### Step 2: Upload Training Files

#### Option A: Direct Upload
1. Click "**Upload Dataset**" or "**New Dataset**"
2. Upload `/opt/Fireworks-Charlie/storage/rlvr_datasets/train.jsonl`
   - Name it: `stock-prediction-train-20251030`
   - Format: JSONL
   - Purpose: Fine-tuning
3. Repeat for dev file:
   - Upload: `/opt/Fireworks-Charlie/storage/rlvr_datasets/dev.jsonl`
   - Name it: `stock-prediction-dev-20251030`

#### Option B: Use CLI (if available)
```bash
# Install Fireworks CLI if not already installed
pip install fireworks-ai

# Upload training file
firectl upload dataset storage/rlvr_datasets/train.jsonl \
    --name stock-prediction-train-20251030 \
    --account lstn

# Upload dev file  
firectl upload dataset storage/rlvr_datasets/dev.jsonl \
    --name stock-prediction-dev-20251030 \
    --account lstn
```

### Step 3: Create GRPO Training Job

1. In Fireworks dashboard, click "**Create Fine-tuning Job**"
2. Fill in the form:

```
Job Name: stock-prediction-grpo-20251030
Algorithm: GRPO
Base Model: accounts/fireworks/models/deepseek-v3p1-terminus

Training Dataset: stock-prediction-train-20251030
Validation Dataset: stock-prediction-dev-20251030

Reward Evaluator: stock-prediction-evaluator
```

3. Configure Hyperparameters:
```
Epochs: 1
Learning Rate: 0.0001
LoRA Rank: 8
Batch Size: 32768 tokens
N Samples (Responses): 4
Temperature: 0.7
Top P: 1.0
Top K: 40
Max Tokens: 8192
```

4. Click "**Submit**" and save the **Job ID**

### Step 4: Monitor Training

Once submitted, monitor progress:

```bash
# Using our CLI
python rlvr_main.py status --job-id <job-id>

# Or check Fireworks dashboard
```

## Alternative: What the API Documentation Says

Based on the Fireworks documentation you mentioned (`https://fireworks.ai/docs/api-reference/upload-dataset-files`), please check:

1. **Correct API Endpoint**: What is the exact URL for file upload?
2. **Request Format**: Does it use multipart/form-data or something else?
3. **Authentication**: Is there additional authentication beyond API key?
4. **Account-specific URLs**: Does the endpoint include account ID?

Once you share these details, I can update the script to use the correct format.

## Troubleshooting

### If Deploy Reward Function Failed

Before starting training, make sure your reward function is deployed:

```bash
python rlvr_main.py deploy
```

This should show:
```
? Reward function deployed successfully!
Evaluator ID: stock-prediction-evaluator
```

### If You See "Evaluator Not Found" Error

The reward function must be deployed before creating the training job. Run:

```bash
python rlvr_main.py deploy
```

Then try creating the training job again.

### Check Available APIs

Try listing your available resources:

```bash
# Check if you can list files/datasets
curl -H "Authorization: Bearer $FIREWORKS_API_KEY" \
     https://api.fireworks.ai/fw/v1/files

# Check fine-tuning jobs
curl -H "Authorization: Bearer $FIREWORKS_API_KEY" \
     https://api.fireworks.ai/fw/v1/fine-tuning/jobs
```

## Expected Training Time

- **Dataset size**: ~72 MB total
- **Examples**: 1,105 training + 402 validation
- **Estimated time**: 2-4 hours (depends on Fireworks capacity)
- **Cost**: Check with Fireworks for GRPO training pricing

## After Training Completes

1. Download the fine-tuned model
2. Test on evaluation examples
3. Compare performance vs base model
4. Document results in `outputs/evaluations/`

## Need Help?

1. **Check Fireworks Docs**: https://docs.fireworks.ai/
2. **Contact Fireworks Support**: 
   - Account ID: `lstn`
   - Issue: "Need help uploading datasets and submitting GRPO training job"
3. **Share the docs**: Let me know what the upload documentation says, and I'll update the script

---

**Status**: Datasets ready ? | Needs manual upload ??
**Next**: Upload files via dashboard ? Create training job ? Monitor progress
