# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""VerificationPolicy engine runner (A-2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Sequence, cast

from aiecs.domain.agent.exceptions import VerificationExhausted
from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.plugins.hooks.gvr_blocking import (
    format_blocking_user_message,
    inject_blocking_user_message,
    run_pre_exit_gvr_check,
)
from aiecs.domain.agent.verification.context_builder import build_verification_context
from aiecs.domain.agent.verification.gvr_checkpoints import gates_already_run, gates_dedupe_key, mark_gates_run
from aiecs.domain.agent.verification.criteria import normalize_acceptance_criteria
from aiecs.domain.agent.verification.gates.conversion import gate_aggregate_to_verdict
from aiecs.domain.agent.verification.gates.registry import BUILTIN_GATES, GateRegistry, build_gate_registry_from_config
from aiecs.domain.agent.verification.models import Verdict
from aiecs.domain.agent.verification.policy_models import VerificationPolicy, resolve_verification_policy
from aiecs.domain.agent.verification.verifier import Verifier, merge_verdicts
from aiecs.llm import LLMMessage

GvrTrigger = Literal["on_task_completed", "on_stop"]

_REFINE_COUNT_KEY = "gvr.refine_count"
_VERIFIED_KEY = "gvr.verified_checkpoints"
_EVENTS_KEY = "gvr.verification_events"


def _verified_checkpoints(plugin_state: dict[str, Any]) -> list[str]:
    """Return JSON-serializable dedupe checkpoint list (migrates legacy set)."""
    raw = plugin_state.get(_VERIFIED_KEY)
    if raw is None:
        checkpoints: list[str] = []
    elif isinstance(raw, set):
        checkpoints = sorted(str(item) for item in raw)
    elif isinstance(raw, list):
        checkpoints = [str(item) for item in raw]
    else:
        checkpoints = [str(raw)]
    plugin_state[_VERIFIED_KEY] = checkpoints
    return checkpoints


def _checkpoint_seen(plugin_state: dict[str, Any], dedupe: str) -> bool:
    return dedupe in _verified_checkpoints(plugin_state)


def _mark_checkpoint_verified(plugin_state: dict[str, Any], dedupe: str) -> None:
    checkpoints = _verified_checkpoints(plugin_state)
    if dedupe not in checkpoints:
        checkpoints.append(dedupe)
    plugin_state[_VERIFIED_KEY] = checkpoints


@dataclass
class PolicyRunResult:
    """Outcome of a verification_policy run."""

    verdict: Verdict
    skipped_llm: bool = False
    continued_loop: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)


def _normalize_registered_id(value: str) -> str:
    return value.strip().lower()


def _is_gate_id(reg_id: str) -> bool:
    return _normalize_registered_id(reg_id) in BUILTIN_GATES


def build_policy_gate_registry(registered_verifiers: Sequence[str]) -> GateRegistry:
    registry = GateRegistry()
    for reg_id in registered_verifiers:
        if _is_gate_id(reg_id):
            registry.register_by_id(reg_id)
    return registry


def resolve_registered_verifiers(
    registered_ids: Sequence[str],
    agent_verifiers: Sequence[Any],
) -> tuple[list[Any], list[str]]:
    """Return LLM verifiers for registered ids; raise on unknown non-gate ids."""
    resolved: list[Any] = []
    unknown: list[str] = []
    for reg_id in registered_ids:
        if _is_gate_id(reg_id):
            continue
        normalized = _normalize_registered_id(reg_id)
        matches = [v for v in agent_verifiers if _normalize_registered_id(getattr(v, "kind", type(v).__name__)) == normalized]
        if matches:
            resolved.extend(matches)
        else:
            unknown.append(reg_id)
    if unknown:
        raise ValueError(f"Unknown registered_verifiers ids: {unknown}. Known gates: {sorted(BUILTIN_GATES)}")
    return resolved, unknown


def _goal_kind(goal: AgentGoal | dict[str, Any] | None) -> Optional[str]:
    if goal is None:
        return None
    if isinstance(goal, dict):
        meta = goal.get("metadata") or {}
        return meta.get("kind") or goal.get("kind")
    meta = goal.metadata or {}
    return meta.get("kind")


def _dedupe_key(goal_id: str | None, iteration: int, trigger: GvrTrigger) -> str:
    return f"{goal_id or 'none'}:{iteration}:{trigger}"


def _record_event(plugin_state: dict[str, Any], event: dict[str, Any]) -> None:
    plugin_state.setdefault(_EVENTS_KEY, []).append(event)


async def run_verification_policy(
    *,
    policy: VerificationPolicy,
    agent_verifiers: Sequence[Any],
    messages: list[LLMMessage],
    loop_result: dict[str, Any],
    goal: AgentGoal | dict[str, Any] | None,
    plugin_state: dict[str, Any],
    trigger: GvrTrigger,
    iteration: int,
) -> PolicyRunResult:
    """Execute verification_policy for a single pre-exit checkpoint."""
    goal_id = None
    if goal is not None:
        goal_id = getattr(goal, "goal_id", None) or (goal.get("goal_id") if isinstance(goal, dict) else None)

    dedupe = _dedupe_key(goal_id, iteration, trigger)
    if _checkpoint_seen(plugin_state, dedupe):
        _record_event(
            plugin_state,
            {"type": "verification_policy", "event": "dedupe_skip", "checkpoint": dedupe},
        )
        return PolicyRunResult(
            verdict=Verdict(passed=True, kind="NA", feedback="Deduped checkpoint."),
            continued_loop=False,
        )
    _mark_checkpoint_verified(plugin_state, dedupe)

    registered = list(policy.registered_verifiers)
    llm_verifiers, _ = resolve_registered_verifiers(registered, agent_verifiers)
    gate_registry = build_policy_gate_registry(registered)

    work_snapshot = {
        "text": loop_result.get("final_response") or loop_result.get("output") or "",
        "output": loop_result.get("output") or loop_result.get("final_response") or "",
    }
    skip_threshold = policy.effective_skip_threshold(_goal_kind(goal))
    gate_verdict: Verdict | None = None
    skipped_llm = False

    if gate_registry.gate_ids:
        if gates_already_run(plugin_state, goal_id, iteration):
            _record_event(
                plugin_state,
                {
                    "type": "verification_policy",
                    "event": "gate_dedupe_skip",
                    "checkpoint": gates_dedupe_key(goal_id, iteration),
                },
            )
        else:
            aggregate = gate_registry.run_all(
                goal=goal,
                result=loop_result,
                work_snapshot=work_snapshot,
                skip_threshold=skip_threshold,
            )
            mark_gates_run(plugin_state, goal_id, iteration)
            gate_verdict = gate_aggregate_to_verdict(aggregate, goal=goal)
            _record_event(
                plugin_state,
                {
                    "type": "verification_policy",
                    "event": "gate_run",
                    "score": aggregate.score,
                    "passed": aggregate.passed,
                    "failed_criteria": aggregate.failed_criteria,
                },
            )
            if aggregate.passed and aggregate.score >= skip_threshold:
                skipped_llm = True
                _record_event(
                    plugin_state,
                    {
                        "type": "verification_policy",
                        "event": "skip_llm",
                        "reason": "gate_score_meets_threshold",
                        "threshold": skip_threshold,
                    },
                )

    criteria = normalize_acceptance_criteria(goal or {})
    context = build_verification_context(
        result=loop_result,
        goal=goal,
        registered_verifier_ids=registered,
        iteration=iteration,
        phase="task_completed" if trigger == "on_task_completed" else "stop",
    )

    verdicts: list[Verdict] = []
    if gate_verdict is not None:
        verdicts.append(gate_verdict)

    if llm_verifiers and not skipped_llm:
        for verifier in llm_verifiers:
            if not isinstance(verifier, Verifier):
                continue
            verdicts.append(
                await verifier.verify(
                    goal=goal or {},
                    result=loop_result,
                    criteria=criteria,
                    context=context,
                )
            )

    if not verdicts:
        final = Verdict(passed=True, kind="NA", feedback="No verifiers resolved for policy run.")
    else:
        final = merge_verdicts(verdicts)

    _record_event(
        plugin_state,
        {
            "type": "verification_policy",
            "event": "verdict",
            "passed": final.passed,
            "kind": final.kind,
            "skipped_llm": skipped_llm,
            "trigger": trigger,
        },
    )

    if final.passed:
        return PolicyRunResult(verdict=final, skipped_llm=skipped_llm, continued_loop=False)

    refine_key = f"{goal_id or 'global'}:{_REFINE_COUNT_KEY}"
    refine_count = int(plugin_state.get(refine_key, 0)) + 1
    plugin_state[refine_key] = refine_count
    _record_event(
        plugin_state,
        {
            "type": "verification_policy",
            "event": "refine",
            "count": refine_count,
            "max_refines": policy.max_refines_per_goal,
        },
    )

    if refine_count > policy.max_refines_per_goal:
        raise VerificationExhausted(final, agent_id=None)

    if not policy.blocking:
        _record_event(
            plugin_state,
            {
                "type": "verification_policy",
                "event": "non_blocking_fail",
                "kind": final.kind,
            },
        )
        return PolicyRunResult(verdict=final, skipped_llm=skipped_llm, continued_loop=False)

    message = format_blocking_user_message(final.feedback, final.feedback_items)
    inject_blocking_user_message(messages, message)
    return PolicyRunResult(verdict=final, skipped_llm=skipped_llm, continued_loop=True)


def _goal_from_agent(agent: Any) -> AgentGoal | dict[str, Any] | None:
    if hasattr(agent, "_current_goal_for_gvr"):
        return cast(AgentGoal | dict[str, Any] | None, agent._current_goal_for_gvr())
    return None


def _resolve_gate_registry(agent: Any) -> GateRegistry:
    gate_registry = getattr(agent, "_gate_registry", None)
    if gate_registry is None:
        gate_registry = build_gate_registry_from_config(getattr(agent._config, "deterministic_gates", None))
    return gate_registry


async def _run_a8_pre_exit_fallback(
    *,
    agent: Any,
    plugin_ctx: Any,
    messages: list[LLMMessage],
    loop_result: dict[str, Any],
    trigger: GvrTrigger,
    iteration: int,
) -> bool:
    """A-8 gate/hook fallback when verification_policy does not handle the trigger."""
    gate_registry = _resolve_gate_registry(agent)

    if trigger == "on_stop":
        if not gate_registry.gate_ids:
            return False
        return await run_pre_exit_gvr_check(
            plugin_ctx=plugin_ctx,
            messages=messages,
            loop_result=loop_result,
            gate_registry=gate_registry,
            goal=_goal_from_agent(agent),
            skip_threshold=getattr(agent._config, "gvr_gate_skip_threshold", 85.0),
            dispatch_task_completed_hook=False,
            iteration=iteration,
        )

    if not gate_registry.gate_ids and not plugin_ctx.context.get("enable_gvr_pre_exit_hooks"):
        from aiecs.domain.agent.plugins.hooks.dispatch import has_registered_hooks
        from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent

        if not has_registered_hooks(plugin_ctx, AgentHookEvent.TASK_COMPLETED):
            return False

    return await run_pre_exit_gvr_check(
        plugin_ctx=plugin_ctx,
        messages=messages,
        loop_result=loop_result,
        gate_registry=gate_registry,
        goal=_goal_from_agent(agent),
        skip_threshold=getattr(agent._config, "gvr_gate_skip_threshold", 85.0),
        dispatch_task_completed_hook=True,
        iteration=iteration,
    )


async def run_gvr_pre_exit(
    *,
    agent: Any,
    plugin_ctx: Any,
    messages: list[LLMMessage],
    loop_result: dict[str, Any],
    trigger: GvrTrigger,
    iteration: int,
) -> bool:
    """
    Pre-exit GVR orchestration: verification_policy (A-2) > HookPlugin gates (A-8) > default.

    Returns True when the FC loop should continue (refine).
    """
    policy: VerificationPolicy | None = resolve_verification_policy(getattr(agent._config, "verification_policy", None))
    if policy is not None and policy.should_run_for_trigger(trigger):
        result = await run_verification_policy(
            policy=policy,
            agent_verifiers=getattr(agent, "_verifiers", []),
            messages=messages,
            loop_result=loop_result,
            goal=_goal_from_agent(agent),
            plugin_state=plugin_ctx.plugin_state,
            trigger=trigger,
            iteration=iteration,
        )
        return result.continued_loop

    return await _run_a8_pre_exit_fallback(
        agent=agent,
        plugin_ctx=plugin_ctx,
        messages=messages,
        loop_result=loop_result,
        trigger=trigger,
        iteration=iteration,
    )


async def run_stop_hook_with_policy_fallback(
    *,
    agent: Any,
    plugin_ctx: Any,
    messages: list[LLMMessage],
    loop_result: dict[str, Any],
    iteration: int,
    hook_result_handler: Any,
) -> bool:
    """
    STOP path: policy may handle on_stop; otherwise delegate to hook prevent_continuation.

    ``hook_result_handler`` is an async callable returning AggregatedHookResult.
    """
    policy: VerificationPolicy | None = resolve_verification_policy(getattr(agent._config, "verification_policy", None))
    if policy is not None and policy.should_run_for_trigger("on_stop"):
        return await run_gvr_pre_exit(
            agent=agent,
            plugin_ctx=plugin_ctx,
            messages=messages,
            loop_result=loop_result,
            trigger="on_stop",
            iteration=iteration,
        )

    continued = await run_gvr_pre_exit(
        agent=agent,
        plugin_ctx=plugin_ctx,
        messages=messages,
        loop_result=loop_result,
        trigger="on_stop",
        iteration=iteration,
    )
    if continued:
        return True

    from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult

    result = await hook_result_handler()
    if not isinstance(result, AggregatedHookResult):
        return False
    return result.prevent_continuation
