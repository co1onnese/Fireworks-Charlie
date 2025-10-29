"""
Configuration management for Fireworks-Charlie
RLVR Training Pipeline with GRPO on Fireworks AI
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

class Config:
    """Centralized configuration management"""
    
    def __init__(self):
        # ====== Database Configuration ======
        self.DB_HOST = os.environ.get("DB_HOST", "localhost")
        self.DB_PORT = int(os.environ.get("DB_PORT", "5432"))
        self.DB_NAME = os.environ.get("DB_NAME", "fireworks_charlie")
        self.DB_USER = os.environ.get("DB_USER", "fireworks_app")
        self.DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")
        self.DB_URL = os.environ.get(
            "DB_URL",
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

        # ====== API Keys - Data Collection ======
        self.EODHD_API_KEY = os.environ.get("EODHD_API_KEY", "")
        self.FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
        self.FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
        self.FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
        self.NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
        self.SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

        # ====== LLM Provider Configuration ======
        self.LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek").lower()

        # ====== DeepSeek API Configuration ======
        self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "60"))

        # ====== Fireworks AI Configuration ======
        self.FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
        self.FIREWORKS_ACCOUNT_ID = os.environ.get("FIREWORKS_ACCOUNT_ID", "")

        # ====== Model Configuration ======
        # General settings (applies to both providers)
        self.MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
        self.TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.7"))  # Must be > 0 for GRPO

        # Fireworks-specific settings
        self.MODEL_NAME = os.environ.get("MODEL_NAME", "accounts/fireworks/models/deepseek-v3p1-terminus")
        self.MODEL_MODE = os.environ.get("MODEL_MODE", "deepseek-chat")  # or deepseek-reasoner

        # ====== GRPO Training Parameters ======
        self.GRPO_NUM_RESPONSES = int(os.environ.get("GRPO_NUM_RESPONSES", "4"))  # 2-8 range
        self.GRPO_EPOCHS = int(os.environ.get("GRPO_EPOCHS", "1"))
        self.GRPO_LEARNING_RATE = float(os.environ.get("GRPO_LEARNING_RATE", "0.0001"))
        self.GRPO_LORA_RANK = int(os.environ.get("GRPO_LORA_RANK", "8"))
        self.GRPO_BATCH_SIZE = int(os.environ.get("GRPO_BATCH_SIZE", "32768"))  # In tokens

        # ====== Generation Parameters (Roll-Out) ======
        self.GEN_TEMPERATURE = float(os.environ.get("GEN_TEMPERATURE", "0.7"))
        self.GEN_TOP_P = float(os.environ.get("GEN_TOP_P", "1.0"))
        self.GEN_TOP_K = int(os.environ.get("GEN_TOP_K", "40"))
        self.GEN_MAX_TOKENS = int(os.environ.get("GEN_MAX_TOKENS", "2048"))

        # ====== Pipeline Configuration ======
        self.START_DATE = os.environ.get("START_DATE", "2024-01-01")
        self.END_DATE = os.environ.get("END_DATE", "2024-12-31")
        self.TICKERS = [t.strip() for t in os.environ.get("TICKERS", "AAPL,NVDA,MSFT,AMZN,META").split(",")]

        # ====== Dataset Time Splits ======
        # Training data range (chronological split to prevent data leakage)
        self.TRAIN_START_DATE = os.environ.get("TRAIN_START_DATE", "2023-10-24")
        self.TRAIN_END_DATE = os.environ.get("TRAIN_END_DATE", "2024-12-31")
        # Test data range (must be after training end date)
        self.TEST_START_DATE = os.environ.get("TEST_START_DATE", "2025-01-01")
        self.TEST_END_DATE = os.environ.get("TEST_END_DATE", "2025-12-31")

        # ====== Reward Function Weights ======
        self.DIRECTIONAL_ACCURACY_WEIGHT = int(os.environ.get("DIRECTIONAL_ACCURACY_WEIGHT", "80"))
        self.SHARPE_RATIO_WEIGHT = int(os.environ.get("SHARPE_RATIO_WEIGHT", "20"))

        # ====== RLVR Configuration (Always Enabled) ======
        self.RLVR_MODE = True
        self.RLVR_OUTPUT_DIR = os.environ.get("RLVR_OUTPUT_DIR", "/opt/Fireworks-Charlie/storage/rlvr_datasets")
        self.RLVR_TRAIN_FILE = os.environ.get("RLVR_TRAIN_FILE", f"{self.RLVR_OUTPUT_DIR}/train.jsonl")
        self.RLVR_DEV_FILE = os.environ.get("RLVR_DEV_FILE", f"{self.RLVR_OUTPUT_DIR}/dev.jsonl")
        self.RLVR_TEST_FILE = os.environ.get("RLVR_TEST_FILE", f"{self.RLVR_OUTPUT_DIR}/test.jsonl")

        # Reward function deployment
        self.EVALUATOR_ID = os.environ.get("EVALUATOR_ID", "stock-prediction-evaluator")
        self.EVALUATOR_NAME = os.environ.get("EVALUATOR_NAME", "Stock Prediction Verifiable Reward")

        # ====== Position Management ======
        self.POSITION_HOLD_DAYS = int(os.environ.get("POSITION_HOLD_DAYS", "3"))
        self.EARLY_EXIT_ON_SIGNAL_CHANGE = os.environ.get("EARLY_EXIT_ON_SIGNAL_CHANGE", "true").lower() == "true"

        # ====== Expected Return Thresholds ======
        self.STRONG_BUY_THRESHOLD = float(os.environ.get("STRONG_BUY_THRESHOLD", "3.0"))
        self.BUY_THRESHOLD = float(os.environ.get("BUY_THRESHOLD", "2.0"))
        self.HOLD_THRESHOLD_LOW = float(os.environ.get("HOLD_THRESHOLD_LOW", "-1.0"))
        self.HOLD_THRESHOLD_HIGH = float(os.environ.get("HOLD_THRESHOLD_HIGH", "1.0"))
        self.SELL_THRESHOLD = float(os.environ.get("SELL_THRESHOLD", "-2.0"))
        self.STRONG_SELL_THRESHOLD = float(os.environ.get("STRONG_SELL_THRESHOLD", "-3.0"))

        # ====== Processing Configuration ======
        self.PARALLEL_WORKERS = int(os.environ.get("PARALLEL_WORKERS", "2"))
        self.CHECKPOINT_INTERVAL = int(os.environ.get("CHECKPOINT_INTERVAL", "1"))
        self.TOKEN_BUDGET = int(os.environ.get("TOKEN_BUDGET", "200000"))
        self.TOKEN_WARNING_THRESHOLD = int(os.environ.get("TOKEN_WARNING_THRESHOLD", "180000"))

        # ====== Directory Configuration ======
        self.DATA_ROOT = os.environ.get("DATA_ROOT", "/opt/Fireworks-Charlie/data")
        self.CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "/opt/Fireworks-Charlie/storage/checkpoints")

        # ====== Market Calendar ======
        self.MARKET_CALENDAR = os.environ.get("MARKET_CALENDAR", "NYSE")

        # ====== Logging ======
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.environ.get("LOG_FILE", "/opt/Fireworks-Charlie/logs/fireworks_charlie.log")

        # ====== Assembly quotas ======
        self.ASSEMBLY_QUOTAS = {
            "news_per_bucket": {
                "0-3": int(os.environ.get("NEWS_BUCKET_0_3", "10")),
                "4-10": int(os.environ.get("NEWS_BUCKET_4_10", "8")),
                "11-30": int(os.environ.get("NEWS_BUCKET_11_30", "5"))
            },
            "max_fundamentals": int(os.environ.get("MAX_FUNDAMENTALS", "3")),
            "max_options": int(os.environ.get("MAX_OPTIONS", "25")),
            "max_macro_events": int(os.environ.get("MAX_MACRO_EVENTS", "5")),
            "max_insider_txns": int(os.environ.get("MAX_INSIDER_TXNS", "10")),
            "max_analyst_recos": int(os.environ.get("MAX_ANALYST_RECOS", "5")),
        }

        # Validate reward weights sum to 100%
        self._validate_reward_weights()

        # Create necessary directories
        self._ensure_directories()

    def _validate_reward_weights(self):
        """Validate that reward weights sum to 100%"""
        total = self.DIRECTIONAL_ACCURACY_WEIGHT + self.SHARPE_RATIO_WEIGHT
        if total != 100:
            raise ValueError(
                f"Reward weights must sum to 100%, got {total}% "
                f"(Directional: {self.DIRECTIONAL_ACCURACY_WEIGHT}%, "
                f"Sharpe: {self.SHARPE_RATIO_WEIGHT}%)"
            )

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.DATA_ROOT,
            self.CHECKPOINT_DIR,
            self.RLVR_OUTPUT_DIR,
            os.path.dirname(self.LOG_FILE),
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> Dict[str, bool]:
        """Validate configuration and return status of each component"""
        status = {
            "database": bool(self.DB_URL),
            "fireworks": bool(self.FIREWORKS_API_KEY and self.FIREWORKS_ACCOUNT_ID),
            "eodhd": bool(self.EODHD_API_KEY),
            "fred": bool(self.FRED_API_KEY),
            "finnhub": bool(self.FINNHUB_API_KEY),
            "fmp": bool(self.FMP_API_KEY),
            "newsapi": bool(self.NEWSAPI_KEY),
            "serpapi": bool(self.SERPAPI_KEY),
            "directories": all(Path(d).exists() for d in [
                self.DATA_ROOT,
                self.CHECKPOINT_DIR,
                self.RLVR_OUTPUT_DIR
            ]),
            "reward_weights": self.DIRECTIONAL_ACCURACY_WEIGHT + self.SHARPE_RATIO_WEIGHT == 100,
        }

        return status
    
    def get_active_apis(self) -> List[str]:
        """Get list of APIs that have valid keys configured"""
        apis = []
        if self.EODHD_API_KEY:
            apis.append("eodhd")
        if self.FRED_API_KEY:
            apis.append("fred")
        if self.FINNHUB_API_KEY:
            apis.append("finnhub")
        if self.FMP_API_KEY:
            apis.append("fmp")
        if self.NEWSAPI_KEY:
            apis.append("newsapi")
        if self.SERPAPI_KEY:
            apis.append("serpapi")
        return apis
    
    def log_configuration(self, logger: logging.Logger):
        """Log current configuration status"""
        logger.info("=== Fireworks-Charlie Configuration ===")
        logger.info(f"Database: {self.DB_URL.split('@')[1] if '@' in self.DB_URL else 'configured'}")
        logger.info(f"Model: {self.MODEL_NAME} ({self.MODEL_MODE})")
        logger.info(f"Tickers: {', '.join(self.TICKERS)}")
        logger.info(f"Data Collection: {self.START_DATE} to {self.END_DATE}")
        logger.info(f"Training Split: {self.TRAIN_START_DATE} to {self.TRAIN_END_DATE}")
        logger.info(f"Test Split: {self.TEST_START_DATE} to {self.TEST_END_DATE}")

        logger.info("\n=== GRPO Training Parameters ===")
        logger.info(f"Num Responses: {self.GRPO_NUM_RESPONSES}")
        logger.info(f"Learning Rate: {self.GRPO_LEARNING_RATE}")
        logger.info(f"LoRA Rank: {self.GRPO_LORA_RANK}")
        logger.info(f"Batch Size: {self.GRPO_BATCH_SIZE} tokens")

        logger.info("\n=== Reward Function Configuration ===")
        logger.info(f"Directional Accuracy: {self.DIRECTIONAL_ACCURACY_WEIGHT}%")
        logger.info(f"Sharpe Ratio: {self.SHARPE_RATIO_WEIGHT}%")
        logger.info(f"Position Hold: {self.POSITION_HOLD_DAYS} days")
        logger.info(f"Early Exit: {'Enabled' if self.EARLY_EXIT_ON_SIGNAL_CHANGE else 'Disabled'}")

        logger.info("\n=== Expected Return Thresholds ===")
        logger.info(f"Strong Buy: ?{self.STRONG_BUY_THRESHOLD:+.1f}%")
        logger.info(f"Buy: ?{self.BUY_THRESHOLD:+.1f}%")
        logger.info(f"Hold: {self.HOLD_THRESHOLD_LOW:+.1f}% to {self.HOLD_THRESHOLD_HIGH:+.1f}%")
        logger.info(f"Sell: ?{self.SELL_THRESHOLD:+.1f}%")
        logger.info(f"Strong Sell: ?{self.STRONG_SELL_THRESHOLD:+.1f}%")

        status = self.validate()
        logger.info("\n=== Component Status ===")
        for component, available in status.items():
            status_str = "? Ready" if available else "? Not configured"
            logger.info(f"  {component}: {status_str}")

        if not status['fireworks']:
            logger.warning("??  Fireworks API not configured - model inference will fail!")

        if not status['reward_weights']:
            logger.error("? Reward weights do not sum to 100%!")

        active_apis = self.get_active_apis()
        if not active_apis:
            logger.warning("??  No data collection APIs configured!")
        else:
            logger.info(f"\nActive data sources: {', '.join(active_apis)}")

        logger.info(f"\n=== RLVR Mode: ENABLED ===")
        logger.info(f"Train file: {self.RLVR_TRAIN_FILE}")
        logger.info(f"Dev file: {self.RLVR_DEV_FILE}")
        logger.info(f"Test file: {self.RLVR_TEST_FILE}")

# Global config instance
config = Config()