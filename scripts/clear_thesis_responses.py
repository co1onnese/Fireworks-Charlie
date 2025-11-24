#!/usr/bin/env python3
"""
Clear LLM responses from thesis_generations table.

This script clears assistant_response and related fields from all thesis
generations, allowing them to be regenerated with new prompts.

Usage:
    python scripts/clear_thesis_responses.py [--dry-run] [--tickers TICKERS] [--start-date DATE] [--end-date DATE]
"""
import sys
import argparse
import logging
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.config_manager import config
from data_collection.database_manager import DatabaseManager, ThesisGeneration, Ticker, Position
from sqlalchemy import select, and_, func

# Setup logging
def setup_logging():
    log_dir = Path("/opt/Fireworks-Charlie/logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "clear_thesis_responses.log")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


def get_thesis_count(
    db_manager: DatabaseManager,
    tickers: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> int:
    """Get count of theses that will be cleared."""
    session = db_manager.get_session()
    try:
        query = session.query(func.count(ThesisGeneration.thesis_id)).join(Ticker)
        
        if tickers:
            query = query.filter(Ticker.symbol.in_([t.upper() for t in tickers]))
        
        if start_date:
            query = query.filter(ThesisGeneration.as_of_date >= start_date)
        
        if end_date:
            query = query.filter(ThesisGeneration.as_of_date <= end_date)
        
        # Only count theses with assistant_response
        query = query.filter(ThesisGeneration.assistant_response.isnot(None))
        
        return query.scalar() or 0
    finally:
        session.close()


def get_position_count(db_manager: DatabaseManager) -> int:
    """Get count of positions that will be deleted."""
    session = db_manager.get_session()
    try:
        return session.query(func.count(Position.position_id)).scalar() or 0
    finally:
        session.close()


def clear_thesis_responses(
    db_manager: DatabaseManager,
    tickers: Optional[List[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    dry_run: bool = False
) -> dict:
    """
    Clear assistant_response and related fields from thesis_generations.
    
    Args:
        db_manager: Database manager instance
        tickers: Optional list of tickers to filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        dry_run: If True, only show what would be cleared
        
    Returns:
        Dictionary with statistics
    """
    session = db_manager.get_session()
    stats = {
        "theses_cleared": 0,
        "positions_deleted": 0,
        "errors": []
    }
    
    try:
        # Get theses to clear
        query = session.query(ThesisGeneration).join(Ticker)
        
        if tickers:
            query = query.filter(Ticker.symbol.in_([t.upper() for t in tickers]))
        
        if start_date:
            query = query.filter(ThesisGeneration.as_of_date >= start_date)
        
        if end_date:
            query = query.filter(ThesisGeneration.as_of_date <= end_date)
        
        # Only clear theses with assistant_response (exclude already cleared ones)
        # Check for theses that don't have the placeholder value
        query = query.filter(ThesisGeneration.assistant_response.isnot(None))
        
        # Filter out theses that are already cleared (have placeholder)
        # We'll do this in Python to avoid complex JSONB queries
        
        all_theses = query.all()
        
        # Filter out theses that are already cleared (have placeholder)
        theses = []
        for thesis in all_theses:
            try:
                if isinstance(thesis.assistant_response, str):
                    response_data = json.loads(thesis.assistant_response)
                else:
                    response_data = thesis.assistant_response
                
                # Skip if already cleared (has placeholder)
                if isinstance(response_data, dict) and response_data.get("cleared") is True:
                    continue
                
                theses.append(thesis)
            except (json.JSONDecodeError, TypeError, AttributeError):
                # If we can't parse it, assume it needs clearing
                theses.append(thesis)
        
        stats["theses_cleared"] = len(theses)
        
        if dry_run:
            logger.info(f"DRY RUN: Would clear {len(theses)} theses (skipped {len(all_theses) - len(theses)} already cleared)")
            return stats
        
        # Clear assistant_response fields for each thesis
        logger.info(f"Clearing assistant_response from {len(theses)} theses...")
        
        for thesis in theses:
            try:
                # assistant_response is JSONB NOT NULL, so use placeholder JSON
                # predicted_action is VARCHAR(20) NOT NULL, so use 'hold' as placeholder
                thesis.assistant_response = json.dumps({"status": "pending", "cleared": True})
                thesis.predicted_action = 'hold'  # Placeholder - must be valid action
                thesis.reasoning = None
                thesis.support = None
                thesis.model_name = None
                thesis.temperature = None
                thesis.tokens_used = None
                thesis.generation_time_ms = None
                thesis.status = 'pending'
                thesis.error_message = None
                thesis.generated_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error clearing thesis {thesis.thesis_id}: {e}")
                stats["errors"].append({
                    "thesis_id": thesis.thesis_id,
                    "error": str(e)
                })
        
        # Commit changes
        session.commit()
        logger.info(f"✓ Cleared assistant_response from {len(theses)} theses")
        
        # Delete positions (they depend on assistant_response)
        logger.info("Deleting positions...")
        positions_deleted = session.query(Position).delete()
        session.commit()
        stats["positions_deleted"] = positions_deleted
        logger.info(f"✓ Deleted {positions_deleted} positions")
        
    except Exception as e:
        logger.error(f"Error clearing thesis responses: {e}")
        session.rollback()
        stats["errors"].append({"error": str(e)})
        raise
    finally:
        session.close()
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Clear LLM responses from thesis_generations table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run - show what would be cleared
    python scripts/clear_thesis_responses.py --dry-run
    
    # Clear all theses
    python scripts/clear_thesis_responses.py
    
    # Clear specific tickers
    python scripts/clear_thesis_responses.py --tickers AAPL,MSFT
    
    # Clear specific date range
    python scripts/clear_thesis_responses.py --start-date 2024-01-01 --end-date 2024-12-31
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - show what would be cleared without making changes'
    )
    
    parser.add_argument(
        '--tickers',
        type=str,
        help='Comma-separated list of tickers to filter (e.g., AAPL,MSFT)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date filter (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date filter (YYYY-MM-DD)'
    )
    
    args = parser.parse_args()
    
    # Parse tickers
    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Parse dates
    start_date = None
    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    
    end_date = None
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    
    # Initialize database
    db_manager = DatabaseManager(config.DB_URL)
    
    try:
        # Get statistics
        thesis_count = get_thesis_count(db_manager, tickers, start_date, end_date)
        position_count = get_position_count(db_manager)
        
        logger.info("=" * 60)
        logger.info("Clear Thesis Responses")
        logger.info("=" * 60)
        logger.info(f"Theses to clear: {thesis_count}")
        logger.info(f"Positions to delete: {position_count}")
        
        if args.dry_run:
            logger.info("\nDRY RUN MODE - No changes will be made")
            logger.info("=" * 60)
            return
        
        # Confirm
        logger.info("\n⚠️  WARNING: This will clear all assistant_response data!")
        logger.info("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        import time
        time.sleep(5)
        
        # Clear responses
        stats = clear_thesis_responses(
            db_manager,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            dry_run=args.dry_run
        )
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info(f"Theses cleared: {stats['theses_cleared']}")
        logger.info(f"Positions deleted: {stats['positions_deleted']}")
        
        if stats['errors']:
            logger.warning(f"Errors: {len(stats['errors'])}")
            for error in stats['errors'][:5]:
                logger.warning(f"  - {error}")
        
        logger.info("\n✓ Clear operation completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Modify pipeline to regenerate when assistant_response IS NULL")
        logger.info("2. Run: python main.py --tickers <tickers> --start-date <start> --end-date <end>")
        logger.info("3. Run: python rlvr_main.py generate --train-split-date 2024-12-31")
        
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to clear thesis responses: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        db_manager.engine.dispose()


if __name__ == "__main__":
    main()
