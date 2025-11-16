"""
Benzinga API Client for Analyst Insights

This module provides a client for interacting with the Benzinga API
to fetch analyst recommendations and insights.
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


class BenzingaClient:
    """
    Client for interacting with the Benzinga API, handling authentication,
    rate limiting, pagination, and basic error handling.
    """

    BASE_URL = "https://api.benzinga.com/api/v1/"
    # Benzinga API rate limits vary by plan
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
        Makes a GET request to the Benzinga API with retry mechanism.
        
        Args:
            endpoint: API endpoint (e.g., "analyst/insights")
            params: Query parameters (token will be added automatically)
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON response (dict or list)
        """
        self._wait_for_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        all_params: Dict[str, Any] = {"token": self.api_key}
        if params:
            all_params.update(params)

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=all_params, timeout=30)
                response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                return response.json()
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
                else:
                    if attempt == max_retries - 1:
                        raise  # Re-raise on last attempt
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

    def get_analyst_insights(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetches analyst insights/recommendations for given ticker symbols.
        
        Note: The Benzinga API may not support date filtering in query parameters.
        Results will be filtered client-side by the `date` field if start_date/end_date are provided.
        
        Args:
            symbols: List of ticker symbols (e.g., ["AAPL", "MSFT"])
            start_date: Start date string (YYYY-MM-DD) - optional, for client-side filtering
            end_date: End date string (YYYY-MM-DD) - optional, for client-side filtering
            page: Page number for pagination (default: 1)
            page_size: Number of items per page (default: 100, max: 100)
            
        Returns:
            List of analyst insight dictionaries
        """
        endpoint = "analyst/insights"
        
        # Convert symbols list to CSV string
        symbols_csv = ",".join(symbols)
        
        # Prepare query parameters
        params = {
            "symbols": symbols_csv,
            "page": page,
            "pageSize": min(page_size, 100),  # Cap at 100 (API max)
        }
        
        all_insights = []
        current_page = page
        
        # Handle pagination - fetch all pages
        while True:
            params["page"] = current_page
            logger.info(f"Fetching analyst insights page {current_page} for symbols: {symbols_csv}")
            
            response = self._make_request(endpoint, params)
            
            if isinstance(response, list):
                if not response:  # Empty list means no more results
                    logger.info(f"No more results at page {current_page}")
                    break
                
                # Filter by date if provided (client-side filtering)
                if start_date or end_date:
                    filtered_response = []
                    for insight in response:
                        insight_date = insight.get("date", "")
                        if start_date and insight_date < start_date:
                            continue
                        if end_date and insight_date > end_date:
                            continue
                        filtered_response.append(insight)
                    response = filtered_response
                
                all_insights.extend(response)
                logger.info(f"Fetched {len(response)} insights from page {current_page}")
                
                # If we got fewer results than page_size, we've reached the last page
                if len(response) < params["pageSize"]:
                    logger.info(f"Reached last page (got {len(response)} items, page size is {params['pageSize']})")
                    break
                
                # Move to next page
                current_page += 1
                
            elif isinstance(response, dict):
                # API might return error or metadata in dict format
                if "error" in response:
                    logger.error(f"API error: {response.get('error')}")
                    break
                else:
                    logger.warning(f"Unexpected dict response: {response}")
                    break
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                break
        
        logger.info(f"Total analyst insights fetched: {len(all_insights)}")
        return all_insights


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    API_KEY = os.environ.get("BENZINGA_API_KEY", "")
    
    if not API_KEY:
        logger.warning("BENZINGA_API_KEY not found in environment variables.")
        print("Skipping live API test due to missing API key.")
    else:
        try:
            client = BenzingaClient(API_KEY)
            print("BenzingaClient initialized. Testing analyst insights fetch...")
            
            # Example: Fetch analyst insights for AAPL
            # insights = client.get_analyst_insights(
            #     symbols=["AAPL"],
            #     start_date="2024-01-01",
            #     end_date="2024-12-31"
            # )
            # logger.info(f"AAPL Analyst Insights (first entry): {insights[0] if insights else 'No insights'}")
            
            logger.info("BenzingaClient test complete.")
            
        except ValueError as e:
            logger.error(f"Initialization error: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
