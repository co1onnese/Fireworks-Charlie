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
    level=logging.DEBUG,  # Enable debug for troubleshooting
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


SIGNED_URL_THRESHOLD_BYTES = 50 * 1024 * 1024  # 50 MB - conservative threshold to avoid Cloudflare worker limits


def upload_file_to_fireworks(file_path: str, purpose: str = "fine-tune") -> str:
    """
    Upload a file to Fireworks AI using the documented two-step API.
    
    Based on: https://fireworks.ai/docs/api-reference/upload-dataset-files
    
    Step 1: Create dataset to get dataset_id
    Step 2: Upload file to that dataset_id
    
    Args:
        file_path: Path to the file to upload
        purpose: Purpose of the file (default: "fine-tune")
        
    Returns:
        Dataset ID from Fireworks
    """
    import requests
    import uuid
    
    logger.info(f"Uploading {file_path} to Fireworks AI...")
    
    try:
        headers = {
            "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Step 1: Create dataset with proper structure
        dataset_id = f"fw-dataset-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        dataset_name = os.path.basename(file_path).replace('.jsonl', '')
        
        create_url = f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets"
        
        create_payload = {
            "datasetId": dataset_id,
            "dataset": {
                "displayName": dataset_name,
                "format": "RL",  # RL format for RLVR/GRPO training
                "userUploaded": {}
            }
        }
        
        logger.debug(f"Creating dataset at: {create_url}")
        logger.debug(f"Payload: {json.dumps(create_payload, indent=2)}")
        
        create_response = requests.post(create_url, headers=headers, json=create_payload, timeout=30)
        
        logger.debug(f"Create response status: {create_response.status_code}")
        logger.debug(f"Create response: {create_response.text[:1000]}")
        
        if create_response.status_code not in [200, 201]:
            logger.error(f"Failed to create dataset: {create_response.status_code}")
            logger.error(f"Response: {create_response.text}")
            raise Exception(f"Dataset creation failed: {create_response.text}")
        
        logger.info(f"✓ Dataset created: {dataset_id}")
        
        # Step 2: Get upload endpoint (for files, especially >150MB)
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        use_signed_url = file_size >= SIGNED_URL_THRESHOLD_BYTES

        if not use_signed_url:
            # Attempt direct :upload endpoint first
            upload_url = f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets/{dataset_id}:upload"

            logger.debug(f"Using direct upload to: {upload_url}")
            logger.debug(f"File size: {file_size:,} bytes (<{SIGNED_URL_THRESHOLD_BYTES} bytes threshold)")

            upload_headers = {
                "Authorization": f"Bearer {config.FIREWORKS_API_KEY}"
            }

            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, 'application/jsonl')
                }

                upload_response = requests.post(
                    upload_url,
                    headers=upload_headers,
                    files=files,
                    timeout=600
                )

            logger.debug(f"Upload response status: {upload_response.status_code}")
            logger.debug(f"Upload response: {upload_response.text[:500]}")

            if upload_response.status_code in [200, 201]:
                upload_data = upload_response.json()
                logger.info(f"✓ File uploaded successfully!")
                logger.info(f"✓ Dataset ID: {dataset_id}")
                logger.info(f"✓ Filename: {upload_data.get('filename', filename)}")
                logger.info(f"✓ Size: {upload_data.get('bytes', file_size):,} bytes")
            else:
                logger.warning(
                    "Direct upload failed with status %s. Falling back to signed URL.",
                    upload_response.status_code,
                )
                logger.debug(f"Direct upload response body: {upload_response.text[:500]}")
                use_signed_url = True

        if use_signed_url:
            logger.debug(
                "File size: %s bytes, using signed URL flow (threshold: %s)",
                f"{file_size:,}",
                f"{SIGNED_URL_THRESHOLD_BYTES:,}",
            )

            get_endpoint_url = f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets/{dataset_id}:getUploadEndpoint"

            get_endpoint_payload = {
                "filenameToSize": {
                    filename: file_size
                }
            }

            logger.debug(f"Getting upload endpoint: {get_endpoint_url}")
            endpoint_response = requests.post(
                get_endpoint_url,
                headers=headers,
                json=get_endpoint_payload,
                timeout=30
            )

            if endpoint_response.status_code not in [200, 201]:
                logger.error(f"Failed to get upload endpoint: {endpoint_response.status_code}")
                logger.error(f"Response: {endpoint_response.text}")
                raise Exception(f"Get upload endpoint failed: {endpoint_response.text}")

            endpoint_data = endpoint_response.json()
            signed_url = endpoint_data.get('filenameToSignedUrls', {}).get(filename)

            if not signed_url:
                raise Exception(f"No signed URL returned for {filename}")

            logger.info(f"✓ Got signed URL for upload")

            with open(file_path, 'rb') as f:
                signed_response = requests.put(
                    signed_url,
                    data=f,
                    headers={'Content-Type': 'application/jsonl'},
                    timeout=600
                )

            if signed_response.status_code not in [200, 201]:
                logger.error(f"Failed to upload to signed URL: {signed_response.status_code}")
                raise Exception(f"Signed URL upload failed")

            logger.info(f"✓ File uploaded to signed URL!")
            logger.info(f"✓ Dataset ID: {dataset_id}")
        
        # Step 3: Validate the uploaded dataset
        logger.info(f"Validating dataset {dataset_id}...")
        validate_url = f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets/{dataset_id}:validateUpload"
        
        validate_response = requests.post(
            validate_url,
            headers=headers,
            json={},
            timeout=60
        )
        
        logger.debug(f"Validation response status: {validate_response.status_code}")
        logger.debug(f"Validation response: {validate_response.text[:500]}")
        
        if validate_response.status_code in [200, 201]:
            logger.info(f"✓ Dataset validation successful!")
        elif validate_response.status_code == 400:
            # Check if it's the "already uploaded" message (which is actually success)
            response_text = validate_response.text
            if "already uploaded" in response_text.lower():
                logger.info(f"✓ Dataset already validated (upload confirmed)")
            else:
                logger.warning(f"Dataset validation returned error:")
                logger.warning(f"Response: {response_text}")
                logger.warning("Continuing despite validation warning...")
        else:
            logger.warning(f"Dataset validation returned {validate_response.status_code}")
            logger.warning(f"Response: {validate_response.text}")
            logger.warning("Continuing despite validation warning...")
        
        return dataset_id
    
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        raise


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
        
        # Upload training and validation files
        logger.info("Uploading training files to Fireworks AI...")
        try:
            train_file_id = upload_file_to_fireworks(config.RLVR_TRAIN_FILE, purpose="fine-tune")
            dev_file_id = upload_file_to_fireworks(config.RLVR_DEV_FILE, purpose="fine-tune")
        except Exception as e:
            logger.error(f"Failed to upload files: {e}")
            return False
        
        # Prepare training parameters
        training_params = {
            "model": config.MODEL_NAME,
            "training_file": train_file_id,  # Use uploaded file ID
            "validation_file": dev_file_id,  # Use uploaded file ID
            "hyperparameters": {
                "n_epochs": config.GRPO_EPOCHS,
                "learning_rate": config.GRPO_LEARNING_RATE,
                "lora_rank": config.GRPO_LORA_RANK,
                "batch_size": config.GRPO_BATCH_SIZE,
                "algorithm": "grpo",
                "n_samples": config.GRPO_NUM_RESPONSES,
                "temperature": config.GEN_TEMPERATURE,  # Use generation temperature
                "max_tokens": config.GEN_MAX_TOKENS,    # Use generation max tokens
                "top_p": config.GEN_TOP_P,              # Use generation top_p
                "top_k": config.GEN_TOP_K               # Use generation top_k
            },
            "reward_config": {
                "evaluator_id": config.EVALUATOR_ID
            }
        }
        
        logger.info("Training parameters:")
        logger.info(f"  Model: {training_params['model']}")
        logger.info(f"  Training file ID: {train_file_id}")
        logger.info(f"  Validation file ID: {dev_file_id}")
        logger.info(f"  Epochs: {training_params['hyperparameters']['n_epochs']}")
        logger.info(f"  Learning Rate: {training_params['hyperparameters']['learning_rate']}")
        logger.info(f"  LoRA Rank: {training_params['hyperparameters']['lora_rank']}")
        logger.info(f"  Batch Size: {training_params['hyperparameters']['batch_size']}")
        logger.info(f"  Num Responses: {training_params['hyperparameters']['n_samples']}")
        logger.info(f"  Temperature: {training_params['hyperparameters']['temperature']}")
        logger.info(f"  Evaluator ID: {training_params['reward_config']['evaluator_id']}")

        # Submit GRPO training job to Fireworks AI
        logger.info("Submitting GRPO training job to Fireworks AI...")

        import requests

        # Use the correct reinforcement fine-tuning endpoint
        api_url = f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/reinforcementFineTuningJobs"
        
        headers = {
            "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
            "Content-Type": "application/json"
        }

        # Prepare API payload according to the reinforcement fine-tuning schema
        # Dataset and evaluator names must be in full resource format
        train_dataset_name = f"accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets/{train_file_id}"
        dev_dataset_name = f"accounts/{config.FIREWORKS_ACCOUNT_ID}/datasets/{dev_file_id}"
        evaluator_name = f"accounts/{config.FIREWORKS_ACCOUNT_ID}/evaluators/{config.EVALUATOR_ID}"
        
        payload = {
            "displayName": f"stock-prediction-grpo-{datetime.now().strftime('%Y%m%d')}",
            "dataset": train_dataset_name,
            "evaluationDataset": dev_dataset_name,
            "evaluator": evaluator_name,
            "trainingConfig": {
                "baseModel": training_params['model'],
                "learningRate": training_params['hyperparameters']['learning_rate'],
                "loraRank": training_params['hyperparameters']['lora_rank'],
                "epochs": training_params['hyperparameters']['n_epochs'],
                "batchSize": training_params['hyperparameters']['batch_size']
            },
            "inferenceParameters": {
                "maxTokens": training_params['hyperparameters']['max_tokens'],
                "temperature": training_params['hyperparameters']['temperature'],
                "topP": training_params['hyperparameters']['top_p'],
                "topK": training_params['hyperparameters']['top_k'],
                "n": training_params['hyperparameters']['n_samples']  # Number of responses for GRPO
            }
        }

        logger.debug(f"API URL: {api_url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        # Submit the training job
        job_id = None
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text[:1000]}")

            if response.status_code in [200, 201]:
                job_data = response.json()
                # The response has 'name' field which is the resource name
                job_name = job_data.get("name", "")
                # Extract job ID from name (format: accounts/{account}/reinforcementFineTuningJobs/{job_id})
                if job_name:
                    job_id = job_name.split('/')[-1]
                else:
                    job_id = f"grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                logger.info(f"✓ GRPO training job submitted successfully!")
                logger.info(f"Job ID: {job_id}")
                logger.info(f"Job Name: {job_name}")
                logger.info(f"Display Name: {job_data.get('displayName', 'N/A')}")
                logger.info(f"State: {job_data.get('state', 'SUBMITTED')}")
                logger.info(f"Dataset: {job_data.get('dataset', train_file_id)}")
                logger.info(f"Evaluation Dataset: {job_data.get('evaluationDataset', dev_file_id)}")
                logger.info(f"Evaluator: {job_data.get('evaluator', config.EVALUATOR_ID)}")
                
                # Check status
                status = job_data.get('status', {})
                if status:
                    status_code = status.get('code', 'OK')
                    status_message = status.get('message', '')
                    if status_code != 'OK':
                        logger.warning(f"Status code: {status_code}, Message: {status_message}")
                
                logger.debug(f"Full response: {json.dumps(job_data, indent=2)}")

            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")

                # Fall back to manual submission instructions
                logger.warning("Automatic submission failed - providing manual instructions")
                job_id = f"manual_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                logger.info("=" * 60)
                logger.info("MANUAL SUBMISSION REQUIRED")
                logger.info("=" * 60)
                logger.info("Files have been uploaded. Use the Fireworks AI CLI or dashboard to submit:")
                logger.info(f"  Training file ID: {train_file_id}")
                logger.info(f"  Validation file ID: {dev_file_id}")
                logger.info(f"  Model: {training_params['model']}")
                logger.info(f"  Evaluator: {training_params['reward_config']['evaluator_id']}")
                logger.info(f"  Algorithm: GRPO")
                logger.info(f"\nSee TRAINING_SUBMISSION_GUIDE.md for detailed instructions")
                logger.info("=" * 60)
        
        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            job_id = f"timeout_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            job_id = f"error_grpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
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