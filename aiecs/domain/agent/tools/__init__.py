# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
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
