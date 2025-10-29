"""
Integration test suite for the complete enhanced pipeline
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from orchestration.main_pipeline import FireworksCharliePipeline
from orchestration.config_manager import Config

class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the complete pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.config = Mock()
        self.config.TICKERS = ["AAPL"]
        self.config.START_DATE = date(2024, 1, 1)
        self.config.END_DATE = date(2024, 1, 31)
        self.config.TOKEN_BUDGET = 200000
        self.config.TOKEN_WARNING_THRESHOLD = 180000
        self.config.PARALLEL_WORKERS = 1
        self.config.CHECKPOINT_INTERVAL = 1
        self.config.FIREWORKS_API_KEY = "test_key"
        self.config.FIREWORKS_ACCOUNT_ID = "test_account"
        
        # Mock database manager
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        
        # Mock data orchestrator
        self.mock_data_orchestrator = Mock()
        
        # Mock LLM client
        self.mock_llm_client = Mock()
        
        # Create pipeline
        self.pipeline = FireworksCharliePipeline(self.config)
        self.pipeline.db_manager = self.mock_db_manager
        self.pipeline.data_orchestrator = self.mock_data_orchestrator
        self.pipeline.llm_client = self.mock_llm_client
    
    def test_enhanced_data_collection_integration(self):
        """Test integration of enhanced data collection"""
        # Mock enhanced data collection response
        mock_data = {
            "ticker": "AAPL",
            "date": date(2024, 1, 15),
            "technical": [
                {
                    "date": date(2024, 1, 15),
                    "open": 100.0,
                    "high": 105.0,
                    "low": 98.0,
                    "close": 103.0,
                    "volume": 1000000,
                    "sma_20": 102.0,
                    "sma_50": 101.0,
                    "ema_20": 102.5,
                    "rsi_14": 65.0,
                    "macd": 0.5,
                    "macd_signal": 0.3,
                    "bollinger_upper": 108.0,
                    "bollinger_lower": 97.0
                }
            ],
            "fundamentals": {
                "report_date": date(2024, 1, 1),
                "market_cap": 3000000000000,
                "pe_ratio": 25.0,
                "eps": 6.0,
                "revenue": 100000000000,
                "net_income": 25000000000,
                "revenue_qoq_change": 0.05,
                "revenue_yoy_change": 0.10
            },
            "news": [
                {
                    "published_at": datetime(2024, 1, 15),
                    "headline": "Apple reports strong earnings",
                    "summary": "Apple reported better than expected earnings",
                    "sentiment_score": 0.8,
                    "sentiment_label": "positive"
                }
            ],
            "macro_features": {
                "date": date(2024, 1, 15),
                "yield_curve_spread": 1.5,
                "cpi_monthly_change": 0.3,
                "gdp_quarterly_change": 2.0,
                "unemployment_rate_change": -0.1
            },
            "insider_transactions": [
                {
                    "transaction_date": date(2024, 1, 15),
                    "owner_name": "Tim Cook",
                    "transaction_code": "P",
                    "shares": 1000,
                    "price": 103.0,
                    "amount": 103000.0,
                    "shares_owned_after": 10000
                }
            ]
        }
        
        self.mock_data_orchestrator.get_data_for_date.return_value = mock_data
        
        # Test data collection
        result = self.mock_data_orchestrator.get_data_for_date("AAPL", date(2024, 1, 15))
        
        # Verify enhanced data structure
        self.assertIn("technical", result)
        self.assertIn("fundamentals", result)
        self.assertIn("news", result)
        self.assertIn("macro_features", result)
        self.assertIn("insider_transactions", result)
        
        # Verify technical data has all indicators
        technical = result["technical"][0]
        expected_indicators = ["sma_20", "sma_50", "ema_20", "rsi_14", "macd", "macd_signal", "bollinger_upper", "bollinger_lower"]
        for indicator in expected_indicators:
            self.assertIn(indicator, technical)
    
    def test_enhanced_prompt_building_integration(self):
        """Test integration of enhanced prompt building"""
        from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
        from thesis_generation.data_deduplicator import DataDeduplicator
        
        # Create enhanced prompt builder
        deduplicator = DataDeduplicator()
        prompt_builder = EnhancedCumulativePromptBuilder(deduplicator)
        
        # Create sample data
        sample_data = [
            {
                "date": date(2024, 1, 15),
                "technical": [{
                    "date": date(2024, 1, 15),
                    "open": 100.0,
                    "high": 105.0,
                    "low": 98.0,
                    "close": 103.0,
                    "volume": 1000000,
                    "sma_20": 102.0,
                    "sma_50": 101.0,
                    "ema_20": 102.5,
                    "rsi_14": 65.0,
                    "macd": 0.5,
                    "macd_signal": 0.3,
                    "bollinger_upper": 108.0,
                    "bollinger_lower": 97.0
                }],
                "fundamentals": {
                    "report_date": date(2024, 1, 1),
                    "market_cap": 3000000000000,
                    "pe_ratio": 25.0,
                    "eps": 6.0,
                    "revenue": 100000000000,
                    "net_income": 25000000000,
                    "revenue_qoq_change": 0.05,
                    "revenue_yoy_change": 0.10
                },
                "news": [{
                    "published_at": datetime(2024, 1, 15),
                    "headline": "Apple reports strong earnings",
                    "summary": "Apple reported better than expected earnings",
                    "sentiment_score": 0.8,
                    "sentiment_label": "positive"
                }],
                "macro_features": {
                    "date": date(2024, 1, 15),
                    "yield_curve_spread": 1.5,
                    "cpi_monthly_change": 0.3,
                    "gdp_quarterly_change": 2.0,
                    "unemployment_rate_change": -0.1
                },
                "insider_transactions": [{
                    "transaction_date": date(2024, 1, 15),
                    "owner_name": "Tim Cook",
                    "transaction_code": "P",
                    "shares": 1000,
                    "price": 103.0,
                    "amount": 103000.0,
                    "shares_owned_after": 10000
                }]
            }
        ]
        
        # Test enhanced prompt building
        system_prompt, user_prompt = prompt_builder.build_comprehensive_prompt(
            "AAPL", sample_data, "json"
        )
        
        # Verify prompts are generated
        self.assertIsInstance(system_prompt, str)
        self.assertIsInstance(user_prompt, str)
        self.assertGreater(len(system_prompt), 0)
        self.assertGreater(len(user_prompt), 0)
        
        # Verify hierarchical structure
        self.assertIn("RECENT DATA", user_prompt)
        self.assertIn("MEDIUM-TERM DATA", user_prompt)
        self.assertIn("HISTORICAL DATA", user_prompt)
        
        # Verify comprehensive analysis sections
        self.assertIn("EXECUTIVE SUMMARY", system_prompt)
        self.assertIn("TECHNICAL ANALYSIS", system_prompt)
        self.assertIn("FUNDAMENTAL ANALYSIS", system_prompt)
        self.assertIn("MARKET SENTIMENT", system_prompt)
        self.assertIn("MACROECONOMIC FACTORS", system_prompt)
    
    def test_token_monitoring_integration(self):
        """Test integration of token monitoring"""
        # Test token estimation
        system_prompt = "System prompt content " * 1000
        user_prompt = "User prompt content " * 2000
        
        estimated_tokens = (len(system_prompt) + len(user_prompt)) // 4
        
        # Test different scenarios
        scenarios = [
            {
                "tokens": 100000,
                "expected_action": "proceed",
                "description": "Under warning threshold"
            },
            {
                "tokens": 185000,
                "expected_action": "warn",
                "description": "Above warning threshold"
            },
            {
                "tokens": 250000,
                "expected_action": "skip",
                "description": "Above budget"
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario["description"]):
                tokens = scenario["tokens"]
                
                if tokens > self.config.TOKEN_BUDGET:
                    self.assertEqual(scenario["expected_action"], "skip")
                elif tokens > self.config.TOKEN_WARNING_THRESHOLD:
                    self.assertEqual(scenario["expected_action"], "warn")
                else:
                    self.assertEqual(scenario["expected_action"], "proceed")
    
    def test_technical_analyzer_integration(self):
        """Test integration of technical analyzer"""
        from data_collection.technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer()
        
        # Create sample technical data
        sample_data = [
            {
                "date": date(2024, 1, 15),
                "open": 100.0,
                "high": 105.0,
                "low": 98.0,
                "close": 103.0,
                "volume": 1000000,
                "sma_20": 102.0,
                "sma_50": 101.0,
                "ema_20": 102.5,
                "rsi_14": 65.0,
                "macd": 0.5,
                "macd_signal": 0.3,
                "bollinger_upper": 108.0,
                "bollinger_lower": 97.0
            }
        ]
        
        # Test trend analysis
        trend_analysis = analyzer.analyze_trends(sample_data)
        self.assertIsInstance(trend_analysis, dict)
        self.assertIn("short_term_trend", trend_analysis)
        self.assertIn("momentum", trend_analysis)
        
        # Test insights generation
        insights = analyzer.generate_insights(sample_data)
        self.assertIsInstance(insights, str)
        self.assertGreater(len(insights), 0)
    
    def test_data_analyzers_integration(self):
        """Test integration of specialized data analyzers"""
        from data_collection.fundamental_analyzer import FundamentalAnalyzer
        from data_collection.news_analyzer import NewsAnalyzer
        from data_collection.macro_analyzer import MacroAnalyzer
        
        # Test fundamental analyzer
        fundamental_analyzer = FundamentalAnalyzer()
        fundamental_data = [{
            "pe_ratio": 25.0,
            "revenue_yoy_change": 0.10,
            "net_income": 25000000000,
            "revenue": 100000000000
        }]
        
        fundamental_analysis = fundamental_analyzer.analyze_fundamentals(fundamental_data)
        self.assertIsInstance(fundamental_analysis, dict)
        
        fundamental_insights = fundamental_analyzer.generate_insights(fundamental_data)
        self.assertIsInstance(fundamental_insights, str)
        
        # Test news analyzer
        news_analyzer = NewsAnalyzer()
        news_data = [{
            "published_at": datetime(2024, 1, 15),
            "headline": "Apple reports strong earnings",
            "summary": "Apple reported better than expected earnings",
            "sentiment_score": 0.8,
            "sentiment_label": "positive"
        }]
        
        news_analysis = news_analyzer.analyze_news(news_data)
        self.assertIsInstance(news_analysis, dict)
        
        news_insights = news_analyzer.generate_insights(news_data)
        self.assertIsInstance(news_insights, str)
        
        # Test macro analyzer
        macro_analyzer = MacroAnalyzer()
        macro_data = [{
            "yield_curve_spread": 1.5,
            "cpi_monthly_change": 0.3,
            "gdp_quarterly_change": 2.0,
            "unemployment_rate_change": -0.1
        }]
        
        macro_analysis = macro_analyzer.analyze_macro_environment(macro_data)
        self.assertIsInstance(macro_analysis, dict)
        
        macro_insights = macro_analyzer.generate_insights(macro_data)
        self.assertIsInstance(macro_insights, str)

if __name__ == '__main__':
    unittest.main()