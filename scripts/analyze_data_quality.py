#!/usr/bin/env python3
"""
Analyze Data Quality

Production script to analyze data quality for a date range.
Checks coverage, identifies gaps, and reports quality metrics.
"""
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestration.config_manager import config
from data_collection.data_orchestrator import DataOrchestrator
from utils.logger import setup_logger

logger = setup_logger(
    name="analyze_data_quality",
    log_file="logs/analyze_data_quality.log",
    log_level="INFO"
)


def analyze_data_quality(tickers: List[str] = None,
                        start_date: date = None,
                        end_date: date = None) -> Dict[str, Any]:
    """
    Analyze data quality for a date range

    Args:
        tickers: List of tickers to analyze (default: all)
        start_date: Start date (default: config)
        end_date: End date (default: config)

    Returns:
        Dictionary with analysis results
    """
    # Use provided values or fall back to config
    tickers = tickers or config.TICKERS
    start_date = start_date or date.fromisoformat(config.START_DATE)
    end_date = end_date or date.fromisoformat(config.END_DATE)

    logger.info("=" * 80)
    logger.info("DATA QUALITY ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"Analyzing {len(tickers)} tickers from {start_date} to {end_date}")
    logger.info("")

    orchestrator = DataOrchestrator(config)

    results = {
        "summary": {
            "total_tickers": len(tickers),
            "date_range": f"{start_date} to {end_date}",
            "technical_coverage": 0,
            "fundamental_coverage": 0,
            "news_coverage": 0,
            "macro_coverage": 0
        },
        "tickers": {}
    }

    for ticker in tickers:
        logger.info(f"Analyzing {ticker}...")

        # Check existing data range
        tech_min, tech_max, tech_count = orchestrator.get_existing_data_range(ticker, 'technical')
        fund_min, fund_max, fund_count = orchestrator.get_existing_data_range(ticker, 'fundamental')
        news_min, news_max, news_count = orchestrator.get_existing_data_range(ticker, 'news')
        macro_min, macro_max, macro_count = orchestrator.get_existing_data_range(ticker, 'macro')

        # Calculate coverage percentage
        total_days = (end_date - start_date).days + 1
        tech_coverage = (tech_count / total_days * 100) if tech_count > 0 else 0
        fund_coverage = 100 if fund_count > 0 else 0
        news_coverage = (news_count / total_days * 100) if news_count > 0 else 0
        macro_coverage = 100 if macro_count > 0 else 0

        # Identify gaps
        gaps = orchestrator.identify_data_gaps(ticker, start_date, end_date)

        results["tickers"][ticker] = {
            "technical": {
                "count": tech_count,
                "min_date": tech_min.isoformat() if tech_min else None,
                "max_date": tech_max.isoformat() if tech_max else None,
                "coverage_pct": round(tech_coverage, 1),
                "gaps": len(gaps['technical'])
            },
            "fundamental": {
                "count": fund_count,
                "min_date": fund_min.isoformat() if fund_min else None,
                "max_date": fund_max.isoformat() if fund_max else None,
                "coverage_pct": round(fund_coverage, 1),
                "gaps": len(gaps['fundamental'])
            },
            "news": {
                "count": news_count,
                "min_date": news_min.isoformat() if news_min else None,
                "max_date": news_max.isoformat() if news_max else None,
                "coverage_pct": round(news_coverage, 1),
                "gaps": len(gaps['news'])
            },
            "macro": {
                "count": macro_count,
                "min_date": macro_min.isoformat() if macro_min else None,
                "max_date": macro_max.isoformat() if macro_max else None,
                "coverage_pct": round(macro_coverage, 1),
                "gaps": len(gaps['macro'])
            },
            "gaps": gaps
        }

    # Calculate overall coverage
    all_tech_coverage = sum(t["technical"]["coverage_pct"] for t in results["tickers"].values()) / len(tickers)
    all_fund_coverage = sum(t["fundamental"]["coverage_pct"] for t in results["tickers"].values()) / len(tickers)
    all_news_coverage = sum(t["news"]["coverage_pct"] for t in results["tickers"].values()) / len(tickers)
    all_macro_coverage = sum(t["macro"]["coverage_pct"] for t in results["tickers"].values()) / len(tickers)

    results["summary"]["technical_coverage"] = round(all_tech_coverage, 1)
    results["summary"]["fundamental_coverage"] = round(all_fund_coverage, 1)
    results["summary"]["news_coverage"] = round(all_news_coverage, 1)
    results["summary"]["macro_coverage"] = round(all_macro_coverage, 1)

    # Print summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Overall Coverage:")
    logger.info(f"  Technical data: {results['summary']['technical_coverage']}%")
    logger.info(f"  Fundamental data: {results['summary']['fundamental_coverage']}%")
    logger.info(f"  News data: {results['summary']['news_coverage']}%")
    logger.info(f"  Macro data: {results['summary']['macro_coverage']}%")
    logger.info("")

    # Tickers with low coverage
    low_tech = [t for t, d in results["tickers"].items() if d["technical"]["coverage_pct"] < 80]
    low_fund = [t for t, d in results["tickers"].items() if d["fundamental"]["coverage_pct"] < 80]
    low_news = [t for t, d in results["tickers"].items() if d["news"]["coverage_pct"] < 80]

    if low_tech:
        logger.info(f"Tickers with low technical coverage (<80%): {', '.join(low_tech)}")
    if low_fund:
        logger.info(f"Tickers with no fundamental data: {', '.join(low_fund)}")
    if low_news:
        logger.info(f"Tickers with low news coverage (<80%): {', '.join(low_news)}")

    # Save detailed results
    output_file = "data_quality_analysis.json"
    import json
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info("")
    logger.info(f"Detailed results saved to: {output_file}")

    return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze data quality")
    parser.add_argument("--tickers", type=str, nargs="+",
                       help="Tickers to analyze (default: all from config)")
    parser.add_argument("--start-date", type=str,
                       help="Start date YYYY-MM-DD (default: from config)")
    parser.add_argument("--end-date", type=str,
                       help="End date YYYY-MM-DD (default: from config)")

    args = parser.parse_args()

    # Parse dates
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None

    # Analyze
    results = analyze_data_quality(
        tickers=args.tickers,
        start_date=start_date,
        end_date=end_date
    )

    # Exit code based on quality
    tech_ok = results["summary"]["technical_coverage"] >= 90
    fund_ok = results["summary"]["fundamental_coverage"] >= 80
    news_ok = results["summary"]["news_coverage"] >= 90

    if tech_ok and fund_ok and news_ok:
        logger.info("\n✅ Data quality is good!")
        return 0
    else:
        logger.warning("\n⚠️  Data quality issues detected!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
