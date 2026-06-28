"""
Unit tests for dispatch helpers and payload builders (H0-04).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.hooks.payload import (
    build_pre_tool_use_payload,
    build_user_prompt_submit_payload,
    redact_context_keys,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult


@pytest.mark.unit
class TestHookPayload:
    def test_context_keys_redaction(self) -> None:
        keys = redact_context_keys(
            {
                "user_id": "u1",
                "api_key": "secret",
                "_internal": "x",
                "refresh_token": "t",
            }
        )
        assert keys == ["user_id"]

    def test_context_keys_allowlist_override(self) -> None:
        keys = redact_context_keys(
            {
                "hook_context_keys_allowlist": ["api_key"],
                "api_key": "secret",
                "user_id": "u1",
            }
        )
        assert keys == ["api_key"]

    def test_h5_payload_shape(self) -> None:
        payload = build_user_prompt_submit_payload(
            prompt="hello",
            agent_id="agent-1",
            task_id="task-1",
            session_id=None,
            context={"user_id": "u1", "api_key": "secret"},
        )
        assert payload["prompt"] == "hello"
        assert payload["context_keys"] == ["user_id"]

    def test_h1_tool_input_included_verbatim_no_redaction(self) -> None:
        """Documents CC-style contract: tool hooks receive full args (see HOOKS.md §5.2)."""
        secret_input = {"path": "/tmp/x", "api_key": "sk-live-secret", "token": "bearer-xyz"}
        payload = build_pre_tool_use_payload(
            tool_name="write_file",
            tool_input=secret_input,
            tool_call_id="call_1",
            iteration=0,
        )
        assert payload["tool_input"] == secret_input
        assert payload["tool_input"]["api_key"] == "sk-live-secret"

    def test_aggregated_empty(self) -> None:
        result = AggregatedHookResult.empty()
        assert result.blocked is False
        assert result.reason == ""
