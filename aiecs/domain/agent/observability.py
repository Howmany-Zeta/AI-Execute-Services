"""
Agent Observability

Observer pattern and controllers for monitoring agent behavior.
"""

import logging
from typing import Dict, Any, List, Protocol
from datetime import datetime

from .base_agent import BaseAIAgent
from .models import AgentState

logger = logging.getLogger(__name__)


class AgentObserver(Protocol):
    """Protocol for observing agent events."""

    def on_state_changed(
        self,
        agent_id: str,
        old_state: AgentState,
        new_state: AgentState,
        timestamp: datetime,
    ) -> None:
        """
        Called when agent state changes.

        Args:
            agent_id: Agent identifier
            old_state: Previous state
            new_state: New state
            timestamp: Change timestamp
        """
        ...

    def on_task_started(
        self,
        agent_id: str,
        task_id: str,
        task: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """
        Called when agent starts a task.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            task: Task specification
            timestamp: Start timestamp
        """
        ...

    def on_task_completed(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """
        Called when agent completes a task.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            result: Task result
            timestamp: Completion timestamp
        """
        ...

    def on_task_failed(
        self,
        agent_id: str,
        task_id: str,
        error: Exception,
        timestamp: datetime,
    ) -> None:
        """
        Called when agent task fails.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            error: Error that occurred
            timestamp: Failure timestamp
        """
        ...

    def on_health_status_changed(
        self,
        agent_id: str,
        health_status: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """
        Called when agent health status changes significantly.

        Args:
            agent_id: Agent identifier
            health_status: Health status dictionary with score and issues
            timestamp: Status change timestamp
        """
        ...

    def on_tool_called(
        self,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """
        Called when agent calls a tool.

        Args:
            agent_id: Agent identifier
            tool_name: Tool name
            parameters: Tool parameters
            timestamp: Call timestamp
        """
        ...


class LoggingObserver:
    """Observer that logs agent events."""

    def __init__(self, log_level: int = logging.INFO):
        """
        Initialize logging observer.

        Args:
            log_level: Logging level
        """
        self.logger = logging.getLogger(f"{__name__}.LoggingObserver")
        self.log_level = log_level

    def on_state_changed(
        self,
        agent_id: str,
        old_state: AgentState,
        new_state: AgentState,
        timestamp: datetime,
    ) -> None:
        """Log state change."""
        self.logger.log(
            self.log_level,
            f"Agent {agent_id}: {old_state.value} → {new_state.value}",
        )

    def on_task_started(
        self,
        agent_id: str,
        task_id: str,
        task: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Log task start."""
        self.logger.log(self.log_level, f"Agent {agent_id}: Task {task_id} started")

    def on_task_completed(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Log task completion."""
        self.logger.log(self.log_level, f"Agent {agent_id}: Task {task_id} completed")

    def on_task_failed(
        self,
        agent_id: str,
        task_id: str,
        error: Exception,
        timestamp: datetime,
    ) -> None:
        """Log task failure."""
        self.logger.log(
            self.log_level,
            f"Agent {agent_id}: Task {task_id} failed - {str(error)}",
        )

    def on_tool_called(
        self,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Log tool call."""
        self.logger.log(self.log_level, f"Agent {agent_id}: Tool '{tool_name}' called")

    def on_health_status_changed(
        self,
        agent_id: str,
        health_status: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Log health status change."""
        status = health_status.get("status", "unknown")
        score = health_status.get("health_score", 0)
        issues = health_status.get("issues", [])

        log_level = self.log_level
        if status == "unhealthy":
            log_level = logging.WARNING
        elif status == "degraded":
            log_level = logging.INFO

        message = f"Agent {agent_id}: Health status {status} (score: {score:.1f}/100)"
        if issues:
            message += f" - Issues: {', '.join(issues)}"

        self.logger.log(log_level, message)


class MetricsObserver:
    """Observer that collects metrics."""

    def __init__(self) -> None:
        """Initialize metrics observer."""
        self.state_changes: List[Dict[str, Any]] = []
        self.task_events: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.health_status_changes: List[Dict[str, Any]] = []

    def on_state_changed(
        self,
        agent_id: str,
        old_state: AgentState,
        new_state: AgentState,
        timestamp: datetime,
    ) -> None:
        """Record state change."""
        self.state_changes.append(
            {
                "agent_id": agent_id,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "timestamp": timestamp.isoformat(),
            }
        )

    def on_task_started(
        self,
        agent_id: str,
        task_id: str,
        task: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Record task start."""
        self.task_events.append(
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "event": "started",
                "timestamp": timestamp.isoformat(),
            }
        )

    def on_task_completed(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Record task completion."""
        self.task_events.append(
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "event": "completed",
                "timestamp": timestamp.isoformat(),
            }
        )

    def on_task_failed(
        self,
        agent_id: str,
        task_id: str,
        error: Exception,
        timestamp: datetime,
    ) -> None:
        """Record task failure."""
        self.task_events.append(
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "event": "failed",
                "error": str(error),
                "timestamp": timestamp.isoformat(),
            }
        )

    def on_tool_called(
        self,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Record tool call."""
        self.tool_calls.append(
            {
                "agent_id": agent_id,
                "tool_name": tool_name,
                "timestamp": timestamp.isoformat(),
            }
        )

    def on_health_status_changed(
        self,
        agent_id: str,
        health_status: Dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """Record health status change."""
        self.health_status_changes.append(
            {
                "agent_id": agent_id,
                "status": health_status.get("status"),
                "health_score": health_status.get("health_score"),
                "issues": health_status.get("issues", []),
                "timestamp": timestamp.isoformat(),
            }
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            "state_changes": len(self.state_changes),
            "task_events": len(self.task_events),
            "tool_calls": len(self.tool_calls),
            "health_status_changes": len(self.health_status_changes),
            "state_changes_data": self.state_changes,
            "task_events_data": self.task_events,
            "tool_calls_data": self.tool_calls,
            "health_status_changes_data": self.health_status_changes,
        }

    def clear(self) -> None:
        """Clear all metrics."""
        self.state_changes.clear()
        self.task_events.clear()
        self.tool_calls.clear()
        self.health_status_changes.clear()


class AgentController:
    """
    Controller for managing agent execution and monitoring.

    Integrates with observers for event tracking.
    """

    def __init__(self, agent: BaseAIAgent):
        """
        Initialize agent controller.

        Args:
            agent: Agent to control
        """
        self.agent = agent
        self.observers: List[AgentObserver] = []
        logger.info(f"AgentController initialized for agent {agent.agent_id}")

    def add_observer(self, observer: AgentObserver) -> None:
        """
        Add an observer.

        Args:
            observer: Observer to add
        """
        self.observers.append(observer)
        logger.debug(f"Observer added to agent {self.agent.agent_id}")

    def remove_observer(self, observer: AgentObserver) -> None:
        """
        Remove an observer.

        Args:
            observer: Observer to remove
        """
        if observer in self.observers:
            self.observers.remove(observer)
            logger.debug(f"Observer removed from agent {self.agent.agent_id}")

    def notify_state_changed(self, old_state: AgentState, new_state: AgentState) -> None:
        """Notify observers of state change."""
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_state_changed(self.agent.agent_id, old_state, new_state, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_task_started(self, task_id: str, task: Dict[str, Any]) -> None:
        """Notify observers of task start."""
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_task_started(self.agent.agent_id, task_id, task, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_task_completed(self, task_id: str, result: Dict[str, Any]) -> None:
        """Notify observers of task completion."""
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_task_completed(self.agent.agent_id, task_id, result, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_task_failed(self, task_id: str, error: Exception) -> None:
        """Notify observers of task failure."""
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_task_failed(self.agent.agent_id, task_id, error, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_tool_called(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """Notify observers of tool call."""
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_tool_called(self.agent.agent_id, tool_name, parameters, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    def notify_health_status_changed(self, health_status: Dict[str, Any]) -> None:
        """
        Notify observers of health status change.

        Args:
            health_status: Health status dictionary with score and issues
        """
        timestamp = datetime.utcnow()
        for observer in self.observers:
            try:
                observer.on_health_status_changed(self.agent.agent_id, health_status, timestamp)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    async def execute_task_with_observation(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task with observer notifications.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Task result
        """
        task_id = task.get("task_id", f"task_{datetime.utcnow().timestamp()}")

        # Notify start
        self.notify_task_started(task_id, task)

        try:
            # Execute task
            result = await self.agent.execute_task(task, context)

            # Notify completion
            self.notify_task_completed(task_id, result)

            return result

        except Exception as e:
            # Notify failure
            self.notify_task_failed(task_id, e)
            raise
