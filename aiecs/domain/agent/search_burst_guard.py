# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Consecutive web_search burst detection (M-D.4)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_SEARCH_TOOL_NAMES = (
    "web_search",
    "search",
    "search_web",
)
DEFAULT_DEPTH_TOOL_NAMES = (
    "web_scrape",
    "scrape",
    "read_files",
    "read_file",
    "collect",
)

DEFAULT_BURST_REMINDER = (
    "[search_burst_guard] You have issued {count} consecutive web_search calls without "
    "web_scrape, read_files, or collect. Scrape must_scrape_urls or a top primary result "
    "before issuing another web_search."
)


@dataclass
class SearchBurstSignal:
    """Read-only burst signal for host DECIDE / hooks (M-D.4)."""

    consecutive_search_count: int = 0
    threshold: int = 3
    triggered: bool = False
    last_search_tool: Optional[str] = None
    last_search_operation: Optional[str] = None
    reminder: Optional[str] = None

    @classmethod
    def empty(cls) -> "SearchBurstSignal":
        return cls()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": "search_burst",
            "consecutive_search_count": self.consecutive_search_count,
            "threshold": self.threshold,
            "triggered": self.triggered,
        }
        if self.last_search_tool is not None:
            payload["last_search_tool"] = self.last_search_tool
        if self.last_search_operation is not None:
            payload["last_search_operation"] = self.last_search_operation
        if self.reminder is not None:
            payload["reminder"] = self.reminder
        return payload


class SearchBurstGuardConfig(BaseModel):
    """Search burst guard configuration (M-D.4). Default off preserves existing loops."""

    enabled: bool = False
    threshold: int = Field(default=3, ge=2)
    hook_on_detect: bool = False
    inject_reminder: bool = True
    search_tool_names: list[str] = Field(default_factory=lambda: list(DEFAULT_SEARCH_TOOL_NAMES))
    depth_tool_names: list[str] = Field(default_factory=lambda: list(DEFAULT_DEPTH_TOOL_NAMES))
    reminder_template: str = Field(default=DEFAULT_BURST_REMINDER)

    model_config = ConfigDict(extra="forbid")


def resolve_search_burst_guard_config(raw: Any) -> SearchBurstGuardConfig | None:
    env_enabled = os.getenv("AIECS_SEARCH_BURST_GUARD", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if raw is None:
        if env_enabled:
            return SearchBurstGuardConfig(enabled=True)
        return None

    if isinstance(raw, SearchBurstGuardConfig):
        cfg = raw
    elif isinstance(raw, dict):
        cfg = SearchBurstGuardConfig.model_validate(raw)
    else:
        raise TypeError(f"Unsupported search_burst_guard type: {type(raw)!r}")

    if env_enabled and not cfg.enabled:
        cfg = cfg.model_copy(update={"enabled": True})
    return cfg


def _normalize(name: str) -> str:
    return name.strip().lower()


def is_search_tool(
    tool_name: str,
    operation: str | None,
    config: SearchBurstGuardConfig,
) -> bool:
    names = {_normalize(tool_name)}
    if operation:
        names.add(_normalize(operation))

    configured = {_normalize(item) for item in config.search_tool_names}
    if names & configured:
        return True

    for ref in names:
        if ref.endswith("_search") or ref == "search" or ref.startswith("search_"):
            return True
    return False


def is_depth_tool(
    tool_name: str,
    operation: str | None,
    config: SearchBurstGuardConfig,
) -> bool:
    names = {_normalize(tool_name)}
    if operation:
        names.add(_normalize(operation))

    configured = {_normalize(item) for item in config.depth_tool_names}
    if names & configured:
        return True

    for ref in names:
        if "scrape" in ref or ref.startswith("read_file") or ref == "collect":
            return True
    return False


class SearchBurstGuardService:
    """Tracks consecutive search tool calls without intervening depth tools."""

    def __init__(self, config: SearchBurstGuardConfig | None = None) -> None:
        self._config = config or SearchBurstGuardConfig()
        self._consecutive_searches = 0
        self._last_signal = SearchBurstSignal.empty()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def reset(self) -> None:
        self._consecutive_searches = 0
        self._last_signal = SearchBurstSignal.empty()

    def get_signal(self) -> SearchBurstSignal:
        return self._last_signal

    def record_tool_call(
        self,
        *,
        tool_name: str,
        operation: str | None = None,
    ) -> Optional[SearchBurstSignal]:
        if not self.enabled:
            return None

        if is_depth_tool(tool_name, operation, self._config):
            self._consecutive_searches = 0
            self._last_signal = SearchBurstSignal(
                consecutive_search_count=0,
                threshold=self._config.threshold,
                triggered=False,
            )
            return None

        if not is_search_tool(tool_name, operation, self._config):
            return None

        self._consecutive_searches += 1
        triggered = self._consecutive_searches >= self._config.threshold
        reminder = None
        if triggered and self._config.inject_reminder:
            reminder = self._config.reminder_template.format(count=self._consecutive_searches)

        self._last_signal = SearchBurstSignal(
            consecutive_search_count=self._consecutive_searches,
            threshold=self._config.threshold,
            triggered=triggered,
            last_search_tool=tool_name,
            last_search_operation=operation,
            reminder=reminder,
        )

        if triggered:
            return self._last_signal
        return None


class SearchBurstGuardMixin:
    """Mixin exposing search burst signals on agents with ``SearchBurstGuardService``."""

    _search_burst_guard: SearchBurstGuardService

    def get_search_burst_signals(self) -> SearchBurstSignal:
        return self._search_burst_guard.get_signal()
