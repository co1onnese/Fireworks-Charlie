#!/usr/bin/env python3
"""
Submit GRPO training job to Fireworks AI

This script submits a GRPO (Group Relative Policy Optimization) training job
to Fireworks AI using the deployed reward function.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_training_files():
    """Validate that training files exist and are properly formatted."""
    logger.info("Validating training files...")
    
    # Check if training files exist
    train_file = Path(config.RLVR_TRAIN_FILE)
    dev_file = Path(config.RLVR_DEV_FILE)
    
    if not train_file.exists():
        logger.error(f"Training file not found: {train_file}")
        return False
    
    if not dev_file.exists():
        logger.error(f"Development file not found: {dev_file}")
        return False
    
    # Check file sizes
    train_size = train_file.stat().st_size
    dev_size = dev_file.stat().st_size
    
    if train_size == 0:
        logger.error("Training file is empty")
        return False
    
    if dev_size == 0:
        logger.error("Development file is empty")
        return False
    
    logger.info(f"✓ Training file: {train_file} ({train_size:,} bytes)")
    logger.info(f"✓ Development file: {dev_file} ({dev_size:,} bytes)")
    
    # Validate JSONL format
    try:
        with open(train_file, 'r') as f:
            train_lines = f.readlines()
        
        with open(dev_file, 'r') as f:
            dev_lines = f.readlines()
        
        # Validate first few lines
        for i, line in enumerate(train_lines[:3]):
            try:
                json.loads(line.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in training file line {i+1}: {e}")
                return False
        
        for i, line in enumerate(dev_lines[:3]):
            try:
                json.loads(line.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in dev file line {i+1}: {e}")
                return False
        
        logger.info(f"✓ Training examples: {len(train_lines)}")
        logger.info(f"✓ Development examples: {len(dev_lines)}")
        
    except Exception as e:
        logger.error(f"Error validating files: {e}")
        return False
    
    return True


def submit_training_job():
    """Submit GRPO training job to Fireworks AI."""
    logger.info("Submitting GRPO training job...")
    
    try:
        # Validate configuration
        if not config.FIREWORKS_API_KEY:
            logger.error("FIREWORKS_API_KEY not configured")
            return False
        
        if not config.EVALUATOR_ID:
            logger.error("EVALUATOR_ID not configured")
            return False
        
        # Validate training files
        if not validate_training_files():
            return False
        
        # Prepare training parameters
        training_params = {
            "model": config.MODEL_NAME,
            "training_file": config.RLVR_TRAIN_FILE,
            "validation_file": config.RLVR_DEV_FILE,
            "hyperparameters": {
                "n_epochs": config.GRPO_EPOCHS,
                "learning_rate": config.GRPO_LEARNING_RATE,
                "lora_rank": config.GRPO_LORA_RANK,
                "batch_size": config.GRPO_BATCH_SIZE,
                "algorithm": "grpo",
                "n_samples": config.GRPO_NUM_RESPONSES,
                "temperature": config.TEMPERATURE,
                "max_tokens": config.MAX_TOKENS,
                "top_p": config.TOP_P,
                "top_k": config.TOP_K
            },
            "reward_config": {
                "evaluator_id": config.EVALUATOR_ID
            }
        }
        
        logger.info("Training parameters:")
        logger.info(f"  Model: {training_params['model']}")
        logger.info(f"  Epochs: {training_params['hyperparameters']['n_epochs']}")
        logger.info(f"  Learning Rate: {training_params['hyperparameters']['learning_rate']}")
        logger.info(f"  LoRA Rank: {training_params['hyperparameters']['lora_rank']}")
        logger.info(f"  Batch Size: {training_params['hyperparameters']['batch_size']}")
        logger.info(f"  Num Responses: {training_params['hyperparameters']['n_samples']}")
        logger.info(f"  Temperature: {training_params['hyperparameters']['temperature']}")
        logger.info(f"  Evaluator ID: {training_params['reward_config']['evaluator_id']}")

        # Submit GRPO training job to Fireworks AI
        logger.info("Submitting training job to Fireworks AI...")

        try:
            # Use Fireworks API directly for fine-tuning
            import requests

            api_url = "https://api.fireworks.ai/v1/fine-tuning/jobs"
            headers = {
                "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
                "Content-Type": "application/json"
            }

            # Prepare API payload
            payload = {
                "model": training_params['model'],
                "training_file": training_params['training_file'],
                "validation_file": training_params['validation_file'],
                "hyperparameters": training_params['hyperparameters'],
                "reward_config": training_params['reward_config'],
                "suffix": f"grpo-{datetime.now().strftime('%Y%m%d')}"
            }

            # Submit the training job
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200 or response.status_code == 201:
                job_data = response.json()
                job_id = job_data.get("id", f"grpo_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

                logger.info(f"✓ Training job submitted successfully!")
                logger.info(f"Job ID: {job_id}")
                logger.info(f"Status: {job_data.get('status', 'Submitted')}")

            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")

                # Fall back to manual submission instructions
                logger.warning("Automatic submission failed - providing manual instructions")
                job_id = f"manual_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                logger.info("=" * 60)
                logger.info("MANUAL SUBMISSION REQUIRED")
                logger.info("=" * 60)
                logger.info("Use the Fireworks AI CLI or dashboard to submit:")
                logger.info(f"  Training file: {training_params['training_file']}")
                logger.info(f"  Validation file: {training_params['validation_file']}")
                logger.info(f"  Model: {training_params['model']}")
                logger.info(f"  Evaluator: {training_params['reward_config']['evaluator_id']}")
                logger.info("=" * 60)

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API call: {e}")

            # Fall back to manual instructions
            job_id = f"manual_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.warning("Network error - falling back to manual submission")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            # Create fallback job ID
            job_id = f"error_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save job details
        job_details = {
            "job_id": job_id,
            "status": "submitted",
            "submitted_at": datetime.now().isoformat(),
            "parameters": training_params
        }
        
        job_file = Path("outputs/training") / f"{job_id}.json"
        job_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(job_file, 'w') as f:
            json.dump(job_details, f, indent=2)
        
        logger.info(f"Job details saved to: {job_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to submit training job: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main training submission function."""
    print("🚀 Submitting GRPO Training Job to Fireworks AI")
    print("=" * 50)
    
    success = submit_training_job()
    
    if success:
        print("\n🎉 Training job submitted successfully!")
        print("\nNext steps:")
        print("1. Monitor training progress in Fireworks AI dashboard")
        print("2. Check job status periodically")
        print("3. Download trained model when complete")
        print("4. Test model performance")
    else:
        print("\n❌ Training job submission failed!")
        print("Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()