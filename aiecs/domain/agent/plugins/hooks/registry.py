# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Agent hook registry (§5.1.2)."""

from __future__ import annotations

from collections import defaultdict

from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.schemas import HookDefinition


class AgentHookRegistry:
    """Store hooks grouped by event."""

    def __init__(self) -> None:
        self._hooks: dict[AgentHookEvent, list[HookDefinition]] = defaultdict(list)

    def register(self, event: AgentHookEvent, hook: HookDefinition) -> None:
        self._hooks[event].append(hook)

    def get_hooks(self, event: AgentHookEvent) -> list[HookDefinition]:
        """Return hooks for an event ordered by priority descending (§5.1.2)."""
        hooks = self._hooks.get(event, [])
        return sorted(hooks, key=lambda hook: -getattr(hook, "priority", 0))

    def has_hooks(self) -> bool:
        return any(self._hooks.values())

    def summary(self) -> str:
        lines: list[str] = []
        for event in AgentHookEvent:
            hooks = self.get_hooks(event)
            if not hooks:
                continue
            lines.append(f"{event.value}:")
            for hook in hooks:
                matcher = getattr(hook, "matcher", None)
                detail = getattr(hook, "command", None) or getattr(hook, "prompt", None) or getattr(hook, "url", None) or ""
                suffix = f" matcher={matcher}" if matcher else ""
                priority = getattr(hook, "priority", 0)
                if priority:
                    suffix += f" priority={priority}"
                lines.append(f"  - {hook.type}{suffix}: {detail}")
        return "\n".join(lines)
