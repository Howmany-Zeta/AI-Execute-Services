"""
API Sources Package

Provider registry with auto-discovery for API data source providers.
Automatically discovers and registers all provider plugins in this directory.
"""

import importlib
import logging
import os
from typing import Dict, List, Optional, Type

from aiecs.tools.api_sources.base_provider import BaseAPIProvider

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
        raise ValueError(
            f"Provider '{name}' not found. "
            f"Available providers: {', '.join(PROVIDER_REGISTRY.keys())}"
        )
    
    # Return cached instance or create new one with config
    if config is None and name in PROVIDER_INSTANCES:
        return PROVIDER_INSTANCES[name]
    
    provider_instance = PROVIDER_REGISTRY[name](config)
    
    if config is None:
        PROVIDER_INSTANCES[name] = provider_instance
    
    return provider_instance


def list_providers() -> List[Dict[str, any]]:
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
            providers.append({
                'name': name,
                'description': 'Provider metadata unavailable',
                'operations': [],
                'error': str(e)
            })
    
    return providers


def discover_providers():
    """
    Auto-discover and register all providers in this directory.
    
    Scans for *_provider.py files and imports them to trigger registration.
    """
    current_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(current_dir):
        if filename.endswith('_provider.py') and not filename.startswith('__'):
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module to trigger provider registration
                importlib.import_module(f'aiecs.tools.api_sources.{module_name}')
                logger.debug(f"Discovered provider module: {module_name}")
            except Exception as e:
                logger.warning(f"Failed to import provider module {module_name}: {e}")


# Auto-discover providers on import
discover_providers()

# Export public API
__all__ = [
    'BaseAPIProvider',
    'register_provider',
    'get_provider',
    'list_providers',
    'PROVIDER_REGISTRY'
]

