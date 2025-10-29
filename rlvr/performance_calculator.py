"""
Performance calculation for RLVR reward function
Implements directional accuracy and Sharpe ratio metrics
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    Calculates performance metrics for RLVR reward function

    Implements:
    - Directional accuracy (binary: correct direction = 1.0, incorrect = 0.0)
    - Sharpe ratio calculation from historical returns
    - Combined reward score (weighted average)
    """

    def __init__(
        self,
        db_session: Session,
        directional_weight: float = 0.80,
        sharpe_weight: float = 0.20,
        strong_buy_threshold: float = 3.0,
        buy_threshold: float = 2.0,
        hold_threshold_low: float = -1.0,
        hold_threshold_high: float = 1.0,
        sell_threshold: float = -2.0,
        strong_sell_threshold: float = -3.0
    ):
        """
        Initialize performance calculator

        Args:
            db_session: SQLAlchemy database session
            directional_weight: Weight for directional accuracy (0-1)
            sharpe_weight: Weight for Sharpe ratio (0-1)
            strong_buy_threshold: Expected return for strong_buy (%)
            buy_threshold: Expected return for buy (%)
            hold_threshold_low: Lower bound for hold (%)
            hold_threshold_high: Upper bound for hold (%)
            sell_threshold: Expected return for sell (%)
            strong_sell_threshold: Expected return for strong_sell (%)
        """
        # Validate weights sum to 1.0
        if abs(directional_weight + sharpe_weight - 1.0) > 0.001:
            raise ValueError(
                f"Weights must sum to 1.0, got {directional_weight + sharpe_weight}"
            )

        self.db_session = db_session
        self.directional_weight = directional_weight
        self.sharpe_weight = sharpe_weight

        # Action thresholds
        self.thresholds = {
            "strong_buy": strong_buy_threshold,
            "buy": buy_threshold,
            "hold_low": hold_threshold_low,
            "hold_high": hold_threshold_high,
            "sell": sell_threshold,
            "strong_sell": strong_sell_threshold
        }

        logger.info(
            f"Initialized PerformanceCalculator: "
            f"directional={directional_weight*100:.0f}%, sharpe={sharpe_weight*100:.0f}%"
        )

    def calculate_directional_accuracy(
        self,
        predicted_action: str,
        actual_return: float
    ) -> Tuple[bool, float, bool, float]:
        """
        Calculate directional accuracy using database function

        Uses the check_directional_accuracy() stored procedure to determine
        if the prediction was correct based on:
        1. Direction (buy/sell) matching sign of return
        2. Magnitude meeting threshold for the predicted action

        Args:
            predicted_action: Predicted action (strong_buy, buy, hold, sell, strong_sell)
            actual_return: Actual return percentage

        Returns:
            Tuple of:
            - is_correct: Boolean indicating if prediction was correct
            - accuracy_score: 1.0 if correct, 0.0 if incorrect
            - met_threshold: Boolean indicating if return met expected threshold
            - threshold_value: The threshold that was checked
        """
        try:
            result = self.db_session.execute(
                text("""
                SELECT * FROM check_directional_accuracy(
                    :predicted_action,
                    :actual_return
                )
                """),
                {
                    "predicted_action": predicted_action,
                    "actual_return": actual_return
                }
            ).fetchone()

            is_correct = result.is_correct
            accuracy_score = 1.0 if is_correct else 0.0
            met_threshold = result.met_threshold
            threshold_value = float(result.threshold_value)

            logger.debug(
                f"Directional accuracy: action={predicted_action}, "
                f"return={actual_return:.2f}%, correct={is_correct}, "
                f"met_threshold={met_threshold} (threshold={threshold_value:.2f}%)"
            )

            return is_correct, accuracy_score, met_threshold, threshold_value

        except Exception as e:
            logger.error(
                f"Error calculating directional accuracy for "
                f"action={predicted_action}, return={actual_return}: {e}"
            )
            # Return conservative failure
            return False, 0.0, False, 0.0

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate Sharpe ratio using database function

        Args:
            returns: List of historical returns (percentages)
            risk_free_rate: Risk-free rate (default: 0.0%)

        Returns:
            Dictionary with:
            - mean_return: Average return
            - std_dev: Standard deviation of returns
            - sharpe_ratio: Sharpe ratio (mean / std_dev)
            - sharpe_score: Normalized score (0-1, where Sharpe>=1.0 maps to 1.0)
            - num_periods: Number of return periods
        """
        try:
            # Convert Python list to PostgreSQL array
            returns_array = "{" + ",".join(str(r) for r in returns) + "}"

            result = self.db_session.execute(
                text(f"""
                SELECT * FROM calculate_sharpe_ratio(
                    '{returns_array}'::numeric[],
                    {risk_free_rate}
                )
                """)
            ).fetchone()

            sharpe_data = {
                "mean_return": float(result.mean_return),
                "std_dev": float(result.std_dev),
                "sharpe_ratio": float(result.sharpe_ratio),
                "sharpe_score": float(result.sharpe_score),
                "num_periods": result.num_periods
            }

            logger.debug(
                f"Sharpe calculation: mean={sharpe_data['mean_return']:.2f}%, "
                f"std={sharpe_data['std_dev']:.2f}%, "
                f"sharpe={sharpe_data['sharpe_ratio']:.2f}, "
                f"score={sharpe_data['sharpe_score']:.2f}, "
                f"n={sharpe_data['num_periods']}"
            )

            return sharpe_data

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return {
                "mean_return": 0.0,
                "std_dev": 0.0,
                "sharpe_ratio": 0.0,
                "sharpe_score": 0.0,
                "num_periods": len(returns),
                "error": str(e)
            }

    def get_historical_returns(
        self,
        ticker_id: int,
        end_date: str,
        num_periods: int = 30
    ) -> List[float]:
        """
        Get historical returns for Sharpe calculation using database function

        Args:
            ticker_id: Database ticker ID
            end_date: End date (ISO format)
            num_periods: Number of historical periods to retrieve

        Returns:
            List of historical return percentages (most recent first)
        """
        try:
            result = self.db_session.execute(
                text("""
                SELECT * FROM get_historical_returns(
                    :ticker_id,
                    :end_date::date,
                    :num_periods
                )
                """),
                {
                    "ticker_id": ticker_id,
                    "end_date": end_date,
                    "num_periods": num_periods
                }
            ).fetchall()

            # Extract returns from result rows
            returns = [float(row.return_pct) for row in result]

            logger.debug(
                f"Retrieved {len(returns)} historical returns for ticker_id={ticker_id}, "
                f"end_date={end_date}"
            )

            return returns

        except Exception as e:
            logger.error(
                f"Error getting historical returns for ticker_id={ticker_id}, "
                f"end_date={end_date}: {e}"
            )
            return []

    def calculate_reward_score(
        self,
        predicted_action: str,
        actual_return: float,
        historical_returns: Optional[List[float]] = None,
        ticker_id: Optional[int] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate combined reward score for RLVR

        Combines:
        1. Directional accuracy (80% weight, binary 0/1)
        2. Sharpe ratio (20% weight, normalized to 0-1)

        Args:
            predicted_action: Predicted action
            actual_return: Actual return percentage
            historical_returns: Pre-computed historical returns (optional)
            ticker_id: Ticker ID for fetching historical returns (if not provided)
            end_date: End date for historical returns (if not provided)

        Returns:
            Dictionary with:
            - reward_score: Combined weighted score (0-1)
            - directional_score: Directional accuracy score (0 or 1)
            - sharpe_score: Sharpe score (0-1)
            - is_correct: Boolean for directional accuracy
            - sharpe_ratio: Raw Sharpe ratio
            - components: Detailed breakdown
        """
        # Calculate directional accuracy
        is_correct, directional_score, met_threshold, threshold = \
            self.calculate_directional_accuracy(predicted_action, actual_return)

        # Calculate Sharpe ratio if historical data available
        sharpe_score = 0.0
        sharpe_ratio = 0.0
        sharpe_data = {}

        if historical_returns is None and ticker_id is not None and end_date is not None:
            historical_returns = self.get_historical_returns(ticker_id, end_date)

        if historical_returns and len(historical_returns) >= 2:
            sharpe_data = self.calculate_sharpe_ratio(historical_returns)
            sharpe_score = sharpe_data["sharpe_score"]
            sharpe_ratio = sharpe_data["sharpe_ratio"]
        else:
            logger.warning(
                f"Insufficient historical returns ({len(historical_returns) if historical_returns else 0}). "
                "Sharpe score set to 0.0"
            )

        # Calculate weighted reward
        reward_score = (
            self.directional_weight * directional_score +
            self.sharpe_weight * sharpe_score
        )

        result = {
            "reward_score": reward_score,
            "directional_score": directional_score,
            "sharpe_score": sharpe_score,
            "is_correct": is_correct,
            "met_threshold": met_threshold,
            "sharpe_ratio": sharpe_ratio,
            "components": {
                "directional": {
                    "score": directional_score,
                    "weight": self.directional_weight,
                    "contribution": self.directional_weight * directional_score,
                    "is_correct": is_correct,
                    "threshold": threshold,
                    "met_threshold": met_threshold
                },
                "sharpe": {
                    "score": sharpe_score,
                    "weight": self.sharpe_weight,
                    "contribution": self.sharpe_weight * sharpe_score,
                    "sharpe_ratio": sharpe_ratio,
                    **sharpe_data
                }
            }
        }

        logger.debug(
            f"Reward score: {reward_score:.3f} "
            f"(directional={directional_score:.1f}@{self.directional_weight*100:.0f}%, "
            f"sharpe={sharpe_score:.2f}@{self.sharpe_weight*100:.0f}%)"
        )

        return result

    def calculate_batch_rewards(
        self,
        predictions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate reward scores for multiple predictions

        Args:
            predictions: List of dictionaries with:
                - predicted_action: str
                - actual_return: float
                - ticker_id: int (optional)
                - end_date: str (optional)
                - historical_returns: List[float] (optional)

        Returns:
            List of reward score dictionaries
        """
        results = []

        for i, pred in enumerate(predictions):
            logger.debug(f"Calculating reward {i+1}/{len(predictions)}")

            reward = self.calculate_reward_score(
                predicted_action=pred["predicted_action"],
                actual_return=pred["actual_return"],
                historical_returns=pred.get("historical_returns"),
                ticker_id=pred.get("ticker_id"),
                end_date=pred.get("end_date")
            )

            results.append(reward)

        successful = sum(1 for r in results if r["reward_score"] > 0)
        avg_reward = sum(r["reward_score"] for r in results) / len(results)

        logger.info(
            f"Batch reward calculation complete: {len(results)} predictions, "
            f"{successful} with reward > 0, avg_reward={avg_reward:.3f}"
        )

        return results
