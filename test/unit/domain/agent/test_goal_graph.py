"""
Unit tests for GoalGraph (A-3).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.goal_graph import GoalGraph
from aiecs.domain.agent.models import GoalStatus
from aiecs.domain.agent.verification.models import AcceptanceCriterion, Verdict


@pytest.mark.unit
class TestGoalGraphApi:
    def test_add_goal_requires_structured_criteria(self) -> None:
        graph = GoalGraph()
        with pytest.raises(ValueError, match="structured"):
            graph.add_goal(description="bad", success_criteria=["plain string"])

        goal = graph.add_goal(
            description="root",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="summary")],
            origin="root",
        )
        assert goal.goal_id in graph.goal_ids
        assert goal.origin == "root"

    def test_parent_child_topology(self) -> None:
        graph = GoalGraph()
        root = graph.add_goal(
            description="root",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="a")],
        )
        child = graph.add_goal(
            description="child",
            success_criteria=[AcceptanceCriterion(criterion_id="c2", description="b")],
            parent_goal_id=root.goal_id,
            origin="decompose",
        )
        assert child.parent_goal_id == root.goal_id

    def test_depends_on_and_next_open_goal(self) -> None:
        graph = GoalGraph()
        g1 = graph.add_goal(
            description="first",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="a")],
        )
        g2 = graph.add_goal(
            description="second",
            success_criteria=[AcceptanceCriterion(criterion_id="c2", description="b")],
            depends_on=[g1.goal_id],
        )
        assert graph.next_open_goal() == g1
        graph.close_goal(g1.goal_id)
        assert graph.next_open_goal() == g2

    def test_spawn_subgoals_expand(self) -> None:
        graph = GoalGraph()
        parent = graph.add_goal(
            description="report",
            success_criteria=[AcceptanceCriterion(criterion_id="c0", description="base")],
        )
        missing = [
            AcceptanceCriterion(criterion_id="m1", description="GIVEN"),
            AcceptanceCriterion(criterion_id="m2", description="WHEN"),
        ]
        spawned = graph.spawn_subgoals(parent.goal_id, missing, origin="expand")
        assert len(spawned) == 2
        assert all(g.parent_goal_id == parent.goal_id for g in spawned)
        assert all(g.origin == "expand" for g in spawned)

    def test_json_round_trip(self) -> None:
        graph = GoalGraph()
        graph.add_goal(
            description="persist",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="x")],
        )
        restored = GoalGraph.from_json(graph.to_json())
        assert len(restored.all_goals()) == 1
        assert restored.all_goals()[0].description == "persist"

    def test_record_verdict_append_only(self) -> None:
        graph = GoalGraph()
        goal = graph.add_goal(
            description="v",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="x")],
        )
        graph.record_verdict(goal.goal_id, Verdict(passed=True, kind="PASS", feedback="a"))
        graph.record_verdict(goal.goal_id, Verdict(passed=False, kind="FAIL", feedback="b"))
        stored = graph.get_goal(goal.goal_id)
        assert stored is not None
        assert len(stored.verdict_history) == 2
        assert stored.verdict_history[0]["kind"] == "PASS"


@pytest.mark.unit
class TestGoalGraphDecompose:
    @pytest.mark.asyncio
    async def test_decompose_without_decomposer_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="decomposer="):
            await GoalGraph.decompose("build api", "gvr_v1")

    @pytest.mark.asyncio
    async def test_custom_decomposer_override(self) -> None:
        async def _decomposer(user_request: str, protocol: str) -> GoalGraph:
            g = GoalGraph()
            g.add_goal(
                description=user_request,
                success_criteria=[AcceptanceCriterion(criterion_id="c1", description=protocol)],
                origin="decompose",
            )
            return g

        graph = await GoalGraph.decompose("task", "quick", decomposer=_decomposer)
        assert len(graph.all_goals()) == 1
        assert graph.all_goals()[0].origin == "decompose"


@pytest.mark.unit
class TestSetGoalGraphIntegration:
    def test_set_goal_accepts_agent_goal_node(self) -> None:
        from aiecs.domain.agent.tool_agent import ToolAgent
        from aiecs.domain.agent.models import AgentConfiguration, AgentGoal

        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        node = AgentGoal(
            description="graph node",
            success_criteria=[
                AcceptanceCriterion(criterion_id="c1", description="tests"),
            ],
        )
        goal_id = agent.set_goal(node)
        assert agent.get_current_goal() is not None
        assert agent.get_current_goal().goal_id == goal_id

    def test_set_goal_graph_registers_nodes(self) -> None:
        from aiecs.domain.agent.tool_agent import ToolAgent
        from aiecs.domain.agent.models import AgentConfiguration

        agent = ToolAgent(
            agent_id="a1",
            name="A",
            description="d",
            config=AgentConfiguration(name="A", description="d"),
            tools={},
        )
        graph = GoalGraph()
        graph.add_goal(
            description="g1",
            success_criteria=[AcceptanceCriterion(criterion_id="c1", description="x")],
        )
        graph.add_goal(
            description="g2",
            success_criteria=[AcceptanceCriterion(criterion_id="c2", description="y")],
            depends_on=[graph.all_goals()[0].goal_id],
        )
        agent.set_goal_graph(graph)
        assert agent.get_current_goal() is not None
        assert agent.get_current_goal().description == "g1"
