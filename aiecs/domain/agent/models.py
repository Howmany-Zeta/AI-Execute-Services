"""
Agent Domain Models

Defines the core data models for the base AI agent system.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class AgentState(str, Enum):
    """Agent lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class AgentType(str, Enum):
    """Types of AI agents."""

    CONVERSATIONAL = "conversational"
    TASK_EXECUTOR = "task_executor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    CREATIVE = "creative"
    DEVELOPER = "developer"
    COORDINATOR = "coordinator"


class GoalStatus(str, Enum):
    """Status of agent goals."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class GoalPriority(str, Enum):
    """Priority levels for goals."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CapabilityLevel(str, Enum):
    """Proficiency levels for agent capabilities."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class MemoryType(str, Enum):
    """Types of agent memory."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class RecoveryStrategy(str, Enum):
    """
    Recovery strategies for error handling.

    Defines different strategies for recovering from task execution failures.
    Strategies are typically applied in sequence until one succeeds or all fail.

    **Strategy Descriptions:**
    - RETRY: Retry the same task with exponential backoff (for transient errors)
    - SIMPLIFY: Simplify the task and retry (break down complex tasks)
    - FALLBACK: Use a fallback approach or alternative method
    - DELEGATE: Delegate the task to another capable agent
    - ABORT: Abort execution and return error (terminal strategy)

    **Usage Pattern:**
    Strategies are typically chained together, trying each in sequence:
    1. RETRY - Quick retry for transient errors
    2. SIMPLIFY - Break down complex tasks
    3. FALLBACK - Use alternative approach
    4. DELEGATE - Hand off to another agent
    5. ABORT - Give up and return error

    Examples:
        # Example 1: Basic retry strategy
        from aiecs.domain.agent.models import RecoveryStrategy

        strategies = [RecoveryStrategy.RETRY]
        result = await agent.execute_with_recovery(
            task=task,
            context=context,
            strategies=strategies
        )

        # Example 2: Full recovery chain
        strategies = [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.SIMPLIFY,
            RecoveryStrategy.FALLBACK,
            RecoveryStrategy.DELEGATE
        ]
        result = await agent.execute_with_recovery(
            task=task,
            context=context,
            strategies=strategies
        )

        # Example 3: Conservative recovery (no delegation)
        strategies = [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.SIMPLIFY,
            RecoveryStrategy.FALLBACK
        ]
        result = await agent.execute_with_recovery(
            task=task,
            context=context,
            strategies=strategies
        )

        # Example 4: Quick fail (abort after retry)
        strategies = [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.ABORT
        ]
        result = await agent.execute_with_recovery(
            task=task,
            context=context,
            strategies=strategies
        )
    """

    RETRY = "retry"  # Retry with exponential backoff
    SIMPLIFY = "simplify"  # Simplify task and retry
    FALLBACK = "fallback"  # Use fallback approach
    DELEGATE = "delegate"  # Delegate to another agent
    ABORT = "abort"  # Abort execution


class RetryPolicy(BaseModel):
    """Retry policy configuration for agent operations."""

    max_retries: int = Field(default=5, ge=0, description="Maximum number of retry attempts")
    base_delay: float = Field(
        default=1.0,
        ge=0,
        description="Base delay in seconds for exponential backoff",
    )
    max_delay: float = Field(default=32.0, ge=0, description="Maximum delay cap in seconds")
    exponential_factor: float = Field(default=2.0, ge=1.0, description="Exponential factor for backoff")
    jitter_factor: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Jitter factor (±percentage) for randomization",
    )
    rate_limit_base_delay: float = Field(default=5.0, ge=0, description="Base delay for rate limit errors")
    rate_limit_max_delay: float = Field(default=120.0, ge=0, description="Maximum delay for rate limit errors")

    model_config = ConfigDict()


class AgentConfiguration(BaseModel):
    """Configuration model for agent behavior and capabilities."""

    # LLM settings
    llm_provider: Optional[str] = Field(None, description="LLM provider name (e.g., 'openai', 'vertex')")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature setting")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens for LLM responses")

    # RAG strategy selection LLM configuration
    strategy_selection_llm_provider: Optional[str] = Field(
        None,
        description="LLM provider for RAG strategy selection (supports custom providers registered via LLMClientFactory)",
    )
    strategy_selection_llm_model: Optional[str] = Field(
        None,
        description="LLM model for RAG strategy selection (lightweight model recommended)",
    )
    strategy_selection_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for strategy selection (0.0 for deterministic classification)",
    )
    strategy_selection_max_tokens: int = Field(
        default=100,
        ge=1,
        description="Maximum tokens for strategy selection response",
    )

    # Tool access
    allowed_tools: List[str] = Field(default_factory=list, description="List of tool names agent can use")
    tool_selection_strategy: str = Field(
        default="llm_based",
        description="Strategy for tool selection ('llm_based', 'rule_based')",
    )

    # Memory configuration
    memory_enabled: bool = Field(default=True, description="Whether memory is enabled")
    memory_capacity: int = Field(default=1000, ge=0, description="Maximum number of memory items")
    memory_ttl_seconds: Optional[int] = Field(None, ge=0, description="Time-to-live for short-term memory in seconds")

    # Behavior parameters
    max_iterations: int = Field(default=10, ge=1, description="Maximum iterations for ReAct loop")
    timeout_seconds: Optional[int] = Field(None, ge=0, description="Task execution timeout")
    verbose: bool = Field(default=False, description="Verbose logging")

    # Retry policy
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="Retry policy configuration")

    # Goal and context
    goal: Optional[str] = Field(None, description="Agent's primary goal")
    backstory: Optional[str] = Field(None, description="Agent's backstory/context")
    domain_knowledge: Optional[str] = Field(None, description="Domain-specific knowledge")
    reasoning_guidance: Optional[str] = Field(None, description="Guidance for reasoning approach")

    # Context compression
    context_window_limit: int = Field(default=20000, ge=0, description="Token limit for context window")
    enable_context_compression: bool = Field(default=True, description="Enable automatic context compression")

    # Knowledge retrieval configuration
    retrieval_strategy: str = Field(
        default="hybrid",
        description="Knowledge retrieval strategy: 'vector' (semantic similarity), 'graph' (graph traversal), 'hybrid' (combination), or 'auto' (automatic selection)",
    )
    enable_knowledge_caching: bool = Field(
        default=True,
        description="Enable caching for knowledge retrieval results",
    )
    cache_ttl: int = Field(
        default=300,
        ge=0,
        description="Cache time-to-live in seconds (default: 300 = 5 minutes)",
    )
    max_context_size: int = Field(
        default=50,
        ge=1,
        description="Maximum number of knowledge entities to include in context (default: 50)",
    )
    entity_extraction_provider: str = Field(
        default="llm",
        description="Entity extraction provider: 'llm' (LLM-based extraction), 'ner' (Named Entity Recognition), or custom provider name",
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration metadata")

    model_config = ConfigDict()


class AgentGoal(BaseModel):
    """Model representing an agent goal."""

    goal_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique goal identifier",
    )
    description: str = Field(..., description="Goal description")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Current goal status")
    priority: GoalPriority = Field(default=GoalPriority.MEDIUM, description="Goal priority level")
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)",
    )

    # Success criteria
    success_criteria: Optional[str] = Field(None, description="Criteria for goal achievement")
    deadline: Optional[datetime] = Field(None, description="Goal deadline")

    # Dependencies
    parent_goal_id: Optional[str] = Field(None, description="Parent goal ID if this is a sub-goal")
    depends_on: List[str] = Field(default_factory=list, description="List of goal IDs this depends on")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Goal creation timestamp")
    started_at: Optional[datetime] = Field(None, description="When goal execution started")
    achieved_at: Optional[datetime] = Field(None, description="When goal was achieved")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional goal metadata")

    model_config = ConfigDict()


class AgentCapabilityDeclaration(BaseModel):
    """Model declaring an agent capability."""

    capability_type: str = Field(
        ...,
        description="Type of capability (e.g., 'text_generation', 'code_generation')",
    )
    level: CapabilityLevel = Field(..., description="Proficiency level")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Capability constraints")
    description: Optional[str] = Field(None, description="Capability description")

    # Timestamps
    acquired_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When capability was acquired",
    )

    model_config = ConfigDict()


class AgentMetrics(BaseModel):
    """Model for tracking agent performance metrics."""

    # Task execution metrics
    total_tasks_executed: int = Field(default=0, ge=0, description="Total number of tasks executed")
    successful_tasks: int = Field(default=0, ge=0, description="Number of successful tasks")
    failed_tasks: int = Field(default=0, ge=0, description="Number of failed tasks")
    success_rate: float = Field(default=0.0, ge=0.0, le=100.0, description="Success rate percentage")

    # Execution time metrics
    average_execution_time: Optional[float] = Field(None, ge=0, description="Average task execution time in seconds")
    total_execution_time: float = Field(default=0.0, ge=0, description="Total execution time in seconds")
    min_execution_time: Optional[float] = Field(None, ge=0, description="Minimum execution time in seconds")
    max_execution_time: Optional[float] = Field(None, ge=0, description="Maximum execution time in seconds")

    # Quality metrics
    average_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average quality score (0-1)")

    # Resource usage
    total_tokens_used: int = Field(default=0, ge=0, description="Total LLM tokens used")
    total_tool_calls: int = Field(default=0, ge=0, description="Total tool calls made")
    total_api_cost: Optional[float] = Field(None, ge=0, description="Total API cost (if tracked)")

    # Retry metrics
    total_retries: int = Field(default=0, ge=0, description="Total number of retry attempts")
    retry_successes: int = Field(default=0, ge=0, description="Number of successful retries")

    # Error tracking
    error_count: int = Field(default=0, ge=0, description="Total number of errors")
    error_types: Dict[str, int] = Field(default_factory=dict, description="Count of errors by type")

    # Session-level metrics (Phase 2 enhancement)
    total_sessions: int = Field(default=0, ge=0, description="Total number of sessions created")
    active_sessions: int = Field(default=0, ge=0, description="Number of currently active sessions")
    completed_sessions: int = Field(default=0, ge=0, description="Number of completed sessions")
    failed_sessions: int = Field(default=0, ge=0, description="Number of failed sessions")
    expired_sessions: int = Field(default=0, ge=0, description="Number of expired sessions")
    total_session_requests: int = Field(default=0, ge=0, description="Total requests across all sessions")
    total_session_errors: int = Field(default=0, ge=0, description="Total errors across all sessions")
    average_session_duration: Optional[float] = Field(None, ge=0, description="Average session duration in seconds")
    average_requests_per_session: Optional[float] = Field(None, ge=0, description="Average number of requests per session")

    # Operation-level metrics (Phase 3 enhancement)
    operation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent operation timing history (limited to last 100)")
    operation_counts: Dict[str, int] = Field(default_factory=dict, description="Count of operations by name")
    operation_total_time: Dict[str, float] = Field(default_factory=dict, description="Total time spent in each operation type (seconds)")
    operation_error_counts: Dict[str, int] = Field(default_factory=dict, description="Error count by operation type")
    p50_operation_time: Optional[float] = Field(None, ge=0, description="50th percentile operation time (median) in seconds")
    p95_operation_time: Optional[float] = Field(None, ge=0, description="95th percentile operation time in seconds")
    p99_operation_time: Optional[float] = Field(None, ge=0, description="99th percentile operation time in seconds")

    # Timestamps
    last_reset_at: Optional[datetime] = Field(None, description="When metrics were last reset")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update")

    model_config = ConfigDict()


class GraphMetrics(BaseModel):
    """Model for tracking knowledge graph retrieval metrics."""

    # Query metrics
    total_graph_queries: int = Field(default=0, ge=0, description="Total number of graph queries executed")
    total_entities_retrieved: int = Field(default=0, ge=0, description="Total number of entities retrieved")
    total_relationships_traversed: int = Field(default=0, ge=0, description="Total number of relationships traversed")

    # Performance metrics
    average_graph_query_time: float = Field(default=0.0, ge=0, description="Average graph query time in seconds")
    total_graph_query_time: float = Field(default=0.0, ge=0, description="Total graph query time in seconds")
    min_graph_query_time: Optional[float] = Field(None, ge=0, description="Minimum graph query time in seconds")
    max_graph_query_time: Optional[float] = Field(None, ge=0, description="Maximum graph query time in seconds")

    # Cache metrics
    cache_hit_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Cache hit rate (0-1)")
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, ge=0, description="Number of cache misses")

    # Strategy metrics
    vector_search_count: int = Field(default=0, ge=0, description="Number of vector-only searches")
    graph_search_count: int = Field(default=0, ge=0, description="Number of graph-only searches")
    hybrid_search_count: int = Field(default=0, ge=0, description="Number of hybrid searches")

    # Entity extraction metrics
    entity_extraction_count: int = Field(default=0, ge=0, description="Number of entity extractions performed")
    average_extraction_time: float = Field(default=0.0, ge=0, description="Average entity extraction time in seconds")
    total_extraction_time: float = Field(default=0.0, ge=0, description="Total entity extraction time in seconds")

    # Timestamps
    last_reset_at: Optional[datetime] = Field(None, description="When metrics were last reset")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update")

    model_config = ConfigDict()


class AgentInteraction(BaseModel):
    """Model representing an agent interaction."""

    interaction_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique interaction identifier",
    )
    agent_id: str = Field(..., description="Agent ID involved in interaction")
    interaction_type: str = Field(
        ...,
        description="Type of interaction (e.g., 'task', 'message', 'tool_call')",
    )
    content: Dict[str, Any] = Field(..., description="Interaction content")

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Interaction timestamp")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Interaction duration")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional interaction metadata")

    model_config = ConfigDict()


class AgentMemory(BaseModel):
    """Model for agent memory interface (base model, not implementation)."""

    memory_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique memory identifier",
    )
    agent_id: str = Field(..., description="Associated agent ID")
    memory_type: MemoryType = Field(..., description="Type of memory")
    key: str = Field(..., description="Memory key")
    value: Any = Field(..., description="Memory value")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When memory was stored")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional memory metadata")

    model_config = ConfigDict()


class Experience(BaseModel):
    """
    Model for recording agent learning experiences.

    Tracks task execution experiences to enable learning and adaptation.
    Used by agents to improve performance over time by learning from
    past successes and failures. Experiences are used to recommend
    optimal approaches for similar tasks.

    **Key Features:**
    - Comprehensive task execution tracking
    - Success/failure outcome recording
    - Quality scoring and error classification
    - Learning insights and recommendations
    - Context and performance metrics

    Attributes:
        experience_id: Unique identifier for the experience
        agent_id: ID of the agent that had this experience
        task_type: Type/category of task (e.g., "data_analysis", "search")
        task_description: Human-readable task description
        task_complexity: Task complexity level (simple, medium, complex)
        approach: Approach/strategy used (e.g., "parallel_tools", "sequential")
        tools_used: List of tool names used in execution
        execution_time: Execution time in seconds
        success: Whether task execution succeeded
        quality_score: Quality score from 0.0 to 1.0 (None if not available)
        error_type: Type of error if failed (e.g., "timeout", "validation_error")
        error_message: Error message if failed
        context_size: Context size in tokens (if applicable)
        iterations: Number of iterations/attempts (if applicable)
        lessons_learned: Human-readable lessons learned from this experience
        recommended_improvements: Recommended improvements for future tasks
        timestamp: When the experience occurred
        metadata: Additional experience metadata

    Examples:
        # Example 1: Successful experience
        experience = Experience(
            agent_id="agent-1",
            task_type="data_analysis",
            task_description="Analyze sales data for Q4",
            task_complexity="medium",
            approach="parallel_tools",
            tools_used=["pandas", "numpy"],
            execution_time=2.5,
            success=True,
            quality_score=0.95,
            context_size=5000,
            iterations=1
        )

        # Example 2: Failed experience with error details
        experience = Experience(
            agent_id="agent-1",
            task_type="web_scraping",
            task_description="Scrape product prices",
            task_complexity="simple",
            approach="single_tool",
            tools_used=["scraper"],
            execution_time=30.0,
            success=False,
            error_type="timeout",
            error_message="Request timed out after 30 seconds",
            lessons_learned="Use retry logic for network operations",
            recommended_improvements="Add exponential backoff retry"
        )

        # Example 3: Experience with learning insights
        experience = Experience(
            agent_id="agent-1",
            task_type="data_analysis",
            task_description="Analyze customer feedback",
            approach="parallel_tools",
            tools_used=["nlp", "sentiment"],
            execution_time=5.2,
            success=True,
            quality_score=0.88,
            lessons_learned="Parallel execution reduced time by 40%",
            recommended_improvements="Use parallel approach for similar tasks"
        )
    """

    experience_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique experience identifier",
    )
    agent_id: str = Field(..., description="Agent that had this experience")

    # Task information
    task_type: str = Field(..., description="Type/category of task")
    task_description: str = Field(..., description="Task description")
    task_complexity: Optional[str] = Field(None, description="Task complexity (simple, medium, complex)")

    # Execution details
    approach: str = Field(..., description="Approach/strategy used")
    tools_used: List[str] = Field(default_factory=list, description="Tools used in execution")
    execution_time: float = Field(..., ge=0, description="Execution time in seconds")

    # Outcome
    success: bool = Field(..., description="Whether task was successful")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score (0-1)")
    error_type: Optional[str] = Field(None, description="Error type if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Context
    context_size: Optional[int] = Field(None, ge=0, description="Context size in tokens")
    iterations: Optional[int] = Field(None, ge=0, description="Number of iterations")

    # Learning insights
    lessons_learned: Optional[str] = Field(None, description="Lessons learned from experience")
    recommended_improvements: Optional[str] = Field(None, description="Recommended improvements")

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When experience occurred")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional experience metadata")

    model_config = ConfigDict()


class ResourceLimits(BaseModel):
    """
    Configuration for agent resource limits and rate limiting.

    Provides control over resource usage to prevent exhaustion and
    ensure stable operation in production environments. Supports
    token bucket algorithm for rate limiting, concurrent task limits,
    and memory constraints.

    **Key Features:**
    - Concurrent task limits to prevent overload
    - Token rate limiting with burst support (token bucket algorithm)
    - Tool call rate limiting per minute/hour
    - Memory usage limits
    - Task timeout configuration
    - Configurable enforcement (enforce vs monitor)

    Attributes:
        max_concurrent_tasks: Maximum number of concurrent tasks (default: 10)
        max_tokens_per_minute: Maximum tokens per minute (None = unlimited)
        max_tokens_per_hour: Maximum tokens per hour (None = unlimited)
        token_burst_size: Token burst size for token bucket (None = use max_tokens_per_minute)
        max_tool_calls_per_minute: Maximum tool calls per minute (None = unlimited)
        max_tool_calls_per_hour: Maximum tool calls per hour (None = unlimited)
        max_memory_mb: Maximum memory usage in MB (None = unlimited)
        task_timeout_seconds: Maximum task execution time in seconds (None = unlimited)
        resource_wait_timeout_seconds: Maximum time to wait for resources (default: 60)
        enforce_limits: Whether to enforce resource limits (default: True)
        reject_on_limit: Reject requests when limit reached vs wait (default: False)

    Examples:
        # Example 1: Basic rate limiting
        limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tokens_per_minute=10000,
            max_tool_calls_per_minute=100
        )

        # Example 2: Token bucket with burst support
        limits = ResourceLimits(
            max_tokens_per_minute=10000,
            token_burst_size=20000,  # Allow 2x burst
            max_tool_calls_per_minute=100
        )

        # Example 3: Strict limits for production
        limits = ResourceLimits(
            max_concurrent_tasks=10,
            max_tokens_per_minute=50000,
            max_tokens_per_hour=2000000,
            max_tool_calls_per_minute=500,
            max_memory_mb=2048,
            task_timeout_seconds=300,
            enforce_limits=True,
            reject_on_limit=True  # Reject instead of waiting
        )

        # Example 4: Monitoring mode (don't enforce)
        limits = ResourceLimits(
            max_concurrent_tasks=10,
            max_tokens_per_minute=10000,
            enforce_limits=False  # Monitor but don't enforce
        )

        # Example 5: Wait for resources instead of rejecting
        limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tokens_per_minute=10000,
            resource_wait_timeout_seconds=120,  # Wait up to 2 minutes
            reject_on_limit=False  # Wait instead of reject
        )
    """

    # Concurrent task limits
    max_concurrent_tasks: int = Field(default=10, ge=1, description="Maximum number of concurrent tasks")

    # Token rate limits (token bucket algorithm)
    max_tokens_per_minute: Optional[int] = Field(None, ge=0, description="Maximum tokens per minute (None = unlimited)")
    max_tokens_per_hour: Optional[int] = Field(None, ge=0, description="Maximum tokens per hour (None = unlimited)")
    token_burst_size: Optional[int] = Field(
        None,
        ge=0,
        description="Token burst size for token bucket (None = use max_tokens_per_minute)",
    )

    # Tool call rate limits
    max_tool_calls_per_minute: Optional[int] = Field(None, ge=0, description="Maximum tool calls per minute (None = unlimited)")
    max_tool_calls_per_hour: Optional[int] = Field(None, ge=0, description="Maximum tool calls per hour (None = unlimited)")

    # Memory limits
    max_memory_mb: Optional[int] = Field(None, ge=0, description="Maximum memory usage in MB (None = unlimited)")

    # Timeout settings
    task_timeout_seconds: Optional[int] = Field(None, ge=0, description="Maximum task execution time in seconds (None = unlimited)")
    resource_wait_timeout_seconds: int = Field(default=60, ge=0, description="Maximum time to wait for resources")

    # Enforcement
    enforce_limits: bool = Field(default=True, description="Whether to enforce resource limits")
    reject_on_limit: bool = Field(default=False, description="Reject requests when limit reached (vs wait)")

    model_config = ConfigDict()


class ToolObservation(BaseModel):
    """
    Structured observation of tool execution results.

    Provides a standardized format for tracking tool execution with
    success/error status, execution time, and timestamps. Used for
    debugging, analysis, and LLM reasoning loops.

    This pattern is essential for MasterController compatibility and
    observation-based reasoning. Observations can be converted to text
    format for inclusion in LLM prompts or to dictionaries for serialization.

    **Key Features:**
    - Automatic success/error tracking
    - Execution time measurement
    - ISO timestamp generation
    - Text formatting for LLM context
    - Dictionary serialization for storage

    Attributes:
        tool_name: Name of the tool that was executed
        parameters: Dictionary of parameters passed to the tool
        result: Tool execution result (any type)
        success: Whether tool execution succeeded (True/False)
        error: Error message if execution failed (None if successful)
        execution_time_ms: Execution time in milliseconds (None if not measured)
        timestamp: ISO format timestamp of execution

    Examples:
        # Example 1: Successful tool execution
        from aiecs.domain.agent.models import ToolObservation

        obs = ToolObservation(
            tool_name="search",
            parameters={"query": "AI", "limit": 10},
            result=["result1", "result2", "result3"],
            success=True,
            execution_time_ms=250.5
        )

        # Convert to text for LLM context
        text = obs.to_text()
        # "Tool: search
        # Parameters: {'query': 'AI', 'limit': 10}
        # Status: SUCCESS
        # Result: ['result1', 'result2', 'result3']
        # Execution time: 250.5ms"

        # Example 2: Failed tool execution
        obs = ToolObservation(
            tool_name="calculator",
            parameters={"operation": "divide", "a": 10, "b": 0},
            result=None,
            success=False,
            error="Division by zero",
            execution_time_ms=5.2
        )

        text = obs.to_text()
        # "Tool: calculator
        # Parameters: {'operation': 'divide', 'a': 10, 'b': 0}
        # Status: ERROR
        # Error: Division by zero
        # Execution time: 5.2ms"

        # Example 3: Using with agent execution
        from aiecs.domain.agent import HybridAgent

        agent = HybridAgent(...)
        obs = await agent._execute_tool_with_observation(
            tool_name="search",
            operation="query",
            parameters={"q": "Python"}
        )

        # Check success
        if obs.success:
            print(f"Found {len(obs.result)} results")
        else:
            print(f"Error: {obs.error}")

        # Example 4: Serialization for storage
        obs = ToolObservation(
            tool_name="api_call",
            parameters={"endpoint": "/data", "method": "GET"},
            result={"status": 200, "data": {...}},
            success=True,
            execution_time_ms=1234.5
        )

        # Convert to dict for JSON serialization
        data = obs.to_dict()
        # {'tool_name': 'api_call', 'parameters': {...}, 'success': True, ...}

        # Example 5: Using in observation-based reasoning loop
        observations = []
        for tool_call in tool_calls:
            obs = await agent._execute_tool_with_observation(
                tool_name=tool_call["tool"],
                parameters=tool_call["parameters"]
            )
            observations.append(obs)

        # Format observations for LLM context
        observation_text = "\\n\\n".join([obs.to_text() for obs in observations])
        # Include in LLM prompt for reasoning
    """

    tool_name: str = Field(..., description="Name of the tool that was executed")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the tool")
    result: Any = Field(None, description="Tool execution result")
    success: bool = Field(..., description="Whether tool execution succeeded")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: Optional[float] = Field(None, ge=0, description="Execution time in milliseconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO format timestamp of execution",
    )

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert observation to dictionary.

        Returns:
            Dict representation of the observation

        Example:
            ```python
            obs = ToolObservation(tool_name="search", success=True, result="data")
            data = obs.to_dict()
            # {'tool_name': 'search', 'success': True, 'result': 'data', ...}
            ```
        """
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }

    def to_text(self) -> str:
        """
        Format observation as text for LLM context.

        Provides a human-readable format suitable for including in
        LLM prompts and reasoning loops.

        Returns:
            Formatted text representation

        Example:
            ```python
            obs = ToolObservation(
                tool_name="search",
                parameters={"query": "AI"},
                success=True,
                result="Found 10 results",
                execution_time_ms=250.5
            )
            text = obs.to_text()
            # "Tool: search
            # Parameters: {'query': 'AI'}
            # Status: SUCCESS
            # Result: Found 10 results
            # Execution time: 250.5ms"
            ```
        """
        lines = [
            f"Tool: {self.tool_name}",
            f"Parameters: {self.parameters}",
        ]

        if self.success:
            lines.append("Status: SUCCESS")
            lines.append(f"Result: {self.result}")
        else:
            lines.append("Status: FAILURE")
            lines.append(f"Error: {self.error}")

        if self.execution_time_ms is not None:
            lines.append(f"Execution time: {self.execution_time_ms:.2f}ms")

        lines.append(f"Timestamp: {self.timestamp}")

        return "\n".join(lines)
