"""
RLVR Dataset Generator

This module provides functionality to generate training and development datasets
for RLVR training from thesis generations stored in the database.

Author: Fireworks-Charlie Team
Date: 2025-10-29
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text

from .json_formatter import (
    create_training_example,
    create_dev_example,
    write_jsonl_file,
    validate_training_example,
    validate_dev_example,
    validate_fireworks_format
)
from data_collection.database_manager import DatabaseManager
from orchestration.config_manager import config

logger = logging.getLogger(__name__)


class RLVRDatasetGenerator:
    """
    Generates RLVR training datasets from thesis generations.
    
    This class handles:
    - Querying thesis generations from the database
    - Calculating position returns and performance metrics
    - Formatting examples for training and development
    - Splitting data chronologically
    - Writing JSONL files
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the dataset generator.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.stats = {
            "total_theses": 0,
            "valid_examples": 0,
            "skipped_insufficient_data": 0,
            "skipped_errors": 0,
            "skipped_validation_errors": 0,
            "training_examples": 0,
            "dev_examples": 0
        }
        self.validation_failures: List[Dict[str, Any]] = []
    
    def generate_rlvr_datasets(
        self,
        tickers: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        train_split_date: Optional[str] = None,
        output_dir: str = "storage/rlvr_datasets"
    ) -> Dict[str, Any]:
        """
        Generate RLVR training and development datasets.
        
        Args:
            tickers: List of ticker symbols to include (None for all)
            start_date: Start date for data (YYYY-MM-DD format)
            end_date: End date for data (YYYY-MM-DD format)
            train_split_date: Date to split train/dev (default: 80% of data)
            output_dir: Directory to save JSONL files
            
        Returns:
            Dictionary with generation statistics and file paths
        """
        logger.info("Starting RLVR dataset generation")
        
        # Reset stats and validation tracking per run
        self.stats.update({
            "total_theses": 0,
            "valid_examples": 0,
            "skipped_insufficient_data": 0,
            "skipped_errors": 0,
            "skipped_validation_errors": 0,
            "training_examples": 0,
            "dev_examples": 0
        })
        self.validation_failures = []

        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Query thesis generations
        theses = self._query_thesis_generations(tickers, start_date, end_date)
        logger.info(f"Found {len(theses)} thesis generations")
        self.stats["total_theses"] = len(theses)
        
        if not theses:
            logger.warning("No thesis generations found")
            return self._create_empty_result()
        
        # Determine train/dev split date
        if not train_split_date:
            train_split_date = self._calculate_split_date(theses)
        
        # Convert train_split_date to date object if it's a string
        if isinstance(train_split_date, str):
            train_split_date = datetime.strptime(train_split_date, "%Y-%m-%d").date()
        
        logger.info(f"Using train/dev split date: {train_split_date}")
        
        # Process theses into examples
        training_examples = []
        dev_examples = []
        
        for thesis in theses:
            try:
                # Determine if training or dev based on date FIRST
                # Use as_of_date as the primary date field, fallback to generated_at
                thesis_date = thesis.get('as_of_date', thesis.get('generated_at'))
                # Training includes dates up to and including the split date
                is_training = thesis_date and thesis_date <= train_split_date
                
                # Process thesis with appropriate format
                example = self._process_thesis_to_example(thesis, is_training=is_training)
                if not example:
                    continue
                
                if is_training:
                    training_examples.append(example)
                else:
                    dev_examples.append(example)
                    
            except Exception as e:
                logger.error(f"Error processing thesis {thesis.get('id', 'unknown')}: {e}")
                self.stats["skipped_errors"] += 1
                continue
        
        # Write datasets to files
        train_file = Path(output_dir) / "train.jsonl"
        dev_file = Path(output_dir) / "dev.jsonl"
        
        write_jsonl_file(training_examples, str(train_file))
        write_jsonl_file(dev_examples, str(dev_file))
        
        # Update statistics
        self.stats["training_examples"] = len(training_examples)
        self.stats["dev_examples"] = len(dev_examples)
        self.stats["valid_examples"] = len(training_examples) + len(dev_examples)
        
        logger.info(f"Dataset generation completed: {self.stats}")

        if self.validation_failures:
            preview_count = min(5, len(self.validation_failures))
            logger.warning(
                "Validation failures encountered for %d examples (showing first %d)",
                len(self.validation_failures),
                preview_count,
            )
            for failure in self.validation_failures[:preview_count]:
                logger.warning(
                    "Validation failure | split=%s | thesis_id=%s | ticker=%s | errors=%s",
                    failure.get("split"),
                    failure.get("thesis_id"),
                    failure.get("ticker"),
                    failure.get("errors"),
                )
        
        return {
            "train_file": str(train_file),
            "dev_file": str(dev_file),
            "stats": self.stats,
            "train_split_date": train_split_date,
            "validation_failures": self.validation_failures,
        }
    
    def _query_thesis_generations(
        self,
        tickers: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query thesis generations from the database.
        
        Args:
            tickers: List of ticker symbols to filter by
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of thesis generation records
        """
        query = text("""
            SELECT 
                tg.thesis_id,
                tg.ticker_id,
                t.symbol,
                tg.as_of_date,
                tg.system_prompt,
                tg.user_prompt,
                tg.assistant_response,
                tg.generated_at
            FROM thesis_generations tg
            JOIN tickers t ON tg.ticker_id = t.ticker_id
            WHERE tg.assistant_response IS NOT NULL
        """)
        
        params = {}
        conditions = []
        
        if tickers:
            conditions.append("t.symbol = ANY(:tickers)")
            params["tickers"] = tickers
        
        if start_date:
            conditions.append("tg.as_of_date >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("tg.as_of_date <= :end_date")
            params["end_date"] = end_date
        
        if conditions:
            query = text(str(query) + " AND " + " AND ".join(conditions))
        
        result = self.db_session.execute(query, params).fetchall()
        
        return [dict(row._mapping) for row in result]
    
    def _calculate_split_date(self, theses: List[Dict[str, Any]]) -> str:
        """
        Calculate the train/dev split date (80% of data for training).
        
        Args:
            theses: List of thesis generation records
            
        Returns:
            Split date in YYYY-MM-DD format
        """
        if not theses:
            return datetime.now().strftime("%Y-%m-%d")
        
        # Sort by generation date
        sorted_theses = sorted(
            theses,
            key=lambda x: x.get('as_of_date', x.get('generated_at', ''))
        )
        
        # Calculate 80% split
        split_index = int(len(sorted_theses) * 0.8)
        split_thesis = sorted_theses[split_index]
        
        # Use as_of_date as the primary date field, fallback to generated_at
        split_date = split_thesis.get('as_of_date', split_thesis.get('generated_at'))
        if isinstance(split_date, str):
            return datetime.strptime(split_date[:10], "%Y-%m-%d").date()
        elif isinstance(split_date, date):
            return split_date
        elif hasattr(split_date, 'date'):
            return split_date.date()
        else:
            return datetime.now().date()
    
    def _process_thesis_to_example(self, thesis: Dict[str, Any], is_training: bool = False) -> Optional[Dict[str, Any]]:
        """
        Process a thesis generation into a training/development example.
        
        Args:
            thesis: Thesis generation record from database
            is_training: If True, create training example (no assistant message).
                        If False, create dev example (with assistant message).
            
        Returns:
            Formatted example dictionary or None if processing fails
        """
        try:
            # Get assistant response (already parsed from JSONB)
            assistant_response = thesis['assistant_response']
            if isinstance(assistant_response, str):
                assistant_response = json.loads(assistant_response)
            if not self._validate_assistant_response(assistant_response):
                logger.warning(f"Invalid assistant response for thesis {thesis['thesis_id']}")
                self.stats["skipped_errors"] += 1
                return None
            
            # Calculate position return using database function
            position_data = self._calculate_position_return(
                thesis['ticker_id'],
                thesis['as_of_date'],
                assistant_response['action']
            )
            
            if not position_data:
                logger.warning(f"Insufficient data for position calculation: thesis {thesis['thesis_id']}")
                self.stats["skipped_insufficient_data"] += 1
                return None
            
            # Get historical returns for Sharpe calculation
            historical_returns = self._get_historical_returns(
                thesis['ticker_id'],
                thesis['as_of_date']
            )
            
            # Create ground truth
            ground_truth = {
                "actual_return_pct": position_data['return_pct'],
                "exit_date": position_data['exit_date'],
                "days_held": position_data['days_held'],
                "early_exit": position_data['early_exit'],
                "entry_price": position_data['entry_price'],
                "exit_price": position_data['exit_price']
            }
            
            # Create metadata
            metadata = {
                "ticker": thesis['symbol'],
                "entry_date": str(thesis['as_of_date']),
                "historical_returns": historical_returns,
                "thesis_id": thesis['thesis_id'],
                "position_id": position_data.get('position_id')
            }
            
            # Create example based on whether this is training or dev data
            if is_training:
                # Training example (no assistant response - model generates during training)
                example = create_training_example(
                    system_prompt=thesis['system_prompt'],
                    user_prompt=thesis['user_prompt'],
                    ground_truth=ground_truth,
                    metadata=metadata
                )
            else:
                # Development example (with assistant response for evaluation)
                example = create_dev_example(
                    system_prompt=thesis['system_prompt'],
                    user_prompt=thesis['user_prompt'],
                    assistant_response=assistant_response,
                    ground_truth=ground_truth,
                    metadata=metadata
                )

            if not self._validate_example(example, is_training, thesis):
                return None
            
            return example
            
        except Exception as e:
            logger.error(f"Error processing thesis {thesis.get('thesis_id', 'unknown')}: {e}")
            self.stats["skipped_errors"] += 1
            return None
    
    def _validate_example(self, example: Dict[str, Any], is_training: bool, thesis: Dict[str, Any]) -> bool:
        """Run structural validation for a generated example."""

        errors: List[str] = []
        split = "train" if is_training else "dev"

        fireworks_ok, fireworks_errors = validate_fireworks_format(example)
        if not fireworks_ok:
            errors.extend(fireworks_errors)

        if is_training:
            specific_ok, specific_errors = validate_training_example(example)
        else:
            specific_ok, specific_errors = validate_dev_example(example)

        if not specific_ok:
            errors.extend(specific_errors)

        if errors:
            self.stats["skipped_validation_errors"] += 1

            failure_summary = {
                "thesis_id": thesis.get("thesis_id"),
                "ticker": thesis.get("symbol"),
                "split": split,
                "errors": errors[:5],
            }

            if len(self.validation_failures) < 50:
                self.validation_failures.append(failure_summary)

            logger.warning(
                "Example validation failed for thesis_id=%s (split=%s, ticker=%s): %s",
                failure_summary["thesis_id"],
                split,
                failure_summary["ticker"],
                errors,
            )

            return False

        return True

    def _validate_assistant_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that assistant response has required fields.
        
        Args:
            response: Parsed assistant response
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['reasoning', 'action', 'support']
        return all(field in response for field in required_fields)
    
    def _calculate_position_return(
        self,
        ticker_id: int,
        entry_date: str,
        predicted_action: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate position return using database stored procedure.

        Args:
            ticker_id: Ticker ID
            entry_date: Entry date (YYYY-MM-DD format)
            predicted_action: Predicted action

        Returns:
            Position data dictionary with actual market returns or None if calculation fails
        """
        try:
            # Convert entry_date string to date object if needed
            if isinstance(entry_date, str):
                entry_date_obj = date.fromisoformat(entry_date)
            else:
                entry_date_obj = entry_date

            # Get entry price from market_data table
            entry_price_query = self.db_session.execute(
                text("""
                    SELECT close
                    FROM market_data
                    WHERE ticker_id = :ticker_id
                      AND date = :entry_date
                """),
                {"ticker_id": ticker_id, "entry_date": entry_date_obj}
            ).fetchone()

            if not entry_price_query or entry_price_query.close is None:
                logger.warning(
                    f"No entry price found for ticker_id={ticker_id}, "
                    f"entry_date={entry_date_obj}"
                )
                return None

            entry_price = float(entry_price_query.close)

            # Call database stored procedure to calculate position return
            result = self.db_session.execute(
                text("""
                    SELECT * FROM calculate_position_return(
                        :ticker_id,
                        :entry_date,
                        :entry_price,
                        :predicted_action,
                        3
                    )
                """),
                {
                    "ticker_id": ticker_id,
                    "entry_date": entry_date_obj,
                    "entry_price": entry_price,
                    "predicted_action": predicted_action
                }
            ).fetchone()

            if not result:
                logger.warning(
                    f"No position return calculated for ticker_id={ticker_id}, "
                    f"entry_date={entry_date_obj}. Likely insufficient future data."
                )
                return None

            # Convert database result to dictionary with proper formatting
            return {
                "return_pct": float(result.return_pct) if result.return_pct is not None else None,
                "exit_date": result.exit_date.isoformat() if result.exit_date else None,
                "days_held": result.days_held,
                "early_exit": result.early_exit,
                "entry_price": entry_price,
                "exit_price": float(result.exit_price) if result.exit_price is not None else None,
                "position_id": f"pos_{ticker_id}_{entry_date}"
            }

        except Exception as e:
            logger.error(f"Error calculating position return: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _get_historical_returns(
        self,
        ticker_id: int,
        end_date: str,
        num_periods: int = 30
    ) -> List[float]:
        """
        Get historical returns for Sharpe calculation using database function.

        Args:
            ticker_id: Ticker ID
            end_date: End date for historical data (YYYY-MM-DD format)
            num_periods: Number of periods to retrieve (default: 30)

        Returns:
            List of actual historical returns from database
        """
        try:
            # Convert end_date string to date object if needed
            if isinstance(end_date, str):
                end_date_obj = date.fromisoformat(end_date)
            else:
                end_date_obj = end_date

            # Call database function to get historical returns
            result = self.db_session.execute(
                text("""
                    SELECT get_historical_returns(
                        :ticker_id,
                        :end_date,
                        :num_periods
                    ) AS returns
                """),
                {
                    "ticker_id": ticker_id,
                    "end_date": end_date_obj,
                    "num_periods": num_periods
                }
            ).fetchone()

            if not result or not result.returns:
                logger.debug(
                    f"No historical returns found for ticker_id={ticker_id}, "
                    f"end_date={end_date_obj}"
                )
                return []

            # Convert PostgreSQL array to Python list of floats
            returns_list = [float(r) for r in result.returns if r is not None]

            logger.debug(
                f"Retrieved {len(returns_list)} historical returns for "
                f"ticker_id={ticker_id}"
            )

            return returns_list

        except Exception as e:
            logger.error(f"Error getting historical returns: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result when no data is available."""
        return {
            "train_file": None,
            "dev_file": None,
            "stats": self.stats,
            "train_split_date": None,
            "validation_failures": []
        }
    
    def generate_sample_datasets(
        self,
        output_dir: str = "storage/rlvr_datasets"
    ) -> Dict[str, Any]:
        """
        Generate sample datasets for testing (without database).
        
        Args:
            output_dir: Directory to save JSONL files
            
        Returns:
            Dictionary with file paths and statistics
        """
        from .json_formatter import create_sample_training_examples, create_sample_dev_examples
        
        logger.info("Generating sample datasets")
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Create sample examples
        training_examples = create_sample_training_examples(10)
        dev_examples = create_sample_dev_examples(10)
        
        # Write to files
        train_file = Path(output_dir) / "sample_train.jsonl"
        dev_file = Path(output_dir) / "sample_dev.jsonl"
        
        write_jsonl_file(training_examples, str(train_file))
        write_jsonl_file(dev_examples, str(dev_file))
        
        return {
            "train_file": str(train_file),
            "dev_file": str(dev_file),
            "stats": {
                "training_examples": len(training_examples),
                "dev_examples": len(dev_examples),
                "total_examples": len(training_examples) + len(dev_examples)
            }
        }


# Export classes and functions
__all__ = ["RLVRDatasetGenerator"]