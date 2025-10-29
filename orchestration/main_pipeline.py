"""
Main pipeline orchestrator for Trainer-Charlie
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
from thesis_generation.data_deduplicator import DataDeduplicator
from thesis_generation.llm_client import DeepSeekClient
from thesis_generation.xml_thesis_generator import XMLThesisGenerator
from utils.logger import setup_logger

# Set up logging
logger = setup_logger(
    name="trainer_charlie",
    log_file=config.LOG_FILE,
    log_level=config.LOG_LEVEL
)

class TrainerCharliePipeline:
    """Main pipeline for cumulative thesis generation"""
    
    def __init__(self):
        """Initialize pipeline components"""
        # Log configuration
        config.log_configuration(logger)
        
        # Initialize components
        self.market_calendar = MarketCalendar(config.MARKET_CALENDAR)
        self.checkpoint_manager = CheckpointManager(config.CHECKPOINT_DIR)
        self.data_orchestrator = DataOrchestrator(config)
        self.xml_generator = XMLThesisGenerator(config.THESIS_OUTPUT_DIR)
        
        # Initialize LLM client
        if config.DEEPSEEK_API_KEY:
            self.llm_client = DeepSeekClient(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL
            )
            # Test connection
            if not self.llm_client.test_connection():
                logger.warning("DeepSeek API connection test failed")
        else:
            self.llm_client = None
            logger.warning("No DeepSeek API key configured - thesis generation will fail")
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=config.PARALLEL_WORKERS)
        
        logger.info("TrainerCharliePipeline initialized successfully")
    
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
                
                # Build cumulative prompt
                logger.debug(f"Building prompt for {ticker} on {trading_day}")
                prompt = prompt_builder.build_cumulative_prompt(
                    ticker,
                    cumulative_data,
                    include_instructions=True
                )
                
                # Check token count
                estimated_tokens = len(prompt) // 4  # Rough estimate
                if estimated_tokens > config.TOKEN_BUDGET:
                    logger.warning(
                        f"Prompt for {ticker} on {trading_day} exceeds token budget "
                        f"({estimated_tokens} > {config.TOKEN_BUDGET})"
                    )
                
                # Generate thesis
                if self.llm_client:
                    logger.info(f"Generating thesis for {ticker} on {trading_day}")
                    thesis_result = self.llm_client.generate_thesis(
                        prompt=prompt,
                        ticker=ticker,
                        as_of_date=trading_day.isoformat()
                    )
                    
                    if thesis_result["status"] == "success":
                        # Save to XML
                        success = self.xml_generator.append_thesis(
                            ticker=ticker,
                            as_of_date=trading_day.isoformat(),
                            thesis_data=thesis_result
                        )
                        
                        if success:
                            theses_generated += 1
                            logger.info(
                                f"Generated thesis for {ticker} on {trading_day}: "
                                f"{thesis_result['action']}"
                            )
                        else:
                            errors.append({
                                "date": trading_day,
                                "error": "Failed to save thesis to XML"
                            })
                    else:
                        # LLM generation failed
                        error_msg = thesis_result.get("error", "Unknown LLM error")
                        logger.error(f"LLM generation failed: {error_msg}")
                        
                        # Add error entry to XML
                        self.xml_generator.append_thesis(
                            ticker=ticker,
                            as_of_date=trading_day.isoformat(),
                            thesis_data={
                                "reasoning": f"ERROR: {error_msg}",
                                "action": "error",
                                "support": "Failed to generate thesis due to API error"
                            }
                        )
                        
                        errors.append({
                            "date": trading_day,
                            "error": error_msg
                        })
                else:
                    # No LLM client available
                    error_msg = "No LLM client configured"
                    self.xml_generator.append_thesis(
                        ticker=ticker,
                        as_of_date=trading_day.isoformat(),
                        thesis_data={
                            "reasoning": f"ERROR: {error_msg}",
                            "action": "error",
                            "support": "Cannot generate thesis without LLM configuration"
                        }
                    )
                    errors.append({
                        "date": trading_day,
                        "error": error_msg
                    })
                
                # Save checkpoint after each successful day
                self.checkpoint_manager.save_checkpoint(
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
                
                # Add error entry
                self.xml_generator.append_thesis(
                    ticker=ticker,
                    as_of_date=trading_day.isoformat(),
                    thesis_data={
                        "reasoning": f"ERROR: Pipeline error - {str(e)}",
                        "action": "error",
                        "support": "Processing failed due to pipeline error"
                    }
                )
                
                errors.append({
                    "date": trading_day,
                    "error": str(e)
                })
        
        # Get final statistics
        total_theses = self.xml_generator.get_thesis_count(ticker)
        latest_thesis = self.xml_generator.get_latest_thesis(ticker)

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