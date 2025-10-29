"""
FRED API Client for Federal Reserve Economic Data

This module provides a client for fetching macroeconomic indicators from the
Federal Reserve Economic Data (FRED) API maintained by the St. Louis Fed.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
"""

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FREDClient:
    """
    Client for interacting with the Federal Reserve Economic Data (FRED) API.

    Rate Limit: 120 requests per minute
    """

    BASE_URL = "https://api.stlouisfed.org/fred"
    RATE_LIMIT_DELAY = 0.5  # 0.5 seconds = 120 requests/minute max

    def __init__(self, api_key: str):
        """
        Initialize the FRED API client.

        Args:
            api_key: 32-character FRED API key from fredaccount.stlouisfed.org
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting to stay under 120 requests/minute."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP GET request to the FRED API with retry logic.

        Args:
            endpoint: API endpoint (e.g., 'series/observations')
            params: Query parameters (api_key and file_type=json added automatically)
            max_retries: Number of retry attempts on failure

        Returns:
            JSON response as dictionary, or None on failure
        """
        url = f"{self.BASE_URL}/{endpoint}"

        # Add API key and JSON format to all requests
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        params["file_type"] = "json"

        for attempt in range(1, max_retries + 1):
            try:
                self._rate_limit()  # Enforce rate limiting

                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                return response.json()

            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    logger.warning(f"FRED series or endpoint not found (404): {endpoint}")
                    return None
                elif response.status_code == 429:
                    logger.warning(f"FRED rate limit exceeded (429). Waiting before retry {attempt}/{max_retries}...")
                    time.sleep(60)  # Wait 1 minute before retry
                else:
                    logger.error(f"HTTP error on attempt {attempt}/{max_retries} for {endpoint}: {e}")
                    if attempt == max_retries:
                        return None
                    time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt}/{max_retries} for {endpoint}: {e}")
                if attempt == max_retries:
                    return None
                time.sleep(2 ** attempt)

        return None

    def get_series_info(self, series_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a FRED economic data series.

        Args:
            series_id: FRED series identifier (e.g., 'GDPC1', 'UNRATE')

        Returns:
            Dictionary with series metadata including:
            - id: Series ID
            - title: Full series name
            - frequency: Data frequency (Daily, Monthly, Quarterly, Annual, etc.)
            - units: Units of measurement
            - seasonal_adjustment: Seasonal adjustment status
            - last_updated: Last update timestamp

        Example:
            {
                "id": "GDPC1",
                "title": "Real Gross Domestic Product",
                "frequency": "Quarterly",
                "units": "Billions of Chained 2017 Dollars",
                "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
                "last_updated": "2024-01-25 07:52:08-06"
            }
        """
        endpoint = "series"
        params = {"series_id": series_id}

        response = self._make_request(endpoint, params)

        if response and "seriess" in response and len(response["seriess"]) > 0:
            return response["seriess"][0]

        logger.warning(f"No metadata found for FRED series: {series_id}")
        return None

    def get_series_observations(
        self, series_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get observation data (actual values) for a FRED economic data series.

        Args:
            series_id: FRED series identifier (e.g., 'GDPC1', 'UNRATE')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of observations, each containing:
            - date: Observation date (YYYY-MM-DD)
            - value: Data value (as string, may be '.' for missing)

        Example:
            [
                {"date": "2024-01-01", "value": "27365.189"},
                {"date": "2024-04-01", "value": "27534.345"}
            ]
        """
        endpoint = "series/observations"
        params = {
            "series_id": series_id,
            "observation_start": start_date,
            "observation_end": end_date,
        }

        response = self._make_request(endpoint, params)

        if response and "observations" in response:
            observations = response["observations"]
            logger.info(f"Fetched {len(observations)} observations for {series_id} from {start_date} to {end_date}")
            return observations

        logger.warning(f"No observations found for FRED series: {series_id}")
        return []


if __name__ == "__main__":
    # Example usage and testing
    import os

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, continue without it

    API_KEY = os.getenv("FRED_API_KEY")

    if not API_KEY or API_KEY == "YOUR_FRED_API_KEY":
        logger.error("FRED_API_KEY not set in environment. Please configure .env file.")
    else:
        try:
            client = FREDClient(API_KEY)
            logger.info("FREDClient initialized. Testing with GDPC1 (Real GDP)...")

            # Test 1: Get series metadata
            info = client.get_series_info("GDPC1")
            if info:
                logger.info(f"Series Info: {info['title']} ({info['frequency']}, {info['units']})")

            # Test 2: Get recent observations
            observations = client.get_series_observations("GDPC1", "2024-01-01", "2024-12-31")
            if observations:
                logger.info(f"Sample observation: {observations[0]}")

        except Exception as e:
            logger.error(f"Error testing FRED client: {e}")
