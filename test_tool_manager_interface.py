#!/usr/bin/env python3
"""
Test script to verify ToolManager implements IToolManager interface correctly.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.multi_task.tools.tool_manager import ToolManager
from services.multi_task.core.interfaces.tool_manager import IToolManager
from services.multi_task.core.models.execution_models import ToolConfig, ToolType


async def test_tool_manager_interface():
    """Test that ToolManager properly implements IToolManager interface."""

    print("Testing ToolManager interface implementation...")

    # Test 1: Verify inheritance
    tool_manager = ToolManager()
    assert isinstance(tool_manager, IToolManager), "ToolManager should inherit from IToolManager"
    print("✓ ToolManager correctly inherits from IToolManager")

    # Test 2: Initialize
    try:
        await tool_manager.initialize()
        print("✓ ToolManager initialization successful")
    except Exception as e:
        print(f"✗ ToolManager initialization failed: {e}")
        return False

    # Test 3: Register a tool
    test_tool_config = ToolConfig(
        name="test_tool",
        tool_type=ToolType.CUSTOM,
        description="A test tool for verification",
        operations={
            "test_operation": {
                "description": "A test operation",
                "parameters": {}
            }
        }
    )

    try:
        result = await tool_manager.register_tool("test_tool", test_tool_config)
        assert result == True, "Tool registration should return True"
        print("✓ Tool registration successful")
    except Exception as e:
        print(f"✗ Tool registration failed: {e}")
        return False

    # Test 4: List tools
    try:
        tools = await tool_manager.list_tools()
        assert "test_tool" in tools, "Registered tool should be in the list"
        print(f"✓ Tool listing successful: {len(tools)} tools found")
    except Exception as e:
        print(f"✗ Tool listing failed: {e}")
        return False

    # Test 5: Get tool
    try:
        retrieved_tool = await tool_manager.get_tool("test_tool")
        assert retrieved_tool is not None, "Should retrieve registered tool"
        assert retrieved_tool.name == "test_tool", "Retrieved tool should match"
        print("✓ Tool retrieval successful")
    except Exception as e:
        print(f"✗ Tool retrieval failed: {e}")
        return False

    # Test 6: Get tool capabilities
    try:
        capabilities = await tool_manager.get_tool_capabilities("test_tool")
        assert "tool_name" in capabilities, "Capabilities should include tool_name"
        assert capabilities["tool_name"] == "test_tool", "Tool name should match"
        print("✓ Tool capabilities retrieval successful")
    except Exception as e:
        print(f"✗ Tool capabilities retrieval failed: {e}")
        return False

    # Test 7: Validate parameters
    try:
        validation_result = await tool_manager.validate_tool_parameters(
            "test_tool",
            "test_operation",
            {}
        )
        assert "valid" in validation_result, "Validation result should include 'valid' field"
        print("✓ Parameter validation successful")
    except Exception as e:
        print(f"✗ Parameter validation failed: {e}")
        return False

    # Test 8: Get tool metrics
    try:
        metrics = await tool_manager.get_tool_metrics("test_tool")
        assert "execution_count" in metrics, "Metrics should include execution_count"
        print("✓ Tool metrics retrieval successful")
    except Exception as e:
        print(f"✗ Tool metrics retrieval failed: {e}")
        return False

    # Test 9: Tool adapters
    try:
        def dummy_adapter(config):
            return f"adapted_tool_{config.get('name', 'unknown')}"

        result = await tool_manager.register_tool_adapter("dummy_adapter", dummy_adapter)
        assert result == True, "Adapter registration should return True"

        adapters = await tool_manager.get_available_adapters()
        assert "dummy_adapter" in adapters, "Registered adapter should be in the list"
        print("✓ Tool adapter functionality successful")
    except Exception as e:
        print(f"✗ Tool adapter functionality failed: {e}")
        return False

    # Test 10: Cleanup
    try:
        await tool_manager.cleanup()
        print("✓ Tool manager cleanup successful")
    except Exception as e:
        print(f"✗ Tool manager cleanup failed: {e}")
        return False

    print("\n🎉 All tests passed! ToolManager successfully implements IToolManager interface.")
    return True


async def test_interface_methods():
    """Test that all interface methods are implemented."""

    print("\nVerifying all interface methods are implemented...")

    # Get all abstract methods from IToolManager
    interface_methods = [
        method for method in dir(IToolManager)
        if not method.startswith('_') and callable(getattr(IToolManager, method))
    ]

    # Get all methods from ToolManager
    tool_manager = ToolManager()
    implementation_methods = [
        method for method in dir(tool_manager)
        if not method.startswith('_') and callable(getattr(tool_manager, method))
    ]

    missing_methods = []
    for method in interface_methods:
        if method not in implementation_methods:
            missing_methods.append(method)

    if missing_methods:
        print(f"✗ Missing methods: {missing_methods}")
        return False
    else:
        print(f"✓ All {len(interface_methods)} interface methods are implemented")
        return True


async def main():
    """Main test function."""
    print("=" * 60)
    print("ToolManager Interface Implementation Test")
    print("=" * 60)

    try:
        # Test interface method coverage
        methods_test = await test_interface_methods()

        # Test actual functionality
        functionality_test = await test_tool_manager_interface()

        if methods_test and functionality_test:
            print("\n🎉 SUCCESS: ToolManager fully implements IToolManager interface!")
            return True
        else:
            print("\n❌ FAILURE: ToolManager implementation has issues.")
            return False

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
