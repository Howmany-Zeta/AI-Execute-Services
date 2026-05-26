# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/

"""Plugin parity testing utilities (golden snapshots, §12.1)."""

from aiecs.domain.agent.plugins.testing.normalize import (
    normalize_execute_task_response,
    normalize_messages,
    normalize_tool_schema_names,
)
from aiecs.domain.agent.plugins.testing.parity import (
    ParityCase,
    ParityCaptureResult,
    capture_parity_case,
    default_fixtures_dir,
    list_parity_fixtures,
    load_parity_fixture,
)

__all__ = [
    "ParityCase",
    "ParityCaptureResult",
    "capture_parity_case",
    "default_fixtures_dir",
    "list_parity_fixtures",
    "load_parity_fixture",
    "normalize_execute_task_response",
    "normalize_messages",
    "normalize_tool_schema_names",
]
