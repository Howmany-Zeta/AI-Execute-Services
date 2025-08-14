"""
Base Agent

Provides the base class for all agents in the multi-task service,
implementing common functionality and the agent interface using LangChain.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from pydantic import Field, ConfigDict

from ..core.interfaces.agent_manager import IAgentManager
from ..core.models.agent_models import AgentConfig, AgentModel, AgentStatus, AgentRole, AgentType
from ..core.exceptions.task_exceptions import TaskValidationError
from ..config.config_manager import ConfigManager
from .langchain_adapter_llm import LangChainAdapterLLM
from app.services.llm_integration import LLMIntegrationManager
from ..tools.langchain_integration_manager import LangChainIntegrationManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-task service.

    Provides common functionality for agent lifecycle management,
    configuration handling, and integration with LangChain.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager: Optional[LangChainIntegrationManager] = None):
        """
        Initialize the base agent with configuration-driven setup.

        Args:
            config: Agent configuration containing role, goal, backstory, etc.
            config_manager: Configuration manager for accessing prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for dynamic LLM selection
            tool_integration_manager: Optional LangChain tool integration manager
        """
        self.config = config
        self.config_manager = config_manager
        self.llm_manager = llm_manager
        self.tool_integration_manager = tool_integration_manager
        self.agent_id = str(uuid.uuid4())
        self.status = AgentStatus.INACTIVE
        self.created_at = datetime.utcnow()
        self.updated_at = None
        self.last_active_at = None

        # Performance metrics
        self.total_tasks_executed = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.average_execution_time = None
        self.average_quality_score = None

        # Memory and context
        self.memory_data: Dict[str, Any] = {}
        self.current_task_id: Optional[str] = None

        self._is_busy = False

        # --- Assembly Logic ---
        # 1. Get role configuration from prompts.yaml
        # Convert enum to string value for config lookup
        role_name = self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)
        role_config = self.config_manager.get_role_config(role_name)
        if not role_config:
            raise ValueError(f"Role '{role_name}' not found in prompts.yaml")

        self.goal = role_config.get('goal')
        self.backstory = role_config.get('backstory')

        # 1.2 Set default behavior: context-aware
        self.static_llm_provider = None
        self.static_llm_model = None

        # 2. Get LLM configuration from llm_bindings.yaml
        llm_binding = self.config_manager.get_llm_binding(role_name)

        if llm_binding:
            # If binding found, this agent uses static LLM specification
            self.static_llm_provider = llm_binding.get('llm_provider')
            self.static_llm_model = llm_binding.get('llm_model')
        else:
            # If no binding found, this agent is context-aware
            self.static_llm_provider = None
            self.static_llm_model = None

        # Handle both enum and string values for role
        role_value = config.role.value if hasattr(config.role, 'value') else str(config.role)
        logger.info(f"Base agent initialized: {self.agent_id} ({role_value})")

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the agent.

        Subclasses should implement this method to perform any
        agent-specific initialization tasks.
        """
        pass

    @abstractmethod
    async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using this agent.

        Args:
            task_data: Data for the task to execute
            context: Execution context and metadata

        Returns:
            Task execution result
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get the capabilities of this agent.

        Returns:
            List of capability names
        """
        pass

    async def create_langchain_agent(self, context: Dict[str, Any], tools: Optional[List[BaseTool]] = None) -> AgentExecutor:
        """
        Create a LangChain AgentExecutor instance using the ReAct framework.

        Args:
            context: Runtime context for LLM selection.
            tools: Optional list of tools to assign to the agent.

        Returns:
            A LangChain AgentExecutor instance configured for ReAct.
        """
        # --- Step 1: Get tools (logic unchanged) ---
        if tools is None:
            if self.tool_integration_manager:
                try:
                    logger.info(f"Getting tools from integration manager for agent {self.config.role.value}")
                    tools = await self.tool_integration_manager.get_tools_for_agent(self.config, context)
                    logger.info(f"Retrieved {len(tools)} tools from integration manager")
                except Exception as e:
                    logger.warning(f"Failed to get tools from integration manager: {e}")
                    tools = []
            else:
                logger.debug(f"No tool integration manager available for agent {self.config.role.value}")
                tools = []

        # Ensure tools is always a list
        if tools is None:
            tools = []

        # --- Step 2: Create LLM adapter (logic unchanged) ---
        adapter_llm = LangChainAdapterLLM(
            manager=self.llm_manager,
            context=context,
            static_provider=self.static_llm_provider,
            static_model=self.static_llm_model
        )

        # --- Step 3: Build ReAct-specific prompt ---
        # ReAct prompt template needs to include `tools`, `tool_names`, `input`, `agent_scratchpad` variables
        prompt_template_str = """
**Your Role:** You are {role}, an AI assistant with the following goal: {goal}
**Background:** {backstory}

**Available Tools:**
You have access to the following tools to help you achieve your goal:
{tools}

**Instructions on How to Respond:**
Use the following format for your thought process:

Thought: you should always think about what to do to solve the user's request.
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation sequence can repeat N times)
Thought: I now have enough information to provide the final answer.
Final Answer: the final answer to the original input question.

Begin!

**User's Request:** {input}
**Your Thought Process:**
{agent_scratchpad}
"""

        backstory = self.backstory
        if self.config.tools_instruction:
            backstory = f"{backstory}\n\n{self.config.tools_instruction}"

        role_value = self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)

        prompt = PromptTemplate.from_template(prompt_template_str).partial(
            role=role_value,
            goal=self.goal,
            backstory=backstory
        )

        # --- Step 4: Create ReAct Agent ---
        agent = create_react_agent(adapter_llm, tools, prompt)

        # --- Step 5: Create Agent Executor ---
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=self.config.verbose,
            max_iterations=self.config.max_iter,
            max_execution_time=self.config.max_execution_time,
            return_intermediate_steps=True,
            handle_parsing_errors=True  # Enable for increased robustness
        )

        return agent_executor

    def to_model(self) -> AgentModel:
        """
        Convert this agent to an AgentModel for persistence/serialization.

        Returns:
            AgentModel representation of this agent
        """
        return AgentModel(
            agent_id=self.agent_id,
            name=self.config.name,
            role=self.config.role,
            agent_type=self.config.agent_type,
            status=self.status,
            is_available=self.status == AgentStatus.ACTIVE,
            current_task_id=self.current_task_id,
            goal=self.config.goal,
            backstory=self.config.backstory,
            verbose=self.config.verbose,
            allow_delegation=self.config.allow_delegation,
            max_iter=self.config.max_iter,
            max_execution_time=self.config.max_execution_time,
            tools=self.config.tools,
            tools_instruction=self.config.tools_instruction,
            capabilities=self.config.capabilities,
            domain_specialization=self.config.domain_specialization,
            domain_knowledge=self.config.domain_knowledge,
            llm_config=self.config.llm_config,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            memory_enabled=self.config.memory_enabled,
            context_window=self.config.context_window,
            memory_data=self.memory_data,
            quality_threshold=self.config.quality_threshold,
            validation_enabled=self.config.validation_enabled,
            total_tasks_executed=self.total_tasks_executed,
            successful_tasks=self.successful_tasks,
            failed_tasks=self.failed_tasks,
            average_execution_time=self.average_execution_time,
            average_quality_score=self.average_quality_score,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_active_at=self.last_active_at,
            created_by="system",  # TODO: Get from context
            team_id=None,  # TODO: Support teams
            metadata=self.config.metadata,
            tags=self.config.tags,
            version="1.0.0"
        )

    async def activate(self) -> None:
        """Activate the agent."""
        if self.status == AgentStatus.ACTIVE:
            logger.debug(f"Agent already active: {self.agent_id}")
            return

        await self.initialize()
        self.status = AgentStatus.ACTIVE
        self.updated_at = datetime.utcnow()
        logger.info(f"Agent activated: {self.agent_id}")

    async def deactivate(self) -> None:
        """Deactivate the agent."""
        self.status = AgentStatus.INACTIVE
        self.current_task_id = None
        self.updated_at = datetime.utcnow()
        logger.info(f"Agent deactivated: {self.agent_id}")

    def set_busy(self, task_id: str) -> None:
        """Mark agent as busy with a specific task."""
        self.status = AgentStatus.BUSY
        self.current_task_id = task_id
        self.last_active_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def set_available(self) -> None:
        """Mark agent as available for new tasks."""
        self.status = AgentStatus.ACTIVE
        self.current_task_id = None
        self.updated_at = datetime.utcnow()

    def is_available(self) -> bool:
        """
        Check if the agent is currently available.
        Returns:
            True if the agent is not busy, False otherwise.
        """
        return not self._is_busy

    def update_performance_metrics(self, execution_time: float, quality_score: Optional[float], success: bool) -> None:
        """
        Update agent performance metrics.

        Args:
            execution_time: Time taken to execute the task
            quality_score: Quality score of the execution (0.0 to 1.0)
            success: Whether the task was successful
        """
        self.total_tasks_executed += 1

        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        # Update average execution time
        if self.average_execution_time is None:
            self.average_execution_time = execution_time
        else:
            self.average_execution_time = (
                (self.average_execution_time * (self.total_tasks_executed - 1) + execution_time)
                / self.total_tasks_executed
            )

        # Update average quality score
        if quality_score is not None:
            if self.average_quality_score is None:
                self.average_quality_score = quality_score
            else:
                self.average_quality_score = (
                    (self.average_quality_score * (self.total_tasks_executed - 1) + quality_score)
                    / self.total_tasks_executed
                )

        self.updated_at = datetime.utcnow()

    def add_memory(self, key: str, value: Any) -> None:
        """
        Add data to agent memory.

        Args:
            key: Memory key
            value: Memory value
        """
        if self.config.memory_enabled:
            self.memory_data[key] = value
            self.updated_at = datetime.utcnow()

    def get_memory(self, key: str, default: Any = None) -> Any:
        """
        Retrieve data from agent memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Memory value or default
        """
        if self.config.memory_enabled:
            return self.memory_data.get(key, default)
        return default

    def clear_memory(self) -> None:
        """Clear agent memory."""
        self.memory_data.clear()
        self.updated_at = datetime.utcnow()

    def validate_config(self) -> List[str]:
        """
        Validate agent configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate required fields
        if not self.config.name:
            errors.append("Agent name is required")

        if not self.config.goal:
            errors.append("Agent goal is required")

        if not self.config.backstory:
            errors.append("Agent backstory is required")

        # Validate numeric constraints
        if self.config.temperature < 0.0 or self.config.temperature > 2.0:
            errors.append("Temperature must be between 0.0 and 2.0")

        if self.config.quality_threshold < 0.0 or self.config.quality_threshold > 1.0:
            errors.append("Quality threshold must be between 0.0 and 1.0")

        if self.config.max_iter <= 0:
            errors.append("Max iterations must be positive")

        if self.config.context_window <= 0:
            errors.append("Context window must be positive")

        return errors

    def __str__(self) -> str:
        """String representation of the agent."""
        # Handle both enum and string values
        role_value = self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)
        status_value = self.status.value if hasattr(self.status, 'value') else str(self.status)
        return f"Agent({self.agent_id}, {role_value}, {status_value})"

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        # Handle both enum and string values
        role_value = self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)
        status_value = self.status.value if hasattr(self.status, 'value') else str(self.status)
        return (
            f"BaseAgent(id={self.agent_id}, role={role_value}, "
            f"status={status_value}, tasks_executed={self.total_tasks_executed})"
        )
