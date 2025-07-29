#!/usr/bin/env python3
"""
Script to run service_executor integration tests with Poetry
"""
import subprocess
import sys
import os

def run_integration_tests():
    """Run the service_executor integration tests using Poetry"""

    # Change to the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🧪 Running ServiceExecutor Integration Tests with Poetry...")
    print("=" * 70)

    # Command to run integration tests with Poetry
    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor_integration.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-m", "not slow"  # Skip slow tests by default
    ]

    try:
        # Run the tests
        result = subprocess.run(cmd, check=True)
        print("\n✅ Integration tests completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Integration tests failed with exit code: {e.returncode}")
        return e.returncode

    except FileNotFoundError:
        print("❌ Poetry not found. Please install Poetry first:")
        print("   curl -sSL https://install.python-poetry.org | python3 -")
        return 1

def run_integration_tests_with_coverage():
    """Run integration tests with coverage report"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🧪 Running ServiceExecutor Integration Tests with coverage...")
    print("=" * 70)

    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor_integration.py",
        "-v",
        "--cov=app.services.service_executor",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_integration",
        "--asyncio-mode=auto",
        "-m", "not slow"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Integration tests with coverage completed successfully!")
        print("📊 Coverage report saved to htmlcov_integration/index.html")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Integration tests failed with exit code: {e.returncode}")
        return e.returncode

def run_all_tests():
    """Run both unit tests and integration tests"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🧪 Running ALL ServiceExecutor Tests (Unit + Integration)...")
    print("=" * 70)

    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor.py",
        "test file/application_tests/test_service_executor_integration.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ All tests completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

def run_slow_tests():
    """Run slow integration tests"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🐌 Running Slow Integration Tests...")
    print("=" * 70)

    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor_integration.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-m", "slow"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Slow tests completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Slow tests failed with exit code: {e.returncode}")
        return e.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--coverage":
            exit_code = run_integration_tests_with_coverage()
        elif sys.argv[1] == "--all":
            exit_code = run_all_tests()
        elif sys.argv[1] == "--slow":
            exit_code = run_slow_tests()
        else:
            print("Usage: python run_integration_tests.py [--coverage|--all|--slow]")
            exit_code = 1
    else:
        exit_code = run_integration_tests()

    sys.exit(exit_code)
