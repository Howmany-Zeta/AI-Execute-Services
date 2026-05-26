# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
MemoryPlugin stub.

Phase 2 fills business logic; do NOT import skills/mixin or memory/conversation.
"""

from typing import ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.models import PluginMetadata


class MemoryPlugin(BaseAgentPlugin):
    """Builtin memory plugin (§7.2). Hooks delegated to BaseAgentPlugin until Phase 2."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="memory",
        version="1.0.0",
        description="Conversation memory plugin",
        priority=80,
    )
