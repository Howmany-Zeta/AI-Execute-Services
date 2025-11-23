"""
Base AI Agent

Abstract base class for all AI agents in the AIECS system.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union, TYPE_CHECKING, AsyncIterator, Set
from dataclasses import dataclass
import logging
import time
import asyncio
import json

from .models import (
    AgentState,
    AgentType,
    AgentConfiguration,
    AgentGoal,
    AgentMetrics,
    AgentCapabilityDeclaration,
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

# Import protocols for type hints
if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )
    from aiecs.tools.base_tool import BaseTool
    from aiecs.domain.context.context_engine import ContextEngine

logger = logging.getLogger(__name__)


class OperationTimer:
    """
    Context manager for timing operations and tracking metrics.

    Automatically records operation duration and can be used to track
    operation-level performance metrics.

    Example:
        with agent.track_operation_time("llm_call") as timer:
            result = llm.generate(prompt)
        # timer.duration contains the elapsed time in seconds
    """

    def __init__(self, operation_name: str, agent: Optional["BaseAIAgent"] = None):
        """
        Initialize operation timer.

        Args:
            operation_name: Name of the operation being timed
            agent: Optional agent instance for automatic metrics recording
        """
        self.operation_name = operation_name
        self.agent = agent
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.error: Optional[Exception] = None

    def __enter__(self) -> "OperationTimer":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Stop timing and record metrics.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Returns:
            False to propagate exceptions
        """
        self.end_time = time.time()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time

        # Track error if one occurred
        if exc_val is not None:
            self.error = exc_val

        # Record metrics if agent is provided
        if self.agent and self.duration is not None:
            self.agent._record_operation_metrics(
                operation_name=self.operation_name,
                duration=self.duration,
                success=exc_val is None,
            )

        # Don't suppress exceptions
        return None

    def get_duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds."""
        return self.duration * 1000 if self.duration is not None else None


@dataclass
class CacheConfig:
    """
    Configuration for tool result caching.

    Provides control over caching behavior to improve performance and reduce costs
    by avoiding redundant tool executions. Supports TTL-based expiration, size limits,
    and automatic cleanup.

    **Key Features:**
    - TTL-based cache expiration (default and per-tool)
    - Size limits to prevent memory exhaustion
    - Automatic cleanup when capacity threshold reached
    - Configurable cache key generation
    - Input hashing for large parameters

    Attributes:
        enabled: Enable/disable caching globally
        default_ttl: Default time-to-live in seconds for cached entries (default: 300 = 5 minutes)
        tool_specific_ttl: Dictionary mapping tool names to custom TTL values (overrides default_ttl)
        max_cache_size: Maximum number of cached entries before cleanup (default: 1000)
        max_memory_mb: Maximum cache memory usage in MB (approximate, default: 100)
        cleanup_interval: Interval in seconds between cleanup checks (default: 60)
        cleanup_threshold: Capacity threshold (0.0-1.0) to trigger cleanup (default: 0.9 = 90%)
        include_timestamp_in_key: Whether to include timestamp in cache key (default: False)
        hash_large_inputs: Whether to hash inputs larger than 1KB for cache keys (default: True)

    Examples:
        # Example 1: Basic caching configuration
        config = CacheConfig(
            enabled=True,
            default_ttl=300,  # 5 minutes
            max_cache_size=1000
        )

        # Example 2: Per-tool TTL overrides
        config = CacheConfig(
            enabled=True,
            default_ttl=300,
            tool_specific_ttl={
                "search": 600,  # Search results cached for 10 minutes
                "calculator": 3600,  # Calculator results cached for 1 hour
                "weather": 1800  # Weather data cached for 30 minutes
            }
        )

        # Example 3: Aggressive caching for expensive operations
        config = CacheConfig(
            enabled=True,
            default_ttl=3600,  # 1 hour default
            max_cache_size=5000,
            max_memory_mb=500,
            cleanup_threshold=0.95  # Cleanup at 95% capacity
        )

        # Example 4: Disable caching for time-sensitive tools
        config = CacheConfig(
            enabled=False  # Disable caching entirely
        )

        # Example 5: Cache with timestamp-aware keys
        config = CacheConfig(
            enabled=True,
            default_ttl=300,
            include_timestamp_in_key=True  # Include timestamp for time-sensitive caching
        )
    """

    # Cache enablement
    enabled: bool = True  # Enable/disable caching

    # TTL settings
    default_ttl: int = 300  # Default TTL in seconds (5 minutes)
    tool_specific_ttl: Optional[Dict[str, int]] = None  # Per-tool TTL overrides

    # Size limits
    max_cache_size: int = 1000  # Maximum number of cached entries
    max_memory_mb: int = 100  # Maximum cache memory in MB (approximate)

    # Cleanup settings
    cleanup_interval: int = 60  # Cleanup interval in seconds
    cleanup_threshold: float = 0.9  # Trigger cleanup at 90% capacity

    # Cache key settings
    include_timestamp_in_key: bool = False  # Include timestamp in cache key
    hash_large_inputs: bool = True  # Hash inputs larger than 1KB

    def __post_init__(self):
        """Initialize defaults."""
        if self.tool_specific_ttl is None:
            self.tool_specific_ttl = {}

    def get_ttl(self, tool_name: str) -> int:
        """
        Get TTL for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            TTL in seconds
        """
        if self.tool_specific_ttl is None:
            return self.default_ttl
        return self.tool_specific_ttl.get(tool_name, self.default_ttl)


class BaseAIAgent(ABC):
    """
    Abstract base class for AI agents.

    Provides common functionality for agent lifecycle management,
    state management, memory, goals, and metrics tracking.

    This base class supports extensive flexibility and advanced features:

    **Tool Flexibility:**
    - Accept tool names (List[str]) for backward compatibility
    - Accept pre-configured tool instances (Dict[str, BaseTool]) with preserved state
    - Automatic tool loading and validation

    **LLM Client Flexibility:**
    - Accept any object implementing LLMClientProtocol (duck typing)
    - No requirement for BaseLLMClient inheritance
    - Custom LLM client wrappers fully supported

    **Advanced Features:**
    - ContextEngine integration for persistent conversation history
    - Custom config managers for dynamic configuration
    - Checkpointers for state persistence (LangGraph compatible)
    - Agent collaboration (delegation, peer review, consensus)
    - Agent learning from experiences
    - Resource management (rate limiting, quotas)
    - Performance tracking and health monitoring
    - Tool result caching
    - Parallel tool execution
    - Streaming responses
    - Error recovery strategies

    Examples:
        # Example 1: Basic agent with tool names (backward compatible)
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search", "calculator"]  # Tool names loaded by subclass
        )

        # Example 2: Agent with tool instances (preserves tool state)
        from aiecs.tools import BaseTool

        class StatefulSearchTool(BaseTool):
            def __init__(self, api_key: str):
                self.api_key = api_key
                self.call_count = 0  # State preserved

            async def run_async(self, query: str):
                self.call_count += 1
                return f"Search results for: {query}"

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools={
                "search": StatefulSearchTool(api_key="..."),
                "calculator": CalculatorTool()
            },
            llm_client=OpenAIClient()
        )
        # Tool state (call_count) is preserved across agent operations

        # Example 3: Agent with custom LLM client (no BaseLLMClient inheritance)
        class CustomLLMClient:
            provider_name = "custom"

            async def generate_text(self, messages, **kwargs):
                # Custom implementation
                return LLMResponse(content="...", provider="custom")

            async def stream_text(self, messages, **kwargs):
                async for token in self._custom_stream():
                    yield token

            async def close(self):
                # Cleanup
                pass

        agent = LLMAgent(
            agent_id="agent1",
            name="My LLM Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            llm_client=CustomLLMClient()  # Works without BaseLLMClient!
        )

        # Example 4: Agent with ContextEngine for persistent storage
        from aiecs.domain.context import ContextEngine

        context_engine = ContextEngine()
        await context_engine.initialize()

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            context_engine=context_engine  # Enables persistent conversation history
        )
        # Conversation history persists across agent restarts

        # Example 5: Agent with custom config manager
        class DatabaseConfigManager:
            async def get_config(self, key: str):
                # Load from database
                return await db.get_config(key)

            async def update_config(self, key: str, value: Any):
                # Update in database
                await db.update_config(key, value)

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            config_manager=DatabaseConfigManager()  # Dynamic config loading
        )

        # Example 6: Agent with checkpointer for LangGraph integration
        class RedisCheckpointer:
            async def save(self, agent_id: str, state: Dict[str, Any]):
                await redis.set(f"checkpoint:{agent_id}", json.dumps(state))

            async def load(self, agent_id: str) -> Optional[Dict[str, Any]]:
                data = await redis.get(f"checkpoint:{agent_id}")
                return json.loads(data) if data else None

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            checkpointer=RedisCheckpointer()  # LangGraph-compatible checkpointing
        )

        # Example 7: Agent with collaboration features
        agent_registry = {
            "agent2": other_agent_instance,
            "agent3": another_agent_instance
        }

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            collaboration_enabled=True,
            agent_registry=agent_registry  # Enable delegation and peer review
        )

        # Delegate task to another agent
        result = await agent.delegate_task(
            task_description="Analyze this data",
            target_agent_id="agent2"
        )

        # Example 8: Agent with learning enabled
        from aiecs.domain.agent.models import ResourceLimits

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            learning_enabled=True  # Learn from past experiences
        )

        # Record experience
        await agent.record_experience(
            task_type="data_analysis",
            approach="parallel_tools",
            success=True,
            execution_time=2.5
        )

        # Get recommended approach based on history
        approach = await agent.get_recommended_approach("data_analysis")
        print(f"Recommended: {approach}")

        # Example 9: Agent with resource limits
        from aiecs.domain.agent.models import ResourceLimits

        resource_limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tokens_per_minute=10000,
            max_tool_calls_per_minute=100
        )

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient(),
            resource_limits=resource_limits  # Rate limiting and quotas
        )

        # Check resource availability before executing
        if await agent.check_resource_availability():
            result = await agent.execute_task(task, context)
        else:
            await agent.wait_for_resources(timeout=30.0)

        # Example 10: Agent with performance tracking
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient()
        )

        # Track operation performance
        with agent.track_operation_time("data_processing"):
            result = await agent.execute_task(task, context)

        # Get performance metrics
        metrics = agent.get_performance_metrics()
        print(f"Average response time: {metrics['avg_response_time']}s")
        print(f"P95 response time: {metrics['p95_response_time']}s")

        # Get health status
        health = agent.get_health_status()
        print(f"Health score: {health['score']}")
        print(f"Status: {health['status']}")

        # Example 11: Agent with tool caching
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient()
        )

        # Execute tool with caching (30 second TTL)
        result1 = await agent.execute_tool_with_cache(
            tool_name="search",
            operation="query",
            parameters={"q": "AI"},
            cache_ttl=30
        )

        # Second call uses cache (no API call)
        result2 = await agent.execute_tool_with_cache(
            tool_name="search",
            operation="query",
            parameters={"q": "AI"},
            cache_ttl=30
        )

        # Get cache statistics
        stats = agent.get_cache_stats()
        print(f"Cache hit rate: {stats['hit_rate']:.1%}")

        # Example 12: Agent with parallel tool execution
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search", "calculator", "translator"],
            llm_client=OpenAIClient()
        )

        # Execute multiple independent tools in parallel (3-5x faster)
        results = await agent.execute_tools_parallel([
            {"tool": "search", "operation": "query", "parameters": {"q": "AI"}},
            {"tool": "calculator", "operation": "add", "parameters": {"a": 1, "b": 2}},
            {"tool": "translator", "operation": "translate", "parameters": {"text": "Hello"}}
        ], max_concurrency=3)

        # Example 13: Agent with streaming responses
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient()
        )

        # Stream task execution (tokens + tool calls)
        async for event in agent.execute_task_streaming(task, context):
            if event['type'] == 'token':
                print(event['content'], end='', flush=True)
            elif event['type'] == 'tool_call':
                print(f"\\nCalling {event['tool_name']}...")
            elif event['type'] == 'result':
                print(f"\\nFinal result: {event['output']}")

        # Example 14: Agent with error recovery
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            agent_type=AgentType.HYBRID,
            config=config,
            tools=["search"],
            llm_client=OpenAIClient()
        )

        # Execute with automatic recovery strategies
        result = await agent.execute_with_recovery(
            task=task,
            context=context,
            strategies=["retry", "simplify", "fallback", "delegate"]
        )
        # Automatically tries retry → simplify → fallback → delegate if errors occur
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        agent_type: AgentType,
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        tools: Optional[Union[List[str], Dict[str, "BaseTool"]]] = None,
        llm_client: Optional["LLMClientProtocol"] = None,
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional["CheckpointerProtocol"] = None,
        context_engine: Optional["ContextEngine"] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
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
            tools: Optional tools - either list of tool names or dict of tool instances.
                   List[str]: Tool names to be loaded by subclass
                   Dict[str, BaseTool]: Pre-configured tool instances with state
            llm_client: Optional LLM client (any object implementing LLMClientProtocol).
                       Supports custom LLM clients without BaseLLMClient inheritance.
            config_manager: Optional configuration manager for dynamic config loading
            checkpointer: Optional checkpointer for state persistence (LangGraph compatible)
            context_engine: Optional ContextEngine instance for persistent conversation history
            collaboration_enabled: Enable agent collaboration features (delegation, peer review)
            agent_registry: Registry of other agents for collaboration (agent_id -> agent instance)
            learning_enabled: Enable agent learning from experiences
            resource_limits: Optional resource limits configuration
                          and session management. If provided, enables persistent storage
                          across agent restarts.

        Example:
            # With tool instances and ContextEngine
            from aiecs.domain.context import ContextEngine

            context_engine = ContextEngine()
            await context_engine.initialize()

            agent = HybridAgent(
                agent_id="agent1",
                name="My Agent",
                agent_type=AgentType.HYBRID,
                config=config,
                tools={
                    "search": SearchTool(api_key="..."),
                    "calculator": CalculatorTool()
                },
                llm_client=CustomLLMClient(),  # Custom client, no inheritance needed
                config_manager=DatabaseConfigManager(),
                checkpointer=RedisCheckpointer(),
                context_engine=context_engine  # Enables persistent storage
            )

            # With tool names (backward compatible)
            agent = HybridAgent(
                agent_id="agent1",
                name="My Agent",
                agent_type=AgentType.HYBRID,
                config=config,
                tools=["search", "calculator"]  # Loaded by subclass
            )
        """
        # Identity
        self.agent_id = agent_id
        self.name = name
        self.agent_type = agent_type
        self.description = description or f"{agent_type.value} agent"
        self.version = version

        # Configuration
        self._config = config
        self._config_manager = config_manager

        # State
        self._state = AgentState.CREATED
        self._previous_state: Optional[AgentState] = None

        # Memory storage (in-memory dict, can be replaced with sophisticated
        # storage)
        self._memory: Dict[str, Any] = {}
        self._memory_metadata: Dict[str, Dict[str, Any]] = {}

        # Goals
        self._goals: Dict[str, AgentGoal] = {}

        # Capabilities
        self._capabilities: Dict[str, AgentCapabilityDeclaration] = {}

        # Metrics
        self._metrics = AgentMetrics()  # type: ignore[call-arg]

        # Timestamps
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_active_at: Optional[datetime] = None

        # Current task tracking
        self._current_task_id: Optional[str] = None

        # Tools (optional - only set if tools provided)
        self._tools_input = tools  # Store original input
        self._available_tools: Optional[List[str]] = None
        self._tool_instances: Optional[Dict[str, "BaseTool"]] = None

        # LLM client (optional)
        self._llm_client = llm_client

        # Checkpointer (optional)
        self._checkpointer = checkpointer

        # ContextEngine (optional - Phase 4 enhancement)
        self._context_engine = context_engine

        # Tool result cache (Phase 7 enhancement)
        self._cache_config = CacheConfig()
        self._tool_cache: Dict[str, Any] = {}  # Cache key -> result
        self._cache_timestamps: Dict[str, float] = {}  # Cache key -> timestamp
        self._cache_access_count: Dict[str, int] = {}  # Cache key -> access count
        self._last_cleanup_time = time.time()

        # Agent collaboration (Phase 7 enhancement - tasks 1.15.15-1.15.22)
        self._collaboration_enabled = collaboration_enabled
        self._agent_registry = agent_registry or {}

        # Agent learning (Phase 8 enhancement - tasks 1.16.4-1.16.10)
        self._learning_enabled = learning_enabled
        self._experiences: List[Any] = []  # List of Experience objects
        self._max_experiences = 1000  # Limit stored experiences

        # Resource management (Phase 8 enhancement - tasks 1.16.11-1.16.17)
        from .models import ResourceLimits

        self._resource_limits = resource_limits or ResourceLimits()  # type: ignore[call-arg]
        self._active_tasks: set = set()  # Set of active task IDs
        self._token_usage_window: List[tuple] = []  # List of (timestamp, token_count)
        self._tool_call_window: List[float] = []  # List of timestamps

        features = []
        if context_engine:
            features.append("ContextEngine")
        if collaboration_enabled:
            features.append("collaboration")
        if learning_enabled:
            features.append("learning")
        if resource_limits:
            features.append("resource limits")

        feature_str = f" with {', '.join(features)}" if features else ""
        logger.info(f"Agent initialized: {self.agent_id} ({self.name}, {self.agent_type.value}){feature_str}")

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
            AgentState.ACTIVE: {
                AgentState.BUSY,
                AgentState.IDLE,
                AgentState.STOPPED,
                AgentState.ERROR,
            },
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

    async def activate(self) -> None:
        """Activate the agent."""
        if self._state == AgentState.IDLE:
            self._transition_state(AgentState.ACTIVE)
            self.last_active_at = datetime.utcnow()
            logger.info(f"Agent {self.agent_id} activated")
        else:
            logger.warning(f"Agent {self.agent_id} cannot be activated from state {self._state.value}")

    async def deactivate(self) -> None:
        """Deactivate the agent (enter idle state)."""
        if self._state == AgentState.ACTIVE:
            self._transition_state(AgentState.IDLE)
            logger.info(f"Agent {self.agent_id} deactivated")
        else:
            logger.warning(f"Agent {self.agent_id} cannot be deactivated from state {self._state.value}")

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

    # ==================== Tool and LLM Client Helper Methods ====================

    def _load_tools(self) -> None:
        """
        Load tools from the tools input parameter.

        Handles both List[str] (tool names) and Dict[str, BaseTool] (tool instances).
        Sets _available_tools and _tool_instances appropriately.

        This helper method should be called by subclasses during initialization
        if they want to use BaseAIAgent's tool management.

        Raises:
            ConfigurationError: If tools input is invalid
        """
        if self._tools_input is None:
            # No tools provided
            return

        if isinstance(self._tools_input, list):
            # Tool names - store for subclass to load
            self._available_tools = self._tools_input
            logger.debug(f"Agent {self.agent_id}: Registered {len(self._tools_input)} tool names")

        elif isinstance(self._tools_input, dict):
            # Tool instances - validate and store
            from aiecs.tools.base_tool import BaseTool

            for tool_name, tool_instance in self._tools_input.items():
                if not isinstance(tool_instance, BaseTool):
                    raise ConfigurationError(f"Tool '{tool_name}' must be a BaseTool instance, got {type(tool_instance)}")

            self._tool_instances = self._tools_input
            self._available_tools = list(self._tools_input.keys())
            logger.debug(f"Agent {self.agent_id}: Registered {len(self._tools_input)} tool instances")

        else:
            raise ConfigurationError(f"Tools must be List[str] or Dict[str, BaseTool], got {type(self._tools_input)}")

    def _validate_llm_client(self) -> None:
        """
        Validate that the LLM client implements the required protocol.

        Checks that the LLM client has the required methods:
        - generate_text
        - stream_text
        - close
        - provider_name (property)

        This helper method should be called by subclasses during initialization
        if they want to use BaseAIAgent's LLM client validation.

        Raises:
            ConfigurationError: If LLM client doesn't implement required methods
        """
        if self._llm_client is None:
            return

        required_methods = ["generate_text", "stream_text", "close"]
        required_properties = ["provider_name"]

        for method_name in required_methods:
            if not hasattr(self._llm_client, method_name):
                raise ConfigurationError(f"LLM client must implement '{method_name}' method")
            if not callable(getattr(self._llm_client, method_name)):
                raise ConfigurationError(f"LLM client '{method_name}' must be callable")

        for prop_name in required_properties:
            if not hasattr(self._llm_client, prop_name):
                raise ConfigurationError(f"LLM client must have '{prop_name}' property")

        logger.debug(f"Agent {self.agent_id}: LLM client validated successfully")

    def _get_tool_instances(self) -> Optional[Dict[str, "BaseTool"]]:
        """
        Get tool instances dictionary.

        Returns:
            Dictionary of tool instances, or None if no tool instances available
        """
        return self._tool_instances

    def get_config_manager(self) -> Optional["ConfigManagerProtocol"]:
        """
        Get the configuration manager.

        Returns:
            Configuration manager instance, or None if not configured
        """
        return self._config_manager

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

    # ==================== Retry Logic Integration ====================

    async def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
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
            jitter=retry_config.jitter_factor > 0,
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

    async def retrieve_memory(self, key: str, default: Any = None) -> Any:
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
            keys_to_remove = [k for k, v in self._memory_metadata.items() if v.get("type") == memory_type.value]
            for key in keys_to_remove:
                del self._memory[key]
                del self._memory_metadata[key]
            logger.info(f"Agent {self.agent_id} cleared {memory_type.value} memory")

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of agent memory."""
        return {
            "total_items": len(self._memory),
            "short_term_count": sum(1 for v in self._memory_metadata.values() if v.get("type") == MemoryType.SHORT_TERM.value),
            "long_term_count": sum(1 for v in self._memory_metadata.values() if v.get("type") == MemoryType.LONG_TERM.value),
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
        goal = AgentGoal(  # type: ignore[call-arg]
            description=description,
            priority=priority,
            success_criteria=success_criteria,
            deadline=deadline,
        )
        self._goals[goal.goal_id] = goal
        logger.info(f"Agent {self.agent_id} set goal: {goal.goal_id} ({priority.value})")
        return goal.goal_id

    def get_goals(self, status: Optional[GoalStatus] = None) -> List[AgentGoal]:
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
        self._metrics.success_rate = self._metrics.successful_tasks / self._metrics.total_tasks_executed * 100

        # Update execution time
        if execution_time is not None:
            self._metrics.total_execution_time += execution_time
            self._metrics.average_execution_time = self._metrics.total_execution_time / self._metrics.total_tasks_executed

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
                total_quality = self._metrics.average_quality_score * (self._metrics.total_tasks_executed - 1)
                self._metrics.average_quality_score = (total_quality + quality_score) / self._metrics.total_tasks_executed

        # Update resource usage
        if tokens_used is not None:
            self._metrics.total_tokens_used += tokens_used
        if tool_calls is not None:
            self._metrics.total_tool_calls += tool_calls

        self._metrics.updated_at = datetime.utcnow()

    def update_session_metrics(
        self,
        session_status: str,
        session_duration: Optional[float] = None,
        session_requests: int = 0,
    ) -> None:
        """
        Update session-level metrics.

        This method should be called when a session is created, updated, or ended
        to track session-level statistics in agent metrics.

        Args:
            session_status: Session status (active, completed, failed, expired)
            session_duration: Session duration in seconds (for ended sessions)
            session_requests: Number of requests in the session

        Example:
            # When creating a session
            agent.update_session_metrics(session_status="active")

            # When ending a session
            agent.update_session_metrics(
                session_status="completed",
                session_duration=300.5,
                session_requests=15
            )
        """
        # Update session counts based on status
        if session_status == "active":
            self._metrics.total_sessions += 1
            self._metrics.active_sessions += 1
        elif session_status == "completed":
            self._metrics.completed_sessions += 1
            if self._metrics.active_sessions > 0:
                self._metrics.active_sessions -= 1
        elif session_status == "failed":
            self._metrics.failed_sessions += 1
            if self._metrics.active_sessions > 0:
                self._metrics.active_sessions -= 1
        elif session_status == "expired":
            self._metrics.expired_sessions += 1
            if self._metrics.active_sessions > 0:
                self._metrics.active_sessions -= 1

        # Update session request tracking
        if session_requests > 0:
            self._metrics.total_session_requests += session_requests

        # Update average session duration
        if session_duration is not None and session_duration > 0:
            completed_count = self._metrics.completed_sessions + self._metrics.failed_sessions + self._metrics.expired_sessions
            if completed_count > 0:
                if self._metrics.average_session_duration is None:
                    self._metrics.average_session_duration = session_duration
                else:
                    # Running average
                    total_duration = self._metrics.average_session_duration * (completed_count - 1)
                    self._metrics.average_session_duration = (total_duration + session_duration) / completed_count

        # Update average requests per session
        if self._metrics.total_sessions > 0:
            self._metrics.average_requests_per_session = self._metrics.total_session_requests / self._metrics.total_sessions

        self._metrics.updated_at = datetime.utcnow()
        logger.debug(f"Agent {self.agent_id} session metrics updated: " f"status={session_status}, total_sessions={self._metrics.total_sessions}, " f"active_sessions={self._metrics.active_sessions}")

    # ==================== Performance Tracking ====================

    def track_operation_time(self, operation_name: str) -> OperationTimer:
        """
        Create a context manager for tracking operation time.

        This method returns an OperationTimer that automatically records
        operation duration and updates agent metrics when the operation completes.

        Args:
            operation_name: Name of the operation to track

        Returns:
            OperationTimer context manager

        Example:
            with agent.track_operation_time("llm_call") as timer:
                result = await llm.generate(prompt)
            # Metrics are automatically recorded

            # Access duration if needed
            print(f"Operation took {timer.duration} seconds")
        """
        return OperationTimer(operation_name=operation_name, agent=self)

    def _record_operation_metrics(self, operation_name: str, duration: float, success: bool = True) -> None:
        """
        Record operation-level metrics.

        This method is called automatically by OperationTimer but can also
        be called manually to record operation metrics.

        Args:
            operation_name: Name of the operation
            duration: Operation duration in seconds
            success: Whether the operation succeeded

        Example:
            # Manual recording
            start = time.time()
            try:
                result = perform_operation()
                agent._record_operation_metrics("custom_op", time.time() - start, True)
            except Exception:
                agent._record_operation_metrics("custom_op", time.time() - start, False)
                raise
        """
        # Update operation counts
        if operation_name not in self._metrics.operation_counts:
            self._metrics.operation_counts[operation_name] = 0
            self._metrics.operation_total_time[operation_name] = 0.0
            self._metrics.operation_error_counts[operation_name] = 0

        self._metrics.operation_counts[operation_name] += 1
        self._metrics.operation_total_time[operation_name] += duration

        if not success:
            self._metrics.operation_error_counts[operation_name] += 1

        # Add to operation history (keep last 100 operations)
        operation_record = {
            "operation": operation_name,
            "duration": duration,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._metrics.operation_history.append(operation_record)

        # Keep only last 100 operations
        if len(self._metrics.operation_history) > 100:
            self._metrics.operation_history = self._metrics.operation_history[-100:]

        # Recalculate percentiles
        self._update_operation_percentiles()

        self._metrics.updated_at = datetime.utcnow()
        logger.debug(f"Agent {self.agent_id} operation metrics recorded: " f"operation={operation_name}, duration={duration:.3f}s, success={success}")

    def _update_operation_percentiles(self) -> None:
        """Update operation time percentiles from operation history."""
        if not self._metrics.operation_history:
            return

        # Extract durations from operation history
        durations = [op["duration"] for op in self._metrics.operation_history]

        # Calculate percentiles
        self._metrics.p50_operation_time = self._calculate_percentile(durations, 50)
        self._metrics.p95_operation_time = self._calculate_percentile(durations, 95)
        self._metrics.p99_operation_time = self._calculate_percentile(durations, 99)

    def _calculate_percentile(self, values: List[float], percentile: int) -> Optional[float]:
        """
        Calculate percentile from a list of values.

        Args:
            values: List of numeric values
            percentile: Percentile to calculate (0-100)

        Returns:
            Percentile value or None if values is empty

        Example:
            p95 = agent._calculate_percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95)
        """
        if not values:
            return None

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)

        # Handle edge cases
        if index >= len(sorted_values):
            index = len(sorted_values) - 1

        return sorted_values[index]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.

        Returns detailed performance statistics including operation-level
        metrics, percentiles, and aggregated statistics.

        Returns:
            Dictionary with performance metrics

        Example:
            metrics = agent.get_performance_metrics()
            print(f"P95 latency: {metrics['p95_operation_time']}s")
            print(f"Total operations: {metrics['total_operations']}")
            for op_name, stats in metrics['operations'].items():
                print(f"{op_name}: {stats['count']} calls, avg {stats['avg_time']:.3f}s")
        """
        # Calculate per-operation statistics
        operations = {}
        for op_name, count in self._metrics.operation_counts.items():
            total_time = self._metrics.operation_total_time.get(op_name, 0.0)
            error_count = self._metrics.operation_error_counts.get(op_name, 0)

            operations[op_name] = {
                "count": count,
                "total_time": total_time,
                "average_time": total_time / count if count > 0 else 0.0,
                "error_count": error_count,
                "error_rate": (error_count / count * 100) if count > 0 else 0.0,
            }

        return {
            "total_operations": sum(self._metrics.operation_counts.values()),
            "operations": operations,
            "p50_operation_time": self._metrics.p50_operation_time,
            "p95_operation_time": self._metrics.p95_operation_time,
            "p99_operation_time": self._metrics.p99_operation_time,
            "recent_operations": self._metrics.operation_history[-10:],  # Last 10 operations
        }

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get agent health status with health score calculation.

        Calculates a health score (0-100) based on multiple factors:
        - Success rate (40% weight)
        - Error rate (30% weight)
        - Performance (20% weight)
        - Session health (10% weight)

        Returns:
            Dictionary with health status and score

        Example:
            health = agent.get_health_status()
            print(f"Health score: {health['health_score']}/100")
            print(f"Status: {health['status']}")  # healthy, degraded, unhealthy
            if health['issues']:
                print(f"Issues: {', '.join(health['issues'])}")
        """
        issues = []
        health_score = 100.0

        # Factor 1: Success rate (40% weight)
        success_rate = self._metrics.success_rate
        if success_rate < 50:
            issues.append("Low success rate")
            health_score -= 40
        elif success_rate < 80:
            issues.append("Moderate success rate")
            health_score -= 20
        elif success_rate < 95:
            health_score -= 10

        # Factor 2: Error rate (30% weight)
        total_tasks = self._metrics.total_tasks_executed
        if total_tasks > 0:
            error_rate = (self._metrics.failed_tasks / total_tasks) * 100
            if error_rate > 50:
                issues.append("High error rate")
                health_score -= 30
            elif error_rate > 20:
                issues.append("Elevated error rate")
                health_score -= 15
            elif error_rate > 5:
                health_score -= 5

        # Factor 3: Performance (20% weight)
        if self._metrics.p95_operation_time is not None:
            # Consider p95 > 5s as slow
            if self._metrics.p95_operation_time > 10:
                issues.append("Very slow operations (p95 > 10s)")
                health_score -= 20
            elif self._metrics.p95_operation_time > 5:
                issues.append("Slow operations (p95 > 5s)")
                health_score -= 10

        # Factor 4: Session health (10% weight)
        if self._metrics.total_sessions > 0:
            session_failure_rate = (self._metrics.failed_sessions + self._metrics.expired_sessions) / self._metrics.total_sessions * 100
            if session_failure_rate > 30:
                issues.append("High session failure rate")
                health_score -= 10
            elif session_failure_rate > 10:
                health_score -= 5

        # Ensure health score is in valid range
        health_score = max(0.0, min(100.0, health_score))

        # Determine status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "health_score": health_score,
            "status": status,
            "issues": issues,
            "metrics_summary": {
                "success_rate": success_rate,
                "total_tasks": total_tasks,
                "total_sessions": self._metrics.total_sessions,
                "active_sessions": self._metrics.active_sessions,
                "p95_operation_time": self._metrics.p95_operation_time,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status combining all metrics.

        Returns a complete view of agent state, health, performance,
        and operational metrics.

        Returns:
            Dictionary with comprehensive status information

        Example:
            status = agent.get_comprehensive_status()
            print(f"Agent: {status['agent_id']}")
            print(f"State: {status['state']}")
            print(f"Health: {status['health']['status']} ({status['health']['health_score']}/100)")
            print(f"Tasks: {status['metrics']['total_tasks_executed']}")
            print(f"Sessions: {status['metrics']['total_sessions']}")
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "type": self.agent_type.value,
            "version": self.version,
            "state": self._state.value,
            "health": self.get_health_status(),
            "performance": self.get_performance_metrics(),
            "metrics": {
                # Task metrics
                "total_tasks_executed": self._metrics.total_tasks_executed,
                "successful_tasks": self._metrics.successful_tasks,
                "failed_tasks": self._metrics.failed_tasks,
                "success_rate": self._metrics.success_rate,
                # Execution time metrics
                "average_execution_time": self._metrics.average_execution_time,
                "total_execution_time": self._metrics.total_execution_time,
                # Session metrics
                "total_sessions": self._metrics.total_sessions,
                "active_sessions": self._metrics.active_sessions,
                "completed_sessions": self._metrics.completed_sessions,
                "failed_sessions": self._metrics.failed_sessions,
                "expired_sessions": self._metrics.expired_sessions,
                # Resource usage
                "total_tokens_used": self._metrics.total_tokens_used,
                "total_tool_calls": self._metrics.total_tool_calls,
                # Error tracking
                "error_count": self._metrics.error_count,
                "error_types": self._metrics.error_types,
            },
            "capabilities": [cap.capability_type for cap in self.get_capabilities()],
            "active_goals": len([g for g in self._goals.values() if g.status == GoalStatus.IN_PROGRESS]),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset_metrics(self) -> None:
        """
        Reset performance and session metrics.

        Resets all metrics to their initial state while preserving
        agent configuration and state.

        Example:
            # Reset metrics at the start of a new monitoring period
            agent.reset_metrics()
        """
        self._metrics = AgentMetrics(last_reset_at=datetime.utcnow())  # type: ignore[call-arg]
        logger.info(f"Agent {self.agent_id} metrics reset")

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize agent to dictionary.

        Includes health status and performance metrics for comprehensive
        agent state representation.

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
                "health_status": self.get_health_status(),  # Phase 3 enhancement
                "performance_metrics": self.get_performance_metrics(),  # Phase 3 enhancement
                "memory_summary": self.get_memory_summary(),
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "last_active_at": (self.last_active_at.isoformat() if self.last_active_at else None),
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

    # ==================== Checkpointer Support ====================

    async def save_checkpoint(self, session_id: str, checkpoint_id: Optional[str] = None) -> Optional[str]:
        """
        Save agent state checkpoint.

        This method saves the current agent state using the configured checkpointer.
        If no checkpointer is configured, logs a warning and returns None.

        Args:
            session_id: Session identifier for the checkpoint
            checkpoint_id: Optional checkpoint identifier (auto-generated if None)

        Returns:
            Checkpoint ID if saved successfully, None otherwise

        Example:
            # Save checkpoint with auto-generated ID
            checkpoint_id = await agent.save_checkpoint(session_id="session-123")

            # Save checkpoint with custom ID
            checkpoint_id = await agent.save_checkpoint(
                session_id="session-123",
                checkpoint_id="v1.0"
            )

        Note:
            Requires a checkpointer to be configured during agent initialization.
            The checkpoint includes full agent state from to_dict().
        """
        if not self._checkpointer:
            logger.warning(f"Agent {self.agent_id}: No checkpointer configured, cannot save checkpoint")
            return None

        try:
            # Get current agent state
            checkpoint_data = self.to_dict()

            # Add checkpoint metadata
            checkpoint_data["checkpoint_metadata"] = {
                "session_id": session_id,
                "checkpoint_id": checkpoint_id,
                "saved_at": datetime.utcnow().isoformat(),
                "agent_version": self.version,
            }

            # Save using checkpointer
            saved_checkpoint_id = await self._checkpointer.save_checkpoint(
                agent_id=self.agent_id,
                session_id=session_id,
                checkpoint_data=checkpoint_data,
            )

            logger.info(f"Agent {self.agent_id}: Checkpoint saved successfully " f"(session={session_id}, checkpoint={saved_checkpoint_id})")
            return saved_checkpoint_id

        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Failed to save checkpoint " f"(session={session_id}): {e}")
            return None

    async def load_checkpoint(self, session_id: str, checkpoint_id: Optional[str] = None) -> bool:
        """
        Load agent state from checkpoint.

        This method loads agent state from a saved checkpoint using the configured
        checkpointer. If no checkpointer is configured, logs a warning and returns False.

        Args:
            session_id: Session identifier for the checkpoint
            checkpoint_id: Optional checkpoint identifier (loads latest if None)

        Returns:
            True if checkpoint loaded successfully, False otherwise

        Example:
            # Load latest checkpoint
            success = await agent.load_checkpoint(session_id="session-123")

            # Load specific checkpoint
            success = await agent.load_checkpoint(
                session_id="session-123",
                checkpoint_id="v1.0"
            )

        Note:
            Requires a checkpointer to be configured during agent initialization.
            This method updates the agent's internal state from the checkpoint.
            Not all state may be restorable (e.g., runtime objects, connections).
        """
        if not self._checkpointer:
            logger.warning(f"Agent {self.agent_id}: No checkpointer configured, cannot load checkpoint")
            return False

        try:
            # Load checkpoint data
            checkpoint_data = await self._checkpointer.load_checkpoint(
                agent_id=self.agent_id,
                session_id=session_id,
                checkpoint_id=checkpoint_id,
            )

            if not checkpoint_data:
                logger.warning(f"Agent {self.agent_id}: No checkpoint found " f"(session={session_id}, checkpoint={checkpoint_id or 'latest'})")
                return False

            # Restore agent state from checkpoint
            self._restore_from_checkpoint(checkpoint_data)

            logger.info(f"Agent {self.agent_id}: Checkpoint loaded successfully " f"(session={session_id}, checkpoint={checkpoint_id or 'latest'})")
            return True

        except Exception as e:
            logger.error(f"Agent {self.agent_id}: Failed to load checkpoint " f"(session={session_id}, checkpoint={checkpoint_id or 'latest'}): {e}")
            return False

    def _restore_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """
        Restore agent state from checkpoint data.

        This is an internal method that updates the agent's state from checkpoint data.
        Subclasses can override this to customize restoration logic.

        Args:
            checkpoint_data: Checkpoint data dictionary

        Note:
            This method restores basic agent state. Runtime objects like
            connections, file handles, etc. are not restored.
        """
        # Restore basic state
        if "state" in checkpoint_data:
            try:
                self._state = AgentState(checkpoint_data["state"])
            except (ValueError, KeyError):
                logger.warning("Could not restore state from checkpoint")

        # Restore metrics
        if "metrics" in checkpoint_data:
            try:
                self._metrics = AgentMetrics(**checkpoint_data["metrics"])
            except Exception as e:
                logger.warning(f"Could not restore metrics from checkpoint: {e}")

        # Restore goals
        if "goals" in checkpoint_data:
            try:
                self._goals = {}
                for goal_data in checkpoint_data["goals"]:
                    goal = AgentGoal(**goal_data)
                    self._goals[goal.goal_id] = goal
            except Exception as e:
                logger.warning(f"Could not restore goals from checkpoint: {e}")

        # Update timestamps
        self.updated_at = datetime.utcnow()

        logger.debug(f"Agent {self.agent_id}: State restored from checkpoint")

    # ==================== Utility Methods ====================

    def is_available(self) -> bool:
        """Check if agent is available for tasks."""
        return self._state == AgentState.ACTIVE

    def is_busy(self) -> bool:
        """Check if agent is currently busy."""
        return self._state == AgentState.BUSY

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a single tool with given parameters.

        This is a default implementation that subclasses can override.
        For ToolAgent, this calls _execute_tool with operation from parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters (may include 'operation' key)

        Returns:
            Tool execution result
        """
        # Check if we have tool instances
        if hasattr(self, "_tool_instances") and self._tool_instances:
            tool = self._tool_instances.get(tool_name)
            if tool:
                # Make a copy to avoid modifying the original
                params = parameters.copy()

                # Try to execute the tool directly (for custom tools with execute method)
                if hasattr(tool, "execute"):
                    return await tool.execute(**params)
                # For standard tools with run_async
                elif hasattr(tool, "run_async"):
                    # Check if operation is specified
                    operation = params.pop("operation", None)
                    if operation:
                        return await tool.run_async(operation, **params)
                    else:
                        return await tool.run_async(**params)

        raise NotImplementedError(f"execute_tool not implemented for {self.__class__.__name__}. " "Tool {tool_name} not found or doesn't have execute/run_async method.")

    # ==================== Parallel Tool Execution (Phase 7) ====================

    async def execute_tools_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        max_concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tools in parallel with concurrency limit.

        Args:
            tool_calls: List of tool call dicts with 'tool_name' and 'parameters'
            max_concurrency: Maximum number of concurrent tool executions

        Returns:
            List of results in same order as tool_calls

        Example:
            tool_calls = [
                {"tool_name": "search", "parameters": {"query": "AI"}},
                {"tool_name": "calculator", "parameters": {"expression": "2+2"}},
                {"tool_name": "search", "parameters": {"query": "ML"}},
            ]
            results = await agent.execute_tools_parallel(tool_calls, max_concurrency=2)
        """
        if not tool_calls:
            return []

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)

        async def execute_with_semaphore(tool_call: Dict[str, Any], index: int):
            """Execute tool with semaphore."""
            async with semaphore:
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})

                if tool_name is None:
                    raise ValueError("tool_name is required in tool_call")

                try:
                    # Execute tool (subclass should implement execute_tool)
                    result = await self.execute_tool(tool_name, parameters)
                    return {"index": index, "success": True, "result": result}
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed: {e}")
                    return {
                        "index": index,
                        "success": False,
                        "error": str(e),
                        "tool_name": tool_name,
                    }

        # Execute all tools in parallel
        tasks = [execute_with_semaphore(tool_call, i) for i, tool_call in enumerate(tool_calls)]

        results_unordered = await asyncio.gather(*tasks, return_exceptions=True)

        # Sort results by index to maintain order
        valid_results = [r for r in results_unordered if not isinstance(r, Exception) and isinstance(r, dict) and "index" in r]
        results_sorted = sorted(
            valid_results,
            key=lambda x: x["index"],  # type: ignore[index]
        )

        # Remove index from results
        return [{k: v for k, v in r.items() if k != "index"} for r in results_sorted]

    async def analyze_tool_dependencies(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analyze dependencies between tool calls.

        Detects if one tool's output is used as input to another tool.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            Dict mapping tool index to list of dependency indices

        Example:
            tool_calls = [
                {"tool_name": "search", "parameters": {"query": "AI"}},
                {"tool_name": "summarize", "parameters": {"text": "${0.result}"}},
            ]
            deps = await agent.analyze_tool_dependencies(tool_calls)
            # deps = {"1": ["0"]}  # Tool 1 depends on tool 0
        """
        dependencies: Dict[str, List[str]] = {}

        for i, tool_call in enumerate(tool_calls):
            deps = []
            parameters = tool_call.get("parameters", {})

            # Check if parameters reference other tool results
            param_str = json.dumps(parameters)

            # Look for ${index.field} patterns
            import re

            matches = re.findall(r"\$\{(\d+)\.", param_str)
            deps = list(set(matches))  # Remove duplicates

            if deps:
                dependencies[str(i)] = deps

        return dependencies

    async def execute_tools_with_dependencies(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute tools respecting dependencies using topological sort.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            List of results in same order as tool_calls

        Example:
            tool_calls = [
                {"tool_name": "search", "parameters": {"query": "AI"}},
                {"tool_name": "summarize", "parameters": {"text": "${0.result}"}},
            ]
            results = await agent.execute_tools_with_dependencies(tool_calls)
        """
        # Analyze dependencies
        dependencies = await self.analyze_tool_dependencies(tool_calls)

        # Topological sort
        executed: Set[int] = set()
        results: List[Optional[Dict[str, Any]]] = [None] * len(tool_calls)

        def can_execute(index: int) -> bool:
            """Check if tool can be executed."""
            deps = dependencies.get(str(index), [])
            return all(int(dep) in executed for dep in deps)

        # Execute tools in dependency order
        while len(executed) < len(tool_calls):
            # Find tools that can be executed
            ready = [i for i in range(len(tool_calls)) if i not in executed and can_execute(i)]

            if not ready:
                # Circular dependency or error
                logger.error("Circular dependency detected or no tools ready")
                break

            # Execute ready tools in parallel
            ready_calls = [tool_calls[i] for i in ready]
            ready_results = await self.execute_tools_parallel(ready_calls)

            # Store results and mark as executed
            for i, result in zip(ready, ready_results):
                if result is not None:
                    results[i] = result
                executed.add(i)

                # Substitute results in dependent tool calls
                for j in range(len(tool_calls)):
                    if j not in executed:
                        tool_calls[j] = self._substitute_tool_result(tool_calls[j], i, result)

        # Filter out None values and return
        return [r for r in results if r is not None]

    def _substitute_tool_result(self, tool_call: Dict[str, Any], source_index: int, source_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute tool result references in parameters.

        Args:
            tool_call: Tool call dict
            source_index: Index of source tool
            source_result: Result from source tool

        Returns:
            Updated tool call dict
        """
        import re

        param_str = json.dumps(tool_call.get("parameters", {}))

        # Replace ${index.field} with actual values
        pattern = rf"\$\{{{source_index}\.(\w+)\}}"

        def replacer(match):
            field = match.group(1)
            value = source_result.get(field)
            return json.dumps(value) if value is not None else "null"

        param_str = re.sub(pattern, replacer, param_str)

        tool_call["parameters"] = json.loads(param_str)
        return tool_call

    # ==================== Tool Result Caching (Phase 7) ====================

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Generate cache key for tool result.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            Cache key string

        Example:
            key = agent._generate_cache_key("search", {"query": "AI"})
        """
        # Sort parameters for consistent keys
        param_str = json.dumps(parameters, sort_keys=True)

        # Hash large inputs
        if self._cache_config.hash_large_inputs and len(param_str) > 1024:
            import hashlib

            param_hash = hashlib.md5(param_str.encode()).hexdigest()
            cache_key = f"{tool_name}:{param_hash}"
        else:
            cache_key = f"{tool_name}:{param_str}"

        # Include timestamp if configured
        if self._cache_config.include_timestamp_in_key:
            timestamp = int(time.time() / 60)  # Minute-level granularity
            cache_key = f"{cache_key}:{timestamp}"

        return cache_key

    async def execute_tool_with_cache(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute tool with caching support.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            Tool result (from cache or fresh execution)

        Example:
            result = await agent.execute_tool_with_cache("search", {"query": "AI"})
        """
        if not self._cache_config.enabled:
            # Cache disabled, execute directly
            return await self.execute_tool(tool_name, parameters)

        # Generate cache key
        cache_key = self._generate_cache_key(tool_name, parameters)

        # Check cache
        if cache_key in self._tool_cache:
            # Check TTL
            cached_time = self._cache_timestamps.get(cache_key, 0)
            ttl = self._cache_config.get_ttl(tool_name)
            age = time.time() - cached_time

            if age < ttl:
                # Cache hit
                self._cache_access_count[cache_key] = self._cache_access_count.get(cache_key, 0) + 1
                logger.debug(f"Cache hit for {tool_name} (age: {age:.1f}s)")
                return self._tool_cache[cache_key]
            else:
                # Cache expired
                logger.debug(f"Cache expired for {tool_name} (age: {age:.1f}s)")
                del self._tool_cache[cache_key]
                del self._cache_timestamps[cache_key]
                if cache_key in self._cache_access_count:
                    del self._cache_access_count[cache_key]

        # Cache miss - execute tool
        logger.debug(f"Cache miss for {tool_name}")
        result = await self.execute_tool(tool_name, parameters)

        # Store in cache
        self._tool_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        self._cache_access_count[cache_key] = 0

        # Cleanup if needed
        await self._cleanup_cache()

        return result

    def invalidate_cache(self, tool_name: Optional[str] = None, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            tool_name: Invalidate all entries for this tool (optional)
            pattern: Invalidate entries matching pattern (optional)

        Returns:
            Number of entries invalidated

        Example:
            # Invalidate all search results
            count = agent.invalidate_cache(tool_name="search")

            # Invalidate all cache
            count = agent.invalidate_cache()
        """
        if tool_name is None and pattern is None:
            # Invalidate all
            count = len(self._tool_cache)
            self._tool_cache.clear()
            self._cache_timestamps.clear()
            self._cache_access_count.clear()
            logger.info(f"Invalidated all cache ({count} entries)")
            return count

        # Invalidate matching entries
        keys_to_delete = []

        for key in list(self._tool_cache.keys()):
            if tool_name and key.startswith(f"{tool_name}:"):
                keys_to_delete.append(key)
            elif pattern and pattern in key:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._tool_cache[key]
            del self._cache_timestamps[key]
            if key in self._cache_access_count:
                del self._cache_access_count[key]

        logger.info(f"Invalidated {len(keys_to_delete)} cache entries")
        return len(keys_to_delete)

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        Example:
            stats = agent.get_cache_stats()
            print(f"Cache size: {stats['size']}")
            print(f"Hit rate: {stats['hit_rate']:.1%}")
        """
        total_entries = len(self._tool_cache)
        total_accesses = sum(self._cache_access_count.values())

        # Calculate hit rate (approximate)
        cache_hits = sum(count for count in self._cache_access_count.values() if count > 0)
        hit_rate = cache_hits / total_accesses if total_accesses > 0 else 0.0

        # Calculate memory usage (approximate)
        import sys

        memory_bytes = sum(sys.getsizeof(v) for v in self._tool_cache.values())
        memory_mb = memory_bytes / (1024 * 1024)

        # Per-tool stats
        tool_stats = {}
        for key in self._tool_cache.keys():
            tool_name = key.split(":")[0]
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {"count": 0, "accesses": 0}
            tool_stats[tool_name]["count"] += 1
            tool_stats[tool_name]["accesses"] += self._cache_access_count.get(key, 0)

        return {
            "enabled": self._cache_config.enabled,
            "size": total_entries,
            "max_size": self._cache_config.max_cache_size,
            "memory_mb": memory_mb,
            "max_memory_mb": self._cache_config.max_memory_mb,
            "total_accesses": total_accesses,
            "hit_rate": hit_rate,
            "tool_stats": tool_stats,
        }

    async def _cleanup_cache(self) -> None:
        """
        Cleanup cache based on size and memory limits.

        Removes least recently used entries when limits are exceeded.
        """
        # Check if cleanup needed
        current_time = time.time()
        if current_time - self._last_cleanup_time < self._cache_config.cleanup_interval:
            return

        self._last_cleanup_time = current_time

        # Check size limit
        if len(self._tool_cache) > self._cache_config.max_cache_size * self._cache_config.cleanup_threshold:
            # Remove oldest entries
            entries_to_remove = int(len(self._tool_cache) - self._cache_config.max_cache_size * 0.8)

            # Sort by timestamp (oldest first)
            sorted_keys = sorted(self._cache_timestamps.items(), key=lambda x: x[1])

            for key, _ in sorted_keys[:entries_to_remove]:
                del self._tool_cache[key]
                del self._cache_timestamps[key]
                if key in self._cache_access_count:
                    del self._cache_access_count[key]

            logger.debug(f"Cleaned up {entries_to_remove} cache entries (size limit)")

    # ==================== Streaming Support (Phase 7 - Tasks 1.15.11-1.15.12) ====================

    async def execute_task_streaming(self, task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a task with streaming results.

        This method streams task execution events as they occur, including:
        - Status updates (started, thinking, acting, completed)
        - LLM tokens (for agents with LLM clients)
        - Tool calls and results (for agents with tools)
        - Final result

        Args:
            task: Task specification
            context: Execution context

        Yields:
            Dict[str, Any]: Event dictionaries with 'type' and event-specific data

        Event types:
            - 'status': Status update (e.g., started, thinking, completed)
            - 'token': LLM token (for streaming text generation)
            - 'tool_call': Tool execution started
            - 'tool_result': Tool execution completed
            - 'result': Final task result
            - 'error': Error occurred

        Example:
            ```python
            async for event in agent.execute_task_streaming(task, context):
                if event['type'] == 'token':
                    print(event['content'], end='', flush=True)
                elif event['type'] == 'tool_call':
                    print(f"\\nCalling tool: {event['tool_name']}")
                elif event['type'] == 'tool_result':
                    print(f"Tool result: {event['result']}")
                elif event['type'] == 'result':
                    print(f"\\nFinal result: {event['output']}")
            ```

        Note:
            Subclasses should override this method to provide streaming support.
            Default implementation falls back to non-streaming execute_task.
        """
        # Default implementation: execute task and yield result
        yield {"type": "status", "status": "started", "timestamp": datetime.utcnow().isoformat()}

        try:
            result = await self.execute_task(task, context)
            yield {"type": "result", **result}
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            raise

    async def process_message_streaming(self, message: str, sender_id: Optional[str] = None) -> AsyncIterator[str]:
        """
        Process a message with streaming response.

        This method streams the response text as it's generated, providing
        a better user experience for long responses.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Yields:
            str: Response text tokens/chunks

        Example:
            ```python
            async for token in agent.process_message_streaming("Hello!"):
                print(token, end='', flush=True)
            ```

        Note:
            Subclasses should override this method to provide streaming support.
            Default implementation falls back to non-streaming process_message.
        """
        # Default implementation: process message and yield result
        try:
            result = await self.process_message(message, sender_id)
            response = result.get("response", "")
            yield response
        except Exception as e:
            logger.error(f"Streaming message processing failed: {e}")
            raise

    # ==================== Agent Collaboration (Phase 7 - Tasks 1.15.15-1.15.22) ====================

    async def delegate_task(
        self,
        task: Dict[str, Any],
        required_capabilities: Optional[List[str]] = None,
        target_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delegate a task to another capable agent.

        Args:
            task: Task specification to delegate
            required_capabilities: Required capabilities for the task
            target_agent_id: Specific agent to delegate to (if None, finds capable agent)

        Returns:
            Task execution result from delegated agent

        Raises:
            ValueError: If collaboration not enabled or no capable agent found

        Example:
            ```python
            # Delegate to specific agent
            result = await agent.delegate_task(
                task={"description": "Search for AI papers"},
                target_agent_id="search_agent"
            )

            # Delegate to any capable agent
            result = await agent.delegate_task(
                task={"description": "Analyze data"},
                required_capabilities=["data_analysis", "statistics"]
            )
            ```
        """
        if not self._collaboration_enabled:
            raise ValueError("Agent collaboration is not enabled")

        # Find target agent
        if target_agent_id:
            target_agent = self._agent_registry.get(target_agent_id)
            if not target_agent:
                raise ValueError(f"Agent {target_agent_id} not found in registry")
        elif required_capabilities:
            capable_agents = await self.find_capable_agents(required_capabilities)
            if not capable_agents:
                raise ValueError(f"No capable agents found for capabilities: {required_capabilities}")
            target_agent = capable_agents[0]  # Use first capable agent
        else:
            raise ValueError("Either target_agent_id or required_capabilities must be provided")

        logger.info(f"Agent {self.agent_id} delegating task to {target_agent.agent_id}")

        # Delegate task
        try:
            result = await target_agent.execute_task(task, context={"delegated_by": self.agent_id})
            logger.info(f"Task delegation successful: {self.agent_id} -> {target_agent.agent_id}")
            return result
        except Exception as e:
            logger.error(f"Task delegation failed: {e}")
            raise

    async def find_capable_agents(self, required_capabilities: List[str]) -> List[Any]:
        """
        Find agents with required capabilities.

        Args:
            required_capabilities: List of required capability names

        Returns:
            List of agents that have all required capabilities

        Example:
            ```python
            agents = await agent.find_capable_agents(["search", "summarize"])
            for capable_agent in agents:
                print(f"Found: {capable_agent.name}")
            ```
        """
        if not self._collaboration_enabled:
            return []

        capable_agents = []
        for agent_id, agent in self._agent_registry.items():
            # Skip self
            if agent_id == self.agent_id:
                continue

            # Check if agent has all required capabilities
            agent_capabilities = getattr(agent, "capabilities", [])
            if all(cap in agent_capabilities for cap in required_capabilities):
                capable_agents.append(agent)

        logger.debug(f"Found {len(capable_agents)} capable agents for {required_capabilities}")
        return capable_agents

    async def request_peer_review(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any],
        reviewer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request peer review of a task result.

        Args:
            task: Original task specification
            result: Task execution result to review
            reviewer_id: Specific reviewer agent ID (if None, selects automatically)

        Returns:
            Review result with 'approved' (bool), 'feedback' (str), 'reviewer_id' (str)

        Example:
            ```python
            result = await agent.execute_task(task, context)
            review = await agent.request_peer_review(task, result)
            if review['approved']:
                print(f"Approved: {review['feedback']}")
            else:
                print(f"Needs revision: {review['feedback']}")
            ```
        """
        if not self._collaboration_enabled:
            raise ValueError("Agent collaboration is not enabled")

        # Find reviewer
        if reviewer_id:
            reviewer = self._agent_registry.get(reviewer_id)
            if not reviewer:
                raise ValueError(f"Reviewer {reviewer_id} not found in registry")
        else:
            # Select first available agent (excluding self)
            available_reviewers = [agent for agent_id, agent in self._agent_registry.items() if agent_id != self.agent_id]
            if not available_reviewers:
                raise ValueError("No reviewers available")
            reviewer = available_reviewers[0]

        logger.info(f"Agent {self.agent_id} requesting review from {reviewer.agent_id}")

        # Request review
        try:
            if hasattr(reviewer, "review_result"):
                review = await reviewer.review_result(task, result)
            else:
                # Fallback: use execute_task with review prompt
                task_desc = task.get("description", "")
                task_result = result.get("output", "")
                review_task = {
                    "description": (f"Review this task result:\nTask: {task_desc}\nResult: {task_result}"),
                    "task_id": f"review_{task.get('task_id', 'unknown')}",
                }
                review_result = await reviewer.execute_task(review_task, context={})
                review = {
                    "approved": True,  # Assume approved if no explicit review method
                    "feedback": review_result.get("output", ""),
                    "reviewer_id": reviewer.agent_id,
                }

            logger.info(f"Review received from {reviewer.agent_id}")
            return review
        except Exception as e:
            logger.error(f"Peer review failed: {e}")
            raise

    async def collaborate_on_task(
        self,
        task: Dict[str, Any],
        collaborator_ids: List[str],
        strategy: str = "parallel",
    ) -> Dict[str, Any]:
        """
        Collaborate with other agents on a task.

        Args:
            task: Task specification
            collaborator_ids: List of agent IDs to collaborate with
            strategy: Collaboration strategy - 'parallel', 'sequential', or 'consensus'

        Returns:
            Aggregated result based on strategy

        Strategies:
            - parallel: All agents work simultaneously, results aggregated
            - sequential: Agents work in order, each building on previous results
            - consensus: All agents work independently, best result selected by voting

        Example:
            ```python
            # Parallel collaboration
            result = await agent.collaborate_on_task(
                task={"description": "Analyze market trends"},
                collaborator_ids=["analyst1", "analyst2", "analyst3"],
                strategy="parallel"
            )

            # Sequential collaboration (pipeline)
            result = await agent.collaborate_on_task(
                task={"description": "Research and summarize"},
                collaborator_ids=["researcher", "summarizer"],
                strategy="sequential"
            )

            # Consensus collaboration
            result = await agent.collaborate_on_task(
                task={"description": "Make recommendation"},
                collaborator_ids=["expert1", "expert2", "expert3"],
                strategy="consensus"
            )
            ```
        """
        if not self._collaboration_enabled:
            raise ValueError("Agent collaboration is not enabled")

        # Get collaborator agents
        collaborators = []
        for agent_id in collaborator_ids:
            agent = self._agent_registry.get(agent_id)
            if not agent:
                logger.warning(f"Collaborator {agent_id} not found, skipping")
                continue
            collaborators.append(agent)

        if not collaborators:
            raise ValueError("No valid collaborators found")

        logger.info(f"Agent {self.agent_id} collaborating with {len(collaborators)} agents " f"using {strategy} strategy")

        # Execute based on strategy
        if strategy == "parallel":
            return await self._collaborate_parallel(task, collaborators)
        elif strategy == "sequential":
            return await self._collaborate_sequential(task, collaborators)
        elif strategy == "consensus":
            return await self._collaborate_consensus(task, collaborators)
        else:
            raise ValueError(f"Unknown collaboration strategy: {strategy}")

    async def _collaborate_parallel(self, task: Dict[str, Any], collaborators: List[Any]) -> Dict[str, Any]:
        """
        Parallel collaboration: all agents work simultaneously.

        Args:
            task: Task specification
            collaborators: List of collaborator agents

        Returns:
            Aggregated result
        """
        # Execute task on all agents in parallel
        tasks = [agent.execute_task(task, context={"collaboration": "parallel"}) for agent in collaborators]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        return await self._aggregate_results(task, results, collaborators)

    async def _collaborate_sequential(self, task: Dict[str, Any], collaborators: List[Any]) -> Dict[str, Any]:
        """
        Sequential collaboration: agents work in order, building on previous results.

        Args:
            task: Task specification
            collaborators: List of collaborator agents (in execution order)

        Returns:
            Final result from last agent
        """
        current_task = task.copy()
        results = []

        for i, agent in enumerate(collaborators):
            logger.debug(f"Sequential step {i + 1}/{len(collaborators)}: {agent.agent_id}")

            # Execute task
            result = await agent.execute_task(current_task, context={"collaboration": "sequential", "step": i + 1})
            results.append(result)

            # Update task for next agent with previous result
            if i < len(collaborators) - 1:
                current_task = {
                    "description": f"{task.get('description')}\n\nPrevious result: {result.get('output')}",
                    "task_id": f"{task.get('task_id', 'unknown')}_step_{i + 2}",
                }

        # Return final result
        return {
            "success": True,
            "output": results[-1].get("output") if results else "",
            "collaboration_strategy": "sequential",
            "steps": len(results),
            "all_results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _collaborate_consensus(self, task: Dict[str, Any], collaborators: List[Any]) -> Dict[str, Any]:
        """
        Consensus collaboration: all agents work independently, best result selected.

        Args:
            task: Task specification
            collaborators: List of collaborator agents

        Returns:
            Best result selected by consensus
        """
        # Execute task on all agents in parallel
        tasks = [agent.execute_task(task, context={"collaboration": "consensus"}) for agent in collaborators]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Select best result by consensus
        return await self._select_consensus_result(task, results, collaborators)

    async def _aggregate_results(self, task: Dict[str, Any], results: List[Any], collaborators: List[Any]) -> Dict[str, Any]:
        """
        Aggregate results from parallel collaboration.

        Args:
            task: Original task
            results: List of results from collaborators
            collaborators: List of collaborator agents

        Returns:
            Aggregated result
        """
        successful_results = []
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({"agent": collaborators[i].agent_id, "error": str(result)})
            else:
                successful_results.append({"agent": collaborators[i].agent_id, "result": result})

        # Combine outputs
        combined_output = "\n\n".join([f"[{r['agent']}]: {r['result'].get('output', '')}" for r in successful_results])

        return {
            "success": len(successful_results) > 0,
            "output": combined_output,
            "collaboration_strategy": "parallel",
            "successful_agents": len(successful_results),
            "failed_agents": len(errors),
            "results": successful_results,
            "errors": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _select_consensus_result(self, task: Dict[str, Any], results: List[Any], collaborators: List[Any]) -> Dict[str, Any]:
        """
        Select best result by consensus voting.

        Args:
            task: Original task
            results: List of results from collaborators
            collaborators: List of collaborator agents

        Returns:
            Best result selected by consensus
        """
        successful_results = []

        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                successful_results.append({"agent": collaborators[i].agent_id, "result": result, "votes": 0})

        if not successful_results:
            return {
                "success": False,
                "output": "All collaborators failed",
                "collaboration_strategy": "consensus",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Simple voting: each agent votes for best result (excluding their own)
        # In a real implementation, this could use LLM to evaluate quality
        for voter_idx, voter_result in enumerate(successful_results):
            # For now, use simple heuristic: longest output is "best"
            # In production, use LLM-based evaluation
            best_idx = max(
                range(len(successful_results)),
                key=lambda i: (len(successful_results[i]["result"].get("output", "")) if i != voter_idx else 0),
            )
            successful_results[best_idx]["votes"] += 1

        # Select result with most votes
        best_result = max(successful_results, key=lambda r: r["votes"])

        return {
            "success": True,
            "output": best_result["result"].get("output", ""),
            "collaboration_strategy": "consensus",
            "selected_agent": best_result["agent"],
            "votes": best_result["votes"],
            "total_agents": len(successful_results),
            "all_results": successful_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ==================== Smart Context Management (Phase 8 - Tasks 1.16.1-1.16.3) ====================

    async def get_relevant_context(
        self,
        query: str,
        context_items: List[Dict[str, Any]],
        max_items: Optional[int] = None,
        min_relevance_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context items using semantic search and relevance scoring.

        This method filters and ranks context items based on their relevance to
        the query, helping agents stay within token limits while maintaining
        the most important context.

        Args:
            query: Query or task description to match against
            context_items: List of context items (dicts with 'content' field)
            max_items: Maximum number of items to return (None = no limit)
            min_relevance_score: Minimum relevance score (0.0-1.0)

        Returns:
            List of relevant context items, sorted by relevance (highest first)

        Example:
            ```python
            context_items = [
                {"content": "User prefers concise answers", "type": "preference"},
                {"content": "Previous task: data analysis", "type": "history"},
                {"content": "System configuration: prod", "type": "config"},
            ]

            relevant = await agent.get_relevant_context(
                query="Analyze sales data",
                context_items=context_items,
                max_items=2,
                min_relevance_score=0.6
            )
            # Returns top 2 most relevant items with score >= 0.6
            ```
        """
        if not context_items:
            return []

        # Score all items
        scored_items = []
        for item in context_items:
            score = await self.score_context_relevance(query, item)
            if score >= min_relevance_score:
                scored_items.append({**item, "_relevance_score": score})

        # Sort by relevance (highest first)
        scored_items.sort(key=lambda x: x["_relevance_score"], reverse=True)

        # Limit number of items
        if max_items is not None:
            scored_items = scored_items[:max_items]

        logger.debug(f"Selected {len(scored_items)}/{len(context_items)} relevant context items " f"(min_score={min_relevance_score})")

        return scored_items

    async def score_context_relevance(self, query: str, context_item: Dict[str, Any]) -> float:
        """
        Score the relevance of a context item to a query.

        Uses multiple signals to determine relevance:
        - Keyword overlap (basic)
        - Semantic similarity (if LLM client with embeddings available)
        - Recency (if timestamp available)
        - Type priority (if type specified)

        Args:
            query: Query or task description
            context_item: Context item to score (dict with 'content' field)

        Returns:
            Relevance score between 0.0 (not relevant) and 1.0 (highly relevant)

        Example:
            ```python
            score = await agent.score_context_relevance(
                query="Analyze sales data",
                context_item={"content": "Previous analysis results", "type": "history"}
            )
            print(f"Relevance: {score:.2f}")
            ```
        """
        content = context_item.get("content", "")
        if not content:
            return 0.0

        # Convert to lowercase for comparison
        query_lower = query.lower()
        content_lower = content.lower()

        # 1. Keyword overlap score (0.0-0.5)
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        if not query_words:
            keyword_score = 0.0
        else:
            overlap = len(query_words & content_words)
            keyword_score = min(0.5, (overlap / len(query_words)) * 0.5)

        # 2. Semantic similarity score (0.0-0.3)
        # If LLM client with embeddings is available, use it
        semantic_score = 0.0
        if self._llm_client and hasattr(self._llm_client, "get_embeddings"):
            try:
                embeddings = await self._llm_client.get_embeddings([query, content])
                if len(embeddings) == 2:
                    # Calculate cosine similarity
                    import math

                    vec1, vec2 = embeddings[0], embeddings[1]
                    dot_product = sum(a * b for a, b in zip(vec1, vec2))
                    mag1 = math.sqrt(sum(a * a for a in vec1))
                    mag2 = math.sqrt(sum(b * b for b in vec2))
                    if mag1 > 0 and mag2 > 0:
                        similarity = dot_product / (mag1 * mag2)
                        semantic_score = max(0.0, similarity) * 0.3
            except Exception as e:
                logger.debug(f"Semantic similarity calculation failed: {e}")

        # 3. Recency score (0.0-0.1)
        recency_score = 0.0
        if "timestamp" in context_item:
            try:
                from datetime import datetime

                timestamp = context_item["timestamp"]
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                age_seconds = (datetime.utcnow() - timestamp).total_seconds()
                # Decay over 24 hours
                recency_score = max(0.0, 0.1 * (1.0 - min(1.0, age_seconds / 86400)))
            except Exception as e:
                logger.debug(f"Recency calculation failed: {e}")

        # 4. Type priority score (0.0-0.1)
        type_score = 0.0
        item_type = context_item.get("type", "")
        priority_types = {"preference": 0.1, "constraint": 0.1, "requirement": 0.09}
        type_score = priority_types.get(item_type, 0.05)

        # Combine scores
        total_score = keyword_score + semantic_score + recency_score + type_score

        return min(1.0, total_score)

    async def prune_context(
        self,
        context_items: List[Dict[str, Any]],
        max_tokens: int,
        query: Optional[str] = None,
        preserve_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Prune context items to fit within token limit.

        Uses relevance scoring to keep the most important context while
        staying within token limits. Optionally preserves certain types
        of context regardless of relevance.

        Args:
            context_items: List of context items to prune
            max_tokens: Maximum total tokens allowed
            query: Optional query for relevance scoring
            preserve_types: Optional list of types to always preserve

        Returns:
            Pruned list of context items that fit within token limit

        Example:
            ```python
            pruned = await agent.prune_context(
                context_items=all_context,
                max_tokens=2000,
                query="Analyze data",
                preserve_types=["constraint", "requirement"]
            )
            print(f"Pruned from {len(all_context)} to {len(pruned)} items")
            ```
        """
        if not context_items:
            return []

        preserve_types = preserve_types or []

        # Separate preserved and regular items
        preserved_items = []
        regular_items = []

        for item in context_items:
            if item.get("type") in preserve_types:
                preserved_items.append(item)
            else:
                regular_items.append(item)

        # Score regular items if query provided
        if query and regular_items:
            scored_items = []
            for item in regular_items:
                score = await self.score_context_relevance(query, item)
                scored_items.append({**item, "_relevance_score": score})
            # Sort by relevance
            scored_items.sort(key=lambda x: x["_relevance_score"], reverse=True)
            regular_items = scored_items

        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        def estimate_tokens(item: Dict[str, Any]) -> int:
            content = str(item.get("content", ""))
            return len(content) // 4

        # Add preserved items first
        result = []
        current_tokens = 0

        for item in preserved_items:
            item_tokens = estimate_tokens(item)
            if current_tokens + item_tokens <= max_tokens:
                result.append(item)
                current_tokens += item_tokens
            else:
                logger.warning(f"Preserved item exceeds token limit, skipping: {item.get('type')}")

        # Add regular items until token limit
        for item in regular_items:
            item_tokens = estimate_tokens(item)
            if current_tokens + item_tokens <= max_tokens:
                result.append(item)
                current_tokens += item_tokens
            else:
                break

        logger.info(f"Pruned context from {len(context_items)} to {len(result)} items " f"({current_tokens}/{max_tokens} tokens)")

        return result

    # ==================== Agent Learning (Phase 8 - Tasks 1.16.4-1.16.10) ====================

    async def record_experience(
        self,
        task: Dict[str, Any],
        result: Dict[str, Any],
        approach: str,
        tools_used: Optional[List[str]] = None,
    ) -> None:
        """
        Record an experience for learning and adaptation.

        Args:
            task: Task specification
            result: Task execution result
            approach: Approach/strategy used
            tools_used: List of tools used (if any)

        Example:
            ```python
            await agent.record_experience(
                task={"description": "Analyze data", "type": "analysis"},
                result={"success": True, "execution_time": 5.2},
                approach="statistical_analysis",
                tools_used=["pandas", "numpy"]
            )
            ```
        """
        if not self._learning_enabled:
            return

        from .models import Experience

        # Classify task
        task_type = await self._classify_task(task)

        # Create experience record
        experience = Experience(  # type: ignore[call-arg]
            agent_id=self.agent_id,
            task_type=task_type,
            task_description=task.get("description", ""),
            task_complexity=task.get("complexity"),
            approach=approach,
            tools_used=tools_used or [],
            execution_time=result.get("execution_time", 0.0),
            success=result.get("success", False),
            quality_score=result.get("quality_score"),
            error_type=result.get("error_type"),
            error_message=result.get("error"),
            context_size=result.get("context_size"),
            iterations=result.get("iterations"),
            metadata={"task_id": task.get("task_id")},
        )

        # Add to experiences
        self._experiences.append(experience)

        # Limit stored experiences
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences :]

        logger.debug(f"Recorded experience: {task_type} - " f"{'success' if experience.success else 'failure'} " f"({experience.execution_time:.2f}s)")

    async def get_recommended_approach(self, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get recommended approach based on past experiences.

        Analyzes similar past experiences to recommend the best approach
        for the current task.

        Args:
            task: Task specification

        Returns:
            Recommended approach dict with 'approach', 'confidence', 'reasoning'
            or None if no relevant experiences

        Example:
            ```python
            recommendation = await agent.get_recommended_approach(
                task={"description": "Analyze sales data", "type": "analysis"}
            )
            if recommendation:
                print(f"Recommended: {recommendation['approach']}")
                print(f"Confidence: {recommendation['confidence']:.2f}")
                print(f"Reasoning: {recommendation['reasoning']}")
            ```
        """
        if not self._learning_enabled or not self._experiences:
            return None

        # Classify current task
        task_type = await self._classify_task(task)

        # Find similar experiences
        similar_experiences = [exp for exp in self._experiences if exp.task_type == task_type]

        if not similar_experiences:
            return None

        # Analyze successful experiences
        successful = [exp for exp in similar_experiences if exp.success]
        if not successful:
            return None

        # Count approaches
        approach_stats: Dict[str, Dict[str, Any]] = {}
        for exp in successful:
            if exp.approach not in approach_stats:
                approach_stats[exp.approach] = {
                    "count": 0,
                    "total_time": 0.0,
                    "avg_quality": 0.0,
                    "quality_count": 0,
                }
            stats = approach_stats[exp.approach]
            stats["count"] += 1
            stats["total_time"] += exp.execution_time
            if exp.quality_score is not None:
                stats["avg_quality"] += exp.quality_score
                stats["quality_count"] += 1

        # Calculate averages and scores
        for approach, stats in approach_stats.items():
            stats["avg_time"] = stats["total_time"] / stats["count"]
            if stats["quality_count"] > 0:
                stats["avg_quality"] = stats["avg_quality"] / stats["quality_count"]
            else:
                stats["avg_quality"] = 0.5  # Default

        # Select best approach (balance success rate, quality, speed)
        best_approach = max(
            approach_stats.items(),
            key=lambda x: (
                x[1]["count"] / len(similar_experiences),  # Success rate
                x[1]["avg_quality"],  # Quality
                -x[1]["avg_time"],  # Speed (negative for faster is better)
            ),
        )

        approach_name, stats = best_approach
        confidence = min(1.0, stats["count"] / max(5, len(similar_experiences)))

        return {
            "approach": approach_name,
            "confidence": confidence,
            "reasoning": (
                f"Based on {stats['count']} successful experiences with {task_type} tasks. " f"Average execution time: {stats['avg_time']:.2f}s, " f"Average quality: {stats['avg_quality']:.2f}"
            ),
            "stats": stats,
        }

    async def get_learning_insights(self) -> Dict[str, Any]:
        """
        Get learning insights and analytics.

        Provides analytics about agent learning including success rates,
        common patterns, and areas for improvement.

        Returns:
            Dict with learning insights and statistics

        Example:
            ```python
            insights = await agent.get_learning_insights()
            print(f"Total experiences: {insights['total_experiences']}")
            print(f"Success rate: {insights['overall_success_rate']:.2%}")
            print(f"Most common task: {insights['most_common_task_type']}")
            ```
        """
        if not self._learning_enabled or not self._experiences:
            return {
                "total_experiences": 0,
                "learning_enabled": self._learning_enabled,
            }

        total = len(self._experiences)
        successful = sum(1 for exp in self._experiences if exp.success)
        failed = total - successful

        # Task type distribution
        task_types: Dict[str, int] = {}
        for exp in self._experiences:
            task_types[exp.task_type] = task_types.get(exp.task_type, 0) + 1

        # Approach effectiveness
        approach_success: Dict[str, Dict[str, int]] = {}
        for exp in self._experiences:
            if exp.approach not in approach_success:
                approach_success[exp.approach] = {"success": 0, "failure": 0}
            if exp.success:
                approach_success[exp.approach]["success"] += 1
            else:
                approach_success[exp.approach]["failure"] += 1

        # Calculate success rates
        approach_rates = {approach: stats["success"] / (stats["success"] + stats["failure"]) for approach, stats in approach_success.items()}

        # Error patterns
        error_types: Dict[str, int] = {}
        for exp in self._experiences:
            if not exp.success and exp.error_type:
                error_types[exp.error_type] = error_types.get(exp.error_type, 0) + 1

        return {
            "total_experiences": total,
            "successful_experiences": successful,
            "failed_experiences": failed,
            "overall_success_rate": successful / total if total > 0 else 0.0,
            "task_type_distribution": task_types,
            "most_common_task_type": (max(task_types.items(), key=lambda x: x[1])[0] if task_types else None),
            "approach_effectiveness": approach_rates,
            "best_approach": (max(approach_rates.items(), key=lambda x: x[1])[0] if approach_rates else None),
            "error_patterns": error_types,
            "most_common_error": (max(error_types.items(), key=lambda x: x[1])[0] if error_types else None),
            "learning_enabled": self._learning_enabled,
        }

    async def adapt_strategy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt strategy based on learning insights.

        Analyzes past experiences to suggest strategy adaptations for
        the current task.

        Args:
            task: Task specification

        Returns:
            Dict with strategy adaptations and recommendations

        Example:
            ```python
            adaptations = await agent.adapt_strategy(
                task={"description": "Complex analysis", "type": "analysis"}
            )
            print(f"Recommended approach: {adaptations['recommended_approach']}")
            print(f"Suggested tools: {adaptations['suggested_tools']}")
            ```
        """
        if not self._learning_enabled:
            return {"adapted": False, "reason": "Learning not enabled"}

        # Get recommended approach
        recommendation = await self.get_recommended_approach(task)

        if not recommendation:
            return {
                "adapted": False,
                "reason": "No relevant experiences found",
            }

        # Classify task
        task_type = await self._classify_task(task)

        # Find similar successful experiences
        similar_successful = [exp for exp in self._experiences if exp.task_type == task_type and exp.success]

        # Analyze tool usage patterns
        tool_usage: Dict[str, int] = {}
        for exp in similar_successful:
            for tool in exp.tools_used:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1

        # Get most commonly used tools
        suggested_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]  # Top 5 tools

        return {
            "adapted": True,
            "recommended_approach": recommendation["approach"],
            "confidence": recommendation["confidence"],
            "reasoning": recommendation["reasoning"],
            "suggested_tools": [tool for tool, _ in suggested_tools],
            "tool_usage_stats": dict(suggested_tools),
            "based_on_experiences": len(similar_successful),
        }

    async def _classify_task(self, task: Dict[str, Any]) -> str:
        """
        Classify task into a type/category.

        Uses simple heuristics to classify tasks. Can be overridden by
        subclasses for more sophisticated classification.

        Args:
            task: Task specification

        Returns:
            Task type string

        Example:
            ```python
            task_type = await agent._classify_task(
                {"description": "Analyze sales data"}
            )
            # Returns: "analysis"
            ```
        """
        # Check explicit type
        if "type" in task:
            return task["type"]

        # Simple keyword-based classification
        description = task.get("description", "").lower()

        if any(word in description for word in ["analyze", "analysis", "examine"]):
            return "analysis"
        elif any(word in description for word in ["search", "find", "lookup"]):
            return "search"
        elif any(word in description for word in ["create", "generate", "write"]):
            return "generation"
        elif any(word in description for word in ["summarize", "summary"]):
            return "summarization"
        elif any(word in description for word in ["calculate", "compute"]):
            return "calculation"
        elif any(word in description for word in ["translate", "convert"]):
            return "translation"
        else:
            return "general"

    # ==================== Resource Management (Phase 8 - Tasks 1.16.11-1.16.17) ====================

    async def check_resource_availability(self) -> Dict[str, Any]:
        """
        Check if resources are available for task execution.

        Checks against configured resource limits including:
        - Concurrent task limits
        - Token rate limits
        - Tool call rate limits

        Returns:
            Dict with 'available' (bool) and details about resource status

        Example:
            ```python
            status = await agent.check_resource_availability()
            if status['available']:
                await agent.execute_task(task, context)
            else:
                print(f"Resources unavailable: {status['reason']}")
            ```
        """
        if not self._resource_limits.enforce_limits:
            return {"available": True, "reason": "Limits not enforced"}

        # Check concurrent task limit
        if len(self._active_tasks) >= self._resource_limits.max_concurrent_tasks:
            return {
                "available": False,
                "reason": "Concurrent task limit reached",
                "active_tasks": len(self._active_tasks),
                "max_tasks": self._resource_limits.max_concurrent_tasks,
            }

        # Check token rate limits
        token_check = await self._check_token_rate_limit()
        if not token_check["available"]:
            return token_check

        # Check tool call rate limits
        tool_check = await self._check_tool_call_rate_limit()
        if not tool_check["available"]:
            return tool_check

        return {
            "available": True,
            "active_tasks": len(self._active_tasks),
            "max_tasks": self._resource_limits.max_concurrent_tasks,
        }

    async def wait_for_resources(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for resources to become available.

        Args:
            timeout: Maximum time to wait in seconds (uses resource_wait_timeout_seconds if None)

        Returns:
            True if resources became available, False if timeout

        Example:
            ```python
            if await agent.wait_for_resources(timeout=30):
                await agent.execute_task(task, context)
            else:
                print("Timeout waiting for resources")
            ```
        """
        if timeout is None:
            timeout = self._resource_limits.resource_wait_timeout_seconds

        start_time = time.time()
        check_interval = 0.5  # Check every 500ms

        while time.time() - start_time < timeout:
            status = await self.check_resource_availability()
            if status["available"]:
                return True

            # Wait before next check
            await asyncio.sleep(check_interval)

        logger.warning(f"Timeout waiting for resources after {timeout}s")
        return False

    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage statistics.

        Returns:
            Dict with resource usage information

        Example:
            ```python
            usage = await agent.get_resource_usage()
            print(f"Active tasks: {usage['active_tasks']}")
            print(f"Tokens/min: {usage['tokens_per_minute']}")
            print(f"Tool calls/min: {usage['tool_calls_per_minute']}")
            ```
        """
        current_time = time.time()

        # Calculate token usage rates
        tokens_last_minute = sum(count for ts, count in self._token_usage_window if current_time - ts < 60)
        tokens_last_hour = sum(count for ts, count in self._token_usage_window if current_time - ts < 3600)

        # Calculate tool call rates
        tool_calls_last_minute = sum(1 for ts in self._tool_call_window if current_time - ts < 60)
        tool_calls_last_hour = sum(1 for ts in self._tool_call_window if current_time - ts < 3600)

        return {
            "active_tasks": len(self._active_tasks),
            "max_concurrent_tasks": self._resource_limits.max_concurrent_tasks,
            "task_utilization": len(self._active_tasks) / self._resource_limits.max_concurrent_tasks,
            "tokens_per_minute": tokens_last_minute,
            "tokens_per_hour": tokens_last_hour,
            "max_tokens_per_minute": self._resource_limits.max_tokens_per_minute,
            "max_tokens_per_hour": self._resource_limits.max_tokens_per_hour,
            "tool_calls_per_minute": tool_calls_last_minute,
            "tool_calls_per_hour": tool_calls_last_hour,
            "max_tool_calls_per_minute": self._resource_limits.max_tool_calls_per_minute,
            "max_tool_calls_per_hour": self._resource_limits.max_tool_calls_per_hour,
            "limits_enforced": self._resource_limits.enforce_limits,
        }

    async def _check_token_rate_limit(self) -> Dict[str, Any]:
        """
        Check token rate limits.

        Returns:
            Dict with 'available' (bool) and limit details
        """
        if not self._resource_limits.enforce_limits:
            return {"available": True}

        current_time = time.time()

        # Clean old entries (older than 1 hour)
        self._token_usage_window = [(ts, count) for ts, count in self._token_usage_window if current_time - ts < 3600]

        # Check per-minute limit
        if self._resource_limits.max_tokens_per_minute is not None:
            tokens_last_minute = sum(count for ts, count in self._token_usage_window if current_time - ts < 60)
            if tokens_last_minute >= self._resource_limits.max_tokens_per_minute:
                return {
                    "available": False,
                    "reason": "Token rate limit (per minute) reached",
                    "tokens_used": tokens_last_minute,
                    "limit": self._resource_limits.max_tokens_per_minute,
                    "window": "minute",
                }

        # Check per-hour limit
        if self._resource_limits.max_tokens_per_hour is not None:
            tokens_last_hour = sum(count for ts, count in self._token_usage_window)
            if tokens_last_hour >= self._resource_limits.max_tokens_per_hour:
                return {
                    "available": False,
                    "reason": "Token rate limit (per hour) reached",
                    "tokens_used": tokens_last_hour,
                    "limit": self._resource_limits.max_tokens_per_hour,
                    "window": "hour",
                }

        return {"available": True}

    async def _check_tool_call_rate_limit(self) -> Dict[str, Any]:
        """
        Check tool call rate limits.

        Returns:
            Dict with 'available' (bool) and limit details
        """
        if not self._resource_limits.enforce_limits:
            return {"available": True}

        current_time = time.time()

        # Clean old entries (older than 1 hour)
        self._tool_call_window = [ts for ts in self._tool_call_window if current_time - ts < 3600]

        # Check per-minute limit
        if self._resource_limits.max_tool_calls_per_minute is not None:
            calls_last_minute = sum(1 for ts in self._tool_call_window if current_time - ts < 60)
            if calls_last_minute >= self._resource_limits.max_tool_calls_per_minute:
                return {
                    "available": False,
                    "reason": "Tool call rate limit (per minute) reached",
                    "calls_made": calls_last_minute,
                    "limit": self._resource_limits.max_tool_calls_per_minute,
                    "window": "minute",
                }

        # Check per-hour limit
        if self._resource_limits.max_tool_calls_per_hour is not None:
            calls_last_hour = len(self._tool_call_window)
            if calls_last_hour >= self._resource_limits.max_tool_calls_per_hour:
                return {
                    "available": False,
                    "reason": "Tool call rate limit (per hour) reached",
                    "calls_made": calls_last_hour,
                    "limit": self._resource_limits.max_tool_calls_per_hour,
                    "window": "hour",
                }

        return {"available": True}

    # ==================== Error Recovery (Phase 8 - Tasks 1.16.18-1.16.22) ====================

    async def execute_with_recovery(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute task with advanced error recovery strategies.

        Tries multiple recovery strategies in sequence until one succeeds:
        1. Retry with exponential backoff
        2. Simplify task and retry
        3. Use fallback approach
        4. Delegate to another agent

        Args:
            task: Task specification
            context: Execution context
            strategies: List of strategy names to try (uses default chain if None)

        Returns:
            Task execution result

        Raises:
            TaskExecutionError: If all recovery strategies fail

        Example:
            ```python
            result = await agent.execute_with_recovery(
                task={"description": "Complex analysis"},
                context={},
                strategies=["retry", "simplify", "delegate"]
            )
            ```
        """
        from .models import RecoveryStrategy
        from .exceptions import TaskExecutionError

        # Default strategy chain
        if strategies is None:
            strategies = [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.SIMPLIFY,
                RecoveryStrategy.FALLBACK,
                RecoveryStrategy.DELEGATE,
            ]

        errors = []

        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery strategy: {strategy}")

                if strategy == RecoveryStrategy.RETRY:
                    # Retry with exponential backoff (using existing retry mechanism)
                    result = await self._execute_with_retry(self.execute_task, task, context)
                    logger.info(f"Recovery successful with strategy: {strategy}")
                    return result

                elif strategy == RecoveryStrategy.SIMPLIFY:
                    # Simplify task and retry
                    simplified_task = await self._simplify_task(task)
                    result = await self.execute_task(simplified_task, context)
                    logger.info(f"Recovery successful with strategy: {strategy}")
                    return result

                elif strategy == RecoveryStrategy.FALLBACK:
                    # Use fallback approach
                    result = await self._execute_with_fallback(task, context)
                    logger.info(f"Recovery successful with strategy: {strategy}")
                    return result

                elif strategy == RecoveryStrategy.DELEGATE:
                    # Delegate to another agent
                    if self._collaboration_enabled:
                        result = await self._delegate_to_capable_agent(task, context)
                        logger.info(f"Recovery successful with strategy: {strategy}")
                        return result
                    else:
                        logger.warning("Delegation not available (collaboration disabled)")
                        continue

            except Exception as e:
                logger.warning(f"Recovery strategy {strategy} failed: {e}")
                errors.append({"strategy": strategy, "error": str(e)})
                continue

        # All strategies failed
        error_summary = "; ".join([f"{e['strategy']}: {e['error']}" for e in errors])
        raise TaskExecutionError(
            f"All recovery strategies failed. Errors: {error_summary}",
            agent_id=self.agent_id,
            task_id=task.get("task_id"),
        )

    async def _simplify_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplify a task to make it easier to execute.

        Strategies:
        - Reduce complexity by breaking into smaller parts
        - Remove optional requirements
        - Use simpler language

        Args:
            task: Original task specification

        Returns:
            Simplified task specification

        Example:
            ```python
            simplified = await agent._simplify_task(
                {"description": "Perform comprehensive analysis with visualizations"}
            )
            # Returns: {"description": "Perform basic analysis"}
            ```
        """
        description = task.get("description", "")

        # Simple heuristics for simplification
        simplified_description = description

        # Remove complexity keywords
        complexity_words = [
            "comprehensive",
            "detailed",
            "thorough",
            "extensive",
            "in-depth",
            "complete",
            "full",
            "exhaustive",
        ]
        for word in complexity_words:
            simplified_description = simplified_description.replace(word, "basic")

        # Remove optional requirements
        optional_phrases = [
            "with visualizations",
            "with charts",
            "with graphs",
            "with examples",
            "with details",
            "with explanations",
        ]
        for phrase in optional_phrases:
            simplified_description = simplified_description.replace(phrase, "")

        # Clean up extra spaces
        simplified_description = " ".join(simplified_description.split())

        simplified_task = task.copy()
        simplified_task["description"] = simplified_description
        simplified_task["simplified"] = True
        simplified_task["original_description"] = description

        logger.debug(f"Simplified task: '{description}' -> '{simplified_description}'")

        return simplified_task

    async def _execute_with_fallback(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task with fallback approach.

        Uses a simpler, more reliable approach when the primary approach fails.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Task execution result

        Example:
            ```python
            result = await agent._execute_with_fallback(task, context)
            ```
        """
        # Create fallback task with reduced requirements
        fallback_task = task.copy()
        fallback_task["fallback_mode"] = True

        # Reduce max_tokens if specified
        if "max_tokens" in context:
            context = context.copy()
            context["max_tokens"] = min(context["max_tokens"], 1000)

        # Reduce temperature for more deterministic output
        if "temperature" in context:
            context = context.copy()
            context["temperature"] = 0.3

        logger.info("Executing with fallback approach (reduced requirements)")

        # Execute with modified parameters
        result = await self.execute_task(fallback_task, context)
        result["fallback_used"] = True

        return result

    async def _delegate_to_capable_agent(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegate task to a capable agent as recovery strategy.

        Finds an agent capable of handling the task and delegates to it.

        Args:
            task: Task specification
            context: Execution context

        Returns:
            Task execution result from delegated agent

        Raises:
            ValueError: If no capable agent found

        Example:
            ```python
            result = await agent._delegate_to_capable_agent(task, context)
            ```
        """
        if not self._collaboration_enabled:
            raise ValueError("Collaboration not enabled, cannot delegate")

        # Try to classify task and find capable agents
        task_type = await self._classify_task(task)

        # Look for agents with matching capabilities
        capable_agents = []
        for agent_id, agent in self._agent_registry.items():
            if agent_id == self.agent_id:
                continue  # Skip self

            # Check if agent has relevant capabilities
            agent_capabilities = getattr(agent, "capabilities", [])
            if task_type in agent_capabilities or "general" in agent_capabilities:
                capable_agents.append(agent)

        if not capable_agents:
            # Try any available agent as last resort
            capable_agents = [agent for agent_id, agent in self._agent_registry.items() if agent_id != self.agent_id]

        if not capable_agents:
            raise ValueError("No capable agents available for delegation")

        # Delegate to first capable agent
        target_agent = capable_agents[0]
        logger.info(f"Delegating task to {target_agent.agent_id} for recovery")

        result = await target_agent.execute_task(task, context={**context, "delegated_by": self.agent_id, "recovery_delegation": True})

        result["delegated_to"] = target_agent.agent_id
        result["recovery_delegation"] = True

        return result

    def __str__(self) -> str:
        """String representation."""
        return f"Agent({self.agent_id}, {self.name}, {self.agent_type.value}, {self._state.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"BaseAIAgent(agent_id='{self.agent_id}', name='{self.name}', " f"type='{self.agent_type.value}', state='{self._state.value}')"
