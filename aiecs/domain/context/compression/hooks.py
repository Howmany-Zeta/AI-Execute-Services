# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""O6: PRE_COMPACT / POST_COMPACT hook registry and executor."""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from aiecs.domain.context.compression.types import (
    PostCompactContext,
    PostCompactHook,
    PreCompactContext,
    PreCompactHook,
    PreCompactResult,
)


class HookEvent(str, Enum):
    """Compact hook event names (host registers against these)."""

    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"


class HookRegistry:
    """Register pre/post compact hooks for a session or host adapter."""

    def __init__(self) -> None:
        self._pre_hooks: list[PreCompactHook] = []
        self._post_hooks: list[PostCompactHook] = []

    @property
    def pre_hooks(self) -> tuple[PreCompactHook, ...]:
        return tuple(self._pre_hooks)

    @property
    def post_hooks(self) -> tuple[PostCompactHook, ...]:
        return tuple(self._post_hooks)

    def register(self, event: HookEvent, hook: PreCompactHook | PostCompactHook) -> None:
        if event is HookEvent.PRE_COMPACT:
            self.register_pre(hook)  # type: ignore[arg-type]
        elif event is HookEvent.POST_COMPACT:
            self.register_post(hook)  # type: ignore[arg-type]
        else:
            raise ValueError(f"Unsupported hook event: {event!r}")

    def register_pre(self, hook: PreCompactHook) -> None:
        self._pre_hooks.append(hook)

    def register_post(self, hook: PostCompactHook) -> None:
        self._post_hooks.append(hook)

    def clear(self) -> None:
        self._pre_hooks.clear()
        self._post_hooks.clear()


class HookExecutor:
    """Run registered compact hooks; merges block/instructions from pre hooks."""

    def __init__(self, registry: HookRegistry | None = None) -> None:
        self.registry = registry or HookRegistry()

    async def execute_pre_compact(self, ctx: PreCompactContext) -> PreCompactResult:
        merged = PreCompactResult()
        for hook in self.registry.pre_hooks:
            result = await hook(ctx)
            if result.block:
                merged.block = True
            if result.append_instructions:
                if merged.append_instructions:
                    merged.append_instructions = f"{merged.append_instructions}\n{result.append_instructions}"
                else:
                    merged.append_instructions = result.append_instructions
        return merged

    async def execute_post_compact(self, ctx: PostCompactContext) -> None:
        for hook in self.registry.post_hooks:
            await hook(ctx)

    def extend_pre_hooks(self, hooks: Iterable[PreCompactHook]) -> None:
        for hook in hooks:
            self.registry.register_pre(hook)

    def extend_post_hooks(self, hooks: Iterable[PostCompactHook]) -> None:
        for hook in hooks:
            self.registry.register_post(hook)
