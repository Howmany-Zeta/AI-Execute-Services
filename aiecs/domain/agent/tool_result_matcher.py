"""
Tool Result Matcher

Checks if a tool result matches configured stop conditions for early loop termination.
"""

import re
from typing import Any, Dict, List, Optional, Union


def _to_text(result: Any) -> str:
    """Convert tool result to searchable string."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        import json
        return json.dumps(result, ensure_ascii=False)
    return str(result)


def _match_one(text: str, result: Any, condition: Union[str, Dict[str, Any]]) -> bool:
    """Check if result matches a single condition."""
    if isinstance(condition, str):
        return condition in text
    if isinstance(condition, dict):
        cond_type = condition.get("type", "substring")
        pattern = condition.get("pattern") or condition.get("value")
        if not pattern:
            return False
        if cond_type == "substring":
            return str(pattern) in text
        if cond_type == "regex":
            try:
                return bool(re.search(pattern, text, re.DOTALL))
            except re.error:
                return False
        if cond_type == "html_tag":
            # Match opening/closing tag presence (e.g., </html>, <html>)
            tag = str(pattern).strip("<>")
            return f"<{tag}" in text.lower() or f"</{tag}>" in text.lower()
    return False


def matches_stop_condition(
    result: Any,
    conditions: Optional[List[Union[str, Dict[str, Any]]]],
) -> bool:
    """
    Check if tool result matches any stop condition.

    Args:
        result: Tool execution result (str, dict, or other)
        conditions: List of conditions. Each item:
            - str: substring match
            - dict: {"type": "substring"|"regex"|"html_tag", "pattern": "..."} or {"value": "..."}

    Returns:
        True if any condition matches, False otherwise.

    Example:
        >>> matches_stop_condition("<html>...</html>", ["</html>"])
        True
        >>> matches_stop_condition({"status": "done"}, [{"type": "substring", "pattern": "done"}])
        True
    """
    if not conditions:
        return False
    text = _to_text(result)
    for cond in conditions:
        if _match_one(text, result, cond):
            return True
    return False
