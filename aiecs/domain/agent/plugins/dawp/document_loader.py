# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
document_loader: compile ``*.dawp.md`` source into :class:`DAWPWorkflow` (§5.0.2, §6.0.2.1).

Parsing pipeline
----------------
1. **Front matter** — standard ``---`` or ``<!-- Metadata … -->``-wrapped ``---`` block.
2. **Metadata & Activation** — ``name``, ``placement``, ``dawp_trigger``, scheduling fields.
3. **Instruction** — ``## Instruction:`` section body → ``spec.instruction``.
4. **Contract** — ``## Contract`` → ``### Action`` + both Marker headings.
5. **Prompt steps** — ``<Prompt N>…</Prompt N>`` blocks → ``steps[]``.
6. **Appendix** — ``## Appendix`` to EOF → ``spec.appendix`` (not a step).

Error contract
--------------
All parse failures raise :class:`~aiecs.domain.agent.plugins.dawp.schema.DawpDocumentError`
with ``path`` and ``line`` (when determinable).  Rejected placements (``after_response_index``,
``on_tool_result_trigger``) always include the source line number.

Dynamic workflow limits (§4.6, D11)
------------------------------------
When ``dynamic_workflow_limits`` is provided :func:`compile` enforces hard caps
**before** returning the workflow:

- ``max_document_bytes`` — byte size of the raw source (checked first, before parsing).
- ``max_prompts`` — maximum number of ``<Prompt N>`` steps.
- ``max_contract_action_chars`` — maximum length of the Contract Action text.
- ``max_iterations_per_prompt`` — per-step iteration cap; applied as
  ``min(declared, limit)`` (or just ``limit`` when the step has no explicit cap).

``require_remaining_budget`` is intentionally **not** checked here; that guard
lives in the ``dawp_start`` handler which has access to the live budget object.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .schema import (
    Activation,
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpDocumentError,
    MarkerCompletion,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
    WorkflowMetadata,
    WorkflowSpec,
)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Comment-wrapped front matter:
#   <!-- Metadata … -->
#   ---
#   …yaml…
#   ---
#   <!-- Metadata … -->
_COMMENT_FM_RE = re.compile(
    r"<!--.*?Metadata.*?-->\s*\n---\s*\n(.*?)\n---\s*\n[^\n]*<!--.*?Metadata.*?-->",
    re.DOTALL | re.IGNORECASE,
)

# Standard front matter at start of file: --- … ---
_STANDARD_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

# <Prompt N>…</Prompt N> blocks (DOTALL so content can span lines)
_PROMPT_BLOCK_RE = re.compile(r"<Prompt\s+(\d+)>(.*?)</Prompt\s+\1>", re.DOTALL)

# First ### heading inside a prompt block (for step id)
_H3_RE = re.compile(r"^###\s+(.+?)$", re.MULTILINE)

# Marker token in backticks on a heading line: `<TOKEN>`
_MARKER_IN_HEADING_RE = re.compile(r"`(<[^`]+>)`")

# Rejected placement types (removed in v2.3, §4.2)
_REJECTED_PLACEMENTS = frozenset({"after_response_index", "on_tool_result_trigger"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _line_of(source: str, pos: int) -> int:
    """Return 1-based line number for character position ``pos`` in ``source``."""
    return source[:pos].count("\n") + 1


def _find_placement_line(source: str, placement_value: str) -> int | None:
    """Return the 1-based line number where ``placement: <value>`` appears, or ``None``."""
    m = re.search(
        rf"^\s*placement\s*:\s*{re.escape(placement_value)}\s*$",
        source,
        re.MULTILINE,
    )
    return _line_of(source, m.start()) if m else None


def _title_to_slug(title: str) -> str:
    """Convert a ``### Heading`` title to a kebab-case slug for ``DAWPStep.id``."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().strip())
    return slug.strip("-") or "step"


def _parse_front_matter(source: str, *, path: str | None) -> tuple[dict[str, Any], str]:
    """Extract YAML front matter and return ``(fm_dict, body)``.

    Supports two front-matter formats (§5.0.2):
    - Standard ``---`` delimited block at the start of the file.
    - ``<!-- Metadata … -->``-wrapped ``---`` block (used by author templates).

    The front matter YAML is parsed with ``yaml.safe_load``; the returned body
    is the source text *after* the front-matter block.
    """
    # Try comment-wrapped format first (dawp-example / ooda format)
    m = _COMMENT_FM_RE.search(source)
    if m:
        fm_text = m.group(1)
        body = source[m.end() :]
    else:
        # Fall back to standard front matter
        m = _STANDARD_FM_RE.match(source)
        if m:
            fm_text = m.group(1)
            body = source[m.end() :]
        else:
            fm_text = ""
            body = source

    try:
        fm: dict[str, Any] = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise DawpDocumentError(f"front matter YAML parse error: {exc}", path=path) from exc

    if not isinstance(fm, dict):
        raise DawpDocumentError("front matter must be a YAML mapping", path=path)

    return fm, body


def _build_metadata_and_activations(
    fm: dict[str, Any],
    *,
    path: str | None,
    source: str,
) -> tuple[WorkflowMetadata, list[Activation]]:
    """Build :class:`WorkflowMetadata` and ``activations`` list from front-matter dict."""
    # --- name (required) ---
    raw_name = fm.get("name") or fm.get("Name")
    if not raw_name:
        raise DawpDocumentError("front matter missing 'name' field", path=path)
    name = str(raw_name).strip()

    # --- trigger_hint (docs only; 'trigger' / 'Trigger conditions' → trigger_hint) ---
    raw_hint = fm.get("trigger_hint") or fm.get("trigger") or fm.get("Trigger conditions")
    trigger_hint = str(raw_hint).strip() if raw_hint else None

    metadata = WorkflowMetadata(name=name, trigger_hint=trigger_hint)

    # --- placement ---
    placement_str = str(fm.get("placement", "pre_main_loop")).strip()

    if placement_str in _REJECTED_PLACEMENTS:
        line = _find_placement_line(source, placement_str)
        raise DawpDocumentError(
            f"placement '{placement_str}' is not supported (removed in v2.3); " "use 'on_response_trigger' instead",
            path=path,
            line=line,
        )

    resolved_placement: OnResponseTriggerPlacement | PreMainLoopPlacement
    if placement_str == "on_response_trigger":
        raw_trigger = fm.get("dawp_trigger")
        if not raw_trigger:
            raise DawpDocumentError(
                "placement 'on_response_trigger' requires 'dawp_trigger' field",
                path=path,
            )
        trigger_once = bool(fm.get("trigger_once", True))
        try:
            resolved_placement = OnResponseTriggerPlacement(
                dawp_trigger=str(raw_trigger).strip(),
                trigger_once=trigger_once,
            )
        except ValidationError as exc:
            raise DawpDocumentError(
                f"invalid dawp_trigger: {exc}",
                path=path,
            ) from exc

    elif placement_str == "pre_main_loop":
        resolved_placement = PreMainLoopPlacement()

    else:
        raise DawpDocumentError(
            f"unknown placement '{placement_str}'; " "valid values: pre_main_loop, on_response_trigger",
            path=path,
        )

    # --- scheduling options ---
    raw_trigger_instr = fm.get("trigger_instruction")
    trigger_instruction = str(raw_trigger_instr).strip() if raw_trigger_instr else None

    raw_merge_back = fm.get("merge_back", "append")
    merge_back = str(raw_merge_back).strip() if raw_merge_back else "append"

    raw_max_iter = fm.get("max_iterations_per_prompt")
    max_iterations_per_prompt = int(raw_max_iter) if raw_max_iter is not None else None

    try:
        activation = Activation(
            placement=resolved_placement,
            trigger_instruction=trigger_instruction,
            merge_back=merge_back,  # type: ignore[arg-type]
            max_iterations_per_prompt=max_iterations_per_prompt,
        )
    except ValidationError as exc:
        raise DawpDocumentError(
            f"invalid activation options: {exc}",
            path=path,
        ) from exc

    return metadata, [activation]


def _extract_section_text(body: str, title_pattern: str) -> str | None:
    """Return the text content under a ``## <title>`` section, or ``None`` if absent.

    The section ends at the next ``## `` heading or EOF.
    ``title_pattern`` is a regex fragment matched against the heading title (colon optional).
    """
    heading_re = re.compile(
        rf"^##\s+{title_pattern}:?\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    m = heading_re.search(body)
    if not m:
        return None
    content_start = m.end()
    next_h2 = re.search(r"^##\s+", body[content_start:], re.MULTILINE)
    content_end = content_start + next_h2.start() if next_h2 else len(body)
    return body[content_start:content_end].strip()


def _extract_appendix(body: str) -> str:
    """Return text from ``## Appendix`` to EOF (§5.0.1); empty string if absent."""
    m = re.search(r"^##\s+Appendix\s*$", body, re.MULTILINE | re.IGNORECASE)
    return body[m.end() :].strip() if m else ""


def _parse_contract_section(
    contract_text: str,
    *,
    path: str | None,
    source: str,
) -> Contract:
    """Parse ``## Contract`` body text into a :class:`Contract`.

    Looks for ``### Action``, ``### Prompt Completion Marker: `<TOKEN>```,
    and ``### DAWP Completion Marker: `<TOKEN>``` (§5.0.2 grammar).
    Both Marker headings are required; ``### Action`` content defaults to ``""`` if absent.
    """
    # Locate marker headings
    pm_m = re.search(
        r"^###\s+Prompt\s+Completion\s+Marker\s*:",
        contract_text,
        re.MULTILINE | re.IGNORECASE,
    )
    dm_m = re.search(
        r"^###\s+DAWP\s+Completion\s+Marker\s*:",
        contract_text,
        re.MULTILINE | re.IGNORECASE,
    )

    if not pm_m:
        line = _line_of(source, source.find("## Contract")) if "## Contract" in source else None
        raise DawpDocumentError(
            "missing '### Prompt Completion Marker: `<TOKEN>`' in Contract section",
            path=path,
            line=line,
        )
    if not dm_m:
        raise DawpDocumentError(
            "missing '### DAWP Completion Marker: `<TOKEN>`' in Contract section",
            path=path,
        )

    # Extract token from the heading line (same line as the heading)
    pm_line_end = contract_text.find("\n", pm_m.start())
    dm_line_end = contract_text.find("\n", dm_m.start())
    pm_heading_line = contract_text[pm_m.start() : pm_line_end if pm_line_end != -1 else None]
    dm_heading_line = contract_text[dm_m.start() : dm_line_end if dm_line_end != -1 else None]

    pm_token_m = _MARKER_IN_HEADING_RE.search(pm_heading_line)
    dm_token_m = _MARKER_IN_HEADING_RE.search(dm_heading_line)

    if not pm_token_m:
        raise DawpDocumentError(
            "Prompt Completion Marker heading must include token in backticks, e.g. `<STEP_DONE>`",
            path=path,
        )
    if not dm_token_m:
        raise DawpDocumentError(
            "DAWP Completion Marker heading must include token in backticks, e.g. `<DAWP_HANDOFF>`",
            path=path,
        )

    prompt_marker = pm_token_m.group(1)
    dawp_marker = dm_token_m.group(1)

    # Action text: between ### Action and ### Prompt Completion Marker
    action_text = ""
    action_m = re.search(r"^###\s+Action\s*$", contract_text, re.MULTILINE | re.IGNORECASE)
    if action_m:
        action_text = contract_text[action_m.end() : pm_m.start()].strip()

    try:
        return Contract(action=action_text, prompt_marker=prompt_marker, dawp_marker=dawp_marker)
    except ValidationError as exc:
        raise DawpDocumentError(
            f"invalid Contract markers: {exc}",
            path=path,
        ) from exc


def _parse_steps(body: str, contract: Contract, *, path: str | None) -> list[DAWPStep]:
    """Extract ``<Prompt N>…</Prompt N>`` blocks and compile into :class:`DAWPStep` list.

    Steps are sorted by prompt number N.  ``is_last`` is set only on the final step.
    ``step.id`` is derived from the first ``### Heading`` inside the block (slugified),
    or falls back to ``prompt-{N}``.
    """
    matches = list(_PROMPT_BLOCK_RE.finditer(body))
    if not matches:
        return []

    # Sort by prompt number; keep (number, content) pairs
    numbered = sorted(
        ((int(m.group(1)), m.group(2)) for m in matches),
        key=lambda t: t[0],
    )
    last_idx = len(numbered) - 1

    steps: list[DAWPStep] = []
    for i, (n, content) in enumerate(numbered):
        instruction = content.strip()

        h3 = _H3_RE.search(content)
        step_id = _title_to_slug(h3.group(1)) if h3 else f"prompt-{n}"

        completion = MarkerCompletion(
            prompt_marker=contract.prompt_marker,
            dawp_marker=contract.dawp_marker,
            is_last=(i == last_idx),
        )
        steps.append(DAWPStep(id=step_id, instruction=instruction, completion=completion))

    return steps


# ---------------------------------------------------------------------------
# Limits helpers (§4.6, D11)
# ---------------------------------------------------------------------------

# Default values matching the design-doc specification
_DEFAULT_LIMITS: dict[str, Any] = {
    "max_prompts": 12,
    "max_iterations_per_prompt": 6,
    "max_contract_action_chars": 8000,
    "max_document_bytes": 256_000,
    "require_remaining_budget": 3,
}


def _check_bytes_limit(source: str, limits: dict[str, Any], *, path: str | None) -> None:
    """Raise :class:`DawpDocumentError` if *source* exceeds ``max_document_bytes``."""
    cap = int(limits.get("max_document_bytes", _DEFAULT_LIMITS["max_document_bytes"]))
    size = len(source.encode("utf-8"))
    if size > cap:
        raise DawpDocumentError(
            f"document_content exceeds max_document_bytes={cap} (got {size})",
            path=path,
        )


def _apply_dynamic_limits(
    workflow: DAWPWorkflow,
    limits: dict[str, Any],
    *,
    path: str | None,
) -> DAWPWorkflow:
    """Enforce post-parse limits on *workflow*; return (possibly mutated) workflow.

    Checks ``max_prompts`` and ``max_contract_action_chars``; applies
    ``max_iterations_per_prompt`` cap to each step in place.

    Raises:
        DawpDocumentError: When ``max_prompts`` or ``max_contract_action_chars`` exceeded.
    """
    max_prompts = int(limits.get("max_prompts", _DEFAULT_LIMITS["max_prompts"]))
    if len(workflow.steps) > max_prompts:
        raise DawpDocumentError(
            f"workflow has {len(workflow.steps)} prompts which exceeds max_prompts={max_prompts}",
            path=path,
        )

    max_action_chars = int(limits.get("max_contract_action_chars", _DEFAULT_LIMITS["max_contract_action_chars"]))
    action_len = len(workflow.spec.contract.action)
    if action_len > max_action_chars:
        raise DawpDocumentError(
            f"Contract Action length {action_len} exceeds max_contract_action_chars={max_action_chars}",
            path=path,
        )

    max_iter = int(limits.get("max_iterations_per_prompt", _DEFAULT_LIMITS["max_iterations_per_prompt"]))
    # Apply iteration cap to each step: min(declared, limit), or just limit when unset
    for step in workflow.steps:
        if step.max_iterations is None:
            step.max_iterations = max_iter
        else:
            step.max_iterations = min(step.max_iterations, max_iter)

    return workflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compile(  # noqa: A001  (shadows builtin; intentional for this domain)
    source: str,
    *,
    path: str | None = None,
    dynamic_workflow_limits: dict[str, Any] | None = None,
) -> DAWPWorkflow:
    """Compile ``*.dawp.md`` source text into a :class:`DAWPWorkflow`.

    Args:
        source:                  Full text of a ``*.dawp.md`` document.
        path:                    Optional file path for error messages (``DawpDocumentError.path``).
        dynamic_workflow_limits: Optional limits dict (§4.6, D11); enforced when compiling
                                 dynamic ``document_content`` via ``dawp_start``.

    Returns:
        Compiled :class:`DAWPWorkflow` ready for scheduling and execution.

    Raises:
        DawpDocumentError: On any parse or validation failure.
    """
    # 0. Byte-size limit (before parsing — fast and cheap)
    if dynamic_workflow_limits is not None:
        _check_bytes_limit(source, dynamic_workflow_limits, path=path)

    # 1. Front matter
    fm, body = _parse_front_matter(source, path=path)

    # 2. Metadata + activation
    metadata, activations = _build_metadata_and_activations(fm, path=path, source=source)

    # 3. Instruction section
    instruction = _extract_section_text(body, r"Instruction") or ""

    # 4. Contract section (required)
    contract_text = _extract_section_text(body, r"Contract")
    if not contract_text:
        raise DawpDocumentError("missing '## Contract' section", path=path)
    contract = _parse_contract_section(contract_text, path=path, source=source)

    # 5. Prompt steps
    steps = _parse_steps(body, contract, path=path)

    # 6. Appendix (not a step)
    appendix = _extract_appendix(body)

    spec = WorkflowSpec(instruction=instruction, contract=contract, appendix=appendix)
    workflow = DAWPWorkflow(metadata=metadata, spec=spec, steps=steps, activations=activations)

    # 7. Post-parse limits enforcement (§4.6, D11 — dynamic only)
    if dynamic_workflow_limits is not None:
        _apply_dynamic_limits(workflow, dynamic_workflow_limits, path=path)

    return workflow


def compile_file(
    path: str | Path,
    *,
    dynamic_workflow_limits: dict[str, Any] | None = None,
) -> DAWPWorkflow:
    """Convenience wrapper: read ``path`` and compile via :func:`compile`.

    Args:
        path:                    Path to a ``*.dawp.md`` file.
        dynamic_workflow_limits: Passed through to :func:`compile`.

    Raises:
        DawpDocumentError: On any parse or validation failure.
        OSError:           If the file cannot be read.
    """
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    return compile(source, path=str(p), dynamic_workflow_limits=dynamic_workflow_limits)
