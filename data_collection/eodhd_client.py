import logging
import time
from typing import Any, Dict, List, Optional, Union

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


JSONDict = Dict[str, Any]
JSONList = List[Any]
JSONResponse = Union[JSONDict, JSONList]


class EODHDClient:
    """
    Client for interacting with the EODHD.com API, handling authentication,
    rate limiting, and basic error handling.
    """

    BASE_URL = "https://eodhd.com/api/"
    # EODHD.com allows 1000 requests/minute for ALL-IN-ONE package
    # This translates to 1 request every 0.06 seconds.
    # To be safe, we'll set it to 0.1 seconds per request (10 requests/second).
    REQUEST_INTERVAL = 0.06  # seconds

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.api_key = api_key
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """Waits to ensure compliance with API rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            sleep_time = self.REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> JSONResponse:
        """
        Makes a GET request to the EODHD API with retry mechanism.
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        all_params: Dict[str, Any] = {"api_token": self.api_key}
        if params:
            all_params.update(params)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=all_params, timeout=10)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                return response.json()
            except requests.exceptions.HTTPError as e:
                logger.error(
                    f"HTTP error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                if response.status_code == 429:  # Too Many Requests
                    logger.warning("Rate limit hit. Retrying with exponential backoff.")
                    time.sleep(2**attempt)  # Exponential backoff
                elif response.status_code == 404:  # Not Found - endpoint may not exist or be unavailable
                    logger.warning(f"Endpoint {endpoint} not found (404). This feature may not be available for your API tier.")
                    return []  # Return empty list/dict instead of crashing
                else:
                    raise  # Re-raise for other HTTP errors
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Connection error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                time.sleep(2**attempt)  # Exponential backoff
            except requests.exceptions.Timeout as e:
                logger.error(
                    f"Timeout error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                time.sleep(2**attempt)  # Exponential backoff
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"An unexpected request error occurred on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                raise

        logger.error(
            f"Failed to fetch data from {endpoint} after {max_retries} attempts."
        )
        return {}

    # --- Data Fetcher Functions (to be implemented in the next phase) ---
    # These methods will call _make_request with specific endpoints and parameters.
    # For example:
    def get_eod_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetches End-Of-Day Historical Stock Market Data."""
        endpoint = f"eod/{symbol}"
        params = {"from": start_date, "to": end_date, "fmt": "json"}
        response = self._make_request(endpoint, params)
        if isinstance(response, list):
            return response
        logger.error("Expected list response for EOD data, received dict.")
        return []

    def get_intraday_data(
        self, symbol: str, interval: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetches Intraday Historical Stock Price Data."""
        endpoint = f"intraday/{symbol}"
        params = {"interval": interval, "from": start_date, "to": end_date, "fmt": "json"}
        response = self._make_request(endpoint, params)
        if isinstance(response, list):
            return response
        logger.error("Expected list response for intraday data, received dict.")
        return []

    def get_technical_indicators(
        self, symbol: str, indicator: str, start_date: str, end_date: str, **kwargs
    ) -> Dict[str, Any]:
        """Fetches Technical Analysis Indicators."""
        endpoint = f"indicators/{symbol}"
        params = {"function": indicator, "from": start_date, "to": end_date}
        params.update(kwargs)
        response = self._make_request(endpoint, params)
        if isinstance(response, dict):
            return response
        logger.error(
            "Expected dict response for technical indicators, received list."
        )
        return {}

    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Fetches Fundamental Data for Stocks, ETFs, Mutual Funds, Indices."""
        endpoint = f"fundamentals/{symbol}"
        response = self._make_request(endpoint)
        if isinstance(response, dict):
            return response
        logger.error("Expected dict response for fundamentals, received list.")
        return {}

    def get_news(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetches Financial News Feed and Stock News Sentiment data."""
        endpoint = "news"
        params = {"s": symbol, "from": start_date, "to": end_date}
        response = self._make_request(endpoint, params)
        if isinstance(response, list):
            return response
        logger.error("Expected list response for news, received dict.")
        return []

    def get_insider_transactions(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Fetches Insider Transactions (SEC "Form 4").
        Note: The API returns all transactions within the date range.
        Client-side filtering by symbol may be required.
        """
        endpoint = "insider-transactions"
        params = {"s": symbol, "from": start_date, "to": end_date, "limit": 1000, "fmt": "json"}
        response = self._make_request(endpoint, params)
        if isinstance(response, list):
            # Filter to only include transactions for the requested symbol
            symbol_code = symbol.split(".")[0].upper()
            filtered = [t for t in response if t.get("code", "").upper() == symbol_code]
            return filtered
        logger.error(
            "Expected list response for insider transactions, received dict."
        )
        return []

    def get_macro_indicators(
        self, country: str, indicator: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetches Macroeconomic Indicators."""
        # EODHD has two macro APIs: 'macro-indicators' and 'macro-data'
        # For simplicity, we'll use 'macro-data' which seems more general for specific indicators
        endpoint = "macro-data"
        params = {
            "country": country,
            "indicator": indicator,
            "from": start_date,
            "to": end_date,
        }
        response = self._make_request(endpoint, params)
        if isinstance(response, list):
            return response
        logger.error(
            "Expected list response for macro indicators, received dict."
        )
        return []


if __name__ == "__main__":
    # Example Usage (replace with your actual API key and desired data)
    # For demonstration, we'll use a placeholder API key.
    # In a real scenario, you'd load this from an environment variable or config file.
    API_KEY = "YOUR_EODHD_API_KEY"

    if API_KEY == "YOUR_EODHD_API_KEY":
        logger.warning(
            "Please replace 'YOUR_EODHD_API_KEY' with your actual EODHD API key."
        )
        # For testing purposes without a real API key, we can mock the request
        # or skip the actual API call.
        print("Skipping live API test due to placeholder API key.")
    else:
        try:
            client = EODHDClient(API_KEY)
            print("EODHDClient initialized. Testing data fetcher functions...")

            # Example: Fetch EOD data for AAPL
            # eod_data = client.get_eod_data(symbol="AAPL.US", start_date="2023-01-01", end_date="2023-01-05")
            # logger.info(f"AAPL EOD Data (first 2 entries): {eod_data[:2]}")

            # Example: Fetch fundamentals for AAPL
            # fundamentals = client.get_fundamentals(symbol="AAPL.US")
            # logger.info(f"AAPL Fundamentals (first few keys): {list(fundamentals.keys())[:5]}")

            # Example: Fetch news for AAPL
            # news = client.get_news(symbol="AAPL.US", start_date="2023-01-01", end_date="2023-01-05")
            # logger.info(f"AAPL News (first entry title): {news[0]["title"] if news else "No news"}")

            # Example: Fetch insider transactions for AAPL
            # insider_transactions = client.get_insider_transactions(symbol="AAPL.US", start_date="2023-01-01", end_date="2023-01-05")
            # logger.info(f"AAPL Insider Transactions (first entry): {insider_transactions[0] if insider_transactions else "No insider transactions"}")

            # Example: Fetch macroeconomic indicator (GDP Growth) for USA
            # macro_data = client.get_macro_indicators(country="USA", indicator="gdp_growth_annual", start_date="2023-01-01", end_date="2023-12-31")
            # logger.info(f"USA GDP Growth (first entry): {macro_data[0] if macro_data else "No macro data"}")

            logger.info(
                "Data fetcher functions implemented and conceptual testing complete."
            )

        except ValueError as e:
            logger.error(f"Initialization error: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
