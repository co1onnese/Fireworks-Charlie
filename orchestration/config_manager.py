"""
Configuration management for Trainer-Charlie
Combines configuration needs from both Charlie-T1-DB and TradingCharlie
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
        # Database Configuration
        self.DB_URL = os.environ.get("DATABASE_URL", os.environ.get("DB_URL", "postgresql://user:password@localhost/trainer_charlie"))
        
        # API Keys - Data Collection
        self.EODHD_API_KEY = os.environ.get("EODHD_API_KEY", "")
        self.FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
        self.FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
        self.FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
        self.NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
        self.SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
        
        # DeepSeek Configuration
        self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.MODEL_NAME = os.environ.get("MODEL_NAME", "deepseek-chat")
        self.MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "128000"))
        
        # Pipeline Configuration
        self.START_DATE = os.environ.get("START_DATE", "2024-01-01")
        self.END_DATE = os.environ.get("END_DATE", "2024-12-31")
        self.TICKERS = [t.strip() for t in os.environ.get("TICKERS", "AAPL,NVDA,MSFT,AMZN,META").split(",")]
        
        # Processing Configuration
        self.PARALLEL_WORKERS = int(os.environ.get("PARALLEL_WORKERS", "2"))
        self.CHECKPOINT_INTERVAL = int(os.environ.get("CHECKPOINT_INTERVAL", "1"))
        self.TOKEN_BUDGET = int(os.environ.get("TOKEN_BUDGET", "120000"))
        
        # Directory Configuration
        self.DATA_ROOT = os.environ.get("DATA_ROOT", "/opt/Trainer-Charlie/data")
        self.THESIS_OUTPUT_DIR = os.environ.get("THESIS_OUTPUT_DIR", "/opt/Trainer-Charlie/storage/distilled_theses")
        self.CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "/opt/Trainer-Charlie/storage/checkpoints")
        
        # Market Calendar
        self.MARKET_CALENDAR = os.environ.get("MARKET_CALENDAR", "NYSE")
        
        # Logging
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.environ.get("LOG_FILE", "/opt/Trainer-Charlie/logs/trainer_charlie.log")
        
        # Assembly quotas (from TradingCharlie)
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
        
        # Create necessary directories
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.DATA_ROOT,
            self.THESIS_OUTPUT_DIR,
            os.path.join(self.THESIS_OUTPUT_DIR, "backups"),
            self.CHECKPOINT_DIR,
            os.path.dirname(self.LOG_FILE),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> Dict[str, bool]:
        """Validate configuration and return status of each component"""
        status = {
            "database": bool(self.DB_URL),
            "eodhd": bool(self.EODHD_API_KEY),
            "fred": bool(self.FRED_API_KEY),
            "finnhub": bool(self.FINNHUB_API_KEY),
            "fmp": bool(self.FMP_API_KEY),
            "newsapi": bool(self.NEWSAPI_KEY),
            "serpapi": bool(self.SERPAPI_KEY),
            "deepseek": bool(self.DEEPSEEK_API_KEY),
            "directories": all(Path(d).exists() for d in [
                self.DATA_ROOT, 
                self.THESIS_OUTPUT_DIR, 
                self.CHECKPOINT_DIR
            ]),
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
        logger.info("=== Trainer-Charlie Configuration ===")
        logger.info(f"Database: {self.DB_URL.split('@')[1] if '@' in self.DB_URL else 'configured'}")
        logger.info(f"Tickers: {', '.join(self.TICKERS)}")
        logger.info(f"Date Range: {self.START_DATE} to {self.END_DATE}")
        logger.info(f"Parallel Workers: {self.PARALLEL_WORKERS}")
        logger.info(f"Token Budget: {self.TOKEN_BUDGET}")
        
        status = self.validate()
        logger.info("\nAPI Status:")
        for component, available in status.items():
            status_str = "✓ Ready" if available else "✗ Not configured"
            logger.info(f"  {component}: {status_str}")
        
        if not status['deepseek']:
            logger.warning("⚠️  DeepSeek API not configured - thesis generation will fail!")
        
        active_apis = self.get_active_apis()
        if not active_apis:
            logger.warning("⚠️  No data collection APIs configured!")
        else:
            logger.info(f"\nActive data sources: {', '.join(active_apis)}")

# Global config instance
config = Config()