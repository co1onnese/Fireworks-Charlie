#!/usr/bin/env python3
"""
Simple dataset generator that bypasses reward_kit import issues
"""
import sys
sys.path.insert(0, '/opt/Fireworks-Charlie')

from orchestration.config_manager import config
from data_collection.database_manager import DatabaseManager
from rlvr.dataset_generator import RLVRDatasetGenerator

def main():
    print("=" * 60)
    print("RLVR Dataset Generator")
    print("=" * 60)

    # Initialize database connection
    db_manager = DatabaseManager(config.DB_URL)
    session = db_manager.get_session()

    try:
        # Initialize dataset generator
        generator = RLVRDatasetGenerator(session)

        # Generate datasets for all available theses
        result = generator.generate_rlvr_datasets(
            tickers=None,  # All tickers
            start_date=None,  # All dates
            end_date=None,
            train_split_date=None,  # Auto-calculate 80/20 split
            output_dir="/opt/Fireworks-Charlie/storage/rlvr_datasets"
        )

        print("\n" + "=" * 60)
        print("✓ Datasets Generated Successfully!")
        print("=" * 60)
        print(f"Training file:   {result['train_file']}")
        print(f"Dev file:        {result['dev_file']}")
        print("")
        print("Statistics:")
        print(f"  Total theses processed:       {result['stats']['total_theses']}")
        print(f"  Valid examples created:       {result['stats']['valid_examples']}")
        print(f"  Training examples:            {result['stats']['training_examples']}")
        print(f"  Dev examples:                 {result['stats']['dev_examples']}")
        print(f"  Skipped (insufficient data):  {result['stats']['skipped_insufficient_data']}")
        print(f"  Skipped (errors):             {result['stats']['skipped_errors']}")
        print("")
        print("Dataset files are ready for GRPO training!")
        print("=" * 60)

    finally:
        session.close()

if __name__ == "__main__":
    main()
