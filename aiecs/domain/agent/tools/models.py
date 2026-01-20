"""
Tool Models

Lightweight tool abstractions for agent-level tool management.
These models enable dynamic tool registration from skills and other sources.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ToolValidationError(Exception):
    """Raised when tool validation fails."""
    pass


@dataclass
class ToolParameter:
    """
    Definition of a tool parameter.
    
    Attributes:
        name: Parameter name
        type: Parameter type (string, number, boolean, object, array)
        description: Human-readable description
        required: Whether the parameter is required
        default: Default value if not provided
        enum: List of allowed values (optional)
    """
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.type,
        }
        if self.description:
            schema["description"] = self.description
        if self.default is not None:
            schema["default"] = self.default
        if self.enum:
            schema["enum"] = self.enum
        return schema


@dataclass
class Tool:
    """
    Lightweight tool definition for agent-level tool management.
    
    This is a simple wrapper that enables dynamic tool registration
    from skills, external sources, or programmatic creation. It differs
    from BaseTool in that:
    
    1. It's a simple dataclass, not a full class with decorators
    2. It wraps an async callable instead of defining operations
    3. It's designed for dynamic registration at runtime
    4. It uses JSON Schema for parameter definitions
    
    Attributes:
        name: Unique tool name (kebab-case recommended)
        description: Human-readable description for LLM context
        parameters: JSON Schema for tool parameters
        execute: Async callable that executes the tool
        tags: Optional list of tags for categorization
        source: Optional source identifier (e.g., skill name)
    
    Usage:
        tool = Tool(
            name="validate-python",
            description="Validate Python code syntax",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code"}
                },
                "required": ["code"]
            },
            execute=async_validate_function,
            tags=["python", "validation"]
        )
    """
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object",
        "properties": {},
        "required": []
    })
    execute: Callable[[Dict[str, Any]], Awaitable[Any]] = field(default=None)  # type: ignore
    tags: Optional[List[str]] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate tool after initialization."""
        self._validate()
    
    def _validate(self) -> None:
        """Validate tool configuration."""
        # Validate name
        if not self.name:
            raise ToolValidationError("Tool name is required")
        
        if not re.match(r'^[a-z][a-z0-9_-]*$', self.name):
            raise ToolValidationError(
                f"Tool name '{self.name}' must be lowercase, start with a letter, "
                "and contain only letters, numbers, hyphens, and underscores"
            )
        
        # Validate description
        if not self.description:
            raise ToolValidationError("Tool description is required")
        
        # Validate execute callable
        if self.execute is None:
            raise ToolValidationError("Tool execute function is required")
        
        if not callable(self.execute):
            raise ToolValidationError("Tool execute must be callable")
        
        # Validate parameters is a dict
        if not isinstance(self.parameters, dict):
            raise ToolValidationError("Tool parameters must be a dictionary")
    
    async def __call__(self, input_data: Dict[str, Any]) -> Any:
        """Execute the tool with the given input data."""
        return await self.execute(input_data)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """
        Convert to OpenAI function calling format.
        
        Returns:
            Dictionary in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def __repr__(self) -> str:
        return f"Tool(name='{self.name}', description='{self.description[:50]}...')"

