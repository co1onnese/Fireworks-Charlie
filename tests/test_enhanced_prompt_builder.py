"""
Test suite for EnhancedCumulativePromptBuilder
"""
import unittest
from datetime import date, datetime, timedelta
from thesis_generation.enhanced_prompt_builder import EnhancedCumulativePromptBuilder
from thesis_generation.data_deduplicator import DataDeduplicator

class TestEnhancedCumulativePromptBuilder(unittest.TestCase):
    """Test cases for EnhancedCumulativePromptBuilder"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.deduplicator = DataDeduplicator()
        self.builder = EnhancedCumulativePromptBuilder(self.deduplicator)
        
        # Create sample data with different time periods
        base_date = date(2024, 1, 15)
        self.sample_data = []
        
        # Recent data (0-7 days)
        for i in range(5):
            day_data = {
                "date": base_date - timedelta(days=i),
                "technical": [{
                    "date": base_date - timedelta(days=i),
                    "open": 100.0 + i,
                    "high": 105.0 + i,
                    "low": 98.0 + i,
                    "close": 103.0 + i,
                    "volume": 1000000 + i * 100000,
                    "sma_20": 102.0 + i,
                    "sma_50": 101.0 + i,
                    "ema_20": 102.5 + i,
                    "rsi_14": 65.0 + i,
                    "macd": 0.5 + i * 0.1,
                    "macd_signal": 0.3 + i * 0.1,
                    "bollinger_upper": 108.0 + i,
                    "bollinger_lower": 97.0 + i
                }],
                "news": [{
                    "published_at": datetime.combine(base_date - timedelta(days=i), datetime.min.time()),
                    "headline": f"Test news {i}",
                    "summary": f"Test summary {i}",
                    "sentiment_score": 0.1 + i * 0.1,
                    "sentiment_label": "positive" if i % 2 == 0 else "negative"
                }],
                "fundamentals": {
                    "report_date": base_date - timedelta(days=i*30),
                    "market_cap": 1000000000 + i * 100000000,
                    "pe_ratio": 20.0 + i,
                    "eps": 5.0 + i,
                    "revenue": 1000000000 + i * 100000000,
                    "net_income": 100000000 + i * 10000000,
                    "revenue_qoq_change": 0.05 + i * 0.01,
                    "revenue_yoy_change": 0.10 + i * 0.02
                } if i == 0 else None,  # Only latest day has fundamentals
                "insider_transactions": [{
                    "transaction_date": base_date - timedelta(days=i),
                    "owner_name": f"Insider {i}",
                    "transaction_code": "P" if i % 2 == 0 else "S",
                    "shares": 1000 + i * 100,
                    "price": 100.0 + i,
                    "amount": 100000.0 + i * 10000,
                    "shares_owned_after": 10000 + i * 1000
                }] if i < 3 else [],  # Only first 3 days have insider transactions
                "macro_features": {
                    "date": base_date - timedelta(days=i),
                    "yield_curve_spread": 1.5 + i * 0.1,
                    "cpi_monthly_change": 0.3 + i * 0.01,
                    "gdp_quarterly_change": 2.0 + i * 0.1,
                    "unemployment_rate_change": -0.1 + i * 0.01
                } if i == 0 else None  # Only latest day has macro features
            }
            self.sample_data.append(day_data)
        
        # Medium data (8-30 days)
        for i in range(15):
            day_data = {
                "date": base_date - timedelta(days=8+i),
                "technical": [{
                    "date": base_date - timedelta(days=8+i),
                    "open": 95.0 + i,
                    "high": 100.0 + i,
                    "low": 93.0 + i,
                    "close": 98.0 + i,
                    "volume": 800000 + i * 50000,
                    "sma_20": 97.0 + i,
                    "sma_50": 96.0 + i,
                    "ema_20": 97.5 + i,
                    "rsi_14": 55.0 + i,
                    "macd": 0.2 + i * 0.05,
                    "macd_signal": 0.1 + i * 0.05,
                    "bollinger_upper": 103.0 + i,
                    "bollinger_lower": 92.0 + i
                }],
                "news": [{
                    "published_at": datetime.combine(base_date - timedelta(days=8+i), datetime.min.time()),
                    "headline": f"Medium term news {i}",
                    "summary": f"Medium term summary {i}",
                    "sentiment_score": 0.0 + i * 0.05,
                    "sentiment_label": "neutral"
                }] if i % 3 == 0 else [],  # Every 3rd day has news
                "fundamentals": None,
                "insider_transactions": [],
                "macro_features": None
            }
            self.sample_data.append(day_data)
        
        # Historical data (31+ days)
        for i in range(10):
            day_data = {
                "date": base_date - timedelta(days=31+i),
                "technical": [{
                    "date": base_date - timedelta(days=31+i),
                    "open": 90.0 + i,
                    "high": 95.0 + i,
                    "low": 88.0 + i,
                    "close": 93.0 + i,
                    "volume": 700000 + i * 30000,
                    "sma_20": 92.0 + i,
                    "sma_50": 91.0 + i,
                    "ema_20": 92.5 + i,
                    "rsi_14": 45.0 + i,
                    "macd": 0.0 + i * 0.02,
                    "macd_signal": 0.0 + i * 0.02,
                    "bollinger_upper": 98.0 + i,
                    "bollinger_lower": 87.0 + i
                }],
                "news": [],
                "fundamentals": None,
                "insider_transactions": [],
                "macro_features": None
            }
            self.sample_data.append(day_data)
    
    def test_build_comprehensive_prompt(self):
        """Test comprehensive prompt building"""
        system_prompt, user_prompt = self.builder.build_comprehensive_prompt(
            "AAPL", 
            self.sample_data, 
            "json"
        )
        
        # Should return both system and user prompts
        self.assertIsInstance(system_prompt, str)
        self.assertIsInstance(user_prompt, str)
        self.assertGreater(len(system_prompt), 0)
        self.assertGreater(len(user_prompt), 0)
        
        # System prompt should contain key sections
        self.assertIn("EXECUTIVE SUMMARY", system_prompt)
        self.assertIn("TECHNICAL ANALYSIS", system_prompt)
        self.assertIn("FUNDAMENTAL ANALYSIS", system_prompt)
        self.assertIn("MARKET SENTIMENT", system_prompt)
        self.assertIn("MACROECONOMIC FACTORS", system_prompt)
        self.assertIn("RISK ASSESSMENT", system_prompt)
        self.assertIn("INVESTMENT RECOMMENDATION", system_prompt)
        
        # User prompt should contain hierarchical sections
        self.assertIn("RECENT DATA", user_prompt)
        self.assertIn("MEDIUM-TERM DATA", user_prompt)
        self.assertIn("HISTORICAL DATA", user_prompt)
        self.assertIn("DATA QUALITY SUMMARY", user_prompt)
    
    def test_organize_data_hierarchically(self):
        """Test hierarchical data organization"""
        organized = self.builder._organize_data_hierarchically(self.sample_data)
        
        # Should have hierarchical structure
        self.assertIn("recent", organized)
        self.assertIn("medium", organized)
        self.assertIn("historical", organized)
        self.assertIn("latest_date", organized)
        
        # Recent data should be 0-7 days
        recent_count = len(organized["recent"])
        self.assertEqual(recent_count, 5)  # We created 5 recent days
        
        # Medium data should be 8-30 days
        medium_count = len(organized["medium"])
        self.assertEqual(medium_count, 15)  # We created 15 medium days
        
        # Historical data should be 31+ days
        historical_count = len(organized["historical"])
        self.assertEqual(historical_count, 10)  # We created 10 historical days
    
    def test_build_detailed_recent_section(self):
        """Test detailed recent data section building"""
        recent_data = self.sample_data[:5]  # First 5 days are recent
        sections = self.builder._build_detailed_recent_section("AAPL", recent_data)
        
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)
        
        # Should contain technical analysis
        content = "\n".join(sections)
        self.assertIn("TECHNICAL ANALYSIS", content)
        self.assertIn("NEWS & SENTIMENT", content)
        self.assertIn("FUNDAMENTALS", content)
        self.assertIn("INSIDER ACTIVITY", content)
    
    def test_build_summarized_medium_section(self):
        """Test summarized medium-term data section building"""
        medium_data = self.sample_data[5:20]  # Days 8-30
        sections = self.builder._build_summarized_medium_section("AAPL", medium_data)
        
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)
        
        # Should contain summarized sections
        content = "\n".join(sections)
        self.assertIn("TECHNICAL TRENDS", content)
        self.assertIn("NEWS SENTIMENT TRENDS", content)
        self.assertIn("MACROECONOMIC ENVIRONMENT", content)
    
    def test_build_historical_insights_section(self):
        """Test historical insights section building"""
        historical_data = self.sample_data[20:]  # Days 31+
        sections = self.builder._build_historical_insights_section("AAPL", historical_data)
        
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)
        
        # Should contain historical analysis
        content = "\n".join(sections)
        self.assertIn("KEY PRICE LEVELS", content)
        self.assertIn("LONG-TERM TRENDS", content)
        self.assertIn("HISTORICAL VOLATILITY", content)

    def test_long_term_trend_analysis_outputs_metrics(self):
        """Long-term trend section should produce concrete metrics."""
        historical_data = self.sample_data[20:]
        sections = self.builder._build_long_term_trends(historical_data)

        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)

        combined = " ".join(sections)
        self.assertNotIn("Implementation pending", combined)
        self.assertIn("Price change over", combined)
        self.assertTrue(
            "Rolling" in combined or "SMA(50) drift" in combined,
            msg="Long-term trends should include rolling or moving-average commentary",
        )
        self.assertRegex(combined, r"[-+]?\d+\.\d+%")

    def test_volatility_analysis_includes_statistics(self):
        """Volatility analysis should include descriptive statistics."""
        historical_data = self.sample_data[20:]
        sections = self.builder._build_volatility_analysis(historical_data)

        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)

        combined = " ".join(filter(None, sections))
        self.assertIn("Daily return volatility", combined)
        self.assertIn("Avg intraday range", combined)
        self.assertIn("90th percentile daily move", combined)
    
    def test_build_data_quality_summary(self):
        """Test data quality summary building"""
        organized_data = self.builder._organize_data_hierarchically(self.sample_data)
        sections = self.builder._build_data_quality_summary(organized_data)
        
        self.assertIsInstance(sections, list)
        self.assertGreater(len(sections), 0)
        
        # Should contain data coverage information
        content = "\n".join(sections)
        self.assertIn("Data Coverage", content)
        self.assertIn("Recent (0-7 days)", content)
        self.assertIn("Medium (8-30 days)", content)
        self.assertIn("Historical (31+ days)", content)
    
    def test_empty_data_handling(self):
        """Test handling of empty data"""
        with self.assertRaises(ValueError):
            self.builder.build_comprehensive_prompt("AAPL", [], "json")
    
    def test_system_prompt_structure(self):
        """Test system prompt structure"""
        system_prompt = self.builder._build_system_prompt("AAPL", "json")
        
        # Should contain all required sections
        required_sections = [
            "EXECUTIVE SUMMARY",
            "TECHNICAL ANALYSIS",
            "FUNDAMENTAL ANALYSIS",
            "MARKET SENTIMENT & NEWS",
            "MACROECONOMIC FACTORS",
            "RISK ASSESSMENT",
            "INVESTMENT RECOMMENDATION"
        ]
        
        for section in required_sections:
            self.assertIn(section, system_prompt)
        
        # Should contain guidelines
        self.assertIn("IMPORTANT GUIDELINES", system_prompt)
        self.assertIn("RESPONSE FORMAT", system_prompt)

if __name__ == '__main__':
    unittest.main()