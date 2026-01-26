"""
Pytest configuration and fixtures for APISource Tool tests

This module provides shared fixtures and configuration for all APISource tests.
Loads API keys from .env.apisource and provides common test utilities.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

import pytest
from dotenv import load_dotenv


# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test/logs/apisource_tests.log')
    ]
)

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "network: marks tests that require network access (deselect with '-m \"not network\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "provider: marks tests for specific providers"
    )


@pytest.fixture(scope="session", autouse=True)
def load_env_config():
    """Load environment variables from .env.apisource and .env.test"""
    root_path = Path(__file__).parent.parent.parent.parent.parent

    # Try .env.apisource first
    env_file = root_path / '.env.apisource'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"✓ Loaded environment from {env_file}")
    else:
        logger.warning(f"⚠ Environment file not found: {env_file}")

    # Also load .env.test (will override .env.apisource if both exist)
    env_test_file = root_path / '.env.test'
    if env_test_file.exists():
        load_dotenv(env_test_file, override=True)
        logger.info(f"✓ Loaded environment from {env_test_file}")
    else:
        logger.warning(f"⚠ Environment file not found: {env_test_file}")

    if not env_file.exists() and not env_test_file.exists():
        logger.warning("  Some tests may fail without API keys")

    # Log configuration (without exposing keys)
    logger.info("Environment Configuration:")
    logger.info(f"  - FRED_API_KEY: {'✓ Set' if os.getenv('FRED_API_KEY') else '✗ Not set'}")
    logger.info(f"  - NEWSAPI_API_KEY: {'✓ Set' if os.getenv('NEWSAPI_API_KEY') else '✗ Not set'}")
    logger.info(f"  - CENSUS_API_KEY: {'✓ Set' if os.getenv('CENSUS_API_KEY') else '✗ Not set'}")
    logger.info(f"  - CONGRESS_API_KEY: {'✓ Set' if os.getenv('CONGRESS_API_KEY') else '✗ Not set'}")
    logger.info(f"  - OPENSTATES_API_KEY: {'✓ Set' if os.getenv('OPENSTATES_API_KEY') else '✗ Not set'}")
    logger.info(f"  - ALPHAVANTAGE_API_KEY: {'✓ Set' if os.getenv('ALPHAVANTAGE_API_KEY') else '✗ Not set'}")
    logger.info(f"  - EXCHANGERATE_API_KEY: {'✓ Set' if os.getenv('EXCHANGERATE_API_KEY') else '✗ Not set'}")
    logger.info(f"  - OPENWEATHERMAP_API_KEY: {'✓ Set' if os.getenv('OPENWEATHERMAP_API_KEY') else '✗ Not set'}")
    logger.info(f"  - GITHUB_API_KEY: {'✓ Set' if os.getenv('GITHUB_API_KEY') else '✗ Not set'}")
    logger.info(f"  - CORE_API_KEY: {'✓ Set' if os.getenv('CORE_API_KEY') else '✗ Not set'}")
    logger.info(f"  - USPTO_API_KEY: {'✓ Set' if os.getenv('USPTO_API_KEY') else '✗ Not set'}")
    logger.info(f"  - SECEDGAR_USER_AGENT: {'✓ Set' if os.getenv('SECEDGAR_USER_AGENT') else '✗ Not set'}")
    logger.info(f"  - OPENCORPORATES_API_KEY: {'✓ Set' if os.getenv('OPENCORPORATES_API_KEY') else '✗ Not set'}")
    logger.info(f"  - COURTLISTENER_API_KEY: {'✓ Set' if os.getenv('COURTLISTENER_API_KEY') else '✗ Not set'}")
    logger.info(f"  - DEBUG_MODE: {os.getenv('DEBUG_MODE', 'false')}")
    logger.info(f"  - VERBOSE_API_CALLS: {os.getenv('VERBOSE_API_CALLS', 'false')}")


@pytest.fixture(scope="session")
def api_keys() -> Dict[str, str]:
    """Provide API keys for tests"""
    return {
        'fred_api_key': os.getenv('FRED_API_KEY'),
        'newsapi_api_key': os.getenv('NEWSAPI_API_KEY'),
        'census_api_key': os.getenv('CENSUS_API_KEY'),
        'congress_api_key': os.getenv('CONGRESS_API_KEY'),
        'alphavantage_api_key': os.getenv('ALPHAVANTAGE_API_KEY'),
        'github_api_key': os.getenv('GITHUB_API_KEY'),
    }


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Provide test configuration"""
    return {
        'enable_fallback': True,
        'enable_query_enhancement': True,
        'enable_data_fusion': True,
        'default_timeout': int(os.getenv('API_REQUEST_TIMEOUT', '30')),
        'max_retries': 3,
        'cache_ttl': int(os.getenv('CACHE_TTL', '300')),
    }


@pytest.fixture
def fred_config(api_keys) -> Dict[str, Any]:
    """Configuration for FRED provider"""
    return {
        'api_key': api_keys['fred_api_key'],
        'timeout': int(os.getenv('FRED_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('FRED_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('FRED_MAX_BURST', '20')),
    }


@pytest.fixture
def newsapi_config(api_keys) -> Dict[str, Any]:
    """Configuration for News API provider"""
    return {
        'api_key': api_keys['newsapi_api_key'],
        'timeout': int(os.getenv('NEWSAPI_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('NEWSAPI_RATE_LIMIT', '5')),
        'max_burst': int(os.getenv('NEWSAPI_MAX_BURST', '10')),
    }


@pytest.fixture
def census_config(api_keys) -> Dict[str, Any]:
    """Configuration for Census provider"""
    return {
        'api_key': api_keys['census_api_key'],
        'timeout': int(os.getenv('CENSUS_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('CENSUS_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('CENSUS_MAX_BURST', '20')),
    }


@pytest.fixture
def congress_config(api_keys) -> Dict[str, Any]:
    """Configuration for Congress provider"""
    return {
        'api_key': api_keys['congress_api_key'],
        'timeout': int(os.getenv('CONGRESS_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('CONGRESS_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('CONGRESS_MAX_BURST', '20')),
    }


@pytest.fixture
def openstates_config() -> Dict[str, Any]:
    """Configuration for OpenStates provider"""
    return {
        'api_key': os.getenv('OPENSTATES_API_KEY'),
        'timeout': int(os.getenv('OPENSTATES_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('OPENSTATES_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('OPENSTATES_MAX_BURST', '20')),
    }


@pytest.fixture
def worldbank_config() -> Dict[str, Any]:
    """Configuration for World Bank provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('WORLDBANK_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('WORLDBANK_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('WORLDBANK_MAX_BURST', '20')),
    }


@pytest.fixture
def alphavantage_config(api_keys) -> Dict[str, Any]:
    """Configuration for Alpha Vantage provider"""
    return {
        'api_key': api_keys['alphavantage_api_key'],
        'timeout': int(os.getenv('ALPHAVANTAGE_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('ALPHAVANTAGE_RATE_LIMIT', '5')),
        'max_burst': int(os.getenv('ALPHAVANTAGE_MAX_BURST', '10')),
    }


@pytest.fixture
def restcountries_config() -> Dict[str, Any]:
    """Configuration for REST Countries provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('RESTCOUNTRIES_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('RESTCOUNTRIES_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('RESTCOUNTRIES_MAX_BURST', '20')),
    }


@pytest.fixture
def exchangerate_config(api_keys) -> Dict[str, Any]:
    """Configuration for ExchangeRate-API provider (API key optional)"""
    return {
        'api_key': os.getenv('EXCHANGERATE_API_KEY'),  # Optional - free tier works without key
        'timeout': int(os.getenv('EXCHANGERATE_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('EXCHANGERATE_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('EXCHANGERATE_MAX_BURST', '20')),
    }


@pytest.fixture
def openlibrary_config() -> Dict[str, Any]:
    """Configuration for Open Library provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('OPENLIBRARY_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('OPENLIBRARY_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('OPENLIBRARY_MAX_BURST', '20')),
    }


@pytest.fixture
def coingecko_config() -> Dict[str, Any]:
    """Configuration for CoinGecko provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('COINGECKO_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('COINGECKO_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('COINGECKO_MAX_BURST', '20')),
    }


@pytest.fixture
def openweathermap_config() -> Dict[str, Any]:
    """Configuration for OpenWeatherMap provider"""
    return {
        'api_key': os.getenv('OPENWEATHERMAP_API_KEY'),
        'timeout': int(os.getenv('OPENWEATHERMAP_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('OPENWEATHERMAP_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('OPENWEATHERMAP_MAX_BURST', '20')),
    }


@pytest.fixture
def wikipedia_config() -> Dict[str, Any]:
    """Configuration for Wikipedia provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('WIKIPEDIA_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('WIKIPEDIA_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('WIKIPEDIA_MAX_BURST', '20')),
    }


@pytest.fixture
def github_config(api_keys) -> Dict[str, Any]:
    """Configuration for GitHub provider (API key optional but recommended)"""
    return {
        'api_key': api_keys['github_api_key'],
        'timeout': int(os.getenv('GITHUB_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('GITHUB_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('GITHUB_MAX_BURST', '20')),
    }


@pytest.fixture
def arxiv_config() -> Dict[str, Any]:
    """Configuration for arXiv provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('ARXIV_TIMEOUT', '30')),
        'rate_limit': float(os.getenv('ARXIV_RATE_LIMIT', '0.33')),  # ~3 second delays (1/3 req/s)
        'max_burst': int(os.getenv('ARXIV_MAX_BURST', '2')),
    }


@pytest.fixture
def pubmed_config() -> Dict[str, Any]:
    """Configuration for PubMed provider (API key optional but recommended)"""
    return {
        'api_key': os.getenv('PUBMED_API_KEY'),  # Optional - improves rate limits
        'timeout': int(os.getenv('PUBMED_TIMEOUT', '30')),
        'rate_limit': float(os.getenv('PUBMED_RATE_LIMIT', '3')),  # 3 req/s without key, 10 with key
        'max_burst': int(os.getenv('PUBMED_MAX_BURST', '5')),
    }


@pytest.fixture
def crossref_config() -> Dict[str, Any]:
    """Configuration for CrossRef provider (no API key needed)"""
    return {
        'mailto': os.getenv('CROSSREF_MAILTO', 'iretbl@gmail.com'),  # For polite pool access
        'timeout': int(os.getenv('CROSSREF_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('CROSSREF_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('CROSSREF_MAX_BURST', '20')),
    }


@pytest.fixture
def semanticscholar_config() -> Dict[str, Any]:
    """Configuration for Semantic Scholar provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('SEMANTICSCHOLAR_TIMEOUT', '30')),
        'rate_limit': float(os.getenv('SEMANTICSCHOLAR_RATE_LIMIT', '1')),  # 1 req/s recommended
        'max_burst': int(os.getenv('SEMANTICSCHOLAR_MAX_BURST', '5')),
    }


@pytest.fixture
def core_config() -> Dict[str, Any]:
    """Configuration for CORE provider"""
    return {
        'api_key': os.getenv('CORE_API_KEY'),
        'timeout': int(os.getenv('CORE_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('CORE_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('CORE_MAX_BURST', '20')),
    }


@pytest.fixture
def uspto_config() -> Dict[str, Any]:
    """Configuration for USPTO provider"""
    return {
        'api_key': os.getenv('USPTO_API_KEY'),
        'timeout': int(os.getenv('USPTO_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('USPTO_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('USPTO_MAX_BURST', '20')),
    }


@pytest.fixture
def secedgar_config() -> Dict[str, Any]:
    """Configuration for SEC EDGAR provider (no API key needed, but User-Agent required)"""
    return {
        'user_agent': os.getenv('SECEDGAR_USER_AGENT', 'APISourceTool test@example.com'),
        'timeout': int(os.getenv('SECEDGAR_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('SECEDGAR_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('SECEDGAR_MAX_BURST', '20')),
    }


@pytest.fixture
def stackexchange_config() -> Dict[str, Any]:
    """Configuration for Stack Exchange provider (API key optional but recommended)"""
    return {
        'api_key': os.getenv('STACKEXCHANGE_API_KEY'),
        'timeout': int(os.getenv('STACKEXCHANGE_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('STACKEXCHANGE_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('STACKEXCHANGE_MAX_BURST', '20')),
    }


@pytest.fixture
def hackernews_config() -> Dict[str, Any]:
    """Configuration for Hacker News provider (no API key needed)"""
    return {
        'timeout': int(os.getenv('HACKERNEWS_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('HACKERNEWS_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('HACKERNEWS_MAX_BURST', '20')),
    }


@pytest.fixture
def opencorporates_config() -> Dict[str, Any]:
    """Configuration for OpenCorporates provider"""
    return {
        'api_key': os.getenv('OPENCORPORATES_API_KEY'),
        'timeout': int(os.getenv('OPENCORPORATES_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('OPENCORPORATES_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('OPENCORPORATES_MAX_BURST', '20')),
    }


@pytest.fixture
def courtlistener_config() -> Dict[str, Any]:
    """Configuration for CourtListener provider"""
    return {
        'api_key': os.getenv('COURTLISTENER_API_KEY'),
        'timeout': int(os.getenv('COURTLISTENER_TIMEOUT', '30')),
        'rate_limit': int(os.getenv('COURTLISTENER_RATE_LIMIT', '10')),
        'max_burst': int(os.getenv('COURTLISTENER_MAX_BURST', '20')),
    }


@pytest.fixture
def skip_if_no_api_key():
    """Skip test if required API keys are not available"""
    def _skip_if_no_key(provider: str):
        key_map = {
            'fred': 'FRED_API_KEY',
            'newsapi': 'NEWSAPI_API_KEY',
            'census': 'CENSUS_API_KEY',
            'congress': 'CONGRESS_API_KEY',
            'alphavantage': 'ALPHAVANTAGE_API_KEY',
            'openweathermap': 'OPENWEATHERMAP_API_KEY',
            'github': 'GITHUB_API_KEY',
            'core': 'CORE_API_KEY',
            'uspto': 'USPTO_API_KEY',
            'opencorporates': 'OPENCORPORATES_API_KEY',
            'courtlistener': 'COURTLISTENER_API_KEY',
        }

        env_var = key_map.get(provider.lower())
        if env_var and not os.getenv(env_var):
            pytest.skip(f"Skipping test: {env_var} not set")

    return _skip_if_no_key


@pytest.fixture
def debug_output():
    """Helper for debug output in tests"""
    def _print_debug(title: str, data: Any, indent: int = 0):
        """Print formatted debug output"""
        prefix = "  " * indent
        print(f"\n{prefix}{'=' * 60}")
        print(f"{prefix}{title}")
        print(f"{prefix}{'=' * 60}")
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)) and len(str(value)) > 100:
                    print(f"{prefix}  {key}: {type(value).__name__} (length: {len(value)})")
                else:
                    print(f"{prefix}  {key}: {value}")
        elif isinstance(data, list):
            print(f"{prefix}  Items: {len(data)}")
            for i, item in enumerate(data[:3]):  # Show first 3 items
                print(f"{prefix}  [{i}]: {item}")
            if len(data) > 3:
                print(f"{prefix}  ... and {len(data) - 3} more items")
        else:
            print(f"{prefix}  {data}")
        
        print(f"{prefix}{'=' * 60}\n")
    
    return _print_debug


@pytest.fixture
def assert_valid_response():
    """Helper to validate API response structure"""
    def _validate(response: Dict[str, Any], operation: str = None):
        """Validate response has required fields"""
        assert isinstance(response, dict), "Response must be a dictionary"

        # APISourceTool returns format: {'provider': ..., 'operation': ..., 'data': ...}
        # OR for search: {'results': ..., 'metadata': ..., 'providers_queried': ...}

        if 'results' in response:
            # Search response format
            assert 'metadata' in response, "Search response must have 'metadata' field"
            assert 'providers_queried' in response, "Search response must have 'providers_queried' field"
        else:
            # Query response format
            assert 'provider' in response, "Response must have 'provider' field"
            assert 'operation' in response, "Response must have 'operation' field"
            assert 'data' in response, "Response must have 'data' field"

            if operation:
                assert response['operation'] == operation, f"Expected operation '{operation}', got '{response['operation']}'"

        return True

    return _validate


@pytest.fixture
def measure_performance():
    """Helper to measure test performance"""
    import time
    
    class PerformanceMeasure:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.duration
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        def print_result(self, operation: str):
            if self.duration:
                print(f"\n⏱  {operation} took {self.duration:.3f} seconds")
    
    return PerformanceMeasure()


@pytest.fixture(autouse=True)
def test_logger(request):
    """Log test execution"""
    test_name = request.node.name
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Starting test: {test_name}")
    logger.info(f"{'=' * 80}")
    
    yield
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"Completed test: {test_name}")
    logger.info(f"{'=' * 80}\n")

