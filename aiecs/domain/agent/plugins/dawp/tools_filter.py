# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Tool schema filtering for DAWP nested runs (§4.5, D10).

DAWP step inner loops must not expose ``dawp_start`` (or its legacy aliases)
to the LLM — doing so would allow the model to recursively trigger DAWP runs,
causing unbounded budget consumption.

:data:`DAWP_EXCLUDED_TOOL_NAMES`
    Names always stripped from nested-run tool schemas.

:func:`resolve_tools_for_scope`
    Returns a filtered copy of *all_tools* when the scope is a DAWP run
    (``scope.kind == "dawp"``); returns *all_tools* unchanged for main scope.

:func:`check_dawp_nesting_guard`
    Rejects ``dawp_start`` when ``plugin_state["dawp.active_run_id"]`` is set (D10, §4.5).
    Also checked inline in :func:`handle_dawp_start`.

References: CUSTOM_REASONING_PLUGIN_DESIGN.md §4.5, D10.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope

# ---------------------------------------------------------------------------
# Excluded names
# ---------------------------------------------------------------------------

DAWP_EXCLUDED_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "dawp_start",
        "dawp_run",  # legacy alias
        "dawp_publish_workflow",  # legacy alias
    }
)
"""Tool names that must never be visible inside a DAWP nested run (§4.5, D10)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tool_name(tool: Any) -> str:
    """Extract the tool name from an instance (`.name`) or schema dict (`["name"]`)."""
    if isinstance(tool, dict):
        return str(tool.get("name", ""))
    return getattr(tool, "name", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_tools_for_scope(all_tools: list[Any], scope: LoopScope) -> list[Any]:
    """Return tools/schemas available for *scope* (§4.5, D10).

    When ``scope.kind == "dawp"`` the entries whose name is in
    :data:`DAWP_EXCLUDED_TOOL_NAMES` are removed.  For ``kind="main"`` the
    list is returned unchanged (no copy overhead).

    Accepts tool instances (objects with a ``.name`` attribute) as well as raw
    schema dicts (OpenAI function format with a ``"name"`` key) so the same
    function can be used from both high-level plugin code and inside
    ``_run_tool_loop_nested_streaming``.

    Args:
        all_tools: Full list of tools or tool schemas visible in the current
                   iteration.
        scope:     :class:`~aiecs.domain.agent.plugins.dawp.loop_scope.LoopScope`
                   for the current loop; ``kind`` determines filtering.

    Returns:
        Filtered (or original) list.  The original list is never mutated.
    """
    if scope.kind != "dawp":
        return all_tools
    return [t for t in all_tools if _get_tool_name(t) not in DAWP_EXCLUDED_TOOL_NAMES]


def check_dawp_nesting_guard(plugin_state: dict[str, Any]) -> dict[str, Any] | None:
    """Reject ``dawp_start`` when a nested DAWP run is already active (D10, §4.5).

    ``plugin_state["dawp.active_run_id"]`` is set by
    :meth:`~aiecs.domain.agent.hybrid_agent.HybridAgent._run_tool_loop_nested_streaming`
    at the start of each nested run and cleared in its ``finally`` block.

    Args:
        plugin_state: The current ``AgentPluginContext.plugin_state`` dict.

    Returns:
        ``None`` when no DAWP run is active (tool may proceed).
        A tool-error rejection dict when a run is active (tool must abort).
    """
    active_run_id = plugin_state.get("dawp.active_run_id")
    if not active_run_id:
        return None
    return {
        "status": "rejected",
        "reason": "dawp_start is not available inside a DAWP run (D10)",
        "active_run_id": active_run_id,
    }
