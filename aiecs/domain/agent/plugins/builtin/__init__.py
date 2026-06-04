# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Built-in agent plugins (Skill, Memory, Tool, Knowledge, Temporal Memory, Collaboration).

Phase 2 fills business logic; stubs are metadata-only for Phase 1.
"""

from aiecs.domain.agent.plugins.builtin.collaboration_plugin import CollaborationPlugin
from aiecs.domain.agent.plugins.builtin.knowledge_plugin import KnowledgePlugin
from aiecs.domain.agent.plugins.builtin.memory_plugin import MemoryPlugin
from aiecs.domain.agent.plugins.builtin.skill_plugin import SkillPlugin
from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import TemporalMemoryPlugin
from aiecs.domain.agent.plugins.builtin.tool_plugin import ToolPlugin

__all__ = [
    "CollaborationPlugin",
    "KnowledgePlugin",
    "MemoryPlugin",
    "SkillPlugin",
    "TemporalMemoryPlugin",
    "ToolPlugin",
]
