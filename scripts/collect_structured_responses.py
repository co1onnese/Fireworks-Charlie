#!/usr/bin/env python3
"""
Structured Response Collection Script for Base Model

Generates structured prompts using StructuredPromptBuilder and collects responses
from DeepSeek-V3-Terminus base model via Fireworks AI API. Stores responses in
database with validation.

Usage:
    python scripts/collect_structured_responses.py \
        --tickers AAPL,MSFT,NVDA \
        --start-date 2024-01-01 \
        --end-date 2024-01-31 \
        --output-dir storage/structured_responses

    # For all tickers in database
    python scripts/collect_structured_responses.py \
        --all-tickers
"""
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from data_collection.database_manager import DatabaseManager, Ticker, ThesisGeneration
from orchestration.config_manager import Config
from orchestration.market_calendar import MarketCalendar
from thesis_generation.structured_prompt_builder import StructuredPromptBuilder
from thesis_generation.llm_factory import create_llm_client
from rlvr.response_adapter import validate_structured_response

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "structured_response_collection.log")
        ]
    )


def get_all_tickers(db_session: Session) -> List[Ticker]:
    """Get all active tickers from database."""
    return db_session.query(Ticker).filter_by(is_active=True).all()


def get_or_create_thesis(
    db_session: Session,
    ticker_id: int,
    as_of_date: date,
    model_name: str
) -> ThesisGeneration:
    """Get existing thesis or create new record."""
    thesis = db_session.query(ThesisGeneration).filter_by(
        ticker_id=ticker_id,
        as_of_date=as_of_date,
        model_name=model_name
    ).first()

    if thesis:
        return thesis

    thesis = ThesisGeneration(
        ticker_id=ticker_id,
        as_of_date=as_of_date,
        model_name=model_name,
        status="pending"
    )
    db_session.add(thesis)
    db_session.commit()
    db_session.refresh(thesis)
    return thesis


def generate_and_save_response(
    db_manager: DatabaseManager,
    prompt_builder: StructuredPromptBuilder,
    llm_client: Any,
    ticker: str,
    as_of_date: date,
    output_dir: Path,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """Generate structured response and save to database."""
    session = db_manager.get_session()

    try:
        # Check if we already have a response
        ticker_obj = session.query(Ticker).filter_by(symbol=ticker).first()
        if not ticker_obj:
            return {"status": "failed", "error": f"Ticker {ticker} not found"}

        existing = session.query(ThesisGeneration).filter_by(
            ticker_id=ticker_obj.ticker_id,
            as_of_date=as_of_date,
            status="completed"
        ).first()

        if existing and validate_structured_response(existing.assistant_response)[0]:
            logger.info(f"Valid response exists for {ticker} on {as_of_date}, skipping")
            return {"status": "skipped", "reason": "already_exists"}

        # Build prompt
        logger.info(f"Building prompt for {ticker} on {as_of_date}")
        system_prompt, user_prompt = prompt_builder.build_structured_prompt(ticker, as_of_date)

        # Generate response
        logger.info(f"Generating response for {ticker} on {as_of_date}")
        start_time = datetime.now()

        response = llm_client.generate_thesis(
            user_prompt,
            ticker,
            as_of_date,
            temperature=temperature,
            response_format=None  # Let the model respond naturally
        )

        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Validate response structure
        if not response.get("assistant_response"):
            logger.error("No assistant response from LLM")
            return {"status": "failed", "error": "Empty response"}

        try:
            response_data = response["assistant_response"]

            # Validate structure
            is_valid, errors = validate_structured_response(response_data)
            if not is_valid:
                logger.error(f"Invalid response structure: {errors}")
                logger.error(f"Raw response: {response_data}")

                # Try to fix common issues or mark as invalid
                return {
                    "status": "failed",
                    "error": f"Validation failed: {errors}"
                }

            # Save to database
            model_name = getattr(llm_client, 'model_name', getattr(llm_client, 'model', 'unknown'))
            thesis = get_or_create_thesis(
                session,
                ticker_obj.ticker_id,
                as_of_date,
                model_name
            )

            thesis.system_prompt = system_prompt
            thesis.user_prompt = user_prompt
            thesis.assistant_response = response_data
            thesis.predicted_action = response.get("action", "hold")
            thesis.reasoning = response.get("reasoning", "")
            thesis.support = response.get("support", "")
            thesis.model_name = model_name
            thesis.temperature = temperature
            thesis.tokens_used = response.get("tokens_used", 0)
            thesis.generation_time_ms = generation_time_ms
            thesis.status = "completed"

            session.commit()

            # Save to file for backup
            if output_dir:
                output_file = output_dir / f"{ticker}_{as_of_date}.json"
                import json
                with open(output_file, 'w') as f:
                    json.dump({
                        "ticker": ticker,
                        "date": str(as_of_date),
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "response": response_data,
                        "generated_at": datetime.now().isoformat(),
                        "model": model_name
                    }, f, indent=2, default=str)

            logger.info(
                f"Successfully generated response for {ticker} on {as_of_date} "
                f"({generation_time_ms}ms, {response.get('tokens_used', 0)} tokens)"
            )

            return {
                "status": "success",
                "ticker": ticker,
                "date": as_of_date,
                "generation_time_ms": generation_time_ms,
                "tokens_used": response.get("tokens_used", 0),
                "recommendation": response_data.get("conclusion", {}).get("recommendation")
            }

        except Exception as e:
            logger.error(f"Error processing response: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

    finally:
        session.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Collect structured responses from base model")
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers (e.g., AAPL,MSFT,NVDA)"
    )
    parser.add_argument(
        "--all-tickers",
        action="store_true",
        help="Use all tickers from database"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2024-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2024-01-31",
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="storage/structured_responses",
        help="Output directory for backup files"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="LLM temperature (0.0-1.0)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of responses to generate (for testing)"
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.log_level)

    config = Config()
    db_manager = DatabaseManager(config.DB_URL)
    market_calendar = MarketCalendar()
    prompt_builder = StructuredPromptBuilder(db_manager, market_calendar)
    llm_client = create_llm_client(config.LLM_PROVIDER, config)

    # Determine tickers
    if args.all_tickers:
        session = db_manager.get_session()
        tickers = [t.symbol for t in get_all_tickers(session)]
        session.close()
        logger.info(f"Found {len(tickers)} active tickers")
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        logger.error("Must specify --tickers or --all-tickers")
        sys.exit(1)

    # Parse dates
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)

    # Get all trading days in range
    trading_days = market_calendar.get_trading_days(start_date, end_date)
    logger.info(f"Processing {len(trading_days)} trading days from {start_date} to {end_date}")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate responses
    stats = {
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "total_tokens": 0,
        "total_time_ms": 0
    }

    total_tasks = len(tickers) * len(trading_days)
    logger.info(f"Total tasks: {total_tasks} ({len(tickers)} tickers × {len(trading_days)} days)")

    if args.limit:
        logger.info(f"Limiting to {args.limit} responses")

    count = 0
    try:
        for ticker in tickers:
            for as_of_date in trading_days:
                if args.limit and count >= args.limit:
                    logger.info("Reached limit, stopping")
                    break

                count += 1
                logger.info(f"[{count}/{total_tasks}] Processing {ticker} on {as_of_date}")

                result = generate_and_save_response(
                    db_manager=db_manager,
                    prompt_builder=prompt_builder,
                    llm_client=llm_client,
                    ticker=ticker,
                    as_of_date=as_of_date,
                    output_dir=output_dir,
                    temperature=args.temperature
                )

                if result["status"] == "success":
                    stats["success"] += 1
                    stats["total_tokens"] += result.get("tokens_used", 0)
                    stats["total_time_ms"] += result.get("generation_time_ms", 0)
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user, stopping...")

    # Print summary
    logger.info("=" * 60)
    logger.info("COLLECTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Success: {stats['success']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Total tokens: {stats['total_tokens']}")
    logger.info(f"Total time: {stats['total_time_ms']}ms")
    logger.info(f"Avg time/response: {stats['total_time_ms'] / max(stats['success'], 1):.0f}ms")

    if stats['success'] > 0:
        logger.info(f"Avg tokens/response: {stats['total_tokens'] / stats['success']:.0f}")

    # Save summary to file
    summary_file = output_dir / "collection_summary.json"
    summary = {
        "generated_at": datetime.now().isoformat(),
        "tickers": tickers,
        "date_range": {"start": str(start_date), "end": str(end_date)},
        "stats": stats,
        "model": getattr(llm_client, 'model_name', getattr(llm_client, 'model', 'unknown')),
        "temperature": args.temperature
    }
    with open(summary_file, 'w') as f:
        import json
        json.dump(summary, f, indent=2, default=str)

    logger.info(f"Summary saved to {summary_file}")

    if stats['failed'] > 0:
        sys.exit(1)
    else:
        logger.info("✅ All responses generated successfully")


if __name__ == "__main__":
    main()
