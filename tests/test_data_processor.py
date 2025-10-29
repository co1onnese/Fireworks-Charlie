"""Unit tests for DataProcessor transformations."""
import unittest
from datetime import datetime, date

from data_collection.data_processor import DataProcessor


class TestDataProcessor(unittest.TestCase):
    """Validate DataProcessor enrichment logic."""

    def setUp(self):
        self.processor = DataProcessor(["AAPL"], "2024-01-01", "2024-12-31")

    def test_process_fundamentals_enriches_metrics(self):
        """Quartely fundamentals should include cash, debt, and snapshot metrics."""

        raw_fundamentals = {
            "Highlights": {
                "MarketCapitalization": "150000000000",
                "PERatio": "28.5",
                "EarningsShare": "6.12",
                "BookValue": "22.1",
            },
            "Financials": {
                "Balance_Sheet": {
                    "quarterly": {
                        "2024-03-31": {
                            "filing_date": "2024-05-01",
                            "totalAssets": "200000000000",
                            "totalLiab": "80000000000",
                            "totalStockholderEquity": "120000000000",
                            "cashAndCashEquivalents": "40000000000",
                            "shortLongTermDebtTotal": "35000000000",
                        }
                    }
                },
                "Income_Statement": {
                    "quarterly": {
                        "2024-03-31": {
                            "filing_date": "2024-05-01",
                            "totalRevenue": "90000000000",
                            "netIncome": "25000000000",
                            "operatingIncome": "28000000000",
                            "grossProfit": "42000000000",
                            "ebitda": "45000000000",
                        }
                    }
                },
                "Cash_Flow": {
                    "quarterly": {
                        "2024-03-31": {
                            "filing_date": "2024-05-01",
                            "totalCashFromOperatingActivities": "32000000000",
                            "freeCashFlow": "29000000000",
                        }
                    }
                },
            },
        }

        results = self.processor.process_fundamentals(raw_fundamentals, "AAPL.US")
        self.assertEqual(len(results), 1)
        record = results[0]

        expected_keys = {
            "cash_and_equivalents",
            "total_debt",
            "operating_cash_flow",
            "free_cash_flow",
            "market_cap",
            "pe_ratio",
            "eps",
            "ebitda",
        }

        self.assertTrue(expected_keys.issubset(record.keys()))
        self.assertEqual(record["market_cap"], 150_000_000_000)
        self.assertEqual(record["pe_ratio"], 28.5)
        self.assertEqual(record["cash_and_equivalents"], 40_000_000_000)

    def test_process_insider_transactions_schema_alignment(self):
        """Insider transactions should map to ORM column names."""

        raw_transactions = [
            {
                "date": "2024-06-01",
                "filingDate": "2024-06-03",
                "ownerName": "Jane Doe",
                "reportingOwnerRelationship": "CFO",
                "transactionCode": "P",
                "transactionAmount": "125000",
                "transactionPrice": "125.0",
                "shares": "1000",
                "sharesOwnedAfterTransaction": "5000",
            }
        ]

        results = self.processor.process_insider_transactions(raw_transactions, "AAPL.US")
        self.assertEqual(len(results), 1)
        record = results[0]

        self.assertEqual(record["owner_name"], "Jane Doe")
        self.assertEqual(record["owner_title"], "CFO")
        self.assertEqual(record["transaction_code"], "P")
        self.assertEqual(record["shares"], 1000)
        self.assertEqual(record["transaction_amount"], 125000)
        self.assertEqual(record["transaction_price"], 125.0)

        self.assertIsInstance(record["transaction_date"], date)
        self.assertIsInstance(record["filing_date"], date)


if __name__ == "__main__":
    unittest.main()
