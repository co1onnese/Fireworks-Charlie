#!/usr/bin/env python3
"""
RLVR Main CLI Entry Point

This script provides a command-line interface for RLVR operations including
dataset generation, reward function testing, deployment, and training.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.database_manager import DatabaseManager
from rlvr.dataset_generator import RLVRDatasetGenerator
from rlvr.reward_function import stock_prediction_reward
from rlvr.json_formatter import create_sample_training_examples, create_sample_dev_examples

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_datasets(args):
    """Generate RLVR training datasets."""
    print("📊 Generating RLVR Datasets")
    print("-" * 40)
    
    try:
        # Initialize database connection
        db_manager = DatabaseManager(config.DB_URL)
        session = db_manager.get_session()
        
        try:
            # Initialize dataset generator
            generator = RLVRDatasetGenerator(session)
            
            # Generate datasets
            result = generator.generate_rlvr_datasets(
                tickers=args.tickers.split(',') if args.tickers else None,
                start_date=args.start_date,
                end_date=args.end_date,
                train_split_date=args.train_split_date,
                output_dir=args.output_dir
            )
            
            print(f"✓ Datasets generated successfully!")
            print(f"  Training file: {result['train_file']}")
            print(f"  Dev file: {result['dev_file']}")
            print(f"  Total theses: {result['stats']['total_theses']}")
            print(f"  Valid examples: {result['stats']['valid_examples']}")
            print(f"  Training examples: {result['stats']['training_examples']}")
            print(f"  Dev examples: {result['stats']['dev_examples']}")
            print(f"  Skipped (insufficient data): {result['stats']['skipped_insufficient_data']}")
            print(f"  Skipped (errors): {result['stats']['skipped_errors']}")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to generate datasets: {str(e)}")
        return False
    
    return True


def test_reward_function(args):
    """Test the reward function locally."""
    print("🧪 Testing Reward Function Locally")
    print("-" * 40)
    
    try:
        # Create test examples
        if args.sample:
            print("Using sample data...")
            
            # Test with sample data
            test_messages = [
                {
                    "role": "system",
                    "content": "You are a financial analyst."
                },
                {
                    "role": "user",
                    "content": "Analyze AAPL stock."
                },
                {
                    "role": "assistant",
                    "content": '{"reasoning": "Strong fundamentals", "action": "buy", "support": "Revenue growth"}'
                }
            ]
            
            test_ground_truth = {
                "actual_return_pct": 2.5,
                "exit_date": "2024-01-05",
                "days_held": 3,
                "early_exit": False
            }
            
            test_metadata = {
                "ticker": "AAPL",
                "entry_date": "2024-01-02",
                "historical_returns": [1.2, -0.5, 3.1, 0.8, -1.2, 2.1, 0.5, -0.8, 1.5, 0.3]
            }
            
            # Test the function
            result = stock_prediction_reward(
                messages=test_messages,
                ground_truth=test_ground_truth,
                metadata=test_metadata
            )
            
            print(f"✓ Reward function test completed!")
            print(f"  Score: {result.score:.3f}")
            print(f"  Valid: {result.is_score_valid}")
            print(f"  Reason: {result.reason}")
            print(f"  Metrics: {len(result.metrics)}")
            
            for name, metric in result.metrics.items():
                print(f"    {name}: {metric.score:.3f} - {metric.reason}")
        
        else:
            print("Testing with real data...")
            print("Real data testing not yet implemented")
            
    except Exception as e:
        logger.error(f"Failed to test reward function: {str(e)}")
        return False
    
    return True


def deploy_reward_function(args):
    """Deploy the reward function to Fireworks AI."""
    print("🚀 Deploying Reward Function")
    print("-" * 40)
    
    try:
        # Import and run deployment script
        from scripts.deploy_reward_function import deploy_reward_function
        
        success = deploy_reward_function()
        
        if success:
            print("✓ Reward function deployed successfully!")
        else:
            print("✗ Reward function deployment failed!")
            return False
            
    except Exception as e:
        logger.error(f"Failed to deploy reward function: {str(e)}")
        return False
    
    return True


def train_model(args):
    """Submit GRPO training job to Fireworks AI."""
    print("🎓 Submitting GRPO Training Job")
    print("-" * 40)
    
    try:
        # Import and run training script
        from scripts.train_grpo_model import submit_training_job
        
        success = submit_training_job()
        
        if success:
            print("✓ Training job submitted successfully!")
        else:
            print("✗ Training job submission failed!")
            return False
            
    except Exception as e:
        logger.error(f"Failed to submit training job: {str(e)}")
        return False
    
    return True


def validate_setup(args):
    """Validate the RLVR setup."""
    print("✅ Validating RLVR Setup")
    print("-" * 40)
    
    try:
        # Check configuration
        print("Checking configuration...")
        
        required_configs = [
            'FIREWORKS_API_KEY',
            'FIREWORKS_ACCOUNT_ID',
            'EVALUATOR_ID',
            'EVALUATOR_NAME',
            'MODEL_NAME'
        ]
        
        missing_configs = []
        for config_name in required_configs:
            if not hasattr(config, config_name) or not getattr(config, config_name):
                missing_configs.append(config_name)
        
        if missing_configs:
            print(f"✗ Missing configuration: {', '.join(missing_configs)}")
            return False
        else:
            print("✓ Configuration complete")
        
        # Check database connection
        print("Checking database connection...")
        db_manager = DatabaseManager(config.DB_URL)
        session = db_manager.get_session()
        
        try:
            # Test database health
            from sqlalchemy import text
            result = session.execute(text("SELECT * FROM database_health_check()")).fetchall()
            print("✓ Database connection successful")
            print(f"  Health check results: {len(result)} checks")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
        finally:
            session.close()
        
        # Check reward function
        print("Checking reward function...")
        try:
            # Test with minimal data
            test_messages = [
                {"role": "system", "content": "Test"},
                {"role": "user", "content": "Test"},
                {"role": "assistant", "content": '{"reasoning": "test", "action": "buy", "support": "test"}'}
            ]
            
            result = stock_prediction_reward(
                messages=test_messages,
                ground_truth={"actual_return_pct": 1.0},
                metadata={"ticker": "TEST", "entry_date": "2024-01-01", "historical_returns": [1.0]}
            )
            
            if result.is_score_valid:
                print("✓ Reward function working")
            else:
                print(f"✗ Reward function error: {result.reason}")
                return False
                
        except Exception as e:
            print(f"✗ Reward function failed: {e}")
            return False
        
        print("\n🎉 RLVR setup validation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Setup validation failed: {str(e)}")
        return False


def check_training_status(args):
    """Check status of GRPO training jobs."""
    print("🔍 Checking GRPO Training Job Status")
    print("-" * 40)

    try:
        import requests

        job_id = args.job_id if hasattr(args, 'job_id') and args.job_id else None

        if job_id:
            # Check specific job
            api_url = f"https://api.fireworks.ai/v1/fine-tuning/jobs/{job_id}"
            headers = {"Authorization": f"Bearer {config.FIREWORKS_API_KEY}"}

            try:
                response = requests.get(api_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    job_data = response.json()
                    print(f"Job ID: {job_data.get('id')}")
                    print(f"Status: {job_data.get('status')}")
                    print(f"Model: {job_data.get('model')}")
                    print(f"Created: {job_data.get('created_at')}")
                    if 'training_metrics' in job_data:
                        print(f"Metrics: {job_data['training_metrics']}")
                else:
                    print(f"✗ Failed to get job status: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"✗ Error checking job status: {e}")

        else:
            # List all jobs
            api_url = "https://api.fireworks.ai/v1/fine-tuning/jobs"
            headers = {"Authorization": f"Bearer {config.FIREWORKS_API_KEY}"}

            try:
                response = requests.get(api_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    jobs_data = response.json()
                    jobs = jobs_data.get('data', [])

                    if not jobs:
                        print("No training jobs found")
                    else:
                        print(f"Found {len(jobs)} training jobs:\n")
                        for job in jobs[:10]:  # Show last 10 jobs
                            print(f"  {job.get('id')}: {job.get('status')} - {job.get('model')}")

                    print("\nUse --job-id to see details for a specific job")
                else:
                    print(f"✗ Failed to list jobs: {response.status_code}")
            except Exception as e:
                print(f"✗ Error listing jobs: {e}")

        return True

    except Exception as e:
        logger.error(f"Failed to check training status: {str(e)}")
        return False


def show_stats(args):
    """Show RLVR statistics."""
    print("📊 RLVR Statistics")
    print("-" * 40)

    try:
        # Initialize database connection
        db_manager = DatabaseManager(config.DB_URL)
        session = db_manager.get_session()

        try:
            # Get database statistics
            stats_queries = [
                ("Total Tickers", "SELECT COUNT(*) FROM tickers WHERE is_active = true"),
                ("Total Thesis Generations", "SELECT COUNT(*) FROM thesis_generations"),
                ("Total Positions", "SELECT COUNT(*) FROM positions"),
                ("Total RLVR Examples", "SELECT COUNT(*) FROM rlvr_training_examples"),
                ("Recent Thesis Generations", "SELECT COUNT(*) FROM thesis_generations WHERE generated_at >= CURRENT_DATE - INTERVAL '7 days'")
            ]

            from sqlalchemy import text
            for name, query in stats_queries:
                try:
                    result = session.execute(text(query)).scalar()
                    print(f"{name}: {result}")
                except Exception as e:
                    print(f"{name}: Error - {e}")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        return False
    
    return True


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="RLVR Main CLI - Reinforcement Learning with Verifiable Rewards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rlvr_main.py generate --tickers AAPL,MSFT --start-date 2024-01-01 --end-date 2024-01-31
  python rlvr_main.py test-local --sample
  python rlvr_main.py deploy
  python rlvr_main.py train
  python rlvr_main.py validate
  python rlvr_main.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate RLVR datasets')
    generate_parser.add_argument('--tickers', help='Comma-separated list of tickers')
    generate_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    generate_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    generate_parser.add_argument('--train-split-date', help='Train/dev split date')
    generate_parser.add_argument('--output-dir', default='storage/rlvr_datasets', help='Output directory')
    
    # Test command
    test_parser = subparsers.add_parser('test-local', help='Test reward function locally')
    test_parser.add_argument('--sample', action='store_true', help='Use sample data')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy reward function')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Submit GRPO training job')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate RLVR setup')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show RLVR statistics')

    # Status command
    status_parser = subparsers.add_parser('status', help='Check GRPO training job status')
    status_parser.add_argument('--job-id', help='Specific job ID to check')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route to appropriate function
    command_functions = {
        'generate': generate_datasets,
        'test-local': test_reward_function,
        'deploy': deploy_reward_function,
        'train': train_model,
        'validate': validate_setup,
        'stats': show_stats,
        'status': check_training_status
    }
    
    if args.command in command_functions:
        success = command_functions[args.command](args)
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()