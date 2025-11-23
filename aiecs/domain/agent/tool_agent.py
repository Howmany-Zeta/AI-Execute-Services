"""
Tool Agent

Agent implementation specialized in tool usage and execution.
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
from datetime import datetime

from aiecs.tools import get_tool, BaseTool

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError, ToolAccessDeniedError

if TYPE_CHECKING:
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )

logger = logging.getLogger(__name__)


class ToolAgent(BaseAIAgent):
    """
    Agent specialized in tool selection and execution.

    This agent can execute one or more tools to complete tasks.

    **Tool Configuration:**
    - Tool names (List[str]): Backward compatible, tools loaded by name
    - Tool instances (Dict[str, BaseTool]): Pre-configured tools with preserved state

    Examples:
        # Example 1: Basic usage with tool names (backward compatible)
        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            tools=["search", "calculator"],
            config=config
        )

        # Example 2: Using tool instances with preserved state
        from aiecs.tools import BaseTool

        class StatefulCalculatorTool(BaseTool):
            def __init__(self):
                self.calculation_history = []  # State preserved

            async def run_async(self, operation: str, a: float, b: float):
                if operation == "add":
                    result = a + b
                elif operation == "multiply":
                    result = a * b
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                # Store in history
                self.calculation_history.append({
                    "operation": operation,
                    "a": a,
                    "b": b,
                    "result": result
                })
                return result

        # Create tool instance
        calculator = StatefulCalculatorTool()

        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            tools={
                "calculator": calculator,  # Stateful tool instance
                "search": SearchTool(api_key="...")
            },
            config=config
        )

        # Execute task
        result = await agent.execute_task({
            "tool": "calculator",
            "operation": "add",
            "parameters": {"a": 5, "b": 3}
        }, {})

        # Tool state (calculation_history) is preserved
        print(f"History: {calculator.calculation_history}")

        # Example 3: Tool instances with dependencies
        class ContextAwareSearchTool(BaseTool):
            def __init__(self, api_key: str, context_engine):
                self.api_key = api_key
                self.context_engine = context_engine
                self.search_cache = {}  # State preserved

            async def run_async(self, operation: str, query: str):
                # Check cache first
                if query in self.search_cache:
                    return self.search_cache[query]

                # Use context_engine for context-aware search
                results = await self._perform_search(query)
                self.search_cache[query] = results
                return results

        context_engine = ContextEngine()
        await context_engine.initialize()

        search_tool = ContextAwareSearchTool(
            api_key="...",
            context_engine=context_engine
        )

        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            tools={
                "search": search_tool,  # Tool with dependencies
                "calculator": CalculatorTool()
            },
            config=config
        )

        # Example 4: Full-featured agent with all options
        from aiecs.domain.context import ContextEngine
        from aiecs.domain.agent.models import ResourceLimits

        context_engine = ContextEngine()
        await context_engine.initialize()

        resource_limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tool_calls_per_minute=100
        )

        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            tools={
                "search": ContextAwareSearchTool(api_key="...", context_engine=context_engine),
                "calculator": StatefulCalculatorTool()
            },
            config=config,
            config_manager=DatabaseConfigManager(),
            checkpointer=RedisCheckpointer(),
            context_engine=context_engine,
            collaboration_enabled=True,
            agent_registry={"agent2": other_agent},
            learning_enabled=True,
            resource_limits=resource_limits
        )
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional["CheckpointerProtocol"] = None,
        context_engine: Optional[Any] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
    ):
        """
        Initialize Tool agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            tools: Tools - either list of tool names or dict of tool instances
            config: Agent configuration
            description: Optional description
            version: Agent version
            config_manager: Optional configuration manager for dynamic config
            checkpointer: Optional checkpointer for state persistence
            context_engine: Optional context engine for persistent storage
            collaboration_enabled: Enable collaboration features
            agent_registry: Registry of other agents for collaboration
            learning_enabled: Enable learning features
            resource_limits: Optional resource limits configuration

        Example with tool instances:
            ```python
            agent = ToolAgent(
                agent_id="agent1",
                name="My Tool Agent",
                tools={
                    "search": SearchTool(api_key="..."),
                    "calculator": CalculatorTool()
                },
                config=config
            )
            ```

        Example with tool names (backward compatible):
            ```python
            agent = ToolAgent(
                agent_id="agent1",
                name="My Tool Agent",
                tools=["search", "calculator"],
                config=config
            )
            ```
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
            description=description or "Tool-based task execution agent",
            version=version,
            tools=tools,
            config_manager=config_manager,
            checkpointer=checkpointer,
            context_engine=context_engine,
            collaboration_enabled=collaboration_enabled,
            agent_registry=agent_registry,
            learning_enabled=learning_enabled,
            resource_limits=resource_limits,
        )

        self._tool_instances: Dict[str, BaseTool] = {}
        self._tool_usage_stats: Dict[str, Dict[str, int]] = {}

        tool_count = len(tools) if isinstance(tools, (list, dict)) else 0
        logger.info(f"ToolAgent initialized: {agent_id} with {tool_count} tools")

    async def _initialize(self) -> None:
        """Initialize Tool agent - load tools using BaseAIAgent helper."""
        # Load tools using BaseAIAgent helper
        self._load_tools()

        # Get tool instances from BaseAIAgent (if provided as instances)
        base_tool_instances = self._get_tool_instances()

        if base_tool_instances:
            # Tool instances were provided - use them directly
            self._tool_instances = base_tool_instances
            logger.info(f"ToolAgent {self.agent_id} using " f"{len(self._tool_instances)} pre-configured tool instances")
        elif self._available_tools:
            # Tool names were provided - load them
            for tool_name in self._available_tools:
                try:
                    self._tool_instances[tool_name] = get_tool(tool_name)
                    logger.debug(f"ToolAgent {self.agent_id} loaded tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to load tool {tool_name}: {e}")

            logger.info(f"ToolAgent {self.agent_id} initialized with {len(self._tool_instances)} tools")

        # Initialize usage stats for all tools
        for tool_name in self._tool_instances.keys():
            self._tool_usage_stats[tool_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
            }

    async def _shutdown(self) -> None:
        """Shutdown Tool agent."""
        self._tool_instances.clear()
        logger.info(f"ToolAgent {self.agent_id} shut down")

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using tools.

        Args:
            task: Task specification with 'tool', 'operation', and 'parameters'
            context: Execution context

        Returns:
            Execution result with 'output', 'tool_used', 'execution_time'

        Raises:
            TaskExecutionError: If task execution fails
        """
        start_time = datetime.utcnow()

        try:
            # Extract tool and operation
            tool_name = task.get("tool")
            operation = task.get("operation")
            parameters = task.get("parameters", {})

            if not tool_name:
                raise TaskExecutionError("Task must contain 'tool' field", agent_id=self.agent_id)

            # Check tool access
            if not self._available_tools or tool_name not in self._available_tools:
                raise ToolAccessDeniedError(self.agent_id, tool_name)

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Execute tool
            result = await self._execute_tool(tool_name, operation, parameters)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(
                execution_time=execution_time,
                success=True,
                tool_calls=1,
            )

            # Update tool usage stats
            self._update_tool_stats(tool_name, success=True)

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return {
                "success": True,
                "output": result,
                "tool_used": tool_name,
                "operation": operation,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Task execution failed for {self.agent_id}: {e}")

            # Update metrics for failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            # Update tool stats if tool was specified
            if tool_name:
                self._update_tool_stats(tool_name, success=False)

            # Transition to error state
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                agent_id=self.agent_id,
                task_id=task.get("task_id"),
            )

    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an incoming message.

        For ToolAgent, this is limited - it's designed for direct tool execution.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary
        """
        available_tools_str = ", ".join(self._available_tools) if self._available_tools else "none"
        return {
            "response": (f"ToolAgent {self.name} received message but requires explicit tool tasks. " f"Available tools: {available_tools_str}"),
            "available_tools": self._available_tools or [],
        }

    async def _execute_tool(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool operation.

        Args:
            tool_name: Tool name
            operation: Operation name (optional for tools with single operation)
            parameters: Operation parameters

        Returns:
            Tool execution result
        """
        tool = self._tool_instances.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not loaded")

        # Execute tool
        if operation:
            result = await tool.run_async(operation, **parameters)
        else:
            # If no operation specified, try to call the tool directly
            if hasattr(tool, "run_async"):
                result = await tool.run_async(**parameters)
            else:
                raise ValueError(f"Tool {tool_name} requires operation to be specified")

        return result

    def _update_tool_stats(self, tool_name: str, success: bool) -> None:
        """Update tool usage statistics."""
        if tool_name not in self._tool_usage_stats:
            self._tool_usage_stats[tool_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
            }

        stats = self._tool_usage_stats[tool_name]
        stats["total_count"] += 1
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

    def get_tool_stats(self) -> Dict[str, Dict[str, int]]:
        """Get tool usage statistics."""
        return self._tool_usage_stats.copy()

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self._available_tools.copy() if self._available_tools else []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolAgent":
        """
        Deserialize ToolAgent from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ToolAgent instance
        """
        raise NotImplementedError("ToolAgent.from_dict not fully implemented yet")
