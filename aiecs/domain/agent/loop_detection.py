# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Tool-loop stall detection signals (A-7)."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Optional

from pydantic import BaseModel, ConfigDict, Field


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ToolTriple:
    tool_name: str
    args_hash: str
    result_hash: str

    def as_dict(self) -> dict[str, str]:
        return {
            "tool_name": self.tool_name,
            "args_hash": self.args_hash,
            "result_hash": self.result_hash,
        }


@dataclass
class LoopSignal:
    """Read-only stall signal for host DECIDE (A-7)."""

    repeated_triple_count: int = 0
    last_triples: list[dict[str, str]] = field(default_factory=list)
    idle_iterations: int = 0
    effective_cycles: int = 0
    triggering_triple: Optional[ToolTriple] = None

    @classmethod
    def empty(cls) -> "LoopSignal":
        return cls()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "repeated_triple_count": self.repeated_triple_count,
            "last_triples": self.last_triples,
            "idle_iterations": self.idle_iterations,
            "effective_cycles": self.effective_cycles,
        }
        if self.triggering_triple is not None:
            payload["triggering_triple"] = self.triggering_triple.as_dict()
        return payload


class LoopDetectionConfig(BaseModel):
    """Engine loop detection configuration (A-7). Default off preserves rc4."""

    enabled: bool = False
    window_size: int = Field(default=20, ge=1)
    repeat_threshold: int = Field(default=3, ge=2)
    hook_on_detect: bool = False

    model_config = ConfigDict(extra="forbid")


def resolve_loop_detection_config(raw: Any) -> LoopDetectionConfig | None:
    if raw is None:
        return None
    if isinstance(raw, LoopDetectionConfig):
        return raw
    if isinstance(raw, dict):
        return LoopDetectionConfig.model_validate(raw)
    raise TypeError(f"Unsupported loop_detection type: {type(raw)!r}")


class LoopDetectionService:
    """Sliding-window tracker for repeated (tool, args, result) triples."""

    def __init__(self, config: LoopDetectionConfig | None = None) -> None:
        self._config = config or LoopDetectionConfig()
        self._window: Deque[tuple[str, str, str]] = deque(maxlen=self._config.window_size)
        self._counts: dict[tuple[str, str, str], int] = {}
        self._idle_iterations = 0
        self._last_signal = LoopSignal.empty()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def reset(self) -> None:
        self._window.clear()
        self._counts.clear()
        self._idle_iterations = 0
        self._last_signal = LoopSignal.empty()

    def get_signal(self) -> LoopSignal:
        return self._last_signal

    def record_iteration(self, *, had_tool_call: bool) -> None:
        if not self.enabled:
            return
        if had_tool_call:
            self._idle_iterations = 0
        else:
            self._idle_iterations += 1
        self._refresh_idle_signal()

    def record_tool_call(
        self,
        *,
        tool_name: str,
        args: Any,
        result: Any,
    ) -> Optional[LoopSignal]:
        if not self.enabled:
            return None

        key = (tool_name, _stable_hash(args), _stable_hash(result))
        if len(self._window) >= self._config.window_size:
            evicted = self._window.popleft()
            self._counts[evicted] -= 1
            if self._counts[evicted] <= 0:
                del self._counts[evicted]

        self._window.append(key)
        self._counts[key] = self._counts.get(key, 0) + 1
        count = self._counts[key]
        self._idle_iterations = 0

        triggering = ToolTriple(*key)
        last_triples = [ToolTriple(*entry).as_dict() for entry in list(self._window)[-5:]]
        effective_cycles = count // self._config.repeat_threshold if count >= self._config.repeat_threshold else 0

        self._last_signal = LoopSignal(
            repeated_triple_count=count,
            last_triples=last_triples,
            idle_iterations=self._idle_iterations,
            effective_cycles=effective_cycles,
            triggering_triple=triggering if count >= self._config.repeat_threshold else None,
        )

        if count >= self._config.repeat_threshold:
            return self._last_signal
        return None

    def _refresh_idle_signal(self) -> None:
        last_triples = [ToolTriple(*entry).as_dict() for entry in list(self._window)[-5:]]
        top_count = max(self._counts.values()) if self._counts else 0
        self._last_signal = LoopSignal(
            repeated_triple_count=top_count,
            last_triples=last_triples,
            idle_iterations=self._idle_iterations,
            effective_cycles=top_count // self._config.repeat_threshold if top_count >= self._config.repeat_threshold else 0,
        )


class LoopDetectionMixin:
    """Mixin exposing loop signals on agents with ``LoopDetectionService``."""

    _loop_detection: LoopDetectionService

    def get_loop_signals(self) -> LoopSignal:
        return self._loop_detection.get_signal()
