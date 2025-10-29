#!/bin/bash
# Test reward function with reward-kit CLI

set -e  # Exit on any error

echo "🧪 Testing Reward Function with reward-kit CLI"
echo "=============================================="

# Change to project directory
cd /opt/Fireworks-Charlie

# Activate virtual environment
source .venv/bin/activate

echo "📋 Step 1: Generate configuration files"
python -c "
from rlvr.reward_kit_config import generate_run_eval_config, create_sample_dataset
eval_config = generate_run_eval_config()
dataset = create_sample_dataset('storage/rlvr_datasets/test_reward_kit.jsonl', 3)
print(f'✓ Generated config: {eval_config}')
print(f'✓ Generated dataset: {dataset}')
"

echo ""
echo "📋 Step 2: Validate dataset format"
python -c "
from rlvr.reward_kit_config import validate_dataset_format
results = validate_dataset_format('storage/rlvr_datasets/test_reward_kit.jsonl')
print(f'Dataset valid: {results[\"valid\"]}')
print(f'Total examples: {results[\"total_examples\"]}')
if results['errors']:
    print('Errors:')
    for error in results['errors']:
        print(f'  - {error}')
if results['warnings']:
    print('Warnings:')
    for warning in results['warnings']:
        print(f'  - {warning}')
"

echo ""
echo "📋 Step 3: Test reward function directly"
python -c "
import json
from rlvr.reward_function import stock_prediction_reward

# Load first example from dataset
with open('storage/rlvr_datasets/test_reward_kit.jsonl', 'r') as f:
    example = json.loads(f.readline().strip())

# Test the reward function
result = stock_prediction_reward(
    messages=example['messages'],
    ground_truth=example['ground_truth'],
    metadata=example['metadata']
)

print(f'Reward Score: {result.score}')
print(f'Valid: {result.is_score_valid}')
print(f'Reason: {result.reason}')
print('Metrics:')
for name, metric in result.metrics.items():
    print(f'  {name}: {metric.score} - {metric.reason}')
"

echo ""
echo "📋 Step 4: Test reward-kit CLI (if available)"
if command -v reward-kit &> /dev/null; then
    echo "Running reward-kit evaluation..."
    python -m reward_kit.cli run \
        --config-path ./conf \
        --config-name run_eval.yaml \
        --dataset-path storage/rlvr_datasets/test_reward_kit.jsonl \
        --output-dir outputs/evaluations/test_run
    
    echo "✓ reward-kit evaluation completed"
    
    # Show results if available
    if [ -d "outputs/evaluations/test_run" ]; then
        echo "📊 Evaluation results:"
        ls -la outputs/evaluations/test_run/
        
        # Try to show preview if available
        if command -v reward-kit &> /dev/null; then
            echo "📋 Preview of results:"
            reward-kit preview --samples outputs/evaluations/test_run/preview_input_output_pairs.jsonl 2>/dev/null || echo "Preview not available"
        fi
    fi
else
    echo "⚠️  reward-kit CLI not available, skipping CLI test"
    echo "   Install with: pip install reward-kit"
fi

echo ""
echo "🎉 Reward function testing completed!"
echo ""
echo "📁 Generated files:"
echo "  - conf/run_eval.yaml (evaluation config)"
echo "  - storage/rlvr_datasets/test_reward_kit.jsonl (test dataset)"
echo "  - outputs/evaluations/ (evaluation results)"
echo ""
echo "🔧 Next steps:"
echo "  1. Review evaluation results"
echo "  2. Adjust reward function if needed"
echo "  3. Generate larger dataset for training"
echo "  4. Deploy reward function to Fireworks"