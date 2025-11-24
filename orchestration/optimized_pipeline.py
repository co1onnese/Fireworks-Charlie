#!/usr/bin/env python3
"""
Optimized pipeline that skips data collection and goes straight to prompt generation.
This uses existing database data to regenerate prompts efficiently.
"""
import sys
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import config
from orchestration.market_calendar import MarketCalendar
from orchestration.checkpoint_manager import CheckpointManager
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator
from thesis_generation.context_compressor import ContextCompressor
from thesis_generation.llm_factory import create_llm_client
from rlvr.position_creator import create_position_after_thesis
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(
    name="fireworks_charlie_optimized",
    log_file=config.LOG_FILE.replace(".log", "_optimized.log"),
    log_level=config.LOG_LEVEL
)

class OptimizedFireworksCharliePipeline:
    """Optimized pipeline that skips data collection and uses existing data."""

    def __init__(self):
        """Initialize pipeline components"""
        # Log configuration
        config.log_configuration(logger)

        # Initialize components
        self.market_calendar = MarketCalendar(config.MARKET_CALENDAR)
        self.checkpoint_manager = CheckpointManager(config.CHECKPOINT_DIR)
        self.data_orchestrator = DataOrchestrator(config)

        # Initialize shared database manager (reuse across all operations)
        from data_collection.database_manager import DatabaseManager
        self.db_manager = DatabaseManager(config.DB_URL)
        logger.info("Shared DatabaseManager initialized for optimized pipeline")

        # Initialize context compression
        self.context_compressor = ContextCompressor(
            max_days_recent=config.MAX_DAYS_RECENT,
            max_days_medium=config.MAX_DAYS_MEDIUM,
            max_days_historical=config.MAX_DAYS_HISTORICAL
        )

        # Initialize LLM client using factory pattern
        provider = config.LLM_PROVIDER
        api_key_available = False

        if provider == "deepseek":
            api_key_available = bool(config.DEEPSEEK_API_KEY)
            key_name = "DEEPSEEK_API_KEY"
        elif provider == "fireworks":
            api_key_available = bool(config.FIREWORKS_API_KEY)
            key_name = "FIREWORKS_API_KEY"
        else:
            logger.error(f"Unknown LLM provider: {provider}")
            self.llm_client = None
            api_key_available = False

        if api_key_available:
            try:
                logger.info(f"Initializing LLM client with provider: {provider}")
                self.llm_client = create_llm_client(provider, config)
                logger.info(f"✓ LLM client initialized (connection test disabled)")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}")
                self.llm_client = None
        else:
            logger.warning(f"No {key_name} provided - thesis generation disabled")
            self.llm_client = None

        logger.info("OptimizedFireworksCharliePipeline initialized successfully")

    def run(self,
            tickers: List[str] = None,
            start_date: str = None,
            end_date: str = None,
            resume: bool = True) -> Dict[str, Any]:
        """
        Run the optimized pipeline (skips data collection)

        Args:
            tickers: List of tickers (uses config if not provided)
            start_date: Start date YYYY-MM-DD (uses config if not provided)
            end_date: End date YYYY-MM-DD (uses config if not provided)
            resume: Whether to resume from checkpoints

        Returns:
            Pipeline execution summary
        """
        # Use provided values or fall back to config
        tickers = tickers or config.TICKERS
        start_date = date.fromisoformat(start_date) if start_date else date.fromisoformat(config.START_DATE)
        end_date = date.fromisoformat(end_date) if end_date else date.fromisoformat(config.END_DATE)

        logger.info(f"Starting OPTIMIZED pipeline for {len(tickers)} tickers from {start_date} to {end_date}")
        logger.info("⚠️  SKIPPING DATA COLLECTION PHASE - Using existing database data")

        # Get trading days
        trading_days = self.market_calendar.get_trading_days(start_date, end_date)
        logger.info(f"Found {len(trading_days)} trading days to process")

        # Skip data collection phase entirely
        logger.info("Phase 1: Data Collection - SKIPPED (using existing data)")
        data_collection_results = {
            "status": "skipped",
            "reason": "using_existing_data",
            "tickers": {ticker: {"status": "skipped", "reason": "using_existing_data"} for ticker in tickers}
        }

        # Process each ticker for thesis generation
        logger.info("Phase 2: Thesis Generation")

        # Create executor with 1 worker per ticker for true parallelization
        num_workers = len(tickers)
        logger.info(f"Creating thread pool with {num_workers} workers (1 per ticker)")

        results = {
            "data_collection": data_collection_results,
            "thesis_generation": {},
            "summary": {
                "tickers_processed": 0,
                "total_theses": 0,
                "failures": 0
            }
        }

        # Process all tickers in parallel with dynamic worker allocation
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all tickers for parallel processing
            futures = []
            for ticker in tickers:
                future = executor.submit(
                    self._process_ticker,
                    ticker,
                    trading_days,
                    resume
                )
                futures.append((ticker, future))

            # Collect results
            for ticker, future in futures:
                try:
                    ticker_result = future.result()
                    results["thesis_generation"][ticker] = ticker_result

                    if ticker_result["status"] == "success":
                        results["summary"]["tickers_processed"] += 1
                        results["summary"]["total_theses"] += ticker_result["theses_generated"]
                    else:
                        results["summary"]["failures"] += 1

                except Exception as e:
                    logger.error(f"Failed to process {ticker}: {e}")
                    results["thesis_generation"][ticker] = {
                        "status": "error",
                        "error": str(e)
                    }
                    results["summary"]["failures"] += 1

        logger.info(
            f"Optimized pipeline completed: {results['summary']['tickers_processed']} tickers, "
            f"{results['summary']['total_theses']} theses, "
            f"{results['summary']['failures']} failures"
        )

        return results

    def _process_ticker(self,
                       ticker: str,
                       trading_days: List[date],
                       resume: bool) -> Dict[str, Any]:
        """
        Process a single ticker through all trading days using existing data

        Args:
            ticker: Stock ticker symbol
            trading_days: List of trading days to process
            resume: Whether to resume from checkpoint

        Returns:
            Processing results for the ticker
        """
        logger.info(f"Processing ticker: {ticker}")

        # Initialize components for this ticker
        deduplicator = DataDeduplicator()
        prompt_builder = CumulativePromptBuilder(deduplicator)

        # Check for existing checkpoint
        start_from_date = None
        cumulative_data = []
        already_complete = False

        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint(ticker)
            if checkpoint:
                start_from_date = date.fromisoformat(checkpoint["last_processed_date"])
                cumulative_data = checkpoint["cumulative_data"]
                logger.info(f"Resuming {ticker} from {start_from_date}")

                # Check if already fully processed
                if trading_days and start_from_date >= trading_days[-1]:
                    already_complete = True
                    logger.info(f"{ticker} already fully processed through {start_from_date}")

        # Track results
        theses_generated = 0
        errors = []

        # Process each trading day
        for trading_day in trading_days:
            # Skip if already processed
            if start_from_date and trading_day <= start_from_date:
                continue

            try:
                # Get data for this day FROM EXISTING DATABASE (no API calls)
                day_data = self.data_orchestrator.get_data_for_date(ticker, trading_day)

                # Ensure day_data is a dict
                if not isinstance(day_data, dict):
                    logger.error(f"get_data_for_date returned non-dict for {ticker} on {trading_day}: {type(day_data)}")
                    errors.append({
                        "date": trading_day,
                        "error": f"Invalid return type: {type(day_data)}"
                    })
                    continue

                if "error" in day_data:
                    logger.error(f"Failed to get data for {ticker} on {trading_day}: {day_data.get('error', 'Unknown error')}")
                    errors.append({
                        "date": trading_day,
                        "error": day_data.get("error", "Unknown error")
                    })
                    continue

                # Add to cumulative data
                cumulative_data.append(day_data)

                # Apply context compression if enabled
                if config.ENABLE_AGGRESSIVE_COMPRESSION:
                    compressed_data = self.context_compressor.compress_cumulative_data(
                        ticker=ticker,
                        cumulative_data=cumulative_data,
                        current_date=trading_day
                    )
                else:
                    compressed_data = cumulative_data

                # Build RLVR prompts (system and user)
                logger.debug(f"Building RLVR prompts for {ticker} on {trading_day}")
                system_prompt, user_prompt = prompt_builder.build_cumulative_prompt_messages(
                    ticker,
                    compressed_data,
                    response_format="json"
                )

                # Enhanced token monitoring
                estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4

                # Log compression effectiveness
                if config.ENABLE_AGGRESSIVE_COMPRESSION:
                    original_size = len(str(cumulative_data)) // 4
                    compressed_size = estimated_tokens
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    logger.info(
                        f"{ticker} on {trading_day}: "
                        f"Compressed {len(cumulative_data)} days → {len(compressed_data)} items "
                        f"({original_size:,} → {compressed_size:,} tokens, {compression_ratio:.1f}% reduction)"
                    )

                if estimated_tokens > config.TOKEN_BUDGET:
                    logger.error(
                        f"Prompt for {ticker} on {trading_day} exceeds token budget "
                        f"({estimated_tokens} > {config.TOKEN_BUDGET}) - SKIPPING"
                    )
                    continue
                elif estimated_tokens > config.TOKEN_WARNING_THRESHOLD:
                    logger.warning(
                        f"Prompt for {ticker} on {trading_day} approaching token limit "
                        f"({estimated_tokens} > {config.TOKEN_WARNING_THRESHOLD})"
                    )
                else:
                    logger.info(f"Token usage for {ticker} on {trading_day}: {estimated_tokens:,} tokens")

                # Generate thesis using Fireworks client
                if self.llm_client:
                    logger.info(f"Generating thesis for {ticker} on {trading_day}")

                    # Combine system and user prompts
                    combined_prompt = f"{system_prompt}\n\n{user_prompt}"

                    try:
                        thesis_result = self.llm_client.generate_thesis(
                            prompt=combined_prompt,
                            ticker=ticker,
                            as_of_date=trading_day.isoformat()
                        )
                    except Exception as llm_exception:
                        logger.error(f"Exception calling generate_thesis for {ticker} on {trading_day}: {llm_exception}")
                        errors.append({
                            "date": trading_day,
                            "error": f"LLM exception: {str(llm_exception)}"
                        })
                        continue

                    # Ensure thesis_result is a dict
                    if not isinstance(thesis_result, dict):
                        logger.error(f"generate_thesis returned non-dict for {ticker} on {trading_day}: {type(thesis_result)}, value: {str(thesis_result)[:200]}")
                        errors.append({
                            "date": trading_day,
                            "error": f"LLM returned invalid type: {type(thesis_result)}"
                        })
                        continue

                    # Ensure status key exists
                    if "status" not in thesis_result:
                        logger.error(f"generate_thesis returned dict without 'status' for {ticker} on {trading_day}: {list(thesis_result.keys())}")
                        errors.append({
                            "date": trading_day,
                            "error": "LLM returned dict without 'status' key"
                        })
                        continue

                    if thesis_result.get("status") == "success":
                        # Save to database and checkpoint
                        session = None
                        try:
                            # Store in database using shared db_manager
                            session = self.db_manager.get_session()

                            # Insert thesis generation
                            from data_collection.database_manager import ThesisGeneration
                            # Convert date objects to strings for JSON serialization
                            import json

                            # Helper function to recursively convert date objects to ISO strings
                            def convert_dates(obj):
                                if isinstance(obj, dict):
                                    return {k: convert_dates(v) for k, v in obj.items()}
                                elif isinstance(obj, list):
                                    return [convert_dates(item) for item in obj]
                                elif hasattr(obj, 'isoformat'):  # date/datetime objects
                                    return obj.isoformat()
                                else:
                                    return obj

                            # Convert assistant_response for database (always apply conversion)
                            assistant_response = thesis_result.get("assistant_response")
                            if assistant_response:
                                # Ensure assistant_response is a dict before processing
                                if not isinstance(assistant_response, dict):
                                    logger.warning(f"assistant_response is not a dict for {ticker} on {trading_day}: {type(assistant_response)}, creating fallback")
                                    assistant_response = {
                                        "reasoning": thesis_result.get("reasoning", ""),
                                        "action": thesis_result.get("action", "hold"),
                                        "support": thesis_result.get("support", "")
                                    }
                                else:
                                    assistant_response = convert_dates(assistant_response)
                            else:
                                # Fallback if assistant_response is missing
                                assistant_response = {
                                    "reasoning": thesis_result.get("reasoning", ""),
                                    "action": thesis_result.get("action", "hold"),
                                    "support": thesis_result.get("support", "")
                                }

                            # Get ticker_id
                            ticker_db_id = self.db_manager.get_ticker_id(session, ticker)

                            # Check if thesis already exists for this ticker and date
                            # This prevents duplicate key violations in parallel processing
                            from sqlalchemy import select
                            existing_thesis = session.execute(
                                select(ThesisGeneration).where(
                                    ThesisGeneration.ticker_id == ticker_db_id,
                                    ThesisGeneration.as_of_date == trading_day
                                )
                            ).scalar_one_or_none()

                            if existing_thesis:
                                # Check if assistant_response is a placeholder (cleared value)
                                import json
                                is_placeholder = False
                                if existing_thesis.assistant_response:
                                    try:
                                        if isinstance(existing_thesis.assistant_response, str):
                                            response_data = json.loads(existing_thesis.assistant_response)
                                        else:
                                            response_data = existing_thesis.assistant_response

                                        # Check if it's the placeholder value
                                        if isinstance(response_data, dict) and response_data.get("cleared") is True:
                                            is_placeholder = True
                                    except (json.JSONDecodeError, TypeError, AttributeError):
                                        pass

                                # If thesis exists and has valid assistant_response (not placeholder), skip
                                if existing_thesis.assistant_response is not None and not is_placeholder:
                                    logger.info(
                                        f"Thesis for {ticker} on {trading_day} already exists with response (ID: {existing_thesis.thesis_id}) - skipping"
                                    )
                                    # Skip to next iteration
                                    continue
                                else:
                                    # Thesis exists but assistant_response is placeholder or NULL - regenerate it
                                    logger.info(
                                        f"Thesis for {ticker} on {trading_day} exists but needs regeneration (ID: {existing_thesis.thesis_id}, placeholder={is_placeholder}) - regenerating"
                                    )
                                    thesis_gen = existing_thesis
                                    # Update existing thesis with new prompts and response
                                    thesis_gen.system_prompt = system_prompt
                                    thesis_gen.user_prompt = user_prompt
                                    thesis_gen.assistant_response = assistant_response
                                    thesis_gen.predicted_action = thesis_result.get("action", "hold")
                                    thesis_gen.reasoning = thesis_result.get("reasoning")
                                    thesis_gen.support = thesis_result.get("support")
                                    thesis_gen.model_name = config.MODEL_NAME
                                    thesis_gen.status = 'success'
                                    thesis_gen.error_message = None
                                    thesis_gen.generated_at = datetime.utcnow()
                                    session.commit()
                            else:
                                # Insert new thesis generation
                                thesis_gen = ThesisGeneration(
                                    ticker_id=ticker_db_id,
                                    as_of_date=trading_day,
                                    system_prompt=system_prompt,
                                    user_prompt=user_prompt,
                                    assistant_response=assistant_response,
                                    predicted_action=thesis_result.get("action", "hold"),
                                    reasoning=thesis_result.get("reasoning"),
                                    support=thesis_result.get("support"),
                                    model_name=config.MODEL_NAME,
                                    generated_at=datetime.utcnow()
                                )
                                session.add(thesis_gen)
                                session.commit()

                            # ✅ DATABASE COMMIT SUCCESSFUL - Now safe to update state

                            # Create position record for this thesis
                            thesis_id = thesis_gen.thesis_id

                            position_id = create_position_after_thesis(
                                db_session=session,
                                thesis_id=thesis_id,
                                ticker_id=ticker_db_id,
                                entry_date=trading_day,
                                predicted_action=thesis_result.get("action", "hold")
                            )

                            if position_id:
                                logger.debug(f"Created position {position_id} for thesis {thesis_id}")
                            else:
                                logger.debug(
                                    f"Position not created for thesis {thesis_id} "
                                    f"(likely insufficient future data)"
                                )

                            # ✅ Increment counter ONLY after successful database commit
                            theses_generated += 1

                            logger.info(
                                f"✅ Successfully saved thesis for {ticker} on {trading_day}: "
                                f"{thesis_result['action']} (thesis_id: {thesis_id})"
                            )

                            # ✅ Save checkpoint ONLY after successful database save
                            # This ensures we never mark a date as processed if the save failed
                            self.checkpoint_manager.save_rlvr_checkpoint(
                                ticker=ticker,
                                processed_date=trading_day,
                                cumulative_data=cumulative_data,
                                metadata={
                                    "theses_generated": theses_generated,
                                    "dedup_stats": deduplicator.get_deduplication_stats()
                                }
                            )

                            # Add prompt to checkpoint history (also convert dates)
                            checkpoint_assistant_response = thesis_result.get("assistant_response")
                            if checkpoint_assistant_response:
                                checkpoint_assistant_response = convert_dates(checkpoint_assistant_response)

                            self.checkpoint_manager.add_prompt_to_checkpoint(
                                ticker=ticker,
                                date=trading_day.isoformat(),
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                assistant_response=checkpoint_assistant_response
                            )

                        except Exception as e:
                            # ❌ DATABASE SAVE FAILED - Do NOT update checkpoint or counter
                            logger.error(f"❌ FAILED to save thesis for {ticker} on {trading_day}: {e}")
                            logger.error(f"   Error type: {type(e).__name__}")
                            logger.debug(traceback.format_exc())

                            if session:
                                session.rollback()
                                logger.warning(f"   Rolled back database transaction for {ticker} on {trading_day}")

                            errors.append({
                                "date": trading_day.isoformat(),
                                "error": f"Database save failed: {str(e)}"
                            })

                            # ❌ DO NOT save checkpoint when database save fails
                            # ❌ DO NOT increment theses_generated counter
                            # This ensures the date will be retried on next run

                        finally:
                            if session:
                                session.close()
                    else:
                        # LLM generation failed
                        error_msg = "Unknown LLM error"
                        if isinstance(thesis_result, dict):
                            error_msg = thesis_result.get("error", "Unknown LLM error")
                        else:
                            error_msg = f"LLM returned invalid response: {type(thesis_result)}"
                        logger.error(f"❌ LLM generation failed for {ticker} on {trading_day}: {error_msg}")
                        errors.append({
                            "date": trading_day,
                            "error": error_msg
                        })
                else:
                    # No LLM client available
                    error_msg = "No LLM client configured"
                    logger.error(f"❌ {error_msg}")
                    errors.append({
                        "date": trading_day,
                        "error": error_msg
                    })

            except Exception as e:
                # Get error message safely
                error_msg = str(e)
                error_type = type(e).__name__
                error_traceback = traceback.format_exc()

                logger.error(f"Error processing {ticker} on {trading_day}: {error_type}: {error_msg}")
                logger.error(f"Full traceback:\n{error_traceback}")

                errors.append({
                    "date": trading_day,
                    "error": f"{error_type}: {error_msg}"
                })

        # Get final statistics from database
        session = None
        try:
            session = self.db_manager.get_session()

            # Count theses for this ticker
            from data_collection.database_manager import ThesisGeneration
            from sqlalchemy import func
            total_theses = session.query(func.count(ThesisGeneration.thesis_id)).filter(
                ThesisGeneration.ticker_id == self.db_manager.get_ticker_id(session, ticker)
            ).scalar() or 0

            # Get latest thesis
            latest_thesis = session.query(ThesisGeneration).filter(
                ThesisGeneration.ticker_id == self.db_manager.get_ticker_id(session, ticker)
            ).order_by(ThesisGeneration.generated_at.desc()).first()

        except Exception as e:
            logger.error(f"Failed to get thesis statistics: {e}")
            total_theses = 0
            latest_thesis = None
        finally:
            if session:
                session.close()

        # Determine status
        if already_complete:
            # Already fully processed from a previous run
            status = "success"
        elif theses_generated > 0:
            # Successfully generated new theses in this run
            status = "success"
        elif total_theses > 0 and len(errors) == 0:
            # No new theses but has existing theses and no errors (edge case)
            status = "success"
        else:
            # Failed to generate any theses
            status = "error"

        # Log comprehensive error summary if there were failures
        if len(errors) > 0:
            logger.error(f"⚠️  {ticker}: {len(errors)} failures during processing!")
            logger.error(f"   Successfully saved: {theses_generated} theses")
            logger.error(f"   Failed: {len(errors)} dates")
            logger.error("   First 5 failures:")
            for error in errors[:5]:
                logger.error(f"      • {error['date']}: {error['error']}")
            if len(errors) > 5:
                logger.error(f"   ... and {len(errors) - 5} more failures")

        return {
            "status": status,
            "ticker": ticker,
            "theses_generated": theses_generated,
            "total_theses": total_theses,
            "latest_thesis": latest_thesis,
            "errors": errors,
            "trading_days_processed": len([d for d in trading_days if not start_from_date or d > start_from_date]),
            "already_complete": already_complete
        }


def main():
    """Main entry point for optimized pipeline."""
    pipeline = OptimizedFireworksCharliePipeline()

    try:
        results = pipeline.run()
        logger.info("Optimized pipeline completed successfully!")
        return results
    except Exception as e:
        logger.error(f"Optimized pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()