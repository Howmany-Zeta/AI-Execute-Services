"""
Base Agent

Provides the base class for all agents in the multi-task service,
implementing common functionality and the agent interface using LangChain.
"""

import uuid
import asyncio
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

from langchain.agents import AgentExecutor, create_react_agent, create_tool_calling_agent
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from pydantic import Field, ConfigDict

from ..core.interfaces.agent_manager import IAgentManager
from ..core.models.agent_models import AgentConfig, AgentModel, AgentRole
from ..core.models.shared_enums import AgentStatus, AgentType
from ..core.exceptions.task_exceptions import TaskValidationError
from ..config.config_manager import ConfigManager
from .langchain_adapter_llm import LangChainAdapterLLM
from app.services.llm_integration import LLMIntegrationManager
from ..tools.langchain_adapter import LangChainToolsProvider

# Import standardized data models and interfaces (keeping for potential future use)
from ..core.models.react_agent_models import (
    ReactAgentFinalPromptData,
    ReactPromptConstructionResult
)
from ..core.models.services_models import (
    ServiceToAgentDataPackage,
    StandardizedServiceTaskData,
    StandardizedServiceContext
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-task service.

    Provides common functionality for agent lifecycle management,
    configuration handling, and integration with LangChain.
    """

    def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager: Optional[LangChainToolsProvider] = None):
        """
        Initialize the base agent with configuration-driven setup.

        Args:
            config: Agent configuration containing role, goal, backstory, etc.
            config_manager: Configuration manager for accessing prompts.yaml and llm_bindings.yaml
            llm_manager: LLM integration manager for dynamic LLM selection
            tool_integration_manager: Optional LangChain tools provider (simplified from LangChainIntegrationManager)
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

        # Conversation history management
        self.conversation_history: List[Dict[str, Any]] = []
        self.context_engine = None  # Will be set by AgentManager if available
        self.current_session_id: Optional[str] = None
        self.conversation_context: Dict[str, Any] = {}

        self._is_busy = False

        # --- Assembly Logic ---
        # 1. Get role configuration from prompts.yaml
        # Convert enum to string value for config lookup
        role_name = self.role_value
        role_config = self.config_manager.get_role_config(role_name)
        if not role_config:
            raise ValueError(f"Role '{role_name}' not found in prompts.yaml")

        self.goal = role_config.get('goal')
        self.backstory = role_config.get('backstory')
        self.reasoning_guidance = role_config.get('reasoning_guidance', 'Follow standard problem-solving approach.')

        # Get reasoning request from role config or agent config
        # Priority: agent config > role config > default
        self.reasoning_request = (
            self.config.reasoning_request or
            self.config_manager.get_role_reasoning_request(role_name) or
            'conventional reasoning'
        )

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

        # 统一重试配置 - 截断指数退避算法
        self.retry_config = {
            'max_retries': 5,           # 最大重试次数
            'base_delay': 1.0,          # 基础延迟(秒)
            'max_delay': 32.0,          # 最大延迟(秒) - 截断值
            'exponential_factor': 2.0,   # 指数因子
            'jitter_factor': 0.2,       # 抖动因子 ±20%
            'rate_limit_base_delay': 5.0,  # 速率限制专用基础延迟
            'rate_limit_max_delay': 120.0, # 速率限制专用最大延迟
        }

        # 从配置文件中覆盖重试参数（如果存在）
        if role_config and 'retry_config' in role_config:
            self.retry_config.update(role_config['retry_config'])

        logger.info(f"Base agent initialized: {self.agent_id} ({self.role_value})")

    @property
    def role_value(self) -> str:
        """
        Get the string representation of the agent's role.

        Returns:
            String value of the role, handling both enum and string types
        """
        return self.config.role.value if hasattr(self.config.role, 'value') else str(self.config.role)

    def _extract_task_info(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> tuple[str, str]:
        """
        Extract task_description and expected_output with fallback logic.

        Args:
            task_data: Complete task data dictionary
            context: Optional context dictionary (fallback source)

        Returns:
            Tuple of (task_description, expected_output) with fallback handling
        """
        # Priority: task_data > context > None
        task_description = self._safe_get_from_task_data(task_data, 'task_description')
        expected_output = self._safe_get_from_task_data(task_data, 'expected_output')

        # Fallback to context if not found in task_data
        if not task_description:
            task_description = self._safe_get_from_context(context, 'task_description')

        if not expected_output:
            expected_output = self._safe_get_from_context(context, 'expected_output')

        return task_description, expected_output

    def _has_valid_task_description(self, task_description: str) -> bool:
        """
        Check if task_description is valid and not a placeholder.

        Args:
            task_description: Task description to validate

        Returns:
            True if task description is valid, False otherwise
        """
        return bool(task_description and
                   task_description.strip() and
                   task_description != 'No specific task description provided.')

    def _build_knowledge_section(self, role_config: Dict[str, Any]) -> str:
        """
        Build the knowledge section combining domain_knowledge and domain_specialization.

        Args:
            role_config: Role configuration from prompts.yaml

        Returns:
            Formatted knowledge section string
        """
        knowledge_parts = []

        # Get domain knowledge from role config
        domain_knowledge = role_config.get('domain_knowledge', '') if role_config else ''

        # Get domain specialization with agent config taking priority
        domain_specialization = role_config.get('domain_specialization', '') if role_config else ''
        if hasattr(self.config, 'domain_specialization') and self.config.domain_specialization:
            domain_specialization = self.config.domain_specialization

        # Format domain knowledge
        if domain_knowledge:
            if isinstance(domain_knowledge, dict):
                knowledge_parts.append("Domain Knowledge:")
                for key, value in domain_knowledge.items():
                    knowledge_parts.append(f"- {key}: {value}")
            else:
                knowledge_parts.append(f"Domain Knowledge: {domain_knowledge}")

        # Add domain specialization
        if domain_specialization:
            knowledge_parts.append(f"Domain Specialization: {domain_specialization}")

        # Return formatted section or default
        return "\n".join(knowledge_parts) if knowledge_parts else "General knowledge and reasoning capabilities."

    def _build_do_not_list_section(self, role_config: Dict[str, Any]) -> str:
        """
        Build the do_not_list section from role configuration.

        Args:
            role_config: Role configuration from prompts.yaml

        Returns:
            Formatted do_not_list section string
        """
        do_not_list = role_config.get('do_not_list', []) if role_config else []

        if do_not_list and len(do_not_list) > 0:
            do_not_list_items = "\n".join([f"- {item}" for item in do_not_list])
            return f"**Do NOT:**\n{do_not_list_items}\n"

        return ""

    def _is_valid_task_data(self, task_data: Any) -> bool:
        """
        Check if task_data is a valid dictionary.

        Args:
            task_data: Task data to validate

        Returns:
            True if task_data is a non-empty dictionary, False otherwise
        """
        return isinstance(task_data, dict) and bool(task_data)

    def _is_valid_context(self, context: Any) -> bool:
        """
        Check if context is a valid dictionary.

        Args:
            context: Context to validate

        Returns:
            True if context is a dictionary, False otherwise
        """
        return isinstance(context, dict)

    def _safe_get_from_task_data(self, task_data: Any, key: str, default: Any = None) -> Any:
        """
        Safely get a value from task_data if it's a valid dictionary.

        Args:
            task_data: Task data dictionary or other type
            key: Key to retrieve
            default: Default value if key not found or task_data invalid

        Returns:
            Value from task_data or default
        """
        return task_data.get(key, default) if isinstance(task_data, dict) else default

    def _safe_get_from_context(self, context: Any, key: str, default: Any = None) -> Any:
        """
        Safely get a value from context if it's a valid dictionary.

        Args:
            context: Context dictionary or other type
            key: Key to retrieve
            default: Default value if key not found or context invalid

        Returns:
            Value from context or default
        """
        return context.get(key, default) if isinstance(context, dict) else default

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

    async def create_final_prompt(self, context: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None, tools: Optional[List[BaseTool]] = None) -> Union[PromptTemplate, ChatPromptTemplate]:
        """
        Create the final prompt based on reasoning_request type.

        Args:
            context: Runtime context for LLM selection
            task_data: Optional task-specific data containing task_description and expected_output
            tools: Optional list of tools to assign to the agent

        Returns:
            PromptTemplate for ReAct or ChatPromptTemplate for tool calling
        """
        # Validate reasoning_request
        if self.reasoning_request not in ['complex reasoning', 'conventional reasoning']:
            logger.warning(f"Invalid reasoning_request '{self.reasoning_request}', defaulting to 'conventional reasoning'")
            self.reasoning_request = 'conventional reasoning'

        # Ensure tools is always a list
        if tools is None:
            tools = []

        # Determine prompt type based on reasoning request and tools availability
        if self.reasoning_request == 'complex reasoning':
            has_tools = len(tools) > 0
            if has_tools:
                # Complex reasoning + has tools - use full ReAct prompt with tools
                return await self._create_react_prompt(context, task_data, tools)
            else:
                # Complex reasoning + no tools - use simplified ReAct prompt without tools
                return await self._create_react_prompt_without_tools(context, task_data)
        else:
            # Conventional reasoning - use tool calling prompt (works with or without tools)
            return await self._create_tool_calling_prompt(context, task_data, tools)

    async def _create_react_prompt(self, context: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None, tools: Optional[List[BaseTool]] = None) -> PromptTemplate:
        """
        Create ReAct prompt for complex reasoning.

        Args:
            context: Runtime context
            task_data: Task-specific data
            tools: List of available tools

        Returns:
            PromptTemplate configured for ReAct
        """
        # Load and format conversation history
        conversation_history_text = await self._get_formatted_conversation_history()

        # Determine if tools are available
        has_tools = tools and len(tools) > 0

        # Use a unified ReAct prompt template that works with or without tools
        # LangChain will automatically handle the tools section based on the tools list
        prompt_template_str = """**AGENT PROFILE:**
**Your Role:** You are {role}, an AI assistant with the following goal: {goal}
**Background:** Here is your background: {backstory}
**Thought Process:** Use this {reasoning_guidance} to guide your thought
**Responsibility:** Always remember your duties {core_responsibilities}
**Requirements:** During your work, do not miss these specific requirements {specific_requirements}
**Knowledge:** {knowledge_section}
{do_not_list_section}

{conversation_history_section}

**Available Tools:**
You have access to the following tools to help you achieve your goal:
{tools}

**REACT FORMAT REQUIREMENTS:**
You MUST follow this EXACT format for every response. This is critical for proper execution:

```
Thought: [Your reasoning about what to do next - be specific and clear]
Action: [MUST be exactly one of: {tool_names}]
Action Input: [The exact input for the action - be precise]
Observation: [This will be filled automatically with the tool result]
... (You may repeat Thought/Action/Action Input/Observation cycles as needed)
Thought: [Your final reasoning based on all observations]
Final Answer: [Your complete, comprehensive final response]
```

**CRITICAL RULES:**
1. EVERY Thought MUST be followed by either an Action OR Final Answer
2. NEVER end a response with just a Thought - always include Action or Final Answer
3. Action names must EXACTLY match one of: {tool_names}
4. If you have all needed information, go directly to Final Answer
5. Your Final Answer should be complete and comprehensive
6. Do NOT repeat the same Action multiple times without progress
7. There should be no more text after the complete final answer

Begin!

{task_assignment_section}

**CURRENT REQUEST:**
**User Input:** {input}

{execution_instructions}

**Your Scratchpad:** {agent_scratchpad}
"""

        # Build prompt sections using existing helper methods
        role_config = self.config_manager.get_role_config(self.role_value)
        core_responsibilities = role_config.get('core_responsibilities', '') if role_config else ''
        specific_requirements = role_config.get('specific_requirements', '') if role_config else ''

        do_not_list_section = self._build_do_not_list_section(role_config)
        knowledge_section = self._build_knowledge_section(role_config)

        task_assignment_section = self._build_task_assignment_section(task_data or {}, context)
        execution_instructions = self._build_execution_instructions(task_data or {}, context)

        # Format conversation history section
        conversation_history_section = ""
        if conversation_history_text and conversation_history_text != "No previous conversation history.":
            conversation_history_section = f"**CONVERSATION CONTEXT:**\n{conversation_history_text}\n"

        # Create prompt template - note that {tools}, {tool_names}, {input}, and {agent_scratchpad}
        # are required by LangChain and will be filled automatically by create_react_agent
        prompt = PromptTemplate.from_template(prompt_template_str).partial(
            role=self.role_value,
            goal=self.goal,
            backstory=self.backstory,
            reasoning_guidance=self.reasoning_guidance,
            core_responsibilities=core_responsibilities,
            specific_requirements=specific_requirements,
            knowledge_section=knowledge_section,
            do_not_list_section=do_not_list_section,
            conversation_history_section=conversation_history_section,
            task_assignment_section=task_assignment_section,
            execution_instructions=execution_instructions
        )

        return prompt

    async def _create_react_prompt_without_tools(self, context: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None) -> PromptTemplate:
        """
        Create ReAct prompt template for agents without tools.
        This version removes Action/Observation cycle and focuses on direct reasoning.

        Args:
            context: Runtime context
            task_data: Task-specific data

        Returns:
            PromptTemplate configured for ReAct without tools
        """
        # Load and format conversation history
        conversation_history_text = await self._get_formatted_conversation_history()

        # Use a simplified ReAct prompt template without Action/Observation cycle
        # Note: {tools} and {tool_names} are required by LangChain even when empty
        prompt_template_str = """**AGENT PROFILE:**
**Your Role:** You are {role}, an AI assistant with the following goal: {goal}
**Background:** Here is your background: {backstory}
**Thought Process:** Use this {reasoning_guidance} to guide your thought
**Responsibility:** Always remember your duties {core_responsibilities}
**Requirements:** During your work, do not miss these specific requirements {specific_requirements}
**Knowledge:** {knowledge_section}
{do_not_list_section}

{conversation_history_section}

**Available Tools:**
{tools}

**Instructions on How to Respond:**
Since no tools [{tool_names}] are available, use direct reasoning with the following format:

Thought: you should always think step by step about what to do to solve the user's request.
Final Answer: the final answer to the original input question.

Focus on:
1. Understanding the question thoroughly
2. Breaking down complex problems into steps
3. Using your knowledge and reasoning capabilities
4. Providing clear, well-structured answers

Begin!

{task_assignment_section}

**CURRENT REQUEST:**
**User Input:** {input}

{execution_instructions}

**Your Scratchpad:** {agent_scratchpad}
"""

        # Build prompt sections using existing helper methods
        role_config = self.config_manager.get_role_config(self.role_value)
        core_responsibilities = role_config.get('core_responsibilities', '') if role_config else ''
        specific_requirements = role_config.get('specific_requirements', '') if role_config else ''

        do_not_list_section = self._build_do_not_list_section(role_config)
        knowledge_section = self._build_knowledge_section(role_config)

        task_assignment_section = self._build_task_assignment_section(task_data or {}, context)
        execution_instructions = self._build_execution_instructions(task_data or {}, context)

        # Format conversation history section
        conversation_history_section = ""
        if conversation_history_text and conversation_history_text != "No previous conversation history.":
            conversation_history_section = f"**CONVERSATION CONTEXT:**\n{conversation_history_text}\n"

        # Create prompt template for no-tools scenario
        # Note: {tools}, {tool_names}, {input}, and {agent_scratchpad} must remain as template variables for LangChain
        prompt = PromptTemplate.from_template(prompt_template_str).partial(
            role=self.role_value,
            goal=self.goal,
            backstory=self.backstory,
            reasoning_guidance=self.reasoning_guidance,
            core_responsibilities=core_responsibilities,
            specific_requirements=specific_requirements,
            knowledge_section=knowledge_section,
            do_not_list_section=do_not_list_section,
            conversation_history_section=conversation_history_section,
            task_assignment_section=task_assignment_section,
            execution_instructions=execution_instructions
        )

        return prompt

    async def _create_tool_calling_prompt(self, context: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None, tools: Optional[List[BaseTool]] = None) -> ChatPromptTemplate:
        """
        Create tool calling prompt for conventional reasoning.

        Args:
            context: Runtime context
            task_data: Task-specific data
            tools: List of available tools

        Returns:
            ChatPromptTemplate configured for tool calling
        """
        # Load and format conversation history
        conversation_history_text = await self._get_formatted_conversation_history()

        # Build prompt sections using existing helper methods
        role_config = self.config_manager.get_role_config(self.role_value)
        core_responsibilities = role_config.get('core_responsibilities', '') if role_config else ''
        specific_requirements = role_config.get('specific_requirements', '') if role_config else ''

        do_not_list_section = self._build_do_not_list_section(role_config)
        knowledge_section = self._build_knowledge_section(role_config)

        task_assignment_section = self._build_task_assignment_section(task_data or {}, context)
        execution_instructions = self._build_execution_instructions(task_data or {}, context)

        # Format conversation history section
        conversation_history_section = ""
        if conversation_history_text and conversation_history_text != "No previous conversation history.":
            conversation_history_section = f"**CONVERSATION CONTEXT:**\n{conversation_history_text}\n"

        # Create system message for tool calling (only static profile information)
        system_message = f"""**AGENT PROFILE:**
**Your Role:** You are {self.role_value}, an AI assistant with the following goal: {self.goal}
**Background:** Here is your background: {self.backstory}
**Thought Process:** Use this {self.reasoning_guidance} to guide your thought
**Responsibility:** Always remember your duties {core_responsibilities}
**Requirements:** During your work, do not miss these specific requirements {specific_requirements}
**Knowledge:** {knowledge_section}
{do_not_list_section}

You have access to tools that can help you complete tasks. Use them when appropriate to provide accurate and helpful responses."""

        # Create human message template with proper order:
        human_message_parts = []

        if conversation_history_section:
            human_message_parts.append(conversation_history_section)

        if task_assignment_section:
            human_message_parts.append(task_assignment_section)

        human_message_parts.append("{input}")

        if execution_instructions:
            human_message_parts.append(execution_instructions)

        human_message_template = "\n\n".join(human_message_parts)

        # Create ChatPromptTemplate for tool calling
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message_template),
            ("placeholder", "{agent_scratchpad}")
        ])

        return prompt


    async def create_langchain_agent(self, context: Dict[str, Any], task_data: Optional[Dict[str, Any]] = None, tools: Optional[List[BaseTool]] = None) -> AgentExecutor:
        """
        Create a LangChain AgentExecutor instance with optimized agent selection logic.

        Args:
            context: Runtime context for LLM selection.
            task_data: Optional task-specific data containing task_description and expected_output.
            tools: Optional list of tools to assign to the agent.

        Returns:
            A LangChain AgentExecutor instance configured for ReAct or Tool Calling.
        """
        logger.info(f"Creating LangChain agent for {self.role_value} with reasoning_request: {self.reasoning_request}")

        # --- Step 1: Ensure tools is always a list ---
        if tools is None:
            tools = []

        # --- Step 2: Create prompt based on optimized logic ---
        prompt = await self.create_final_prompt(context, task_data, tools)

        # --- DEBUG: Final prompt information ---
        print(f"� FINAL PROMPT DEBUG:")
        print(f"📋 Prompt type: {type(prompt).__name__}")
        print(f"📋 Reasoning request: {self.reasoning_request}")
        print(f"📋 Tools count: {len(tools)}")
        if hasattr(prompt, 'input_variables'):
            print(f"📋 Input variables: {prompt.input_variables}")
        elif hasattr(prompt, 'messages'):
            print(f"📋 Message count: {len(prompt.messages)}")

        logger.debug(f"Created prompt for agent {self.role_value} with reasoning_request: {self.reasoning_request}")

        # --- Step 3: Create Agent based on reasoning request ---
        if self.reasoning_request == 'complex reasoning':
            # Complex reasoning - use ReAct agent (with or without tools)
            has_tools = len(tools) > 0

            try:
                adapter_llm = LangChainAdapterLLM(
                    manager=self.llm_manager,
                    context=context,
                    static_provider=self.static_llm_provider,
                    static_model=self.static_llm_model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )

                agent = create_react_agent(adapter_llm, tools, prompt)
                logger.info(f"Created ReAct agent for {self.role_value} (complex reasoning, {'with' if has_tools else 'without'} tools)")

            except Exception as e:
                error_msg = f"Failed to create ReAct agent (complex reasoning): {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        else:
            # Conventional reasoning - use Tool Calling agent
            try:
                from .langchain_adapter_llm import LangChainAdapterChatModel
                adapter_chat_model = LangChainAdapterChatModel(
                    manager=self.llm_manager,
                    context=context,
                    static_provider=self.static_llm_provider,
                    static_model=self.static_llm_model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )

                agent = create_tool_calling_agent(adapter_chat_model, tools, prompt)
                logger.info(f"Created Tool Calling agent for {self.role_value}")

            except Exception as e:
                error_msg = f"Failed to create Tool Calling agent: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        # --- Step 4: Create Agent Executor ---
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,  # Pass tools list (empty or populated) - LangChain handles both cases
            verbose=self.config.verbose,
            max_iterations=self.config.max_iter,
            max_execution_time=self.config.max_execution_time,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )

        logger.info(f"Created AgentExecutor for {self.role_value}")
        return agent_executor

    def _build_task_assignment_section(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        Build conditional task assignment section based on task_data and context content.

        Args:
            task_data: Complete task data dictionary
            context: Optional context dictionary (fallback for task_description and expected_output)

        Returns:
            Formatted task assignment section
        """
        # Extract task information using centralized helper
        task_description, expected_output = self._extract_task_info(task_data, context)

        # Check if task_description is valid
        has_valid_task_description = self._has_valid_task_description(task_description)

        if has_valid_task_description:
            # PREDEFINED mode: explicit task without task_data (moved to execution instructions)
            result = f"""**TASK ASSIGNMENT:**
**Your Task:** {task_description}
**Expected Output:** {expected_output or 'Complete the assigned task effectively'}"""
        else:
            # COMPREHENSIVE mode: parse from input without task_data (moved to execution instructions)
            result = f"""**TASK ASSIGNMENT:**
**Note:** No predefined task description provided. Your task details are contained in the user input below.
**Instruction:** Carefully analyze the user input to understand the complete task requirements, expected output format, and any specific constraints."""

        return result

    def _build_execution_instructions(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """
        Build execution instructions based on whether task has predefined description.
        Now includes task data section to ensure it's always available.

        Args:
            task_data: Complete task data dictionary
            context: Optional context dictionary (fallback for task_description)

        Returns:
            Formatted execution instructions with task data
        """
        # Extract task information using centralized helper
        task_description, _ = self._extract_task_info(task_data, context)

        # Build task data section (always included regardless of mode)
        task_data_section = ""
        if self._is_valid_task_data(task_data):
            task_data_lines = ["**Here is the data related to this task, you should use it correctly:**"]
            for key, value in task_data.items():
                if isinstance(value, dict):
                    # Convert dict to a safe string representation that avoids template variable conflicts
                    import json
                    try:
                        # Use JSON dumps but then escape any remaining braces
                        value_str = json.dumps(value, ensure_ascii=False)[:200]
                        # Double escape all curly braces to prevent LangChain template interpretation
                        value_str = value_str.replace('{', '{{').replace('}', '}}')
                    except (TypeError, ValueError):
                        # Fallback to string representation with escaping
                        value_str = str(value)[:200]
                        value_str = value_str.replace('{', '{{').replace('}', '}}')
                    task_data_lines.append(f"- {key}: {value_str}{'...' if len(str(value)) > 200 else ''}")
                elif isinstance(value, (list, tuple)):
                    # Handle lists/tuples similarly
                    import json
                    try:
                        value_str = json.dumps(value, ensure_ascii=False)[:200]
                        value_str = value_str.replace('{', '{{').replace('}', '}}')
                    except (TypeError, ValueError):
                        value_str = str(value)[:200]
                        value_str = value_str.replace('{', '{{').replace('}', '}}')
                    task_data_lines.append(f"- {key}: {value_str}{'...' if len(str(value)) > 200 else ''}")
                else:
                    # Handle simple values with escaping
                    value_str = str(value)
                    value_str = value_str.replace('{', '{{').replace('}', '}}')
                    task_data_lines.append(f"- {key}: {value_str}")
            task_data_section = "\n".join(task_data_lines)

        # Build instructions based on task type
        if self._has_valid_task_description(task_description):
            instructions = """**Instructions:**
Execute the assigned task according to the specifications above, using the user input as additional context or data."""
        else:
            instructions = """**Instructions:**
Extract the complete task requirements from the user input, including what needs to be done, how it should be formatted, and any quality requirements. Then execute accordingly."""

        # Combine instructions with task data section
        if task_data_section:
            return f"""{instructions}

{task_data_section}"""
        else:
            return instructions

    def get_prompt_construction_info(self, task_data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get information about how the prompt will be constructed for this agent.

        Updated for new data flow: shows conditional prompt construction based on task_data content.
        Provides transparency into the optimized prompt construction process with reduced data packaging.

        Args:
            task_data: Complete task-specific data (no longer re-packaged)
            context: Optional execution context

        Returns:
            Dictionary containing detailed prompt construction information
        """
        # Static agent information (from prompts.yaml and agent config)
        static_info = {
            "role": self.role_value,
            "goal": self.config.goal,
            "backstory": self.backstory,
            "reasoning_guidance": self.reasoning_guidance,
            "static_llm_provider": self.static_llm_provider,
            "static_llm_model": self.static_llm_model,
            "domain_knowledge": getattr(self.config, 'domain_knowledge', None),
            "domain_specialization": getattr(self.config, 'domain_specialization', None)
        }

        # Analyze task data for conditional prompt construction
        task_data = task_data or {}
        context = context or {}

        # Extract task information using centralized helper
        task_description, expected_output = self._extract_task_info(task_data, context)
        has_predefined_task = self._has_valid_task_description(task_description)

        # Build conditional sections (simulate what will happen during execution)
        task_assignment_section = self._build_task_assignment_section(task_data, context)
        execution_instructions = self._build_execution_instructions(task_data, context)

        # Complete task information analysis
        dynamic_info = {
            "task_description": task_description or "No specific task description provided",
            "expected_output": expected_output or "No specific expected output provided",
            "task_type": task_data.get('task_type') or context.get('task_type') or "standard",
            "has_predefined_task": has_predefined_task,
            "prompt_mode": "predefined_task" if has_predefined_task else "comprehensive_task",
            "business_data_preserved": bool([k for k in task_data.keys() if k not in ['task_description', 'expected_output', 'task_name', 'task_type']]),
            "complete_task_data_keys": list(task_data.keys()),
            "task_assignment_section": task_assignment_section,
            "execution_instructions": execution_instructions
        }

        # Input formatting analysis
        input_formatting_info = self._analyze_input_formatting(task_data)

        return {
            "agent_id": self.agent_id,
            "data_flow_version": "optimized_v2",
            "optimization_summary": {
                "data_packaging_layers": "Reduced from 6 to 3 layers",
                "data_preservation": "Complete task_data preserved throughout flow",
                "conditional_prompting": "Dynamic prompt based on task type",
                "input_formatting": "Service layer responsibility via TaskInputFormatter"
            },
            "prompt_construction_flow": [
                "1. Load static agent information from prompts.yaml (role, goal, backstory, reasoning_guidance)",
                "2. Load LLM binding from llm_binding.yaml (if exists) or use dynamic selection",
                "3. Receive COMPLETE task_data directly from AgentManager (no re-packaging)",
                "4. Analyze task_data to determine prompt mode (predefined vs comprehensive)",
                "5. Build conditional task_assignment_section based on task type",
                "6. Build conditional execution_instructions based on task type",
                "7. Combine static info + conditional sections into ReAct prompt template",
                "8. TaskInputFormatter generates appropriate input based on task type",
                "9. Create LangChain AgentExecutor with optimized prompt"
            ],
            "static_agent_info": static_info,
            "dynamic_task_info": dynamic_info,
            "input_formatting_info": input_formatting_info,
            "prompt_template_variables": [
                "role", "goal", "backstory", "reasoning_guidance",
                "core_responsibilities", "specific_requirements", "knowledge_section",
                "do_not_list_section", "conversation_history_section",
                "task_assignment_section", "execution_instructions",
                "tools", "tool_names", "input", "agent_scratchpad"
            ],
            "conditional_sections": {
                "task_assignment_section": {
                    "description": "Dynamic section based on task type",
                    "predefined_mode": "Shows explicit task and expected output",
                    "comprehensive_mode": "Instructs agent to parse task from input"
                },
                "execution_instructions": {
                    "description": "Dynamic instructions based on task type",
                    "predefined_mode": "Execute assigned task using input as data",
                    "comprehensive_mode": "Extract task requirements from input then execute"
                }
            }
        }

    def _analyze_input_formatting(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how input will be formatted for this task_data.

        Args:
            task_data: Complete task data dictionary

        Returns:
            Dictionary containing input formatting analysis
        """
        task_description = self._safe_get_from_task_data(task_data, 'task_description')
        has_task_description = self._has_valid_task_description(task_description)

        # Simulate TaskInputFormatter behavior
        business_data = {}
        if self._is_valid_task_data(task_data):
            business_data = {k: v for k, v in task_data.items()
                            if k not in ['task_description', 'expected_output', 'task_name', 'task_type']}

        if has_task_description:
            input_format = "concise_execution_trigger"
            input_content = "Execute assigned task with business data as JSON"
        else:
            input_format = "comprehensive_task_specification"
            input_content = "Complete task requirements with detailed specifications"

        return {
            "input_format_type": input_format,
            "input_content_type": input_content,
            "has_business_data": bool(business_data),
            "business_data_keys": list(business_data.keys()),
            "formatter_class": "TaskInputFormatter",
            "formatting_method": f"format_{self.role_value.lower()}_input",
            "input_preview": self._generate_input_preview(task_data)
        }

    def _generate_input_preview(self, task_data: Dict[str, Any]) -> str:
        """
        Generate a preview of what the input would look like.

        Args:
            task_data: Complete task data dictionary

        Returns:
            Preview string of formatted input
        """
        task_description = self._safe_get_from_task_data(task_data, 'task_description')
        has_task_description = self._has_valid_task_description(task_description)

        if has_task_description:
            business_data = {}
            if self._is_valid_task_data(task_data):
                business_data = {k: v for k, v in task_data.items()
                               if k not in ['task_description', 'expected_output', 'task_name', 'task_type']}
            if business_data:
                return f"Execute the assigned task with the following data:\n{str(business_data)[:200]}..."
            else:
                return "Execute the assigned task according to your role and capabilities."
        else:
            # Simulate comprehensive format
            role_name = self.role_value.lower()
            if role_name == 'writer':
                content_type = task_data.get('content_type', 'content')
                return f"Generate {content_type} content based on the following requirements:\n[Detailed specifications...]"
            elif role_name == 'analyst':
                analysis_type = task_data.get('analysis_type', 'general')
                return f"Analyze the provided data with the following specifications:\nAnalysis Type: {analysis_type}\n[Detailed requirements...]"
            else:
                return f"Execute {role_name} task with the following specifications:\n[Detailed requirements...]"

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

    def extract_original_output(self, result: Dict[str, Any]) -> str:
        """
        Extract the original output field from LangChain's result.

        This method removes <thinking> tags to ensure clean separation between
        reasoning (extracted separately) and actual output.

        Args:
            result: LangChain execution result dictionary

        Returns:
            Cleaned output string with <thinking> tags removed
        """
        import re

        if not isinstance(result, dict):
            return str(result)

        # Extract the actual output from LangChain result
        actual_output = result.get('output', str(result))

        # Remove <thinking> tags from actual_output to ensure clean separation
        # The reasoning content is extracted separately by extract_reasoning_process()
        thinking_pattern = r'<thinking>.*?</thinking>\s*'
        cleaned_output = re.sub(thinking_pattern, '', actual_output, flags=re.DOTALL)

        return cleaned_output.strip()

    def extract_reasoning_process(self, result: Dict[str, Any], actual_output: str = None) -> str:
        """
        Extract the reasoning process (Thought: sections) from LangChain's execution result.
        Enhanced to handle both ReAct and Tool Calling agent formats.

        Args:
            result: LangChain execution result dictionary
            actual_output: Optional actual output string (fallback source)

        Returns:
            Extracted reasoning process or empty string if not found
        """
        import re

        reasoning_parts = []

        if isinstance(result, dict):
            # Method 1: Extract from intermediate_steps (most comprehensive for ReAct agents)
            intermediate_steps = result.get('intermediate_steps', [])
            if intermediate_steps:
                for step in intermediate_steps:
                    if isinstance(step, tuple) and len(step) >= 2:
                        # step[0] is AgentAction, step[1] is observation
                        agent_action = step[0]
                        observation = step[1]

                        # Extract thought from agent action
                        if hasattr(agent_action, 'log'):
                            log_content = agent_action.log
                            # Extract thought from the log
                            thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', log_content, re.DOTALL)
                            if thought_match:
                                thought = thought_match.group(1).strip()
                                reasoning_parts.append(f"Thought: {thought}")

                            # Extract action
                            action_match = re.search(r'Action:\s*(.*?)(?=\nAction Input:|$)', log_content, re.DOTALL)
                            if action_match:
                                action = action_match.group(1).strip()
                                reasoning_parts.append(f"Action: {action}")

                            # Extract action input
                            input_match = re.search(r'Action Input:\s*(.*?)$', log_content, re.DOTALL)
                            if input_match:
                                action_input = input_match.group(1).strip()
                                reasoning_parts.append(f"Action Input: {action_input}")

                        # Add observation
                        if observation:
                            reasoning_parts.append(f"Observation: {str(observation)}")

            # Method 2: Extract from <thinking> tags (for Tool Calling agents)
            if not reasoning_parts and actual_output:
                thinking_pattern = r'<thinking>\s*(.*?)\s*</thinking>'
                thinking_match = re.search(thinking_pattern, actual_output, re.DOTALL)
                if thinking_match:
                    thinking_content = thinking_match.group(1).strip()
                    reasoning_parts.append(f"Thinking Process:\n{thinking_content}")

            # Method 3: Extract from verbose output if available (for ReAct agents without tools)
            if not reasoning_parts:
                verbose_output = result.get('_verbose_output', '')
                if verbose_output:
                    # Extract all Thought sections from verbose output
                    thought_pattern = r'Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)'
                    thought_matches = re.findall(thought_pattern, verbose_output, re.DOTALL)
                    for thought in thought_matches:
                        reasoning_parts.append(f"Thought: {thought.strip()}")

            # Method 4: Extract ReAct format from actual_output (fallback)
            if not reasoning_parts and actual_output:
                # Look for complete ReAct format in actual output
                react_pattern = r'(Thought:.*?)(?=Final Answer:|$)'
                react_match = re.search(react_pattern, actual_output, re.DOTALL)
                if react_match:
                    react_content = react_match.group(1).strip()
                    reasoning_parts.append(react_content)

        # Join all reasoning parts
        reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else ""

        return reasoning

    def create_simplified_result(self, langchain_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Create simplified agent result with only reasoning and actual_output.

        This is the new standard format for all agent results, eliminating redundant
        fields like user_text, timestamp, categories, confidence, etc.

        Args:
            langchain_result: Raw LangChain execution result

        Returns:
            Simplified result dictionary with only reasoning and actual_output
        """
        # IMPORTANT: Extract reasoning BEFORE cleaning actual_output
        # extract_reasoning_process() needs the original output with <thinking> tags
        # to extract reasoning content (Method 2 in extract_reasoning_process)
        original_output = langchain_result.get('output', str(langchain_result)) if isinstance(langchain_result, dict) else str(langchain_result)
        reasoning = self.extract_reasoning_process(langchain_result, original_output)

        # Now extract and clean the actual_output (removes <thinking> tags)
        # This ensures actual_output only contains the real output, not reasoning
        actual_output = self.extract_original_output(langchain_result)

        # Return simplified structure with clean separation
        # Include 'status' field for compatibility with LangChainEngine
        return {
            "reasoning": reasoning,
            "actual_output": actual_output,
            "status": "completed"  # Mark as completed if no exception was raised
        }

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
        status_value = self.status.value if hasattr(self.status, 'value') else str(self.status)
        return f"Agent({self.agent_id}, {self.role_value}, {status_value})"

    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        # Handle both enum and string values
        status_value = self.status.value if hasattr(self.status, 'value') else str(self.status)
        return (
            f"BaseAgent(id={self.agent_id}, role={self.role_value}, "
            f"status={status_value}, tasks_executed={self.total_tasks_executed})"
        )

    # ==================== Conversation History Management ====================

    def set_context_engine(self, context_engine, session_id: str = None):
        """
        Set the ContextEngine for conversation history management.

        Args:
            context_engine: ContextEngine instance
            session_id: Current session ID
        """
        self.context_engine = context_engine
        self.current_session_id = session_id
        logger.info(f"ContextEngine set for agent {self.agent_id}")

    async def load_conversation_history(
        self,
        session_id: str = None,
        other_participant_role: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Load conversation history from ContextEngine.

        Args:
            session_id: Session ID (uses current if not provided)
            other_participant_role: Other participant role (for agent-to-agent) or None (for MC)
            limit: Maximum number of messages to load

        Returns:
            List of conversation messages
        """
        if not self.context_engine:
            logger.warning("ContextEngine not available, using local conversation history")
            return self.conversation_history[-limit:] if self.conversation_history else []

        try:
            session_id = session_id or self.current_session_id
            if not session_id:
                logger.warning("No session ID available for loading conversation history")
                return []

            # Get agent role
            agent_role = self.role_value

            # Load from ContextEngine
            if other_participant_role:
                # Agent-to-agent conversation
                session_key = f"{session_id}_{agent_role}_{other_participant_role}"
                logger.debug(f"Loading agent conversation history from ContextEngine with session_key: {session_key}")

                messages = await self.context_engine.get_agent_conversation_history(
                    session_key=session_key,
                    limit=limit
                )
            else:
                # MC-to-agent or general conversation
                logger.debug(f"Loading conversation history from ContextEngine with session_id: {session_id}")

                messages = await self.context_engine.get_conversation_history(
                    session_id=session_id,
                    limit=limit
                )

            # Convert to unified format
            history = []
            for msg in messages:
                if hasattr(msg, 'to_dict'):
                    # ConversationMessage object
                    history.append(msg.to_dict())
                elif isinstance(msg, dict):
                    # Already a dict
                    history.append(msg)
                else:
                    # Try to convert to dict
                    try:
                        history.append({
                            'role': getattr(msg, 'role', 'unknown'),
                            'content': getattr(msg, 'content', str(msg)),
                            'timestamp': getattr(msg, 'timestamp', None)
                        })
                    except Exception as conv_error:
                        logger.warning(f"Failed to convert message to dict: {conv_error}")

            logger.info(f"Loaded {len(history)} messages from ContextEngine for session {session_id}")
            return history

        except Exception as e:
            logger.error(f"Failed to load conversation history from ContextEngine: {e}")
            logger.debug(f"Falling back to local conversation history")
            # Fallback to local conversation history
            return self.conversation_history[-limit:] if self.conversation_history else []

    def add_conversation_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """
        Add a message to the conversation history.

        Args:
            role: Message role (user, assistant, system, etc.)
            content: Message content
            metadata: Additional metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        self.conversation_history.append(message)

        # Keep only recent messages to avoid memory issues
        max_history_length = 100
        if len(self.conversation_history) > max_history_length:
            self.conversation_history = self.conversation_history[-max_history_length:]

        logger.debug(f"Added conversation message: {role}")

    def format_conversation_history_for_prompt(
        self,
        history: List[Dict[str, Any]] = None,
        include_metadata: bool = False
    ) -> str:
        """
        Format conversation history for inclusion in agent prompts.

        Args:
            history: Conversation history (uses current if not provided)
            include_metadata: Whether to include metadata in formatting

        Returns:
            Formatted conversation history string
        """
        if history is None:
            history = self.conversation_history

        if not history:
            return "No previous conversation history."

        formatted_messages = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            if include_metadata and msg.get("metadata"):
                metadata_str = f" [Metadata: {msg['metadata']}]"
            else:
                metadata_str = ""

            formatted_messages.append(f"{role.upper()}: {content}{metadata_str}")

        return "\n".join(formatted_messages)

    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Get conversation context for the agent.

        Returns:
            Dictionary containing conversation context
        """
        return {
            "session_id": self.current_session_id,
            "agent_role": self.role_value,
            "conversation_length": len(self.conversation_history),
            "last_message_time": self.conversation_history[-1].get("timestamp") if self.conversation_history else None,
            "context_data": self.conversation_context
        }

    def update_conversation_context(self, context_updates: Dict[str, Any]):
        """
        Update conversation context with new information.

        Args:
            context_updates: Dictionary of context updates
        """
        self.conversation_context.update(context_updates)
        logger.debug(f"Updated conversation context: {list(context_updates.keys())}")

    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history.clear()
        self.conversation_context.clear()
        logger.info(f"Cleared conversation history for agent {self.agent_id}")


    def record_agent_response(self, response_content: str, metadata: Dict[str, Any] = None):
        """
        Record the agent's response in conversation history.

        Args:
            response_content: The agent's response content
            metadata: Additional metadata about the response
        """
        try:
            # Get agent role
            agent_role = self.role_value

            # Add agent response to conversation history
            self.add_conversation_message(
                role=f"assistant_{agent_role}",
                content=response_content,
                metadata=metadata or {}
            )

            logger.debug(f"Recorded agent response for {agent_role}")

        except Exception as e:
            logger.error(f"Failed to record agent response: {e}")

    async def _get_formatted_conversation_history(self, limit: int = 10) -> str:
        """
        Get formatted conversation history for inclusion in React prompt.

        Args:
            limit: Maximum number of recent messages to include

        Returns:
            Formatted conversation history string
        """
        try:
            # Load recent conversation history
            history = await self.load_conversation_history(limit=limit)

            # Format conversation history for prompt
            return self.format_conversation_history_for_prompt(history)

        except Exception as e:
            logger.error(f"Failed to get formatted conversation history: {e}")
            return "No previous conversation history."

    async def execute_with_unified_retry(
        self,
        agent_executor: AgentExecutor,
        agent_input: Dict[str, Any],
        operation_name: str = "agent_execution",
        fallback_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        统一的重试执行方法 - 使用截断指数退避算法

        这是所有Agent执行的统一入口，提供：
        1. 截断指数退避重试策略
        2. 错误分类和针对性处理
        3. 结构化的错误恢复
        4. 统一的日志记录

        Args:
            agent_executor: LangChain AgentExecutor实例
            agent_input: Agent输入数据
            operation_name: 操作名称（用于日志）
            fallback_response: 可选的回退响应

        Returns:
            Agent执行结果
        """
        retry_count = 0
        max_retries = self.retry_config['max_retries']

        while retry_count < max_retries:
            try:
                logger.info(f"{operation_name} attempt {retry_count + 1}/{max_retries} for agent {self.agent_id}")

                # 执行Agent
                result = await agent_executor.ainvoke(agent_input)

                # 验证结果质量
                if self._is_valid_agent_result(result):
                    logger.info(f"{operation_name} successful on attempt {retry_count + 1}")
                    return result
                else:
                    logger.warning(f"{operation_name} returned invalid result on attempt {retry_count + 1}/{max_retries}")

            except Exception as e:
                logger.error(f"{operation_name} failed on attempt {retry_count + 1}/{max_retries}: {e}")

                # 错误分类
                error_type = self._classify_execution_error(e)
                logger.info(f"Error classified as: {error_type}")

            # 如果不是最后一次重试，计算延迟
            if retry_count < max_retries - 1:
                delay = self._calculate_retry_delay(retry_count, error_type if 'error_type' in locals() else 'unknown')
                logger.info(f"Waiting {delay:.2f}s before retry {retry_count + 2}")
                await asyncio.sleep(delay)

            retry_count += 1

        # 所有重试都失败，返回回退响应
        logger.error(f"All {max_retries} attempts failed for {operation_name}")
        return self._create_fallback_result(fallback_response, operation_name)

    def _is_valid_agent_result(self, result: Dict[str, Any]) -> bool:
        """
        验证Agent执行结果是否有效

        Args:
            result: Agent执行结果

        Returns:
            是否为有效结果
        """
        if not result or not isinstance(result, dict):
            return False

        output = result.get('output', '')

        # 检查常见的失败模式
        failure_patterns = [
            'Agent stopped due to',
            'Invalid or incomplete response',
            'Invalid Format: Missing',
            'technical difficulties',
            'Error:'
        ]

        for pattern in failure_patterns:
            if pattern in str(output):
                return False

        # 检查输出是否为空或过短
        if not output or len(str(output).strip()) < 10:
            return False

        return True

    def _classify_execution_error(self, error: Exception) -> str:
        """
        分类执行错误类型

        Args:
            error: 异常对象

        Returns:
            错误类型字符串
        """
        error_str = str(error).lower()

        if "429" in error_str or "resource exhausted" in error_str or "rate limit" in error_str:
            return "rate_limiting"
        elif "timeout" in error_str or "time limit" in error_str:
            return "timeout"
        elif "invalid format" in error_str or "missing action" in error_str:
            return "format_error"
        elif "connection" in error_str or "network" in error_str:
            return "network_error"
        elif "authentication" in error_str or "unauthorized" in error_str:
            return "auth_error"
        else:
            return "unknown_error"

    def _calculate_retry_delay(self, retry_count: int, error_type: str) -> float:
        """
        计算重试延迟 - 截断指数退避算法

        Args:
            retry_count: 当前重试次数（从0开始）
            error_type: 错误类型

        Returns:
            延迟时间（秒）
        """
        # 根据错误类型选择参数
        if error_type == "rate_limiting":
            base_delay = self.retry_config['rate_limit_base_delay']
            max_delay = self.retry_config['rate_limit_max_delay']
        else:
            base_delay = self.retry_config['base_delay']
            max_delay = self.retry_config['max_delay']

        exponential_factor = self.retry_config['exponential_factor']
        jitter_factor = self.retry_config['jitter_factor']

        # 计算指数延迟: base_delay * (exponential_factor ^ retry_count)
        exponential_delay = base_delay * (exponential_factor ** retry_count)

        # 应用截断: 限制最大延迟
        truncated_delay = min(exponential_delay, max_delay)

        # 添加抖动: ±jitter_factor 的随机变化
        jitter = random.uniform(-jitter_factor, jitter_factor)
        final_delay = truncated_delay * (1 + jitter)

        # 确保延迟不为负数
        return max(0.1, final_delay)

    def _create_fallback_result(self, fallback_response: Optional[str], operation_name: str) -> Dict[str, Any]:
        """
        创建回退结果

        Args:
            fallback_response: 可选的自定义回退响应
            operation_name: 操作名称

        Returns:
            回退结果字典
        """
        if fallback_response:
            output = fallback_response
        else:
            output = (
                f"I apologize, but I'm experiencing persistent technical difficulties with {operation_name}. "
                f"This appears to be a complex request that would benefit from manual review. "
                f"Please try again later when the system is more stable, or contact support if the issue persists."
            )

        return {
            'output': output,
            'reasoning': f"Fallback response after {self.retry_config['max_retries']} failed attempts",
            'actual_output': output
        }
