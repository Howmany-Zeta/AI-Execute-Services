"""Configuration module

Contains application configuration and service registry.
"""

from .config import Settings, get_settings
from .registry import register_ai_service, get_ai_service, AI_SERVICE_REGISTRY

__all__ = [
    "Settings",
    "get_settings",
    "register_ai_service",
    "get_ai_service",
    "AI_SERVICE_REGISTRY",
]
