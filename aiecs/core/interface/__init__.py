# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Core interfaces module"""

from .execution_interface import (
    ExecutionInterface,
    IToolProvider,
    IToolExecutor,
    ICacheProvider,
    IOperationExecutor,
)

from .storage_interface import (
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage,
    IStorageBackend,
    ICheckpointerBackend,
    IPermanentStorageBackend,
)

__all__ = [
    # Execution interfaces
    "ExecutionInterface",
    "IToolProvider",
    "IToolExecutor",
    "ICacheProvider",
    "IOperationExecutor",
    # Storage interfaces
    "ISessionStorage",
    "IConversationStorage",
    "ICheckpointStorage",
    "ITaskContextStorage",
    "IStorageBackend",
    "ICheckpointerBackend",
    "IPermanentStorageBackend",
]
