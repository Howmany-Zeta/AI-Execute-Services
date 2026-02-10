"""
Fixtures for ContextEngine integration tests (Redis + ClickHouse).

Requires: Redis and ClickHouse running, configured in .env.test
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test before any imports that read env
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)

# Ensure ClickHouse is enabled for these tests
os.environ["CLICKHOUSE_ENABLED"] = "true"


@pytest.fixture(scope="module")
def llm_response_content():
    """Load real LLM response from test/data/response.txt."""
    path = PROJECT_ROOT / "test" / "data" / "response.txt"
    if not path.exists():
        pytest.skip(f"LLM response file not found: {path}")
    return path.read_text(encoding="utf-8")
