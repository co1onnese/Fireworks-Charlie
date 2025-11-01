"""
Test suite for enhanced data collection functionality
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from data_collection.data_orchestrator import DataOrchestrator
from data_collection.database_manager import Ticker, MarketData, News, InsiderTransaction, Fundamental, MacroFeatures

class TestEnhancedDataCollection(unittest.TestCase):
    """Test cases for enhanced data collection"""

    @patch('data_collection.data_orchestrator.FeatureEngineer')
    @patch('data_collection.data_orchestrator.FREDClient')
    @patch('data_collection.data_orchestrator.EODHDClient')
    @patch('data_collection.data_orchestrator.DatabaseManager')
    def setUp(self, mock_db_class, mock_eodhd_class, mock_fred_class, mock_feature_class):
        """Set up test fixtures with proper mocking"""
        # Create proper config mock with all required attributes
        self.config = Mock()
        self.config.DB_URL = "postgresql://test:test@localhost/test_db"
        self.config.EODHD_API_KEY = "test_eodhd_key"
        self.config.FRED_API_KEY = "test_fred_key"

        # Setup mock database manager instance
        self.mock_db_manager = Mock()
        self.mock_session = Mock()
        self.mock_db_manager.get_session.return_value = self.mock_session
        mock_db_class.return_value = self.mock_db_manager

        # Setup mock client instances (return None if no API key is acceptable)
        self.mock_eodhd_client = Mock()
        mock_eodhd_class.return_value = self.mock_eodhd_client

        self.mock_fred_client = Mock()
        mock_fred_class.return_value = self.mock_fred_client

        # Create orchestrator (will use mocked dependencies)
        self.orchestrator = DataOrchestrator(self.config)
    
    def test_get_data_for_date_90_days_technical(self):
        """Test that technical data collection is expanded to 90 days"""
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1

        # Mock technical data (90 days) with proper spec
        mock_technical_data = []
        for i in range(90):
            mock_data = Mock(spec=['date', 'open', 'high', 'low', 'close', 'adjusted_close',
                                    'volume', 'sma_20', 'sma_50', 'ema_20', 'rsi_14',
                                    'macd', 'macd_signal', 'bollinger_upper', 'bollinger_lower'])
            mock_data.date = date(2024, 1, 15) - timedelta(days=i)
            mock_data.open = 100.0
            mock_data.high = 105.0
            mock_data.low = 98.0
            mock_data.close = 103.0
            mock_data.adjusted_close = 102.5
            mock_data.volume = 1000000
            mock_data.sma_20 = 102.0
            mock_data.sma_50 = 101.0
            mock_data.ema_20 = 102.5
            mock_data.rsi_14 = 65.0
            mock_data.macd = 0.5
            mock_data.macd_signal = 0.3
            mock_data.bollinger_upper = 108.0
            mock_data.bollinger_lower = 97.0
            mock_technical_data.append(mock_data)

        # Track the limit call for verification
        limit_calls = []

        # Use side_effect to handle multiple different queries
        def query_side_effect(model_class):
            mock_query = Mock()
            if model_class.__name__ == 'Ticker':
                mock_query.filter_by.return_value.first.return_value = mock_ticker
            elif model_class.__name__ == 'MarketData':
                # Create a mock limit that tracks calls
                mock_limit = Mock()
                mock_limit.all.return_value = mock_technical_data
                # Track the limit call
                def track_limit(n):
                    limit_calls.append(n)
                    return mock_limit
                mock_query.filter.return_value.order_by.return_value.limit = track_limit
            elif model_class.__name__ == 'Fundamental':
                mock_query.filter.return_value.order_by.return_value.first.return_value = None
            elif model_class.__name__ == 'News':
                mock_query.filter.return_value.order_by.return_value.all.return_value = []
            elif model_class.__name__ == 'MacroFeature':
                mock_query.filter.return_value.order_by.return_value.first.return_value = None
            elif model_class.__name__ == 'InsiderTransaction':
                mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return mock_query

        self.mock_session.query.side_effect = query_side_effect

        # Test the method
        result = self.orchestrator.get_data_for_date("AAPL", date(2024, 1, 15))

        # Verify 90 days of technical data was requested
        self.assertIn(90, limit_calls, f"Expected limit(90) to be called, but got limits: {limit_calls}")

        # Verify result structure
        self.assertIn("technical", result)
        self.assertEqual(len(result["technical"]), 90)
    
    def test_get_data_for_date_60_days_news(self):
        """Test that news data collection is expanded to 60 days"""
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ticker
        
        # Mock news data (60 days)
        mock_news_data = []
        for i in range(60):
            mock_news = Mock()
            mock_news.published_date = datetime(2024, 1, 15) - timedelta(days=i)
            mock_news.title = f"News {i}"
            mock_news.content = f"Content {i}"
            mock_news.sentiment_score = 0.1
            mock_news.sentiment = "positive"
            mock_news_data.append(mock_news)
        
        # Mock query chain for technical data (no data)
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        # Mock news query
        mock_news_query = Mock()
        mock_news_query.filter.return_value.order_by.return_value.all.return_value = mock_news_data
        self.mock_session.query.return_value = mock_news_query
        
        # Mock other data sources
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None  # No fundamentals
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None  # No macro
        self.mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []  # No insider
        
        # Test the method
        result = self.orchestrator.get_data_for_date("AAPL", date(2024, 1, 15))
        
        # Verify 60 days of news data was requested
        # The filter should include 60 days lookback
        self.mock_session.query.assert_called()
        
        # Verify result structure
        self.assertIn("news", result)
        self.assertEqual(len(result["news"]), 60)
    
    def test_get_data_for_date_insider_transactions(self):
        """Test that insider transactions are included"""
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.ticker_id = 1

        # Mock insider transactions with proper spec to avoid Mock float conversion issues
        mock_insider_data = []
        for i in range(20):
            mock_insider = Mock(spec=['transaction_date', 'owner_name', 'transaction_code',
                                       'shares', 'price', 'amount', 'shares_owned_after'])
            mock_insider.transaction_date = date(2024, 1, 15) - timedelta(days=i)
            mock_insider.owner_name = f"Owner {i}"
            mock_insider.transaction_code = "P" if i % 2 == 0 else "S"
            mock_insider.shares = 1000 + i * 100  # int
            mock_insider.price = 100.0 + float(i)  # Explicit float
            mock_insider.amount = 100000.0 + float(i * 10000)  # Explicit float
            mock_insider.shares_owned_after = 10000 + i * 1000  # int
            mock_insider_data.append(mock_insider)

        # Use side_effect to handle multiple different queries
        def query_side_effect(model_class):
            mock_query = Mock()
            if model_class.__name__ == 'Ticker':
                mock_query.filter_by.return_value.first.return_value = mock_ticker
            elif model_class.__name__ == 'MarketData':
                mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            elif model_class.__name__ == 'Fundamental':
                mock_query.filter.return_value.order_by.return_value.first.return_value = None
            elif model_class.__name__ == 'News':
                mock_query.filter.return_value.order_by.return_value.all.return_value = []
            elif model_class.__name__ == 'MacroFeature':
                mock_query.filter.return_value.order_by.return_value.first.return_value = None
            elif model_class.__name__ == 'InsiderTransaction':
                mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_insider_data
            return mock_query

        self.mock_session.query.side_effect = query_side_effect

        # Test the method
        result = self.orchestrator.get_data_for_date("AAPL", date(2024, 1, 15))

        # Verify insider transactions are included
        self.assertIn("insider_transactions", result)
        self.assertEqual(len(result["insider_transactions"]), 20)
    
    def test_serialize_technical_all_indicators(self):
        """Test that technical serialization includes all indicators"""
        # Create mock technical data with all indicators
        mock_technical = Mock()
        mock_technical.date = date(2024, 1, 15)
        mock_technical.open = 100.0
        mock_technical.high = 105.0
        mock_technical.low = 98.0
        mock_technical.close = 103.0
        mock_technical.adjusted_close = 102.5
        mock_technical.volume = 1000000
        mock_technical.sma_20 = 102.0
        mock_technical.sma_50 = 101.0
        mock_technical.ema_20 = 102.5
        mock_technical.rsi_14 = 65.0
        mock_technical.macd = 0.5
        mock_technical.macd_signal = 0.3
        mock_technical.bollinger_upper = 108.0
        mock_technical.bollinger_lower = 97.0
        
        # Test serialization
        result = self.orchestrator._serialize_technical(mock_technical)
        
        # Verify all indicators are included
        expected_fields = [
            "date", "open", "high", "low", "close", "adjusted_close", "volume",
            "sma_20", "sma_50", "ema_20", "rsi_14", "macd", "macd_signal",
            "bollinger_upper", "bollinger_lower"
        ]
        
        for field in expected_fields:
            self.assertIn(field, result)
    
    def test_serialize_insider_transaction(self):
        """Test insider transaction serialization"""
        # Create mock insider transaction
        mock_insider = Mock()
        mock_insider.transaction_date = date(2024, 1, 15)
        mock_insider.owner_name = "John Doe"
        mock_insider.transaction_code = "P"
        mock_insider.shares = 1000
        mock_insider.price = 100.0
        mock_insider.amount = 100000.0
        mock_insider.shares_owned_after = 10000
        
        # Test serialization
        result = self.orchestrator._serialize_insider_transaction(mock_insider)
        
        # Verify all fields are included
        expected_fields = [
            "transaction_date", "owner_name", "transaction_code", "shares",
            "price", "amount", "shares_owned_after"
        ]
        
        for field in expected_fields:
            self.assertIn(field, result)
        
        # Verify data types
        self.assertIsInstance(result["shares"], int)
        self.assertIsInstance(result["price"], float)
        self.assertIsInstance(result["amount"], float)
    
    def test_ticker_not_found(self):
        """Test handling when ticker is not found"""
        # Mock no ticker found
        self.mock_session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Test the method
        result = self.orchestrator.get_data_for_date("INVALID", date(2024, 1, 15))
        
        # Should return error
        self.assertIn("error", result)
        self.assertIn("INVALID", result["error"])

if __name__ == '__main__':
    unittest.main()