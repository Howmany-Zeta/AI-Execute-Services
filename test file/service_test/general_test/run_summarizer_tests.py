#!/usr/bin/env python3
"""
Test Runner for SummarizerService Real API Tests

This script provides an easy way to run the comprehensive SummarizerService tests
with real XAI and Vertex AI API connections.

Usage:
    python run_summarizer_tests.py [options]

Options:
    --xai-only      Run only XAI tests
    --vertex-only   Run only Vertex AI tests
    --integration   Run only integration tests
    --quick         Run quick tests (skip slow ones)
    --parallel      Run tests in parallel
    --workers N     Number of parallel workers (default: auto)
    --coverage      Run with coverage analysis
    --verbose       Verbose output
    --help          Show this help message

Environment Variables Required:
    XAI_API_KEY or GROK_API_KEY    - For XAI/Grok API tests
    VERTEX_PROJECT_ID              - For Vertex AI tests
    GOOGLE_APPLICATION_CREDENTIALS - Path to Google Cloud credentials file
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking environment configuration...")

    # Check XAI configuration
    xai_key = os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
    if xai_key:
        print("✅ XAI API key configured")
        xai_available = True
    else:
        print("⚠️  XAI API key not found (set XAI_API_KEY or GROK_API_KEY)")
        xai_available = False

    # Check Vertex AI configuration
    vertex_project = os.getenv('VERTEX_PROJECT_ID')
    vertex_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if vertex_project:
        print("✅ Vertex AI project ID configured")
        if vertex_creds and os.path.exists(vertex_creds):
            print("✅ Google Cloud credentials file found")
            vertex_available = True
        else:
            print("⚠️  Google Cloud credentials not found or invalid")
            vertex_available = False
    else:
        print("⚠️  Vertex AI project ID not found (set VERTEX_PROJECT_ID)")
        vertex_available = False

    return xai_available, vertex_available

def run_tests(test_filter=None, verbose=False, quick=False, parallel=False, workers=None, coverage=False):
    """Run the tests with specified filters"""

    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "test_summarizer_real_api.py",
        "-c", "pytest_summarizer.ini"
    ]

    # Add verbosity
    if verbose:
        cmd.extend(["-v", "-s"])

    # Add parallel execution
    if parallel:
        if workers:
            cmd.extend(["-n", str(workers)])
        else:
            cmd.extend(["-n", "auto"])

    # Add coverage analysis
    if coverage:
        cmd.extend([
            "--cov=app.services.general.services.summarizer",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])

    # Add test filters
    if test_filter:
        cmd.extend(["-k", test_filter])

    # Skip slow tests if quick mode
    if quick:
        cmd.extend(["-m", "not slow"])

    # Add markers for real API tests
    cmd.extend(["-m", "not slow or real_api"])

    print(f"🚀 Running command: {' '.join(cmd)}")
    print("=" * 80)

    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Run SummarizerService real API tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--xai-only",
        action="store_true",
        help="Run only XAI/Grok API tests"
    )

    parser.add_argument(
        "--vertex-only",
        action="store_true",
        help="Run only Vertex AI tests"
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip slow ones)"
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )

    parser.add_argument(
        "--workers",
        type=int,
        metavar="N",
        help="Number of parallel workers (default: auto)"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage analysis"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    print("🧪 SummarizerService Real API Test Runner")
    print("=" * 50)

    # Check environment
    xai_available, vertex_available = check_environment()

    if not xai_available and not vertex_available:
        print("\n❌ No API keys configured. Please set up at least one:")
        print("   - XAI_API_KEY or GROK_API_KEY for XAI tests")
        print("   - VERTEX_PROJECT_ID + GOOGLE_APPLICATION_CREDENTIALS for Vertex AI tests")
        return 1

    # Determine test filter
    test_filter = None

    if args.xai_only:
        if not xai_available:
            print("\n❌ XAI API key not configured")
            return 1
        test_filter = "xai"
        print("\n🎯 Running XAI-only tests")

    elif args.vertex_only:
        if not vertex_available:
            print("\n❌ Vertex AI not properly configured")
            return 1
        test_filter = "vertex"
        print("\n🎯 Running Vertex AI-only tests")

    elif args.integration:
        test_filter = "integration"
        print("\n🎯 Running integration tests")

    else:
        print(f"\n🎯 Running all available tests")
        if xai_available:
            print("   ✅ XAI tests will run")
        if vertex_available:
            print("   ✅ Vertex AI tests will run")

    # Show additional options
    if args.parallel:
        workers_info = f" with {args.workers} workers" if args.workers else " with auto workers"
        print(f"⚡ Parallel execution enabled{workers_info}")

    if args.coverage:
        print("📊 Coverage analysis enabled")

    if args.quick:
        print("🏃 Quick mode enabled (skipping slow tests)")

    print()

    # Run tests
    exit_code = run_tests(
        test_filter=test_filter,
        verbose=args.verbose,
        quick=args.quick,
        parallel=args.parallel,
        workers=args.workers,
        coverage=args.coverage
    )

    print("\n" + "=" * 80)
    if exit_code == 0:
        print("🎉 All tests completed successfully!")
    else:
        print("❌ Some tests failed or encountered errors")

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
