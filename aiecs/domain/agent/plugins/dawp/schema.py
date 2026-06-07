# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP schema models.

Defines the internal compiled representation of a DAWP workflow and supporting types:

- :class:`PreMainLoopPlacement` / :class:`OnResponseTriggerPlacement` — activation placement
- :class:`Placement` — discriminated union of the two placement types
- :class:`Contract` — per-workflow action prefix and Marker tokens
- :class:`MarkerCompletion` — step completion via marker detection
- :class:`DAWPStep` — single Prompt N step
- :class:`WorkflowMetadata` / :class:`WorkflowSpec` / :class:`DAWPWorkflow` — full workflow
- :class:`Activation` — compiled scheduling descriptor
- :class:`DawpPendingRun` — enqueued run awaiting drain
- :class:`DawpDocumentError` — compilation failure exception

References: CUSTOM_REASONING_PLUGIN_DESIGN.md §5.4, §6.1, §6.0.2.1.
Rejected placement types (v2.3+): ``after_response_index``, ``on_tool_result_trigger``.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_MARKER_RE = re.compile(r"^<[A-Z0-9_]+>$")


def _validate_marker_format(name: str, value: str) -> str:
    """Validate marker/trigger token: ^<[A-Z0-9_]+>$, total length ≤25 (§6.0.2.1)."""
    if len(value) > 25:
        raise ValueError(f"{name} exceeds 25 chars: {value!r}")
    if not _MARKER_RE.match(value):
        raise ValueError(f"{name} must match ^<[A-Z0-9_]+>$: {value!r}")
    return value


# ---------------------------------------------------------------------------
# Placement types  (D9 · v2.3+: only pre_main_loop | on_response_trigger)
# ---------------------------------------------------------------------------


class PreMainLoopPlacement(BaseModel):
    """Run DAWP before the main loop starts (§4.2)."""

    type: Literal["pre_main_loop"] = "pre_main_loop"


class OnResponseTriggerPlacement(BaseModel):
    """Run DAWP when the main-loop response contains ``dawp_trigger`` on a scannable line (§4.2, D7).

    ``dawp_trigger`` must follow the marker format ``^<[A-Z0-9_]+>$`` with total length ≤25.
    ``trigger_once`` (default ``True``) prevents re-activation after the first match.
    """

    type: Literal["on_response_trigger"] = "on_response_trigger"
    dawp_trigger: str
    trigger_once: bool = True

    @field_validator("dawp_trigger")
    @classmethod
    def _validate_trigger_format(cls, v: str) -> str:
        return _validate_marker_format("dawp_trigger", v)


Placement = Annotated[
    PreMainLoopPlacement | OnResponseTriggerPlacement,
    Field(discriminator="type"),
]
"""Discriminated union of valid placement types.

Passing ``type="after_response_index"`` or ``type="on_tool_result_trigger"`` raises
``ValidationError`` (removed in v2.3, §4.2).
"""


# ---------------------------------------------------------------------------
# Contract  (§6.0.2, §6.0.2.1)
# ---------------------------------------------------------------------------


class Contract(BaseModel):
    """DAWP workflow contract: per-step action prefix and completion marker tokens.

    ``prompt_marker`` and ``dawp_marker`` must differ, each match ``^<[A-Z0-9_]+>$``,
    and be ≤25 characters total (§6.0.2.1).
    """

    action: str
    prompt_marker: str
    dawp_marker: str

    @field_validator("prompt_marker")
    @classmethod
    def _validate_prompt_marker(cls, v: str) -> str:
        return _validate_marker_format("prompt_marker", v)

    @field_validator("dawp_marker")
    @classmethod
    def _validate_dawp_marker(cls, v: str) -> str:
        return _validate_marker_format("dawp_marker", v)

    @model_validator(mode="after")
    def _markers_must_differ(self) -> Contract:
        if self.prompt_marker == self.dawp_marker:
            raise ValueError("prompt_marker and dawp_marker must differ")
        return self


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------


class MarkerCompletion(BaseModel):
    """Step completion via marker detection; compiled default for ``*.dawp.md`` steps (§6.0, §7.1)."""

    type: Literal["marker"] = "marker"
    prompt_marker: str
    dawp_marker: str
    is_last: bool


class NoToolCallsCompletion(BaseModel):
    """Legacy completion: step succeeds when iteration has no tool calls (§7.2)."""

    type: Literal["no_tool_calls"] = "no_tool_calls"
    is_last: bool


StepCompletion = MarkerCompletion | NoToolCallsCompletion


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


class DAWPStep(BaseModel):
    """Single Prompt N step compiled from a ``<Prompt N>…</Prompt N>`` block (§5.0.1, §6.0)."""

    id: str
    instruction: str
    completion: StepCompletion
    max_iterations: int | None = None


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------


class Activation(BaseModel):
    """Compiled activation descriptor: placement + scheduling options (§4.2, §5.0.2)."""

    placement: Placement
    trigger_instruction: str | None = None
    merge_back: Literal["append", "inject_only"] = "append"
    max_iterations_per_prompt: int | None = None
    workflow_id: str | None = None


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class WorkflowMetadata(BaseModel):
    """Workflow identity parsed from front-matter (§5.0.2)."""

    name: str
    trigger_hint: str | None = None


class WorkflowSpec(BaseModel):
    """Parsed body of a ``*.dawp.md`` document: instruction, contract, and appendix (§5.0.1)."""

    instruction: str = ""
    contract: Contract
    appendix: str = ""


class DAWPWorkflow(BaseModel):
    """Compiled internal representation of a DAWP workflow (§6.1).

    Produced by ``document_loader`` from a ``*.dawp.md`` source.
    ``steps`` follow the ``<Prompt N>`` order; ``activations`` drive scheduling.
    """

    metadata: WorkflowMetadata
    spec: WorkflowSpec
    steps: list[DAWPStep]
    activations: list[Activation] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pending run record  (§5.4)
# ---------------------------------------------------------------------------


class DawpPendingRun(BaseModel):
    """Enqueued DAWP run record awaiting drain by HybridAgent (§5.4, §6.2).

    ``trigger`` is either ``"config"`` (developer-declared activation) or ``"tool"``
    (model called ``dawp_start``).
    ``drain_mode`` is ``"on_iteration_end"`` for config-path runs and ``"inline"``
    for tool-path runs (§4.1.2, §6.5).
    ``abort_main`` enables D3 abort-main mode: if the DAWP run fails (no DAWP Completion
    Marker seen), the entire task fails instead of silently continuing (§7, D3).
    Defaults to ``False`` (safe default; main loop always continues on DAWP failure).
    """

    trigger: Literal["config", "tool"]
    workflow_source: Literal["static", "dynamic"]
    workflow_id: str
    temp_document_path: str | None = None
    enqueued_at_iteration: int
    drain_mode: Literal["on_iteration_end", "inline"]
    merge_back: Literal["append", "inject_only"] = "append"
    config_placement: Literal["pre_main_loop", "on_response_trigger"] | None = None
    abort_main: bool = False


# ---------------------------------------------------------------------------
# Document error  (§5.0.2)
# ---------------------------------------------------------------------------


class DawpDocumentError(Exception):
    """Raised when a ``*.dawp.md`` document fails to compile (§5.0.2).

    Attributes:
        path:   Source file path (``None`` when compiling inline ``document_content``).
        line:   Approximate line number of the failure (``None`` when unknown).
        reason: Human-readable description of the compilation failure.
    """

    def __init__(self, reason: str, *, path: str | None = None, line: int | None = None) -> None:
        self.path = path
        self.line = line
        self.reason = reason

        location_parts: list[str] = []
        if path:
            location_parts.append(path)
        if line is not None:
            location_parts.append(str(line))
        prefix = ":".join(location_parts)
        message = f"{prefix}: {reason}" if prefix else reason
        super().__init__(message)


class DawpAbortMainError(RuntimeError):
    """Raised when a DAWP run fails and ``abort_main=True`` is set (D3, §7).

    This propagates from ``_drain_pending_dawp_runs`` through
    ``_tool_loop_streaming_with_plugins``, which catches it and yields a
    failure ``result`` event to end the task with ``success=False``.
    """

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"DAWP run for workflow '{workflow_id}' failed and abort_main=True (D3); " "terminating task.")
