"""Configuration module

Contains application configuration and service registry.
"""

from .config import Settings, get_settings, validate_required_settings
from .tool_config import ToolConfigLoader, get_tool_config_loader
from .skills_config import (
    SkillsConfig,
    get_skills_config,
    validate_skills_config,
    SKILL_DIRECTORIES_ENV,
    DEFAULT_SKILL_DIRECTORY,
)

# Re-export registry functions from core.registry for backward compatibility
# The registry has been moved to aiecs.core.registry to prevent circular imports
from ..core.registry import (
    register_ai_service,
    get_ai_service,
    AI_SERVICE_REGISTRY,
    list_registered_services,
    clear_registry,
)

__all__ = [
    "Settings",
    "get_settings",
    "validate_required_settings",
    "register_ai_service",  # Re-exported from core.registry
    "get_ai_service",  # Re-exported from core.registry
    "AI_SERVICE_REGISTRY",  # Re-exported from core.registry
    "list_registered_services",  # Re-exported from core.registry
    "clear_registry",  # Re-exported from core.registry
    "ToolConfigLoader",
    "get_tool_config_loader",
    # Skills configuration
    "SkillsConfig",
    "get_skills_config",
    "validate_skills_config",
    "SKILL_DIRECTORIES_ENV",
    "DEFAULT_SKILL_DIRECTORY",
]
