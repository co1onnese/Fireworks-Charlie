"""Tests for FundamentalAnalyzer financial health scoring."""
import unittest

from data_collection.fundamental_analyzer import FundamentalAnalyzer


class TestFundamentalAnalyzerFinancialHealth(unittest.TestCase):
    """Validate financial health metrics and assessments."""

    def setUp(self):
        self.analyzer = FundamentalAnalyzer()

    def test_financial_health_metrics_net_cash(self):
        """Company with strong balance sheet should be marked healthy."""

        fundamentals = [{
            "total_assets": 2_000_000_000,
            "total_liabilities": 800_000_000,
            "stockholder_equity": 1_200_000_000,
            "total_debt": 300_000_000,
            "cash_and_equivalents": 600_000_000,
            "operating_income": 150_000_000,
        }]

        analysis = self.analyzer.analyze_fundamentals(fundamentals)
        health = analysis["financial_health"]

        self.assertIn("metrics", health)
        self.assertEqual(len(health["warnings"]), 0)
        self.assertEqual(health["assessment"], "Balance sheet appears healthy")
        self.assertGreater(health["metrics"]["equity_ratio"], 0.0)
        self.assertEqual(health["metrics"]["net_debt_status"], "Net cash position")

    def test_financial_health_flags_leverage_risks(self):
        """Highly levered company should trigger warnings and risk assessment."""

        fundamentals = [{
            "total_assets": 500_000_000,
            "total_liabilities": 450_000_000,
            "stockholder_equity": 50_000_000,
            "total_debt": 400_000_000,
            "cash_and_equivalents": 20_000_000,
            "operating_income": 15_000_000,
        }]

        analysis = self.analyzer.analyze_fundamentals(fundamentals)
        health = analysis["financial_health"]

        self.assertGreaterEqual(len(health["warnings"]), 1)
        self.assertEqual(health["assessment"], "Financial health presents notable risks")
        self.assertIn("debt_to_equity", health["metrics"])
        self.assertLess(health["metrics"]["cash_to_liabilities"], 0.2)


if __name__ == "__main__":
    unittest.main()
