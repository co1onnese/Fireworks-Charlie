#!/usr/bin/env python3
"""
Test runner for Evalprotocol Server

Simple script to run the test suite with proper configuration.

Usage:
    python rlvr/run_tests.py [--verbose] [--coverage]

Author: Fireworks-Charlie Team
Date: 2025-12-07
"""

import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_tests(verbose=False, coverage=False):
    """Run the test suite."""
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append("rlvr/tests/")
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=rlvr", "--cov-report=html", "--cov-report=term"])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "--strict-markers",  # Strict marker checking
        "-ra"  # Show all test results
    ])
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Evalprotocol Server tests")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    
    args = parser.parse_args()
    
    print("🧪 Running Evalprotocol Server Tests")
    
    exit_code = run_tests(verbose=args.verbose, coverage=args.coverage)
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
