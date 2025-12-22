"""
Pytest configuration for knowledge graph tests
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv


def pytest_configure(config):
    """Load test environment variables before tests run"""
    # Get the project root directory (go up from test/unit_tests/knowledge_graph/conftest.py)
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Try to load .env.test file
    env_test_path = project_root / ".env.test"
    if env_test_path.exists():
        load_dotenv(env_test_path, override=True)
        print(f"Loaded test environment from {env_test_path}")
    else:
        # If .env.test doesn't exist, set minimal defaults for testing
        os.environ.setdefault("DOC_PARSER_ENABLE_CLOUD_STORAGE", "false")
        os.environ.setdefault("DOC_PARSER_USER_AGENT", "DocumentParser/Test/1.0")
        os.environ.setdefault("DOC_PARSER_TEMP_DIR", "/tmp/aiecs_test_document_parser")
        print("Using default test environment variables (no .env.test file found)")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Session-scoped fixture to ensure environment variables are loaded
    before any DocumentParserTool instances are created.
    
    This runs before any tests and ensures the environment is properly
    configured even when coverage collection instruments the code.
    """
    # Get the project root directory (go up from test/unit_tests/knowledge_graph/conftest.py)
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Try to load .env.test file
    env_test_path = project_root / ".env.test"
    if env_test_path.exists():
        load_dotenv(env_test_path, override=True)
    else:
        # Set minimal defaults for testing
        os.environ.setdefault("DOC_PARSER_ENABLE_CLOUD_STORAGE", "false")
        os.environ.setdefault("DOC_PARSER_USER_AGENT", "DocumentParser/Test/1.0")
        os.environ.setdefault("DOC_PARSER_TEMP_DIR", "/tmp/aiecs_test_document_parser")
        os.environ.setdefault("DOC_PARSER_MAX_FILE_SIZE", "52428800")
        os.environ.setdefault("DOC_PARSER_DEFAULT_ENCODING", "utf-8")
        os.environ.setdefault("DOC_PARSER_TIMEOUT", "30")
        os.environ.setdefault("DOC_PARSER_MAX_PAGES", "1000")
        os.environ.setdefault("DOC_PARSER_GCS_BUCKET_NAME", "test-aiecs-documents")
    
    # Pre-load Settings to ensure they're initialized before coverage instruments the code
    # This prevents pytest-cov from interfering with Pydantic BaseSettings
    try:
        from aiecs.config.config import get_settings
        # Clear the cache to force reload with new environment
        get_settings.cache_clear()
        settings = get_settings()
        # Verify settings loaded correctly
        assert settings is not None
    except Exception as e:
        # If Settings loading fails, log but don't fail the test setup
        # The actual tests will handle missing configuration
        import logging
        logging.warning(f"Failed to pre-load Settings: {e}")
    
    yield
    
    # Cleanup if needed (optional)


@pytest.fixture
def check_llm_configured():
    """
    Check if LLM is configured for testing.
    Skips test if LLM credentials are not available.
    """
    # Check for any LLM provider configuration
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_vertex = bool(os.getenv("VERTEX_PROJECT_ID") and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    has_googleai = bool(os.getenv("GOOGLEAI_API_KEY"))
    has_xai = bool(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
    
    if not (has_openai or has_vertex or has_googleai or has_xai):
        pytest.skip("LLM not configured. Please set OPENAI_API_KEY, VERTEX_PROJECT_ID+GOOGLE_APPLICATION_CREDENTIALS, GOOGLEAI_API_KEY, or XAI_API_KEY in .env.test")
    
    return True

