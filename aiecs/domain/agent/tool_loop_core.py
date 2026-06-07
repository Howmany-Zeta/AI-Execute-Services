# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Shared types for HybridAgent tool-loop extraction (§8.4, DAWP v2.1 DAWP-1).

``HybridAgent._run_tool_loop_with_iteration_hooks`` and DAWP StepRunner
share the same LLM+tool iteration semantics; ``ON_ITERATION_*`` hooks use ``plugin_ctx``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class ToolLoopRunState:
    """Mutable accumulator for one tool-loop run."""

    steps: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls_count: int = 0
    total_tokens: int = 0
    last_outcome: Optional["ToolLoopIterationOutcome"] = None


@dataclass(frozen=True)
class ToolLoopIterationOutcome:
    """Result of a single tool-loop iteration (sync or streaming)."""

    kind: Literal["continue", "final", "stop_match", "max_iterations"]
    result: Optional[Dict[str, Any]] = None
