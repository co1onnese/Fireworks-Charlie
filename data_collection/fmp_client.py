"""
Financial Modeling Prep (FMP) API Client for Historical Grades

This module provides a client for interacting with the FMP API
to fetch historical analyst grades/recommendations.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


JSONDict = Dict[str, Any]
JSONList = List[Any]
JSONResponse = Union[JSONDict, JSONList]


class FMPClient:
    """
    Client for interacting with the Financial Modeling Prep (FMP) API,
    specifically for historical grades/analyst recommendations.
    Handles authentication, rate limiting, and basic error handling.
    """

    BASE_URL = "https://financialmodelingprep.com/stable/"
    # FMP API rate limits vary by plan
    # Conservative default: 1 request per 0.5 seconds (2 requests/second)
    REQUEST_INTERVAL = 0.5  # seconds

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
        Makes a GET request to the FMP API with retry mechanism.
        
        Args:
            endpoint: API endpoint (e.g., "historical-grades/AAPL")
            params: Query parameters (apikey will be added automatically)
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response (dict or list)
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        all_params: Dict[str, Any] = {"apikey": self.api_key}
        if params:
            all_params.update(params)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=all_params, timeout=30)
                
                # Log request details for debugging (without exposing full API key)
                if attempt == 0:  # Only log on first attempt
                    logger.debug(
                        f"FMP API request: {endpoint} with params: "
                        f"{', '.join([k for k in all_params.keys() if k != 'apikey'])}"
                    )
                
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                json_response = response.json()
                
                # Check for error messages in response
                if isinstance(json_response, dict) and "Error Message" in json_response:
                    error_msg = json_response["Error Message"]
                    logger.warning(
                        f"FMP API returned error message: {error_msg}. "
                        f"This may indicate: (1) API key lacks access to this endpoint, "
                        f"(2) Legacy endpoint requires subscription upgrade, or "
                        f"(3) Invalid parameters. "
                        f"Returning empty list to allow backfill to continue. "
                        f"Analyst recommendations are optional for training data."
                    )
                    return []  # Return empty list instead of crashing - analyst recommendations are optional
                
                return json_response
            except requests.exceptions.HTTPError as e:
                logger.error(
                    f"HTTP error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                if response.status_code == 429:  # Too Many Requests
                    logger.warning("Rate limit hit. Retrying with exponential backoff.")
                    time.sleep(2**attempt)  # Exponential backoff
                elif response.status_code == 404:  # Not Found
                    logger.warning(f"Endpoint {endpoint} not found (404).")
                    return []  # Return empty list instead of crashing
                elif response.status_code == 401:  # Unauthorized
                    logger.error("Authentication failed. Check API key.")
                    raise
                elif response.status_code == 500:  # Internal Server Error
                    error_msg = response.text[:200] if response.text else "Empty response body"
                    logger.warning(
                        f"FMP API returned 500 Internal Server Error for {endpoint}. "
                        f"Response: {error_msg}. "
                        f"This may indicate: (1) API key lacks access to this endpoint, "
                        f"(2) Server-side issues, or (3) Invalid parameters. "
                        f"Returning empty list to allow backfill to continue. "
                        f"Analyst recommendations are optional for training data."
                    )
                    return []  # Return empty list instead of crashing - analyst recommendations are optional
                else:
                    if attempt == max_retries - 1:
                        logger.warning(
                            f"Failed after {max_retries} attempts with status {response.status_code}. "
                            f"Returning empty list to allow backfill to continue."
                        )
                        return []  # Return empty list on final failure instead of crashing
                    time.sleep(2**attempt)  # Exponential backoff
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Connection error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    raise
            except requests.exceptions.Timeout as e:
                logger.error(
                    f"Timeout error on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"An unexpected request error occurred on attempt {attempt + 1}/{max_retries} for {endpoint}: {e}"
                )
                raise

        logger.error(
            f"Failed to fetch data from {endpoint} after {max_retries} attempts."
        )
        return []

    def get_historical_grades(
        self,
        symbol: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches historical analyst grades/recommendations for a given ticker symbol.
        
        API Endpoint: GET /stable/grades-historical?symbol={symbol}
        Documentation: https://site.financialmodelingprep.com/developer/docs#historical-grades
        
        Note: This endpoint returns aggregated rating counts per date, not individual recommendations.
        
        Args:
            symbol: Ticker symbol (e.g., "AAPL")
            limit: Optional limit on number of results to return
            
        Returns:
            List of historical grade dictionaries with aggregated counts:
            - symbol: Ticker symbol
            - date: Date of the ratings snapshot (YYYY-MM-DD)
            - analystRatingsStrongBuy: Count of Strong Buy ratings
            - analystRatingsBuy: Count of Buy ratings
            - analystRatingsHold: Count of Hold ratings
            - analystRatingsSell: Count of Sell ratings
            - analystRatingsStrongSell: Count of Strong Sell ratings
        """
        endpoint = "grades-historical"
        
        # Prepare query parameters
        params = {"symbol": symbol.upper()}
        if limit:
            params["limit"] = limit
        
        logger.info(f"Fetching historical grades for symbol: {symbol}")
        
        response = self._make_request(endpoint, params)
        
        if isinstance(response, list):
            # Filter by limit if provided
            if limit and len(response) > limit:
                response = response[:limit]
            logger.info(f"Fetched {len(response)} historical grades for {symbol}")
            return response
        elif isinstance(response, dict):
            # API might return error or metadata in dict format
            if "Error Message" in response:
                logger.warning(f"API error: {response.get('Error Message')}")
                return []
            else:
                logger.warning(f"Unexpected dict response: {response}")
                return []
        else:
            logger.warning(f"Unexpected response type: {type(response)}")
            return []


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    API_KEY = os.environ.get("FMP_API_KEY", "")
    
    if not API_KEY:
        logger.warning("FMP_API_KEY not found in environment variables.")
        print("Skipping live API test due to missing API key.")
    else:
        try:
            client = FMPClient(API_KEY)
            print("FMPClient initialized. Testing historical grades fetch...")
            
            # Example: Fetch historical grades for AAPL
            grades = client.get_historical_grades("AAPL", limit=10)
            if grades:
                logger.info(f"AAPL Historical Grades (first entry): {grades[0]}")
            else:
                logger.info("No historical grades returned (may require subscription upgrade)")
            
            logger.info("FMPClient test complete.")
            
        except ValueError as e:
            logger.error(f"Initialization error: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
