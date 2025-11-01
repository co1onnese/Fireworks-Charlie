#!/usr/bin/env python3
"""
Check Fine-Tuned Model Deployment Status

Monitors the deployment status of a fine-tuned model on Fireworks AI.

Author: Fireworks-Charlie Team
Date: 2025-10-30
"""

import sys
import os
import json
import time
import requests
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config


def check_model_status(model_id: str) -> dict:
    """
    Check the status of a fine-tuned model.
    
    Args:
        model_id: Model ID (e.g., rftj-v1in37s4-evv0b)
        
    Returns:
        Status information dictionary
    """
    headers = {
        "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try to query the model info
    # Note: The exact endpoint might vary - trying common patterns
    endpoints = [
        f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/reinforcementFineTuningJobs/{model_id}",
        f"https://api.fireworks.ai/v1/accounts/{config.FIREWORKS_ACCOUNT_ID}/models/{model_id}",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "status": response.json(),
                    "endpoint": endpoint
                }
            elif response.status_code == 404:
                continue
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "endpoint": endpoint
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "endpoint": endpoint
            }
    
    return {
        "success": False,
        "error": "Model not found at any known endpoint"
    }


def test_model_inference(model_name: str) -> dict:
    """
    Test if model is available for inference.
    
    Args:
        model_name: Full model name (e.g., accounts/lstn/models/xyz)
        
    Returns:
        Inference test result
    """
    from openai import OpenAI
    
    client = OpenAI(
        api_key=config.FIREWORKS_API_KEY,
        base_url="https://api.fireworks.ai/inference/v1"
    )
    
    try:
        # Simple test query
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        return {
            "success": True,
            "message": "Model is ready for inference",
            "response": response.choices[0].message.content
        }
    
    except Exception as e:
        error_str = str(e)
        
        if "404" in error_str or "NOT_FOUND" in error_str:
            return {
                "success": False,
                "message": "Model not yet deployed or inaccessible",
                "error": error_str
            }
        elif "rate_limit" in error_str.lower():
            return {
                "success": False,
                "message": "Rate limited - but model exists",
                "error": error_str
            }
        else:
            return {
                "success": False,
                "message": "Inference test failed",
                "error": error_str
            }


def list_models(account_id: str) -> dict:
    """
    List all models for an account.
    
    Args:
        account_id: Fireworks account ID
        
    Returns:
        List of models
    """
    headers = {
        "Authorization": f"Bearer {config.FIREWORKS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try to list models
    endpoints = [
        f"https://api.fireworks.ai/v1/accounts/{account_id}/models",
        f"https://api.fireworks.ai/v1/accounts/{account_id}/reinforcementFineTuningJobs",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "models": response.json(),
                    "endpoint": endpoint
                }
        
        except Exception as e:
            continue
    
    return {
        "success": False,
        "error": "Could not list models"
    }


def monitor_deployment(model_id: str, model_name: str, check_interval: int = 30, max_checks: int = 120):
    """
    Monitor model deployment until ready.
    
    Args:
        model_id: Model ID
        model_name: Full model name
        check_interval: Seconds between checks
        max_checks: Maximum number of checks before giving up
    """
    print(f"?? Monitoring deployment of {model_name}")
    print(f"Checking every {check_interval} seconds...")
    print("=" * 70)
    
    for i in range(max_checks):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Check {i+1}/{max_checks}")
        
        # Check job status
        status_result = check_model_status(model_id)
        
        if status_result['success']:
            job_info = status_result['status']
            state = job_info.get('state', 'UNKNOWN')
            
            print(f"  Job State: {state}")
            
            if 'completedTime' in job_info:
                print(f"  Completed: {job_info['completedTime']}")
            
            if state == 'JOB_STATE_SUCCEEDED':
                print("\n? Training job completed successfully!")
                
                # Test inference
                print("\nTesting model inference...")
                inference_result = test_model_inference(model_name)
                
                if inference_result['success']:
                    print("? Model is READY for inference!")
                    print(f"  Test response: {inference_result['response']}")
                    return True
                else:
                    print(f"? Model inference not yet available")
                    print(f"  {inference_result['message']}")
            
            elif state in ['JOB_STATE_FAILED', 'JOB_STATE_CANCELLED']:
                print(f"\n? Training job {state.lower()}")
                if 'status' in job_info:
                    print(f"  Status: {job_info['status']}")
                return False
        
        else:
            # Try inference test directly
            inference_result = test_model_inference(model_name)
            
            if inference_result['success']:
                print("? Model is READY for inference!")
                return True
            else:
                print(f"  Status: {inference_result['message']}")
        
        if i < max_checks - 1:
            print(f"\nWaiting {check_interval} seconds...")
            time.sleep(check_interval)
    
    print(f"\n? Timeout after {max_checks} checks")
    return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Check fine-tuned model deployment status",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--model-id',
        default='rftj-v1in37s4-evv0b',
        help='Model ID (without account prefix)'
    )
    parser.add_argument(
        '--model-name',
        default='accounts/lstn/models/rftj-v1in37s4-evv0b',
        help='Full model name for inference testing'
    )
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Monitor deployment until ready'
    )
    parser.add_argument(
        '--check-interval',
        type=int,
        default=30,
        help='Seconds between checks (default: 30)'
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List all models for account'
    )
    
    args = parser.parse_args()
    
    print("?? Fireworks Model Status Checker")
    print("=" * 70)
    
    if args.list_models:
        print("\n?? Listing all models...")
        result = list_models(config.FIREWORKS_ACCOUNT_ID)
        
        if result['success']:
            print(json.dumps(result['models'], indent=2))
        else:
            print(f"? {result['error']}")
        
        return
    
    if args.monitor:
        success = monitor_deployment(
            args.model_id,
            args.model_name,
            args.check_interval
        )
        sys.exit(0 if success else 1)
    
    else:
        # Single check
        print(f"\nModel ID: {args.model_id}")
        print(f"Model Name: {args.model_name}\n")
        
        # Check status
        print("Checking job status...")
        status_result = check_model_status(args.model_id)
        
        if status_result['success']:
            print("? Job found!")
            print(json.dumps(status_result['status'], indent=2))
        else:
            print(f"? {status_result['error']}")
        
        print("\n" + "-" * 70)
        
        # Test inference
        print("\nTesting model inference...")
        inference_result = test_model_inference(args.model_name)
        
        if inference_result['success']:
            print("? Model is READY for inference!")
            print(f"  Test response: {inference_result['response']}")
        else:
            print(f"? {inference_result['message']}")
            if 'error' in inference_result:
                print(f"  Error: {inference_result['error'][:200]}")


if __name__ == "__main__":
    main()
