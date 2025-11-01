#!/usr/bin/env python3
"""
Deploy reward function to Fireworks AI

This script deploys the stock prediction reward function to Fireworks AI
for use in RLVR training.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from rlvr.reward_function_advanced import stock_prediction_reward  # Using advanced version

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def deploy_reward_function():
    """Deploy the reward function to Fireworks AI."""
    logger.info("Starting reward function deployment")
    
    try:
        # Validate configuration
        if not config.FIREWORKS_API_KEY:
            logger.error("FIREWORKS_API_KEY not configured")
            return False
        
        if not config.EVALUATOR_ID:
            logger.error("EVALUATOR_ID not configured")
            return False
        
        if not config.EVALUATOR_NAME:
            logger.error("EVALUATOR_NAME not configured")
            return False
        
        logger.info(f"Deploying reward function: {config.EVALUATOR_NAME}")
        logger.info(f"Evaluator ID: {config.EVALUATOR_ID}")

        # Step 1: Test the reward function locally first
        logger.info("Step 1: Testing reward function locally...")

        # Create a test example
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

        if result.is_score_valid:
            logger.info(f"✓ Reward function test successful: score={result.score:.3f}")
        else:
            logger.error(f"✗ Reward function test failed: {result.reason}")
            return False

        # Step 2: Deploy to Fireworks AI using reward-kit CLI
        logger.info("Step 2: Deploying reward function to Fireworks AI...")

        try:
            import subprocess
            import sys

            # Build the deploy command using reward-kit CLI
            deploy_cmd = [
                sys.executable, "-m", "reward_kit", "deploy",
                "--id", config.EVALUATOR_ID,
                "--metrics-folders", f"stock_prediction={os.path.join(os.getcwd(), 'rlvr')}",
                "--display-name", config.EVALUATOR_NAME,
                "--force"
            ]

            logger.info(f"Running deployment command: {' '.join(deploy_cmd)}")

            # Run the deployment
            result = subprocess.run(
                deploy_cmd,
                cwd="/opt/Fireworks-Charlie",
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info(f"✓ Reward function deployed successfully!")
                logger.info(f"Evaluator ID: {config.EVALUATOR_ID}")
                logger.info(f"Evaluator Name: {config.EVALUATOR_NAME}")
                logger.info(f"Deployment output:\n{result.stdout}")
            else:
                logger.error(f"✗ Deployment failed with exit code {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")

                # Provide manual deployment instructions
                logger.info("\n" + "="*60)
                logger.info("MANUAL DEPLOYMENT INSTRUCTIONS:")
                logger.info("="*60)
                logger.info(f"1. Use the reward-kit CLI command:")
                logger.info(f"   reward-kit deploy --id {config.EVALUATOR_ID} \\")
                logger.info(f"     --function-ref rlvr.reward_function:stock_prediction_reward \\")
                logger.info(f"     --force")
                logger.info(f"2. Or use the Fireworks AI web dashboard to upload the function")
                logger.info(f"3. Reward function location: rlvr/reward_function.py")
                logger.info("="*60)

                return False

        except subprocess.TimeoutExpired:
            logger.error("Deployment timed out after 60 seconds")
            return False

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to deploy reward function: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main deployment function."""
    print("🚀 Deploying Reward Function to Fireworks AI")
    print("=" * 50)
    
    success = deploy_reward_function()
    
    if success:
        print("\n🎉 Reward function deployed successfully!")
        print(f"Evaluator ID: {config.EVALUATOR_ID}")
        print(f"Evaluator Name: {config.EVALUATOR_NAME}")
        print("\nNext steps:")
        print("1. Verify deployment in Fireworks AI dashboard")
        print("2. Test with sample data")
        print("3. Proceed with GRPO training")
    else:
        print("\n❌ Reward function deployment failed!")
        print("Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()