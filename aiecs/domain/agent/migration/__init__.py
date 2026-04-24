# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Migration Utilities

Tools for migrating from legacy agents and LangChain to BaseAIAgent.
"""

from .legacy_wrapper import LegacyAgentWrapper
from .conversion import convert_langchain_prompt, convert_legacy_config

__all__ = [
    "LegacyAgentWrapper",
    "convert_langchain_prompt",
    "convert_legacy_config",
]
