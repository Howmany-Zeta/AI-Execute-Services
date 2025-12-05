"""
Service Registry - Core Infrastructure

This module provides service registration and discovery functionality.
It has ZERO dependencies on other AIECS modules to prevent circular imports.

This is part of the core infrastructure layer and should never import from
upper layers (domain, application, etc.).
"""

from typing import Dict, Tuple, Type, Any

# Global registry: maps (mode, service) -> service class
AI_SERVICE_REGISTRY: Dict[Tuple[str, str], Type[Any]] = {}


def register_ai_service(mode: str, service: str):
    """
    Decorator for registering a service class to the registry.

    Args:
        mode: Service mode (e.g., "execute", "analyze")
        service: Service name (e.g., "openai", "custom")

    Returns:
        Decorator function that registers the class

    Example:
        @register_ai_service("execute", "openai")
        class OpenAIExecuteService:
            pass
    """

    def decorator(cls: Type[Any]) -> Type[Any]:
        key = (mode, service)
        AI_SERVICE_REGISTRY[key] = cls
        return cls

    return decorator


def get_ai_service(mode: str, service: str) -> Type[Any]:
    """
    Retrieve a registered service class.

    Args:
        mode: Service mode
        service: Service name

    Returns:
        The registered service class

    Raises:
        ValueError: If no service is registered for the given mode and service

    Example:
        service_cls = get_ai_service("execute", "openai")
        service_instance = service_cls()
    """
    key = (mode, service)
    if key not in AI_SERVICE_REGISTRY:
        raise ValueError(f"No registered service for mode '{mode}', service '{service}'. " f"Available services: {list(AI_SERVICE_REGISTRY.keys())}")
    return AI_SERVICE_REGISTRY[key]


def list_registered_services() -> Dict[Tuple[str, str], Type[Any]]:
    """
    List all registered services.

    Returns:
        Dictionary mapping (mode, service) tuples to service classes

    Example:
        services = list_registered_services()
        for (mode, name), cls in services.items():
            print(f"{mode}/{name}: {cls.__name__}")
    """
    return AI_SERVICE_REGISTRY.copy()


def clear_registry() -> None:
    """
    Clear all registered services.

    Primarily used for testing purposes to reset the registry state
    between tests.

    Example:
        # In test setup or teardown
        clear_registry()
    """
    AI_SERVICE_REGISTRY.clear()
