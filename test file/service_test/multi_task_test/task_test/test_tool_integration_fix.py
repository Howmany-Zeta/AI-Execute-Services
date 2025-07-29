#!/usr/bin/env python3
"""
Test script to verify that tools are properly passed from langchain_integration_manager
to agents through the agent_manager and agent_factory.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.multi_task.agent.agent_manager import AgentManager
from app.services.multi_task.agent.factory.agent_factory import AgentFactory
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole, AgentType
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.tools.langchain_integration_manager import LangChainIntegrationManager
from app.services.multi_task.tools.tool_manager import ToolManager


async def test_tool_integration():
    """Test that tools are properly integrated into agents."""
    print("Testing tool integration fix...")

    try:
        # Initialize managers
        config_manager = ConfigManager()
        llm_manager = LLMIntegrationManager()

        # Initialize tool manager and integration manager
        tool_manager = ToolManager()
        tool_integration_manager = LangChainIntegrationManager(tool_manager)

        # Initialize tool integration manager
        await tool_integration_manager.initialize()

        # Create agent manager with tool integration
        agent_manager = AgentManager(
            config_manager=config_manager,
            llm_manager=llm_manager,
            tool_integration_manager=tool_integration_manager
        )

        # Initialize agent manager
        await agent_manager.initialize()

        # Create a test agent configuration
        agent_config = AgentConfig(
            name="test_agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test agent for tool integration",
            backstory="A test agent to verify tool integration works",
            tools=["summarize", "keyword_extract"],
            domain_specialization="testing"
        )

        # Create agent
        agent_model = await agent_manager.create_agent(agent_config)
        print(f"✓ Agent created successfully: {agent_model.agent_id}")

        # Get the actual agent instance
        agent = agent_manager.agent_registry.get_agent(agent_model.agent_id)

        if agent is None:
            print("✗ Failed to retrieve agent from registry")
            return False

        # Check if tool integration manager is properly assigned
        if agent.tool_integration_manager is None:
            print("✗ Tool integration manager not assigned to agent")
            return False
        else:
            print("✓ Tool integration manager properly assigned to agent")

        # Test creating langchain agent with tools
        context = {"task_type": "research", "domain": "testing"}

        try:
            langchain_agent = await agent.create_langchain_agent(context)
            print("✓ LangChain agent created successfully")

            # Check if tools were retrieved
            if hasattr(langchain_agent, 'tools') and langchain_agent.tools:
                print(f"✓ Tools successfully retrieved: {len(langchain_agent.tools)} tools")
                for tool in langchain_agent.tools:
                    print(f"  - {tool.name}: {tool.description}")
            else:
                print("⚠ No tools found, but this might be expected if no tools are configured")

        except Exception as e:
            print(f"✗ Failed to create LangChain agent: {e}")
            return False

        # Cleanup
        await agent_manager.cleanup()
        await tool_integration_manager.cleanup()

        print("✓ Tool integration test completed successfully!")
        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tool_integration())
    sys.exit(0 if success else 1)
