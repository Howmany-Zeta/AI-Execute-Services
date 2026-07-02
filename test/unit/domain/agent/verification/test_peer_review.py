"""
Unit tests for peer review mini-Verdict (A-5).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.domain.agent.verification.models import Verdict
from aiecs.domain.agent.verification.peer_review import (
    assert_peer_review_eligible,
    peer_review_response_to_verdict,
)
from aiecs.domain.agent.verification.peer_review_policy_models import PeerReviewPolicy


@pytest.mark.unit
class TestPeerReviewVerdict:
    def test_legacy_dict_maps_to_verdict(self) -> None:
        verdict = peer_review_response_to_verdict(
            {"approved": True, "feedback": "looks good", "reviewer_id": "r1"},
            criteria=[],
        )
        assert verdict.passed is True
        assert verdict.kind == "PASS"
        round_trip = Verdict.from_dict(verdict.to_dict())
        assert round_trip.passed is True

    def test_high_criteria_count_rejected(self) -> None:
        criteria = [{"criterion_id": f"c{i}", "description": f"d{i}"} for i in range(5)]
        from aiecs.domain.agent.verification.peer_review import coerce_criteria

        normalized = coerce_criteria(criteria)
        with pytest.raises(ValueError, match="MUST NOT use peer_review alone"):
            assert_peer_review_eligible(normalized, PeerReviewPolicy(enabled=True, max_criteria=4))

    def test_policy_max_criteria_enforced(self) -> None:
        from aiecs.domain.agent.verification.peer_review import coerce_criteria

        normalized = coerce_criteria(
            [
                {"criterion_id": "c1", "description": "a"},
                {"criterion_id": "c2", "description": "b"},
                {"criterion_id": "c3", "description": "c"},
            ]
        )
        with pytest.raises(ValueError, match="max_criteria"):
            assert_peer_review_eligible(normalized, PeerReviewPolicy(enabled=True, max_criteria=2))


@pytest.mark.unit
class TestRequestPeerReviewQuickPath:
    @pytest.mark.asyncio
    async def test_quick_goal_two_criteria_returns_verdict(self) -> None:
        reviewer = MagicMock()
        reviewer.agent_id = "reviewer-1"

        async def _review_result(task, result):
            assert task.get("review_contract") == "gvr_peer_review_v1"
            assert len(task.get("criteria", [])) == 2
            return {"approved": False, "feedback": "missing summary", "partial": True}

        reviewer.review_result = _review_result

        config = AgentConfiguration(
            name="Main",
            description="main",
            peer_review_policy={"enabled": True, "max_criteria": 2},
        )
        main = ToolAgent(
            agent_id="main",
            name="Main",
            description="main",
            config=config,
            tools={},
            collaboration_enabled=True,
            agent_registry={"reviewer-1": reviewer},
        )

        task = {
            "description": "QUICK summary",
            "task_id": "t1",
            "success_criteria": [
                {"criterion_id": "c1", "description": "summary"},
                {"criterion_id": "c2", "description": "bullets"},
            ],
        }
        result = {"output": "draft only", "success": True}

        verdict = await main.request_peer_review(task, result, reviewer_id="reviewer-1")
        assert isinstance(verdict, Verdict)
        assert verdict.kind == "PARTIAL"
        assert Verdict.from_dict(verdict.to_dict()).kind == "PARTIAL"
