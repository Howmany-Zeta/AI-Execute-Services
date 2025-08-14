#!/usr/bin/env python3
"""
Test Runner Script for MiningService Event Loop Tests

This script provides easy debugging capabilities for running specific tests
or test categories with different levels of verbosity and debugging options.
"""

import sys
import os
import subprocess
import argparse
from typing import List, Optional


def run_pytest_tests(
    test_file: str = "test_clarification_loop.py",
    test_pattern: Optional[str] = None,
    markers: Optional[List[str]] = None,
    verbose: bool = True,
    debug: bool = False,
    capture_output: bool = False
) -> subprocess.CompletedProcess:
    """
    Run pytest tests with specified options.

    Args:
        test_file: The test file to run
        test_pattern: Pattern to match specific tests
        markers: List of pytest markers to run
        verbose: Whether to run in verbose mode
        debug: Whether to run in debug mode
        capture_output: Whether to capture output

    Returns:
        CompletedProcess result from pytest
    """

    cmd = [sys.executable, "-m", "pytest", test_file]

    # Add verbosity
    if verbose:
        cmd.append("-v")
    if debug:
        cmd.append("-s")  # Don't capture stdout/stderr
        cmd.append("--tb=long")  # Full traceback
    else:
        cmd.append("--tb=short")

    # Add test pattern if specified
    if test_pattern:
        cmd.extend(["-k", test_pattern])

    # Add markers if specified
    if markers:
        for marker in markers:
            cmd.extend(["-m", marker])

    # Add output capture option
    if capture_output:
        cmd.append("--capture=no")

    # Add additional useful options
    cmd.extend([
        "--durations=10",
        "--color=yes"
    ])

    print(f"Running command: {' '.join(cmd)}")

    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd)

    return result


def run_specific_test(test_name: str, debug: bool = False) -> subprocess.CompletedProcess:
    """Run a specific test by name."""
    return run_pytest_tests(
        test_pattern=test_name,
        debug=debug,
        capture_output=not debug
    )


def run_debug_tests(debug: bool = True) -> subprocess.CompletedProcess:
    """Run all debug tests."""
    return run_pytest_tests(
        markers=["debug"],
        debug=debug,
        capture_output=not debug
    )


def run_integration_tests(debug: bool = False) -> subprocess.CompletedProcess:
    """Run all integration tests."""
    return run_pytest_tests(
        markers=["integration"],
        debug=debug,
        capture_output=not debug
    )


def run_unit_tests(debug: bool = False) -> subprocess.CompletedProcess:
    """Run all unit tests."""
    return run_pytest_tests(
        markers=["unit"],
        debug=debug,
        capture_output=not debug
    )


def run_all_tests(debug: bool = False) -> subprocess.CompletedProcess:
    """Run all tests."""
    return run_pytest_tests(
        debug=debug,
        capture_output=not debug
    )


def list_available_tests() -> None:
    """List all available tests."""
    cmd = [
        sys.executable, "-m", "pytest",
        "test_clarification_loop.py",
        "--collect-only",
        "-q"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Available tests:")
        for line in result.stdout.split('\n'):
            if line.strip() and 'test_' in line:
                print(f"  {line.strip()}")
    else:
        print("Error collecting tests:")
        print(result.stderr)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run MiningService Event Loop Tests with debugging options"
    )

    parser.add_argument(
        "--test", "-t",
        help="Run specific test by name pattern"
    )

    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Run in debug mode with full output"
    )

    parser.add_argument(
        "--category", "-c",
        choices=["debug", "integration", "unit", "all"],
        default="all",
        help="Run tests by category"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available tests"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Run in verbose mode"
    )

    args = parser.parse_args()

    if args.list:
        list_available_tests()
        return

    try:
        if args.test:
            print(f"Running specific test: {args.test}")
            result = run_specific_test(args.test, args.debug)
        elif args.category == "debug":
            print("Running debug tests...")
            result = run_debug_tests(args.debug)
        elif args.category == "integration":
            print("Running integration tests...")
            result = run_integration_tests(args.debug)
        elif args.category == "unit":
            print("Running unit tests...")
            result = run_unit_tests(args.debug)
        else:
            print("Running all tests...")
            result = run_all_tests(args.debug)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with return code: {result.returncode}")
            if hasattr(result, 'stderr') and result.stderr:
                print(f"Error output:\n{result.stderr}")

        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\n⚠️ Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
