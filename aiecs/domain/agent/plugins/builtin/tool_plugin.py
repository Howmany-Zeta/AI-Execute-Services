# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
ToolPlugin stub.

Phase 2 fills business logic; do NOT import skills/mixin or memory/conversation.
"""

from typing import ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.models import PluginMetadata


class ToolPlugin(BaseAgentPlugin):
    """Builtin tool plugin (§7.3). Hooks delegated to BaseAgentPlugin until Phase 2."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="tool",
        version="1.0.0",
        description="Tool schema and filtering plugin",
        priority=100,
    )
