"""P0-02: M-D.5 pytest gate markers registered (--strict-markers smoke)."""

from __future__ import annotations

import pytest


@pytest.mark.gate_p0
def test_gate_p0_marker_registered() -> None:
    pass


@pytest.mark.gate_p1
def test_gate_p1_marker_registered() -> None:
    pass


@pytest.mark.gate_p2
def test_gate_p2_marker_registered() -> None:
    pass


@pytest.mark.gate_p3
def test_gate_p3_marker_registered() -> None:
    pass


@pytest.mark.gate_p4
def test_gate_p4_marker_registered() -> None:
    pass


@pytest.mark.gate_p5
def test_gate_p5_marker_registered() -> None:
    pass
