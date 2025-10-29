"""
Fireworks AI client for DeepSeek V3.1-Terminus integration
Supports RLVR (Reinforcement Learning with Verifiable Rewards) and GRPO training
"""
import logging
import time
import json
from typing import Dict, Any, Optional, List
from fireworks.client import Fireworks

logger = logging.getLogger(__name__)


class FireworksDeepSeekClient:
    """
    Client for interacting with DeepSeek V3.1-Terminus via Fireworks AI

    This client is optimized for RLVR training with:
    - JSON response format (not XML)
    - Separate storage of system/user prompts for RLVR datasets
    - Support for GRPO training parameters
    - DeepSeek V3.1-Terminus (671B params, 37B active, 128K context)
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "accounts/fireworks/models/deepseek-v3p1-terminus",
        model_mode: str = "deepseek-chat",
        max_tokens: int = 128000,
        temperature: float = 0.7
    ):
        """
        Initialize Fireworks DeepSeek client

        Args:
            api_key: Fireworks API key
            model_name: Fireworks model identifier
            model_mode: deepseek-chat or deepseek-reasoner
            max_tokens: Maximum context length (V3.1-Terminus supports 128K)
            temperature: Generation temperature (must be > 0 for GRPO)
        """
        if temperature <= 0:
            logger.warning(
                f"Temperature {temperature} is ≤ 0. GRPO requires temperature > 0 for exploration. "
                "Setting to 0.7"
            )
            temperature = 0.7

        self.client = Fireworks(api_key=api_key)
        self.model = model_name
        self.model_mode = model_mode
        self.max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(
            f"Initialized Fireworks client with model: {self.model} "
            f"(mode: {self.model_mode}, temp: {temperature})"
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
        Generate investment thesis using DeepSeek V3.1-Terminus via Fireworks

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
4. Support your thesis with specific data points

CRITICAL: Your response MUST be valid JSON in this exact format:
{
  "reasoning": "Your detailed analysis explaining the investment thesis. Include specific data points, trends, and insights that support your recommendation.",
  "action": "one of: strong_buy, buy, hold, sell, strong_sell",
  "support": "Key supporting evidence with specific numbers, dates, and metrics that justify your action recommendation."
}

Do not include any text outside the JSON object. The action field must be exactly one of the five specified values (lowercase, with underscores)."""
        else:
            # XML format (legacy compatibility)
            system_prompt = """You are a senior financial analyst with deep expertise in equity research and investment analysis.

Your task is to generate investment theses based on comprehensive market data. You must:
1. Analyze ALL provided data thoroughly
2. Identify key patterns and correlations
3. Generate clear, actionable recommendations
4. Support your thesis with specific data points

CRITICAL: Your response MUST be in the exact XML format specified in the prompt. Do not include any text outside the XML tags."""

        try:
            logger.info(f"Generating thesis for {ticker} as of {as_of_date} (format: {response_format})")
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=2048,  # Leave room for response within context
            )

            generation_time = time.time() - start_time

            # Extract the response
            assistant_response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            logger.info(f"Generated thesis in {generation_time:.2f}s using {tokens_used:,} tokens")

            # Parse response based on format
            if response_format == "json":
                parsed_thesis = self._parse_json_response(assistant_response_text)
            else:
                parsed_thesis = self._parse_xml_response(assistant_response_text)

            if parsed_thesis.get("error"):
                logger.error(f"Failed to parse thesis: {parsed_thesis['error']}")
                return {
                    "status": "error",
                    "error": parsed_thesis["error"],
                    "raw_response": assistant_response_text,
                    "system_prompt": system_prompt,
                    "user_prompt": prompt
                }

            # Convert assistant response to JSON for storage
            assistant_response_json = {
                "reasoning": parsed_thesis["reasoning"],
                "action": parsed_thesis["action"],
                "support": parsed_thesis["support"]
            }

            return {
                "status": "success",
                "system_prompt": system_prompt,  # Store for RLVR
                "user_prompt": prompt,           # Store for RLVR
                "assistant_response": assistant_response_json,  # JSONB for database
                "reasoning": parsed_thesis["reasoning"],
                "action": parsed_thesis["action"],
                "support": parsed_thesis["support"],
                "metadata": {
                    "model": self.model,
                    "model_mode": self.model_mode,
                    "tokens_used": tokens_used,
                    "generation_time": generation_time,
                    "temperature": temperature,
                    "response_format": response_format
                }
            }

        except Exception as e:
            logger.error(f"Error generating thesis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "system_prompt": system_prompt,
                "user_prompt": prompt
            }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM

        Args:
            response: Raw LLM response (should be JSON)

        Returns:
            Dictionary with parsed components or error
        """
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split("\n")
                # Remove first and last lines if they are code fence markers
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                response = "\n".join(lines)

            # Parse JSON
            parsed = json.loads(response)

            # Validate required fields
            if "reasoning" not in parsed:
                return {"error": "Missing 'reasoning' field in JSON response"}
            if "action" not in parsed:
                return {"error": "Missing 'action' field in JSON response"}
            if "support" not in parsed:
                return {"error": "Missing 'support' field in JSON response"}

            # Validate action
            action = parsed["action"].strip().lower()
            valid_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
            if action not in valid_actions:
                return {
                    "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}"
                }

            return {
                "reasoning": parsed["reasoning"].strip(),
                "action": action,
                "support": parsed["support"].strip()
            }

        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing error: {str(e)}. Response: {response[:200]}"}
        except Exception as e:
            return {"error": f"Unexpected parsing error: {str(e)}"}

    def _parse_xml_response(self, response: str) -> Dict[str, Any]:
        """
        Parse XML response from LLM (legacy compatibility)

        Args:
            response: Raw LLM response

        Returns:
            Dictionary with parsed components or error
        """
        try:
            import re

            # Extract reasoning
            reasoning_match = re.search(r'<reasoning>\s*(.*?)\s*</reasoning>', response, re.DOTALL)
            if not reasoning_match:
                return {"error": "No <reasoning> tag found in response"}
            reasoning = reasoning_match.group(1).strip()

            # Extract action
            action_match = re.search(r'<action>\s*(.*?)\s*</action>', response, re.DOTALL)
            if not action_match:
                return {"error": "No <action> tag found in response"}
            action = action_match.group(1).strip().lower()

            # Validate action
            valid_actions = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
            if action not in valid_actions:
                return {
                    "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}"
                }

            # Extract support
            support_match = re.search(r'<support>\s*(.*?)\s*</support>', response, re.DOTALL)
            if not support_match:
                return {"error": "No <support> tag found in response"}
            support = support_match.group(1).strip()

            return {
                "reasoning": reasoning,
                "action": action,
                "support": support
            }

        except Exception as e:
            return {"error": f"XML parsing error: {str(e)}"}

    def test_connection(self) -> bool:
        """
        Test connection to Fireworks API

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, please respond with 'Connection successful'."}
                ],
                max_tokens=10,
                temperature=0.1
            )

            result = response.choices[0].message.content
            success = "successful" in result.lower()

            if success:
                logger.info("Fireworks API connection test successful")
            else:
                logger.warning(f"Unexpected test response: {result}")

            return success

        except Exception as e:
            logger.error(f"Fireworks API connection test failed: {e}")
            return False

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

        GRPO requires n≥2 responses per prompt (typically 4-8) to compute
        group-relative rewards.

        Args:
            prompt: The cumulative data prompt
            ticker: Stock ticker
            as_of_date: Analysis date
            num_responses: Number of responses to generate (2-8 recommended)
            temperature: Generation temperature

        Returns:
            List of response dictionaries (same format as generate_thesis)
        """
        if num_responses < 2:
            logger.warning(f"GRPO requires num_responses >= 2, got {num_responses}. Setting to 2.")
            num_responses = 2

        if num_responses > 8:
            logger.warning(f"num_responses > 8 may be inefficient. Got {num_responses}.")

        logger.info(f"Generating {num_responses} responses for GRPO training")

        responses = []
        for i in range(num_responses):
            logger.info(f"Generating response {i+1}/{num_responses}")
            response = self.generate_thesis(
                prompt=prompt,
                ticker=ticker,
                as_of_date=as_of_date,
                temperature=temperature,
                response_format="json"
            )
            responses.append(response)

            # Add response index to metadata
            if "metadata" in response:
                response["metadata"]["response_index"] = i

        return responses
