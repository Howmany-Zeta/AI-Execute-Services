"""
Unit tests for AggregatedHookResult merge semantics (§5.1.3).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult


@pytest.mark.unit
class TestAggregatedHookResultMerge:
    def test_modified_output_last_non_empty_wins(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(hook_type="http", success=True, modified_output="first"),
                HookResult(hook_type="http", success=True, modified_output="second"),
            ]
        )
        assert result.modified_output == "second"

    def test_updated_mcp_output_last_non_empty_wins(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(hook_type="prompt", success=True, updated_mcp_output="a"),
                HookResult(hook_type="prompt", success=True, updated_mcp_output="b"),
            ]
        )
        assert result.updated_mcp_output == "b"

    def test_updated_input_merges_with_later_keys_winning(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(
                    hook_type="prompt",
                    success=True,
                    updated_input={"path": "/a", "mode": "read"},
                ),
                HookResult(
                    hook_type="prompt",
                    success=True,
                    updated_input={"path": "/b", "extra": True},
                ),
            ]
        )
        assert result.updated_input == {"path": "/b", "mode": "read", "extra": True}

    def test_permission_decision_last_hook_wins(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(hook_type="prompt", success=True, permission_decision="allow"),
                HookResult(hook_type="prompt", success=True, permission_decision="deny"),
            ]
        )
        assert result.permission_decision == "deny"

    def test_additional_context_last_hook_wins(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(hook_type="prompt", success=True, additional_context="first"),
                HookResult(hook_type="prompt", success=True, additional_context="second"),
            ]
        )
        assert result.additional_context == "second"

    def test_blocked_any_hook_blocks(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(hook_type="http", success=False, blocked=True, reason="policy"),
                HookResult(hook_type="http", success=True, blocked=False),
            ]
        )
        assert result.blocked is True
        assert result.reason == "policy"
