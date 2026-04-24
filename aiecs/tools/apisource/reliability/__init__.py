# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Reliability Module

Contains error handling and fallback strategy components.
"""

from aiecs.tools.apisource.reliability.error_handler import SmartErrorHandler
from aiecs.tools.apisource.reliability.fallback_strategy import (
    FallbackStrategy,
)

__all__ = ["SmartErrorHandler", "FallbackStrategy"]
