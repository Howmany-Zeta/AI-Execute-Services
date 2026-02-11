"""
Pydantic schemas for type-safe parsing of tool calls and tool definitions.

Provides defensive validation at boundaries where Vertex API / upstream callers
may return unexpected structures (lists, protobuf, etc.).
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ToolCallFunction(BaseModel):
    """OpenAI-format function call sub-object."""

    name: str = ""
    arguments: str = "{}"


class ToolCallItem(BaseModel):
    """Single tool call in OpenAI format."""

    id: Optional[str] = None
    type: str = "function"
    function: Union[ToolCallFunction, dict] = Field(
        default_factory=lambda: ToolCallFunction()
    )

    model_config = {"extra": "ignore"}

    @classmethod
    def model_validate_safe(cls, obj: Any) -> Optional["ToolCallItem"]:
        """Validate or return None if coercion fails (e.g. when obj is a list)."""
        if obj is None:
            return None
        if isinstance(obj, list):
            return None  # Guard against list-instead-of-dict
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            try:
                func = obj.get("function")
                if func is None:
                    func = {}
                if not isinstance(func, dict):
                    return None
                return cls(
                    id=obj.get("id"),
                    type=obj.get("type", "function"),
                    function=ToolCallFunction(
                        name=func.get("name", ""),
                        arguments=func.get("arguments", "{}"),
                    ),
                )
            except Exception:
                return None
        return None


class OpenAIToolSchema(BaseModel):
    """OpenAI tool schema (single tool in tools list)."""

    type: str = "function"
    function: Optional[dict] = None

    model_config = {"extra": "ignore"}

    @classmethod
    def model_validate_safe(cls, obj: Any) -> Optional["OpenAIToolSchema"]:
        """Validate or return None if coercion fails (e.g. when obj is a list)."""
        if obj is None:
            return None
        if isinstance(obj, dict) and obj.get("type") == "function":
            func = obj.get("function")
            if isinstance(func, dict):
                return cls(type="function", function=func)
        return None
