"""
API Source Tool

Unified interface for querying various external real-time API data sources including
economic indicators, news, public databases, and custom APIs with plugin architecture.

Features:
- Auto-discovery of API providers
- Unified query interface
- Rate limiting and caching
- Standardized response format
- Multi-provider search
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.api_sources import get_provider, list_providers, PROVIDER_REGISTRY

logger = logging.getLogger(__name__)


# Custom exceptions
class APISourceError(Exception):
    """Base exception for API Source Tool errors"""
    pass


class ProviderNotFoundError(APISourceError):
    """Raised when requested provider is not found"""
    pass


class APIRateLimitError(APISourceError):
    """Raised when API rate limit is exceeded"""
    pass


class APIAuthenticationError(APISourceError):
    """Raised when API authentication fails"""
    pass


@register_tool("apisource")
class APISourceTool(BaseTool):
    """
    Query external real-time API data sources including economic indicators, news, public databases, and custom APIs.
    
    Supports multiple data providers through a plugin architecture:
    - FRED: Federal Reserve Economic Data (US economic indicators)
    - World Bank: Global development indicators
    - News API: News articles and headlines
    - Census: US Census Bureau demographic and economic data
    
    Provides unified interface with automatic rate limiting, caching, and error handling.
    """
    
    # Configuration schema
    class Config(BaseModel):
        """Configuration for the API Source Tool"""
        model_config = ConfigDict(env_prefix="APISOURCE_TOOL_")
        
        cache_ttl: int = Field(
            default=300,
            description="Cache time-to-live in seconds for API responses"
        )
        default_timeout: int = Field(
            default=30,
            description="Default timeout in seconds for API requests"
        )
        max_retries: int = Field(
            default=3,
            description="Maximum number of retries for failed requests"
        )
        enable_rate_limiting: bool = Field(
            default=True,
            description="Whether to enable rate limiting for API requests"
        )
        fred_api_key: Optional[str] = Field(
            default=None,
            description="API key for Federal Reserve Economic Data (FRED)"
        )
        newsapi_api_key: Optional[str] = Field(
            default=None,
            description="API key for News API"
        )
        census_api_key: Optional[str] = Field(
            default=None,
            description="API key for US Census Bureau"
        )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API Source Tool with configuration.
        
        Args:
            config: Configuration dictionary with API keys and settings
        """
        super().__init__(config)
        
        # Parse configuration
        self.config = self.Config(**(config or {}))
        
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            self.logger.addHandler(handler)
        
        # Load providers (they auto-discover on import)
        self._providers = {}
        self._load_providers()
    
    def _load_providers(self):
        """Load and cache provider instances"""
        for provider_name in PROVIDER_REGISTRY.keys():
            try:
                # Create provider config from tool config
                provider_config = {
                    'timeout': self.config.default_timeout,
                }
                
                # Add provider-specific API key if available
                api_key_attr = f'{provider_name}_api_key'
                if hasattr(self.config, api_key_attr):
                    api_key = getattr(self.config, api_key_attr)
                    if api_key:
                        provider_config['api_key'] = api_key
                
                provider = get_provider(provider_name, provider_config)
                self._providers[provider_name] = provider
                self.logger.debug(f"Loaded provider: {provider_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load provider {provider_name}: {e}")
    
    # Schema definitions
    class QuerySchema(BaseModel):
        """Schema for query operation"""
        provider: str = Field(description="API provider name (e.g., 'fred', 'worldbank', 'newsapi', 'census')")
        operation: str = Field(description="Provider-specific operation to perform (e.g., 'get_series', 'search_indicators')")
        params: Dict[str, Any] = Field(description="Operation-specific parameters as key-value pairs")
    
    class ListProvidersSchema(BaseModel):
        """Schema for list_providers operation (no parameters required)"""
        pass
    
    class GetProviderInfoSchema(BaseModel):
        """Schema for get_provider_info operation"""
        provider: str = Field(description="API provider name to get information about")
    
    class SearchSchema(BaseModel):
        """Schema for search operation"""
        query: str = Field(description="Search query text to find across providers")
        providers: Optional[List[str]] = Field(
            default=None,
            description="List of provider names to search (searches all if not specified)"
        )
        limit: int = Field(
            default=10,
            description="Maximum number of results to return per provider"
        )
    
    def query(self, provider: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query a specific API provider with the given operation and parameters.
        
        Args:
            provider: API provider name (e.g., 'fred', 'worldbank', 'newsapi', 'census')
            operation: Provider-specific operation (e.g., 'get_series', 'search_indicators')
            params: Operation-specific parameters as dictionary
        
        Returns:
            Dictionary containing response data in standardized format with provider, operation, data, and metadata
        
        Raises:
            ProviderNotFoundError: If the specified provider is not available
            ValueError: If operation or parameters are invalid
            APISourceError: If the API request fails
        """
        if provider not in self._providers:
            available = ', '.join(self._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{provider}' not found. Available providers: {available}"
            )
        
        try:
            provider_instance = self._providers[provider]
            result = provider_instance.execute(operation, params)
            return result
        except Exception as e:
            self.logger.error(f"Error querying {provider}.{operation}: {e}")
            raise APISourceError(f"Failed to query {provider}: {str(e)}")
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all available API providers with their metadata.
        
        Returns:
            List of provider metadata dictionaries containing name, description, supported operations, and statistics
        """
        return list_providers()
    
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific API provider.
        
        Args:
            provider: API provider name to get information about
        
        Returns:
            Dictionary with provider metadata including name, description, operations, and configuration
        
        Raises:
            ProviderNotFoundError: If the specified provider is not found
        """
        if provider not in self._providers:
            available = ', '.join(self._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{provider}' not found. Available providers: {available}"
            )
        
        provider_instance = self._providers[provider]
        return provider_instance.get_metadata()
    
    def search(self, query: str, providers: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search across multiple API providers for the given query.
        
        Args:
            query: Search query text to find relevant data
            providers: List of provider names to search (searches all providers if not specified)
            limit: Maximum number of results to return per provider
        
        Returns:
            List of search results from all queried providers, each with provider name and matched data
        """
        if providers is None:
            providers = list(self._providers.keys())
        
        results = []
        
        for provider_name in providers:
            if provider_name not in self._providers:
                self.logger.warning(f"Skipping unknown provider: {provider_name}")
                continue
            
            try:
                provider_instance = self._providers[provider_name]
                
                # Try provider-specific search operations
                if provider_name == 'fred':
                    result = provider_instance.execute(
                        'search_series',
                        {'search_text': query, 'limit': limit}
                    )
                elif provider_name == 'worldbank':
                    result = provider_instance.execute(
                        'search_indicators',
                        {'search_text': query, 'limit': limit}
                    )
                elif provider_name == 'newsapi':
                    result = provider_instance.execute(
                        'search_everything',
                        {'q': query, 'page_size': limit}
                    )
                else:
                    # Skip providers without search capability
                    continue
                
                results.append(result)
                
            except Exception as e:
                self.logger.warning(f"Search failed for provider {provider_name}: {e}")
                # Continue with other providers
        
        return results


# Register the tool (done via decorator)

