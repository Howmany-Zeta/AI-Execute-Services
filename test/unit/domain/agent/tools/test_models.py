"""
Unit tests for Tool models.
"""

import pytest
from typing import Dict, Any

from aiecs.domain.agent.tools.models import (
    Tool,
    ToolParameter,
    ToolValidationError,
)


# Sample async execute function for testing
async def sample_execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sample execute function for testing."""
    return {"result": input_data.get("value", "default")}


async def error_execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute function that raises an error."""
    raise ValueError("Execution failed")


class TestToolParameter:
    """Tests for ToolParameter."""
    
    def test_basic_creation(self):
        """Test basic parameter creation."""
        param = ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True
    
    def test_to_json_schema(self):
        """Test JSON Schema conversion."""
        param = ToolParameter(
            name="count",
            type="number",
            description="Number of results",
            required=False,
            default=10
        )
        schema = param.to_json_schema()
        
        assert schema["type"] == "number"
        assert schema["description"] == "Number of results"
        assert schema["default"] == 10
    
    def test_with_enum(self):
        """Test parameter with enum values."""
        param = ToolParameter(
            name="format",
            type="string",
            description="Output format",
            enum=["json", "xml", "csv"]
        )
        schema = param.to_json_schema()
        
        assert schema["enum"] == ["json", "xml", "csv"]


class TestToolCreation:
    """Tests for Tool creation and validation."""
    
    def test_basic_creation(self):
        """Test basic tool creation."""
        tool = Tool(
            name="test-tool",
            description="A test tool",
            execute=sample_execute
        )
        assert tool.name == "test-tool"
        assert tool.description == "A test tool"
        assert tool.execute is sample_execute
    
    def test_with_all_fields(self):
        """Test tool creation with all fields."""
        params = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
        tool = Tool(
            name="search-tool",
            description="Search for information",
            parameters=params,
            execute=sample_execute,
            tags=["search", "web"],
            source="my-skill"
        )
        
        assert tool.name == "search-tool"
        assert tool.parameters == params
        assert tool.tags == ["search", "web"]
        assert tool.source == "my-skill"
    
    def test_name_validation_empty(self):
        """Test that empty name raises error."""
        with pytest.raises(ToolValidationError, match="name is required"):
            Tool(name="", description="Test", execute=sample_execute)
    
    def test_name_validation_format(self):
        """Test that invalid name format raises error."""
        with pytest.raises(ToolValidationError, match="must be lowercase"):
            Tool(name="InvalidName", description="Test", execute=sample_execute)
    
    def test_name_validation_starts_with_number(self):
        """Test that name starting with number raises error."""
        with pytest.raises(ToolValidationError, match="start with a letter"):
            Tool(name="123-tool", description="Test", execute=sample_execute)
    
    def test_description_required(self):
        """Test that description is required."""
        with pytest.raises(ToolValidationError, match="description is required"):
            Tool(name="test-tool", description="", execute=sample_execute)
    
    def test_execute_required(self):
        """Test that execute function is required."""
        with pytest.raises(ToolValidationError, match="execute function is required"):
            Tool(name="test-tool", description="Test", execute=None)
    
    def test_execute_must_be_callable(self):
        """Test that execute must be callable."""
        with pytest.raises(ToolValidationError, match="must be callable"):
            Tool(name="test-tool", description="Test", execute="not_callable")  # type: ignore
    
    def test_valid_name_formats(self):
        """Test various valid name formats."""
        valid_names = [
            "tool",
            "my-tool",
            "my_tool",
            "tool123",
            "my-tool-v2",
            "tool_v2_beta"
        ]
        for name in valid_names:
            tool = Tool(name=name, description="Test", execute=sample_execute)
            assert tool.name == name


class TestToolExecution:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling tool directly."""
        tool = Tool(
            name="test-tool",
            description="A test tool",
            execute=sample_execute
        )
        result = await tool({"value": "test_input"})
        assert result == {"result": "test_input"}

    @pytest.mark.asyncio
    async def test_call_tool_with_default(self):
        """Test calling tool with default value."""
        tool = Tool(
            name="test-tool",
            description="A test tool",
            execute=sample_execute
        )
        result = await tool({})
        assert result == {"result": "default"}

    @pytest.mark.asyncio
    async def test_tool_execution_error(self):
        """Test tool execution that raises error."""
        tool = Tool(
            name="error-tool",
            description="A tool that errors",
            execute=error_execute
        )
        with pytest.raises(ValueError, match="Execution failed"):
            await tool({})


class TestToolConversion:
    """Tests for tool format conversion."""

    def test_to_openai_function(self):
        """Test conversion to OpenAI function format."""
        params = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "number", "description": "Max results"}
            },
            "required": ["query"]
        }
        tool = Tool(
            name="search-tool",
            description="Search for information online",
            parameters=params,
            execute=sample_execute
        )

        openai_func = tool.to_openai_function()

        assert openai_func["type"] == "function"
        assert openai_func["function"]["name"] == "search-tool"
        assert openai_func["function"]["description"] == "Search for information online"
        assert openai_func["function"]["parameters"] == params

    def test_default_parameters(self):
        """Test that default parameters are valid JSON Schema."""
        tool = Tool(
            name="simple-tool",
            description="A simple tool",
            execute=sample_execute
        )

        # Default parameters should be valid empty object schema
        assert tool.parameters["type"] == "object"
        assert tool.parameters["properties"] == {}
        assert tool.parameters["required"] == []


class TestToolRepr:
    """Tests for tool string representation."""

    def test_repr_short_description(self):
        """Test repr with short description."""
        tool = Tool(
            name="test-tool",
            description="Short desc",
            execute=sample_execute
        )
        repr_str = repr(tool)
        assert "test-tool" in repr_str
        assert "Short desc" in repr_str

    def test_repr_long_description(self):
        """Test repr with long description (truncated)."""
        long_desc = "This is a very long description " * 10
        tool = Tool(
            name="test-tool",
            description=long_desc,
            execute=sample_execute
        )
        repr_str = repr(tool)
        assert "test-tool" in repr_str
        assert "..." in repr_str  # Should be truncated


class TestToolEdgeCases:
    """Tests for edge cases."""

    def test_parameters_must_be_dict(self):
        """Test that parameters must be a dictionary."""
        with pytest.raises(ToolValidationError, match="must be a dictionary"):
            Tool(
                name="test-tool",
                description="Test",
                parameters="not a dict",  # type: ignore
                execute=sample_execute
            )

    def test_name_with_underscores(self):
        """Test name with underscores is valid."""
        tool = Tool(
            name="my_test_tool",
            description="Test tool",
            execute=sample_execute
        )
        assert tool.name == "my_test_tool"

    def test_name_with_numbers(self):
        """Test name with numbers is valid."""
        tool = Tool(
            name="tool-v2-beta3",
            description="Test tool",
            execute=sample_execute
        )
        assert tool.name == "tool-v2-beta3"

    @pytest.mark.asyncio
    async def test_lambda_execute(self):
        """Test tool with lambda execute function."""
        tool = Tool(
            name="lambda-tool",
            description="Tool with lambda",
            execute=lambda x: sample_execute(x)  # type: ignore
        )
        # Note: lambda returns coroutine, so we await
        result = await tool({"value": "lambda_test"})
        assert result == {"result": "lambda_test"}

