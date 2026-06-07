# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
TaskIterationBudget — shared iteration pool for main loop and all DAWP steps (§4.4, D5).

One budget per ``execute_task`` / ``execute_task_streaming`` call.  Every completed
LLM+tool round — whether in the main loop **or** inside a DAWP step's mini-loop —
calls ``consume(1)``.  When ``remaining == 0`` no further LLM calls are issued.

Storage key: ``plugin_state["task.iteration_budget"]``.

``allocate_for_step`` computes the actual iteration cap for a single DAWP Prompt step:
  min(step_cap, remaining)  — honouring ``max_iterations_per_prompt`` without granting
  an independent quota (D5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

PLUGIN_STATE_KEY = "task.iteration_budget"


@dataclass
class TaskIterationBudget:
    """
    Shared iteration budget for a single agent task execution (§4.4, D5).

    Attributes:
        limit:    Total iteration allowance fixed at task start.
        consumed: Iterations consumed so far across main loop and all DAWP steps.
    """

    limit: int
    consumed: int = field(default=0)

    @property
    def remaining(self) -> int:
        """Iterations still available; never negative."""
        return max(0, self.limit - self.consumed)

    @property
    def is_exhausted(self) -> bool:
        """True when no iterations remain."""
        return self.remaining == 0

    def allocate_for_step(
        self,
        step_cap: int | None,
        default_cap: int | None = None,
    ) -> int:
        """
        Actual iteration cap for a single DAWP Prompt step mini-loop (§4.4).

        ``step_cap`` is the per-prompt declaration (``max_iterations_per_prompt``
        from the front matter or activation).  ``default_cap`` is the global
        fallback from plugin / agent config.  Returns ``min(effective_cap, remaining)``
        so a step can never exceed the remaining shared budget.

        Args:
            step_cap:    Per-step iteration cap; takes priority over ``default_cap``.
            default_cap: Fallback cap when ``step_cap`` is ``None``.

        Returns:
            Effective iteration limit for this step; 0 when budget is exhausted.
        """
        cap = step_cap if step_cap is not None else default_cap
        if cap is None:
            return self.remaining
        return min(cap, self.remaining)

    def consume(self, n: int = 1) -> None:
        """
        Record that ``n`` iterations have been consumed.

        Args:
            n: Number of iterations to deduct (default 1).

        Raises:
            ValueError: If ``n`` is negative.
        """
        if n < 0:
            raise ValueError(f"consume() requires n >= 0, got {n!r}")
        self.consumed += n
