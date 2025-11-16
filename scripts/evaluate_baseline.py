#!/usr/bin/env python3
"""
Evaluate Base Model Performance (Baseline)

This script evaluates the base DeepSeek-v3 model performance to establish
baseline metrics before fine-tuning. Results serve as comparison point for
evaluating fine-tuned models.

Implements three trading strategies:
- Strategy A: Long-only (BUY signals only, others = 0% return)
- Strategy B: Long/short (BUY = +return, SELL = -return, HOLD = 0%)
- Strategy C: Weighted (STRONG_BUY = 2x, BUY = 1x, SELL = -1x, STRONG_SELL = -2x)

Author: Fireworks-Charlie Team
Date: 2025-11-05
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaselineEvaluator:
    """Evaluate base model performance for baseline metrics."""

    # Action thresholds (from config)
    STRONG_BUY_THRESHOLD = 3.0
    BUY_THRESHOLD = 2.0
    HOLD_THRESHOLD_LOW = -2.0
    HOLD_THRESHOLD_HIGH = 2.0
    SELL_THRESHOLD = -2.0
    STRONG_SELL_THRESHOLD = -3.0

    def __init__(self, model: str):
        """
        Initialize evaluator.

        Args:
            model: Name/ID of the model to evaluate
        """
        from openai import OpenAI

        self.model = model

        # Initialize Fireworks client (OpenAI-compatible)
        self.client = OpenAI(
            api_key=config.FIREWORKS_API_KEY,
            base_url="https://api.fireworks.ai/inference/v1"
        )

        logger.info(f"Baseline Evaluator initialized")
        logger.info(f"  Model: {self.model}")

    def load_evaluation_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Load evaluation dataset from JSONL file."""
        logger.info(f"Loading evaluation dataset from {dataset_path}")

        examples = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    example = json.loads(line)
                    examples.append(example)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON on line {line_num}: {e}")
                    continue

        logger.info(f"Loaded {len(examples)} evaluation examples")
        return examples

    def query_model(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Query model with given messages.

        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature (uses config default if None)
            max_tokens: Maximum tokens to generate

        Returns:
            Response dictionary with content, usage, etc.
        """
        if temperature is None:
            temperature = config.GEN_TEMPERATURE

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Ensure JSON output
            )

            return {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error querying model: {e}")
            return {
                "content": None,
                "error": str(e),
                "finish_reason": "error"
            }

    def parse_prediction(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse model prediction from JSON response."""
        if not response_content:
            return None

        try:
            prediction = json.loads(response_content)

            # Validate required fields
            if 'action' not in prediction:
                logger.warning("Prediction missing 'action' field")
                return None

            return prediction

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse prediction JSON: {e}")
            logger.debug(f"Content: {response_content[:200]}")
            return None

    def calculate_directional_accuracy(
        self,
        predicted_action: str,
        actual_return: float
    ) -> bool:
        """
        Calculate if prediction was directionally correct.

        Args:
            predicted_action: Predicted action (buy, sell, hold, etc.)
            actual_return: Actual return percentage

        Returns:
            True if correct, False otherwise
        """
        action = predicted_action.lower()

        # Action thresholds from config
        if action == "strong_buy":
            return actual_return >= self.STRONG_BUY_THRESHOLD
        elif action == "buy":
            return actual_return >= self.BUY_THRESHOLD
        elif action == "hold":
            return self.HOLD_THRESHOLD_LOW <= actual_return <= self.HOLD_THRESHOLD_HIGH
        elif action == "sell":
            return actual_return <= self.SELL_THRESHOLD
        elif action == "strong_sell":
            return actual_return <= self.STRONG_SELL_THRESHOLD
        else:
            logger.warning(f"Unknown action: {action}")
            return False

    def calculate_portfolio_return_strategy_a(
        self,
        predicted_action: str,
        actual_return: float
    ) -> float:
        """
        Calculate portfolio return for Strategy A (Long-only).

        Strategy A:
        - BUY/STRONG_BUY → portfolio_return = actual_return_pct
        - HOLD/SELL/STRONG_SELL → portfolio_return = 0%

        Args:
            predicted_action: Predicted action
            actual_return: Actual return percentage

        Returns:
            Portfolio return for this prediction
        """
        action = predicted_action.lower()

        if action in ['buy', 'strong_buy']:
            return actual_return
        else:
            return 0.0

    def calculate_portfolio_return_strategy_b(
        self,
        predicted_action: str,
        actual_return: float
    ) -> float:
        """
        Calculate portfolio return for Strategy B (Long/short).

        Strategy B:
        - BUY/STRONG_BUY → Long position → +actual_return
        - HOLD → No position → 0%
        - SELL/STRONG_SELL → Short position → -actual_return

        Args:
            predicted_action: Predicted action
            actual_return: Actual return percentage

        Returns:
            Portfolio return for this prediction
        """
        action = predicted_action.lower()

        if action in ['buy', 'strong_buy']:
            return actual_return
        elif action in ['sell', 'strong_sell']:
            return -actual_return
        else:  # hold
            return 0.0

    def calculate_portfolio_return_strategy_c(
        self,
        predicted_action: str,
        actual_return: float
    ) -> float:
        """
        Calculate portfolio return for Strategy C (Weighted).

        Strategy C:
        - STRONG_BUY → 2x position → 2 × actual_return
        - BUY → 1x position → actual_return
        - HOLD → 0x position → 0%
        - SELL → -1x position → -actual_return
        - STRONG_SELL → -2x position → -2 × actual_return

        Args:
            predicted_action: Predicted action
            actual_return: Actual return percentage

        Returns:
            Portfolio return for this prediction
        """
        action = predicted_action.lower()

        weights = {
            'strong_buy': 2.0,
            'buy': 1.0,
            'hold': 0.0,
            'sell': -1.0,
            'strong_sell': -2.0
        }

        return weights.get(action, 0.0) * actual_return

    def calculate_sharpe_ratio(
        self,
        portfolio_returns: List[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate Sharpe Ratio over the entire test period.

        Sharpe Ratio = (mean_return - risk_free_rate) / std_return

        Note: Not annualized, calculated over actual holding period.

        Args:
            portfolio_returns: List of portfolio returns
            risk_free_rate: Risk-free rate (default 0%)

        Returns:
            Sharpe Ratio
        """
        if not portfolio_returns or len(portfolio_returns) < 2:
            return 0.0

        returns_array = np.array(portfolio_returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array, ddof=1)  # Sample std

        if std_return == 0:
            return 0.0

        sharpe = (mean_return - risk_free_rate) / std_return
        return sharpe

    def evaluate_example(
        self,
        example: Dict[str, Any],
        strategy: str = 'A'
    ) -> Dict[str, Any]:
        """
        Evaluate a single example.

        Args:
            example: Evaluation example with messages, ground_truth, metadata
            strategy: Trading strategy ('A', 'B', or 'C')

        Returns:
            Evaluation result dictionary
        """
        # Extract messages (remove assistant message for fresh prediction)
        messages = [m for m in example['messages'] if m['role'] != 'assistant']

        ground_truth = example['ground_truth']
        metadata = example['metadata']

        # Query the model
        response = self.query_model(messages)

        if response.get('error'):
            return {
                "ticker": metadata.get('ticker'),
                "entry_date": metadata.get('entry_date'),
                "error": response['error'],
                "correct": False,
                "actual_return": ground_truth.get('actual_return_pct'),
                "portfolio_return": 0.0,
                "days_held": ground_truth.get('days_held')
            }

        # Parse prediction
        prediction = self.parse_prediction(response['content'])

        if not prediction:
            return {
                "ticker": metadata.get('ticker'),
                "entry_date": metadata.get('entry_date'),
                "error": "Failed to parse prediction",
                "correct": False,
                "actual_return": ground_truth.get('actual_return_pct'),
                "portfolio_return": 0.0,
                "days_held": ground_truth.get('days_held')
            }

        # Extract data
        predicted_action = prediction.get('action', '').lower()
        actual_return = ground_truth.get('actual_return_pct', 0.0)

        # Calculate directional accuracy
        correct = self.calculate_directional_accuracy(predicted_action, actual_return)

        # Calculate portfolio return based on strategy
        if strategy == 'A':
            portfolio_return = self.calculate_portfolio_return_strategy_a(
                predicted_action, actual_return
            )
        elif strategy == 'B':
            portfolio_return = self.calculate_portfolio_return_strategy_b(
                predicted_action, actual_return
            )
        elif strategy == 'C':
            portfolio_return = self.calculate_portfolio_return_strategy_c(
                predicted_action, actual_return
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        return {
            "ticker": metadata.get('ticker'),
            "entry_date": metadata.get('entry_date'),
            "predicted_action": predicted_action,
            "actual_return": actual_return,
            "portfolio_return": portfolio_return,
            "correct": correct,
            "reasoning": prediction.get('reasoning', ''),
            "support": prediction.get('support', ''),
            "usage": response.get('usage', {}),
            "ground_truth": ground_truth,
            "days_held": ground_truth.get('days_held')
        }

    def evaluate_dataset(
        self,
        dataset_path: str,
        max_examples: Optional[int] = None,
        strategy: str = 'A'
    ) -> Dict[str, Any]:
        """
        Evaluate entire dataset.

        Args:
            dataset_path: Path to evaluation JSONL file
            max_examples: Maximum examples to evaluate (None = all)
            strategy: Trading strategy ('A', 'B', or 'C')

        Returns:
            Evaluation results dictionary
        """
        logger.info(f"Evaluating {self.model} on {dataset_path}")
        logger.info(f"Using Strategy {strategy}")

        # Load dataset
        examples = self.load_evaluation_dataset(dataset_path)

        if max_examples:
            examples = examples[:max_examples]
            logger.info(f"Limited to {max_examples} examples")

        # Evaluate each example
        results = []
        correct_count = 0
        error_count = 0
        portfolio_returns = []
        actual_returns = []

        for i, example in enumerate(examples, 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(examples)} examples evaluated")

            result = self.evaluate_example(example, strategy)
            results.append(result)

            if result.get('error'):
                error_count += 1
            else:
                if result.get('correct'):
                    correct_count += 1

                portfolio_returns.append(result['portfolio_return'])
                actual_returns.append(result['actual_return'])

        # Calculate metrics
        total_evaluated = len(results) - error_count
        accuracy = correct_count / total_evaluated if total_evaluated > 0 else 0.0

        # Calculate by action type
        action_stats = self._calculate_action_statistics(results)

        # Calculate return statistics
        return_stats = self._calculate_return_statistics(portfolio_returns, actual_returns)

        # Calculate Sharpe Ratio
        sharpe_ratio = self.calculate_sharpe_ratio(portfolio_returns)

        # Calculate buy-and-hold benchmark
        buy_hold_return = np.mean(actual_returns) if actual_returns else 0.0
        buy_hold_std = np.std(actual_returns, ddof=1) if len(actual_returns) > 1 else 0.0
        buy_hold_sharpe = buy_hold_return / buy_hold_std if buy_hold_std > 0 else 0.0

        return {
            "model": self.model,
            "dataset": dataset_path,
            "strategy": strategy,
            "total_examples": len(examples),
            "evaluated": total_evaluated,
            "errors": error_count,
            "correct": correct_count,
            "incorrect": total_evaluated - correct_count,
            "accuracy": accuracy,
            "action_statistics": action_stats,
            "return_statistics": return_stats,
            "sharpe_ratio": sharpe_ratio,
            "buy_and_hold_benchmark": {
                "mean_return": buy_hold_return,
                "std_return": buy_hold_std,
                "sharpe_ratio": buy_hold_sharpe
            },
            "results": results
        }

    def _calculate_action_statistics(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics by action type."""
        action_counts = {}
        action_correct = {}
        action_returns = {}

        for result in results:
            if result.get('error'):
                continue

            action = result.get('predicted_action', 'unknown')
            action_counts[action] = action_counts.get(action, 0) + 1

            if result.get('correct'):
                action_correct[action] = action_correct.get(action, 0) + 1

            # Track returns per action
            if action not in action_returns:
                action_returns[action] = []
            action_returns[action].append(result.get('portfolio_return', 0.0))

        # Calculate accuracy and return stats per action
        action_accuracy = {}
        for action, count in action_counts.items():
            correct = action_correct.get(action, 0)
            returns = action_returns.get(action, [])

            action_accuracy[action] = {
                "count": count,
                "correct": correct,
                "accuracy": correct / count if count > 0 else 0.0,
                "mean_portfolio_return": np.mean(returns) if returns else 0.0,
                "std_portfolio_return": np.std(returns, ddof=1) if len(returns) > 1 else 0.0
            }

        return action_accuracy

    def _calculate_return_statistics(
        self,
        portfolio_returns: List[float],
        actual_returns: List[float]
    ) -> Dict[str, Any]:
        """Calculate return statistics."""
        if not portfolio_returns:
            return {}

        portfolio_array = np.array(portfolio_returns)
        actual_array = np.array(actual_returns)

        return {
            "portfolio": {
                "mean": np.mean(portfolio_array),
                "median": np.median(portfolio_array),
                "std": np.std(portfolio_array, ddof=1),
                "min": np.min(portfolio_array),
                "max": np.max(portfolio_array),
                "total_return": np.sum(portfolio_array),
                "positive_count": np.sum(portfolio_array > 0),
                "negative_count": np.sum(portfolio_array < 0),
                "neutral_count": np.sum(portfolio_array == 0)
            },
            "actual": {
                "mean": np.mean(actual_array),
                "median": np.median(actual_array),
                "std": np.std(actual_array, ddof=1),
                "min": np.min(actual_array),
                "max": np.max(actual_array),
                "positive_count": np.sum(actual_array > 0),
                "negative_count": np.sum(actual_array < 0),
                "neutral_count": np.sum(actual_array == 0)
            }
        }

    def save_results(
        self,
        results: Dict[str, Any],
        output_dir: str = "outputs/baseline_evaluations"
    ) -> str:
        """
        Save evaluation results to file.

        Args:
            results: Evaluation results dictionary
            output_dir: Output directory

        Returns:
            Path to saved file
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        strategy = results.get('strategy', 'A')
        filename = f"baseline_strategy_{strategy}_{timestamp}.json"
        filepath = Path(output_dir) / filename

        # Custom JSON encoder to handle numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (np.integer, np.int64, np.int32)):
                    return int(obj)
                elif isinstance(obj, (np.floating, np.float64, np.float32)):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

        logger.info(f"✓ Results saved to {filepath}")

        # Also save a human-readable summary
        summary_path = Path(output_dir) / f"baseline_strategy_{strategy}_{timestamp}_summary.txt"
        self._save_summary(results, summary_path)

        return str(filepath)

    def _save_summary(self, results: Dict[str, Any], filepath: Path):
        """Save human-readable summary."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("BASELINE MODEL EVALUATION SUMMARY\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Evaluated at: {datetime.now().isoformat()}\n")
            f.write(f"Model: {results['model']}\n")
            f.write(f"Strategy: {results.get('strategy', 'A')}\n")
            f.write(f"Dataset: {results['dataset']}\n\n")

            # Overall results
            f.write("OVERALL PERFORMANCE\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total Examples: {results['total_examples']}\n")
            f.write(f"Successfully Evaluated: {results['evaluated']}\n")
            f.write(f"Errors: {results['errors']}\n")
            f.write(f"Accuracy: {results['accuracy']:.2%}\n")
            f.write(f"Correct: {results['correct']}/{results['evaluated']}\n")
            f.write(f"Incorrect: {results['incorrect']}\n\n")

            # Portfolio performance
            f.write(f"PORTFOLIO PERFORMANCE\n")
            f.write("-" * 70 + "\n")
            f.write(f"Mean Return: {results['return_statistics']['portfolio']['mean']:.4f}%\n")
            f.write(f"Median Return: {results['return_statistics']['portfolio']['median']:.4f}%\n")
            f.write(f"Std Dev: {results['return_statistics']['portfolio']['std']:.4f}%\n")
            f.write(f"Min Return: {results['return_statistics']['portfolio']['min']:.4f}%\n")
            f.write(f"Max Return: {results['return_statistics']['portfolio']['max']:.4f}%\n")
            f.write(f"Total Cumulative Return: {results['return_statistics']['portfolio']['total_return']:.4f}%\n")
            f.write(f"Sharpe Ratio: {results['sharpe_ratio']:.4f}\n\n")

            # Position breakdown
            port = results['return_statistics']['portfolio']
            f.write(f"Position Distribution:\n")
            f.write(f"  Positive Returns: {port['positive_count']} ({port['positive_count']/results['evaluated']*100:.1f}%)\n")
            f.write(f"  Negative Returns: {port['negative_count']} ({port['negative_count']/results['evaluated']*100:.1f}%)\n")
            f.write(f"  Neutral (0%) Returns: {port['neutral_count']} ({port['neutral_count']/results['evaluated']*100:.1f}%)\n\n")

            # Action breakdown
            f.write("ACTION STATISTICS\n")
            f.write("-" * 70 + "\n")
            for action, stats in results.get('action_statistics', {}).items():
                f.write(f"{action.upper()}:\n")
                f.write(f"  Count: {stats['count']}\n")
                f.write(f"  Accuracy: {stats['accuracy']:.2%}\n")
                f.write(f"  Correct: {stats['correct']}/{stats['count']}\n")
                f.write(f"  Mean Portfolio Return: {stats['mean_portfolio_return']:.4f}%\n")
                f.write(f"  Std Portfolio Return: {stats['std_portfolio_return']:.4f}%\n")
                f.write("\n")

            # Buy-and-hold benchmark
            benchmark = results['buy_and_hold_benchmark']
            f.write("BUY-AND-HOLD BENCHMARK\n")
            f.write("-" * 70 + "\n")
            f.write(f"Mean Return: {benchmark['mean_return']:.4f}%\n")
            f.write(f"Std Dev: {benchmark['std_return']:.4f}%\n")
            f.write(f"Sharpe Ratio: {benchmark['sharpe_ratio']:.4f}\n\n")

            # Comparison to benchmark
            f.write("COMPARISON TO BENCHMARK\n")
            f.write("-" * 70 + "\n")
            mean_diff = results['return_statistics']['portfolio']['mean'] - benchmark['mean_return']
            sharpe_diff = results['sharpe_ratio'] - benchmark['sharpe_ratio']

            f.write(f"Mean Return Difference: {mean_diff:+.4f}%\n")
            f.write(f"Sharpe Ratio Difference: {sharpe_diff:+.4f}\n")

            if mean_diff > 0:
                f.write("✓ Model outperforms buy-and-hold on mean return\n")
            else:
                f.write("✗ Model underperforms buy-and-hold on mean return\n")

            if sharpe_diff > 0:
                f.write("✓ Model has better risk-adjusted returns\n")
            else:
                f.write("✗ Model has worse risk-adjusted returns\n")

            f.write("\n" + "=" * 70 + "\n")

        logger.info(f"✓ Summary saved to {filepath}")


def main():
    """Main baseline evaluation function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate base model performance (baseline metrics)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Trading Strategies:
  A - Long-only: BUY signals take position, others = 0% return
  B - Long/short: BUY = long, SELL = short, HOLD = 0%
  C - Weighted: STRONG_BUY = 2x, BUY = 1x, SELL = -1x, STRONG_SELL = -2x

Examples:
  # Evaluate with default settings (Strategy A, full dev set)
  python scripts/evaluate_baseline.py --model accounts/fireworks/models/deepseek-v3p1-terminus

  # Evaluate specific strategy with limited examples
  python scripts/evaluate_baseline.py \\
    --model accounts/fireworks/models/deepseek-v3p1-terminus \\
    --strategy B \\
    --max-examples 50

  # Evaluate all strategies
  python scripts/evaluate_baseline.py \\
    --model accounts/fireworks/models/deepseek-v3p1-terminus \\
    --all-strategies
        """
    )

    parser.add_argument(
        '--model',
        required=True,
        help='Model name/ID to evaluate (e.g., accounts/fireworks/models/deepseek-v3p1-terminus)'
    )
    parser.add_argument(
        '--dataset',
        default=None,
        help='Path to evaluation dataset (defaults to dev.jsonl)'
    )
    parser.add_argument(
        '--max-examples',
        type=int,
        default=None,
        help='Maximum number of examples to evaluate (None = all)'
    )
    parser.add_argument(
        '--strategy',
        choices=['A', 'B', 'C'],
        default='A',
        help='Trading strategy to evaluate (default: A - Long-only)'
    )
    parser.add_argument(
        '--all-strategies',
        action='store_true',
        help='Evaluate all three strategies (A, B, C)'
    )
    parser.add_argument(
        '--output-dir',
        default='outputs/baseline_evaluations',
        help='Output directory for results'
    )

    args = parser.parse_args()

    # Determine dataset path
    dataset_path = args.dataset or config.RLVR_DEV_FILE

    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {dataset_path}")
        sys.exit(1)

    # Determine which strategies to run
    if args.all_strategies:
        strategies = ['A', 'B', 'C']
    else:
        strategies = [args.strategy]

    print("=" * 70)
    print("📊 BASELINE MODEL EVALUATION")
    print("=" * 70)
    print(f"Model: {args.model}")
    print(f"Dataset: {dataset_path}")
    print(f"Strategies: {', '.join(strategies)}")
    print(f"Max examples: {args.max_examples or 'All'}")
    print("=" * 70)
    print()

    try:
        # Initialize evaluator
        evaluator = BaselineEvaluator(args.model)

        # Store results for all strategies
        all_results = {}

        # Run evaluation for each strategy
        for strategy in strategies:
            print(f"\n{'='*70}")
            print(f"🔄 EVALUATING STRATEGY {strategy}")
            print(f"{'='*70}\n")

            results = evaluator.evaluate_dataset(
                dataset_path,
                args.max_examples,
                strategy
            )

            # Save results
            output_file = evaluator.save_results(results, args.output_dir)

            # Store for comparison
            all_results[strategy] = results

            # Print summary
            print(f"\n{'='*70}")
            print(f"✅ STRATEGY {strategy} COMPLETE")
            print(f"{'='*70}")
            print(f"\n📈 ACCURACY: {results['accuracy']:.2%}")
            print(f"   Correct: {results['correct']}/{results['evaluated']}")

            print(f"\n💰 MEAN RETURN: {results['return_statistics']['portfolio']['mean']:.4f}%")
            print(f"   Total Return: {results['return_statistics']['portfolio']['total_return']:.4f}%")

            print(f"\n📊 SHARPE RATIO: {results['sharpe_ratio']:.4f}")

            benchmark = results['buy_and_hold_benchmark']
            print(f"\n🎯 BENCHMARK:")
            print(f"   Mean Return: {benchmark['mean_return']:.4f}%")
            print(f"   Sharpe Ratio: {benchmark['sharpe_ratio']:.4f}")

            print(f"\n💾 Results saved to: {output_file}")

        # If multiple strategies, create comparison report
        if len(strategies) > 1:
            print(f"\n{'='*70}")
            print("📊 GENERATING STRATEGY COMPARISON REPORT")
            print(f"{'='*70}\n")

            comparison_path = Path(args.output_dir) / f"baseline_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            _save_comparison_report(all_results, comparison_path, args.model)

            print(f"✓ Comparison report saved to: {comparison_path}")

        print(f"\n{'='*70}")
        print("✅ BASELINE EVALUATION COMPLETE")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def _save_comparison_report(all_results: Dict[str, Dict], filepath: Path, model: str):
    """Save comparison report across all strategies."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("BASELINE MODEL STRATEGY COMPARISON REPORT\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Model: {model}\n")
        f.write(f"Evaluated at: {datetime.now().isoformat()}\n")
        f.write(f"Strategies Compared: {', '.join(all_results.keys())}\n\n")

        # Summary table
        f.write("SUMMARY COMPARISON\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'Strategy':<12} {'Accuracy':<12} {'Mean Return':<15} {'Sharpe Ratio':<12}\n")
        f.write("-" * 70 + "\n")

        for strategy, results in all_results.items():
            accuracy = results['accuracy']
            mean_return = results['return_statistics']['portfolio']['mean']
            sharpe = results['sharpe_ratio']
            f.write(f"{strategy:<12} {accuracy:>10.2%} {mean_return:>13.4f}% {sharpe:>11.4f}\n")

        f.write("-" * 70 + "\n\n")

        # Detailed comparison
        for strategy, results in all_results.items():
            f.write(f"\nSTRATEGY {strategy} - DETAILED RESULTS\n")
            f.write("-" * 70 + "\n")

            f.write(f"Accuracy: {results['accuracy']:.2%} ({results['correct']}/{results['evaluated']})\n")
            f.write(f"Mean Return: {results['return_statistics']['portfolio']['mean']:.4f}%\n")
            f.write(f"Total Return: {results['return_statistics']['portfolio']['total_return']:.4f}%\n")
            f.write(f"Std Dev: {results['return_statistics']['portfolio']['std']:.4f}%\n")
            f.write(f"Sharpe Ratio: {results['sharpe_ratio']:.4f}\n")
            f.write(f"Errors: {results['errors']}\n\n")

            # Action distribution
            f.write("Action Distribution:\n")
            for action, stats in results['action_statistics'].items():
                f.write(f"  {action}: {stats['count']} ({stats['accuracy']:.1%} accuracy)\n")

            f.write("\n")

        # Recommendations
        f.write("\nRECOMMENDATIONS\n")
        f.write("-" * 70 + "\n")

        # Find best strategy by different metrics
        best_accuracy = max(all_results.items(), key=lambda x: x[1]['accuracy'])
        best_return = max(all_results.items(), key=lambda x: x[1]['return_statistics']['portfolio']['mean'])
        best_sharpe = max(all_results.items(), key=lambda x: x[1]['sharpe_ratio'])

        f.write(f"Best Accuracy: Strategy {best_accuracy[0]} ({best_accuracy[1]['accuracy']:.2%})\n")
        f.write(f"Best Mean Return: Strategy {best_return[0]} ({best_return[1]['return_statistics']['portfolio']['mean']:.4f}%)\n")
        f.write(f"Best Sharpe Ratio: Strategy {best_sharpe[0]} ({best_sharpe[1]['sharpe_ratio']:.4f})\n\n")

        f.write("=" * 70 + "\n")

    logger.info(f"✓ Comparison report saved to {filepath}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
