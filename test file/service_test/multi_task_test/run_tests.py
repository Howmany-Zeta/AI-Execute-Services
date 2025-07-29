#!/usr/bin/env python3
"""
Test runner script for agent layer tests.

This script provides convenient ways to run the agent layer tests with different configurations:
- All tests
- Specific test categories
- Real API tests only
- Unit tests only
- Performance tests

Usage:
    python run_tests.py [options]
    poetry run python run_tests.py [options]
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or Path(__file__).parent,
            capture_output=False,
            text=True,
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        return False


def check_environment():
    """Check if the test environment is properly set up."""
    print("Checking test environment...")

    # Check required environment variables
    required_vars = ["OPENAI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these variables before running tests.")
        return False

    # Check if poetry is available
    try:
        subprocess.run(["poetry", "--version"], capture_output=True, check=True)
        print("✅ Poetry is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Poetry is not available. Please install poetry first.")
        return False

    # Check if project dependencies are installed
    try:
        subprocess.run(["poetry", "check"], capture_output=True, check=True)
        print("✅ Poetry dependencies are properly configured")
    except subprocess.CalledProcessError:
        print("⚠️  Poetry dependencies may need to be installed")
        print("Run: poetry install")

    print("✅ Environment check completed")
    return True


def run_all_tests():
    """Run all agent layer tests."""
    print("\n🚀 Running all agent layer tests...")
    cmd = [
        "poetry", "run", "pytest",
        "test_agent_layer.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--durations=10"
    ]
    return run_command(cmd)


def run_unit_tests():
    """Run unit tests only (no real API calls)."""
    print("\n🧪 Running unit tests only...")
    cmd = [
        "poetry", "run", "pytest",
        "test_agent_layer.py",
        "-v",
        "-m", "not real_api",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    return run_command(cmd)


def run_integration_tests():
    """Run integration tests with real API calls."""
    print("\n🔗 Running integration tests with real API calls...")
    cmd = [
        "poetry", "run", "pytest",
        "test_agent_layer.py",
        "-v",
        "-m", "real_api",
        "--tb=short",
        "--asyncio-mode=auto",
        "--durations=10"
    ]
    return run_command(cmd)


def run_smoke_tests():
    """Run smoke tests for quick validation."""
    print("\n💨 Running smoke tests...")
    cmd = [
        "poetry", "run", "pytest",
        "test_agent_layer.py",
        "-v",
        "-m", "smoke",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    return run_command(cmd)


def run_specific_test_class(test_class):
    """Run a specific test class."""
    print(f"\n🎯 Running specific test class: {test_class}")
    cmd = [
        "poetry", "run", "pytest",
        f"test_agent_layer.py::{test_class}",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    return run_command(cmd)


def run_with_coverage():
    """Run tests with coverage reporting."""
    print("\n📊 Running tests with coverage reporting...")
    cmd = [
        "poetry", "run", "pytest",
        "test_agent_layer.py",
        "-v",
        "--cov=app.services.multi_task.agent",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    return run_command(cmd)


def install_dependencies():
    """Install test dependencies."""
    print("\n📦 Installing dependencies...")
    cmd = ["poetry", "install"]
    return run_command(cmd)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Agent Layer Test Runner")
    parser.add_argument(
        "--mode",
        choices=["all", "unit", "integration", "smoke", "coverage"],
        default="all",
        help="Test mode to run"
    )
    parser.add_argument(
        "--class",
        dest="test_class",
        help="Specific test class to run"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install dependencies before running tests"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Only check environment setup"
    )

    args = parser.parse_args()

    print("🧪 Agent Layer Test Runner")
    print("=" * 50)

    # Check environment
    if not check_environment():
        sys.exit(1)

    if args.check_env:
        print("✅ Environment check completed successfully")
        sys.exit(0)

    # Install dependencies if requested
    if args.install:
        if not install_dependencies():
            print("❌ Failed to install dependencies")
            sys.exit(1)

    # Run tests based on mode
    success = False

    if args.test_class:
        success = run_specific_test_class(args.test_class)
    elif args.mode == "all":
        success = run_all_tests()
    elif args.mode == "unit":
        success = run_unit_tests()
    elif args.mode == "integration":
        success = run_integration_tests()
    elif args.mode == "smoke":
        success = run_smoke_tests()
    elif args.mode == "coverage":
        success = run_with_coverage()

    # Print results
    print("\n" + "=" * 50)
    if success:
        print("✅ Tests completed successfully!")
        print("\nNext steps:")
        print("- Review test results above")
        print("- Check any warnings or failures")
        print("- Verify AI API responses are valid")
    else:
        print("❌ Tests failed!")
        print("\nTroubleshooting:")
        print("- Check environment variables are set")
        print("- Verify API keys are valid")
        print("- Review error messages above")
        print("- Run with --mode unit to test without API calls")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
