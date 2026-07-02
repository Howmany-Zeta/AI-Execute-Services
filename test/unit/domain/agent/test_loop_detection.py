"""
Unit tests for loop detection signals (A-7).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.loop_detection import LoopDetectionConfig, LoopDetectionService


@pytest.mark.unit
class TestLoopDetectionService:
    def test_repeated_triple_fires_at_threshold(self) -> None:
        svc = LoopDetectionService(
            LoopDetectionConfig(enabled=True, window_size=10, repeat_threshold=3)
        )
        args = {"q": "x"}
        result = {"status": "ok"}
        signals = []
        for _ in range(3):
            signal = svc.record_tool_call(tool_name="search", args=args, result=result)
            if signal is not None:
                signals.append(signal)

        assert len(signals) == 1
        assert signals[0].repeated_triple_count == 3
        assert signals[0].effective_cycles == 1
        assert len(signals[0].last_triples) == 3

    def test_different_args_do_not_accumulate(self) -> None:
        svc = LoopDetectionService(
            LoopDetectionConfig(enabled=True, window_size=10, repeat_threshold=3)
        )
        for i in range(3):
            signal = svc.record_tool_call(tool_name="search", args={"q": i}, result={"ok": True})
        assert signal is None
        assert svc.get_signal().repeated_triple_count == 1

    def test_disabled_has_negligible_state(self) -> None:
        svc = LoopDetectionService(LoopDetectionConfig(enabled=False))
        assert svc.record_tool_call(tool_name="t", args={}, result={}) is None
        assert svc.get_signal().repeated_triple_count == 0

    def test_idle_iterations_tracked(self) -> None:
        svc = LoopDetectionService(LoopDetectionConfig(enabled=True))
        svc.record_iteration(had_tool_call=False)
        svc.record_iteration(had_tool_call=False)
        assert svc.get_signal().idle_iterations == 2
        svc.record_tool_call(tool_name="t", args={}, result={})
        assert svc.get_signal().idle_iterations == 0
