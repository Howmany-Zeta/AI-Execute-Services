"""
Unit tests for hook loader (H0-02).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.errors import PluginConfigErrorException
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.loader import (
    HookLoadOptions,
    hook_fingerprint,
    load_hooks_from_json,
    merge_hook_sources,
    normalize_event_key,
)
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import HttpHookDefinition

_FIXTURES = Path(__file__).resolve().parents[6] / "tests" / "fixtures" / "hooks"


@pytest.mark.unit
class TestHookLoader:
    def test_pascal_case_alias_maps_to_canonical_event(self) -> None:
        registry = AgentHookRegistry()
        load_hooks_from_json(
            {
                "hooks": {
                    "PreToolUse": [
                        {"type": "http", "url": "https://example.com/pre", "priority": 1}
                    ]
                }
            },
            registry,
        )
        hooks = registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)
        assert len(hooks) == 1
        assert hooks[0].url == "https://example.com/pre"

    def test_priority_descending_stable_tie_break(self) -> None:
        registry = AgentHookRegistry()
        load_hooks_from_json(
            {
                "hooks": {
                    "pre_tool_use": [
                        {"type": "http", "url": "https://example.com/a", "priority": 0},
                        {"type": "http", "url": "https://example.com/b", "priority": 10},
                        {"type": "http", "url": "https://example.com/c", "priority": 10},
                    ]
                }
            },
            registry,
        )
        urls = [hook.url for hook in registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)]
        assert urls == [
            "https://example.com/b",
            "https://example.com/c",
            "https://example.com/a",
        ]

    def test_merge_append_and_duplicate_fingerprint_dedupe(self) -> None:
        hook_a = {"type": "http", "url": "https://example.com/same", "matcher": "read_*"}
        registry = merge_hook_sources(
            [
                ("file-a", {"hooks": {"pre_tool_use": [hook_a]}}),
                ("file-b", {"hooks": {"pre_tool_use": [hook_a, hook_a]}}),
            ]
        )
        hooks = registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)
        assert len(hooks) == 1

    def test_invalid_type_fail_fast(self) -> None:
        registry = AgentHookRegistry()
        with pytest.raises(PluginConfigErrorException):
            load_hooks_from_json({"hooks": {"pre_tool_use": [{"type": "unknown"}]}}, registry)

    def test_command_requires_allow_command_hooks(self) -> None:
        registry = AgentHookRegistry()
        with pytest.raises(PluginConfigErrorException):
            load_hooks_from_json(
                {
                    "hooks": {
                        "pre_tool_use": [
                            {"type": "command", "command": ["python", "-c", "print('ok')"]}
                        ]
                    }
                },
                registry,
                options=HookLoadOptions(allow_command_hooks=False),
            )

    def test_notification_warn_not_registered(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = AgentHookRegistry()
        with caplog.at_level("WARNING"):
            event = normalize_event_key("Notification", options=HookLoadOptions())
        assert event is None
        load_hooks_from_json(
            {"hooks": {"notification": [{"type": "http", "url": "https://example.com/n"}]}},
            registry,
        )
        assert registry.get_hooks(AgentHookEvent.NOTIFICATION) == []

    def test_strict_cc_hooks_fail_fast(self) -> None:
        with pytest.raises(PluginConfigErrorException):
            normalize_event_key("ConfigChange", options=HookLoadOptions(strict_cc_hooks=True))

    def test_v2_permission_denied_alias_maps(self) -> None:
        event = normalize_event_key("PermissionDenied", options=HookLoadOptions())
        assert event == AgentHookEvent.PERMISSION_DENIED

    def test_load_sample_fixture(self) -> None:
        sample_path = _FIXTURES / "sample.json"
        registry = AgentHookRegistry()
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        load_hooks_from_json(data, registry)
        pre_hooks = registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)
        assert len(pre_hooks) >= 2
        assert pre_hooks[0].priority >= pre_hooks[-1].priority

    def test_hook_fingerprint_stable(self) -> None:
        hook = HttpHookDefinition(url="https://example.com/x", matcher="read_*")
        assert hook_fingerprint(hook) == ("http", "https://example.com/x", "read_*")

    def test_cc_wrapper_applies_outer_matcher_to_nested_hooks(self) -> None:
        registry = AgentHookRegistry()
        load_hooks_from_json(
            {
                "hooks": {
                    "pre_tool_use": {
                        "matcher": "write_*",
                        "hooks": [
                            {"type": "http", "url": "https://example.com/inherited"},
                            {
                                "type": "http",
                                "url": "https://example.com/explicit",
                                "matcher": "delete_*",
                            },
                        ],
                    }
                }
            },
            registry,
        )
        hooks = registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)
        assert len(hooks) == 2
        by_url = {hook.url: hook.matcher for hook in hooks}
        assert by_url["https://example.com/inherited"] == "write_*"
        assert by_url["https://example.com/explicit"] == "delete_*"
