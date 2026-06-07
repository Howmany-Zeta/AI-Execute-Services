# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP (Dynamic Adaptive Work Process) plugin package.

See CUSTOM_REASONING_PLUGIN_DESIGN.md for full specification.
"""

from aiecs.domain.agent.plugins.dawp.stream_consumer import (
    DAWP_BOUNDARY_EVENT_TYPES,
    DAWP_RUN_COMPLETED,
    DAWP_RUN_STARTED,
    DawpRunPanel,
    DawpStreamConsumer,
    effective_loop_scope,
    is_dawp_boundary_event,
    is_dawp_scoped_event,
)

__all__ = [
    "DAWP_BOUNDARY_EVENT_TYPES",
    "DAWP_RUN_COMPLETED",
    "DAWP_RUN_STARTED",
    "DawpRunPanel",
    "DawpStreamConsumer",
    "effective_loop_scope",
    "is_dawp_boundary_event",
    "is_dawp_scoped_event",
]
