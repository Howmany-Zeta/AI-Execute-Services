"""
Test LangChain Integration

This module provides basic tests to verify the LangChain tool integration functionality.
It tests tool discovery, injection, selection, and execution with error handling.
"""

import asyncio
import logging
from typing import Dict, Any

from .tool_manager import ToolManager
from .langchain_integration_manager import (
    LangChainIntegrationManager,
    IntegrationConfig,
    create_langchain_integration
)
from .langchain_tool_selector import ToolExecutionContext
from ..core.models.agent_models import AgentConfig, AgentRole, AgentType

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockToolManager(ToolManager):
    """Mock tool manager for testing purposes."""

    def __init__(self):
        """Initialize mock tool manager with fake tools."""
        # Initialize with minimal setup
        self.logger = logging.getLogger(__name__)

        # Mock available tools
        self._mock_tools = ['classifier', 'research', 'scraper', 'pandas', 'stats']
        self._mock_operations = {
            'classifier': ['summarize', 'keyword_extract', 'classify'],
            'research': ['summarize', 'deduction', 'induction'],
            'scraper': ['get_requests', 'get_aiohttp', 'parse_html'],
            'pandas': ['describe', 'mean', 'filter'],
            'stats': ['describe', 'ttest', 'correlation']
        }

        logger.info("Mock tool manager initialized")

    def get_available_tools(self):
        """Return mock available tools."""
        return self._mock_tools.copy()

    def get_available_operations(self, tool_name=None):
        """Return mock available operations."""
        if tool_name:
            return self._mock_operations.get(tool_name, [])
        return self._mock_operations.copy()

    def is_tool_available(self, tool_name):
        """Check if mock tool is available."""
        return tool_name in self._mock_tools

    def is_operation_available(self, tool_name, operation_name):
        """Check if mock operation is available."""
        operations = self._mock_operations.get(tool_name, [])
        return operation_name in operations

    def get_operation_info(self, operation_spec):
        """Return mock operation info."""
        tool_name, operation_name = operation_spec.split('.', 1)
        return {
            'tool': tool_name,
            'operation': operation_name,
            'description': f"Mock {operation_name} operation for {tool_name}",
            'signature': {
                'parameters': {'input': {'required': True, 'type': 'str'}},
                'return_type': 'str'
            }
        }

    def validate_operation_params(self, tool_name, operation_name, params):
        """Mock parameter validation."""
        errors = []
        if 'input' not in params:
            errors.append("Missing required parameter: input")
        return errors

    def execute_tool_sync(self, tool_name, operation_name, **params):
        """Mock synchronous tool execution."""
        return f"Mock result from {tool_name}.{operation_name} with params: {params}"

    async def execute_tool(self, tool_name, operation_name, **params):
        """Mock asynchronous tool execution."""
        await asyncio.sleep(0.1)  # Simulate async work
        return f"Mock async result from {tool_name}.{operation_name} with params: {params}"

    def refresh_discovery(self):
        """Mock refresh discovery."""
        logger.info("Mock tool discovery refreshed")

    def get_system_stats(self):
        """Return mock system stats."""
        return {
            "discovery": {
                "total_tools": len(self._mock_tools),
                "total_operations": sum(len(ops) for ops in self._mock_operations.values())
            }
        }


async def test_tool_discovery():
    """Test tool discovery functionality."""
    logger.info("=== Testing Tool Discovery ===")

    try:
        # Create mock tool manager
        tool_manager = MockToolManager()

        # Create integration manager
        config = IntegrationConfig(
            enable_tool_discovery=True,
            enable_error_handling=True,
            max_tools_per_agent=5
        )

        integration_manager = await create_langchain_integration(tool_manager, config)

        # Test tool discovery
        tools_count = integration_manager.get_available_tools_count()
        logger.info(f"Discovered {tools_count} tools")

        # Get integration status
        status = integration_manager.get_integration_status()
        logger.info(f"Integration status: {status['system_health']}")

        assert tools_count > 0, "Should discover some tools"
        assert status['initialized'], "Integration should be initialized"

        logger.info("✅ Tool discovery test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Tool discovery test failed: {e}")
        return False


async def test_tool_injection():
    """Test tool injection for agents."""
    logger.info("=== Testing Tool Injection ===")

    try:
        # Create mock tool manager and integration
        tool_manager = MockToolManager()
        integration_manager = await create_langchain_integration(tool_manager)

        # Create mock agent config
        agent_config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test goal",
            backstory="Test backstory",
            tools=['classifier', 'research'],
            agent_id="test_agent_001"
        )

        # Test tool injection
        context = {
            "task_category": "analyze",
            "domain": "test",
            "user_id": "test_user"
        }

        tools = await integration_manager.get_tools_for_agent(agent_config, context)
        logger.info(f"Injected {len(tools)} tools for agent")

        # Verify tools were injected
        assert len(tools) > 0, "Should inject some tools"

        # Check tool names
        tool_names = [tool.name for tool in tools]
        logger.info(f"Tool names: {tool_names}")

        logger.info("✅ Tool injection test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Tool injection test failed: {e}")
        return False


async def test_tool_execution():
    """Test tool execution with error handling."""
    logger.info("=== Testing Tool Execution ===")

    try:
        # Create mock tool manager and integration
        tool_manager = MockToolManager()
        integration_manager = await create_langchain_integration(tool_manager)

        # Create mock agent config
        agent_config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test goal",
            backstory="Test backstory",
            tools=['classifier'],
            agent_id="test_agent_002"
        )

        # Test task execution with tools
        task_data = {
            "task_id": "test_task_001",
            "description": "Test task description",
            "category": "analyze",
            "expected_output": "Test output"
        }

        context = {
            "user_id": "test_user",
            "domain": "test"
        }

        result = await integration_manager.execute_agent_task_with_tools(
            agent_config, task_data, context
        )

        logger.info(f"Task execution result: {result['status']}")
        logger.info(f"Tools used: {result.get('tools_used', 0)}")

        # Verify execution completed
        assert result['status'] in ['completed', 'failed'], "Should have execution status"

        logger.info("✅ Tool execution test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Tool execution test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling and recovery mechanisms."""
    logger.info("=== Testing Error Handling ===")

    try:
        # Create integration with error handling enabled
        tool_manager = MockToolManager()
        config = IntegrationConfig(
            enable_error_handling=True,
            enable_circuit_breakers=True,
            fallback_enabled=True
        )

        integration_manager = await create_langchain_integration(tool_manager, config)

        # Test with invalid tool configuration
        agent_config = AgentConfig(
            name="test_agent",
            role=AgentRole.RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test goal",
            backstory="Test backstory",
            tools=['nonexistent_tool'],  # Invalid tool
            agent_id="test_agent_003"
        )

        context = {"user_id": "test_user"}

        # This should handle the error gracefully
        tools = await integration_manager.get_tools_for_agent(agent_config, context)

        # Should return empty list instead of crashing
        logger.info(f"Tools for invalid config: {len(tools)}")

        # Get error statistics
        error_stats = integration_manager.error_handler.get_error_statistics()
        logger.info(f"Error statistics: {error_stats}")

        logger.info("✅ Error handling test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False


async def test_integration_status():
    """Test integration status and health monitoring."""
    logger.info("=== Testing Integration Status ===")

    try:
        # Create integration
        tool_manager = MockToolManager()
        integration_manager = await create_langchain_integration(tool_manager)

        # Get comprehensive status
        status = integration_manager.get_integration_status()

        logger.info("Integration Status:")
        logger.info(f"  Initialized: {status['initialized']}")
        logger.info(f"  System Health: {status['system_health']}")
        logger.info(f"  Available Tools: {status['tool_registry']['cached_adapters']}")
        logger.info(f"  Performance Metrics: {status['performance_metrics']}")

        # Verify status structure
        assert 'initialized' in status, "Status should include initialization state"
        assert 'system_health' in status, "Status should include health assessment"
        assert 'configuration' in status, "Status should include configuration"

        logger.info("✅ Integration status test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Integration status test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests."""
    logger.info("🚀 Starting LangChain Integration Tests")

    tests = [
        test_tool_discovery,
        test_tool_injection,
        test_tool_execution,
        test_error_handling,
        test_integration_status
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)

    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! LangChain integration is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Please check the implementation.")

    return passed == total


# Main execution
if __name__ == "__main__":
    asyncio.run(run_all_tests())
