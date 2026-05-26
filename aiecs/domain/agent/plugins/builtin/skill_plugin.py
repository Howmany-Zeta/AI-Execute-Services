# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
SkillPlugin stub.

Phase 2 fills business logic; do NOT import skills/mixin or memory/conversation.
"""

from typing import ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.models import PluginMetadata


class SkillPlugin(BaseAgentPlugin):
    """Builtin skill plugin (§7.1). Hooks delegated to BaseAgentPlugin until Phase 2."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="skill",
        version="1.0.0",
        description="Skill context and attachment plugin",
        priority=90,
    )
