#!/usr/bin/env python3
"""
Test runner script for user_token API tests.

This script provides a convenient way to run the user_token API tests with various options.
It can be used for development, CI/CD, and debugging purposes.

Usage:
    python run_pytest_user_token_api.py [options]

Examples:
    # Run all tests
    python run_pytest_user_token_api.py

    # Run tests with verbose output
    python run_pytest_user_token_api.py --verbose

    # Run specific test class
    python run_pytest_user_token_api.py --test-class TestGetUserTokenUsage

    # Run tests with coverage report
    python run_pytest_user_token_api.py --coverage

    # Run tests in parallel
    python run_pytest_user_token_api.py --parallel

    # Generate HTML coverage report
    python run_pytest_user_token_api.py --coverage --html-report
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def setup_python_path():
    """Setup Python path to include the project root."""
    # Get the project root directory (3 levels up from this script)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent

    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Set PYTHONPATH environment variable
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    if str(project_root) not in current_pythonpath:
        os.environ['PYTHONPATH'] = f"{project_root}:{current_pythonpath}" if current_pythonpath else str(project_root)


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'pytest',
        'pytest-asyncio',
        'fastapi',
        'httpx',  # Required for TestClient
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    return True


def build_pytest_command(args):
    """Build the pytest command based on arguments."""
    cmd = ['python', '-m', 'pytest']

    # Test file path
    test_file = Path(__file__).parent / 'test_user_token_api.py'

    # Add specific test class if specified
    if args.test_class:
        cmd.append(f"{test_file}::{args.test_class}")
    elif args.test_method:
        cmd.append(f"{test_file}::{args.test_method}")
    else:
        cmd.append(str(test_file))

    # Verbosity options
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')

    # Output options
    if args.show_capture:
        cmd.append('-s')

    # Coverage options
    if args.coverage:
        cmd.extend([
            '--cov=app.api.user_token',
            '--cov=app.utils.token_usage_repository',
            '--cov-report=term-missing'
        ])

        if args.html_report:
            cmd.append('--cov-report=html:htmlcov')

    # Parallel execution
    if args.parallel:
        try:
            import pytest_xdist
            cmd.extend(['-n', 'auto'])
        except ImportError:
            print("⚠️  pytest-xdist not installed. Running tests sequentially.")

    # Additional pytest options
    if args.fail_fast:
        cmd.append('-x')

    if args.last_failed:
        cmd.append('--lf')

    if args.markers:
        cmd.extend(['-m', args.markers])

    # Add any extra arguments
    if args.extra_args:
        cmd.extend(args.extra_args.split())

    return cmd


def run_tests(cmd):
    """Run the pytest command and return the result."""
    print("🚀 Running user_token API tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def print_summary(return_code):
    """Print test summary based on return code."""
    print("-" * 60)
    if return_code == 0:
        print("✅ All tests passed!")
    elif return_code == 1:
        print("❌ Some tests failed")
    elif return_code == 2:
        print("❌ Test execution was interrupted")
    elif return_code == 3:
        print("❌ Internal error occurred")
    elif return_code == 4:
        print("❌ pytest command line usage error")
    elif return_code == 5:
        print("❌ No tests were collected")
    else:
        print(f"❌ Tests exited with code {return_code}")


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(
        description="Run user_token API tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Test selection options
    parser.add_argument(
        '--test-class',
        help='Run specific test class (e.g., TestGetUserTokenUsage)'
    )
    parser.add_argument(
        '--test-method',
        help='Run specific test method (e.g., TestGetUserTokenUsage::test_get_user_token_usage_success)'
    )
    parser.add_argument(
        '-m', '--markers',
        help='Run tests with specific markers'
    )

    # Output options
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet output'
    )
    parser.add_argument(
        '-s', '--show-capture',
        action='store_true',
        help='Show captured output (don\'t capture stdout/stderr)'
    )

    # Coverage options
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run tests with coverage report'
    )
    parser.add_argument(
        '--html-report',
        action='store_true',
        help='Generate HTML coverage report (requires --coverage)'
    )

    # Execution options
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel (requires pytest-xdist)'
    )
    parser.add_argument(
        '-x', '--fail-fast',
        action='store_true',
        help='Stop on first failure'
    )
    parser.add_argument(
        '--last-failed',
        action='store_true',
        help='Run only tests that failed in the last run'
    )

    # Additional options
    parser.add_argument(
        '--extra-args',
        help='Additional arguments to pass to pytest'
    )
    parser.add_argument(
        '--skip-deps-check',
        action='store_true',
        help='Skip dependency check'
    )

    args = parser.parse_args()

    # Setup environment
    setup_python_path()

    # Check dependencies
    if not args.skip_deps_check and not check_dependencies():
        return 1

    # Build and run pytest command
    cmd = build_pytest_command(args)
    return_code = run_tests(cmd)

    # Print summary
    print_summary(return_code)

    # Additional information
    if args.coverage and args.html_report and return_code == 0:
        html_report_path = Path(__file__).parent / 'htmlcov' / 'index.html'
        if html_report_path.exists():
            print(f"📊 HTML coverage report generated: {html_report_path}")

    return return_code


if __name__ == '__main__':
    sys.exit(main())
