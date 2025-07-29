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

from langchain.agents import AgentExecutor, BaseSingleActionAgent
from langchain.schema import AgentAction, AgentFinish
from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForChainRun
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


class LangChainAgent(BaseSingleActionAgent):
    """
    LangChain-based agent implementation that wraps our custom agent logic.

    This class bridges our custom agent system with LangChain's agent framework,
    providing compatibility while maintaining our existing functionality.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_agent: 'BaseAgent' = Field(...)
    llm: LangChainAdapterLLM = Field(...)
    tools: List[BaseTool] = Field(default_factory=list)
    prompt_template: PromptTemplate = Field(...)

    def __init__(
        self,
        base_agent: 'BaseAgent',
        llm: LangChainAdapterLLM,
        tools: List[BaseTool],
        prompt_template: PromptTemplate,
        **kwargs
    ):
        """
        Initialize the LangChain agent wrapper.

        Args:
            base_agent: The base agent instance
            llm: LangChain-compatible LLM adapter
            tools: List of available tools
            prompt_template: Prompt template for the agent
        """
        super().__init__(
            base_agent=base_agent,
            llm=llm,
            tools=tools,
            prompt_template=prompt_template,
            **kwargs
        )

    @property
    def input_keys(self) -> List[str]:
        """Return the input keys for the agent."""
        return ["input"]

    def plan(
        self,
        intermediate_steps: List[tuple],
        callbacks: Optional[CallbackManagerForChainRun] = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """
        Plan the next action for the agent.

        Args:
            intermediate_steps: Previous actions and observations
            callbacks: Callback manager for the chain run
            **kwargs: Additional arguments

        Returns:
            Next action to take or finish signal
        """
        # Get the input from kwargs
        user_input = kwargs.get("input", "")

        # Format the prompt with current context - only use input_variables
        prompt_vars = {
            "input": user_input,
            "agent_scratchpad": self._format_intermediate_steps(intermediate_steps)
        }

        formatted_prompt = self.prompt_template.format(**prompt_vars)

        # Get response from LLM - use sync method that handles event loop properly
        try:
            import asyncio
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, but this is a sync method
                # Use the sync call method which should handle this properly
                response = self.llm._call(formatted_prompt)
            except RuntimeError:
                # No running loop, safe to use regular call
                response = self.llm(formatted_prompt)
        except Exception as e:
            logger.error(f"Error calling LLM in plan method: {e}")
            # Fallback to a simple response
            response = f"Error: {str(e)}"

        # Parse the response to determine action
        return self._parse_response(response)

    async def aplan(
        self,
        intermediate_steps: List[tuple],
        callbacks: Optional[CallbackManagerForChainRun] = None,
        **kwargs: Any,
    ) -> Union[AgentAction, AgentFinish]:
        """
        Async version of plan method.

        Args:
            intermediate_steps: Previous actions and observations
            callbacks: Callback manager for the chain run
            **kwargs: Additional arguments

        Returns:
            Next action to take or finish signal
        """
        # Get the input from kwargs
        user_input = kwargs.get("input", "")

        # Format the prompt with current context - only use input_variables
        prompt_vars = {
            "input": user_input,
            "agent_scratchpad": self._format_intermediate_steps(intermediate_steps)
        }

        formatted_prompt = self.prompt_template.format(**prompt_vars)

        # Get response from LLM using async method
        response = await self.llm._acall(formatted_prompt)

        # Parse the response to determine action
        return self._parse_response(response)

    def _format_intermediate_steps(self, intermediate_steps: List[tuple]) -> str:
        """Format intermediate steps for the prompt."""
        if not intermediate_steps:
            return ""

        formatted_steps = []
        for action, observation in intermediate_steps:
            formatted_steps.append(f"Action: {action.tool}\nAction Input: {action.tool_input}\nObservation: {observation}")

        return "\n".join(formatted_steps)

    def _format_tools(self) -> str:
        """Format tools description for the prompt."""
        tool_descriptions = []
        for tool in self.tools:
            tool_descriptions.append(f"{tool.name}: {tool.description}")
        return "\n".join(tool_descriptions)

    def _parse_response(self, response: str) -> Union[AgentAction, AgentFinish]:
        """
        Parse LLM response to determine next action.

        Args:
            response: Raw LLM response

        Returns:
            AgentAction or AgentFinish
        """
        # Simple parsing logic - can be enhanced with more sophisticated parsing
        response = response.strip()

        # Check if this is a final answer
        if "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
            return AgentFinish(
                return_values={"output": final_answer},
                log=response
            )

        # Try to extract action and input
        if "Action:" in response and "Action Input:" in response:
            try:
                action_part = response.split("Action:")[1].split("Action Input:")[0].strip()
                input_part = response.split("Action Input:")[1].strip()

                # Find matching tool
                tool_name = action_part
                for tool in self.tools:
                    if tool.name.lower() == tool_name.lower():
                        return AgentAction(
                            tool=tool.name,
                            tool_input=input_part,
                            log=response
                        )
            except Exception as e:
                logger.warning(f"Failed to parse action from response: {e}")

        # Default to finishing if we can't parse an action
        return AgentFinish(
            return_values={"output": response},
            log=response
        )


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

        # LangChain agent instance
        self._langchain_agent: Optional[AgentExecutor] = None

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
        Create a LangChain AgentExecutor instance using the assembled configuration and smart adapter.

        Args:
            context: Runtime context for LLM selection
            tools: Optional list of tools to assign to the agent

        Returns:
            LangChain AgentExecutor instance with smart LLM adapter and integrated tools
        """
        # Get tools from integration manager if available and no tools provided
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

        # Create the smart adapter LLM
        adapter_llm = LangChainAdapterLLM(
            manager=self.llm_manager,
            context=context,
            static_provider=self.static_llm_provider,
            static_model=self.static_llm_model
        )

        # Prepare backstory with tools instruction if available
        backstory = self.backstory
        if self.config.tools_instruction:
            backstory = f"{backstory}\n\n{self.config.tools_instruction}"

        # Create prompt template for the agent
        role_value = self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)

        # Format tools for the prompt
        if tools:
            tools_description = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
            tool_names = ", ".join([tool.name for tool in tools])
        else:
            tools_description = "No tools available"
            tool_names = "none"

        prompt_template = PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template="""You are {role}, an AI assistant with the following goal: {goal}

Background: {backstory}

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}""",
            partial_variables={
                "role": role_value,
                "goal": self.goal,
                "backstory": backstory,
                "tools": tools_description,
                "tool_names": tool_names
            }
        )

        # Create the LangChain agent wrapper
        langchain_agent = LangChainAgent(
            base_agent=self,
            llm=adapter_llm,
            tools=tools or [],
            prompt_template=prompt_template
        )

        # Create AgentExecutor
        agent_executor = AgentExecutor(
            agent=langchain_agent,
            tools=tools or [],
            verbose=self.config.verbose,
            max_iterations=self.config.max_iter,
            max_execution_time=self.config.max_execution_time,
            return_intermediate_steps=True
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
