import pandas as pd
import numpy as np
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Processes raw data fetched from EODHD.com API into a standardized format
    suitable for the Charlie-TR1-DB schema.
    """

    def __init__(self, target_tickers: list, start_date: str, end_date: str):
        self.target_tickers = [t.upper() for t in target_tickers]
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

    def _filter_by_date_and_ticker(
        self, df: pd.DataFrame, date_column: str, ticker_column: str
    ) -> pd.DataFrame:
        """
        Filters a DataFrame by date range and target tickers.
        Assumes date_column is already in datetime format or can be converted.
        """
        if df.empty:
            return df

        df[date_column] = pd.to_datetime(df[date_column])
        df = df[
            (df[date_column] >= self.start_date) & (df[date_column] <= self.end_date)
        ]
        df = df[df[ticker_column].isin(self.target_tickers)]
        return df

    def process_eod_data(self, raw_data: list, symbol: str) -> list:
        """
        Processes raw End-Of-Day data.
        Expected raw_data format: [{'date': 'YYYY-MM-DD', 'open': ..., 'high': ..., ...}]
        """
        if not raw_data:
            return []

        df = pd.DataFrame(raw_data)
        df["symbol"] = symbol.split(".")[
            0
        ].upper()  # Extract base symbol if it has exchange suffix
        df["date"] = pd.to_datetime(df["date"])
        df["interval"] = "1d"
        df = df.rename(columns={"adjusted_close": "adjusted_close"})

        # Filter by date and ticker
        df = self._filter_by_date_and_ticker(df, "date", "symbol")

        # Select and reorder columns to match DB schema
        columns = [
            "symbol",
            "date",
            "interval",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
        ]

        # Convert NaN to None for proper NULL handling in database
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")

        for record in processed_data:
            if record.get("transaction_date"):
                record["transaction_date"] = record["transaction_date"].date()
            if record.get("filing_date"):
                record["filing_date"] = record["filing_date"].date()

        return processed_data

    def process_intraday_data(self, raw_data: list, symbol: str, interval: str) -> list:
        """
        Processes raw Intraday data.
        Expected raw_data format: [{'datetime': 'YYYY-MM-DD HH:MM:SS', 'open': ..., 'high': ..., ...}]
        """
        if not raw_data:
            return []

        df = pd.DataFrame(raw_data)
        df["symbol"] = symbol.split(".")[0].upper()
        df = df.rename(columns={"datetime": "timestamp"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date  # Extract date part for filtering
        df["interval"] = interval

        # Filter by date and ticker
        df = self._filter_by_date_and_ticker(df, "date", "symbol")

        # Select and reorder columns to match DB schema
        columns = [
            "symbol",
            "date",
            "timestamp",
            "interval",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        # Convert NaN to None for proper NULL handling in database
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")
        return processed_data

    def process_technical_indicators(
        self, raw_data: dict, symbol: str, indicator_type: str
    ) -> list:
        """
        Processes raw Technical Indicators data.
        Expected raw_data format: {'<date>': {'<indicator_value>': ...}}
        Note: EODHD returns indicators in a dictionary where keys are dates.
        """
        if not raw_data:
            return []

        processed_list = []
        for date_str, values in raw_data.items():
            record = {
                "symbol": symbol.split(".")[0].upper(),
                "date": datetime.strptime(date_str, "%Y-%m-%d"),
                indicator_type.lower(): values[indicator_type],  # e.g., 'SMA' -> 'sma'
            }
            processed_list.append(record)

        df = pd.DataFrame(processed_list)
        df = self._filter_by_date_and_ticker(df, "date", "symbol")
        return df.to_dict(orient="records")

    def process_fundamentals(self, raw_data: dict, symbol: str) -> list:
        """
        Processes raw Fundamental Data into multiple quarterly records.
        Returns a list of fundamental records, one per quarter where filing_date is in range.

        Expected raw_data format: {'General': {...}, 'Highlights': {...}, 'Financials': {...}}
        """
        if not raw_data:
            return []

        symbol_clean = symbol.split(".")[0].upper()
        financials = raw_data.get("Financials", {})

        # Get quarterly data from all three financial statements
        balance_sheets = financials.get("Balance_Sheet", {}).get("quarterly", {})
        income_statements = financials.get("Income_Statement", {}).get("quarterly", {})
        cash_flows = financials.get("Cash_Flow", {}).get("quarterly", {})

        if not isinstance(balance_sheets, dict) or not isinstance(income_statements, dict):
            logger.warning(f"No quarterly data available for {symbol}")
            return []

        # Collect all unique quarter dates
        all_quarters = set(balance_sheets.keys()) | set(income_statements.keys()) | set(cash_flows.keys())

        processed_records = []

        for quarter_date_str in all_quarters:
            try:
                quarter_date = datetime.strptime(quarter_date_str, "%Y-%m-%d")

                # Get data from each financial statement
                bs_data = balance_sheets.get(quarter_date_str, {})
                inc_data = income_statements.get(quarter_date_str, {})
                cf_data = cash_flows.get(quarter_date_str, {})

                # Extract filing date (when this became public knowledge)
                filing_date_str = (
                    bs_data.get("filing_date") or
                    inc_data.get("filing_date") or
                    cf_data.get("filing_date")
                )

                if not filing_date_str:
                    logger.warning(f"No filing_date for {symbol} quarter {quarter_date_str}, skipping")
                    continue

                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")

                # Filter by filing date - only include quarters filed within our date range
                # This ensures point-in-time integrity: you only know data after it's filed
                if not (self.start_date <= filing_date <= self.end_date):
                    continue

                # Extract numerical fields, converting string numbers to proper types
                def safe_int(value):
                    """Safely convert to int, handling None and string values."""
                    if value is None or value == "":
                        return None
                    try:
                        return int(float(str(value)))
                    except (ValueError, TypeError):
                        return None

                # Create a record for this quarter
                highlights = raw_data.get("Highlights", {})

                def safe_float(value):
                    if value in (None, "", "NaN"):
                        return None
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None

                record = {
                    "symbol": symbol_clean,
                    "report_date": quarter_date,
                    "filing_date": filing_date,
                    # From Income Statement
                    "revenue": safe_int(inc_data.get("totalRevenue")),
                    "net_income": safe_int(inc_data.get("netIncome")),
                    "operating_income": safe_int(inc_data.get("operatingIncome")),
                    "gross_profit": safe_int(inc_data.get("grossProfit")),
                    "ebitda": safe_int(inc_data.get("ebitda")),
                    # From Balance Sheet
                    "total_assets": safe_int(bs_data.get("totalAssets")),
                    "total_liabilities": safe_int(bs_data.get("totalLiab")),
                    "stockholder_equity": safe_int(bs_data.get("totalStockholderEquity")),
                    "cash_and_equivalents": safe_int(bs_data.get("cashAndCashEquivalents")) or safe_int(bs_data.get("cash")) or safe_int(bs_data.get("cashAndShortTermInvestments")),
                    "total_debt": safe_int(bs_data.get("shortLongTermDebtTotal")) or safe_int(bs_data.get("totalDebt")) or safe_int(bs_data.get("longTermDebt")),
                    # From Cash Flow Statement
                    "operating_cash_flow": safe_int(cf_data.get("totalCashFromOperatingActivities")),
                    "free_cash_flow": safe_int(cf_data.get("freeCashFlow")),
                    # Store full quarterly data as JSON for detailed analysis
                    "balance_sheet_json": json.dumps(bs_data) if bs_data else None,
                    "income_statement_json": json.dumps(inc_data) if inc_data else None,
                    "cash_flow_json": json.dumps(cf_data) if cf_data else None,
                    # Snapshot metrics from highlights
                    "market_cap": safe_int(highlights.get("MarketCapitalization")),
                    "pe_ratio": safe_float(highlights.get("PERatio")),
                    "eps": safe_float(highlights.get("EarningsShare")),
                    "book_value": safe_float(highlights.get("BookValue")),
                }

                processed_records.append(record)

            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing quarter {quarter_date_str} for {symbol}: {e}")
                continue

        logger.info(f"Processed {len(processed_records)} quarterly fundamental records for {symbol}")
        return processed_records

    def process_news(self, raw_data: list, symbol: str) -> list:
        """
        Processes raw News data.
        Expected raw_data format: [{'date': 'YYYY-MM-DD HH:MM:SS', 'title': ..., 'content': ..., 'sentiment': ..., 'link': ...}]
        """
        if not raw_data:
            logger.debug(f"No raw news data to process for {symbol}")
            return []

        initial_count = len(raw_data)
        logger.debug(f"Processing {initial_count} raw news articles for {symbol}")

        df = pd.DataFrame(raw_data)
        df["symbol"] = symbol.split(".")[0].upper()
        df = df.rename(columns={"link": "url", "date": "published_at", "title": "headline"})
        df["published_at"] = pd.to_datetime(df["published_at"])
        
        # Extract sentiment polarity score (raw -1.0 to +1.0) and categorical sentiment
        df["sentiment_score"] = df["sentiment"].apply(
            lambda x: x.get("polarity") if isinstance(x, dict) and x.get("polarity") is not None else None
        )
        df["sentiment_label"] = df["sentiment"].apply(
            lambda x: (
                "positive" if x.get("polarity", 0) > 0.1
                else "negative" if x.get("polarity", 0) < -0.1
                else "neutral"
            ) if isinstance(x, dict) else None
        )
        df["sentiment"] = df["sentiment"].apply(
            lambda x: (
                "Positive" if x.get("polarity", 0) > 0.1
                else "Negative" if x.get("polarity", 0) < -0.1
                else "Neutral"
            ) if isinstance(x, dict) else None
        )
        df["date"] = df["published_at"].dt.date  # Extract date part for filtering

        # Filter by date and ticker
        pre_filter_count = len(df)
        df = self._filter_by_date_and_ticker(df, "date", "symbol")
        post_filter_count = len(df)
        
        if pre_filter_count > post_filter_count:
            filtered_out = pre_filter_count - post_filter_count
            logger.info(
                f"Filtered out {filtered_out} news articles for {symbol} "
                f"(outside date range {self.start_date.date()} to {self.end_date.date()})"
            )

        # Select and reorder columns to match DB schema
        columns = ["symbol", "published_at", "headline", "content", "sentiment", "sentiment_score", "sentiment_label", "url"]

        # Convert NaN to None for proper NULL handling in database
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")
        
        logger.info(
            f"Successfully processed {len(processed_data)} news articles for {symbol} "
            f"(from {initial_count} raw articles)"
        )
        
        return processed_data

    def process_insider_transactions(self, raw_data: list, symbol: str) -> list:
        """
        Processes raw Insider Transactions data.
        Expected raw_data format: [{'date': 'YYYY-MM-DD', 'ownerName': ..., 'transactionCode': ..., ...}]
        """
        if not raw_data:
            return []

        df = pd.DataFrame(raw_data)
        df["symbol"] = symbol.split(".")[0].upper()
        df = df.rename(
            columns={
                "date": "transaction_date",
                "ownerName": "owner_name",
                "transactionCode": "transaction_code",
                "transactionAmount": "transaction_amount",
                "transactionPrice": "transaction_price",
                "reportingOwnerRelationship": "owner_title",
                "filingDate": "filing_date",
                "shares": "shares",
                "sharesOwnedAfterTransaction": "shares_owned_after",
            }
        )
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        if "filing_date" in df.columns:
            df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
        df["date"] = df["transaction_date"].dt.date  # Extract date part for filtering

        # Normalize numeric columns
        numeric_columns = [
            "transaction_amount",
            "transaction_price",
            "shares",
            "shares_owned_after",
        ]
        integer_columns = ["shares", "shares_owned_after", "transaction_amount"]
        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")
                if column in integer_columns:
                    df[column] = df[column].apply(lambda x: int(x) if pd.notna(x) else None)

        # Filter by date and ticker
        df = self._filter_by_date_and_ticker(df, "date", "symbol")

        # Select and reorder columns to match DB schema
        columns = [
            "symbol",
            "transaction_date",
            "filing_date",
            "owner_name",
            "owner_title",
            "transaction_code",
            "shares",
            "transaction_price",
            "transaction_amount",
            "shares_owned_after",
        ]

        # Ensure all expected columns exist
        for col in columns:
            if col not in df.columns:
                df[col] = None

        # Convert NaN to None for proper NULL handling in database
        # PostgreSQL cannot store NaN in BIGINT columns
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")
        return processed_data

    def process_analyst_recommendations(self, raw_data: list, symbol: str) -> list:
        """
        Processes raw analyst recommendations data from Benzinga API.
        
        Expected raw_data format from Benzinga API:
        [{
            'id': 'uuid',
            'action': 'Reiterates',
            'rating': 'Buy',
            'pt': '155.00',
            'analyst_insights': '...',
            'firm': 'Goldman Sachs',
            'firm_id': '...',
            'rating_id': '...',
            'date': '2024-02-15',
            'updated': 1708018876,
            'security': {'symbol': 'AAPL', ...}
        }]
        
        Args:
            raw_data: List of analyst insight dictionaries from Benzinga API
            symbol: Ticker symbol (e.g., "AAPL")
            
        Returns:
            List of processed analyst recommendation dictionaries
        """
        if not raw_data:
            logger.debug(f"No raw analyst recommendations data to process for {symbol}")
            return []

        initial_count = len(raw_data)
        logger.debug(f"Processing {initial_count} raw analyst recommendations for {symbol}")

        processed_data = []
        symbol_clean = symbol.split(".")[0].upper()

        for insight in raw_data:
            try:
                # Validate that this insight is for the requested symbol
                security = insight.get("security", {})
                insight_symbol = security.get("symbol", "").upper()
                
                if insight_symbol != symbol_clean:
                    logger.debug(f"Skipping insight for {insight_symbol} (requested {symbol_clean})")
                    continue

                # Parse date
                date_str = insight.get("date", "")
                if not date_str:
                    logger.warning(f"Skipping insight with missing date: {insight.get('id')}")
                    continue
                
                try:
                    insight_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Invalid date format '{date_str}' for insight {insight.get('id')}")
                    continue

                # Filter by date range
                if insight_date < self.start_date.date() or insight_date > self.end_date.date():
                    continue

                # Parse target price (pt field is string, convert to float)
                target_price = None
                pt_str = insight.get("pt", "")
                if pt_str:
                    try:
                        target_price = float(pt_str)
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse target price '{pt_str}' for insight {insight.get('id')}")

                # Extract action field
                action = insight.get("action", "").strip()

                record = {
                    "symbol": symbol_clean,
                    "date": insight_date,
                    "firm": insight.get("firm", ""),
                    "firm_id": insight.get("firm_id"),
                    "analyst_insight_id": insight.get("id"),  # UUID from Benzinga
                    "rating_id": insight.get("rating_id"),
                    "action": action,
                    "rating": insight.get("rating", ""),  # "Buy", "Hold", "Sell", etc.
                    "target_price": target_price,
                    "analyst_insights": insight.get("analyst_insights", ""),  # Full text
                    "updated_timestamp": insight.get("updated"),  # Unix timestamp
                }

                processed_data.append(record)

            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Error processing analyst recommendation for {symbol}: {e}")
                continue

        logger.info(f"Processed {len(processed_data)} analyst recommendation records for {symbol} (from {initial_count} raw insights)")
        return processed_data

    def process_macro_indicators(
        self, raw_data: list, country: str, indicator_name: str
    ) -> list:
        """
        Processes raw Macroeconomic Indicators data.
        Expected raw_data format: [{'date': 'YYYY-MM-DD', 'value': ..., 'indicator': ..., 'country': ...}]
        """
        if not raw_data:
            return []

        df = pd.DataFrame(raw_data)
        df = df.rename(columns={"indicator": "indicator_name"})
        df["country"] = country.upper()
        df["date"] = pd.to_datetime(df["date"])
        df["unit"] = (
            None  # EODHD macro data often lacks explicit units in the main response, might need to infer or add manually
        )

        # Filter by date (no ticker filtering for macro data)
        df = df[(df["date"] >= self.start_date) & (df["date"] <= self.end_date)]

        # Select and reorder columns to match DB schema
        columns = ["country", "indicator_name", "date", "value", "unit"]

        # Convert NaN to None for proper NULL handling in database
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")
        return processed_data

    def process_fred_series(
        self, observations: list, series_info: dict, series_id: str
    ) -> list:
        """
        Processes FRED economic data series into database-ready format.

        Args:
            observations: List of observations from FRED API
                Format: [{"date": "YYYY-MM-DD", "value": "123.45"}, ...]
            series_info: Metadata from FRED API
                Format: {"title": "...", "frequency": "...", "units": "..."}
            series_id: FRED series ID (e.g., "GDPC1", "UNRATE")

        Returns:
            List of dictionaries ready for database insertion
        """
        if not observations:
            return []

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(observations)

        # Parse date column
        df["date"] = pd.to_datetime(df["date"])

        # Filter out missing values (FRED uses "." for missing data)
        df = df[df["value"] != "."]

        # Convert value to float
        df["value"] = df["value"].astype(float)

        # Filter by date range
        df = df[(df["date"] >= self.start_date) & (df["date"] <= self.end_date)]

        if df.empty:
            return []

        # Add metadata from series_info
        df["series_id"] = series_id
        df["country"] = "USA"  # FRED is US-only data
        df["indicator_name"] = series_info.get("title", series_id) if series_info else series_id
        df["frequency"] = series_info.get("frequency", None) if series_info else None
        df["unit"] = series_info.get("units", None) if series_info else None

        # Select columns to match database schema
        columns = ["series_id", "country", "indicator_name", "date", "value", "unit", "frequency"]

        # Convert NaN to None for proper NULL handling in database
        df = df.replace({np.nan: None})

        processed_data = df[columns].to_dict(orient="records")
        return processed_data


if __name__ == "__main__":
    # Example Usage
    TARGET_TICKERS = ["AAPL", "MSFT"]
    START_DATE = "2024-01-01"
    END_DATE = "2025-05-31"

    processor = DataProcessor(TARGET_TICKERS, START_DATE, END_DATE)

    # Example EOD Data
    raw_eod = [
        {
            "date": "2024-01-02",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 104,
            "adjusted_close": 103,
            "volume": 100000,
        },
        {
            "date": "2024-01-03",
            "open": 104,
            "high": 106,
            "low": 103,
            "close": 105,
            "adjusted_close": 104,
            "volume": 120000,
        },
        {
            "date": "2023-12-29",
            "open": 98,
            "high": 100,
            "low": 97,
            "close": 99,
            "adjusted_close": 98,
            "volume": 80000,
        },  # Outside date range
    ]
    processed_eod = processor.process_eod_data(raw_eod, "AAPL.US")
    logger.info(f"Processed EOD Data: {processed_eod}")

    # Example Fundamentals Data
    raw_fundamentals = {
        "General": {
            "Name": "Apple Inc.",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
            "LastUpdate": "2025-01-15T12:00:00",
        },
        "Highlights": {
            "MarketCapitalization": 3000000000000,
            "PERatio": 30.5,
            "EarningsShare": 6.0,
            "BookValue": 15.0,
        },
        "Financials": {
            "Balance_Sheet": {
                "quarterly": [
                    {"date": "2024-12-31", "assets": 1000},
                    {"date": "2024-09-30", "assets": 900},
                ]
            },
            "Income_Statement": {
                "quarterly": [
                    {"date": "2024-12-31", "revenue": 200},
                    {"date": "2024-09-30", "revenue": 180},
                ]
            },
            "Cash_Flow": {
                "quarterly": [
                    {"date": "2024-12-31", "cash_flow": 50},
                    {"date": "2024-09-30", "cash_flow": 45},
                ]
            },
        },
    }
    processed_fundamentals = processor.process_fundamentals(raw_fundamentals, "AAPL.US")
    logger.info(f"Processed Fundamentals Data: {processed_fundamentals}")

    # Example News Data
    raw_news = [
        {
            "date": "2024-03-10 10:30:00",
            "title": "Apple announces new product",
            "content": "...",
            "sentiment": {"sentiment": "Positive"},
            "link": "http://example.com/news1",
        },
        {
            "date": "2024-03-11 11:00:00",
            "title": "Market reacts to tech news",
            "content": "...",
            "sentiment": {"sentiment": "Neutral"},
            "link": "http://example.com/news2",
        },
        {
            "date": "2023-01-01 09:00:00",
            "title": "Old news",
            "content": "...",
            "sentiment": {"sentiment": "Negative"},
            "link": "http://example.com/oldnews",
        },  # Outside date range
    ]
    processed_news = processor.process_news(raw_news, "AAPL.US")
    logger.info(f"Processed News Data: {processed_news}")

    # Example Insider Transactions Data
    raw_insider = [
        {
            "date": "2024-02-01",
            "ownerName": "Tim Cook",
            "transactionCode": "P",
            "transactionAmount": 10000,
            "transactionPrice": 170.0,
        },
        {
            "date": "2024-02-05",
            "ownerName": "Luca Maestri",
            "transactionCode": "S",
            "transactionAmount": 5000,
            "transactionPrice": 172.0,
        },
        {
            "date": "2023-01-01",
            "ownerName": "Old Insider",
            "transactionCode": "P",
            "transactionAmount": 100,
            "transactionPrice": 150.0,
        },  # Outside date range
    ]
    processed_insider = processor.process_insider_transactions(raw_insider, "AAPL.US")
    logger.info(f"Processed Insider Transactions Data: {processed_insider}")

    # Example Macroeconomic Indicators Data
    raw_macro = [
        {
            "date": "2024-03-01",
            "value": 3.5,
            "indicator": "gdp_growth_annual",
            "country": "USA",
        },
        {
            "date": "2024-06-01",
            "value": 3.2,
            "indicator": "gdp_growth_annual",
            "country": "USA",
        },
        {
            "date": "2023-01-01",
            "value": 2.0,
            "indicator": "gdp_growth_annual",
            "country": "USA",
        },  # Outside date range
    ]
    processed_macro = processor.process_macro_indicators(
        raw_macro, "USA", "gdp_growth_annual"
    )
    logger.info(f"Processed Macroeconomic Indicators Data: {processed_macro}")
