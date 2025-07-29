#!/usr/bin/env python3
"""
Script to run service_executor tests with Poetry
"""
import subprocess
import sys
import os

def run_tests():
    """Run the service_executor tests using Poetry"""

    # Change to the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🧪 Running ServiceExecutor tests with Poetry...")
    print("=" * 60)

    # Command to run tests with Poetry
    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor.py",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]

    try:
        # Run the tests
        result = subprocess.run(cmd, check=True)
        print("\n✅ Tests completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

    except FileNotFoundError:
        print("❌ Poetry not found. Please install Poetry first:")
        print("   curl -sSL https://install.python-poetry.org | python3 -")
        return 1

def run_tests_with_coverage():
    """Run tests with coverage report"""

    # Change to the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.join(script_dir, "..", "..")
    os.chdir(project_dir)

    print("🧪 Running ServiceExecutor tests with coverage...")
    print("=" * 60)

    cmd = [
        "poetry", "run", "pytest",
        "test file/application_tests/test_service_executor.py",
        "-v",
        "--cov=app.services.service_executor",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--asyncio-mode=auto"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n✅ Tests with coverage completed successfully!")
        print("📊 Coverage report saved to htmlcov/index.html")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        exit_code = run_tests_with_coverage()
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
