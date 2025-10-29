"""
Main pipeline orchestrator for Fireworks-Charlie
Coordinates data collection, prompt building, and thesis generation
"""
import logging
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import traceback

from orchestration.config_manager import config
from orchestration.market_calendar import MarketCalendar
from orchestration.checkpoint_manager import CheckpointManager
from data_collection.data_orchestrator import DataOrchestrator
from thesis_generation.prompt_builder import CumulativePromptBuilder
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator
from thesis_generation.fireworks_client import FireworksDeepSeekClient
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(
    name="fireworks_charlie",
    log_file=config.LOG_FILE,
    log_level=config.LOG_LEVEL
)

class FireworksCharliePipeline:
    """Main pipeline for cumulative thesis generation"""
    
    def __init__(self):
        """Initialize pipeline components"""
        # Log configuration
        config.log_configuration(logger)
        
        # Initialize components
        self.market_calendar = MarketCalendar(config.MARKET_CALENDAR)
        self.checkpoint_manager = CheckpointManager(config.CHECKPOINT_DIR)
        self.data_orchestrator = DataOrchestrator(config)
        
        # Initialize Fireworks LLM client
        if config.FIREWORKS_API_KEY:
            self.llm_client = FireworksDeepSeekClient(
                api_key=config.FIREWORKS_API_KEY,
                model_name=config.MODEL_NAME,
                model_mode=config.MODEL_MODE,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE
            )
            # Test connection
            if not self.llm_client.test_connection():
                logger.warning("Fireworks API connection test failed")
        else:
            logger.warning("No Fireworks API key provided - thesis generation disabled")
            self.llm_client = None
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=config.PARALLEL_WORKERS)
        
        logger.info("FireworksCharliePipeline initialized successfully")
    
    def run(self, 
            tickers: List[str] = None,
            start_date: str = None,
            end_date: str = None,
            resume: bool = True) -> Dict[str, Any]:
        """
        Run the full pipeline
        
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
        
        logger.info(f"Starting pipeline for {len(tickers)} tickers from {start_date} to {end_date}")
        
        # Get trading days
        trading_days = self.market_calendar.get_trading_days(start_date, end_date)
        logger.info(f"Found {len(trading_days)} trading days to process")
        
        # First, ensure we have collected all necessary data
        logger.info("Phase 1: Data Collection")
        data_collection_results = self._run_data_collection(tickers, start_date, end_date)
        
        # Then, process each ticker for thesis generation
        logger.info("Phase 2: Thesis Generation")
        
        # Submit all tickers for parallel processing
        futures = []
        for ticker in tickers:
            future = self.executor.submit(
                self._process_ticker,
                ticker,
                trading_days,
                resume
            )
            futures.append((ticker, future))
        
        # Collect results
        results = {
            "data_collection": data_collection_results,
            "thesis_generation": {},
            "summary": {
                "tickers_processed": 0,
                "total_theses": 0,
                "failures": 0
            }
        }
        
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
            f"Pipeline completed: {results['summary']['tickers_processed']} tickers, "
            f"{results['summary']['total_theses']} theses, "
            f"{results['summary']['failures']} failures"
        )
        
        return results
    
    def _run_data_collection(self, 
                           tickers: List[str], 
                           start_date: date, 
                           end_date: date) -> Dict[str, Any]:
        """Run data collection phase"""
        results = {
            "tickers": {},
            "macro": {},
            "feature_engineering": {}
        }
        
        # Collect data for each ticker
        for ticker in tickers:
            logger.info(f"Collecting data for {ticker}")
            result = self.data_orchestrator.collect_data_for_ticker(
                ticker, start_date, end_date
            )
            results["tickers"][ticker] = result
        
        # Collect macro data
        logger.info("Collecting macroeconomic data")
        results["macro"] = self.data_orchestrator.collect_macro_data(
            start_date, end_date
        )
        
        # Run feature engineering
        logger.info("Running feature engineering")
        results["feature_engineering"] = self.data_orchestrator.run_feature_engineering(
            tickers, start_date, end_date
        )
        
        return results
    
    def _process_ticker(self, 
                       ticker: str, 
                       trading_days: List[date],
                       resume: bool) -> Dict[str, Any]:
        """
        Process a single ticker through all trading days
        
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
                # Get data for this day
                day_data = self.data_orchestrator.get_data_for_date(ticker, trading_day)
                
                if "error" in day_data:
                    logger.error(f"Failed to get data for {ticker} on {trading_day}: {day_data['error']}")
                    errors.append({
                        "date": trading_day,
                        "error": day_data["error"]
                    })
                    continue
                
                # Add to cumulative data
                cumulative_data.append(day_data)
                
                # Build RLVR prompts (system and user)
                logger.debug(f"Building RLVR prompts for {ticker} on {trading_day}")
                system_prompt, user_prompt = prompt_builder.build_cumulative_prompt_messages(
                    ticker,
                    cumulative_data,
                    response_format="json"
                )
                
                # Enhanced token monitoring
                estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
                
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
                    
                    thesis_result = self.llm_client.generate_thesis(
                        prompt=combined_prompt,
                        ticker=ticker,
                        as_of_date=trading_day.isoformat()
                    )
                    
                    if thesis_result["status"] == "success":
                        # Save to database and checkpoint
                        try:
                            # Store in database
                            from data_collection.database_manager import DatabaseManager
                            db_manager = DatabaseManager(config.DB_URL)
                            session = db_manager.get_session()

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
                                assistant_response = convert_dates(assistant_response)
                            else:
                                # Fallback if assistant_response is missing
                                assistant_response = {
                                    "reasoning": thesis_result.get("reasoning", ""),
                                    "action": thesis_result.get("action", "hold"),
                                    "support": thesis_result.get("support", "")
                                }

                            thesis_gen = ThesisGeneration(
                                ticker_id=db_manager.get_ticker_id(session, ticker),
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

                            # Add prompt to checkpoint (also convert dates)
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

                            session.close()

                            theses_generated += 1
                            logger.info(
                                f"Generated thesis for {ticker} on {trading_day}: "
                                f"{thesis_result['action']}"
                            )

                        except Exception as e:
                            logger.error(f"Failed to save thesis to database: {e}")
                            logger.debug(traceback.format_exc())
                            errors.append({
                                "date": trading_day.isoformat(),  # Convert date to string!
                                "error": f"Database save failed: {str(e)}"
                            })
                    else:
                        # LLM generation failed
                        error_msg = thesis_result.get("error", "Unknown LLM error")
                        logger.error(f"LLM generation failed: {error_msg}")
                        errors.append({
                            "date": trading_day,
                            "error": error_msg
                        })
                else:
                    # No LLM client available
                    error_msg = "No LLM client configured"
                    logger.error(error_msg)
                    errors.append({
                        "date": trading_day,
                        "error": error_msg
                    })
                
                # Save checkpoint after each successful day
                self.checkpoint_manager.save_rlvr_checkpoint(
                    ticker=ticker,
                    processed_date=trading_day,
                    cumulative_data=cumulative_data,
                    metadata={
                        "theses_generated": theses_generated,
                        "dedup_stats": deduplicator.get_deduplication_stats()
                    }
                )
                
            except Exception as e:
                logger.error(f"Error processing {ticker} on {trading_day}: {e}")
                logger.debug(traceback.format_exc())
                
                errors.append({
                    "date": trading_day,
                    "error": str(e)
                })
        
        # Get final statistics from database
        try:
            from data_collection.database_manager import DatabaseManager
            db_manager = DatabaseManager(config.DB_URL)
            session = db_manager.get_session()
            
            # Count theses for this ticker
            from data_collection.database_manager import ThesisGeneration
            from sqlalchemy import func
            total_theses = session.query(func.count(ThesisGeneration.thesis_id)).filter(
                ThesisGeneration.ticker_id == db_manager.get_ticker_id(session, ticker)
            ).scalar() or 0
            
            # Get latest thesis
            latest_thesis = session.query(ThesisGeneration).filter(
                ThesisGeneration.ticker_id == db_manager.get_ticker_id(session, ticker)
            ).order_by(ThesisGeneration.generated_at.desc()).first()
            
            session.close()
        except Exception as e:
            logger.error(f"Failed to get thesis statistics: {e}")
            total_theses = 0
            latest_thesis = None

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
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Shutting down pipeline")
        self.executor.shutdown(wait=True)
        
        # Clean old checkpoints
        deleted = self.checkpoint_manager.clean_old_checkpoints(days_to_keep=7)
        if deleted > 0:
            logger.info(f"Cleaned {deleted} old checkpoints")