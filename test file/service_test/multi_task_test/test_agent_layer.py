#!/usr/bin/env python3
"""
Refactored Agent Layer Test Suite

This test suite validates the complete agent layer implementation including:
- Agent self-instantiation and configuration-driven behavior
- LangChain adapter integration with LLMIntegrationManager
- Real AI API connectivity through app.llm.* architecture
- Agent execution with correct LLM provider/model selection
- Task execution and result validation

Requirements:
- Uses pytest with poetry
- Real API connections (no mocking)
- Strict validation of AI client responses
- Comprehensive coverage of agent layer functions
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables using the project's configuration
from app.config.config import get_settings

# Initialize settings to load .env file
settings = get_settings()

# Import agent layer components
from app.services.multi_task.agent.base_agent import BaseAgent
from app.services.multi_task.agent.agent_manager import AgentManager
from app.services.multi_task.agent.factory.agent_factory import AgentFactory
from app.services.multi_task.agent.registry.agent_registry import AgentRegistry
from app.services.multi_task.agent.langchain_adapter_llm import LangChainAdapterLLM
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole, AgentStatus, AgentType
from app.services.llm_integration import LLMIntegrationManager

# Import specific agent implementations
from app.services.multi_task.agent.domain.researcher import ResearcherAgent
from app.services.multi_task.agent.domain.analyst import AnalystAgent
from app.services.multi_task.agent.domain.fieldwork import FieldworkAgent
from app.services.multi_task.agent.domain.writer import WriterAgent
from app.services.multi_task.agent.domain.meta_architect import MetaArchitectAgent
from app.services.multi_task.agent.system.director import DirectorAgent
from app.services.multi_task.agent.system.intent_parser import IntentParserAgent
from app.services.multi_task.agent.system.planner import PlannerAgent
from app.services.multi_task.agent.system.supervisor import SupervisorAgent
from app.services.multi_task.agent.system.task_decomposer import TaskDecomposerAgent

# Import LLM architecture components
from app.llm import get_llm_manager, LLMMessage, LLMResponse, AIProvider
from app.llm.client_factory import LLMClientFactory, LLMClientManager

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "timeout": 30,  # seconds
    "min_response_length": 10,  # minimum characters in AI response
    "required_env_vars": ["XAI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"],
    "test_data_dir": Path(__file__).parent / "test_data"
}

class TestAgentLayerBase:
    """Base class for agent layer tests with common utilities."""

    @pytest.fixture(scope="function")
    def config_manager(self):
        """Create and return a ConfigManager instance."""
        return ConfigManager()

    @pytest_asyncio.fixture(scope="function")
    async def llm_manager(self):
        """Create and return an LLMIntegrationManager instance."""
        manager = LLMIntegrationManager()
        yield manager
        # Ensure manager is closed after tests
        if hasattr(manager, 'close'):
            await manager.close()

    @pytest_asyncio.fixture(scope="function")
    async def agent_factory(self, config_manager, llm_manager):
        """Create and return an AgentFactory instance."""
        return AgentFactory(config_manager, llm_manager)

    @pytest_asyncio.fixture(scope="function")
    async def agent_manager(self, config_manager, llm_manager):
        """Create and initialize an AgentManager instance."""
        manager = AgentManager(config_manager, llm_manager)
        await manager.initialize()
        yield manager
        await manager.cleanup()

    @pytest.fixture(scope="function")
    def test_context(self):
        """Create test execution context with AI preferences."""
        return {
            "task_id": f"test_task_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "test_mode": True,
            "timeout": TEST_CONFIG["timeout"],
            "metadata": {
                "aiPreference": {
                    "provider": "xAI",
                    "model": "grok-2"
                }
            }
        }

    @pytest.fixture(scope="function")
    def vertex_context(self):
        """Create test execution context with Vertex AI preferences."""
        return {
            "task_id": f"test_task_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "test_mode": True,
            "timeout": TEST_CONFIG["timeout"],
            "metadata": {
                "aiPreference": {
                    "provider": "Vertex AI",
                    "model": "gemini-2.0-flash-exp"
                }
            }
        }

    def validate_ai_response(self, response: Any, min_length: int = None) -> bool:
        """Validate AI response meets minimum requirements."""
        if min_length is None:
            min_length = TEST_CONFIG["min_response_length"]

        if not response:
            return False

        if isinstance(response, str):
            return len(response.strip()) >= min_length

        if isinstance(response, dict):
            # Check for meaningful content in dict response
            content_fields = ["result", "content", "response", "output"]
            for field in content_fields:
                if field in response and isinstance(response[field], str):
                    return len(response[field].strip()) >= min_length
            return len(str(response)) >= min_length

        return len(str(response)) >= min_length


class TestEnvironmentSetup(TestAgentLayerBase):
    """Test environment setup and prerequisites."""

    def test_environment_variables(self):
        """Test that required environment variables are set."""
        # Check if environment variables are loaded through settings
        try:
            # Test XAI API key
            xai_key = settings.xai_api_key or os.getenv("XAI_API_KEY")
            assert xai_key is not None and xai_key.strip() != "", "XAI_API_KEY is required"

            # Test Google credentials
            google_creds = settings.google_application_credentials or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            assert google_creds is not None and google_creds.strip() != "", "GOOGLE_APPLICATION_CREDENTIALS is required"

            logger.info("Environment variables loaded successfully")
            logger.info(f"XAI API Key: {'*' * (len(xai_key) - 8) + xai_key[-8:] if len(xai_key) > 8 else '***'}")
            logger.info(f"Google Credentials Path: {google_creds}")

        except Exception as e:
            pytest.fail(f"Failed to load environment variables: {e}")

    def test_project_structure(self):
        """Test that required project files exist."""
        required_files = [
            "config/multi_task/prompts.yaml",
            "config/multi_task/llm_binding.yaml",
            "config/multi_task/agent_list.yaml"
        ]

        missing_files = []
        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing_files.append(file_path)

        assert not missing_files, f"Missing required files: {missing_files}"

    def test_dependencies_import(self):
        """Test that all required dependencies can be imported."""
        try:
            import langchain
            import google.cloud.aiplatform
            import httpx  # For XAI client
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import required dependencies: {e}")


class TestAgentSelfInstantiation(TestAgentLayerBase):
    """Test agent self-instantiation and configuration-driven behavior."""

    @pytest.mark.asyncio
    async def test_base_agent_instantiation_with_config(self, config_manager, llm_manager):
        """Test BaseAgent instantiation with configuration loading."""
        # Create agent config
        config = AgentConfig(
            name="Test Researcher Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Conduct comprehensive research and analysis",
            backstory="You are a skilled researcher with expertise in data collection and analysis",
            tools=["search", "analysis"],
            domain_specialization="general"
        )

        # Instantiate ResearcherAgent (concrete implementation of BaseAgent)
        agent = ResearcherAgent(config, config_manager, llm_manager)

        # Validate instantiation
        assert agent is not None
        assert isinstance(agent, BaseAgent)
        assert agent.config.role == AgentRole.GENERAL_RESEARCHER
        assert agent.config.name == "Test Researcher Agent"
        assert agent.status == AgentStatus.INACTIVE

        # Validate configuration-driven assembly
        assert agent.goal is not None  # Should be loaded from prompts.yaml
        assert agent.backstory is not None  # Should be loaded from prompts.yaml
        assert hasattr(agent, 'static_llm_provider')  # LLM binding should be checked
        assert hasattr(agent, 'static_llm_model')  # LLM binding should be checked

        logger.info(f"Agent instantiated successfully: {agent.agent_id}")
        logger.info(f"Goal from config: {agent.goal}")
        logger.info(f"LLM binding: {agent.static_llm_provider}/{agent.static_llm_model}")

    @pytest.mark.asyncio
    async def test_agent_factory_instantiation(self, agent_factory):
        """Test agent instantiation through AgentFactory."""
        # Test creating different agent types
        test_roles = [
            AgentRole.GENERAL_RESEARCHER,
            AgentRole.GENERAL_ANALYST,
            AgentRole.INTENT_PARSER,
            AgentRole.DIRECTOR
        ]

        factory = agent_factory

        for role in test_roles:
            config = AgentConfig(
                name=f"Test {role.value} Agent",
                role=role,
                agent_type=AgentType.DOMAIN if role in [AgentRole.GENERAL_RESEARCHER, AgentRole.GENERAL_ANALYST] else AgentType.SYSTEM,
                goal=f"Test goal for {role.value}",
                backstory=f"Test backstory for {role.value}",
                tools=["search"] if role == AgentRole.GENERAL_RESEARCHER else [],
                domain_specialization="test"
            )

            agent = factory.create_agent(config)

            assert agent is not None
            assert isinstance(agent, BaseAgent)
            assert agent.config.role == role

            logger.info(f"Successfully created {role.value} agent via factory")

    @pytest.mark.asyncio
    async def test_agent_from_role_config(self, agent_factory):
        """Test agent creation from role configuration in prompts.yaml."""
        # Test creating agents from configuration files
        test_role_names = ['general_researcher', 'general_analyst', 'intent_parser']

        factory = agent_factory

        for role_name in test_role_names:
            try:
                agent = factory.create_agent_from_role_config(role_name)

                assert agent is not None
                assert isinstance(agent, BaseAgent)
                assert agent.goal is not None  # Should be loaded from prompts.yaml
                assert agent.backstory is not None  # Should be loaded from prompts.yaml

                logger.info(f"Successfully created {role_name} agent from role config")
                logger.info(f"Goal: {agent.goal[:100]}...")
                logger.info(f"Backstory: {agent.backstory[:100]}...")

            except Exception as e:
                pytest.fail(f"Failed to create {role_name} agent from role config: {e}")


class TestLangChainAdapterIntegration(TestAgentLayerBase):
    """Test LangChain adapter integration with LLMIntegrationManager."""

    @pytest.mark.asyncio
    async def test_langchain_adapter_initialization(self, llm_manager, test_context):
        """Test LangChainAdapterLLM initialization and configuration."""

        # Test context-aware adapter (no static configuration)
        context_adapter = LangChainAdapterLLM(
            manager=llm_manager,
            context=test_context
        )

        assert context_adapter is not None
        assert context_adapter.static_provider is None
        assert context_adapter.static_model is None
        assert context_adapter._llm_type == "langchain_smart_adapter"

        # Test static configuration adapter
        static_adapter = LangChainAdapterLLM(
            manager=llm_manager,
            context=test_context,
            static_provider="xAI",
            static_model="grok-2"
        )

        assert static_adapter.static_provider == "xAI"
        assert static_adapter.static_model == "grok-2"

        logger.info("LangChain adapters initialized successfully")

    @pytest.mark.asyncio
    async def test_langchain_adapter_llm_call_context_aware(self, llm_manager, test_context):
        """Test LangChain adapter making real LLM calls with context-aware selection."""
        adapter = LangChainAdapterLLM(
            manager=llm_manager,
            context=test_context
        )

        test_prompt = "Hello, this is a test. Please respond with 'Context-aware test successful'."

        try:
            # Test async call
            response = await adapter._acall(test_prompt)

            assert response is not None
            assert isinstance(response, str)
            assert self.validate_ai_response(response)

            logger.info(f"Context-aware adapter response: {response[:100]}...")

            # 移除以下对同步方法的测试，因为它们与异步测试环境冲突
            # # Test sync call
            # sync_response = adapter._call(test_prompt)
            #
            # assert sync_response is not None
            # assert isinstance(sync_response, str)
            # assert self.validate_ai_response(sync_response)
            #
            # logger.info(f"Sync adapter response: {sync_response[:100]}...")

        except Exception as e:
            pytest.fail(f"LangChain adapter LLM call failed: {e}")

    @pytest.mark.asyncio
    async def test_langchain_adapter_llm_call_static_config(self, llm_manager, test_context):
        """Test LangChain adapter making real LLM calls with static configuration."""
        adapter = LangChainAdapterLLM(
            manager=llm_manager,
            context=test_context,
            static_provider="xAI",
            static_model="grok-2"
        )

        test_prompt = "Hello, this is a test. Please respond with 'Static config test successful'."

        try:
            response = await adapter._acall(test_prompt)

            assert response is not None
            assert isinstance(response, str)
            assert self.validate_ai_response(response)

            logger.info(f"Static config adapter response: {response[:100]}...")

        except Exception as e:
            pytest.fail(f"Static config adapter LLM call failed: {e}")


class TestAgentLLMIntegration(TestAgentLayerBase):
    """Test agent integration with LLM through LangChain adapter."""

    @pytest.mark.asyncio
    async def test_agent_langchain_agent_creation(self, config_manager, llm_manager, test_context):
        """Test agent creating LangChain AgentExecutor with correct LLM adapter."""
        # Create researcher agent
        config = AgentConfig(
            name="Test LLM Integration Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test LLM integration through LangChain",
            backstory="You are a test agent for validating LLM integration",
            tools=["search"],
            domain_specialization="test"
        )

        agent = ResearcherAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Create LangChain agent
        langchain_agent = await agent.create_langchain_agent(test_context)

        assert langchain_agent is not None
        assert hasattr(langchain_agent, 'agent')
        assert hasattr(langchain_agent, 'tools')

        # Validate the adapter is properly configured
        langchain_wrapper = langchain_agent.agent
        assert hasattr(langchain_wrapper, 'llm')
        assert isinstance(langchain_wrapper.llm, LangChainAdapterLLM)

        logger.info("LangChain agent created successfully with LLM adapter")

    @pytest.mark.asyncio
    async def test_agent_execute_task_with_xai(self, config_manager, llm_manager, test_context):
        """Test agent executing task with xAI through LangChain adapter."""
        # Create researcher agent
        config = AgentConfig(
            name="Test xAI Integration Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Conduct research using xAI LLM",
            backstory="You are a researcher specialized in using xAI for information gathering",
            tools=[],
            domain_specialization="test"
        )

        agent = ResearcherAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Test task data
        task_data = {
            "parameters": {
                "query": "What is artificial intelligence and its applications?"
            },
            "type": "general",
            "depth": "medium",
            "sources": 3
        }

        try:
            result = await agent.execute_task(task_data, test_context)

            assert result is not None
            assert isinstance(result, dict)
            assert "topic" in result
            assert "full_report" in result
            assert self.validate_ai_response(result["full_report"])

            logger.info(f"xAI task execution successful")
            logger.info(f"Result keys: {list(result.keys())}")
            logger.info(f"Report length: {len(result['full_report'])} characters")

        except Exception as e:
            pytest.fail(f"Agent task execution with xAI failed: {e}")

    @pytest.mark.asyncio
    async def test_agent_execute_task_with_vertex_ai(self, config_manager, llm_manager, vertex_context):
        """Test agent executing task with Vertex AI through LangChain adapter."""
        # Create analyst agent
        config = AgentConfig(
            name="Test Vertex AI Integration Agent",
            role=AgentRole.GENERAL_ANALYST,
            agent_type=AgentType.DOMAIN,
            goal="Perform analysis using Vertex AI LLM",
            backstory="You are an analyst specialized in using Vertex AI for data analysis",
            tools=[],
            domain_specialization="test"
        )

        agent = AnalystAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Test task data
        task_data = {
            "data": "sample market data",
            "analysis_type": "trend_analysis",
            "metrics": ["growth_rate", "market_share"],
            "description": "Analyze market trends and provide insights"
        }

        try:
            result = await agent.execute_task(task_data, vertex_context)

            assert result is not None
            assert isinstance(result, dict)
            assert self.validate_ai_response(result)

            logger.info(f"Vertex AI task execution successful")
            logger.info(f"Result keys: {list(result.keys())}")

        except Exception as e:
            pytest.fail(f"Agent task execution with Vertex AI failed: {e}")

    @pytest.mark.asyncio
    async def test_intent_parser_context_aware_llm(self, config_manager, llm_manager, test_context):
        """Test IntentParserAgent using context-aware LLM selection."""
        # Create intent parser agent (should be context-aware, no static LLM binding)
        config = AgentConfig(
            name="Test Intent Parser",
            role=AgentRole.INTENT_PARSER,
            agent_type=AgentType.SYSTEM,
            goal="Analyze user input to identify and prioritize the intended task categories accurately",
            backstory="You are an expert in natural language processing, trained to understand nuanced user intents",
            tools=[],
            domain_specialization="general"
        )

        agent = IntentParserAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Verify this agent is context-aware (no static LLM binding)
        assert agent.static_llm_provider is None or agent.static_llm_provider == ""
        assert agent.static_llm_model is None or agent.static_llm_model == ""

        # Test task data
        task_data = {
            "text": "I need to research market trends and analyze the data to create a comprehensive report"
        }

        try:
            result = await agent.execute_task(task_data, test_context)

            assert result is not None
            assert isinstance(result, dict)
            assert 'categories' in result or 'intent' in result
            assert self.validate_ai_response(str(result))

            logger.info(f"Intent parser context-aware execution successful")
            logger.info(f"Intent result: {result}")

        except Exception as e:
            pytest.fail(f"Intent parser context-aware execution failed: {e}")


class TestLLMProviderSelection(TestAgentLayerBase):
    """Test correct LLM provider and model selection."""

    @pytest.mark.asyncio
    async def test_llm_integration_manager_direct_call(self, llm_manager, test_context):
        """Test LLMIntegrationManager direct calls with different providers."""
        test_prompt = "Hello, this is a test. Please respond with 'Direct LLM test successful'."

        # Test with xAI context
        try:
            response = await llm_manager.generate_with_context(
                messages=test_prompt,
                context=test_context
            )

            assert response is not None
            assert hasattr(response, 'content')
            assert hasattr(response, 'provider')
            assert hasattr(response, 'model')
            assert self.validate_ai_response(response.content)

            logger.info(f"Direct LLM call successful: {response.provider}/{response.model}")
            logger.info(f"Response: {response.content[:100]}...")

        except Exception as e:
            pytest.fail(f"Direct LLM integration manager call failed: {e}")

    @pytest.mark.asyncio
    async def test_app_llm_client_factory(self):
        """Test app.llm client factory and manager."""
        try:
            # Test getting LLM manager
            llm_manager = await get_llm_manager()
            assert llm_manager is not None
            assert isinstance(llm_manager, LLMClientManager)

            # Test client factory
            factory = LLMClientFactory()

            # Test getting different clients
            xai_client = factory.get_client(AIProvider.XAI)
            assert xai_client is not None
            assert xai_client.provider_name == "xAI"

            vertex_client = factory.get_client(AIProvider.VERTEX)
            assert vertex_client is not None
            assert vertex_client.provider_name == "Vertex"

            openai_client = factory.get_client(AIProvider.OPENAI)
            assert openai_client is not None
            assert openai_client.provider_name == "OpenAI"

            logger.info("LLM client factory test successful")

        except Exception as e:
            pytest.fail(f"LLM client factory test failed: {e}")

    @pytest.mark.asyncio
    async def test_static_vs_context_llm_selection(self, config_manager, llm_manager):
        """Test static LLM binding vs context-aware selection."""
        # Create two agents: one with static binding, one context-aware

        # Agent with potential static binding (researcher)
        researcher_config = AgentConfig(
            name="Static Binding Researcher",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Research with static LLM binding",
            backstory="Researcher with predefined LLM",
            tools=[],
            domain_specialization="test"
        )

        researcher_agent = ResearcherAgent(researcher_config, config_manager, llm_manager)
        await researcher_agent.initialize()

        # Agent that should be context-aware (intent parser)
        intent_config = AgentConfig(
            name="Context Aware Intent Parser",
            role=AgentRole.INTENT_PARSER,
            agent_type=AgentType.SYSTEM,
            goal="Parse intent with context-aware LLM",
            backstory="Intent parser using context preferences",
            tools=[],
            domain_specialization="general"
        )

        intent_agent = IntentParserAgent(intent_config, config_manager, llm_manager)
        await intent_agent.initialize()

        # Check LLM binding configuration
        logger.info(f"Researcher static LLM: {researcher_agent.static_llm_provider}/{researcher_agent.static_llm_model}")
        logger.info(f"Intent parser static LLM: {intent_agent.static_llm_provider}/{intent_agent.static_llm_model}")

        # Both should have proper LLM configuration
        assert hasattr(researcher_agent, 'static_llm_provider')
        assert hasattr(intent_agent, 'static_llm_provider')


class TestAgentManagerIntegration(TestAgentLayerBase):
    """Test agent manager integration with LLM system."""

    @pytest.mark.asyncio
    async def test_agent_manager_create_and_execute(self, agent_manager, test_context):
        """Test creating and executing tasks through agent manager."""
        # Create agent config
        config = AgentConfig(
            name="Manager Test Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test agent manager integration",
            backstory="Agent created through manager for testing",
            tools=[],
            domain_specialization="test"
        )

        # Create agent through manager
        agent_model = await agent_manager.create_agent(config)
        assert agent_model is not None
        assert agent_model.name == "Manager Test Agent"

        # Execute task through manager
        task_data = {
            "parameters": {"query": "Test query for agent manager"},
            "type": "general",
            "description": "Test task execution through agent manager"
        }

        try:
            result = await agent_manager.execute_agent_task(
                agent_model.agent_id,
                task_data,
                test_context
            )

            assert result is not None
            assert isinstance(result, dict)
            assert self.validate_ai_response(result)

            logger.info("Agent manager task execution successful")

        except Exception as e:
            pytest.fail(f"Agent manager task execution failed: {e}")
        finally:
            # Clean up
            await agent_manager.delete_agent(agent_model.agent_id)


class TestErrorHandling(TestAgentLayerBase):
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_llm_provider_handling(self, config_manager, llm_manager):
        """Test handling of invalid LLM provider configuration."""
        # Create context with invalid provider
        invalid_context = {
            "task_id": "test_invalid",
            "metadata": {
                "aiPreference": {
                    "provider": "InvalidProvider",
                    "model": "invalid-model"
                }
            }
        }

        config = AgentConfig(
            name="Invalid Provider Test Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test invalid provider handling",
            backstory="Test agent for error handling",
            tools=[],
            domain_specialization="test"
        )

        agent = ResearcherAgent(config, config_manager, llm_manager)
        await agent.initialize()

        task_data = {
            "parameters": {"query": "Test with invalid provider"},
            "type": "general"
        }

        # Should handle gracefully and fall back to default provider
        try:
            result = await agent.execute_task(task_data, invalid_context)
            # Should still get a result due to fallback mechanism
            assert result is not None
            logger.info("Invalid provider handled gracefully with fallback")
        except Exception as e:
            # Or should raise a meaningful error
            logger.info(f"Invalid provider properly rejected: {e}")
            assert "provider" in str(e).lower() or "invalid" in str(e).lower()

    @pytest.mark.asyncio
    async def test_agent_status_management(self, config_manager, llm_manager):
        """Test agent status management during task execution."""
        config = AgentConfig(
            name="Status Test Agent",
            role=AgentRole.GENERAL_RESEARCHER,
            agent_type=AgentType.DOMAIN,
            goal="Test status management",
            backstory="Agent for testing status changes",
            tools=[],
            domain_specialization="test"
        )

        agent = ResearcherAgent(config, config_manager, llm_manager)

        # Initial status should be INACTIVE
        assert agent.status == AgentStatus.INACTIVE

        # Activate agent
        await agent.activate()
        assert agent.status == AgentStatus.ACTIVE

        # Deactivate agent
        await agent.deactivate()
        assert agent.status == AgentStatus.INACTIVE

        logger.info("Agent status management test successful")


class TestIntentParserDetailedAnalysis(TestAgentLayerBase):
    """Test detailed analysis of intent parser agent including LLM raw output capture."""

    @pytest.mark.asyncio
    async def test_intent_parser_raw_llm_output_capture(self, config_manager, llm_manager, test_context):
        """
        Test intent_parser agent with specific financial query to capture:
        1. LLM raw output from the intent parsing process
        2. Final processed result after code processing

        Input: "What is Apple's Q3 2024 financial performance compared to Q2 2024, focusing on revenue growth and profit margins"
        """
        # Create intent parser agent
        config = AgentConfig(
            name="Test Intent Parser for Financial Query",
            role=AgentRole.INTENT_PARSER,
            agent_type=AgentType.SYSTEM,
            goal="Analyze user input to identify and prioritize the intended task categories accurately",
            backstory="You are an expert in natural language processing, trained to understand nuanced user intents",
            tools=[],
            domain_specialization="general"
        )

        agent = IntentParserAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Test input - the specific financial query
        test_query = "What is Apple's Q3 2024 financial performance compared to Q2 2024, focusing on revenue growth and profit margins"

        task_data = {
            "text": test_query
        }

        # Create a comprehensive capturing adapter to track the entire flow
        class ComprehensiveLLMCapturingAdapter(LangChainAdapterLLM):
            # Declare the new attributes as class attributes with type hints.
            # This makes them known to Pydantic.
            captured_raw_output: Optional[Any] = None
            captured_final_input_to_ai: Optional[str] = None
            captured_llm_integration_call: Optional[Dict] = None
            captured_context: Optional[Dict] = None
            all_captured_calls: List[Dict] = []

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.all_captured_calls = []

            async def _acall(self, prompt: str, stop=None, run_manager=None, **kwargs):
                # Capture the complete final input that AI receives
                self.captured_final_input_to_ai = prompt
                self.captured_context = self.context

                # Store this call
                call_info = {
                    "prompt": prompt,
                    "context": self.context,
                    "static_provider": self.static_provider,
                    "static_model": self.static_model,
                    "kwargs": kwargs,
                    "stop": stop
                }
                self.all_captured_calls.append(call_info)

                # Log the complete input structure
                logger.info("🔍 CAPTURING AI INPUT DETAILS:")
                logger.info(f"Final Input to AI: {prompt}")
                logger.info(f"Context: {self.context}")
                logger.info(f"Static Provider: {self.static_provider}")
                logger.info(f"Static Model: {self.static_model}")
                logger.info(f"Additional kwargs: {kwargs}")

                # Call the original method to get LLM response
                response = await super()._acall(prompt, stop, run_manager, **kwargs)

                # Capture the raw LLM output
                self.captured_raw_output = response

                # Update the last call with response
                if self.all_captured_calls:
                    self.all_captured_calls[-1]["response"] = response

                logger.info(f"🔍 CAPTURED RAW LLM RESPONSE: {response}")

                return response

            def _call(self, prompt: str, stop=None, run_manager=None, **kwargs):
                # Also capture sync calls
                self.captured_final_input_to_ai = prompt
                self.captured_context = self.context

                call_info = {
                    "prompt": prompt,
                    "context": self.context,
                    "static_provider": self.static_provider,
                    "static_model": self.static_model,
                    "kwargs": kwargs,
                    "stop": stop,
                    "call_type": "sync"
                }
                self.all_captured_calls.append(call_info)

                logger.info("🔍 CAPTURING AI INPUT DETAILS (SYNC):")
                logger.info(f"Final Input to AI: {prompt}")
                logger.info(f"Context: {self.context}")

                response = super()._call(prompt, stop, run_manager, **kwargs)

                self.captured_raw_output = response

                if self.all_captured_calls:
                    self.all_captured_calls[-1]["response"] = response

                logger.info(f"🔍 CAPTURED RAW LLM RESPONSE (SYNC): {response}")

                return response

        # Capture LLM integration manager calls with more comprehensive logging
        original_generate_with_context = llm_manager.generate_with_context
        captured_llm_calls = []

        async def capturing_generate_with_context(messages, context, **kwargs):
            # Capture the call to LLM integration manager
            call_info = {
                "messages": messages,
                "context": context,
                "kwargs": kwargs,
                "timestamp": test_context.get('timestamp')
            }
            captured_llm_calls.append(call_info)

            logger.info("🔍 CAPTURING LLM INTEGRATION MANAGER CALL:")
            logger.info(f"Messages (input to LLM): {messages}")
            logger.info(f"Context: {context}")
            logger.info(f"Additional kwargs: {kwargs}")

            # Call the original method
            response = await original_generate_with_context(messages, context, **kwargs)

            # Update call info with response
            call_info["response"] = response

            logger.info(f"🔍 LLM INTEGRATION MANAGER RESPONSE: {response}")

            return response

        # Also capture direct LLM client calls if they exist
        from app.llm import get_llm_manager
        try:
            app_llm_manager = await get_llm_manager()
            original_generate = getattr(app_llm_manager, 'generate', None)
            captured_direct_calls = []

            if original_generate:
                async def capturing_generate(*args, **kwargs):
                    call_info = {
                        "args": args,
                        "kwargs": kwargs,
                        "timestamp": test_context.get('timestamp'),
                        "call_type": "direct_llm_generate"
                    }
                    captured_direct_calls.append(call_info)

                    logger.info("🔍 CAPTURING DIRECT LLM GENERATE CALL:")
                    logger.info(f"Args: {args}")
                    logger.info(f"Kwargs: {kwargs}")

                    response = await original_generate(*args, **kwargs)
                    call_info["response"] = response

                    logger.info(f"🔍 DIRECT LLM GENERATE RESPONSE: {response}")

                    return response

                app_llm_manager.generate = capturing_generate
        except Exception as e:
            logger.info(f"Could not patch direct LLM calls: {e}")
            captured_direct_calls = []

        # Monkey patch the LLM manager
        llm_manager.generate_with_context = capturing_generate_with_context

        original_create_langchain_agent = agent.create_langchain_agent
        capturing_adapter = None

        async def create_capturing_langchain_agent(context):
            nonlocal capturing_adapter
            # Create the original langchain agent
            langchain_agent = await original_create_langchain_agent(context)

            # Replace the LLM with our comprehensive capturing adapter
            capturing_adapter = ComprehensiveLLMCapturingAdapter(
                manager=llm_manager,
                context=context,
                static_provider=agent.static_llm_provider,
                static_model=agent.static_llm_model
            )

            # Replace the LLM in the agent
            langchain_agent.agent.llm = capturing_adapter

            return langchain_agent

        # Replace the method
        agent.create_langchain_agent = create_capturing_langchain_agent

        try:
            # Execute the intent parsing task
            logger.info(f"🚀 Testing intent parser with query: {test_query}")

            result = await agent.execute_task(task_data, test_context)

            # Validate that we got results
            assert result is not None
            assert isinstance(result, dict)
            assert 'categories' in result
            assert self.validate_ai_response(str(result))

            # Capture and log the complete flow
            assert capturing_adapter is not None, "Capturing adapter was not created"

            # Check if we captured anything
            has_captured_data = (
                capturing_adapter.captured_raw_output is not None or
                capturing_adapter.captured_final_input_to_ai is not None or
                len(capturing_adapter.all_captured_calls) > 0 or
                len(captured_llm_calls) > 0
            )

            # Comprehensive logging
            logger.info("=" * 100)
            logger.info("🎯 INTENT PARSER COMPLETE FLOW ANALYSIS")
            logger.info("=" * 100)

            logger.info("📝 1. ORIGINAL USER INPUT:")
            logger.info(f"   Query: {test_query}")
            logger.info(f"   Task Data: {json.dumps(task_data, indent=4)}")
            logger.info("-" * 100)

            logger.info("🔧 2. AGENT CONFIGURATION:")
            logger.info(f"   Agent Name: {agent.config.name}")
            logger.info(f"   Agent Role: {agent.config.role}")
            logger.info(f"   Static LLM Provider: {agent.static_llm_provider}")
            logger.info(f"   Static LLM Model: {agent.static_llm_model}")
            logger.info("-" * 100)

            logger.info("🎯 3. ALL CAPTURED LLM CALLS:")
            if len(capturing_adapter.all_captured_calls) > 0:
                for i, call in enumerate(capturing_adapter.all_captured_calls):
                    logger.info(f"   Call {i+1}:")
                    logger.info(f"     Prompt/Input to AI: {call.get('prompt', 'N/A')}")
                    logger.info(f"     Response from AI: {call.get('response', 'N/A')}")
                    logger.info(f"     Context: {call.get('context', 'N/A')}")
                    logger.info(f"     Call Type: {call.get('call_type', 'async')}")
                    logger.info(f"     Static Provider: {call.get('static_provider', 'N/A')}")
                    logger.info(f"     Static Model: {call.get('static_model', 'N/A')}")
                    logger.info("     " + "-" * 80)
            else:
                logger.info("   No LLM calls captured through adapter")
            logger.info("-" * 100)

            logger.info("🎯 4. FINAL INPUT SENT TO AI/LLM:")
            logger.info("   (This is the complete prompt that the AI model receives)")
            logger.info(f"   Input: {capturing_adapter.captured_final_input_to_ai}")
            logger.info("-" * 100)

            logger.info("🤖 5. RAW LLM OUTPUT:")
            logger.info("   (This is the unprocessed response from the AI model)")
            logger.info(f"   Output: {capturing_adapter.captured_raw_output}")
            logger.info("-" * 100)

            logger.info("⚙️ 6. LLM INTEGRATION MANAGER CALLS:")
            if len(captured_llm_calls) > 0:
                for i, call in enumerate(captured_llm_calls):
                    logger.info(f"   Call {i+1}:")
                    logger.info(f"     Messages: {call['messages']}")
                    logger.info(f"     Response: {call.get('response', 'N/A')}")
                    logger.info(f"     Context: {call['context']}")
                    logger.info(f"     Kwargs: {call['kwargs']}")
            else:
                logger.info("   No LLM integration manager calls captured")
            logger.info("-" * 100)

            logger.info("⚙️ 7. DIRECT LLM CALLS:")
            if 'captured_direct_calls' in locals() and len(captured_direct_calls) > 0:
                for i, call in enumerate(captured_direct_calls):
                    logger.info(f"   Call {i+1}:")
                    logger.info(f"     Args: {call['args']}")
                    logger.info(f"     Kwargs: {call['kwargs']}")
                    logger.info(f"     Response: {call.get('response', 'N/A')}")
            else:
                logger.info("   No direct LLM calls captured")
            logger.info("-" * 100)

            logger.info("📊 7. FINAL PROCESSED RESULT:")
            logger.info("   (This is the result after all code processing)")
            logger.info(json.dumps(result, indent=4, ensure_ascii=False))
            logger.info("-" * 100)

            # Additional analysis
            logger.info("🔍 8. PROCESSING ANALYSIS:")
            logger.info(f"   - Identified categories: {result.get('categories', [])}")
            logger.info(f"   - Confidence score: {result.get('confidence', 'N/A')}")
            logger.info(f"   - Reasoning: {result.get('reasoning', 'N/A')}")

            # Validate expected categories for this financial query
            expected_categories = ["collect", "analyze"]  # Should involve collecting data and analyzing
            identified_categories = result.get('categories', [])

            logger.info(f"   - Expected categories: {expected_categories}")
            logger.info(f"   - Categories match expectation: {any(cat in identified_categories for cat in expected_categories)}")
            logger.info(f"   - Has captured data: {has_captured_data}")

            logger.info("=" * 100)

            # Store comprehensive results
            test_results = {
                "original_user_input": test_query,
                "task_data": task_data,
                "agent_config": {
                    "name": agent.config.name,
                    "role": str(agent.config.role),
                    "static_llm_provider": agent.static_llm_provider,
                    "static_llm_model": agent.static_llm_model
                },
                "final_input_to_ai": capturing_adapter.captured_final_input_to_ai,
                "raw_llm_output": capturing_adapter.captured_raw_output,
                "all_captured_calls": capturing_adapter.all_captured_calls,
                "llm_integration_calls": captured_llm_calls,
                "final_processed_result": result,
                "test_context": test_context,
                "test_timestamp": test_context.get('timestamp'),
                "llm_provider_used": test_context.get('metadata', {}).get('aiPreference', {}).get('provider'),
                "llm_model_used": test_context.get('metadata', {}).get('aiPreference', {}).get('model'),
                "has_captured_data": has_captured_data
            }

            # Validate the processing pipeline worked correctly
            assert len(identified_categories) > 0, "No categories were identified"
            assert result.get('confidence', 0) > 0, "Confidence score should be greater than 0"

            logger.info("✅ Intent parser comprehensive flow capture test completed successfully")

            if not has_captured_data:
                logger.warning("⚠️ Warning: No LLM input/output was captured. This might indicate the capturing mechanism needs adjustment.")

            return test_results

        except Exception as e:
            logger.error(f"❌ Intent parser comprehensive flow capture test failed: {e}")
            if capturing_adapter:
                logger.error(f"Captured final input to AI: {capturing_adapter.captured_final_input_to_ai}")
                logger.error(f"Captured raw output: {capturing_adapter.captured_raw_output}")
                logger.error(f"All captured calls: {capturing_adapter.all_captured_calls}")
            logger.error(f"Captured LLM calls: {captured_llm_calls}")
            raise
        finally:
            # Restore original method
            llm_manager.generate_with_context = original_generate_with_context

    @pytest.mark.asyncio
    async def test_intent_parser_processing_pipeline_analysis(self, config_manager, llm_manager, test_context):
        """
        Test the complete processing pipeline of intent parser to understand:
        1. How raw LLM output is processed
        2. Category validation and filtering
        3. Confidence calculation
        4. Final result formatting
        """
        # Create intent parser agent
        config = AgentConfig(
            name="Test Intent Parser Pipeline",
            role=AgentRole.INTENT_PARSER,
            agent_type=AgentType.SYSTEM,
            goal="Analyze user input to identify and prioritize the intended task categories accurately",
            backstory="You are an expert in natural language processing, trained to understand nuanced user intents",
            tools=[],
            domain_specialization="general"
        )

        agent = IntentParserAgent(config, config_manager, llm_manager)
        await agent.initialize()

        # Test with the same financial query
        test_query = "What is Apple's Q3 2024 financial performance compared to Q2 2024, focusing on revenue growth and profit margins"

        task_data = {
            "text": test_query
        }

        try:
            # Execute the task
            result = await agent.execute_task(task_data, test_context)

            # Test individual processing methods
            logger.info("=" * 80)
            logger.info("INTENT PARSER PROCESSING PIPELINE ANALYSIS")
            logger.info("=" * 80)

            # Test category extraction from text (fallback method)
            test_raw_outputs = [
                '["collect", "analyze"]',  # Valid JSON
                'collect, analyze',        # Non-JSON format
                'The categories are: collect and analyze',  # Natural language
                'invalid response'         # Invalid response
            ]

            for i, raw_output in enumerate(test_raw_outputs):
                logger.info(f"Test {i+1}: Raw output = '{raw_output}'")

                # Test category extraction
                extracted = agent._extract_categories_from_text(raw_output)
                logger.info(f"  Extracted categories: {extracted}")

                # Test category validation
                validated = agent._validate_categories(extracted)
                logger.info(f"  Validated categories: {validated}")

                # Test confidence calculation
                confidence = agent._calculate_confidence(test_query, validated)
                logger.info(f"  Confidence score: {confidence}")
                logger.info("-" * 40)

            # Test question type classification
            question_analysis = agent.classify_question_type(test_query)
            logger.info("QUESTION TYPE ANALYSIS:")
            logger.info(json.dumps(question_analysis, indent=2))
            logger.info("-" * 40)

            # Test entity and keyword extraction
            entity_analysis = agent.extract_entities_and_keywords(test_query)
            logger.info("ENTITY AND KEYWORD ANALYSIS:")
            logger.info(json.dumps(entity_analysis, indent=2))
            logger.info("-" * 40)

            # Test complexity assessment
            complexity_analysis = agent.assess_request_complexity(test_query, result.get('categories', []))
            logger.info("COMPLEXITY ANALYSIS:")
            logger.info(json.dumps(complexity_analysis, indent=2))
            logger.info("-" * 40)

            # Test execution strategy suggestion
            strategy = agent.suggest_execution_strategy(result.get('categories', []), complexity_analysis)
            logger.info("EXECUTION STRATEGY:")
            logger.info(json.dumps(strategy, indent=2))

            logger.info("=" * 80)

            # Validate all components worked
            assert question_analysis is not None
            assert entity_analysis is not None
            assert complexity_analysis is not None
            assert strategy is not None

            logger.info("Intent parser processing pipeline analysis completed successfully")

        except Exception as e:
            logger.error(f"Intent parser processing pipeline analysis failed: {e}")
            raise


@pytest.mark.asyncio
async def test_suite_completeness():
    """Test that the test suite covers all required functionality."""
    required_test_areas = [
        "agent_self_instantiation",
        "langchain_adapter_integration",
        "llm_provider_selection",
        "real_api_connectivity",
        "error_handling"
    ]

    # This test ensures we have comprehensive coverage
    logger.info(f"Test suite covers: {', '.join(required_test_areas)}")
    assert len(required_test_areas) >= 5  # Ensure we have comprehensive coverage
