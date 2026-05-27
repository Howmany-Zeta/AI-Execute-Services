# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Normalize HybridAgent outputs for plugin parity golden snapshots (§12.1).

Normalize rules (stable comparison for ``tests/fixtures/plugin_parity/*.yaml``):

1. **Volatile top-level response fields** — drop ``timestamp``, ``execution_time`` from
   ``execute_task`` shells before compare.
2. **Volatile dict keys (any depth)** — drop keys such as ``timestamp``, ``id``,
   ``request_id``, ``call_id``, ``tool_call_id`` (when non-deterministic), ``cache_hit``,
   ``cached_tokens``, and Anthropic-style ``cache_control`` blobs on messages.
3. **ISO timestamps in strings** — replace ``YYYY-MM-DDTHH:MM:SS…`` substrings with
   ``<timestamp>`` so embedded times do not fail diffs.
4. **JSON key order** — emit dicts with sorted keys at each level (``normalize_dict``).
5. **Message list order** — preserve list order for ``messages_normalized`` (system/user
   blocks must stay in the same sequence as production).
6. **String whitespace** — ``strip()`` each string; collapse runs of whitespace to a
   single space (newlines in multiline skill blocks are preserved as ``\\n``).
7. **LLMMessage** — map to ``{role, content, …}``; optional ``images`` / ``tool_calls``;
   tool function names kept, volatile call ids omitted from normalized tool_calls.
8. **Tool schemas** — ``normalize_tool_schema_names`` returns sorted function names only.
9. **Execute-task shell** — keep only §8.2 parity fields: ``success``, ``reason``,
   ``output``, ``reasoning_steps``, ``tool_calls_count``, ``iterations``.

Business plugin events and ``source_plugin`` payloads are not normalized here.
"""

from __future__ import annotations

import json
import re
from typing import Any

from aiecs.llm import LLMMessage

_VOLATILE_RESPONSE_KEYS = frozenset({"timestamp", "execution_time"})
_VOLATILE_DICT_KEYS = frozenset(
    {
        "timestamp",
        "execution_time",
        "id",
        "request_id",
        "call_id",
        "cache_hit",
        "cached_tokens",
        "cache_control",
    }
)
_ISO_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?")
_WHITESPACE_RUN_RE = re.compile(r"[ \t]+")
_VOLATILE_TOOL_CALL_KEYS = frozenset({"id"})


def _collapse_whitespace(value: str) -> str:
    """Strip ends; collapse horizontal runs; preserve newlines."""
    lines = [_WHITESPACE_RUN_RE.sub(" ", line.strip()) for line in value.split("\n")]
    return "\n".join(lines).strip()


def _strip_timestamps_in_string(value: str) -> str:
    return _ISO_TIMESTAMP_RE.sub("<timestamp>", value)


def normalize_value(value: Any) -> Any:
    """Recursively normalize a value for stable comparison."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _strip_timestamps_in_string(_collapse_whitespace(value))
    if isinstance(value, LLMMessage):
        return normalize_message(value)
    if isinstance(value, dict):
        return normalize_dict(value)
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    return _strip_timestamps_in_string(_collapse_whitespace(str(value)))


def normalize_dict(data: dict[str, Any], *, drop_volatile: bool = True) -> dict[str, Any]:
    """Normalize dict with stable key ordering."""
    normalized: dict[str, Any] = {}
    for key in sorted(data.keys()):
        if drop_volatile and key in _VOLATILE_DICT_KEYS:
            continue
        if drop_volatile and key in _VOLATILE_RESPONSE_KEYS:
            continue
        normalized[key] = normalize_value(data[key])
    return normalized


def _normalize_tool_calls(tool_calls: list[Any]) -> list[Any]:
    """Keep tool call shape but drop volatile ids."""
    out: list[Any] = []
    for call in tool_calls:
        if isinstance(call, dict):
            trimmed = {k: normalize_value(v) for k, v in call.items() if k not in _VOLATILE_TOOL_CALL_KEYS}
            if isinstance(trimmed.get("function"), dict):
                fn = dict(trimmed["function"])
                fn.pop("id", None)
                trimmed["function"] = normalize_dict(fn, drop_volatile=False)
            out.append(normalize_dict(trimmed, drop_volatile=False))
        else:
            out.append(normalize_value(call))
    return out


def normalize_message(message: LLMMessage) -> dict[str, Any]:
    """Normalize a single LLMMessage for fixture storage."""
    payload: dict[str, Any] = {
        "role": message.role,
        "content": normalize_value(message.content),
    }
    if message.images:
        payload["images"] = normalize_value(message.images)
    if message.tool_calls:
        payload["tool_calls"] = _normalize_tool_calls(message.tool_calls)
    if message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id
    return payload


def normalize_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Normalize message list preserving order."""
    return [normalize_message(msg) for msg in messages]


def normalize_tool_schema_names(schemas: list[dict[str, Any]]) -> list[str]:
    """Extract sorted tool function names from OpenAI-style schema dicts."""
    names: list[str] = []
    for schema in schemas:
        name = schema.get("name")
        if not name and isinstance(schema.get("function"), dict):
            name = schema["function"].get("name")
        if name:
            names.append(str(name))
    return sorted(names)


def normalize_plugin_state_keys(plugin_state: dict[str, Any]) -> list[str]:
    """Sorted plugin_state top-level keys for golden comparison."""
    return sorted(str(k) for k in plugin_state.keys())


def normalize_execute_task_response(
    response: dict[str, Any],
    *,
    extra_fields: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Normalize execute_task outer shell (§8.2).

    ``extra_fields`` adds agent-specific keys (e.g. ``tool_used`` for ToolAgent
    direct mode) used by LLM/Tool parity fixtures (P3-00).
    """
    allowed = {
        "success",
        "reason",
        "output",
        "reasoning_steps",
        "tool_calls_count",
        "iterations",
    }
    if extra_fields:
        allowed = allowed | extra_fields
    shell = {k: response[k] for k in allowed if k in response}
    return normalize_dict(shell)


def dumps_normalized(data: Any, indent: int = 2) -> str:
    """JSON dump with stable key order."""
    return json.dumps(normalize_value(data), indent=indent, sort_keys=True, ensure_ascii=False)
