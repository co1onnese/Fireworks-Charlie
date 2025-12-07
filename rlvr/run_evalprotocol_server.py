#!/usr/bin/env python3
"""
Development server runner for Evalprotocol Stock Prediction Evaluator

This script provides a convenient way to run the evalprotocol server locally
for development and testing purposes.

Usage:
    python rlvr/run_evalprotocol_server.py [--port 8000] [--host 0.0.0.0] [--reload]

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from rlvr.evalprotocol_server import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import eval_protocol
        import fastapi
        import sqlalchemy
        logger.info("✓ All required dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"✗ Missing dependency: {e}")
        logger.error("Please install requirements: pip install -r rlvr/requirements_evalprotocol.txt")
        return False


def check_database_connection():
    """Check if database connection is available."""
    try:
        from data_collection.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        session.close()
        logger.info("✓ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        logger.error("Please ensure PostgreSQL is running and configured correctly")
        return False


def check_environment():
    """Check environment variables and configuration."""
    required_env_vars = [
        "DATABASE_URL",  # or individual DB config vars
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            # Check for alternative DB config
            if var == "DATABASE_URL":
                alt_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
                if not all(os.getenv(v) for v in alt_vars):
                    missing_vars.append(f"{var} (or {', '.join(alt_vars)})")
            else:
                missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"⚠ Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Server may not function correctly without proper configuration")
        return False
    
    logger.info("✓ Environment configuration looks good")
    return True


def main():
    """Main entry point for the development server."""
    parser = argparse.ArgumentParser(
        description="Run the Evalprotocol Stock Prediction Evaluator server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-flight checks (not recommended)"
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Evalprotocol Stock Prediction Evaluator Server")
    logger.info(f"Server will run on http://{args.host}:{args.port}")
    
    # Pre-flight checks
    if not args.skip_checks:
        logger.info("Running pre-flight checks...")
        
        checks_passed = True
        checks_passed &= check_dependencies()
        checks_passed &= check_database_connection()
        check_environment()  # Warning only, don't fail
        
        if not checks_passed:
            logger.error("❌ Pre-flight checks failed. Use --skip-checks to override.")
            sys.exit(1)
        
        logger.info("✅ All pre-flight checks passed")
    
    # Start the server
    try:
        uvicorn.run(
            "rlvr.evalprotocol_server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
