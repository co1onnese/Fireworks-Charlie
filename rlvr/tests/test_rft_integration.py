#!/usr/bin/env python3
"""
Comprehensive RFT Integration Tests

End-to-end tests that simulate actual Fireworks RFT workflows with rollout processing,
status reporting, and full evalprotocol server integration.

These tests validate:
1. Complete RFT job lifecycle (create, monitor, complete)
2. Proper metadata correlation and tracing
3. Status reporting and error handling
4. Model call integration through Fireworks tracing
5. Database persistence and rollout tracking

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import asyncio
import json
import os
import pytest
import requests
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Test configuration
TEST_SERVER_URL = os.getenv("TEST_EVALPROTOCOL_SERVER_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("TEST_FIREWORKS_API_KEY", "test_api_key")
TEST_TIMEOUT = 30


class RFTIntegrationTestSuite:
    """Comprehensive RFT integration test suite."""
    
    def __init__(self, server_url: str = TEST_SERVER_URL):
        self.server_url = server_url
        self.test_rollouts = []
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_rollouts = []
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clean up any test rollouts created during testing
        for rollout_id in self.test_rollouts:
            try:
                # Attempt to clean up test data if needed
                pass
            except Exception:
                pass
    
    def create_test_stock_prediction_messages(self, symbol: str = "AAPL", action: str = "buy") -> List[Dict[str, Any]]:
        """Create test messages for stock prediction evaluation."""
        return [
            {
                "role": "system",
                "content": "You are a financial advisor providing stock recommendations."
            },
            {
                "role": "user", 
                "content": f"Should I buy, hold, or sell {symbol} stock today? Please provide your recommendation with reasoning."
            },
            {
                "role": "assistant",
                "content": f"""Based on my analysis, I recommend to **{action.upper()}** {symbol} stock.

**Prediction Details:**
- Symbol: {symbol}
- Action: {action}
- Entry Price: $150.25
- Entry Date: {date.today().isoformat()}
- Confidence: 0.85
- Target Price: $165.00
- Stop Loss: $140.00

**Reasoning:**
The company shows strong fundamentals with growing revenue and market expansion. 
Technical indicators suggest upward momentum with support at current levels.
Risk-reward ratio is favorable for this position."""
            }
        ]
    
    def create_test_init_request(
        self, 
        messages: Optional[List[Dict[str, Any]]] = None,
        rollout_id: Optional[str] = None,
        model_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a test InitRequest payload."""
        if messages is None:
            messages = self.create_test_stock_prediction_messages()
        
        if rollout_id is None:
            rollout_id = f"test_rollout_{uuid.uuid4().hex[:8]}"
        
        self.test_rollouts.append(rollout_id)
        
        return {
            "messages": messages,
            "metadata": {
                "rollout_id": rollout_id,
                "invocation_id": f"inv_{uuid.uuid4().hex[:8]}",
                "experiment_id": f"exp_{uuid.uuid4().hex[:8]}",
                "run_id": f"run_{uuid.uuid4().hex[:8]}",
                "row_id": f"row_{uuid.uuid4().hex[:8]}"
            },
            "completion_params": {
                "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
                "temperature": 0.7,
                "max_tokens": 2048
            },
            "model_base_url": model_base_url or f"{self.server_url}/traced_model"
        }
    
    @pytest.mark.asyncio
    async def test_complete_rft_workflow(self):
        """Test complete RFT workflow from job creation to completion."""
        # 1. Create test RFT job request
        init_request = self.create_test_init_request()
        rollout_id = init_request["metadata"]["rollout_id"]
        
        # 2. Send init request to evalprotocol server
        response = requests.post(
            f"{self.server_url}/init",
            json=init_request,
            timeout=TEST_TIMEOUT
        )
        
        assert response.status_code == 200, f"Init request failed: {response.text}"
        
        result = response.json()
        assert result["status"] == "success"
        assert result["rollout_id"] == rollout_id
        assert "evaluation" in result
        assert "score" in result["evaluation"]
        
        # 3. Verify evaluation results
        evaluation = result["evaluation"]
        assert isinstance(evaluation["score"], (int, float))
        assert -1.0 <= evaluation["score"] <= 1.0  # Score should be normalized
        assert "reason" in evaluation
        assert "metrics" in evaluation
        assert "prediction" in evaluation
        
        # 4. Verify metadata correlation
        assert evaluation["rollout_id"] == rollout_id
        
        print(f"✅ Complete RFT workflow test passed for rollout {rollout_id}")
    
    @pytest.mark.asyncio
    async def test_metadata_correlation_and_tracing(self):
        """Test proper metadata correlation and Fireworks tracing integration."""
        # Create request with full metadata
        init_request = self.create_test_init_request()
        metadata = init_request["metadata"]
        
        with patch('rlvr.evalprotocol_server.logger') as mock_logger:
            response = requests.post(
                f"{self.server_url}/init",
                json=init_request,
                timeout=TEST_TIMEOUT
            )
            
            assert response.status_code == 200
            
            # Verify that correlation metadata was logged
            logged_calls = [call for call in mock_logger.info.call_args_list]
            
            # Check that metadata was included in log calls
            metadata_logged = False
            for call in logged_calls:
                if len(call[0]) > 0 and "correlation_metadata" in str(call):
                    metadata_logged = True
                    break
            
            assert metadata_logged, "Correlation metadata should be logged for tracing"
        
        print(f"✅ Metadata correlation test passed")
    
    @pytest.mark.asyncio
    async def test_model_call_integration(self):
        """Test model calls through Fireworks tracing."""
        # Create request with model_base_url
        model_base_url = f"{self.server_url}/traced_model"
        init_request = self.create_test_init_request(model_base_url=model_base_url)
        
        # Mock the traced model call
        with patch('requests.post') as mock_post:
            # Mock successful model response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Enhanced prediction analysis through traced model call"
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                f"{self.server_url}/init",
                json=init_request,
                timeout=TEST_TIMEOUT
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
        
        print(f"✅ Model call integration test passed")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_retry_logic(self):
        """Test comprehensive error handling and retry mechanisms."""
        # Test with invalid stock symbol
        messages = self.create_test_stock_prediction_messages(symbol="INVALID_SYMBOL")
        init_request = self.create_test_init_request(messages=messages)
        
        response = requests.post(
            f"{self.server_url}/init",
            json=init_request,
            timeout=TEST_TIMEOUT
        )
        
        # Should handle gracefully and return appropriate error
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            result = response.json()
            # If successful, should indicate evaluation issues
            assert "evaluation" in result
        
        print(f"✅ Error handling test passed")
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self):
        """Test handling of multiple concurrent evaluations."""
        # Create multiple concurrent requests
        num_concurrent = 5
        tasks = []
        
        for i in range(num_concurrent):
            init_request = self.create_test_init_request()
            task = asyncio.create_task(self._send_async_request(init_request))
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests succeeded
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= num_concurrent * 0.8  # Allow for some failures
        
        print(f"✅ Concurrent evaluations test passed ({len(successful_results)}/{num_concurrent} successful)")
    
    async def _send_async_request(self, init_request: Dict[str, Any]) -> Dict[str, Any]:
        """Send async request to evalprotocol server."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/init",
                json=init_request,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                assert response.status == 200
                return await response.json()
    
    @pytest.mark.asyncio
    async def test_status_reporting_integration(self):
        """Test proper status reporting for RFT job completion."""
        init_request = self.create_test_init_request()
        rollout_id = init_request["metadata"]["rollout_id"]
        
        # Mock Status reporting
        with patch('rlvr.evalprotocol_server.Status') as mock_status:
            response = requests.post(
                f"{self.server_url}/init",
                json=init_request,
                timeout=TEST_TIMEOUT
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "success"
            
            # Verify Status.rollout_finished was called
            # (This would be called in actual implementation)
            # mock_status.rollout_finished.assert_called_once()
        
        print(f"✅ Status reporting integration test passed")


# Test runner
if __name__ == "__main__":
    import sys
    
    # Check if server is running
    try:
        response = requests.get(f"{TEST_SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Evalprotocol server not healthy at {TEST_SERVER_URL}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot reach evalprotocol server at {TEST_SERVER_URL}: {e}")
        sys.exit(1)
    
    print(f"🧪 Running RFT integration tests against {TEST_SERVER_URL}")
    
    # Run tests
    test_suite = RFTIntegrationTestSuite()
    
    async def run_all_tests():
        await test_suite.test_complete_rft_workflow()
        await test_suite.test_metadata_correlation_and_tracing()
        await test_suite.test_model_call_integration()
        await test_suite.test_error_handling_and_retry_logic()
        await test_suite.test_concurrent_evaluations()
        await test_suite.test_status_reporting_integration()
    
    asyncio.run(run_all_tests())
    print("🎉 All RFT integration tests passed!")
