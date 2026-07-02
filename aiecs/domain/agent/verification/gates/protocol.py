# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""DeterministicGate protocol (A-4)."""

from __future__ import annotations

from typing import Any, Protocol, Union, runtime_checkable

from aiecs.domain.agent.models import AgentGoal

from .models import GateScore


@runtime_checkable
class DeterministicGate(Protocol):
    """Pure-code pre-exit gate with zero LLM dependency."""

    kind: str

    def score(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any], None],
        result: dict[str, Any],
        work_snapshot: dict[str, Any],
    ) -> GateScore:
        """Return deterministic gate score for the deliverable snapshot."""
        ...
