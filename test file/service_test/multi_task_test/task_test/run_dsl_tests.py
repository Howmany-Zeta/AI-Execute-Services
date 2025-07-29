#!/usr/bin/env python3
"""
Test runner script for DSL workflow function tests.

This script demonstrates how to run the comprehensive DSL tests with coverage.
It can be used with poetry and pytest to execute all DSL-related tests.

Usage:
    python run_dsl_tests.py

Or with poetry:
    poetry run python run_dsl_tests.py

Or directly with pytest:
    pytest test_workflow_dsl_function.py -v --cov
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Run DSL tests with coverage reporting."""

    # Get the directory containing this script
    script_dir = Path(__file__).parent
    test_file = script_dir / "test_workflow_dsl_function.py"

    # Check if test file exists
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)

    # Pytest command with coverage
    cmd = [
        "python", "-m", "pytest",
        str(test_file),
        "-v",
        "--cov=../../../../app/services/multi_task/workflows/dsl",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=85",
        "--tb=short",
        "--durations=10"
    ]

    print("Running DSL workflow function tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)

    try:
        # Run the tests
        result = subprocess.run(cmd, cwd=script_dir, check=False)

        if result.returncode == 0:
            print("\n" + "=" * 80)
            print("✅ All DSL tests passed successfully!")
            print("📊 Coverage report generated in htmlcov/ directory")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ Some tests failed or coverage threshold not met")
            print("📊 Check the coverage report for details")
            print("=" * 80)

        return result.returncode

    except FileNotFoundError:
        print("Error: pytest not found. Please install pytest and pytest-cov:")
        print("  pip install pytest pytest-cov pytest-asyncio")
        print("  or")
        print("  poetry add --group dev pytest pytest-cov pytest-asyncio")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def run_specific_test_class(test_class_name):
    """Run a specific test class."""
    script_dir = Path(__file__).parent
    test_file = script_dir / "test_workflow_dsl_function.py"

    cmd = [
        "python", "-m", "pytest",
        f"{test_file}::{test_class_name}",
        "-v",
        "--tb=short"
    ]

    print(f"Running test class: {test_class_name}")
    result = subprocess.run(cmd, cwd=script_dir, check=False)
    return result.returncode

def run_with_markers(marker):
    """Run tests with specific markers."""
    script_dir = Path(__file__).parent
    test_file = script_dir / "test_workflow_dsl_function.py"

    cmd = [
        "python", "-m", "pytest",
        str(test_file),
        "-m", marker,
        "-v"
    ]

    print(f"Running tests with marker: {marker}")
    result = subprocess.run(cmd, cwd=script_dir, check=False)
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--class" and len(sys.argv) > 2:
            # Run specific test class
            exit_code = run_specific_test_class(sys.argv[2])
        elif sys.argv[1] == "--marker" and len(sys.argv) > 2:
            # Run tests with specific marker
            exit_code = run_with_markers(sys.argv[2])
        else:
            print("Usage:")
            print("  python run_dsl_tests.py                    # Run all tests")
            print("  python run_dsl_tests.py --class TestDSLParser  # Run specific class")
            print("  python run_dsl_tests.py --marker asyncio       # Run async tests only")
            exit_code = 1
    else:
        # Run all tests
        exit_code = main()

    sys.exit(exit_code)
