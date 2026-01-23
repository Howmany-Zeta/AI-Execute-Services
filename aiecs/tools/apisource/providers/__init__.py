"""
API Providers Module

Contains all API provider implementations for the APISource tool.
"""

from aiecs.tools.apisource.providers.base import BaseAPIProvider, RateLimiter
from aiecs.tools.apisource.providers.fred import FREDProvider
from aiecs.tools.apisource.providers.worldbank import WorldBankProvider
from aiecs.tools.apisource.providers.newsapi import NewsAPIProvider
from aiecs.tools.apisource.providers.census import CensusProvider
from aiecs.tools.apisource.providers.alphavantage import AlphaVantageProvider
from aiecs.tools.apisource.providers.restcountries import RESTCountriesProvider
from aiecs.tools.apisource.providers.exchangerate import ExchangeRateProvider
from aiecs.tools.apisource.providers.openlibrary import OpenLibraryProvider
from aiecs.tools.apisource.providers.coingecko import CoinGeckoProvider
from aiecs.tools.apisource.providers.openweathermap import OpenWeatherMapProvider
from aiecs.tools.apisource.providers.wikipedia import WikipediaProvider
from aiecs.tools.apisource.providers.github import GitHubProvider
from aiecs.tools.apisource.providers.arxiv import ArxivProvider
from aiecs.tools.apisource.providers.pubmed import PubMedProvider
from aiecs.tools.apisource.providers.crossref import CrossRefProvider
from aiecs.tools.apisource.providers.semanticscholar import SemanticScholarProvider

import logging
from typing import Dict, List, Optional, Type, Any

logger = logging.getLogger(__name__)

# Global provider registry
PROVIDER_REGISTRY: Dict[str, Type[BaseAPIProvider]] = {}
PROVIDER_INSTANCES: Dict[str, BaseAPIProvider] = {}


def register_provider(provider_class: Type[BaseAPIProvider]):
    """
    Register a provider class.

    Args:
        provider_class: Provider class to register
    """
    # Instantiate to get name
    temp_instance = provider_class()
    provider_name = temp_instance.name

    PROVIDER_REGISTRY[provider_name] = provider_class
    logger.debug(f"Registered provider: {provider_name}")


def get_provider(name: str, config: Optional[Dict] = None) -> BaseAPIProvider:
    """
    Get a provider instance by name.

    Args:
        name: Provider name
        config: Optional configuration for the provider

    Returns:
        Provider instance

    Raises:
        ValueError: If provider is not registered
    """
    if name not in PROVIDER_REGISTRY:
        raise ValueError(f"Provider '{name}' not found. " f"Available providers: {', '.join(PROVIDER_REGISTRY.keys())}")

    # Return cached instance or create new one with config
    if config is None and name in PROVIDER_INSTANCES:
        return PROVIDER_INSTANCES[name]

    provider_instance = PROVIDER_REGISTRY[name](config)

    if config is None:
        PROVIDER_INSTANCES[name] = provider_instance

    return provider_instance


def list_providers() -> List[Dict[str, Any]]:
    """
    List all registered providers.

    Returns:
        List of provider metadata dictionaries
    """
    providers = []
    for name, provider_class in PROVIDER_REGISTRY.items():
        try:
            # Get or create instance to access metadata
            provider = get_provider(name)
            providers.append(provider.get_metadata())
        except Exception as e:
            logger.warning(f"Failed to get metadata for provider {name}: {e}")
            providers.append(
                {
                    "name": name,
                    "description": "Provider metadata unavailable",
                    "operations": [],
                    "error": str(e),
                }
            )

    return providers


# Auto-register all providers
register_provider(FREDProvider)
register_provider(WorldBankProvider)
register_provider(NewsAPIProvider)
register_provider(CensusProvider)
register_provider(AlphaVantageProvider)
register_provider(RESTCountriesProvider)
register_provider(ExchangeRateProvider)
register_provider(OpenLibraryProvider)
register_provider(CoinGeckoProvider)
register_provider(OpenWeatherMapProvider)
register_provider(WikipediaProvider)
register_provider(GitHubProvider)
register_provider(ArxivProvider)
register_provider(PubMedProvider)
register_provider(CrossRefProvider)
register_provider(SemanticScholarProvider)


__all__ = [
    "BaseAPIProvider",
    "RateLimiter",
    "FREDProvider",
    "WorldBankProvider",
    "NewsAPIProvider",
    "CensusProvider",
    "AlphaVantageProvider",
    "RESTCountriesProvider",
    "ExchangeRateProvider",
    "OpenLibraryProvider",
    "CoinGeckoProvider",
    "OpenWeatherMapProvider",
    "WikipediaProvider",
    "GitHubProvider",
    "ArxivProvider",
    "PubMedProvider",
    "CrossRefProvider",
    "SemanticScholarProvider",
    "register_provider",
    "get_provider",
    "list_providers",
    "PROVIDER_REGISTRY",
]
