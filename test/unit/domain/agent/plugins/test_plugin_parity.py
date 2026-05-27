"""
Plugin parity golden snapshot tests (§12.1, P2-14 / P3-10 CI gate).

Compares live agent output (mock LLM/tool) to YAML fixtures under
``tests/fixtures/plugin_parity/``.

Recommended CI command::

    poetry run pytest test/unit/domain/agent/plugins/test_plugin_parity.py -m plugin_parity -v --tb=short
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.testing.normalize import (
    dumps_normalized,
    normalize_dict,
    normalize_execute_task_response,
    normalize_value,
)
from aiecs.domain.agent.plugins.testing.parity import (
    capture_parity_case,
    compare_parity_expect,
    default_fixtures_dir,
    list_all_parity_fixtures,
    list_knowledge_parity_fixtures,
    list_llm_parity_fixtures,
    list_parity_fixtures,
    list_tool_parity_fixtures,
    load_parity_fixture,
)

_FIXTURES = list_parity_fixtures()
_FIXTURE_IDS = [p.name for p in _FIXTURES]
_SYNC_FIXTURES = [
    p
    for p in _FIXTURES
    if load_parity_fixture(p).parity_mode != "streaming_phases"
]
_SYNC_FIXTURE_IDS = [p.name for p in _SYNC_FIXTURES]

_LLM_FIXTURES = list_llm_parity_fixtures()
_LLM_FIXTURE_IDS = [p.name for p in _LLM_FIXTURES]
_TOOL_FIXTURES = list_tool_parity_fixtures()
_TOOL_FIXTURE_IDS = [p.name for p in _TOOL_FIXTURES]
_LLM_TOOL_FIXTURES = _LLM_FIXTURES + _TOOL_FIXTURES
_LLM_TOOL_FIXTURE_IDS = [p.name for p in _LLM_TOOL_FIXTURES]
_TOOL_MESSAGES_FIXTURES = [
    p
    for p in _TOOL_FIXTURES
    if load_parity_fixture(p).expect.get("messages_normalized")
]
_TOOL_MESSAGES_FIXTURE_IDS = [p.name for p in _TOOL_MESSAGES_FIXTURES]
_KNOWLEDGE_FIXTURES = list_knowledge_parity_fixtures()
_KNOWLEDGE_FIXTURE_IDS = [p.name for p in _KNOWLEDGE_FIXTURES]


@pytest.mark.unit
class TestNormalizeRules:
    """Unit coverage for §12.1 normalize rules."""

    def test_strips_volatile_response_keys(self) -> None:
        raw = {
            "success": True,
            "output": "done",
            "timestamp": "2026-05-26T12:00:00Z",
            "execution_time": 1.23,
        }
        assert normalize_execute_task_response(raw) == {
            "output": "done",
            "success": True,
        }

    def test_iso_timestamp_in_string_replaced(self) -> None:
        assert normalize_value("run at 2026-05-26T12:00:00Z") == "run at <timestamp>"

    def test_collapses_horizontal_whitespace(self) -> None:
        assert normalize_value("  hello   world  ") == "hello world"

    def test_dict_keys_sorted(self) -> None:
        assert list(normalize_dict({"b": 2, "a": 1}).keys()) == ["a", "b"]

    def test_drops_volatile_nested_keys(self) -> None:
        assert normalize_dict({"id": "call_abc", "name": "tool"}) == {"name": "tool"}

    def test_dumps_normalized_is_stable_json(self) -> None:
        payload = {"z": 1, "timestamp": "2026-01-01T00:00:00Z", "nested": {"b": 2, "a": 1}}
        text = dumps_normalized(payload)
        assert "timestamp" not in text
        assert text.index('"a"') < text.index('"b"')


@pytest.mark.plugin_parity
@pytest.mark.unit
class TestPluginParityFixtures:
    """Fixture skeleton and expect blocks."""

    @pytest.mark.parametrize("fixture_path", _FIXTURES, ids=_FIXTURE_IDS)
    def test_fixture_file_exists(self, fixture_path: Path) -> None:
        assert fixture_path.is_file()

    @pytest.mark.parametrize("fixture_path", _FIXTURES, ids=_FIXTURE_IDS)
    def test_fixture_has_expect_block(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        expect = case.expect
        assert expect
        if case.parity_mode == "streaming_phases":
            assert "streaming_phase_sequence" in expect
            assert "sync_phase_sequence" in expect
        else:
            assert "messages_normalized" in expect
            assert "tool_schema_names" in expect
            assert "execute_task_response" in expect


@pytest.mark.plugin_parity
@pytest.mark.unit
@pytest.mark.asyncio
class TestPluginParityComparison:
    """Compare live HybridAgent output to golden fixtures (mock LLM/tool)."""

    @pytest.mark.parametrize("fixture_path", _SYNC_FIXTURES, ids=_SYNC_FIXTURE_IDS)
    async def test_messages_normalized(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _SYNC_FIXTURES, ids=_SYNC_FIXTURE_IDS)
    async def test_tool_schema_names(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_plugin_state_keys=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _SYNC_FIXTURES, ids=_SYNC_FIXTURE_IDS)
    async def test_execute_task_response_shell(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _FIXTURES, ids=_FIXTURE_IDS)
    async def test_full_parity_capture(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        check_streaming = case.parity_mode == "streaming_phases"
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_streaming_phases=check_streaming,
            check_messages=not check_streaming,
            check_tool_schemas=not check_streaming,
            check_execute_response=not check_streaming,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    async def test_streaming_phase_sequence_matches_sync_and_fixture(self) -> None:
        case = load_parity_fixture(
            default_fixtures_dir() / "hybrid_streaming_phases.yaml"
        )
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_execute_response=False,
        )
        assert mismatches == [], f"mismatch in {mismatches}"


@pytest.mark.plugin_parity
@pytest.mark.unit
@pytest.mark.asyncio
class TestPluginsEmptyRegression:
    """``plugins=[]`` derives defaults and matches baseline golden (§6.3.2)."""

    async def test_plugins_empty_matches_baseline_messages(self) -> None:
        baseline = load_parity_fixture(default_fixtures_dir() / "hybrid_baseline.yaml")
        regression = load_parity_fixture(
            default_fixtures_dir() / "hybrid_plugins_empty_regression.yaml"
        )
        baseline_got = await capture_parity_case(baseline)
        regression_got = await capture_parity_case(regression)

        assert (
            regression_got.messages_normalized == baseline_got.messages_normalized
        )
        assert regression_got.tool_schema_names == baseline_got.tool_schema_names
        assert (
            regression_got.execute_task_response == baseline_got.execute_task_response
        )


@pytest.mark.plugin_parity
@pytest.mark.unit
class TestLLMToolParityFixtures:
    """LLMAgent / ToolAgent parity fixture skeleton (§12.1 Phase 3 matrix)."""

    @pytest.mark.parametrize("fixture_path", _LLM_TOOL_FIXTURES, ids=_LLM_TOOL_FIXTURE_IDS)
    def test_fixture_file_exists(self, fixture_path: Path) -> None:
        assert fixture_path.is_file()

    @pytest.mark.parametrize("fixture_path", _LLM_FIXTURES, ids=_LLM_FIXTURE_IDS)
    def test_llm_fixture_has_expect_block(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        expect = case.expect
        assert expect
        assert "messages_normalized" in expect
        assert "tool_schema_names" in expect
        assert "execute_task_response" in expect
        shell = expect["execute_task_response"]
        assert "success" in shell
        assert "output" in shell

    @pytest.mark.parametrize("fixture_path", _TOOL_FIXTURES, ids=_TOOL_FIXTURE_IDS)
    def test_tool_fixture_has_expect_block(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        expect = case.expect
        assert expect
        assert "execute_task_response" in expect
        shell = expect["execute_task_response"]
        assert "success" in shell
        assert "output" in shell
        if case.name == "tool_direct_invoke":
            assert "tool_used" in shell
            assert "operation" in shell
        elif case.name == "tool_llm_fc_mode":
            assert "messages_normalized" in expect
            assert "tool_schema_names" in expect
            assert "tool_calls_count" in shell


@pytest.mark.plugin_parity
@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMToolParityComparison:
    """Compare live LLMAgent / ToolAgent output to golden fixtures (§12.1)."""

    @pytest.mark.parametrize("fixture_path", _LLM_FIXTURES, ids=_LLM_FIXTURE_IDS)
    async def test_llm_messages_normalized(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize(
        "fixture_path", _TOOL_MESSAGES_FIXTURES, ids=_TOOL_MESSAGES_FIXTURE_IDS
    )
    async def test_tool_messages_and_schemas(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_plugin_state_keys=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _LLM_TOOL_FIXTURES, ids=_LLM_TOOL_FIXTURE_IDS)
    async def test_execute_task_response_shell(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _LLM_TOOL_FIXTURES, ids=_LLM_TOOL_FIXTURE_IDS)
    async def test_full_parity_capture(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_streaming_phases=False,
            check_plugin_state_keys=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"


@pytest.mark.plugin_parity
@pytest.mark.unit
class TestKnowledgeParityFixtures:
    """KnowledgeAwareAgent parity fixture skeleton (E-07)."""

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    def test_fixture_file_exists(self, fixture_path: Path) -> None:
        assert fixture_path.is_file()

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    def test_knowledge_fixture_has_expect_block(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        expect = case.expect
        assert expect
        assert "messages_normalized" in expect
        assert "tool_schema_names" in expect
        assert "execute_task_response" in expect
        assert "plugin_state_keys" in expect
        shell = expect["execute_task_response"]
        assert "success" in shell
        assert "output" in shell


@pytest.mark.plugin_parity
@pytest.mark.unit
@pytest.mark.asyncio
class TestKnowledgeParityComparison:
    """Compare live KnowledgeAwareAgent output to golden fixtures (E-07)."""

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    async def test_knowledge_messages_normalized(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    async def test_knowledge_plugin_state_keys(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_tool_schemas=False,
            check_execute_response=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    async def test_knowledge_execute_task_response_shell(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_messages=False,
            check_tool_schemas=False,
            check_plugin_state_keys=False,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"

    @pytest.mark.parametrize("fixture_path", _KNOWLEDGE_FIXTURES, ids=_KNOWLEDGE_FIXTURE_IDS)
    async def test_full_parity_capture(self, fixture_path: Path) -> None:
        case = load_parity_fixture(fixture_path)
        got = await capture_parity_case(case)
        mismatches = compare_parity_expect(
            case.expect,
            got,
            check_streaming_phases=False,
        )
        assert mismatches == [], f"mismatch in {mismatches} for {case.name}"


@pytest.mark.plugin_parity
@pytest.mark.unit
def test_default_fixtures_dir_points_at_repo_fixtures() -> None:
    root = default_fixtures_dir()
    assert root.is_dir()
    assert (root / "hybrid_baseline.yaml").is_file()
    assert len(list_parity_fixtures(root)) == 5
    assert len(list_llm_parity_fixtures(root)) == 2
    assert len(list_tool_parity_fixtures(root)) == 2
    assert len(list_all_parity_fixtures(root)) == 11
    assert len(list_knowledge_parity_fixtures(root)) == 2
