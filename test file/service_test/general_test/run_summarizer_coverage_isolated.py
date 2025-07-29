#!/usr/bin/env python3
"""
Isolated Coverage Test Runner for SummarizerService

This script runs coverage testing for the SummarizerService while avoiding
PyO3 dependency conflicts by skipping the problematic office_tool import.

Usage:
    python run_summarizer_coverage_isolated.py
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run isolated coverage testing for SummarizerService"""

    # Set environment variable to skip office_tool import
    os.environ['SKIP_OFFICE_TOOL'] = 'true'

    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    # Change to project root directory
    os.chdir(project_root)

    print("🔬 Running Isolated Coverage Testing for SummarizerService")
    print("=" * 60)
    print(f"📁 Project Root: {project_root}")
    print(f"🚫 Skipping office_tool import to avoid PyO3 conflicts")
    print("=" * 60)

    # Coverage command focusing specifically on summarizer module
    coverage_cmd = [
        "poetry", "run", "pytest",
        "--cov=app.services.general.services.summarizer",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov_summarizer_isolated",
        "--cov-config=test file/service_test/pytest_summarizer_isolated.ini",
        "-c", "test file/service_test/pytest_summarizer_isolated.ini",
        "test file/service_test/test_summarizer_real_api.py",
        "-v"
    ]

    try:
        print("🧪 Starting coverage analysis...")
        print(f"📋 Command: {' '.join(coverage_cmd)}")
        print("-" * 60)

        # Run the coverage command
        result = subprocess.run(
            coverage_cmd,
            cwd=project_root,
            env=os.environ.copy(),
            capture_output=False,
            text=True
        )

        print("-" * 60)
        if result.returncode == 0:
            print("✅ Coverage testing completed successfully!")
            print(f"📊 HTML coverage report generated: htmlcov_summarizer/index.html")
        else:
            print(f"❌ Coverage testing failed with exit code: {result.returncode}")
            return result.returncode

    except Exception as e:
        print(f"💥 Error running coverage testing: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
