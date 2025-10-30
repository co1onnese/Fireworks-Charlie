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

    @patch('concurrent.futures.ThreadPoolExecutor')
    @patch('thesis_generation.llm_factory.create_llm_client')
    @patch('thesis_generation.context_compressor.ContextCompressor')
    @patch('data_collection.data_orchestrator.DataOrchestrator')
    @patch('data_collection.database_manager.DatabaseManager')
    @patch('orchestration.checkpoint_manager.CheckpointManager')
    @patch('orchestration.market_calendar.MarketCalendar')
    @patch('orchestration.main_pipeline.config')
    def setUp(self, mock_config, mock_calendar, mock_checkpoint, mock_db_class,
              mock_orchestrator_class, mock_compressor, mock_llm_factory, mock_executor):
        """Set up test fixtures with proper global config mocking"""
        # Configure the mock global config with all required attributes
        mock_config.TICKERS = ["AAPL"]
        mock_config.START_DATE = "2024-01-01"
        mock_config.END_DATE = "2024-01-31"
        mock_config.TOKEN_BUDGET = 200000
        mock_config.TOKEN_WARNING_THRESHOLD = 180000
        mock_config.PARALLEL_WORKERS = 1
        mock_config.CHECKPOINT_INTERVAL = 1
        mock_config.FIREWORKS_API_KEY = "test_key"
        mock_config.FIREWORKS_ACCOUNT_ID = "test_account"
        mock_config.LLM_PROVIDER = "fireworks"
        mock_config.DEEPSEEK_API_KEY = ""
        mock_config.DB_URL = "postgresql://test:test@localhost/test"
        mock_config.LOG_FILE = "/tmp/test.log"
        mock_config.LOG_LEVEL = "INFO"
        mock_config.MARKET_CALENDAR = "NYSE"
        mock_config.CHECKPOINT_DIR = "/tmp/checkpoints"
        mock_config.MAX_DAYS_RECENT = 7
        mock_config.MAX_DAYS_MEDIUM = 30
        mock_config.MAX_DAYS_HISTORICAL = 90
        mock_config.ENABLE_AGGRESSIVE_COMPRESSION = True
        mock_config.MODEL_NAME = "test-model"

        # Mock log_configuration method
        mock_config.log_configuration = Mock()

        # Setup mock instances
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        mock_db_class.return_value = self.mock_db_manager

        self.mock_data_orchestrator = Mock()
        mock_orchestrator_class.return_value = self.mock_data_orchestrator

        self.mock_llm_client = Mock()
        self.mock_llm_client.test_connection.return_value = True
        mock_llm_factory.return_value = self.mock_llm_client

        self.mock_calendar = Mock()
        mock_calendar.return_value = self.mock_calendar

        self.mock_checkpoint = Mock()
        mock_checkpoint.return_value = self.mock_checkpoint

        self.mock_compressor = Mock()
        mock_compressor.return_value = self.mock_compressor

        self.mock_executor = Mock()
        mock_executor.return_value = self.mock_executor

        # Create pipeline (no arguments!)
        self.pipeline = FireworksCharliePipeline()

        # Store the mock config for tests to use
        self.config = mock_config
    
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

        # Create sample data spanning all three time periods
        # Recent: 0-7 days, Medium: 8-30 days, Historical: 31+ days
        base_date = date(2024, 1, 15)
        sample_data = []

        # Add data for recent period (1 day ago)
        sample_data.append({
            "date": base_date - timedelta(days=1),
            "technical": [{
                "date": base_date - timedelta(days=1),
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
                "published_at": datetime(2024, 1, 14),
                "headline": "Apple reports strong earnings",
                "summary": "Apple reported better than expected earnings",
                "sentiment_score": 0.8,
                "sentiment_label": "positive"
            }],
            "macro_features": None,
            "insider_transactions": []
        })

        # Add data for medium period (15 days ago)
        sample_data.append({
            "date": base_date - timedelta(days=15),
            "technical": [{
                "date": base_date - timedelta(days=15),
                "open": 98.0,
                "high": 102.0,
                "low": 97.0,
                "close": 100.0,
                "volume": 950000,
                "sma_20": 100.0,
                "sma_50": 99.0,
                "ema_20": 100.5,
                "rsi_14": 58.0,
                "macd": 0.3,
                "macd_signal": 0.2,
                "bollinger_upper": 105.0,
                "bollinger_lower": 95.0
            }],
            "fundamentals": None,
            "news": [],
            "macro_features": None,
            "insider_transactions": []
        })

        # Add data for historical period (40 days ago)
        sample_data.append({
            "date": base_date - timedelta(days=40),
            "technical": [{
                "date": base_date - timedelta(days=40),
                "open": 95.0,
                "high": 99.0,
                "low": 94.0,
                "close": 97.0,
                "volume": 900000,
                "sma_20": 97.0,
                "sma_50": 96.0,
                "ema_20": 97.5,
                "rsi_14": 52.0,
                "macd": 0.1,
                "macd_signal": 0.1,
                "bollinger_upper": 102.0,
                "bollinger_lower": 92.0
            }],
            "fundamentals": None,
            "news": [],
            "macro_features": None,
            "insider_transactions": []
        })
        
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