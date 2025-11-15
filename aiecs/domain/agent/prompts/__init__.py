"""
Prompt Templates Module

Native prompt template system replacing LangChain templates.
"""

from .template import (
    PromptTemplate,
    ChatPromptTemplate,
    MessageTemplate,
    TemplateMissingVariableError,
)
from .builder import MessageBuilder
from .formatters import (
    format_conversation_history,
    format_tool_result,
    truncate_context,
)

__all__ = [
    "PromptTemplate",
    "ChatPromptTemplate",
    "MessageTemplate",
    "TemplateMissingVariableError",
    "MessageBuilder",
    "format_conversation_history",
    "format_tool_result",
    "truncate_context",
]
