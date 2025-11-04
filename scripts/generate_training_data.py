#!/usr/bin/env python3
"""
Generate RLVR Training Data

Production script to generate RLVR training datasets from database.
This script uses existing database data (no API calls) to generate clean training data.
"""
import os
import sys
import json
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestration.config_manager import config
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator
from utils.logger import setup_logger

logger = setup_logger(
    name="generate_training_data",
    log_file="logs/generate_training_data.log",
    log_level="INFO"
)


def load_thesis_dates_from_db(session) -> List[Dict[str, Any]]:
    """Load thesis dates from database"""
    from sqlalchemy import text

    # Query to get unique ticker-date combinations from theses
    # This gives us the training examples we need to generate
    query = text("""
        SELECT DISTINCT ticker_symbol, thesis_date
        FROM stock_theses
        WHERE thesis_date BETWEEN :start_date AND :end_date
        ORDER BY ticker_symbol, thesis_date
    """)

    result = session.execute(query, {
        "start_date": config.START_DATE,
        "end_date": config.END_DATE
    })

    thesis_dates = []
    for row in result:
        thesis_dates.append({
            "ticker": row[0],
            "date": row[1]
        })

    return thesis_dates


def generate_single_prompt(orchestrator: DataOrchestrator,
                           prompt_builder: CumulativePromptBuilder,
                           deduplicator: DataDeduplicator,
                           ticker: str,
                           thesis_date: date) -> Dict[str, Any]:
    """Generate a single training example"""

    # Get data for the thesis date
    data = orchestrator.get_data_for_date(ticker, thesis_date)

    if "error" in data:
        logger.error(f"  ❌ {ticker} on {thesis_date}: {data['error']}")
        return None

    # Generate prompt messages
    system_prompt, user_prompt = prompt_builder.build_cumulative_prompt_messages(
        ticker,
        [data],
        response_format="json"
    )

    # Build training example
    example = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "metadata": {
            "ticker": ticker,
            "date": thesis_date.isoformat(),
            "technical_days": data.get("technical_days", 0),
            "has_fundamentals": data.get("fundamentals") is not None,
            "has_macro": data.get("macro_features") is not None,
            "news_count": len(data.get("news", {}).get("recent_articles", [])) +
                         len(data.get("news", {}).get("older_articles", []))
        }
    }

    return example


def generate_training_data(output_dir: str,
                          split_ratios: Dict[str, float] = {"train": 0.95, "dev": 0.05},
                          start_date: str = None,
                          end_date: str = None) -> Dict[str, Any]:
    """
    Generate RLVR training datasets from database

    Args:
        output_dir: Output directory for JSONL files
        split_ratios: Train/dev split ratios
        start_date: Override start date
        end_date: Override end date

    Returns:
        Dictionary with generation results
    """
    # Use provided dates or fall back to config
    start_date = date.fromisoformat(start_date) if start_date else date.fromisoformat(config.START_DATE)
    end_date = date.fromisoformat(end_date) if end_date else date.fromisoformat(config.END_DATE)

    logger.info("=" * 80)
    logger.info("RLVR TRAINING DATA GENERATION")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  Date range: {start_date} to {end_date}")
    logger.info(f"  Output directory: {output_dir}")
    logger.info(f"  Split ratios: {split_ratios}")
    logger.info("")

    # Initialize components
    orchestrator = DataOrchestrator(config)
    prompt_builder = CumulativePromptBuilder(DataDeduplicator())

    # Connect to database
    from data_collection.database_manager import DatabaseManager
    db_manager = DatabaseManager(config.DB_URL)
    session = db_manager.get_session()

    try:
        # Load thesis dates
        logger.info("Loading thesis dates from database...")
        thesis_dates = load_thesis_dates_from_db(session)

        if not thesis_dates:
            logger.error("No thesis dates found in database!")
            return {"error": "no_thesis_dates"}

        logger.info(f"Found {len(thesis_dates)} thesis records")

        # Shuffle for random split
        import random
        random.seed(42)  # For reproducibility
        random.shuffle(thesis_dates)

        # Calculate split points
        total = len(thesis_dates)
        train_count = int(total * split_ratios.get("train", 0.95))
        dev_count = total - train_count

        train_thesis_dates = thesis_dates[:train_count]
        dev_thesis_dates = thesis_dates[train_count:]

        logger.info(f"Train split: {len(train_thesis_dates)} examples")
        logger.info(f"Dev split: {len(dev_thesis_dates)} examples")
        logger.info("")

        # Generate datasets
        results = {}

        for split_name, split_data in [("train", train_thesis_dates), ("dev", dev_thesis_dates)]:
            logger.info(f"=" * 80)
            logger.info(f"Generating {split_name} dataset")
            logger.info(f"=" * 80)

            output_file = Path(output_dir) / f"{split_name}.jsonl"
            logger.info(f"Output file: {output_file}")

            successful = 0
            failed = 0

            with open(output_file, 'w') as f:
                for i, thesis_info in enumerate(split_data, 1):
                    ticker = thesis_info["ticker"]
                    thesis_date = thesis_info["date"]

                    # Progress logging
                    if i % 100 == 0 or i == 1:
                        logger.info(f"  Processing {i}/{len(split_data)}...")

                    # Generate prompt
                    example = generate_single_prompt(
                        orchestrator,
                        prompt_builder,
                        DataDeduplicator(),  # Fresh deduplicator per example
                        ticker,
                        thesis_date
                    )

                    if example:
                        # Write to file
                        f.write(json.dumps(example) + '\n')
                        successful += 1
                    else:
                        failed += 1

            results[split_name] = {
                "file": str(output_file),
                "total": len(split_data),
                "successful": successful,
                "failed": failed
            }

            logger.info(f"✅ Wrote {successful} examples to {output_file}")
            logger.info("")

        # Print summary
        logger.info("=" * 80)
        logger.info("DATA QUALITY SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Total processed: {total}")
        logger.info(f"Successful: {results['train']['successful'] + results['dev']['successful']}")
        logger.info(f"Errors: {results['train']['failed'] + results['dev']['failed']}")
        logger.info("")

        logger.info("Data Coverage:")
        # Calculate coverage metrics
        total_successful = results['train']['successful'] + results['dev']['successful']
        logger.info(f"  Total examples: {total_successful}/{total}")
        logger.info("")

        logger.info("Files created:")
        logger.info(f"  Training: {results['train']['file']}")
        logger.info(f"  Dev: {results['dev']['file']}")
        logger.info("")

        return results

    finally:
        session.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate RLVR training datasets")
    parser.add_argument("--output-dir", type=str,
                       default="/opt/Fireworks-Charlie/storage/rlvr_datasets",
                       help="Output directory (default: from config)")
    parser.add_argument("--start-date", type=str,
                       help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str,
                       help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--train-ratio", type=float, default=0.95,
                       help="Train split ratio (default: 0.95)")

    args = parser.parse_args()

    # Build split ratios
    split_ratios = {
        "train": args.train_ratio,
        "dev": 1.0 - args.train_ratio
    }

    # Generate training data
    results = generate_training_data(
        output_dir=args.output_dir,
        split_ratios=split_ratios,
        start_date=args.start_date,
        end_date=args.end_date
    )

    # Print final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Validate data quality: python scripts/validate_training_data.py")
    logger.info("  2. Analyze data: python scripts/analyze_data_quality.py")
    logger.info("  3. Upload to Fireworks for training")


if __name__ == "__main__":
    main()
