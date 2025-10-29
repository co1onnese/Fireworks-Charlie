"""
DeepSeek API client for direct DeepSeek V3 integration
Uses OpenAI-compatible API endpoint
"""
import logging
import time
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    Client for direct interaction with DeepSeek V3 API

    Uses OpenAI-compatible API with DeepSeek's base URL.
    Designed as a drop-in replacement for FireworksDeepSeekClient.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout: int = 60
    ):
        """
        Initialize DeepSeek client

        Args:
            api_key: DeepSeek API key (starts with sk-)
            model_name: Model identifier (deepseek-chat or deepseek-reasoner)
            base_url: DeepSeek API base URL
            max_tokens: Maximum tokens in response
            temperature: Generation temperature (must be > 0 for GRPO)
            timeout: Request timeout in seconds
        """
        if temperature <= 0:
            logger.warning(
                f"Temperature {temperature} is ≤ 0. GRPO requires temperature > 0 for exploration. "
                "Setting to 0.7"
            )
            temperature = 0.7

        # Initialize OpenAI client with DeepSeek base URL
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

        self.model = model_name
        self.max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(
            f"Initialized DeepSeek client with model: {self.model} "
            f"(base: {base_url}, temp: {temperature})"
        )

    def generate_thesis(
        self,
        prompt: str,
        ticker: str,
        as_of_date: str,
        temperature: Optional[float] = None,
        response_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate investment thesis using DeepSeek V3

        Args:
            prompt: The cumulative data prompt (user message)
            ticker: Stock ticker for context
            as_of_date: Analysis date
            temperature: Generation temperature (defaults to self.default_temperature)
            response_format: "json" or "xml" (default: json for RLVR compatibility)

        Returns:
            Dictionary with:
            - status: "success" or "error"
            - system_prompt: The system prompt used (for RLVR)
            - user_prompt: The user prompt used (for RLVR)
            - assistant_response: Full JSON response from model
            - reasoning: Extracted reasoning text
            - action: Predicted action (strong_buy, buy, hold, sell, strong_sell)
            - support: Supporting evidence
            - metadata: Generation metrics
        """
        if temperature is None:
            temperature = self.default_temperature

        # System prompt for JSON response format
        if response_format == "json":
            system_prompt = """You are a senior financial analyst with deep expertise in equity research and investment analysis.

Your task is to generate investment theses based on comprehensive market data. You must:
1. Analyze ALL provided data thoroughly
2. Identify key patterns and correlations
3. Generate clear, actionable recommendations

IMPORTANT: Respond ONLY with a JSON object containing exactly these fields:
{
    "reasoning": "Detailed analysis with specific data points and logic",
    "action": "strong_buy|buy|hold|sell|strong_sell",
    "support": "Key evidence supporting the recommendation"
}

Action definitions:
- strong_buy: High confidence in significant upside (>3%)
- buy: Positive outlook with moderate upside (>2%)
- hold: Neutral outlook or high uncertainty (-1% to +1%)
- sell: Negative outlook with downside risk (<-2%)
- strong_sell: High confidence in significant downside (<-3%)

Do NOT include any text before or after the JSON object."""
        else:
            # XML format (for backwards compatibility)
            system_prompt = """You are a senior financial analyst with deep expertise in equity research and investment analysis.

Your task is to generate investment theses based on comprehensive market data. You must:
1. Analyze ALL provided data thoroughly
2. Identify key patterns and correlations
3. Generate clear, actionable recommendations

Respond in XML format with the following structure:
<thesis>
    <reasoning>Detailed analysis with specific data points and logic</reasoning>
    <action>strong_buy|buy|hold|sell|strong_sell</action>
    <support>Key evidence supporting the recommendation</support>
</thesis>"""

        # User prompt includes the ticker context
        user_prompt = f"""Ticker: {ticker}
Analysis Date: {as_of_date}

{prompt}"""

        try:
            start_time = time.time()

            # Make API call using OpenAI SDK
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=self.max_tokens
            )

            generation_time = time.time() - start_time

            # Extract response content
            assistant_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                f"Generated thesis for {ticker} on {as_of_date} "
                f"in {generation_time:.2f}s using {tokens_used} tokens"
            )

            # Parse response based on format
            if response_format == "json":
                parsed_response = self._parse_json_response(assistant_content)
            else:
                parsed_response = self._parse_xml_response(assistant_content)

            if not parsed_response:
                return {
                    "status": "error",
                    "error": "Failed to parse response",
                    "raw_response": assistant_content
                }

            return {
                "status": "success",
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "assistant_response": parsed_response,
                "reasoning": parsed_response.get("reasoning", ""),
                "action": parsed_response.get("action", "hold"),
                "support": parsed_response.get("support", ""),
                "metadata": {
                    "model": self.model,
                    "tokens_used": tokens_used,
                    "generation_time": round(generation_time, 2),
                    "temperature": temperature,
                    "ticker": ticker,
                    "as_of_date": as_of_date
                }
            }

        except Exception as e:
            logger.error(f"Error generating thesis for {ticker}: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            return {
                "status": "error",
                "error": str(e),
                "ticker": ticker,
                "as_of_date": as_of_date
            }

    def generate_multi_response(
        self,
        prompt: str,
        ticker: str,
        as_of_date: str,
        num_responses: int = 4,
        temperature: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple responses for GRPO training

        Args:
            prompt: The cumulative data prompt
            ticker: Stock ticker
            as_of_date: Analysis date
            num_responses: Number of responses to generate (2-8)
            temperature: Generation temperature

        Returns:
            List of response dictionaries
        """
        if temperature is None:
            temperature = self.default_temperature

        responses = []
        for i in range(num_responses):
            logger.info(f"Generating response {i+1}/{num_responses} for {ticker}")
            response = self.generate_thesis(
                prompt=prompt,
                ticker=ticker,
                as_of_date=as_of_date,
                temperature=temperature,
                response_format="json"
            )
            responses.append(response)

            # Small delay to avoid rate limits
            if i < num_responses - 1:
                time.sleep(0.5)

        return responses

    def test_connection(self) -> bool:
        """
        Test DeepSeek API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'OK' if you can hear me."}
                ],
                max_tokens=10,
                temperature=0.1
            )

            content = response.choices[0].message.content
            logger.info(f"✓ DeepSeek API connection successful: {content}")
            return True

        except Exception as e:
            logger.error(f"✗ DeepSeek API connection failed: {e}")
            return False

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON response from model

        Args:
            response: Raw response string

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Try direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                try:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    json_str = response[json_start:json_end].strip()
                    return json.loads(json_str)
                except:
                    pass

            # Try to extract JSON object
            if "{" in response and "}" in response:
                try:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                except:
                    pass

            logger.error(f"Failed to parse JSON response: {response[:200]}")
            return None

    def _parse_xml_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse XML response from model (legacy format)

        Args:
            response: Raw response string

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            import re

            # Extract XML content
            reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", response, re.DOTALL)
            action_match = re.search(r"<action>(.*?)</action>", response, re.DOTALL)
            support_match = re.search(r"<support>(.*?)</support>", response, re.DOTALL)

            if reasoning_match and action_match and support_match:
                return {
                    "reasoning": reasoning_match.group(1).strip(),
                    "action": action_match.group(1).strip(),
                    "support": support_match.group(1).strip()
                }

            logger.error(f"Failed to parse XML response: {response[:200]}")
            return None

        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return None


# Export the client
__all__ = ["DeepSeekClient"]
