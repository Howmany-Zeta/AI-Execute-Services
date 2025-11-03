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


class RetryPolicy(BaseModel):
    """Retry policy configuration for agent operations."""

    max_retries: int = Field(default=5, ge=0, description="Maximum number of retry attempts")
    base_delay: float = Field(default=1.0, ge=0, description="Base delay in seconds for exponential backoff")
    max_delay: float = Field(default=32.0, ge=0, description="Maximum delay cap in seconds")
    exponential_factor: float = Field(default=2.0, ge=1.0, description="Exponential factor for backoff")
    jitter_factor: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Jitter factor (±percentage) for randomization"
    )
    rate_limit_base_delay: float = Field(
        default=5.0, ge=0, description="Base delay for rate limit errors"
    )
    rate_limit_max_delay: float = Field(
        default=120.0, ge=0, description="Maximum delay for rate limit errors"
    )

    model_config = ConfigDict()


class AgentConfiguration(BaseModel):
    """Configuration model for agent behavior and capabilities."""

    # LLM settings
    llm_provider: Optional[str] = Field(None, description="LLM provider name (e.g., 'openai', 'vertex')")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature setting")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens for LLM responses")

    # Tool access
    allowed_tools: List[str] = Field(default_factory=list, description="List of tool names agent can use")
    tool_selection_strategy: str = Field(
        default="llm_based", description="Strategy for tool selection ('llm_based', 'rule_based')"
    )

    # Memory configuration
    memory_enabled: bool = Field(default=True, description="Whether memory is enabled")
    memory_capacity: int = Field(
        default=1000, ge=0, description="Maximum number of memory items"
    )
    memory_ttl_seconds: Optional[int] = Field(
        None, ge=0, description="Time-to-live for short-term memory in seconds"
    )

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
    context_window_limit: int = Field(
        default=20000, ge=0, description="Token limit for context window"
    )
    enable_context_compression: bool = Field(
        default=True, description="Enable automatic context compression"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration metadata")

    model_config = ConfigDict()


class AgentGoal(BaseModel):
    """Model representing an agent goal."""

    goal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique goal identifier")
    description: str = Field(..., description="Goal description")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Current goal status")
    priority: GoalPriority = Field(default=GoalPriority.MEDIUM, description="Goal priority level")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage (0-100)")

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

    capability_type: str = Field(..., description="Type of capability (e.g., 'text_generation', 'code_generation')")
    level: CapabilityLevel = Field(..., description="Proficiency level")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Capability constraints")
    description: Optional[str] = Field(None, description="Capability description")

    # Timestamps
    acquired_at: datetime = Field(default_factory=datetime.utcnow, description="When capability was acquired")

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
    average_quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Average quality score (0-1)"
    )

    # Resource usage
    total_tokens_used: int = Field(default=0, ge=0, description="Total LLM tokens used")
    total_tool_calls: int = Field(default=0, ge=0, description="Total tool calls made")
    total_api_cost: Optional[float] = Field(None, ge=0, description="Total API cost (if tracked)")

    # Retry metrics
    total_retries: int = Field(default=0, ge=0, description="Total number of retry attempts")
    retry_successes: int = Field(default=0, ge=0, description="Number of successful retries")

    # Error tracking
    error_count: int = Field(default=0, ge=0, description="Total number of errors")
    error_types: Dict[str, int] = Field(
        default_factory=dict, description="Count of errors by type"
    )

    # Timestamps
    last_reset_at: Optional[datetime] = Field(None, description="When metrics were last reset")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update")

    model_config = ConfigDict()


class AgentInteraction(BaseModel):
    """Model representing an agent interaction."""

    interaction_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique interaction identifier"
    )
    agent_id: str = Field(..., description="Agent ID involved in interaction")
    interaction_type: str = Field(..., description="Type of interaction (e.g., 'task', 'message', 'tool_call')")
    content: Dict[str, Any] = Field(..., description="Interaction content")

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Interaction timestamp")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Interaction duration")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional interaction metadata")

    model_config = ConfigDict()


class AgentMemory(BaseModel):
    """Model for agent memory interface (base model, not implementation)."""

    memory_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique memory identifier")
    agent_id: str = Field(..., description="Associated agent ID")
    memory_type: MemoryType = Field(..., description="Type of memory")
    key: str = Field(..., description="Memory key")
    value: Any = Field(..., description="Memory value")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When memory was stored")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional memory metadata")

    model_config = ConfigDict()

