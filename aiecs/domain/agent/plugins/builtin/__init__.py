# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Built-in agent plugins (Skill, Memory, Tool).

Phase 2 fills business logic; stubs are metadata-only for Phase 1.
"""

from aiecs.domain.agent.plugins.builtin.memory_plugin import MemoryPlugin
from aiecs.domain.agent.plugins.builtin.skill_plugin import SkillPlugin
from aiecs.domain.agent.plugins.builtin.tool_plugin import ToolPlugin

__all__ = ["MemoryPlugin", "SkillPlugin", "ToolPlugin"]
