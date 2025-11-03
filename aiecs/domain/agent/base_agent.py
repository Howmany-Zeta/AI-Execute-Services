"""
Base AI Agent

Abstract base class for all AI agents in the AIECS system.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
import logging

from .models import (
    AgentState,
    AgentType,
    AgentConfiguration,
    AgentGoal,
    AgentMetrics,
    AgentCapabilityDeclaration,
    AgentMemory,
    GoalStatus,
    GoalPriority,
    MemoryType,
)
from .exceptions import (
    InvalidStateTransitionError,
    ConfigurationError,
    AgentInitializationError,
    SerializationError,
)

logger = logging.getLogger(__name__)


class BaseAIAgent(ABC):
    """
    Abstract base class for AI agents.

    Provides common functionality for agent lifecycle management,
    state management, memory, goals, and metrics tracking.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        agent_type: AgentType,
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
    ):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for the agent
            name: Agent name
            agent_type: Type of agent
            config: Agent configuration
            description: Optional agent description
            version: Agent version
        """
        # Identity
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.description = description or f"{agent_type.value} agent"
        self.version = version

        # Configuration
        self._config = config

        # State
        self._state = AgentState.CREATED
        self._previous_state: Optional[AgentState] = None

        # Memory storage (in-memory dict, can be replaced with sophisticated storage)
        self._memory: Dict[str, Any] = {}
        self._memory_metadata: Dict[str, Dict[str, Any]] = {}

        # Goals
        self._goals: Dict[str, AgentGoal] = {}

        # Capabilities
        self._capabilities: Dict[str, AgentCapabilityDeclaration] = {}

        # Metrics
        self._metrics = AgentMetrics()

        # Timestamps
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_active_at: Optional[datetime] = None

        # Current task tracking
        self._current_task_id: Optional[str] = None

        logger.info(f"Agent initialized: {self.agent_id} ({self.name}, {self.agent_type.value})")

    # ==================== State Management ====================

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    def _transition_state(self, new_state: AgentState) -> None:
        """
        Transition to a new state with validation.

        Args:
            new_state: Target state

        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        # Define valid transitions
        valid_transitions = {
            AgentState.CREATED: {AgentState.INITIALIZING},
            AgentState.INITIALIZING: {AgentState.ACTIVE, AgentState.ERROR},
            AgentState.ACTIVE: {AgentState.BUSY, AgentState.IDLE, AgentState.STOPPED, AgentState.ERROR},
            AgentState.BUSY: {AgentState.ACTIVE, AgentState.ERROR},
            AgentState.IDLE: {AgentState.ACTIVE, AgentState.STOPPED},
            AgentState.ERROR: {AgentState.ACTIVE, AgentState.STOPPED},
            AgentState.STOPPED: set(),  # Terminal state
        }

        if new_state not in valid_transitions.get(self._state, set()):
            raise InvalidStateTransitionError(
                agent_id=self.agent_id,
                current_state=self._state.value,
                attempted_state=new_state.value,
            )

        self._previous_state = self._state
        self._state = new_state
        self.updated_at = datetime.utcnow()

        logger.info(f"Agent {self.agent_id} state: {self._previous_state.value} → {new_state.value}")

    # ==================== Lifecycle Methods ====================

    async def initialize(self) -> None:
        """
        Initialize the agent.

        This method should be called before the agent can be used.
        Override in subclasses to add initialization logic.

        Raises:
            AgentInitializationError: If initialization fails
        """
        try:
            self._transition_state(AgentState.INITIALIZING)
            logger.info(f"Initializing agent {self.agent_id}...")

            # Subclass initialization
            await self._initialize()

            self._transition_state(AgentState.ACTIVE)
            self.last_active_at = datetime.utcnow()
            logger.info(f"Agent {self.agent_id} initialized successfully")

        except Exception as e:
            self._transition_state(AgentState.ERROR)
            logger.error(f"Agent {self.agent_id} initialization failed: {e}")
            raise AgentInitializationError(
                f"Failed to initialize agent {self.agent_id}: {str(e)}",
                agent_id=self.agent_id,
            )

    @abstractmethod
    async def _initialize(self) -> None:
        """
        Subclass-specific initialization logic.

        Override this method in subclasses to implement
        custom initialization.
        """
        pass

    async def activate(self) -> None:
        """Activate the agent."""
        if self._state == AgentState.IDLE:
            self._transition_state(AgentState.ACTIVE)
            self.last_active_at = datetime.utcnow()
            logger.info(f"Agent {self.agent_id} activated")
        else:
            logger.warning(
                f"Agent {self.agent_id} cannot be activated from state {self._state.value}"
            )

    async def deactivate(self) -> None:
        """Deactivate the agent (enter idle state)."""
        if self._state == AgentState.ACTIVE:
            self._transition_state(AgentState.IDLE)
            logger.info(f"Agent {self.agent_id} deactivated")
        else:
            logger.warning(
                f"Agent {self.agent_id} cannot be deactivated from state {self._state.value}"
            )

    async def shutdown(self) -> None:
        """
        Shutdown the agent.

        Override in subclasses to add cleanup logic.
        """
        logger.info(f"Shutting down agent {self.agent_id}...")
        await self._shutdown()
        self._transition_state(AgentState.STOPPED)
        logger.info(f"Agent {self.agent_id} shut down")

    @abstractmethod
    async def _shutdown(self) -> None:
        """
        Subclass-specific shutdown logic.

        Override this method in subclasses to implement
        custom cleanup.
        """
        pass

    # ==================== Abstract Execution Methods ====================

    @abstractmethod
    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Task execution result

        Raises:
            TaskExecutionError: If task execution fails

        Note:
            Subclasses can use `_execute_with_retry()` to wrap task execution
            with automatic retry logic based on agent configuration.
        """
        pass

    @abstractmethod
    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an incoming message.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary

        Note:
            Subclasses can use `_execute_with_retry()` to wrap message processing
            with automatic retry logic based on agent configuration.
        """
        pass

    # ==================== Retry Logic Integration ====================

    async def _execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic using agent's retry policy.

        This helper method wraps function execution with automatic retry based on
        the agent's configuration. It uses EnhancedRetryPolicy for sophisticated
        error handling with exponential backoff and error classification.

        Args:
            func: Async function to execute
            *args: Function positional arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries are exhausted

        Example:
            ```python
            async def _execute_task_internal(self, task, context):
                # Actual task execution logic
                return result

            async def execute_task(self, task, context):
                return await self._execute_with_retry(
                    self._execute_task_internal,
                    task,
                    context
                )
            ```
        """
        from .integration.retry_policy import EnhancedRetryPolicy

        # Get retry policy from configuration
        retry_config = self._config.retry_policy
        
        # Create retry policy instance
        retry_policy = EnhancedRetryPolicy(
            max_retries=retry_config.max_retries,
            base_delay=retry_config.base_delay,
            max_delay=retry_config.max_delay,
            exponential_base=retry_config.exponential_factor,
            jitter=retry_config.jitter_factor > 0
        )

        # Execute with retry
        return await retry_policy.execute_with_retry(func, *args, **kwargs)

    # ==================== Memory Management ====================

    async def add_to_memory(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add an item to agent memory.

        Args:
            key: Memory key
            value: Memory value
            memory_type: Type of memory (short_term or long_term)
            metadata: Optional metadata
        """
        self._memory[key] = value
        self._memory_metadata[key] = {
            "type": memory_type.value,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
        }
        logger.debug(f"Agent {self.agent_id} added memory: {key} ({memory_type.value})")

    async def retrieve_memory(
        self, key: str, default: Any = None
    ) -> Any:
        """
        Retrieve an item from memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Memory value or default
        """
        return self._memory.get(key, default)

    async def clear_memory(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear agent memory.

        Args:
            memory_type: If specified, clear only this type of memory
        """
        if memory_type is None:
            self._memory.clear()
            self._memory_metadata.clear()
            logger.info(f"Agent {self.agent_id} cleared all memory")
        else:
            keys_to_remove = [
                k
                for k, v in self._memory_metadata.items()
                if v.get("type") == memory_type.value
            ]
            for key in keys_to_remove:
                del self._memory[key]
                del self._memory_metadata[key]
            logger.info(f"Agent {self.agent_id} cleared {memory_type.value} memory")

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of agent memory."""
        return {
            "total_items": len(self._memory),
            "short_term_count": sum(
                1 for v in self._memory_metadata.values() if v.get("type") == MemoryType.SHORT_TERM.value
            ),
            "long_term_count": sum(
                1 for v in self._memory_metadata.values() if v.get("type") == MemoryType.LONG_TERM.value
            ),
        }

    # ==================== Goal Management ====================

    def set_goal(
        self,
        description: str,
        priority: GoalPriority = GoalPriority.MEDIUM,
        success_criteria: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ) -> str:
        """
        Set a new goal for the agent.

        Args:
            description: Goal description
            priority: Goal priority
            success_criteria: Success criteria
            deadline: Goal deadline

        Returns:
            Goal ID
        """
        goal = AgentGoal(
            description=description,
            priority=priority,
            success_criteria=success_criteria,
            deadline=deadline,
        )
        self._goals[goal.goal_id] = goal
        logger.info(f"Agent {self.agent_id} set goal: {goal.goal_id} ({priority.value})")
        return goal.goal_id

    def get_goals(
        self, status: Optional[GoalStatus] = None
    ) -> List[AgentGoal]:
        """
        Get agent goals.

        Args:
            status: Filter by status (optional)

        Returns:
            List of goals
        """
        if status is None:
            return list(self._goals.values())
        return [g for g in self._goals.values() if g.status == status]

    def get_goal(self, goal_id: str) -> Optional[AgentGoal]:
        """Get a specific goal by ID."""
        return self._goals.get(goal_id)

    def update_goal_status(
        self,
        goal_id: str,
        status: GoalStatus,
        progress: Optional[float] = None,
    ) -> None:
        """
        Update goal status.

        Args:
            goal_id: Goal ID
            status: New status
            progress: Optional progress percentage
        """
        if goal_id not in self._goals:
            logger.warning(f"Goal {goal_id} not found for agent {self.agent_id}")
            return

        goal = self._goals[goal_id]
        goal.status = status

        if progress is not None:
            goal.progress = progress

        if status == GoalStatus.IN_PROGRESS and goal.started_at is None:
            goal.started_at = datetime.utcnow()
        elif status == GoalStatus.ACHIEVED:
            goal.achieved_at = datetime.utcnow()

        logger.info(f"Agent {self.agent_id} updated goal {goal_id}: {status.value}")

    # ==================== Configuration Management ====================

    def get_config(self) -> AgentConfiguration:
        """Get agent configuration."""
        return self._config

    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update agent configuration.

        Args:
            updates: Configuration updates

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            # Update configuration
            for key, value in updates.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                else:
                    logger.warning(f"Unknown config key: {key}")

            self.updated_at = datetime.utcnow()
            logger.info(f"Agent {self.agent_id} configuration updated")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to update configuration: {str(e)}",
                agent_id=self.agent_id,
            )

    # ==================== Capability Management ====================

    def declare_capability(
        self,
        capability_type: str,
        level: str,
        description: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Declare an agent capability.

        Args:
            capability_type: Type of capability
            level: Proficiency level
            description: Capability description
            constraints: Capability constraints
        """
        from .models import CapabilityLevel

        capability = AgentCapabilityDeclaration(
            capability_type=capability_type,
            level=CapabilityLevel(level),
            description=description,
            constraints=constraints or {},
        )
        self._capabilities[capability_type] = capability
        logger.info(f"Agent {self.agent_id} declared capability: {capability_type} ({level})")

    def has_capability(self, capability_type: str) -> bool:
        """Check if agent has a capability."""
        return capability_type in self._capabilities

    def get_capabilities(self) -> List[AgentCapabilityDeclaration]:
        """Get all agent capabilities."""
        return list(self._capabilities.values())

    # ==================== Metrics Tracking ====================

    def get_metrics(self) -> AgentMetrics:
        """Get agent metrics."""
        return self._metrics

    def update_metrics(
        self,
        execution_time: Optional[float] = None,
        success: bool = True,
        quality_score: Optional[float] = None,
        tokens_used: Optional[int] = None,
        tool_calls: Optional[int] = None,
    ) -> None:
        """
        Update agent metrics.

        Args:
            execution_time: Task execution time
            success: Whether task succeeded
            quality_score: Quality score (0-1)
            tokens_used: Tokens used
            tool_calls: Number of tool calls
        """
        self._metrics.total_tasks_executed += 1

        if success:
            self._metrics.successful_tasks += 1
        else:
            self._metrics.failed_tasks += 1

        # Update success rate
        self._metrics.success_rate = (
            self._metrics.successful_tasks / self._metrics.total_tasks_executed * 100
        )

        # Update execution time
        if execution_time is not None:
            self._metrics.total_execution_time += execution_time
            self._metrics.average_execution_time = (
                self._metrics.total_execution_time / self._metrics.total_tasks_executed
            )

            if self._metrics.min_execution_time is None or execution_time < self._metrics.min_execution_time:
                self._metrics.min_execution_time = execution_time
            if self._metrics.max_execution_time is None or execution_time > self._metrics.max_execution_time:
                self._metrics.max_execution_time = execution_time

        # Update quality score
        if quality_score is not None:
            if self._metrics.average_quality_score is None:
                self._metrics.average_quality_score = quality_score
            else:
                # Running average
                total_quality = self._metrics.average_quality_score * (
                    self._metrics.total_tasks_executed - 1
                )
                self._metrics.average_quality_score = (total_quality + quality_score) / self._metrics.total_tasks_executed

        # Update resource usage
        if tokens_used is not None:
            self._metrics.total_tokens_used += tokens_used
        if tool_calls is not None:
            self._metrics.total_tool_calls += tool_calls

        self._metrics.updated_at = datetime.utcnow()

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize agent to dictionary.

        Returns:
            Dictionary representation

        Raises:
            SerializationError: If serialization fails
        """
        try:
            return {
                "agent_id": self.agent_id,
                "name": self.name,
                "agent_type": self.agent_type.value,
                "description": self.description,
                "version": self.version,
                "state": self._state.value,
                "config": self._config.model_dump(),
                "goals": [g.model_dump() for g in self._goals.values()],
                "capabilities": [c.model_dump() for c in self._capabilities.values()],
                "metrics": self._metrics.model_dump(),
                "memory_summary": self.get_memory_summary(),
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            }
        except Exception as e:
            raise SerializationError(
                f"Failed to serialize agent: {str(e)}",
                agent_id=self.agent_id,
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseAIAgent":
        """
        Deserialize agent from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Agent instance

        Raises:
            SerializationError: If deserialization fails
        """
        raise NotImplementedError("from_dict must be implemented by subclasses")

    # ==================== Utility Methods ====================

    def is_available(self) -> bool:
        """Check if agent is available for tasks."""
        return self._state == AgentState.ACTIVE

    def is_busy(self) -> bool:
        """Check if agent is currently busy."""
        return self._state == AgentState.BUSY

    def __str__(self) -> str:
        """String representation."""
        return f"Agent({self.agent_id}, {self.name}, {self.agent_type.value}, {self._state.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"BaseAIAgent(agent_id='{self.agent_id}', name='{self.name}', "
            f"type='{self.agent_type.value}', state='{self._state.value}')"
        )

