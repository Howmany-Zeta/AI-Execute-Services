# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
GVR consumer API contract tests (M-8).

Tier ``baseline``: symbols required in 2.1.0rc4 — must pass on every CI run.
Tier ``gvr_ga``: symbols planned for GA (A-1…A-11) — skipped until implemented.
"""

from __future__ import annotations

import importlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.contract


@dataclass(frozen=True)
class SymbolSpec:
    module: str
    name: str
    kind: str = "class"  # class | function | enum_member
    attr: str | None = None  # for enum_member or nested attr check


# --- Tier 1: 2.1.0rc4 baseline (task 0.1 confirmation) ---

BASELINE_SYMBOLS: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.hybrid_agent", "HybridAgent"),
    SymbolSpec("aiecs.domain.agent.base_agent", "BaseAIAgent"),
    SymbolSpec("aiecs.domain.agent.models", "AgentGoal"),
    SymbolSpec("aiecs.domain.agent.models", "AgentConfiguration"),
    SymbolSpec("aiecs.domain.agent.plugins.builtin.hook_plugin", "HookPlugin"),
    SymbolSpec("aiecs.domain.agent.plugins.hooks.events", "AgentHookEvent"),
    SymbolSpec("aiecs.domain.agent.plugins.models", "PluginPhase"),
    SymbolSpec("aiecs.domain.agent.plugins.builtin.dawp_plugin", "DawpPlugin"),
)

BASELINE_AGENT_HOOK_EVENTS = frozenset({"TASK_COMPLETED", "STOP"})

BASELINE_AGENT_CONFIG_FIELDS = frozenset({"compact_after_tool_batch", "compact_after_tool_batch_min_tokens"})

BASELINE_BASE_AGENT_METHODS = frozenset({"execute_with_recovery", "request_peer_review"})


# --- Tier 2: GVR GA target (A-1+ implemented; remainder skipped until later tasks) ---

GVR_GA_SYMBOLS_A1: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.verification.models", "Verdict"),
    SymbolSpec("aiecs.domain.agent.verification.models", "FeedbackItem"),
    SymbolSpec("aiecs.domain.agent.verification.models", "EvidenceItem"),
    SymbolSpec("aiecs.domain.agent.verification.models", "AcceptanceCriterion"),
    SymbolSpec("aiecs.domain.agent.verification.models", "VerificationContext"),
    SymbolSpec("aiecs.domain.agent.verification.verifier", "Verifier"),
    SymbolSpec("aiecs.domain.agent.verification", "normalize_acceptance_criteria", kind="function"),
    SymbolSpec("aiecs.domain.agent.verification.read_only_verifier", "ReadOnlyAdversarialVerifier"),
    SymbolSpec("aiecs.domain.agent.verification.gates", "GateRegistry"),
    SymbolSpec("aiecs.domain.agent.verification.gates", "GateScore"),
    SymbolSpec("aiecs.domain.agent.verification.gates", "SpecGate"),
    SymbolSpec("aiecs.domain.agent.verification.gates", "gate_aggregate_to_verdict", kind="function"),
)

GVR_GA_SYMBOLS_A2: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.models", "VerificationPolicy"),
    SymbolSpec("aiecs.domain.agent.verification", "VerificationExhausted", kind="class"),
    SymbolSpec("aiecs.domain.agent.verification", "run_gvr_pre_exit", kind="function"),
)

GVR_GA_SYMBOLS_A5: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.models", "PeerReviewPolicy"),
    SymbolSpec("aiecs.domain.agent.verification", "peer_review_response_to_verdict", kind="function"),
)

GVR_GA_SYMBOLS_A7: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.loop_detection", "LoopSignal"),
    SymbolSpec("aiecs.domain.agent.loop_detection", "LoopDetectionService"),
    SymbolSpec("aiecs.domain.agent.loop_detection", "LoopDetectionConfig"),
)

GVR_GA_SYMBOLS_A3: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.goal_graph", "GoalGraph"),
    SymbolSpec("aiecs.domain.agent.models", "GoalGraphConfig"),
)

GVR_GA_SYMBOLS_A6: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.verification.dawp_result", "DAWPResult"),
    SymbolSpec("aiecs.domain.agent.verification", "build_dawp_result", kind="function"),
)

GVR_GA_SYMBOLS_A9: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.models", "RecoveryResult"),
)

GVR_GA_SYMBOLS_A11: tuple[SymbolSpec, ...] = (
    SymbolSpec("aiecs.domain.agent.verification.cwe_verifier", "CweVerifier"),
    SymbolSpec("aiecs.domain.agent.verification.cwe_verifier_policy_models", "CweVerifierPolicy"),
)

GVR_GA_SYMBOLS_PENDING: tuple[SymbolSpec, ...] = ()


def _import_symbol(spec: SymbolSpec) -> Any:
    mod = importlib.import_module(spec.module)
    return getattr(mod, spec.name)


class TestGvrBaselineSurface:
    """M-8 / task 0.1: confirm 2.1.0rc4 baseline exports."""

    @pytest.mark.parametrize("spec", BASELINE_SYMBOLS, ids=lambda s: f"{s.module}.{s.name}")
    def test_baseline_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_agent_hook_events_task_completed_and_stop(self) -> None:
        from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent

        names = {e.name for e in AgentHookEvent}
        assert BASELINE_AGENT_HOOK_EVENTS <= names

    def test_plugin_phase_on_tool_batch_end(self) -> None:
        from aiecs.domain.agent.plugins.models import PluginPhase

        assert hasattr(PluginPhase, "ON_TOOL_BATCH_END")

    def test_agent_configuration_compact_after_tool_batch_fields(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        fields = set(AgentConfiguration.model_fields.keys())
        assert BASELINE_AGENT_CONFIG_FIELDS <= fields

    def test_agent_goal_flat_model_fields(self) -> None:
        from aiecs.domain.agent.models import AgentGoal

        fields = set(AgentGoal.model_fields.keys())
        assert "goal_id" in fields
        assert "parent_goal_id" in fields
        assert "success_criteria" in fields
        assert "depends_on" in fields

    def test_base_agent_recovery_and_peer_review_methods(self) -> None:
        from aiecs.domain.agent.base_agent import BaseAIAgent

        for method_name in BASELINE_BASE_AGENT_METHODS:
            assert hasattr(BaseAIAgent, method_name)
            assert callable(getattr(BaseAIAgent, method_name))

    def test_hybrid_agent_execute_task_streaming(self) -> None:
        from aiecs.domain.agent.hybrid_agent import HybridAgent

        assert hasattr(HybridAgent, "execute_task_streaming")
        assert inspect.isasyncgenfunction(HybridAgent.execute_task_streaming)


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA1:
    """GVR A-1 symbols — required after task 2."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A1, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a1_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_hybrid_agent_verify_hook(self) -> None:
        from aiecs.domain.agent.hybrid_agent import HybridAgent

        assert hasattr(HybridAgent, "verify")
        assert callable(getattr(HybridAgent, "verify"))

    def test_agent_public_api_exports_verdict(self) -> None:
        import aiecs.domain.agent as agent_module

        for name in ("Verdict", "VerificationContext", "normalize_acceptance_criteria"):
            assert hasattr(agent_module, name), f"missing public export: {name}"


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA2:
    """GVR A-2 verification_policy symbols — required after task 5."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A2, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a2_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_agent_configuration_verification_policy_field(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        assert "verification_policy" in AgentConfiguration.model_fields

    def test_verification_exhausted_from_exceptions(self) -> None:
        from aiecs.domain.agent.exceptions import VerificationExhausted as exc_mod

        from aiecs.domain.agent.verification import VerificationExhausted as exc_pkg

        assert exc_mod is exc_pkg


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA5:
    """GVR A-5 peer_review symbols — required after task 6."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A5, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a5_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_agent_configuration_peer_review_policy_field(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        assert "peer_review_policy" in AgentConfiguration.model_fields


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA7:
    """GVR A-7 loop detection symbols — required after task 7."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A7, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a7_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_hybrid_agent_get_loop_signals(self) -> None:
        from aiecs.domain.agent.hybrid_agent import HybridAgent

        assert hasattr(HybridAgent, "get_loop_signals")
        assert callable(getattr(HybridAgent, "get_loop_signals"))

    def test_on_loop_detected_hook_event(self) -> None:
        from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent

        assert hasattr(AgentHookEvent, "ON_LOOP_DETECTED")

    def test_agent_configuration_loop_detection_field(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        assert "loop_detection" in AgentConfiguration.model_fields


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA3:
    """GVR A-3 GoalGraph symbols — required after task 8."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A3, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a3_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_agent_goal_gvr_fields(self) -> None:
        from aiecs.domain.agent.models import AgentGoal

        fields = set(AgentGoal.model_fields.keys())
        assert {"verdict_history", "origin", "parent_goal_id", "goal_id"}.issubset(fields)
        goal = AgentGoal.model_validate({"id": "x", "description": "d"})
        assert goal.id == "x"

    def test_base_agent_set_goal_graph(self) -> None:
        from aiecs.domain.agent.base_agent import BaseAIAgent

        assert hasattr(BaseAIAgent, "set_goal_graph")
        assert hasattr(BaseAIAgent, "get_current_goal")


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA6:
    """GVR A-6 DAWPResult symbols — required after task 9."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A6, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a6_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_dawp_result_partial_not_passed(self) -> None:
        from aiecs.domain.agent.verification.dawp_result import DAWPResult

        assert DAWPResult(status="partial").passed is False

    def test_agent_configuration_dawp_emit_field(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        assert "dawp_emit_structured_result" in AgentConfiguration.model_fields


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA9:
    """GVR A-9 recovery symbols — required after task 10."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A9, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a9_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_base_agent_execute_with_recovery_streaming(self) -> None:
        from aiecs.domain.agent.base_agent import BaseAIAgent

        assert hasattr(BaseAIAgent, "execute_with_recovery_streaming")
        assert inspect.isasyncgenfunction(BaseAIAgent.execute_with_recovery_streaming)


@pytest.mark.gvr_ga
class TestGvrGaSurfaceA11:
    """GVR A-11 CWE verifier symbols — required after task 12."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_A11, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_a11_symbol_importable(self, spec: SymbolSpec) -> None:
        obj = _import_symbol(spec)
        assert obj is not None

    def test_agent_configuration_cwe_verifier_field(self) -> None:
        from aiecs.domain.agent.models import AgentConfiguration

        assert "cwe_verifier" in AgentConfiguration.model_fields


@pytest.mark.gvr_ga
class TestGvrGaSurfacePending:
    """GVR symbols planned for tasks 3+."""

    @pytest.mark.parametrize("spec", GVR_GA_SYMBOLS_PENDING, ids=lambda s: f"{s.module}.{s.name}")
    def test_gvr_pending_symbol_importable(self, spec: SymbolSpec) -> None:
        try:
            obj = _import_symbol(spec)
        except (ImportError, ModuleNotFoundError, AttributeError) as exc:
            pytest.skip(f"GVR symbol not yet available: {spec.module}.{spec.name} ({exc})")
        assert obj is not None


class TestGvrVerdictFixture:
    """M-8 shared fixture skeleton (task 0.3)."""

    @pytest.fixture
    def verdict_fixture_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "fixtures" / "gvr_verdict_v1.json"

    def test_verdict_fixture_exists_and_valid_json(self, verdict_fixture_path: Path) -> None:
        assert verdict_fixture_path.is_file()
        data = json.loads(verdict_fixture_path.read_text(encoding="utf-8"))
        assert data["title"] == "GVR Verdict v1"
        assert "examples" in data
        example = data["examples"][0]
        assert example["kind"] in {"PASS", "FAIL", "PARTIAL", "NA"}
        assert "feedback_items" in example
        assert "evidence" in example

    def test_verdict_fixture_example_quote_max_length(self, verdict_fixture_path: Path) -> None:
        data = json.loads(verdict_fixture_path.read_text(encoding="utf-8"))
        for example in data.get("examples", []):
            for item in example.get("evidence", []):
                quote = item.get("quote", "")
                assert len(quote) <= 120, f"evidence quote exceeds 120 chars: {len(quote)}"


class TestGvrDocsPackaged:
    """Task 1.5: GVR docs included in wheel package-data."""

    def test_gvr_consumer_api_doc_on_disk(self) -> None:
        root = Path(__file__).resolve().parents[2]
        doc = root / "aiecs" / "docs" / "gvr_consumer_api.md"
        assert doc.is_file()
        text = doc.read_text(encoding="utf-8")
        assert "§ Adoption paths" in text or "Adoption paths" in text
        assert "Semver policy" in text

    def test_migration_guide_on_disk(self) -> None:
        root = Path(__file__).resolve().parents[2]
        doc = root / "aiecs" / "docs" / "migration_2.1.0rc4_to_ga.md"
        assert doc.is_file()
        assert "2.1.0rc4" in doc.read_text(encoding="utf-8")
