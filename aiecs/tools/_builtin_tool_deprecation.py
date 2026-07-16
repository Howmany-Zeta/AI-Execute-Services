# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Shared deprecation notices for built-in tools migrating to MCP server services.
"""

from __future__ import annotations

import warnings

BUILTIN_TOOL_MCP_MIGRATION_DATE = "2026-07-01"

_BUILTIN_TOOL_DEPRECATION_MESSAGES = {
    "task_tools": (
        f"aiecs.tools.task_tools is deprecated and will be removed on {BUILTIN_TOOL_MCP_MIGRATION_DATE}. "
        "Task tools are being migrated to MCP server services; "
        "please migrate to the corresponding MCP server tools."
    ),
}

_warned_packages: set[str] = set()


def warn_builtin_tool_deprecated(package: str, *, stacklevel: int = 2) -> None:
    """Emit :class:`DeprecationWarning` once per built-in tool package per process."""
    if package in _warned_packages:
        return
    message = _BUILTIN_TOOL_DEPRECATION_MESSAGES.get(package)
    if message is None:
        return
    _warned_packages.add(package)
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)
