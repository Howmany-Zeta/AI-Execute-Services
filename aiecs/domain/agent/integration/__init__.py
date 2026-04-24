# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Integration Module

Integration adapters for external systems.
"""

from .context_engine_adapter import ContextEngineAdapter
from .retry_policy import EnhancedRetryPolicy, ErrorClassifier, ErrorType
from .role_config import RoleConfiguration, load_role_config
from .context_compressor import (
    ContextCompressor,
    compress_messages,
    CompressionStrategy,
)
from .protocols import ConfigManagerProtocol, CheckpointerProtocol

__all__ = [
    "ContextEngineAdapter",
    "EnhancedRetryPolicy",
    "ErrorClassifier",
    "ErrorType",
    "RoleConfiguration",
    "load_role_config",
    "ContextCompressor",
    "compress_messages",
    "CompressionStrategy",
    "ConfigManagerProtocol",
    "CheckpointerProtocol",
]
