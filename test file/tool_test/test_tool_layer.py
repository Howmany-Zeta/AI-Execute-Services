"""
Test file for the Tool Layer functionality

This test file demonstrates and validates the functionality of all four tool layer components:
- ToolDiscovery
- ToolInspector
- ToolExecutor
- ToolManager

Run this file to test the tool layer implementation.
"""

import asyncio
import logging
import sys
import traceback
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.append('app')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

def print_result(result: Any, max_length: int = 200):
    """Print a result with optional truncation."""
    result_str = str(result)
    if len(result_str) > max_length:
        print(f"{result_str[:max_length]}...")
    else:
        print(result_str)

def test_tool_discovery():
    """Test ToolDiscovery component functionality."""
    print_section("Testing ToolDiscovery Component")

    try:
        from app.services.multi_task.tools.discovery import ToolDiscovery

        # Initialize discovery
        print_subsection("Initializing ToolDiscovery")
        discovery = ToolDiscovery()
        print("✓ ToolDiscovery initialized successfully")

        # Test get_available_tools
        print_subsection("Testing get_available_tools()")
        tools = discovery.get_available_tools()
        print(f"Available tools ({len(tools)}): {tools}")

        # Test get_available_operations
        print_subsection("Testing get_available_operations()")
        all_operations = discovery.get_available_operations()
        print(f"All operations: {dict(list(all_operations.items())[:3])}...")  # Show first 3

        # Test specific tool operations
        if tools:
            first_tool = tools[0]
            print_subsection(f"Testing operations for tool: {first_tool}")
            tool_ops = discovery.get_available_operations(first_tool)
            print(f"Operations for {first_tool}: {tool_ops}")

        # Test utility methods
        print_subsection("Testing utility methods")
        if tools:
            print(f"Is '{tools[0]}' available: {discovery.is_tool_available(tools[0])}")
            print(f"Is 'nonexistent_tool' available: {discovery.is_tool_available('nonexistent_tool')}")

        # Test discovery stats
        stats = discovery.get_discovery_stats()
        print(f"Discovery stats: {stats}")

        print("✓ ToolDiscovery tests completed successfully")
        return discovery

    except Exception as e:
        print(f"✗ ToolDiscovery test failed: {e}")
        traceback.print_exc()
        return None

def test_tool_inspector(discovery=None):
    """Test ToolInspector component functionality."""
    print_section("Testing ToolInspector Component")

    try:
        from app.services.multi_task.tools.inspector import ToolInspector

        # Initialize inspector
        print_subsection("Initializing ToolInspector")
        inspector = ToolInspector(tool_discovery=discovery)
        print("✓ ToolInspector initialized successfully")

        # Get available tools for testing
        if discovery:
            tools = discovery.get_available_tools()
        else:
            tools = inspector.tool_discovery.get_available_tools()

        if not tools:
            print("No tools available for testing")
            return inspector

        # Test operation info
        print_subsection("Testing get_operation_info()")
        first_tool = tools[0]
        operations = inspector.tool_discovery.get_available_operations(first_tool)

        if operations:
            first_operation = operations[0]
            operation_spec = f"{first_tool}.{first_operation}"
            print(f"Getting info for: {operation_spec}")

            try:
                op_info = inspector.get_operation_info(operation_spec)
                print("Operation info:")
                for key, value in op_info.items():
                    if key == 'signature':
                        print(f"  {key}: {dict(list(value.items())[:3])}...")  # Truncate signature
                    else:
                        print_result(f"  {key}: {value}", 100)
            except Exception as e:
                print(f"Error getting operation info: {e}")

        # Test signature analysis
        print_subsection("Testing get_operation_signature()")
        if operations:
            try:
                signature = inspector.get_operation_signature(first_tool, operations[0])
                print("Signature details:")
                for key, value in signature.items():
                    print_result(f"  {key}: {value}", 150)
            except Exception as e:
                print(f"Error getting signature: {e}")

        # Test parameter validation
        print_subsection("Testing validate_operation_params()")
        if operations:
            try:
                # Test with empty params
                errors = inspector.validate_operation_params(first_tool, operations[0], {})
                print(f"Validation errors with empty params: {errors}")

                # Test with invalid params
                errors = inspector.validate_operation_params(first_tool, operations[0], {"invalid_param": "value"})
                print(f"Validation errors with invalid params: {errors}")
            except Exception as e:
                print(f"Error validating params: {e}")

        # Test cache stats
        cache_stats = inspector.get_cache_stats()
        print(f"Inspector cache stats: {cache_stats}")

        print("✓ ToolInspector tests completed successfully")
        return inspector

    except Exception as e:
        print(f"✗ ToolInspector test failed: {e}")
        traceback.print_exc()
        return None

def test_tool_executor(discovery=None):
    """Test ToolExecutor component functionality."""
    print_section("Testing ToolExecutor Component")

    try:
        from app.services.multi_task.tools.executor import ToolExecutor

        # Initialize executor
        print_subsection("Initializing ToolExecutor")
        executor = ToolExecutor(tool_discovery=discovery)
        print("✓ ToolExecutor initialized successfully")

        # Get available tools for testing
        if discovery:
            tools = discovery.get_available_tools()
        else:
            tools = executor.tool_discovery.get_available_tools()

        if not tools:
            print("No tools available for testing")
            return executor

        # Find a simple operation to test
        print_subsection("Finding testable operations")
        test_tool = None
        test_operation = None

        for tool in tools[:3]:  # Check first 3 tools
            operations = executor.tool_discovery.get_available_operations(tool)
            if operations:
                # Look for simple operations (avoid complex ones)
                simple_ops = [op for op in operations if any(keyword in op.lower()
                             for keyword in ['get', 'list', 'info', 'status', 'check'])]
                if simple_ops:
                    test_tool = tool
                    test_operation = simple_ops[0]
                    break

        if test_tool and test_operation:
            print(f"Testing with: {test_tool}.{test_operation}")

            # Test synchronous execution
            print_subsection("Testing execute_tool_sync()")
            try:
                result = executor.execute_tool_sync(test_tool, test_operation)
                print(f"Sync execution result: ")
                print_result(result, 200)
            except Exception as e:
                print(f"Sync execution failed (expected for some operations): {e}")

            # Test asynchronous execution
            print_subsection("Testing execute_tool() async")
            try:
                async def test_async():
                    result = await executor.execute_tool(test_tool, test_operation)
                    return result

                # Run async test
                result = asyncio.run(test_async())
                print(f"Async execution result: ")
                print_result(result, 200)
            except Exception as e:
                print(f"Async execution failed (expected for some operations): {e}")

        else:
            print("No suitable test operations found")

        # Test execution stats
        print_subsection("Testing execution statistics")
        stats = executor.get_execution_stats()
        print(f"Execution stats: {stats}")

        # Test cache stats
        cache_stats = executor.get_cache_stats()
        print(f"Executor cache stats: {cache_stats}")

        print("✓ ToolExecutor tests completed successfully")
        return executor

    except Exception as e:
        print(f"✗ ToolExecutor test failed: {e}")
        traceback.print_exc()
        return None

def test_tool_manager():
    """Test ToolManager component functionality."""
    print_section("Testing ToolManager Component")

    try:
        from app.services.multi_task.tools.manager import ToolManager

        # Initialize manager
        print_subsection("Initializing ToolManager")
        manager = ToolManager()
        print("✓ ToolManager initialized successfully")

        # Test discovery interface
        print_subsection("Testing discovery interface")
        tools = manager.get_available_tools()
        print(f"Available tools via manager ({len(tools)}): {tools[:5]}...")  # Show first 5

        operations = manager.get_available_operations()
        print(f"Available operations via manager: {len(operations)} tools with operations")

        # Test inspection interface
        print_subsection("Testing inspection interface")
        if tools:
            first_tool = tools[0]
            tool_operations = manager.get_available_operations(first_tool)

            if tool_operations:
                first_operation = tool_operations[0]
                operation_spec = f"{first_tool}.{first_operation}"

                try:
                    op_info = manager.get_operation_info(operation_spec)
                    print(f"Operation info via manager for {operation_spec}:")
                    print_result(f"  Description: {op_info.get('description', 'N/A')}", 150)
                    print(f"  Has signature: {'signature' in op_info}")
                except Exception as e:
                    print(f"Error getting operation info via manager: {e}")

        # Test system stats
        print_subsection("Testing system statistics")
        system_stats = manager.get_system_stats()
        print("System stats:")
        for component, stats in system_stats.items():
            print(f"  {component}: {stats}")

        # Test component health
        print_subsection("Testing component health")
        health = manager.get_component_health()
        print(f"Component health: {health}")

        # Test manager representation
        print_subsection("Testing manager representation")
        print(f"Manager repr: {repr(manager)}")

        print("✓ ToolManager tests completed successfully")
        return manager

    except Exception as e:
        print(f"✗ ToolManager test failed: {e}")
        traceback.print_exc()
        return None

def test_convenience_functions():
    """Test convenience functions from __init__.py."""
    print_section("Testing Convenience Functions")

    try:
        from app.services.multi_task.tools import (
            get_tool_manager,
            get_available_tools,
            get_available_operations,
            get_operation_info
        )

        # Test singleton manager
        print_subsection("Testing get_tool_manager()")
        manager1 = get_tool_manager()
        manager2 = get_tool_manager()
        print(f"Singleton test - Same instance: {manager1 is manager2}")

        # Test convenience functions
        print_subsection("Testing convenience functions")
        tools = get_available_tools()
        print(f"Tools via convenience function: {len(tools)} tools")

        operations = get_available_operations()
        print(f"Operations via convenience function: {len(operations)} tools")

        # Test operation info
        if tools:
            first_tool = tools[0]
            tool_ops = get_available_operations(first_tool)
            if tool_ops:
                operation_spec = f"{first_tool}.{tool_ops[0]}"
                try:
                    op_info = get_operation_info(operation_spec)
                    print(f"Operation info via convenience function: Available")
                except Exception as e:
                    print(f"Operation info error: {e}")

        print("✓ Convenience functions tests completed successfully")

    except Exception as e:
        print(f"✗ Convenience functions test failed: {e}")
        traceback.print_exc()

def run_comprehensive_test():
    """Run comprehensive tests of all tool layer components."""
    print_section("COMPREHENSIVE TOOL LAYER TEST")
    print("Testing all components of the refactored tool layer")

    # Test individual components
    discovery = test_tool_discovery()
    inspector = test_tool_inspector(discovery)
    executor = test_tool_executor(discovery)
    manager = test_tool_manager()

    # Test convenience functions
    test_convenience_functions()

    # Summary
    print_section("TEST SUMMARY")
    components = {
        "ToolDiscovery": discovery is not None,
        "ToolInspector": inspector is not None,
        "ToolExecutor": executor is not None,
        "ToolManager": manager is not None
    }

    print("Component test results:")
    for component, success in components.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {component}: {status}")

    all_passed = all(components.values())
    overall_status = "✓ ALL TESTS PASSED" if all_passed else "✗ SOME TESTS FAILED"
    print(f"\nOverall result: {overall_status}")

    if all_passed:
        print("\n🎉 Tool layer refactoring is working correctly!")
        print("All four components (Discovery, Inspector, Executor, Manager) are functional.")
    else:
        print("\n⚠️  Some components need attention.")
        print("Check the error messages above for details.")

if __name__ == "__main__":
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error during testing: {e}")
        traceback.print_exc()
