"""
Tool Integration

Tool schema generation and integration with AIECS tools.
Includes lightweight tool models for agent-level tool management
and a registry for managing tools created from skill scripts.
"""

from .schema_generator import (
    ToolSchemaGenerator,
    generate_tool_schema,
)
from .models import (
    Tool,
    ToolParameter,
    ToolValidationError,
)
from .registry import (
    SkillScriptRegistry,
    SkillScriptRegistryError,
)

__all__ = [
    # Schema generation
    "ToolSchemaGenerator",
    "generate_tool_schema",
    # Tool models
    "Tool",
    "ToolParameter",
    "ToolValidationError",
    # Skill script registry
    "SkillScriptRegistry",
    "SkillScriptRegistryError",
]
