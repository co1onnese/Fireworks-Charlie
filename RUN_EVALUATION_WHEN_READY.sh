#!/bin/bash
# 
# Quick Evaluation Runner
# Run this script when your model is deployed!
#

set -e

MODEL_NAME="accounts/lstn/models/rftj-v1in37s4-evv0b"

echo "🔬 Fireworks-Charlie Model Evaluation"
echo "======================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "Step 1: Checking model deployment status..."
echo ""
python scripts/check_model_status.py --model-name "$MODEL_NAME"
echo ""

read -p "Is the model READY for inference? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "⏳ Model not ready yet. You can monitor it with:"
    echo "   python scripts/check_model_status.py --model-name $MODEL_NAME --monitor"
    exit 0
fi

echo ""
echo "Step 2: Running quick test (3 examples)..."
echo ""
python scripts/evaluate_model.py \
    --fine-tuned-model "$MODEL_NAME" \
    --max-examples 3 \
    --strategy A

echo ""
read -p "Quick test successful? Run full evaluation? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Exiting. You can run full evaluation later with:"
    echo "   python scripts/evaluate_model.py --fine-tuned-model $MODEL_NAME --strategy A"
    exit 0
fi

echo ""
echo "Step 3: Running FULL evaluation (402 examples, ~30-45 min)..."
echo ""
python scripts/evaluate_model.py \
    --fine-tuned-model "$MODEL_NAME" \
    --strategy A

echo ""
echo "✅ Evaluation complete!"
echo "📁 Results saved to: outputs/evaluations/"
echo ""
echo "To view results:"
echo "   cat outputs/evaluations/eval_strategy_A_*_summary.txt"
