# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP marker and response-trigger detection utilities (§6.0.2, §6.0.2.1, §6.0.2.2).

Public API
----------
- :func:`validate_marker`         — compile-time format/uniqueness check (§6.0.2.1)
- :func:`_visible_assistant_text` — strip ``<thinking>…</thinking>`` from raw LLM output
- :func:`iter_scannable_lines`    — yield scannable lines (skip fences & blockquotes)
- :func:`marker_detected`         — whole-line exact match on scannable lines
- :func:`prompt_step_complete`    — state-machine result for one DAWP step iteration
- :func:`matches_response_trigger`— ``on_response_trigger`` check with ``trigger_once`` guard

Detection pipeline
------------------
::

    raw_assistant_text
        │
        ▼
    _visible_assistant_text()   ← strips <thinking> blocks
        │
        ▼
    iter_scannable_lines()      ← skips fenced code & blockquotes
        │
        ▼
    marker_detected()           ← whole-line equality (no substring match)

Rule references (§6.0.2, §6.0.2.2):
- Fenced code blocks (````` ``` `````) — ``inside_fence`` state machine; lines inside skipped.
- Blockquote lines (``>`` prefix) — skipped entirely.
- ``<thinking>`` blocks — stripped by ``_visible_assistant_text`` before line scan.
- Indented code blocks (4-space/tab) — optional; v2.5.1 minimum is fence + blockquote only.
"""

from __future__ import annotations

import re
from typing import Any, Iterator, Literal

_MARKER_RE = re.compile(r"^<[A-Z0-9_]+>$")
_THINKING_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------------------
# Compile-time validation
# ---------------------------------------------------------------------------


def validate_marker(name: str, value: str, *, other: str | None = None) -> None:
    """Validate a DAWP marker / trigger token at compile time (§6.0.2.1).

    Args:
        name:  Field name for error messages (e.g. ``"prompt_marker"``).
        value: Token to validate (e.g. ``"<STEP_DONE>"``).
        other: When given, ``value`` must differ from ``other`` (prevents same markers).

    Raises:
        ValueError: On format, length, or uniqueness violation.
    """
    if len(value) > 25:
        raise ValueError(f"{name} exceeds 25 chars: {value!r}")
    if not _MARKER_RE.match(value):
        raise ValueError(f"{name} must match ^<[A-Z0-9_]+>$: {value!r}")
    if other is not None and value == other:
        raise ValueError("prompt_marker and dawp_marker must differ")


# ---------------------------------------------------------------------------
# Text visibility
# ---------------------------------------------------------------------------


def _visible_assistant_text(raw: str) -> str:
    """Strip all ``<thinking>…</thinking>`` blocks (case-insensitive, DOTALL).

    The remaining text is the assistant's *visible* output — the only part that
    is checked for Markers and ``on_response_trigger`` tokens (§6.0.2).

    Multiple ``<thinking>`` blocks are all removed; nested tags are handled
    correctly by the non-greedy ``.*?`` pattern.
    """
    return _THINKING_RE.sub("", raw)


# ---------------------------------------------------------------------------
# Scannable line iterator
# ---------------------------------------------------------------------------


def iter_scannable_lines(visible_text: str) -> Iterator[str]:
    """Yield stripped lines from *visible_text* that are eligible for marker detection.

    Skipped regions (§6.0.2.2):
    - Lines inside fenced code blocks (`` ``` … ``` ``).
    - Lines whose first non-whitespace character is ``>`` (Markdown blockquote).

    The caller is responsible for passing text that has already had ``<thinking>``
    blocks removed via :func:`_visible_assistant_text`.

    Yields:
        ``line.strip()`` for each scannable line (empty strings included when the
        original line was blank but scannable).
    """
    inside_fence = False
    for line in visible_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            inside_fence = not inside_fence
            continue
        if inside_fence:
            continue
        if line.lstrip().startswith(">"):
            continue
        yield stripped


# ---------------------------------------------------------------------------
# Marker detection
# ---------------------------------------------------------------------------


def marker_detected(visible_text: str, marker: str) -> bool:
    """Return ``True`` when any scannable line equals *marker* exactly (§6.0.2).

    Whole-line exact match only — substring containment and regex matching are
    explicitly prohibited (§6.0.2.1).

    Args:
        visible_text: Text with ``<thinking>`` already stripped.
        marker:       Token to search for (e.g. ``"<STEP_DONE>"``).
    """
    return any(line == marker for line in iter_scannable_lines(visible_text))


# ---------------------------------------------------------------------------
# Step completion state machine
# ---------------------------------------------------------------------------


def prompt_step_complete(
    assistant_text: str,
    *,
    prompt_marker: str,
    dawp_marker: str,
    is_last: bool,
) -> Literal["prompt_done", "dawp_done", "continue"]:
    """Evaluate one DAWP step iteration to determine the next state (§6.0.2).

    Args:
        assistant_text: Raw LLM output (``<thinking>`` blocks not yet stripped).
        prompt_marker:  Non-final step completion token.
        dawp_marker:    Final run completion token.
        is_last:        ``True`` when this is the last ``DAWPStep`` in the run.

    Returns:
        - ``"prompt_done"``  — non-last step saw ``prompt_marker``; advance to next step.
        - ``"dawp_done"``    — ``dawp_marker`` detected; end the DAWP run.
        - ``"continue"``     — neither marker seen; run another iteration of this step.

    Edge cases:
        - **Last step, only ``prompt_marker`` seen**: ``"continue"`` — treated as mis-labelled
          output; the step must produce ``dawp_marker`` to complete (§6.0.2 末步规则).
        - **Non-last step, ``dawp_marker`` seen**: ``"dawp_done"`` — early run handoff allowed.
    """
    visible = _visible_assistant_text(assistant_text)

    if is_last:
        if marker_detected(visible, dawp_marker):
            return "dawp_done"
        # Last step: seeing only prompt_marker is a mis-label → keep running
        return "continue"

    # Non-last step
    if marker_detected(visible, prompt_marker):
        return "prompt_done"
    if marker_detected(visible, dawp_marker):
        # Early handoff: non-last step signals run completion
        return "dawp_done"
    return "continue"


# ---------------------------------------------------------------------------
# Response trigger matching
# ---------------------------------------------------------------------------


def matches_response_trigger(
    assistant_text: str,
    dawp_trigger: str,
    *,
    trigger_once: bool = True,
    plugin_state: dict[str, Any],
) -> bool:
    """Check whether *assistant_text* contains *dawp_trigger* on a scannable line (§4.2, D7).

    This is the runtime counterpart of the ``on_response_trigger`` placement.  The
    trigger is detected using the same :func:`iter_scannable_lines` pipeline as
    Marker detection (§6.0.2.2), so tokens inside code fences, blockquotes, or
    ``<thinking>`` blocks do **not** fire.

    Args:
        assistant_text: Raw LLM output for the current iteration.
        dawp_trigger:   Token to look for (e.g. ``"<START_OODA_REVIEW>"``).
        trigger_once:   When ``True`` (default), fire at most once per task; subsequent
                        calls return ``False`` after the first successful match.
        plugin_state:   Mutable ``AgentPluginContext.plugin_state`` dict; used to store
                        the ``"dawp.triggered.<token>"`` guard flag.

    Returns:
        ``True`` when the trigger is detected *and* (``trigger_once`` is ``False`` or the
        trigger has not fired yet in this task).
    """
    state_key = f"dawp.triggered.{dawp_trigger}"

    if trigger_once and plugin_state.get(state_key):
        return False

    visible = _visible_assistant_text(assistant_text)
    detected = marker_detected(visible, dawp_trigger)

    if detected and trigger_once:
        plugin_state[state_key] = True

    return detected
