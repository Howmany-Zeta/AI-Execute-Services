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
