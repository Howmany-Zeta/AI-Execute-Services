# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
CWE multi-perspective verifier (A-11).

Delegates to ``CollaborativeWorkflowEngine.review_refinement`` — sequential fact→style
via ``spawn_verifier`` (host analogue: ``spawn_subagent(verifier)``).
"""

from __future__ import annotations

from typing import Any, Union

from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.verification.criteria import normalize_acceptance_criteria
from aiecs.domain.agent.verification.cwe_verifier_policy_models import (
    CweVerifierPolicy,
    H1_DELIVERY_KINDS,
    H1_MIN_CRITERIA,
    resolve_cwe_verifier_policy,
)
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict, VerificationContext
from aiecs.domain.agent.verification.review_refinement import (
    build_review_refinement_task,
    review_refinement_response_to_verdict,
)
from aiecs.domain.agent.verification.verifier import merge_verdicts
from aiecs.domain.community.collaborative_workflow import (
    CollaborativeWorkflowEngine,
    SpawnVerifierCallback,
)


def is_h1_goal(goal: Union[AgentGoal, dict[str, Any], None]) -> bool:
    """H1 goals: ≥5 criteria or delivery_kind in {report, analysis}."""
    if goal is None:
        return False
    if isinstance(goal, AgentGoal):
        metadata = goal.metadata or {}
        payload = goal.model_dump()
    else:
        metadata = goal.get("metadata") or {}
        payload = goal
    delivery_kind = str(metadata.get("delivery_kind") or payload.get("delivery_kind") or "").lower()
    if delivery_kind in H1_DELIVERY_KINDS:
        return True
    return len(normalize_acceptance_criteria(payload)) >= H1_MIN_CRITERIA


async def run_dual_spawn_verifier_path(
    *,
    task: dict[str, Any],
    result: dict[str, Any],
    criteria: list[AcceptanceCriterion],
    spawn_verifier: SpawnVerifierCallback,
) -> Verdict:
    """
    V-3 B reference path: sequential dual ``spawn_subagent(verifier)`` without CWE engine.

    Host fallback when ``cwe_verifier.enabled=false``. Each role spawns an independent
    verifier subagent in order (fact, then style) — no parallel SSE.
    """
    verdicts: list[Verdict] = []
    for role in ("fact", "style"):
        review_task = build_review_refinement_task(
            role=role,
            task=task,
            result=result,
            criteria=criteria,
        )
        review_payload = await spawn_verifier(review_task)
        verdicts.append(review_refinement_response_to_verdict(review_payload, role=role, criteria=criteria))
    return merge_verdicts(verdicts)


class CweVerifier:
    """
    Sequential fact→style verifier via ``CollaborativeWorkflowEngine.review_refinement``.

    Enabled only for H1 goals when ``cwe_verifier.enabled=true``.
    Requires ``spawn_verifier`` — maps to host ``spawn_subagent(verifier)`` per role.
    """

    kind: str = "cwe_verifier"

    def __init__(
        self,
        policy: CweVerifierPolicy | None = None,
        *,
        engine: CollaborativeWorkflowEngine | None = None,
        spawn_verifier: SpawnVerifierCallback | None = None,
    ) -> None:
        self._policy = policy or CweVerifierPolicy()
        self._engine = engine or CollaborativeWorkflowEngine()
        self._spawn_verifier = spawn_verifier

    @property
    def policy(self) -> CweVerifierPolicy:
        return self._policy

    @property
    def engine(self) -> CollaborativeWorkflowEngine:
        return self._engine

    async def verify(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any]],
        result: dict[str, Any],
        criteria: list[AcceptanceCriterion],
        context: VerificationContext,
    ) -> Verdict:
        if not self._policy.enabled:
            return Verdict(passed=True, kind="NA", feedback="CWE verifier disabled.")

        if not is_h1_goal(goal):
            return Verdict(passed=True, kind="NA", feedback="CWE verifier applies to H1 goals only.")

        if self._spawn_verifier is None:
            return Verdict(
                passed=False,
                kind="FAIL",
                feedback=("CWE verifier misconfigured: spawn_verifier required when " "cwe_verifier.enabled=true (spawn_subagent analogue)."),
            )

        task = {
            "task_id": context.goal_snapshot.get("goal_id") or "unknown",
            "description": context.goal_snapshot.get("description") or "",
        }
        payload = await self._engine.review_refinement(
            task=task,
            result=result,
            criteria=criteria,
            spawn_verifier=self._spawn_verifier,
        )
        return Verdict.from_dict(payload["verdict"])


def build_cwe_verifier_from_config(
    raw_policy: Any,
    *,
    engine: CollaborativeWorkflowEngine | None = None,
    spawn_verifier: SpawnVerifierCallback | None = None,
) -> CweVerifier | None:
    """Construct verifier when policy enabled; None when disabled (rc4 behavior)."""
    policy = resolve_cwe_verifier_policy(raw_policy)
    if policy is None or not policy.enabled:
        return None
    return CweVerifier(policy=policy, engine=engine, spawn_verifier=spawn_verifier)
