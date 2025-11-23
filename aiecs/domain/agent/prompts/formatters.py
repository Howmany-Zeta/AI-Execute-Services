"""
Prompt Formatters

Utilities for formatting prompts with context.
"""

from typing import List, Dict, Any, Optional
from aiecs.llm import LLMMessage


def format_conversation_history(
    history: List[LLMMessage],
    max_messages: Optional[int] = None,
    format_style: str = "compact",
) -> str:
    """
    Format conversation history as string.

    Args:
        history: List of LLMMessage instances
        max_messages: Optional limit on number of messages
        format_style: "compact" or "detailed"

    Returns:
        Formatted conversation string
    """
    if max_messages:
        history = history[-max_messages:]

    if format_style == "compact":
        lines = []
        for msg in history:
            lines.append(f"{msg.role.upper()}: {msg.content}")
        return "\n".join(lines)

    elif format_style == "detailed":
        lines = []
        for i, msg in enumerate(history):
            lines.append(f"[{i+1}] {msg.role.upper()}")
            lines.append(msg.content)
            lines.append("")  # Empty line between messages
        return "\n".join(lines)

    else:
        raise ValueError(f"Unknown format_style: {format_style}")


def format_tool_result(
    tool_name: str,
    result: Any,
    success: bool = True,
    error: Optional[str] = None,
) -> str:
    """
    Format tool execution result.

    Args:
        tool_name: Tool name
        result: Tool result (if successful)
        success: Whether execution succeeded
        error: Error message (if failed)

    Returns:
        Formatted tool result string
    """
    if success:
        return f"Tool '{tool_name}' returned:\n{result}"
    else:
        return f"Tool '{tool_name}' failed: {error}"


def truncate_context(
    text: str,
    max_length: int,
    strategy: str = "middle",
    placeholder: str = "...",
) -> str:
    """
    Truncate text to fit within max_length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        strategy: "start", "middle", or "end"
        placeholder: Placeholder for truncated content

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    if strategy == "end":
        # Keep start, truncate end
        return text[: max_length - len(placeholder)] + placeholder

    elif strategy == "start":
        # Truncate start, keep end
        return placeholder + text[-(max_length - len(placeholder)) :]

    elif strategy == "middle":
        # Keep start and end, truncate middle
        half = (max_length - len(placeholder)) // 2
        return text[:half] + placeholder + text[-half:]

    else:
        raise ValueError(f"Unknown strategy: {strategy}")


def format_list_items(items: List[str], style: str = "bullets") -> str:
    """
    Format list items.

    Args:
        items: List of items
        style: "bullets", "numbered", or "compact"

    Returns:
        Formatted list string
    """
    if style == "bullets":
        return "\n".join(f"• {item}" for item in items)

    elif style == "numbered":
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

    elif style == "compact":
        return ", ".join(items)

    else:
        raise ValueError(f"Unknown style: {style}")


def format_key_value_pairs(
    data: Dict[str, Any],
    separator: str = ": ",
    exclude_keys: Optional[List[str]] = None,
) -> str:
    """
    Format dictionary as key-value pairs.

    Args:
        data: Dictionary to format
        separator: Separator between key and value
        exclude_keys: Keys to exclude

    Returns:
        Formatted string
    """
    exclude_keys = exclude_keys or []
    lines = []

    for key, value in data.items():
        if key in exclude_keys or key.startswith("_"):
            continue
        lines.append(f"{key}{separator}{value}")

    return "\n".join(lines)


def inject_context_in_prompt(prompt: str, context: Dict[str, Any], context_marker: str = "{context}") -> str:
    """
    Inject context into prompt at marker position.

    Args:
        prompt: Prompt template with context marker
        context: Context dictionary
        context_marker: Marker to replace with context

    Returns:
        Prompt with context injected
    """
    context_str = format_key_value_pairs(context)
    return prompt.replace(context_marker, context_str)


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count (4 chars ≈ 1 token)
    """
    return len(text) // 4
