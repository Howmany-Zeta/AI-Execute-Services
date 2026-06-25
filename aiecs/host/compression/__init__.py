# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""M4 host migration helpers for python-middleware (H0–H3).

Copy or import from ``app/services/multi_task/`` — L1/L2 policy stays in the host.
"""

from aiecs.host.compression.config import use_aiecs_compression
from aiecs.host.compression.l2_mc_adapter import compact_at_mc_recursive_boundary
from aiecs.host.compression.progress_bridge import compact_progress_event_to_sse_payload
from aiecs.host.compression.s3_tool_artifact_port import S3ToolArtifactPort

__all__ = [
    "S3ToolArtifactPort",
    "compact_at_mc_recursive_boundary",
    "compact_progress_event_to_sse_payload",
    "use_aiecs_compression",
]
