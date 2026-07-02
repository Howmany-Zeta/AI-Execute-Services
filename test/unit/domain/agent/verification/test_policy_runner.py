"""
Unit tests for verification_policy (A-2).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.exceptions import VerificationExhausted
from aiecs.domain.agent.verification.gates.registry import build_gate_registry_from_config
from aiecs.domain.agent.verification.policy_models import VerificationPolicy, WhenToVerify, resolve_verification_policy
from aiecs.domain.agent.verification.policy_runner import (
    _VERIFIED_KEY,
    resolve_registered_verifiers,
    run_gvr_pre_exit,
    run_stop_hook_with_policy_fallback,
    run_verification_policy,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestVerificationPolicyModel:
    def test_resolve_from_dict(self) -> None:
        policy = resolve_verification_policy({"enabled": True, "registered_verifiers": ["spec_gate"]})
        assert policy is not None
        assert policy.enabled is True
        assert policy.registered_verifiers == ["spec_gate"]

    def test_effective_skip_threshold_by_kind(self) -> None:
        policy = VerificationPolicy(skip_threshold=85.0, skip_threshold_by_kind={"factual": 90.0})
        assert policy.effective_skip_threshold("factual") == 90.0
        assert policy.effective_skip_threshold(None) == 85.0

    def test_when_to_verify_gating(self) -> None:
        on_stop = VerificationPolicy(enabled=True, when_to_verify=WhenToVerify.ON_STOP)
        assert on_stop.should_run_for_trigger("on_stop") is True
        assert on_stop.should_run_for_trigger("on_task_completed") is False

        never = VerificationPolicy(enabled=True, when_to_verify=WhenToVerify.NEVER)
        assert never.should_run_for_trigger("on_task_completed") is False
        assert never.should_run_for_trigger("on_stop") is False


@pytest.mark.unit
class TestResolveRegisteredVerifiers:
    def test_unknown_verifier_id_fails_fast(self) -> None:
        with pytest.raises(ValueError, match="Unknown registered_verifiers"):
            resolve_registered_verifiers(["unknown_verifier"], [])

    def test_gate_ids_do_not_require_llm_verifiers(self) -> None:
        resolved, _ = resolve_registered_verifiers(["spec_gate"], [])
        assert resolved == []


@pytest.mark.unit
class TestRunVerificationPolicy:
    @pytest.mark.asyncio
    async def test_blocking_false_records_verdict_without_refine(self) -> None:
        messages = [LLMMessage(role="user", content="task")]
        policy = VerificationPolicy(
            enabled=True,
            blocking=False,
            registered_verifiers=["spec_gate"],
        )
        plugin_state: dict = {}
        result = await run_verification_policy(
            policy=policy,
            agent_verifiers=[],
            messages=messages,
            loop_result={"output": "plain text without structure"},
            goal=None,
            plugin_state=plugin_state,
            trigger="on_task_completed",
            iteration=0,
        )
        assert result.continued_loop is False
        assert result.verdict.passed is False
        assert len(messages) == 1
        events = plugin_state.get("gvr.verification_events", [])
        assert any(e.get("event") == "non_blocking_fail" for e in events)

    @pytest.mark.asyncio
    async def test_max_refines_raises_verification_exhausted(self) -> None:
        policy = VerificationPolicy(
            enabled=True,
            blocking=True,
            max_refines_per_goal=0,
            registered_verifiers=["spec_gate"],
        )
        plugin_state: dict = {}
        with pytest.raises(VerificationExhausted):
            await run_verification_policy(
                policy=policy,
                agent_verifiers=[],
                messages=[LLMMessage(role="user", content="task")],
                loop_result={"output": "plain text"},
                goal={"goal_id": "g1"},
                plugin_state=plugin_state,
                trigger="on_task_completed",
                iteration=0,
            )

    @pytest.mark.asyncio
    async def test_skip_llm_when_gate_passes_threshold(self) -> None:
        policy = VerificationPolicy(
            enabled=True,
            registered_verifiers=["spec_gate"],
            skip_threshold=85.0,
        )
        plugin_state: dict = {}
        result = await run_verification_policy(
            policy=policy,
            agent_verifiers=[],
            messages=[LLMMessage(role="user", content="task")],
            loop_result={"output": "GIVEN x\nWHEN y\nTHEN z"},
            goal=None,
            plugin_state=plugin_state,
            trigger="on_task_completed",
            iteration=0,
        )
        assert result.skipped_llm is True
        assert result.verdict.passed is True
        events = plugin_state.get("gvr.verification_events", [])
        assert any(e.get("event") == "skip_llm" for e in events)

    @pytest.mark.asyncio
    async def test_dedupe_checkpoints_json_serializable_list(self) -> None:
        import json

        policy = VerificationPolicy(enabled=True, registered_verifiers=["spec_gate"])
        plugin_state: dict = {}
        loop_result = {"output": "plain text without structure"}
        messages = [LLMMessage(role="user", content="task")]

        first = await run_verification_policy(
            policy=policy,
            agent_verifiers=[],
            messages=messages,
            loop_result=loop_result,
            goal={"goal_id": "g1"},
            plugin_state=plugin_state,
            trigger="on_task_completed",
            iteration=0,
        )
        second = await run_verification_policy(
            policy=policy,
            agent_verifiers=[],
            messages=messages,
            loop_result=loop_result,
            goal={"goal_id": "g1"},
            plugin_state=plugin_state,
            trigger="on_task_completed",
            iteration=0,
        )

        checkpoints = plugin_state[_VERIFIED_KEY]
        assert isinstance(checkpoints, list)
        json.dumps(plugin_state)
        assert first.continued_loop is True
        assert second.verdict.kind == "NA"
        assert any(e.get("event") == "dedupe_skip" for e in plugin_state["gvr.verification_events"])

    @pytest.mark.asyncio
    async def test_legacy_set_checkpoints_migrated_to_list(self) -> None:
        import json

        policy = VerificationPolicy(enabled=True, registered_verifiers=["spec_gate"])
        plugin_state: dict = {_VERIFIED_KEY: {"none:0:on_task_completed"}}
        result = await run_verification_policy(
            policy=policy,
            agent_verifiers=[],
            messages=[LLMMessage(role="user", content="task")],
            loop_result={"output": "plain text"},
            goal=None,
            plugin_state=plugin_state,
            trigger="on_task_completed",
            iteration=0,
        )

        assert isinstance(plugin_state[_VERIFIED_KEY], list)
        json.dumps(plugin_state)
        assert result.verdict.kind == "NA"
        assert any(e.get("event") == "dedupe_skip" for e in plugin_state["gvr.verification_events"])


@pytest.mark.unit
class TestRunGvrPreExit:
    @pytest.mark.asyncio
    async def test_policy_off_delegates_to_a8_fallback(self) -> None:
        agent = MagicMock()
        agent._config.verification_policy = None
        agent._gate_registry = MagicMock()
        agent._gate_registry.gate_ids = ["spec_gate"]
        agent._verifiers = []
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}
        messages = [LLMMessage(role="user", content="task")]
        loop_result = {"output": "bad"}

        with patch(
            "aiecs.domain.agent.verification.policy_runner.run_pre_exit_gvr_check",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_a8:
            continued = await run_gvr_pre_exit(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=loop_result,
                trigger="on_task_completed",
                iteration=0,
            )
        assert continued is True
        mock_a8.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_stop_policy_does_not_run_on_task_completed(self) -> None:
        agent = MagicMock()
        agent._config.verification_policy = VerificationPolicy(
            enabled=True,
            when_to_verify=WhenToVerify.ON_STOP,
            registered_verifiers=["spec_gate"],
        )
        agent._verifiers = []
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}

        with patch(
            "aiecs.domain.agent.verification.policy_runner.run_verification_policy",
            new_callable=AsyncMock,
        ) as mock_policy:
            with patch(
                "aiecs.domain.agent.verification.policy_runner.run_pre_exit_gvr_check",
                new_callable=AsyncMock,
                return_value=False,
            ):
                continued = await run_gvr_pre_exit(
                    agent=agent,
                    plugin_ctx=plugin_ctx,
                    messages=[LLMMessage(role="user", content="task")],
                    loop_result={"output": "bad"},
                    trigger="on_task_completed",
                    iteration=0,
                )
        assert continued is False
        mock_policy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_never_policy_skips_policy_run(self) -> None:
        agent = MagicMock()
        agent._config.verification_policy = VerificationPolicy(
            enabled=True,
            when_to_verify=WhenToVerify.NEVER,
            registered_verifiers=["spec_gate"],
        )
        agent._verifiers = []
        agent._current_goal_for_gvr = MagicMock(return_value=None)
        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}

        with patch(
            "aiecs.domain.agent.verification.policy_runner.run_verification_policy",
            new_callable=AsyncMock,
        ) as mock_policy:
            await run_gvr_pre_exit(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=[LLMMessage(role="user", content="task")],
                loop_result={"output": "bad"},
                trigger="on_stop",
                iteration=0,
            )
        mock_policy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_on_stop_gate_fallback_when_policy_disabled(self) -> None:
        """A-8 gate-only path runs on STOP when verification_policy is off."""
        agent = MagicMock()
        agent._config.verification_policy = None
        agent._config.gvr_gate_skip_threshold = 85.0
        agent._gate_registry = build_gate_registry_from_config(["spec_gate"])
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}
        messages = [LLMMessage(role="user", content="task")]

        with patch(
            "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
            new_callable=AsyncMock,
        ) as mock_task_hook:
            continued = await run_gvr_pre_exit(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result={"output": "unstructured draft"},
                trigger="on_stop",
                iteration=0,
            )

        assert continued is True
        assert len(messages) == 2
        mock_task_hook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stop_hook_runs_gate_fallback_before_stop_hook(self) -> None:
        agent = MagicMock()
        agent._config.verification_policy = None
        agent._config.gvr_gate_skip_threshold = 85.0
        agent._gate_registry = build_gate_registry_from_config(["spec_gate"])
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}
        messages = [LLMMessage(role="user", content="task")]

        hook_handler = AsyncMock(return_value=AggregatedHookResult.empty())

        continued = await run_stop_hook_with_policy_fallback(
            agent=agent,
            plugin_ctx=plugin_ctx,
            messages=messages,
            loop_result={"output": "unstructured draft"},
            iteration=0,
            hook_result_handler=hook_handler,
        )

        assert continued is True
        hook_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_on_stop_skips_gates_after_task_completed_ran_them(self) -> None:
        """Hybrid flow: task_completed gates must not re-run on on_stop (same iteration)."""
        agent = MagicMock()
        agent._config.verification_policy = None
        agent._config.gvr_gate_skip_threshold = 85.0
        registry = build_gate_registry_from_config(["spec_gate"])
        agent._gate_registry = registry
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}
        plugin_ctx.agent = agent
        plugin_ctx.task = {}
        messages = [LLMMessage(role="user", content="task")]

        good_output = {
            "output": "GIVEN context WHEN action THEN outcome",
            "final_response": "GIVEN context WHEN action THEN outcome",
        }
        fail_output = {"output": "unstructured draft"}

        with patch.object(registry, "run_all", wraps=registry.run_all) as mock_run_all:
            with patch(
                "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
                new_callable=AsyncMock,
                return_value=AggregatedHookResult.empty(),
            ):
                continued_tc = await run_gvr_pre_exit(
                    agent=agent,
                    plugin_ctx=plugin_ctx,
                    messages=messages,
                    loop_result=good_output,
                    trigger="on_task_completed",
                    iteration=0,
                )
                assert continued_tc is False
                assert mock_run_all.call_count == 1

                continued_stop = await run_gvr_pre_exit(
                    agent=agent,
                    plugin_ctx=plugin_ctx,
                    messages=messages,
                    loop_result=fail_output,
                    trigger="on_stop",
                    iteration=0,
                )
                assert continued_stop is False
                assert mock_run_all.call_count == 1
                assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_stop_hook_runs_when_gates_deduped_on_stop(self) -> None:
        agent = MagicMock()
        agent._config.verification_policy = None
        agent._config.gvr_gate_skip_threshold = 85.0
        registry = build_gate_registry_from_config(["spec_gate"])
        agent._gate_registry = registry
        agent._current_goal_for_gvr = MagicMock(return_value=None)

        plugin_ctx = MagicMock()
        plugin_ctx.context = {}
        plugin_ctx.plugin_state = {}
        plugin_ctx.agent = agent
        plugin_ctx.task = {}
        messages = [LLMMessage(role="user", content="task")]

        good_output = {
            "output": "GIVEN context WHEN action THEN outcome",
            "final_response": "GIVEN context WHEN action THEN outcome",
        }
        fail_output = {"output": "unstructured draft"}
        hook_handler = AsyncMock(return_value=AggregatedHookResult.empty())

        with patch(
            "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
            new_callable=AsyncMock,
            return_value=AggregatedHookResult.empty(),
        ):
            await run_gvr_pre_exit(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=good_output,
                trigger="on_task_completed",
                iteration=0,
            )
            continued = await run_stop_hook_with_policy_fallback(
                agent=agent,
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=fail_output,
                iteration=0,
                hook_result_handler=hook_handler,
            )

        assert continued is False
        hook_handler.assert_awaited_once()
        assert len(messages) == 1
