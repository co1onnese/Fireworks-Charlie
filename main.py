#!/usr/bin/env python3
"""
Main entry point for Fireworks-Charlie pipeline
"""
import argparse
import sys
from datetime import date

from orchestration.main_pipeline import FireworksCharliePipeline

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Fireworks-Charlie: RLVR Investment Thesis Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  python main.py
  
  # Run for specific tickers
  python main.py --tickers AAPL,MSFT,GOOGL
  
  # Run for specific date range
  python main.py --start-date 2024-01-01 --end-date 2024-03-31
  
  # Run without resuming from checkpoints
  python main.py --no-resume
  
  # Run single ticker for testing
  python main.py --tickers AAPL --start-date 2024-01-01 --end-date 2024-01-10

  # Run in test mode with custom ticker and duration
  python main.py --test --test-ticker MSFT --test-days 10

  # Run in test mode with defaults (AAPL, 5 days)
  python main.py --test
"""
    )
    
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers (overrides config)"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date in YYYY-MM-DD format (overrides config)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date in YYYY-MM-DD format (overrides config)"
    )
    
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start fresh without resuming from checkpoints"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with limited data"
    )

    parser.add_argument(
        "--test-ticker",
        type=str,
        default="AAPL",
        help="Ticker to use in test mode (default: AAPL)"
    )

    parser.add_argument(
        "--test-days",
        type=int,
        default=5,
        help="Number of days to test in test mode (default: 5)"
    )

    args = parser.parse_args()

    # Process arguments
    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]

    # Test mode settings
    if args.test:
        if not tickers:
            # Use test-ticker flag or default to AAPL
            tickers = [args.test_ticker.upper()]
        if not args.start_date:
            args.start_date = "2024-01-01"
        if not args.end_date:
            # Calculate end date based on test-days
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_dt = start_dt + timedelta(days=args.test_days)
            args.end_date = end_dt.strftime("%Y-%m-%d")
    
    # Validate dates if provided
    if args.start_date:
        try:
            date.fromisoformat(args.start_date)
        except ValueError:
            print(f"Error: Invalid start date format: {args.start_date}")
            sys.exit(1)
    
    if args.end_date:
        try:
            date.fromisoformat(args.end_date)
        except ValueError:
            print(f"Error: Invalid end date format: {args.end_date}")
            sys.exit(1)
    
    # Create and run pipeline
    try:
        print("Starting Fireworks-Charlie Pipeline...")
        print("=" * 60)
        
        pipeline = FireworksCharliePipeline()
        
        results = pipeline.run(
            tickers=tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            resume=not args.no_resume
        )
        
        # Print summary
        print("\n" + "=" * 60)
        print("Pipeline Execution Summary")
        print("=" * 60)
        
        summary = results["summary"]
        print(f"Tickers Processed: {summary['tickers_processed']}")
        print(f"Total Theses Generated: {summary['total_theses']}")
        print(f"Failures: {summary['failures']}")
        
        # Print per-ticker results
        print("\nPer-Ticker Results:")
        print("-" * 40)
        
        for ticker, result in results["thesis_generation"].items():
            if result["status"] == "success":
                if result.get("already_complete"):
                    print(f"{ticker}: Already complete ({result['total_theses']} theses)")
                    if result.get("latest_thesis"):
                        latest = result["latest_thesis"]
                        print(f"  Latest: {latest['as-of-date']} - {latest['action']}")
                else:
                    print(f"{ticker}: {result['theses_generated']} theses generated")
                    if result.get("latest_thesis"):
                        latest = result["latest_thesis"]
                        print(f"  Latest: {latest['as-of-date']} - {latest['action']}")
            else:
                print(f"{ticker}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Clean up
        pipeline.cleanup()
        
        # Exit with appropriate code
        if summary['failures'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nPipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()