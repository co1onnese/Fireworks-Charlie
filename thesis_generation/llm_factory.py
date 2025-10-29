"""
LLM Factory for creating thesis generation clients

Supports multiple LLM providers:
- DeepSeek: Direct API access (recommended for thesis generation)
- Fireworks: Via Fireworks AI (for RLVR/GRPO training)
"""
import logging
from typing import Union

from .deepseek_client import DeepSeekClient
from .fireworks_client import FireworksDeepSeekClient

logger = logging.getLogger(__name__)


def create_llm_client(
    provider: str,
    config
) -> Union[DeepSeekClient, FireworksDeepSeekClient]:
    """
    Factory function to create the appropriate LLM client

    Args:
        provider: LLM provider name ("deepseek" or "fireworks")
        config: Configuration object with API keys and settings

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider is unknown or required config is missing
    """
    provider = provider.lower().strip()

    if provider == "deepseek":
        # Create DeepSeek client for direct API access
        if not hasattr(config, 'DEEPSEEK_API_KEY') or not config.DEEPSEEK_API_KEY:
            raise ValueError(
                "DEEPSEEK_API_KEY not configured. "
                "Add it to your .env file or set the environment variable."
            )

        logger.info("Creating DeepSeek client (direct API)")

        return DeepSeekClient(
            api_key=config.DEEPSEEK_API_KEY,
            model_name=getattr(config, 'DEEPSEEK_MODEL', 'deepseek-chat'),
            base_url=getattr(config, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
            max_tokens=getattr(config, 'MAX_TOKENS', 2048),
            temperature=getattr(config, 'TEMPERATURE', 0.7),
            timeout=getattr(config, 'API_TIMEOUT', 60)
        )

    elif provider == "fireworks":
        # Create Fireworks client (for RLVR/GRPO training)
        if not hasattr(config, 'FIREWORKS_API_KEY') or not config.FIREWORKS_API_KEY:
            raise ValueError(
                "FIREWORKS_API_KEY not configured. "
                "Add it to your .env file or set the environment variable."
            )

        logger.info("Creating Fireworks client (for RLVR/GRPO)")

        return FireworksDeepSeekClient(
            api_key=config.FIREWORKS_API_KEY,
            model_name=getattr(config, 'MODEL_NAME', 'accounts/fireworks/models/deepseek-v3p1-terminus'),
            model_mode=getattr(config, 'MODEL_MODE', 'deepseek-chat'),
            max_tokens=getattr(config, 'MAX_TOKENS', 128000),
            temperature=getattr(config, 'TEMPERATURE', 0.7)
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported providers: 'deepseek', 'fireworks'"
        )


def get_provider_info(provider: str) -> dict:
    """
    Get information about an LLM provider

    Args:
        provider: Provider name

    Returns:
        Dictionary with provider information
    """
    providers = {
        "deepseek": {
            "name": "DeepSeek",
            "description": "Direct DeepSeek API access (OpenAI-compatible)",
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "recommended_for": "Thesis generation (cost-effective)",
            "pricing": {
                "input": "$0.27/1M tokens",
                "output": "$1.10/1M tokens"
            },
            "features": ["Fast", "Low cost", "High quality"],
            "limitations": ["No built-in GRPO training"]
        },
        "fireworks": {
            "name": "Fireworks AI",
            "description": "DeepSeek via Fireworks AI platform",
            "models": ["deepseek-v3p1-terminus"],
            "recommended_for": "RLVR/GRPO training",
            "pricing": {
                "input": "~$1.00/1M tokens",
                "output": "~$2.00/1M tokens"
            },
            "features": ["GRPO training", "Reward functions", "128K context"],
            "limitations": ["Higher cost", "Additional latency"]
        }
    }

    provider = provider.lower().strip()
    return providers.get(provider, {"error": f"Unknown provider: {provider}"})


def list_providers() -> list:
    """
    List all supported LLM providers

    Returns:
        List of provider names
    """
    return ["deepseek", "fireworks"]


# Export public interface
__all__ = ["create_llm_client", "get_provider_info", "list_providers"]
