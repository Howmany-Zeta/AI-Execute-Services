"""
Tool Agent

Agent implementation specialized in tool usage and execution.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from aiecs.tools import get_tool, BaseTool

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError, ToolAccessDeniedError

logger = logging.getLogger(__name__)


class ToolAgent(BaseAIAgent):
    """
    Agent specialized in tool selection and execution.

    This agent can execute one or more tools to complete tasks.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        tools: List[str],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
    ):
        """
        Initialize Tool agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            tools: List of tool names agent can use
            config: Agent configuration
            description: Optional description
            version: Agent version
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
            description=description or "Tool-based task execution agent",
            version=version,
        )
        
        self._available_tools = tools
        self._tool_instances: Dict[str, BaseTool] = {}
        self._tool_usage_stats: Dict[str, Dict[str, int]] = {}

        logger.info(f"ToolAgent initialized: {agent_id} with tools: {', '.join(tools)}")

    async def _initialize(self) -> None:
        """Initialize Tool agent - load tools."""
        # Load tool instances
        for tool_name in self._available_tools:
            try:
                self._tool_instances[tool_name] = get_tool(tool_name)
                self._tool_usage_stats[tool_name] = {
                    "success_count": 0,
                    "failure_count": 0,
                    "total_count": 0,
                }
                logger.debug(f"ToolAgent {self.agent_id} loaded tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to load tool {tool_name}: {e}")

        logger.info(f"ToolAgent {self.agent_id} initialized with {len(self._tool_instances)} tools")

    async def _shutdown(self) -> None:
        """Shutdown Tool agent."""
        self._tool_instances.clear()
        logger.info(f"ToolAgent {self.agent_id} shut down")

    async def execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
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
            tool_name = task.get('tool')
            operation = task.get('operation')
            parameters = task.get('parameters', {})

            if not tool_name:
                raise TaskExecutionError(
                    "Task must contain 'tool' field",
                    agent_id=self.agent_id
                )

            # Check tool access
            if tool_name not in self._available_tools:
                raise ToolAccessDeniedError(self.agent_id, tool_name)

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get('task_id')

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
                task_id=task.get('task_id')
            )

    async def process_message(
        self,
        message: str,
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message.

        For ToolAgent, this is limited - it's designed for direct tool execution.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary
        """
        return {
            "response": f"ToolAgent {self.name} received message but requires explicit tool tasks. "
                       f"Available tools: {', '.join(self._available_tools)}",
            "available_tools": self._available_tools,
        }

    async def _execute_tool(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any]
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
            if hasattr(tool, 'run_async'):
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
        return self._available_tools.copy()

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

