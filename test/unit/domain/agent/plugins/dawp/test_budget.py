"""
Unit tests for aiecs/domain/agent/plugins/dawp/budget.py (D1-01).

Covers:
- TaskIterationBudget.remaining (never negative)
- TaskIterationBudget.is_exhausted
- TaskIterationBudget.consume (main loop and nested)
- TaskIterationBudget.allocate_for_step (step_cap / default_cap / None combos)
- Shared budget exhaustion with limit=6 (D5 scenario)
- PLUGIN_STATE_KEY constant
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.budget import PLUGIN_STATE_KEY, TaskIterationBudget


# ---------------------------------------------------------------------------
# PLUGIN_STATE_KEY
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plugin_state_key():
    assert PLUGIN_STATE_KEY == "task.iteration_budget"


# ---------------------------------------------------------------------------
# Basic construction and remaining
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaskIterationBudgetBasics:
    def test_initial_remaining_equals_limit(self):
        b = TaskIterationBudget(limit=10)
        assert b.remaining == 10

    def test_initial_consumed_zero(self):
        b = TaskIterationBudget(limit=10)
        assert b.consumed == 0

    def test_remaining_after_consume(self):
        b = TaskIterationBudget(limit=10)
        b.consume(3)
        assert b.remaining == 7

    def test_remaining_never_negative(self):
        b = TaskIterationBudget(limit=3)
        b.consume(3)
        b.consume(5)  # over-consume
        assert b.remaining == 0

    def test_is_exhausted_false_initially(self):
        b = TaskIterationBudget(limit=6)
        assert b.is_exhausted is False

    def test_is_exhausted_true_when_zero(self):
        b = TaskIterationBudget(limit=6)
        b.consume(6)
        assert b.is_exhausted is True

    def test_is_exhausted_true_when_over_consumed(self):
        b = TaskIterationBudget(limit=2)
        b.consume(10)
        assert b.is_exhausted is True

    def test_limit_zero_exhausted_immediately(self):
        b = TaskIterationBudget(limit=0)
        assert b.remaining == 0
        assert b.is_exhausted is True

    def test_consume_default_n_is_one(self):
        b = TaskIterationBudget(limit=5)
        b.consume()
        assert b.consumed == 1

    def test_consume_negative_raises(self):
        b = TaskIterationBudget(limit=5)
        with pytest.raises(ValueError, match="n >= 0"):
            b.consume(-1)

    def test_explicit_consumed_at_construction(self):
        b = TaskIterationBudget(limit=10, consumed=4)
        assert b.remaining == 6


# ---------------------------------------------------------------------------
# Shared budget exhaustion — limit=6 scenario (D5)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSharedBudgetLimit6:
    """Simulates a task with limit=6 shared across main loop and DAWP steps."""

    def test_main_loop_consumes_then_exhausted(self):
        b = TaskIterationBudget(limit=6)
        # Main loop: 6 iterations
        for _ in range(6):
            b.consume(1)
        assert b.remaining == 0
        assert b.is_exhausted is True

    def test_main_plus_dawp_shared(self):
        b = TaskIterationBudget(limit=6)
        # Main loop: 2 iterations
        b.consume(2)
        assert b.remaining == 4
        # DAWP step A: 2 iterations
        b.consume(2)
        assert b.remaining == 2
        # Main loop: 2 more
        b.consume(2)
        assert b.remaining == 0

    def test_seventh_iteration_would_be_zero_remaining(self):
        b = TaskIterationBudget(limit=6)
        b.consume(6)
        # Simulating "would 7th iteration fire?" — remaining is already 0
        assert b.remaining == 0
        # allocate_for_step also returns 0 → no step starts
        assert b.allocate_for_step(None, None) == 0

    def test_dawp_pre_main_plus_main_plus_trigger(self):
        """§4.4 example: pre_main DAWP + main iterations + trigger DAWP."""
        b = TaskIterationBudget(limit=10)
        # pre_main DAWP: 2 iterations
        b.consume(2)
        assert b.remaining == 8
        # main loop 0–2: 3 iterations
        b.consume(3)
        assert b.remaining == 5
        # trigger DAWP: 2 Prompt × 2 iter = 4 iterations
        b.consume(4)
        assert b.remaining == 1
        # main iteration 3: 1 more
        b.consume(1)
        assert b.remaining == 0


# ---------------------------------------------------------------------------
# allocate_for_step
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAllocateForStep:
    def test_no_caps_returns_remaining(self):
        b = TaskIterationBudget(limit=6)
        b.consume(2)
        # remaining=4, no caps → 4
        assert b.allocate_for_step(None, None) == 4

    def test_step_cap_below_remaining(self):
        b = TaskIterationBudget(limit=10)
        # remaining=10, step_cap=4 → 4
        assert b.allocate_for_step(step_cap=4) == 4

    def test_step_cap_above_remaining(self):
        b = TaskIterationBudget(limit=3)
        # remaining=3, step_cap=10 → 3
        assert b.allocate_for_step(step_cap=10) == 3

    def test_step_cap_equals_remaining(self):
        b = TaskIterationBudget(limit=5)
        assert b.allocate_for_step(step_cap=5) == 5

    def test_default_cap_used_when_step_cap_none(self):
        b = TaskIterationBudget(limit=10)
        # remaining=10, step_cap=None, default_cap=3 → 3
        assert b.allocate_for_step(step_cap=None, default_cap=3) == 3

    def test_step_cap_overrides_default_cap(self):
        b = TaskIterationBudget(limit=10)
        # step_cap=2 wins over default_cap=6 → 2
        assert b.allocate_for_step(step_cap=2, default_cap=6) == 2

    def test_default_cap_capped_by_remaining(self):
        b = TaskIterationBudget(limit=5)
        b.consume(3)  # remaining=2
        # default_cap=6 but remaining=2 → 2
        assert b.allocate_for_step(step_cap=None, default_cap=6) == 2

    def test_zero_remaining_always_zero(self):
        b = TaskIterationBudget(limit=3)
        b.consume(3)
        assert b.allocate_for_step(step_cap=4, default_cap=4) == 0
        assert b.allocate_for_step(step_cap=None, default_cap=None) == 0

    def test_step_cap_zero(self):
        b = TaskIterationBudget(limit=10)
        assert b.allocate_for_step(step_cap=0) == 0

    def test_default_cap_none_and_step_cap_none_returns_full_remaining(self):
        b = TaskIterationBudget(limit=8)
        b.consume(3)
        assert b.allocate_for_step(None) == 5
