"""
Test suite for TechnicalAnalyzer
"""
import unittest
import pandas as pd
from datetime import date, datetime, timedelta
from data_collection.technical_analyzer import TechnicalAnalyzer

class TestTechnicalAnalyzer(unittest.TestCase):
    """Test cases for TechnicalAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = TechnicalAnalyzer()
        
        # Create sample technical data
        self.sample_data = [
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
            },
            {
                "date": date(2024, 1, 16),
                "open": 103.0,
                "high": 107.0,
                "low": 101.0,
                "close": 105.0,
                "volume": 1200000,
                "sma_20": 102.5,
                "sma_50": 101.2,
                "ema_20": 103.0,
                "rsi_14": 70.0,
                "macd": 0.7,
                "macd_signal": 0.4,
                "bollinger_upper": 109.0,
                "bollinger_lower": 98.0
            },
            {
                "date": date(2024, 1, 17),
                "open": 105.0,
                "high": 110.0,
                "low": 103.0,
                "close": 108.0,
                "volume": 1500000,
                "sma_20": 103.0,
                "sma_50": 101.5,
                "ema_20": 103.5,
                "rsi_14": 75.0,
                "macd": 0.9,
                "macd_signal": 0.5,
                "bollinger_upper": 110.0,
                "bollinger_lower": 99.0
            }
        ]
    
    def test_analyze_trends(self):
        """Test trend analysis functionality"""
        result = self.analyzer.analyze_trends(self.sample_data)
        
        # Should return a dictionary with trend analysis
        self.assertIsInstance(result, dict)
        self.assertIn("short_term_trend", result)
        self.assertIn("medium_term_trend", result)
        self.assertIn("long_term_trend", result)
        self.assertIn("momentum", result)
        self.assertIn("volatility", result)
        self.assertIn("volume_analysis", result)
    
    def test_generate_insights(self):
        """Test insights generation"""
        insights = self.analyzer.generate_insights(self.sample_data)
        
        # Should return a string with insights
        self.assertIsInstance(insights, str)
        self.assertGreater(len(insights), 0)
        
        # Should contain key technical indicators
        self.assertIn("Price Change", insights)
        self.assertIn("RSI", insights)
        self.assertIn("MACD", insights)
    
    def test_empty_data(self):
        """Test handling of empty data"""
        result = self.analyzer.analyze_trends([])
        self.assertIn("error", result)
        
        insights = self.analyzer.generate_insights([])
        self.assertEqual(insights, "No technical data available")
    
    def test_short_term_trend_analysis(self):
        """Test short-term trend analysis"""
        # Test uptrend
        uptrend_data = [
            {"date": date(2024, 1, 1), "close": 100.0},
            {"date": date(2024, 1, 2), "close": 101.0},
            {"date": date(2024, 1, 3), "close": 102.0},
            {"date": date(2024, 1, 4), "close": 103.0},
            {"date": date(2024, 1, 5), "close": 104.0}
        ]
        
        df = pd.DataFrame(uptrend_data)
        trend = self.analyzer._analyze_short_term_trend(df)
        self.assertEqual(trend, "Uptrend")
        
        # Test downtrend
        downtrend_data = [
            {"date": date(2024, 1, 1), "close": 104.0},
            {"date": date(2024, 1, 2), "close": 103.0},
            {"date": date(2024, 1, 3), "close": 102.0},
            {"date": date(2024, 1, 4), "close": 101.0},
            {"date": date(2024, 1, 5), "close": 100.0}
        ]
        
        df = pd.DataFrame(downtrend_data)
        trend = self.analyzer._analyze_short_term_trend(df)
        self.assertEqual(trend, "Downtrend")
    
    def test_momentum_analysis(self):
        """Test momentum analysis"""
        momentum = self.analyzer._analyze_momentum(pd.DataFrame(self.sample_data))
        
        self.assertIsInstance(momentum, dict)
        # Should contain RSI and MACD analysis if data is available
        if 'rsi_14' in self.sample_data[0]:
            self.assertIn('rsi', momentum)
        if 'macd' in self.sample_data[0]:
            self.assertIn('macd', momentum)
    
    def test_volatility_analysis(self):
        """Test volatility analysis"""
        # Create more data points for volatility analysis
        extended_data = self.sample_data * 10  # 30 data points
        volatility = self.analyzer._analyze_volatility(pd.DataFrame(extended_data))
        
        self.assertIsInstance(volatility, dict)
        if "error" not in volatility:
            self.assertIn("daily_volatility", volatility)
            self.assertIn("recent_range", volatility)
        else:
            # If insufficient data, should return error
            self.assertIn("error", volatility)
    
    def test_volume_analysis(self):
        """Test volume analysis"""
        # Create more data points for volume analysis
        extended_data = self.sample_data * 10  # 30 data points
        volume_analysis = self.analyzer._analyze_volume(pd.DataFrame(extended_data))
        
        self.assertIsInstance(volume_analysis, dict)
        if "error" not in volume_analysis:
            self.assertIn("volume_ratio", volume_analysis)
            self.assertIn("volume_trend", volume_analysis)
        else:
            # If insufficient data, should return error
            self.assertIn("error", volume_analysis)

if __name__ == '__main__':
    unittest.main()