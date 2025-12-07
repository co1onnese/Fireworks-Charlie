#!/usr/bin/env python3
"""
Fireworks RFT Job Management Utilities

CLI utilities for creating, monitoring, and managing Fireworks RFT training jobs
that use our evalprotocol server as the remote evaluator.

Usage:
    python rlvr/rft_manager.py create --dataset-path storage/rlvr_datasets/train.jsonl --server-url http://localhost:8000
    python rlvr/rft_manager.py monitor --job-id your-job-id
    python rlvr/rft_manager.py list
    python rlvr/rft_manager.py cancel --job-id your-job-id

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    from eval_protocol import create_rft_job, get_rft_job_status, list_rft_jobs, cancel_rft_job
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install -r rlvr/requirements_evalprotocol.txt")
    sys.exit(1)


class RFTJobManager:
    """Manager for Fireworks RFT training jobs."""
    
    def __init__(self, api_key: Optional[str] = None, server_url: Optional[str] = None):
        """
        Initialize RFT job manager.
        
        Args:
            api_key: Fireworks API key (defaults to FIREWORKS_API_KEY env var)
            server_url: Evalprotocol server URL (defaults to http://localhost:8000)
        """
        self.api_key = api_key or os.getenv("FIREWORKS_API_KEY")
        self.server_url = server_url or os.getenv("EVALPROTOCOL_SERVER_URL", "http://localhost:8000")
        
        if not self.api_key:
            raise ValueError("Fireworks API key required. Set FIREWORKS_API_KEY environment variable or pass --api-key")
    
    def validate_server(self) -> bool:
        """Validate that the evalprotocol server is running and healthy."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    print(f"✅ Evalprotocol server is healthy at {self.server_url}")
                    return True
            
            print(f"❌ Evalprotocol server unhealthy: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ Cannot reach evalprotocol server at {self.server_url}: {e}")
            return False
    
    def create_rft_job(
        self,
        dataset_path: str,
        base_model: str = "accounts/fireworks/models/llama-v3p1-8b-instruct",
        job_name: Optional[str] = None,
        epochs: int = 1,
        learning_rate: float = 1e-4,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        validation_dataset_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new RFT training job.
        
        Args:
            dataset_path: Path to training dataset (JSONL format)
            base_model: Base model to fine-tune
            job_name: Optional job name (auto-generated if not provided)
            epochs: Number of training epochs
            learning_rate: Learning rate for training
            temperature: Temperature for model generation
            max_tokens: Maximum tokens per generation
            validation_dataset_path: Optional validation dataset path
            
        Returns:
            Dictionary with job creation details
        """
        # Validate inputs
        if not Path(dataset_path).exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        if validation_dataset_path and not Path(validation_dataset_path).exists():
            raise FileNotFoundError(f"Validation dataset not found: {validation_dataset_path}")
        
        # Validate server is running
        if not self.validate_server():
            raise RuntimeError("Evalprotocol server is not available")
        
        # Generate job name if not provided
        if not job_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_name = f"fireworks_charlie_rft_{timestamp}"
        
        # Prepare job configuration
        job_config = {
            "job_name": job_name,
            "base_model": base_model,
            "remote_server_url": self.server_url,
            "dataset_path": dataset_path,
            "validation_dataset_path": validation_dataset_path,
            "training_params": {
                "epochs": epochs,
                "learning_rate": learning_rate,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        print(f"🚀 Creating RFT job: {job_name}")
        print(f"📊 Dataset: {dataset_path}")
        print(f"🤖 Base model: {base_model}")
        print(f"🌐 Evaluator server: {self.server_url}")
        print(f"⚙️  Training params: {epochs} epochs, lr={learning_rate}, temp={temperature}")
        
        try:
            # Create the RFT job using eval-protocol
            job_result = create_rft_job(
                base_model=base_model,
                remote_server_url=self.server_url,
                dataset=dataset_path,
                validation_dataset=validation_dataset_path,
                job_name=job_name,
                epochs=epochs,
                learning_rate=learning_rate,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key
            )
            
            print(f"✅ RFT job created successfully!")
            print(f"📋 Job ID: {job_result.get('job_id', 'N/A')}")
            print(f"🔗 Monitor with: python rlvr/rft_manager.py monitor --job-id {job_result.get('job_id', 'N/A')}")
            
            return job_result
            
        except Exception as e:
            print(f"❌ Failed to create RFT job: {e}")
            raise
    
    def monitor_job(self, job_id: str, follow: bool = False) -> Dict[str, Any]:
        """
        Monitor RFT job status.
        
        Args:
            job_id: RFT job identifier
            follow: Whether to continuously monitor (tail -f style)
            
        Returns:
            Job status information
        """
        print(f"📊 Monitoring RFT job: {job_id}")
        
        try:
            while True:
                status = get_rft_job_status(job_id, api_key=self.api_key)
                
                # Display status
                print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"📋 Job ID: {job_id}")
                print(f"📊 Status: {status.get('status', 'unknown')}")
                print(f"📈 Progress: {status.get('progress', 'N/A')}")
                
                if status.get('metrics'):
                    metrics = status['metrics']
                    print(f"🎯 Current metrics:")
                    for key, value in metrics.items():
                        print(f"   {key}: {value}")
                
                if status.get('error'):
                    print(f"❌ Error: {status['error']}")
                
                # Check if job is complete
                if status.get('status') in ['completed', 'failed', 'cancelled']:
                    print(f"\n🏁 Job {status.get('status')}!")
                    if status.get('model_id'):
                        print(f"🤖 Fine-tuned model: {status['model_id']}")
                    break
                
                if not follow:
                    break
                
                # Wait before next check
                time.sleep(30)
            
            return status
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Monitoring stopped by user")
            return {}
        except Exception as e:
            print(f"❌ Error monitoring job: {e}")
            raise

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all RFT jobs."""
        try:
            jobs = list_rft_jobs(api_key=self.api_key)

            print(f"📋 RFT Jobs ({len(jobs)} total):")
            print("-" * 80)

            for job in jobs:
                print(f"📋 {job.get('job_id', 'N/A'):<20} | {job.get('status', 'unknown'):<12} | {job.get('job_name', 'N/A')}")

            return jobs

        except Exception as e:
            print(f"❌ Error listing jobs: {e}")
            raise

    def cancel_job(self, job_id: str) -> bool:
        """Cancel an RFT job."""
        try:
            print(f"⏹️  Cancelling RFT job: {job_id}")

            result = cancel_rft_job(job_id, api_key=self.api_key)

            if result.get('success'):
                print(f"✅ Job {job_id} cancelled successfully")
                return True
            else:
                print(f"❌ Failed to cancel job: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ Error cancelling job: {e}")
            raise


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Fireworks RFT Job Manager")
    parser.add_argument("--api-key", help="Fireworks API key (or set FIREWORKS_API_KEY)")
    parser.add_argument("--server-url", help="Evalprotocol server URL (default: http://localhost:8000)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new RFT job")
    create_parser.add_argument("--dataset-path", required=True, help="Path to training dataset (JSONL)")
    create_parser.add_argument("--validation-dataset-path", help="Path to validation dataset (JSONL)")
    create_parser.add_argument("--base-model", default="accounts/fireworks/models/llama-v3p1-8b-instruct", help="Base model to fine-tune")
    create_parser.add_argument("--job-name", help="Job name (auto-generated if not provided)")
    create_parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    create_parser.add_argument("--learning-rate", type=float, default=1e-4, help="Learning rate")
    create_parser.add_argument("--temperature", type=float, default=0.7, help="Generation temperature")
    create_parser.add_argument("--max-tokens", type=int, default=2048, help="Max tokens per generation")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor RFT job")
    monitor_parser.add_argument("--job-id", required=True, help="RFT job ID to monitor")
    monitor_parser.add_argument("--follow", "-f", action="store_true", help="Continuously monitor (like tail -f)")

    # List command
    list_parser = subparsers.add_parser("list", help="List all RFT jobs")

    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel RFT job")
    cancel_parser.add_argument("--job-id", required=True, help="RFT job ID to cancel")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        manager = RFTJobManager(api_key=args.api_key, server_url=args.server_url)

        if args.command == "create":
            manager.create_rft_job(
                dataset_path=args.dataset_path,
                validation_dataset_path=args.validation_dataset_path,
                base_model=args.base_model,
                job_name=args.job_name,
                epochs=args.epochs,
                learning_rate=args.learning_rate,
                temperature=args.temperature,
                max_tokens=args.max_tokens
            )

        elif args.command == "monitor":
            manager.monitor_job(args.job_id, follow=args.follow)

        elif args.command == "list":
            manager.list_jobs()

        elif args.command == "cancel":
            manager.cancel_job(args.job_id)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
