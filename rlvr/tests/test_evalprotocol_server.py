"""
Tests for Evalprotocol Stock Prediction Evaluator Server

Comprehensive test suite to validate the evalprotocol server functionality,
including stock prediction evaluation, reward calculation, and API endpoints.

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import json
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Import the server app
from rlvr.evalprotocol_server import app, StockPredictionEvaluator

# Test client
client = TestClient(app)


class TestEvalprotocolServer:
    """Test suite for the evalprotocol server."""
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "evalprotocol-server"}
    
    @patch('rlvr.evalprotocol_server.db_manager')
    def test_init_endpoint_success(self, mock_db_manager):
        """Test successful stock prediction evaluation."""
        # Mock database responses
        mock_session = Mock()
        mock_db_manager.get_session.return_value = mock_session
        
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1
        mock_ticker.symbol = "AAPL"
        mock_ticker.company_name = "Apple Inc."
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ticker
        
        # Mock market data
        mock_market_data = Mock()
        mock_market_data.close = 150.0
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_market_data
        
        # Mock position tracker
        with patch('rlvr.evalprotocol_server.evaluator') as mock_evaluator:
            mock_evaluator.evaluate_prediction.return_value = {
                "score": 0.85,
                "reason": "R:0.850 | Dir:✓ | Mag:0.92 | Sharpe:0.65 | Cal:0.80 | buy→+2.3%",
                "metrics": {
                    "directional_accuracy": {"score": 1.0, "success": True},
                    "magnitude_accuracy": {"score": 0.92, "success": True}
                },
                "actual_return_pct": 2.3,
                "prediction": {"action": "buy", "symbol": "AAPL"},
                "rollout_id": "test-rollout-123"
            }
            
            # Test request payload
            request_payload = {
                "completion_params": {"model": "gpt-4", "temperature": 0.7},
                "messages": [
                    {"role": "user", "content": "Analyze AAPL stock"},
                    {"role": "assistant", "content": '{"action": "buy", "reasoning": "Strong fundamentals", "support": "Revenue growth"}'}
                ],
                "tools": [],
                "model_base_url": "https://api.openai.com",
                "metadata": {"rollout_id": "test-rollout-123"},
                "api_key": "test-key"
            }
            
            response = client.post("/init", json=request_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["rollout_id"] == "test-rollout-123"
            assert "evaluation" in data
            assert data["evaluation"]["score"] == 0.85
    
    def test_init_endpoint_invalid_request(self):
        """Test init endpoint with invalid request."""
        # Missing required fields
        invalid_payload = {
            "messages": [],
            "metadata": {"rollout_id": "test-rollout-456"}
        }
        
        response = client.post("/init", json=invalid_payload)
        assert response.status_code == 422  # Validation error


class TestStockPredictionEvaluator:
    """Test suite for the StockPredictionEvaluator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = StockPredictionEvaluator()
    
    def test_extract_prediction_valid_json(self):
        """Test extracting valid prediction from messages."""
        messages = [
            {"role": "user", "content": "Analyze AAPL stock"},
            {"role": "assistant", "content": '{"action": "buy", "reasoning": "Strong growth", "support": "Q3 earnings beat"}'}
        ]
        
        with patch.object(self.evaluator, '_extract_symbol_from_messages', return_value="AAPL"):
            with patch.object(self.evaluator, '_get_current_price', return_value=150.0):
                result = self.evaluator._extract_prediction(messages)
                
                assert result is not None
                assert result["action"] == "buy"
                assert result["reasoning"] == "Strong growth"
                assert result["support"] == "Q3 earnings beat"
                assert result["symbol"] == "AAPL"
                assert result["entry_price"] == 150.0
    
    def test_extract_prediction_invalid_json(self):
        """Test extracting prediction with invalid JSON."""
        messages = [
            {"role": "user", "content": "Analyze AAPL stock"},
            {"role": "assistant", "content": "Invalid JSON response"}
        ]
        
        result = self.evaluator._extract_prediction(messages)
        assert result is None
    
    def test_extract_symbol_from_messages(self):
        """Test symbol extraction from messages."""
        messages = [
            {"role": "user", "content": "Please analyze AAPL stock for me"},
            {"role": "assistant", "content": "Analysis complete"}
        ]
        
        result = self.evaluator._extract_symbol_from_messages(messages)
        assert result == "AAPL"
    
    @patch('rlvr.evalprotocol_server.db_manager')
    def test_get_current_price(self, mock_db_manager):
        """Test getting current stock price."""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_manager.get_session.return_value = mock_session
        
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ticker
        
        # Mock market data
        mock_market_data = Mock()
        mock_market_data.close = 150.75
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_market_data
        
        result = self.evaluator._get_current_price("AAPL")
        assert result == 150.75
    
    @patch('rlvr.evalprotocol_server.db_manager')
    def test_get_ticker_info(self, mock_db_manager):
        """Test getting ticker information."""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_manager.get_session.return_value = mock_session
        
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1
        mock_ticker.symbol = "AAPL"
        mock_ticker.company_name = "Apple Inc."
        mock_ticker.sector = "Technology"
        mock_ticker.industry = "Consumer Electronics"
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ticker
        
        result = self.evaluator._get_ticker_info("AAPL")
        
        assert result is not None
        assert result["ticker_id"] == 1
        assert result["symbol"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"

    def test_calculate_actual_performance(self):
        """Test calculating actual 3-day performance."""
        # Mock position tracker
        mock_result = {
            "status": "completed",
            "actual_return_pct": 2.5,
            "exit_date": date.today() + timedelta(days=3),
            "exit_price": 153.75,
            "days_held": 3,
            "early_exit": False,
            "early_exit_reason": None
        }

        with patch.object(self.evaluator.position_tracker, 'track_position', return_value=mock_result):
            result = self.evaluator._calculate_actual_performance(
                ticker_id=1,
                entry_date=date.today(),
                entry_price=150.0
            )

            assert result is not None
            assert result["actual_return_pct"] == 2.5
            assert result["exit_price"] == 153.75
            assert result["days_held"] == 3
            assert result["early_exit"] is False

    @patch('rlvr.evalprotocol_server.db_manager')
    def test_get_historical_returns(self, mock_db_manager):
        """Test getting historical returns for Sharpe calculation."""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_manager.get_session.return_value = mock_session

        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ticker

        # Mock historical market data
        mock_data = []
        prices = [150.0, 148.5, 151.2, 149.8, 152.1]  # 5 days of prices
        for i, price in enumerate(prices):
            mock_record = Mock()
            mock_record.close = price
            mock_data.append(mock_record)

        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_data

        result = self.evaluator._get_historical_returns("AAPL", date.today())

        # Should calculate daily returns: [(148.5-150)/150, (151.2-148.5)/148.5, ...]
        assert len(result) == 4  # n-1 returns from n prices
        assert isinstance(result[0], float)

    def test_get_expected_return(self):
        """Test getting expected return for different actions."""
        assert self.evaluator._get_expected_return("strong_buy") == 4.0
        assert self.evaluator._get_expected_return("buy") == 2.5
        assert self.evaluator._get_expected_return("hold") == 0.0
        assert self.evaluator._get_expected_return("sell") == -2.5
        assert self.evaluator._get_expected_return("strong_sell") == -4.0
        assert self.evaluator._get_expected_return("unknown") == 0.0

    @patch('rlvr.reward_function_advanced._is_directionally_correct')
    @patch('rlvr.reward_function_advanced._calculate_magnitude_accuracy')
    @patch('rlvr.reward_function_advanced._calculate_confidence_calibration')
    def test_calculate_reward_score(self, mock_calibration, mock_magnitude, mock_directional):
        """Test reward score calculation."""
        # Mock the imported functions
        mock_directional.return_value = True
        mock_magnitude.return_value = 0.85
        mock_calibration.return_value = 0.75

        # Mock other dependencies
        with patch.object(self.evaluator, '_get_historical_returns', return_value=[1.0, -0.5, 2.0]):
            with patch('rlvr.reward_function_advanced._calculate_sharpe_ratio', return_value=0.6):
                with patch('rlvr.reward_function_advanced._normalize_sharpe_ratio', return_value=0.65):
                    with patch('rlvr.reward_function_advanced._calculate_downside_penalty', return_value=0.1):
                        with patch('rlvr.reward_function_advanced._evaluate_action_reasonableness', return_value=0.8):

                            prediction_data = {
                                "action": "buy",
                                "reasoning": "Strong fundamentals and technical indicators",
                                "support": "Revenue growth of 15% YoY",
                                "symbol": "AAPL",
                                "entry_date": date.today()
                            }

                            actual_performance = {
                                "actual_return_pct": 2.3
                            }

                            result = self.evaluator._calculate_reward_score(
                                prediction_data, actual_performance, "test-rollout"
                            )

                            assert result is not None
                            assert "score" in result
                            assert "reason" in result
                            assert "metrics" in result
                            assert 0.0 <= result["score"] <= 1.0


class TestIntegration:
    """Integration tests for the complete evaluation pipeline."""

    @patch('rlvr.evalprotocol_server.db_manager')
    @patch('rlvr.evalprotocol_server.evaluator')
    def test_full_evaluation_pipeline(self, mock_evaluator, mock_db_manager):
        """Test the complete evaluation pipeline from request to response."""
        # Mock the evaluator to return a complete evaluation
        mock_evaluator.evaluate_prediction.return_value = {
            "score": 0.78,
            "reason": "R:0.780 | Dir:✓ | Mag:0.85 | Sharpe:0.60 | Cal:0.75 | buy→+1.8%",
            "metrics": {
                "directional_accuracy": {"score": 1.0, "success": True, "reason": "✓ Correct: buy vs +1.8%"},
                "magnitude_accuracy": {"score": 0.85, "success": True, "reason": "Magnitude error: 0.7%"},
                "sharpe_score": {"score": 0.60, "success": True, "reason": "Sharpe ratio: 0.45 (20 returns)"},
                "confidence_calibration": {"score": 0.75, "success": True, "reason": "Calibration: well-calibrated"},
                "downside_protection": {"score": 0.95, "reason": "Downside risk: 5.0% penalty"},
                "reasoning_quality": {"score": 0.80, "success": True, "reason": "Reasoning: 45 chars, support: 25 chars"}
            },
            "actual_return_pct": 1.8,
            "prediction": {
                "action": "buy",
                "reasoning": "Strong technical indicators and momentum",
                "support": "RSI oversold, volume spike",
                "symbol": "AAPL",
                "entry_price": 150.0
            },
            "rollout_id": "integration-test-123"
        }

        # Test request
        request_payload = {
            "completion_params": {"model": "gpt-4", "temperature": 0.7},
            "messages": [
                {"role": "system", "content": "You are a stock analyst."},
                {"role": "user", "content": "Analyze AAPL stock and provide a trading recommendation."},
                {"role": "assistant", "content": '{"action": "buy", "reasoning": "Strong technical indicators and momentum", "support": "RSI oversold, volume spike"}'}
            ],
            "tools": [],
            "model_base_url": "https://api.openai.com/v1",
            "metadata": {"rollout_id": "integration-test-123"},
            "api_key": "test-api-key"
        }

        response = client.post("/init", json=request_payload)

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["rollout_id"] == "integration-test-123"

        evaluation = data["evaluation"]
        assert evaluation["score"] == 0.78
        assert "✓" in evaluation["reason"]  # Indicates correct prediction
        assert evaluation["actual_return_pct"] == 1.8

        # Verify metrics structure
        metrics = evaluation["metrics"]
        assert "directional_accuracy" in metrics
        assert "magnitude_accuracy" in metrics
        assert "sharpe_score" in metrics
        assert "confidence_calibration" in metrics
        assert "downside_protection" in metrics
        assert "reasoning_quality" in metrics

        # Verify evaluator was called correctly
        mock_evaluator.evaluate_prediction.assert_called_once()
        call_args = mock_evaluator.evaluate_prediction.call_args
        assert call_args[1]["rollout_id"] == "integration-test-123"
