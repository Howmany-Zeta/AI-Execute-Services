"""
E2E Test Configuration

This conftest provides E2E-specific configuration including:
- Real API key loading from environment
- E2E test utilities
- Cost tracking for API calls
- Skip conditions for missing API keys
"""

import pytest
import os
import logging
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv


# =============================================================================
# Environment Setup for E2E Tests
# =============================================================================

# Load .env file for E2E tests (contains real API keys)
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    logging.info("✓ Loaded E2E environment variables from .env")


# =============================================================================
# API Key Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def api_keys() -> Dict[str, str]:
    """
    Load all API keys from environment.
    
    Returns:
        dict: Dictionary of API keys
    """
    return {
        'openai': os.getenv('OPENAI_API_KEY'),
        'google': os.getenv('GOOGLEAI_API_KEY'),
        'vertex_project': os.getenv('VERTEX_PROJECT_ID'),
        'vertex_location': os.getenv('VERTEX_LOCATION', 'us-central1'),
        'xai': os.getenv('XAI_API_KEY'),
        'google_cse_id': os.getenv('GOOGLE_CSE_ID'),
        'google_cse_key': os.getenv('GOOGLE_CSE_API_KEY')
    }


@pytest.fixture(scope="session")
def openai_api_key(api_keys) -> str:
    """
    Get OpenAI API key from environment.
    
    Returns:
        str: OpenAI API key
        
    Raises:
        pytest.skip: If API key is not set
    """
    key = api_keys['openai']
    if not key:
        pytest.skip("OPENAI_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def google_api_key(api_keys) -> str:
    """
    Get Google AI API key from environment.
    
    Returns:
        str: Google AI API key
        
    Raises:
        pytest.skip: If API key is not set
    """
    key = api_keys['google']
    if not key:
        pytest.skip("GOOGLEAI_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def vertex_config(api_keys) -> Dict[str, str]:
    """
    Get Vertex AI configuration from environment.
    
    Returns:
        dict: Vertex AI configuration
        
    Raises:
        pytest.skip: If configuration is not complete
    """
    project_id = api_keys['vertex_project']
    location = api_keys['vertex_location']
    
    if not project_id:
        pytest.skip("VERTEX_PROJECT_ID not set in environment")
    
    return {
        'project_id': project_id,
        'location': location
    }


@pytest.fixture(scope="session")
def xai_api_key(api_keys) -> str:
    """
    Get xAI API key from environment.
    
    Returns:
        str: xAI API key
        
    Raises:
        pytest.skip: If API key is not set
    """
    key = api_keys['xai']
    if not key:
        pytest.skip("XAI_API_KEY not set in environment")
    return key


@pytest.fixture(scope="session")
def google_cse_config(api_keys) -> Dict[str, str]:
    """
    Get Google Custom Search Engine configuration.
    
    Returns:
        dict: Google CSE configuration
        
    Raises:
        pytest.skip: If configuration is not complete
    """
    cse_id = api_keys['google_cse_id']
    cse_key = api_keys['google_cse_key']
    
    if not cse_id or not cse_key:
        pytest.skip("Google CSE configuration not complete")
    
    return {
        'cse_id': cse_id,
        'api_key': cse_key
    }


# =============================================================================
# Skip Helpers
# =============================================================================

@pytest.fixture
def skip_if_no_openai():
    """Skip test if OpenAI API key is not available."""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("OPENAI_API_KEY not set")


@pytest.fixture
def skip_if_no_google():
    """Skip test if Google AI API key is not available."""
    if not os.getenv('GOOGLEAI_API_KEY'):
        pytest.skip("GOOGLEAI_API_KEY not set")


@pytest.fixture
def skip_if_no_vertex():
    """Skip test if Vertex AI configuration is not available."""
    if not os.getenv('VERTEX_PROJECT_ID'):
        pytest.skip("VERTEX_PROJECT_ID not set")


@pytest.fixture
def skip_if_no_xai():
    """Skip test if xAI API key is not available."""
    if not os.getenv('XAI_API_KEY'):
        pytest.skip("XAI_API_KEY not set")


# =============================================================================
# Cost Tracking
# =============================================================================

class CostTracker:
    """Track API call costs during E2E tests."""
    
    def __init__(self):
        self.calls = []
        self.total_tokens = 0
        self.estimated_cost = 0.0
    
    def record_call(self, provider: str, model: str, 
                   prompt_tokens: int, completion_tokens: int,
                   cost: float = 0.0):
        """Record an API call."""
        total = prompt_tokens + completion_tokens
        self.calls.append({
            'provider': provider,
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total,
            'cost': cost
        })
        self.total_tokens += total
        self.estimated_cost += cost
    
    def summary(self) -> str:
        """Get cost summary."""
        return (
            f"E2E Test API Usage:\n"
            f"  Total Calls: {len(self.calls)}\n"
            f"  Total Tokens: {self.total_tokens}\n"
            f"  Estimated Cost: ${self.estimated_cost:.4f}"
        )


@pytest.fixture(scope="session")
def cost_tracker():
    """
    Create a cost tracker for E2E tests.
    
    Returns:
        CostTracker: Instance to track API costs
    """
    tracker = CostTracker()
    yield tracker
    
    # Print summary at end of session
    if tracker.calls:
        print("\n" + "="*60)
        print(tracker.summary())
        print("="*60)


# =============================================================================
# E2E Test Utilities
# =============================================================================

@pytest.fixture
def minimal_prompt():
    """
    Get a minimal prompt for testing to reduce token usage.
    
    Returns:
        str: Minimal test prompt
    """
    return "Say 'OK' if you understand."


@pytest.fixture
def test_messages():
    """
    Get minimal test messages for chat testing.
    
    Returns:
        list: Minimal chat messages
    """
    return [
        {"role": "user", "content": "Reply with just 'OK'"}
    ]


# =============================================================================
# Pytest Configuration for E2E
# =============================================================================

def pytest_configure(config):
    """Configure pytest for E2E tests."""
    config.addinivalue_line(
        "markers", 
        "openai: Tests requiring OpenAI API"
    )
    config.addinivalue_line(
        "markers", 
        "google: Tests requiring Google AI API"
    )
    config.addinivalue_line(
        "markers", 
        "vertex: Tests requiring Vertex AI"
    )
    config.addinivalue_line(
        "markers", 
        "xai: Tests requiring xAI API"
    )
    config.addinivalue_line(
        "markers", 
        "expensive: Tests that may cost significant API credits"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark E2E tests."""
    for item in items:
        # All E2E tests are slow and require APIs
        item.add_marker(pytest.mark.slow)
        item.add_marker(pytest.mark.requires_api)
        
        # Add provider-specific markers based on test name
        test_name = item.name.lower()
        if "openai" in test_name:
            item.add_marker(pytest.mark.openai)
        if "google" in test_name or "gemini" in test_name:
            item.add_marker(pytest.mark.google)
        if "vertex" in test_name:
            item.add_marker(pytest.mark.vertex)
        if "xai" in test_name or "grok" in test_name:
            item.add_marker(pytest.mark.xai)
