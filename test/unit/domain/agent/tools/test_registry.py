"""
Unit tests for SkillScriptRegistry.
"""

import pytest
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from aiecs.domain.agent.tools.registry import (
    SkillScriptRegistry,
    SkillScriptRegistryError,
)
from aiecs.domain.agent.tools.models import Tool


# Sample async execute function for testing
async def sample_execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sample execute function for testing."""
    return {"result": input_data.get("value", "default")}


def create_tool(
    name: str,
    description: str = "Test tool",
    tags: list = None,
    source: str = None
) -> Tool:
    """Helper to create test tools."""
    return Tool(
        name=name,
        description=description,
        execute=sample_execute,
        tags=tags,
        source=source
    )


class TestSkillScriptRegistryBasic:
    """Basic registry operations."""
    
    def test_create_empty_registry(self):
        """Test creating an empty registry."""
        registry = SkillScriptRegistry()
        assert registry.tool_count() == 0
        assert registry.list_tool_names() == []
    
    def test_register_tool(self):
        """Test registering a tool."""
        registry = SkillScriptRegistry()
        tool = create_tool("test-tool")
        
        registry.register_tool(tool)
        
        assert registry.has_tool("test-tool")
        assert registry.tool_count() == 1
    
    def test_register_multiple_tools(self):
        """Test registering multiple tools."""
        registry = SkillScriptRegistry()
        
        registry.register_tool(create_tool("tool-a"))
        registry.register_tool(create_tool("tool-b"))
        registry.register_tool(create_tool("tool-c"))
        
        assert registry.tool_count() == 3
        assert set(registry.list_tool_names()) == {"tool-a", "tool-b", "tool-c"}
    
    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate raises error."""
        registry = SkillScriptRegistry()
        tool = create_tool("test-tool")
        
        registry.register_tool(tool)
        
        with pytest.raises(SkillScriptRegistryError, match="already registered"):
            registry.register_tool(tool)
    
    def test_register_duplicate_with_replace(self):
        """Test registering duplicate with replace=True."""
        registry = SkillScriptRegistry()
        tool1 = create_tool("test-tool", description="Original")
        tool2 = create_tool("test-tool", description="Replaced")
        
        registry.register_tool(tool1)
        registry.register_tool(tool2, replace=True)
        
        retrieved = registry.get_tool("test-tool")
        assert retrieved.description == "Replaced"


class TestSkillScriptRegistryRetrieval:
    """Tool retrieval operations."""
    
    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = SkillScriptRegistry()
        tool = create_tool("test-tool")
        registry.register_tool(tool)
        
        retrieved = registry.get_tool("test-tool")
        
        assert retrieved is tool
    
    def test_get_nonexistent_tool(self):
        """Test getting a nonexistent tool returns None."""
        registry = SkillScriptRegistry()
        
        assert registry.get_tool("nonexistent") is None
    
    def test_has_tool_true(self):
        """Test has_tool returns True for existing tool."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("test-tool"))
        
        assert registry.has_tool("test-tool") is True
    
    def test_has_tool_false(self):
        """Test has_tool returns False for nonexistent tool."""
        registry = SkillScriptRegistry()
        
        assert registry.has_tool("nonexistent") is False
    
    def test_get_all_tools(self):
        """Test getting all tools as dictionary."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a"))
        registry.register_tool(create_tool("tool-b"))
        
        all_tools = registry.get_all_tools()
        
        assert len(all_tools) == 2
        assert "tool-a" in all_tools
        assert "tool-b" in all_tools


class TestSkillScriptRegistryFiltering:
    """Tool filtering operations."""
    
    def test_list_tools_no_filter(self):
        """Test listing all tools without filter."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a"))
        registry.register_tool(create_tool("tool-b"))
        
        tools = registry.list_tools()
        
        assert len(tools) == 2
    
    def test_list_tools_by_tag(self):
        """Test listing tools filtered by tag."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("python-tool", tags=["python", "code"]))
        registry.register_tool(create_tool("js-tool", tags=["javascript", "code"]))
        registry.register_tool(create_tool("other-tool", tags=["misc"]))

        python_tools = registry.list_tools(tags=["python"])
        code_tools = registry.list_tools(tags=["code"])

        assert len(python_tools) == 1
        assert python_tools[0].name == "python-tool"
        assert len(code_tools) == 2

    def test_list_tools_by_source(self):
        """Test listing tools filtered by source."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a", source="skill-1"))
        registry.register_tool(create_tool("tool-b", source="skill-1"))
        registry.register_tool(create_tool("tool-c", source="skill-2"))

        skill1_tools = registry.list_tools(source="skill-1")
        skill2_tools = registry.list_tools(source="skill-2")

        assert len(skill1_tools) == 2
        assert len(skill2_tools) == 1

    def test_get_tools_by_source(self):
        """Test get_tools_by_source helper."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a", source="my-skill"))
        registry.register_tool(create_tool("tool-b", source="my-skill"))
        registry.register_tool(create_tool("tool-c", source="other-skill"))

        tools = registry.get_tools_by_source("my-skill")

        assert len(tools) == 2
        assert all(t.source == "my-skill" for t in tools)

    def test_list_tools_combined_filter(self):
        """Test listing tools with both tag and source filter."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a", tags=["python"], source="skill-1"))
        registry.register_tool(create_tool("tool-b", tags=["python"], source="skill-2"))
        registry.register_tool(create_tool("tool-c", tags=["other"], source="skill-1"))

        tools = registry.list_tools(tags=["python"], source="skill-1")

        assert len(tools) == 1
        assert tools[0].name == "tool-a"


class TestSkillScriptRegistryUnregistration:
    """Tool unregistration operations."""

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("test-tool"))

        result = registry.unregister_tool("test-tool")

        assert result is True
        assert registry.has_tool("test-tool") is False

    def test_unregister_nonexistent(self):
        """Test unregistering a nonexistent tool returns False."""
        registry = SkillScriptRegistry()

        result = registry.unregister_tool("nonexistent")

        assert result is False

    def test_unregister_by_source(self):
        """Test unregistering all tools from a source."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a", source="skill-1"))
        registry.register_tool(create_tool("tool-b", source="skill-1"))
        registry.register_tool(create_tool("tool-c", source="skill-2"))

        count = registry.unregister_by_source("skill-1")

        assert count == 2
        assert registry.tool_count() == 1
        assert registry.has_tool("tool-c")

    def test_unregister_by_source_none_found(self):
        """Test unregistering by source when none found."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a", source="other"))

        count = registry.unregister_by_source("nonexistent")

        assert count == 0
        assert registry.tool_count() == 1

    def test_clear_registry(self):
        """Test clearing all tools."""
        registry = SkillScriptRegistry()
        registry.register_tool(create_tool("tool-a"))
        registry.register_tool(create_tool("tool-b"))
        registry.register_tool(create_tool("tool-c"))

        count = registry.clear()

        assert count == 3
        assert registry.tool_count() == 0


class TestSkillScriptRegistryThreadSafety:
    """Thread safety tests."""

    def test_concurrent_registration(self):
        """Test concurrent tool registration."""
        registry = SkillScriptRegistry()
        num_tools = 100

        def register_tool(i):
            tool = create_tool(f"tool-{i}")
            registry.register_tool(tool)

        with ThreadPoolExecutor(max_workers=10) as executor:
            list(executor.map(register_tool, range(num_tools)))

        assert registry.tool_count() == num_tools

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes."""
        registry = SkillScriptRegistry()
        errors = []

        # Pre-populate with some tools
        for i in range(50):
            registry.register_tool(create_tool(f"initial-{i}"))

        def writer(i):
            try:
                registry.register_tool(create_tool(f"new-{i}"))
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                registry.list_tools()
                registry.tool_count()
                registry.list_tool_names()
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=20) as executor:
            # Mix of reads and writes
            futures = []
            for i in range(50):
                futures.append(executor.submit(writer, i))
                futures.append(executor.submit(reader))
            for f in futures:
                f.result()

        assert len(errors) == 0
        assert registry.tool_count() == 100  # 50 initial + 50 new

