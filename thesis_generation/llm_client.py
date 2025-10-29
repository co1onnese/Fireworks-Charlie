"""
LLM client for DeepSeek-V3 integration
"""
import logging
import time
from typing import Dict, Any, Optional
from openai import OpenAI
import json

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """Client for interacting with DeepSeek-V3 API using OpenAI-compatible interface"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """
        Initialize DeepSeek client
        
        Args:
            api_key: DeepSeek API key
            base_url: Base URL for DeepSeek API
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = "deepseek-chat"
        self.max_tokens = 4000  # Leave room in the 128K context
        
        logger.info(f"Initialized DeepSeek client with model: {self.model}")
    
    def generate_thesis(self, 
                       prompt: str,
                       ticker: str,
                       as_of_date: str,
                       temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate investment thesis using DeepSeek
        
        Args:
            prompt: The cumulative data prompt
            ticker: Stock ticker for context
            as_of_date: Analysis date
            temperature: Generation temperature (0-1)
            
        Returns:
            Dictionary with thesis components or error
        """
        system_prompt = """You are a senior financial analyst with deep expertise in equity research and investment analysis. 

Your task is to generate investment theses based on comprehensive market data. You must:
1. Analyze ALL provided data thoroughly
2. Identify key patterns and correlations
3. Generate clear, actionable recommendations
4. Support your thesis with specific data points

CRITICAL: Your response MUST be in the exact XML format specified in the prompt. Do not include any text outside the XML tags."""
        
        try:
            logger.info(f"Generating thesis for {ticker} as of {as_of_date}")
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=self.max_tokens
            )
            
            generation_time = time.time() - start_time
            
            # Extract the response
            thesis_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            
            logger.info(f"Generated thesis in {generation_time:.2f}s using {tokens_used:,} tokens")
            
            # Parse XML response
            parsed_thesis = self._parse_xml_response(thesis_text)
            
            if parsed_thesis.get("error"):
                logger.error(f"Failed to parse thesis XML: {parsed_thesis['error']}")
                return {
                    "status": "error",
                    "error": parsed_thesis["error"],
                    "raw_response": thesis_text
                }
            
            return {
                "status": "success",
                "reasoning": parsed_thesis["reasoning"],
                "action": parsed_thesis["action"],
                "support": parsed_thesis["support"],
                "metadata": {
                    "model": self.model,
                    "tokens_used": tokens_used,
                    "generation_time": generation_time,
                    "temperature": temperature
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating thesis: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _parse_xml_response(self, response: str) -> Dict[str, Any]:
        """
        Parse XML response from LLM
        
        Args:
            response: Raw LLM response
            
        Returns:
            Dictionary with parsed components or error
        """
        try:
            # Simple XML parsing without external dependencies
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
                return {"error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}"}
            
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
        Test connection to DeepSeek API
        
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
                temperature=0
            )
            
            result = response.choices[0].message.content
            success = "successful" in result.lower()
            
            if success:
                logger.info("DeepSeek API connection test successful")
            else:
                logger.warning(f"Unexpected test response: {result}")
                
            return success
            
        except Exception as e:
            logger.error(f"DeepSeek API connection test failed: {e}")
            return False