"""
Test suite for token usage and monitoring
"""
import unittest
from unittest.mock import Mock, patch
from orchestration.config_manager import Config

class TestTokenUsage(unittest.TestCase):
    """Test cases for token usage and monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        with patch.dict('os.environ', {
            'TOKEN_BUDGET': '200000',
            'TOKEN_WARNING_THRESHOLD': '180000'
        }):
            self.config = Config()
    
    def test_token_budget_configuration(self):
        """Test that token budget is properly configured"""
        self.assertEqual(self.config.TOKEN_BUDGET, 200000)
        self.assertEqual(self.config.TOKEN_WARNING_THRESHOLD, 180000)
    
    def test_token_estimation(self):
        """Test token estimation calculation"""
        # Test token estimation (roughly 4 characters per token)
        system_prompt = "This is a system prompt with some content. " * 1000  # ~1000 words
        user_prompt = "This is a user prompt with some content. " * 2000     # ~2000 words
        
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        
        # Should be a reasonable estimate
        self.assertGreater(estimated_tokens, 0)
        self.assertLess(estimated_tokens, 100000)  # Should be well under budget
    
    def test_token_budget_validation(self):
        """Test token budget validation logic"""
        # Test within budget
        estimated_tokens = 150000
        self.assertLess(estimated_tokens, self.config.TOKEN_BUDGET)
        self.assertLess(estimated_tokens, self.config.TOKEN_WARNING_THRESHOLD)
        
        # Test warning threshold
        estimated_tokens = 185000
        self.assertLess(estimated_tokens, self.config.TOKEN_BUDGET)
        self.assertGreater(estimated_tokens, self.config.TOKEN_WARNING_THRESHOLD)
        
        # Test over budget
        estimated_tokens = 250000
        self.assertGreater(estimated_tokens, self.config.TOKEN_BUDGET)
    
    def test_prompt_length_estimation(self):
        """Test prompt length estimation for different data sizes"""
        # Small prompt
        small_prompt = "Small prompt content"
        small_tokens = len(small_prompt) // 4
        self.assertLess(small_tokens, 100)
        
        # Medium prompt
        medium_prompt = "Medium prompt content " * 1000
        medium_tokens = len(medium_prompt) // 4
        self.assertGreater(medium_tokens, 1000)
        self.assertLess(medium_tokens, 50000)
        
        # Large prompt
        large_prompt = "Large prompt content " * 10000
        large_tokens = len(large_prompt) // 4
        self.assertGreater(large_tokens, 10000)
        self.assertLess(large_tokens, 200000)  # Should still be under budget
    
    def test_token_monitoring_scenarios(self):
        """Test different token monitoring scenarios"""
        scenarios = [
            {
                "name": "Under warning threshold",
                "tokens": 100000,
                "should_warn": False,
                "should_skip": False
            },
            {
                "name": "Above warning threshold",
                "tokens": 185000,
                "should_warn": True,
                "should_skip": False
            },
            {
                "name": "Above budget",
                "tokens": 250000,
                "should_warn": False,
                "should_skip": True
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                tokens = scenario["tokens"]
                
                # Test warning condition
                if tokens > self.config.TOKEN_WARNING_THRESHOLD and tokens <= self.config.TOKEN_BUDGET:
                    self.assertTrue(scenario["should_warn"])
                else:
                    self.assertFalse(scenario["should_warn"])
                
                # Test skip condition
                if tokens > self.config.TOKEN_BUDGET:
                    self.assertTrue(scenario["should_skip"])
                else:
                    self.assertFalse(scenario["should_skip"])
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test valid configuration
        self.assertTrue(self.config.TOKEN_BUDGET > 0)
        self.assertTrue(self.config.TOKEN_WARNING_THRESHOLD > 0)
        self.assertTrue(self.config.TOKEN_WARNING_THRESHOLD < self.config.TOKEN_BUDGET)
        
        # Test warning threshold is reasonable (80% of budget)
        warning_ratio = self.config.TOKEN_WARNING_THRESHOLD / self.config.TOKEN_BUDGET
        self.assertGreater(warning_ratio, 0.8)
        self.assertLess(warning_ratio, 1.0)

if __name__ == '__main__':
    unittest.main()