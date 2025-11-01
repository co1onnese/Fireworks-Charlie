#!/usr/bin/env python3
"""
Evaluate Fine-tuned Model Performance

This script evaluates the fine-tuned GRPO model against the base model
on the evaluation dataset and documents the results.

Implements three trading strategies:
- Strategy A: Long-only (BUY signals only, others = 0% return)
- Strategy B: Long/short (BUY = +return, SELL = -return, HOLD = 0%)
- Strategy C: Weighted (STRONG_BUY = 2x, BUY = 1x, SELL = -1x, STRONG_SELL = -2x)

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
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


class ModelEvaluator:
    """Evaluate and compare model performance."""
    
    # Action thresholds (from config)
    STRONG_BUY_THRESHOLD = 3.0
    BUY_THRESHOLD = 2.0
    HOLD_THRESHOLD_LOW = -2.0
    HOLD_THRESHOLD_HIGH = 2.0
    SELL_THRESHOLD = -2.0
    STRONG_SELL_THRESHOLD = -3.0
    
    def __init__(self, fine_tuned_model: str, base_model: str = None):
        """
        Initialize evaluator.
        
        Args:
            fine_tuned_model: Name/ID of the fine-tuned model
            base_model: Name of the base model (defaults to config)
        """
        from openai import OpenAI
        
        self.fine_tuned_model = fine_tuned_model
        self.base_model = base_model or config.MODEL_NAME
        
        # Initialize Fireworks client (OpenAI-compatible)
        self.client = OpenAI(
            api_key=config.FIREWORKS_API_KEY,
            base_url="https://api.fireworks.ai/inference/v1"
        )
        
        logger.info(f"Evaluator initialized")
        logger.info(f"  Fine-tuned model: {self.fine_tuned_model}")
        logger.info(f"  Base model: {self.base_model}")
    
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
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Query a model with given messages.
        
        Args:
            model: Model name/ID
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
                model=model,
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
            logger.error(f"Error querying model {model}: {e}")
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
        - BUY/STRONG_BUY ? portfolio_return = actual_return_pct
        - HOLD/SELL/STRONG_SELL ? portfolio_return = 0%
        
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
        - BUY/STRONG_BUY ? Long position ? +actual_return
        - HOLD ? No position ? 0%
        - SELL/STRONG_SELL ? Short position ? -actual_return
        
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
        - STRONG_BUY ? 2x position ? 2 ? actual_return
        - BUY ? 1x position ? actual_return
        - HOLD ? 0x position ? 0%
        - SELL ? -1x position ? -actual_return
        - STRONG_SELL ? -2x position ? -2 ? actual_return
        
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
        model: str,
        strategy: str = 'A'
    ) -> Dict[str, Any]:
        """
        Evaluate a single example.
        
        Args:
            example: Evaluation example with messages, ground_truth, metadata
            model: Model to evaluate
            strategy: Trading strategy ('A', 'B', or 'C')
            
        Returns:
            Evaluation result dictionary
        """
        # Extract messages (remove assistant message for fresh prediction)
        messages = [m for m in example['messages'] if m['role'] != 'assistant']
        
        ground_truth = example['ground_truth']
        metadata = example['metadata']
        
        # Query the model
        response = self.query_model(model, messages)
        
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
        model: str,
        max_examples: Optional[int] = None,
        strategy: str = 'A'
    ) -> Dict[str, Any]:
        """
        Evaluate entire dataset.
        
        Args:
            dataset_path: Path to evaluation JSONL file
            model: Model to evaluate
            max_examples: Maximum examples to evaluate (None = all)
            strategy: Trading strategy ('A', 'B', or 'C')
            
        Returns:
            Evaluation results dictionary
        """
        logger.info(f"Evaluating {model} on {dataset_path}")
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
            
            result = self.evaluate_example(example, model, strategy)
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
            "model": model,
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
    
    def compare_models(
        self,
        dataset_path: str,
        max_examples: Optional[int] = None,
        strategy: str = 'A'
    ) -> Dict[str, Any]:
        """
        Compare fine-tuned model vs base model.
        
        Args:
            dataset_path: Path to evaluation dataset
            max_examples: Maximum examples to evaluate
            strategy: Trading strategy ('A', 'B', or 'C')
            
        Returns:
            Comparison results dictionary
        """
        logger.info("=" * 70)
        logger.info(f"STARTING MODEL COMPARISON - STRATEGY {strategy}")
        logger.info("=" * 70)
        
        # Evaluate base model
        logger.info("\n?? Evaluating BASE MODEL...")
        base_results = self.evaluate_dataset(
            dataset_path, self.base_model, max_examples, strategy
        )
        
        # Evaluate fine-tuned model
        logger.info("\n?? Evaluating FINE-TUNED MODEL...")
        finetuned_results = self.evaluate_dataset(
            dataset_path, self.fine_tuned_model, max_examples, strategy
        )
        
        # Calculate improvements (handle missing data gracefully)
        accuracy_improvement = (
            finetuned_results['accuracy'] - base_results['accuracy']
        ) * 100
        
        sharpe_improvement = (
            finetuned_results.get('sharpe_ratio', 0) - base_results.get('sharpe_ratio', 0)
        )
        
        base_mean = base_results.get('return_statistics', {}).get('portfolio', {}).get('mean', 0.0)
        ft_mean = finetuned_results.get('return_statistics', {}).get('portfolio', {}).get('mean', 0.0)
        return_improvement = ft_mean - base_mean
        
        logger.info("\n" + "=" * 70)
        logger.info("EVALUATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"\n?? ACCURACY")
        logger.info(f"  Base Model: {base_results['accuracy']:.2%}")
        logger.info(f"  Fine-tuned Model: {finetuned_results['accuracy']:.2%}")
        logger.info(f"  Improvement: {accuracy_improvement:+.2f} percentage points")
        
        logger.info(f"\n?? RETURNS (Strategy {strategy})")
        logger.info(f"  Base Model: {base_results['return_statistics']['portfolio']['mean']:.4f}%")
        logger.info(f"  Fine-tuned Model: {finetuned_results['return_statistics']['portfolio']['mean']:.4f}%")
        logger.info(f"  Improvement: {return_improvement:+.4f}%")
        
        logger.info(f"\n?? SHARPE RATIO")
        logger.info(f"  Base Model: {base_results['sharpe_ratio']:.4f}")
        logger.info(f"  Fine-tuned Model: {finetuned_results['sharpe_ratio']:.4f}")
        logger.info(f"  Improvement: {sharpe_improvement:+.4f}")
        
        logger.info(f"\n?? BUY-AND-HOLD BENCHMARK")
        logger.info(f"  Mean Return: {base_results['buy_and_hold_benchmark']['mean_return']:.4f}%")
        logger.info(f"  Sharpe Ratio: {base_results['buy_and_hold_benchmark']['sharpe_ratio']:.4f}")
        
        return {
            "base_model": base_results,
            "fine_tuned_model": finetuned_results,
            "comparison": {
                "accuracy_improvement": accuracy_improvement,
                "return_improvement": return_improvement,
                "sharpe_improvement": sharpe_improvement,
                "base_accuracy": base_results['accuracy'],
                "finetuned_accuracy": finetuned_results['accuracy'],
                "base_sharpe": base_results['sharpe_ratio'],
                "finetuned_sharpe": finetuned_results['sharpe_ratio'],
                "base_mean_return": base_results['return_statistics']['portfolio']['mean'],
                "finetuned_mean_return": finetuned_results['return_statistics']['portfolio']['mean']
            },
            "strategy": strategy,
            "evaluated_at": datetime.now().isoformat()
        }
    
    def save_results(
        self,
        results: Dict[str, Any],
        output_dir: str = "outputs/evaluations"
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
        filename = f"eval_strategy_{strategy}_{timestamp}.json"
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
        
        logger.info(f"? Results saved to {filepath}")
        
        # Also save a human-readable summary
        summary_path = Path(output_dir) / f"eval_strategy_{strategy}_{timestamp}_summary.txt"
        self._save_summary(results, summary_path)
        
        return str(filepath)
    
    def _save_summary(self, results: Dict[str, Any], filepath: Path):
        """Save human-readable summary."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("MODEL EVALUATION SUMMARY\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Evaluated at: {results['evaluated_at']}\n")
            f.write(f"Strategy: {results.get('strategy', 'A')}\n\n")
            
            # Base model results
            base = results['base_model']
            f.write("BASE MODEL RESULTS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Model: {base['model']}\n")
            f.write(f"Accuracy: {base['accuracy']:.2%}\n")
            f.write(f"Correct: {base['correct']}/{base['evaluated']}\n")
            f.write(f"Errors: {base['errors']}\n\n")
            
            f.write(f"Portfolio Performance:\n")
            f.write(f"  Mean Return: {base['return_statistics']['portfolio']['mean']:.4f}%\n")
            f.write(f"  Std Dev: {base['return_statistics']['portfolio']['std']:.4f}%\n")
            f.write(f"  Sharpe Ratio: {base['sharpe_ratio']:.4f}\n")
            f.write(f"  Total Return: {base['return_statistics']['portfolio']['total_return']:.4f}%\n\n")
            
            # Action breakdown for base
            f.write("Action Statistics:\n")
            for action, stats in base.get('action_statistics', {}).items():
                f.write(f"  {action}:\n")
                f.write(f"    Count: {stats['count']}\n")
                f.write(f"    Accuracy: {stats['accuracy']:.2%}\n")
                f.write(f"    Mean Portfolio Return: {stats['mean_portfolio_return']:.4f}%\n")
            f.write("\n")
            
            # Fine-tuned model results
            ft = results['fine_tuned_model']
            f.write("FINE-TUNED MODEL RESULTS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Model: {ft['model']}\n")
            f.write(f"Accuracy: {ft['accuracy']:.2%}\n")
            f.write(f"Correct: {ft['correct']}/{ft['evaluated']}\n")
            f.write(f"Errors: {ft['errors']}\n\n")
            
            f.write(f"Portfolio Performance:\n")
            f.write(f"  Mean Return: {ft['return_statistics']['portfolio']['mean']:.4f}%\n")
            f.write(f"  Std Dev: {ft['return_statistics']['portfolio']['std']:.4f}%\n")
            f.write(f"  Sharpe Ratio: {ft['sharpe_ratio']:.4f}\n")
            f.write(f"  Total Return: {ft['return_statistics']['portfolio']['total_return']:.4f}%\n\n")
            
            # Action breakdown for fine-tuned
            f.write("Action Statistics:\n")
            for action, stats in ft.get('action_statistics', {}).items():
                f.write(f"  {action}:\n")
                f.write(f"    Count: {stats['count']}\n")
                f.write(f"    Accuracy: {stats['accuracy']:.2%}\n")
                f.write(f"    Mean Portfolio Return: {stats['mean_portfolio_return']:.4f}%\n")
            f.write("\n")
            
            # Comparison
            comp = results['comparison']
            f.write("COMPARISON\n")
            f.write("-" * 70 + "\n")
            f.write(f"Accuracy Improvement: {comp['accuracy_improvement']:+.2f} percentage points\n")
            f.write(f"Mean Return Improvement: {comp['return_improvement']:+.4f}%\n")
            f.write(f"Sharpe Ratio Improvement: {comp['sharpe_improvement']:+.4f}\n\n")
            
            # Buy-and-hold benchmark
            benchmark = base['buy_and_hold_benchmark']
            f.write("BUY-AND-HOLD BENCHMARK\n")
            f.write("-" * 70 + "\n")
            f.write(f"Mean Return: {benchmark['mean_return']:.4f}%\n")
            f.write(f"Std Dev: {benchmark['std_return']:.4f}%\n")
            f.write(f"Sharpe Ratio: {benchmark['sharpe_ratio']:.4f}\n\n")
            
            # Overall assessment
            f.write("OVERALL ASSESSMENT\n")
            f.write("-" * 70 + "\n")
            
            if comp['accuracy_improvement'] > 0:
                f.write("? Fine-tuned model has BETTER accuracy\n")
            else:
                f.write("? Fine-tuned model has WORSE accuracy\n")
            
            if comp['sharpe_improvement'] > 0:
                f.write("? Fine-tuned model has BETTER risk-adjusted returns\n")
            else:
                f.write("? Fine-tuned model has WORSE risk-adjusted returns\n")
            
            if comp['return_improvement'] > 0:
                f.write("? Fine-tuned model has HIGHER mean returns\n")
            else:
                f.write("? Fine-tuned model has LOWER mean returns\n")
            
            f.write("\n" + "=" * 70 + "\n")
        
        logger.info(f"? Summary saved to {filepath}")


def main():
    """Main evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned model performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Trading Strategies:
  A - Long-only: BUY signals take position, others = 0% return
  B - Long/short: BUY = long, SELL = short, HOLD = 0% (NOT YET IMPLEMENTED)
  C - Weighted: STRONG_BUY = 2x, BUY = 1x, SELL = -1x, STRONG_SELL = -2x (NOT YET IMPLEMENTED)

Examples:
  # Evaluate with default settings (Strategy A, full dev set)
  python scripts/evaluate_model.py --fine-tuned-model accounts/lstn/models/rftj-v1in37s4-evv0b
  
  # Evaluate with custom base model and limited examples
  python scripts/evaluate_model.py \\
    --fine-tuned-model accounts/lstn/models/rftj-v1in37s4-evv0b \\
    --base-model accounts/fireworks/models/llama-v3p1-70b-instruct \\
    --max-examples 50
        """
    )
    
    parser.add_argument(
        '--fine-tuned-model',
        required=True,
        help='Fine-tuned model name/ID (e.g., accounts/lstn/models/rftj-v1in37s4-evv0b)'
    )
    parser.add_argument(
        '--base-model',
        default=None,
        help='Base model name (defaults to config.MODEL_NAME)'
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
        '--output-dir',
        default='outputs/evaluations',
        help='Output directory for results'
    )
    
    args = parser.parse_args()
    
    
    # Determine dataset path
    dataset_path = args.dataset or config.RLVR_DEV_FILE
    
    if not Path(dataset_path).exists():
        logger.error(f"Dataset not found: {dataset_path}")
        sys.exit(1)
    
    print("?? Model Evaluation")
    print("=" * 70)
    print(f"Fine-tuned model: {args.fine_tuned_model}")
    print(f"Base model: {args.base_model or config.MODEL_NAME}")
    print(f"Dataset: {dataset_path}")
    print(f"Strategy: {args.strategy}")
    print(f"Max examples: {args.max_examples or 'All'}")
    print("=" * 70)
    print()
    
    try:
        # Initialize evaluator
        evaluator = ModelEvaluator(args.fine_tuned_model, args.base_model)
        
        # Run comparison
        results = evaluator.compare_models(
            dataset_path,
            args.max_examples,
            args.strategy
        )
        
        # Save results
        output_file = evaluator.save_results(results, args.output_dir)
        
        print("\n" + "=" * 70)
        print("?? FINAL RESULTS")
        print("=" * 70)
        print(f"\n? ACCURACY")
        print(f"  Base Model: {results['comparison']['base_accuracy']:.2%}")
        print(f"  Fine-tuned Model: {results['comparison']['finetuned_accuracy']:.2%}")
        print(f"  Improvement: {results['comparison']['accuracy_improvement']:+.2f} pp")
        
        print(f"\n?? MEAN RETURNS (Strategy {args.strategy})")
        print(f"  Base Model: {results['comparison']['base_mean_return']:.4f}%")
        print(f"  Fine-tuned Model: {results['comparison']['finetuned_mean_return']:.4f}%")
        print(f"  Improvement: {results['comparison']['return_improvement']:+.4f}%")
        
        print(f"\n?? SHARPE RATIO")
        print(f"  Base Model: {results['comparison']['base_sharpe']:.4f}")
        print(f"  Fine-tuned Model: {results['comparison']['finetuned_sharpe']:.4f}")
        print(f"  Improvement: {results['comparison']['sharpe_improvement']:+.4f}")
        
        benchmark = results['base_model']['buy_and_hold_benchmark']
        print(f"\n?? BUY-AND-HOLD BENCHMARK")
        print(f"  Mean Return: {benchmark['mean_return']:.4f}%")
        print(f"  Sharpe Ratio: {benchmark['sharpe_ratio']:.4f}")
        
        print(f"\n?? Results saved to: {output_file}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
