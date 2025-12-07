"""
Evalprotocol HTTP Server for Stock Prediction Ground Truth Evaluation

This server implements the evalprotocol specification for serving reward function
data based on actual stock performance up to 3 days in the future.

Architecture:
- FastAPI server with POST /init endpoint
- Accepts InitRequest payloads with stock prediction messages
- Evaluates predictions against actual 3-day stock performance
- Uses existing multi-metric reward calculation system
- Integrates with Fireworks tracing for completion signaling

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
from functools import wraps

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Evalprotocol imports
from eval_protocol import Status, InitRequest, FireworksTracingHttpHandler, RolloutIdFilter

# Local imports
from data_collection.database_manager import DatabaseManager, Position, MarketData, Ticker
from rlvr.position_tracker import PositionTracker
from orchestration.market_calendar import MarketCalendar

# Configure logging with Fireworks tracing
fireworks_handler = FireworksTracingHttpHandler()
logging.getLogger().addHandler(fireworks_handler)
logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise

                    delay = backoff_factor * (2 ** attempt)
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay}s...")
                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


def timeout_handler(timeout_seconds: int = 30):
    """
    Decorator for adding timeout to functions.

    Args:
        timeout_seconds: Maximum execution time in seconds
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
                raise HTTPException(status_code=408, detail=f"Operation timed out after {timeout_seconds} seconds")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import signal

            def timeout_handler_func(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")

            # Set up timeout signal
            old_handler = signal.signal(signal.SIGALRM, timeout_handler_func)
            signal.alarm(timeout_seconds)

            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Cancel timeout
                return result
            except TimeoutError as e:
                logger.error(str(e))
                raise HTTPException(status_code=408, detail=str(e))
            finally:
                signal.signal(signal.SIGALRM, old_handler)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

app = FastAPI(
    title="Fireworks-Charlie Evalprotocol Server",
    description="Ground Truth evaluator for stock price movement predictions",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
db_manager = DatabaseManager()
market_calendar = MarketCalendar()


class StockPredictionEvaluator:
    """
    Core evaluator that adapts the existing multi-metric reward function
    to work within the evalprotocol framework.
    """
    
    def __init__(self):
        self.position_tracker = PositionTracker(
            db_session=db_manager.get_session(),
            hold_days=3,
            early_exit_enabled=True
        )
    
    def evaluate_prediction(
        self,
        messages: List[Dict[str, Any]],
        rollout_id: str,
        correlation_metadata: Optional[Dict[str, Any]] = None,
        completion_params: Optional[Dict[str, Any]] = None,
        model_base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate stock prediction against actual 3-day performance.

        Args:
            messages: Conversation messages from InitRequest
            rollout_id: Unique rollout identifier for logging
            correlation_metadata: Full metadata for Fireworks tracing correlation
            completion_params: Model configuration parameters
            model_base_url: Fireworks tracing URL for model calls
            api_key: Fireworks API key for authenticated calls

        Returns:
            Dictionary with evaluation results and metrics
        """
        try:
            # Log evaluation start with full context
            logger.info(
                f"Starting prediction evaluation for rollout {rollout_id}",
                extra={
                    "correlation_metadata": correlation_metadata,
                    "completion_params": completion_params,
                    "model_base_url": model_base_url,
                    "message_count": len(messages)
                }
            )

            # Extract prediction from assistant message (with optional model call support)
            prediction_data = self._extract_prediction(messages, model_base_url, api_key)
            if not prediction_data:
                raise ValueError("No valid prediction found in messages")
            
            # Get stock ticker and current price
            ticker_info = self._get_ticker_info(prediction_data.get("symbol"))
            if not ticker_info:
                raise ValueError(f"Ticker {prediction_data.get('symbol')} not found")
            
            # Calculate actual 3-day performance
            actual_performance = self._calculate_actual_performance(
                ticker_info["ticker_id"],
                prediction_data["entry_date"],
                prediction_data["entry_price"]
            )
            
            if not actual_performance:
                raise ValueError("Unable to calculate actual performance")
            
            # Apply existing multi-metric reward calculation
            reward_score = self._calculate_reward_score(
                prediction_data,
                actual_performance,
                rollout_id
            )
            
            # Log successful evaluation
            logger.info(
                f"Evaluation completed for rollout {rollout_id}",
                extra={
                    "score": reward_score["score"],
                    "actual_return_pct": actual_performance["actual_return_pct"],
                    "prediction_action": prediction_data.get("action", "unknown"),
                    "correlation_metadata": correlation_metadata
                }
            )

            return {
                "score": reward_score["score"],
                "reason": reward_score["reason"],
                "metrics": reward_score["metrics"],
                "actual_return_pct": actual_performance["actual_return_pct"],
                "prediction": prediction_data,
                "rollout_id": rollout_id
            }

        except Exception as e:
            logger.error(
                f"Evaluation failed for rollout {rollout_id}: {e}",
                extra={
                    "rollout_id": rollout_id,
                    "correlation_metadata": correlation_metadata,
                    "error_type": type(e).__name__
                }
            )
            raise
    
    def _extract_prediction(
        self,
        messages: List[Dict[str, Any]],
        model_base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract stock prediction from assistant message.

        If model_base_url is provided, this method can make additional model calls
        through Fireworks tracing for enhanced prediction extraction or validation.

        Args:
            messages: Conversation messages
            model_base_url: Optional Fireworks tracing URL for model calls
            api_key: Optional Fireworks API key

        Returns:
            Dictionary with prediction data or None if extraction fails
        """
        try:
            # Find the last assistant message
            for message in reversed(messages):
                if message.get("role") == "assistant":
                    content = message.get("content", "")
                    if content and content.strip():
                        # Parse JSON prediction
                        prediction_data = json.loads(content.strip())

                        # Validate required fields
                        required_fields = ["action", "reasoning", "support"]
                        if all(field in prediction_data for field in required_fields):
                            # Extract symbol from context or metadata
                            symbol = self._extract_symbol_from_messages(messages)
                            if symbol:
                                prediction_data["symbol"] = symbol
                                prediction_data["entry_date"] = date.today()

                                # Get current price for entry
                                entry_price = self._get_current_price(symbol)
                                if entry_price:
                                    prediction_data["entry_price"] = entry_price
                                    return prediction_data
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error extracting prediction: {e}")
            return None

    def _extract_symbol_from_messages(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract stock symbol from conversation messages."""
        # Look for ticker symbol in user messages or system prompts
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                # Simple regex to find stock symbols (3-5 uppercase letters)
                import re
                symbols = re.findall(r'\b[A-Z]{2,5}\b', content)
                if symbols:
                    # Return the first symbol found
                    return symbols[0]
        return None

    @retry_with_backoff(max_retries=3, backoff_factor=0.5, exceptions=(Exception,))
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price from database."""
        try:
            session = db_manager.get_session()

            # Get ticker
            ticker = session.query(Ticker).filter_by(symbol=symbol).first()
            if not ticker:
                return None

            # Get most recent market data
            latest_data = session.query(MarketData).filter(
                MarketData.ticker_id == ticker.ticker_id
            ).order_by(MarketData.date.desc()).first()

            if latest_data:
                return float(latest_data.close)
            return None

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    @retry_with_backoff(max_retries=3, backoff_factor=0.5, exceptions=(Exception,))
    def _get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker information from database."""
        try:
            session = db_manager.get_session()
            ticker = session.query(Ticker).filter_by(symbol=symbol).first()

            if ticker:
                return {
                    "ticker_id": ticker.ticker_id,
                    "symbol": ticker.symbol,
                    "company_name": ticker.company_name,
                    "sector": ticker.sector,
                    "industry": ticker.industry
                }
            return None

        except Exception as e:
            logger.error(f"Error getting ticker info for {symbol}: {e}")
            return None

    @retry_with_backoff(max_retries=2, backoff_factor=1.0, exceptions=(Exception,))
    def _calculate_actual_performance(
        self,
        ticker_id: int,
        entry_date: date,
        entry_price: float
    ) -> Optional[Dict[str, Any]]:
        """Calculate actual 3-day stock performance."""
        try:
            # Use PositionTracker to calculate 3-day performance
            result = self.position_tracker.track_position(
                ticker_id=ticker_id,
                entry_date=entry_date,
                entry_price=entry_price,
                predicted_action="evaluation"  # Placeholder action
            )

            if result and result.get("status") == "completed":
                return {
                    "actual_return_pct": result["actual_return_pct"],
                    "exit_date": result["exit_date"],
                    "exit_price": result["exit_price"],
                    "days_held": result["days_held"],
                    "early_exit": result["early_exit"],
                    "early_exit_reason": result["early_exit_reason"]
                }
            return None

        except Exception as e:
            logger.error(f"Error calculating actual performance: {e}")
            return None

    def _calculate_reward_score(
        self,
        prediction_data: Dict[str, Any],
        actual_performance: Dict[str, Any],
        rollout_id: str
    ) -> Dict[str, Any]:
        """Apply existing multi-metric reward calculation."""
        try:
            # Import the existing reward function components
            from rlvr.reward_function_advanced import (
                _is_directionally_correct,
                _calculate_magnitude_accuracy,
                _calculate_confidence_calibration,
                _calculate_downside_penalty,
                _calculate_sharpe_ratio,
                _normalize_sharpe_ratio,
                _evaluate_action_reasonableness,
                DIRECTIONAL_WEIGHT,
                MAGNITUDE_WEIGHT,
                SHARPE_WEIGHT,
                CALIBRATION_WEIGHT,
                DOWNSIDE_WEIGHT
            )

            # Extract data
            predicted_action = prediction_data.get("action", "").lower()
            reasoning = prediction_data.get("reasoning", "")
            support = prediction_data.get("support", "")
            actual_return = actual_performance.get("actual_return_pct", 0.0)

            # Get historical returns for Sharpe calculation
            historical_returns = self._get_historical_returns(
                prediction_data.get("symbol"),
                prediction_data.get("entry_date")
            )

            # Calculate component scores using existing logic
            is_correct = _is_directionally_correct(predicted_action, actual_return)
            directional_score = 1.0 if is_correct else 0.0

            magnitude_score = _calculate_magnitude_accuracy(predicted_action, actual_return)

            sharpe_ratio = _calculate_sharpe_ratio(historical_returns)
            sharpe_score = _normalize_sharpe_ratio(sharpe_ratio)

            calibration_score = _calculate_confidence_calibration(
                predicted_action, actual_return, is_correct
            )

            downside_penalty = _calculate_downside_penalty(predicted_action, actual_return)

            reasonableness_score = _evaluate_action_reasonableness(
                predicted_action, reasoning, support
            )

            # Combine scores with weights
            component_scores = {
                'directional': directional_score * DIRECTIONAL_WEIGHT,
                'magnitude': magnitude_score * MAGNITUDE_WEIGHT,
                'sharpe': sharpe_score * SHARPE_WEIGHT,
                'calibration': calibration_score * CALIBRATION_WEIGHT,
                'downside': (1.0 - downside_penalty) * DOWNSIDE_WEIGHT
            }

            # Calculate final reward
            reward_score = sum(component_scores.values())

            # Apply reasonableness multiplier (0.5-1.0)
            reward_score *= (0.5 + 0.5 * reasonableness_score)

            # Ensure in [0, 1]
            reward_score = max(0.0, min(1.0, reward_score))

            # Create detailed metrics
            metrics = {
                "directional_accuracy": {
                    "score": directional_score,
                    "reason": f"{'✓ Correct' if is_correct else '✗ Incorrect'}: {predicted_action} vs {actual_return:+.2f}%",
                    "success": is_correct
                },
                "magnitude_accuracy": {
                    "score": magnitude_score,
                    "reason": f"Magnitude error: {abs(self._get_expected_return(predicted_action) - actual_return):.2f}%",
                    "success": magnitude_score >= 0.7
                },
                "sharpe_score": {
                    "score": sharpe_score,
                    "reason": f"Sharpe ratio: {sharpe_ratio:.3f} ({len(historical_returns)} returns)",
                    "success": sharpe_score >= 0.5
                },
                "confidence_calibration": {
                    "score": calibration_score,
                    "reason": f"Calibration: {'well-calibrated' if calibration_score > 0.7 else 'needs improvement'}",
                    "success": calibration_score >= 0.7
                },
                "downside_protection": {
                    "score": 1.0 - downside_penalty,
                    "reason": f"Downside risk: {downside_penalty:.2%} penalty"
                },
                "reasoning_quality": {
                    "score": reasonableness_score,
                    "reason": f"Reasoning: {len(reasoning)} chars, support: {len(support)} chars",
                    "success": reasonableness_score >= 0.6
                }
            }

            # Create comprehensive reason
            status = "✓" if is_correct else "✗"
            reason = (
                f"R:{reward_score:.3f} | "
                f"Dir:{status} | "
                f"Mag:{magnitude_score:.2f} | "
                f"Sharpe:{sharpe_ratio:.2f} | "
                f"Cal:{calibration_score:.2f} | "
                f"{predicted_action}→{actual_return:+.2f}%"
            )

            return {
                "score": reward_score,
                "reason": reason,
                "metrics": metrics,
                "component_scores": component_scores
            }

        except Exception as e:
            logger.error(f"Error calculating reward score for rollout {rollout_id}: {e}")
            return {
                "score": 0.0,
                "reason": f"Error: {str(e)}",
                "metrics": {"error": {"score": 0.0, "reason": str(e), "success": False}}
            }

    def _get_historical_returns(self, symbol: str, as_of_date: date) -> List[float]:
        """Get historical returns for Sharpe ratio calculation."""
        try:
            session = db_manager.get_session()

            # Get ticker
            ticker = session.query(Ticker).filter_by(symbol=symbol).first()
            if not ticker:
                return []

            # Get last 30 trading days of market data before as_of_date
            historical_data = session.query(MarketData).filter(
                MarketData.ticker_id == ticker.ticker_id,
                MarketData.date < as_of_date
            ).order_by(MarketData.date.desc()).limit(30).all()

            if len(historical_data) < 2:
                return []

            # Calculate daily returns
            returns = []
            for i in range(len(historical_data) - 1):
                current_price = float(historical_data[i].close)
                previous_price = float(historical_data[i + 1].close)
                daily_return = ((current_price - previous_price) / previous_price) * 100.0
                returns.append(daily_return)

            return returns

        except Exception as e:
            logger.error(f"Error getting historical returns for {symbol}: {e}")
            return []

    def _get_expected_return(self, predicted_action: str) -> float:
        """Get expected return for a predicted action."""
        action_expectations = {
            "strong_buy": 4.0,
            "buy": 2.5,
            "hold": 0.0,
            "sell": -2.5,
            "strong_sell": -4.0
        }
        return action_expectations.get(predicted_action.lower(), 0.0)

    def _make_traced_model_call(
        self,
        messages: List[Dict[str, Any]],
        model_base_url: str,
        api_key: str,
        completion_params: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Make a model call through Fireworks tracing for enhanced prediction processing.

        This method can be used to make additional LLM calls during evaluation,
        with all calls properly traced and correlated with the rollout metadata.

        Args:
            messages: Messages to send to the model
            model_base_url: Fireworks tracing URL with correlation metadata
            api_key: Fireworks API key
            completion_params: Model configuration parameters

        Returns:
            Model response content or None if call fails
        """
        try:
            import requests

            # Prepare request payload
            payload = {
                "messages": messages,
                "api_key": api_key
            }

            # Add completion parameters if provided
            if completion_params:
                payload.update(completion_params)

            # Make traced model call
            response = requests.post(
                f"{model_base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("choices", [{}])[0].get("message", {}).get("content")
            else:
                logger.warning(f"Model call failed with status {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error making traced model call: {e}")
            return None


# Global evaluator instance
evaluator = StockPredictionEvaluator()


@app.post("/init")
async def init_rollout(request: InitRequest):
    """
    Evalprotocol /init endpoint for stock prediction evaluation.

    Accepts InitRequest with stock prediction messages and evaluates
    against actual 3-day stock performance using ground truth data.

    Implements full Fireworks RFT integration with proper metadata correlation.
    """
    # Extract all metadata fields for proper correlation
    metadata = request.metadata
    rollout_id = metadata.rollout_id
    invocation_id = getattr(metadata, 'invocation_id', None)
    experiment_id = getattr(metadata, 'experiment_id', None)
    run_id = getattr(metadata, 'run_id', None)
    row_id = getattr(metadata, 'row_id', None)

    # Create rollout-specific logger with comprehensive metadata
    rollout_logger = logging.getLogger(f"eval_server.{rollout_id}")
    rollout_logger.addFilter(RolloutIdFilter(rollout_id))

    # Log all correlation metadata for debugging
    correlation_info = {
        "rollout_id": rollout_id,
        "invocation_id": invocation_id,
        "experiment_id": experiment_id,
        "run_id": run_id,
        "row_id": row_id
    }

    try:
        rollout_logger.info(
            f"Starting rollout evaluation {rollout_id}",
            extra={
                "correlation_metadata": correlation_info,
                "request_metadata": metadata.dict() if hasattr(metadata, 'dict') else str(metadata)
            }
        )

        # Evaluate the stock prediction with enhanced metadata
        evaluation_result = evaluator.evaluate_prediction(
            messages=request.messages,
            rollout_id=rollout_id,
            correlation_metadata=correlation_info,
            completion_params=request.completion_params,
            model_base_url=request.model_base_url,
            api_key=request.api_key
        )

        # Log successful completion with structured status and full metadata
        rollout_logger.info(
            f"Rollout {rollout_id} completed successfully",
            extra={
                "status": Status.rollout_finished(),
                "evaluation_result": evaluation_result,
                "correlation_metadata": correlation_info,
                "completion_details": {
                    "score": evaluation_result.get("score", 0.0),
                    "actual_return_pct": evaluation_result.get("actual_return_pct", 0.0),
                    "prediction_action": evaluation_result.get("prediction", {}).get("action", "unknown")
                }
            }
        )

        return {
            "status": "success",
            "rollout_id": rollout_id,
            "evaluation": evaluation_result,
            "metadata": correlation_info
        }

    except Exception as e:
        # Log errors with structured status and full context
        error_details = {
            "error_message": str(e),
            "error_type": type(e).__name__,
            "correlation_metadata": correlation_info
        }

        rollout_logger.error(
            f"Rollout {rollout_id} failed: {e}",
            extra={
                "status": Status.rollout_error(str(e)),
                "error_details": error_details
            }
        )

        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}",
            headers={"X-Rollout-ID": rollout_id}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "evalprotocol-server"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
