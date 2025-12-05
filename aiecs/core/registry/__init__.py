"""
Service Registry Module

Provides service registration and discovery for AIECS.
This is a core infrastructure module with no dependencies on other AIECS modules.

Usage:
    from aiecs.core.registry import register_ai_service, get_ai_service

    @register_ai_service("execute", "openai")
    class OpenAIExecuteService:
        pass

    service_cls = get_ai_service("execute", "openai")
"""

from .service_registry import (
    AI_SERVICE_REGISTRY,
    register_ai_service,
    get_ai_service,
    list_registered_services,
    clear_registry,
)

__all__ = [
    "AI_SERVICE_REGISTRY",
    "register_ai_service",
    "get_ai_service",
    "list_registered_services",
    "clear_registry",
]
