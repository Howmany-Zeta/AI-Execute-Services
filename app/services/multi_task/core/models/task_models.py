"""
Task Models

Data models for task-related entities in the multi-task service.
"""

from pydantic import ConfigDict, BaseModel, Field, field_serializer
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Task execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskCategory(Enum):
    """Task category types."""
    ANSWER = "answer"
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"


class TaskType(Enum):
    """Task execution types."""
    FAST = "fast"
    HEAVY = "heavy"


class TaskModel(BaseModel):
    """
    Core task model representing a task in the system.
    """
    task_id: str = Field(..., description="Unique identifier for the task")
    name: str = Field(..., description="Human-readable name of the task")
    description: str = Field(..., description="Detailed description of the task")
    category: TaskCategory = Field(..., description="Category of the task")
    task_type: TaskType = Field(default=TaskType.FAST, description="Type of task execution")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority level")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")

    # Configuration
    timeout_seconds: Optional[int] = Field(None, description="Task timeout in seconds")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    # Relationships
    user_id: str = Field(..., description="ID of the user who created the task")
    parent_task_id: Optional[str] = Field(None, description="ID of parent task if this is a subtask")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow this task belongs to")

    # Execution details
    agent_id: Optional[str] = Field(None, description="ID of the agent assigned to this task")
    tools: List[str] = Field(default_factory=list, description="List of tools required for this task")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs this task depends on")

    # Results and errors
    result: Optional[Dict[str, Any]] = Field(None, description="Task execution result")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    error_code: Optional[str] = Field(None, description="Error code if task failed")

    # Metrics
    execution_time_seconds: Optional[float] = Field(None, description="Task execution time in seconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at', 'updated_at', 'started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


class TaskRequest(BaseModel):
    """
    Request model for task creation and execution.
    """
    # Basic task information
    name: Optional[str] = Field(None, description="Human-readable name of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    category: Optional[TaskCategory] = Field(None, description="Category of the task")
    task_type: TaskType = Field(default=TaskType.FAST, description="Type of task execution")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority level")

    # Input data
    input_data: Dict[str, Any] = Field(..., description="Input data for task execution")
    text: Optional[str] = Field(None, description="Text input for the task")

    # Configuration
    timeout_seconds: Optional[int] = Field(None, description="Task timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    # User and context
    user_id: str = Field(..., description="ID of the user creating the task")
    task_id: Optional[str] = Field(None, description="Optional task ID for resuming existing tasks")
    parent_task_id: Optional[str] = Field(None, description="ID of parent task if this is a subtask")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow this task belongs to")

    # Execution preferences
    preferred_agent: Optional[str] = Field(None, description="Preferred agent for task execution")
    required_tools: List[str] = Field(default_factory=list, description="List of required tools")
    execution_mode: str = Field(default="sequential", description="Execution mode (sequential, parallel)")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)


class TaskResponse(BaseModel):
    """
    Response model for task execution results.
    """
    # Task identification
    task_id: str = Field(..., description="Unique identifier for the task")
    status: TaskStatus = Field(..., description="Current task status")

    # Execution results
    result: Optional[Dict[str, Any]] = Field(None, description="Task execution result")
    message: str = Field(..., description="Human-readable status message")

    # Progress information
    progress: float = Field(default=0.0, description="Task completion progress (0.0 to 1.0)")
    current_step: Optional[str] = Field(None, description="Current execution step")
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")

    # Timing information
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    execution_time_seconds: Optional[float] = Field(None, description="Task execution time in seconds")

    # Error information
    error_code: Optional[str] = Field(None, description="Error code if task failed")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

    # Quality control
    quality_score: Optional[float] = Field(None, description="Quality score of the result (0.0 to 1.0)")
    validation_passed: Optional[bool] = Field(None, description="Whether result passed validation")
    validation_feedback: Optional[str] = Field(None, description="Validation feedback")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Sub-results for complex tasks
    sub_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results from sub-tasks")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


class TaskStep(BaseModel):
    """
    Model representing a single step in task execution.
    """
    step_id: str = Field(..., description="Unique identifier for the step")
    name: str = Field(..., description="Name of the step")
    description: Optional[str] = Field(None, description="Description of the step")
    order: int = Field(..., description="Execution order of the step")

    # Step configuration
    step_type: str = Field(..., description="Type of step (task, condition, parallel, etc.)")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Step configuration")

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="List of step IDs this step depends on")

    # Execution details
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Step execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Step execution result")
    error_message: Optional[str] = Field(None, description="Error message if step failed")

    # Timing
    started_at: Optional[datetime] = Field(None, description="Step start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Step completion timestamp")
    execution_time_seconds: Optional[float] = Field(None, description="Step execution time in seconds")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


class TaskWorkflow(BaseModel):
    """
    Model representing a workflow composed of multiple tasks.
    """
    workflow_id: str = Field(..., description="Unique identifier for the workflow")
    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(None, description="Description of the workflow")

    # Workflow structure
    steps: List[TaskStep] = Field(..., description="List of steps in the workflow")
    execution_mode: str = Field(default="sequential", description="Workflow execution mode")

    # Status and progress
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Workflow status")
    progress: float = Field(default=0.0, description="Workflow completion progress")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Workflow creation timestamp")
    user_id: str = Field(..., description="ID of the user who created the workflow")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class ExecutionContext(BaseModel):
    """
    Model representing the execution context for tasks and agents.
    """
    # Context identification
    context_id: str = Field(..., description="Unique identifier for the execution context")
    task_id: str = Field(..., description="ID of the task being executed")
    user_id: str = Field(..., description="ID of the user who initiated the task")

    # Execution environment
    session_id: Optional[str] = Field(None, description="Session ID for the execution")
    workflow_id: Optional[str] = Field(None, description="ID of the workflow this execution belongs to")
    parent_context_id: Optional[str] = Field(None, description="ID of parent execution context")

    # Timing information
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Context start timestamp")
    timeout_at: Optional[datetime] = Field(None, description="Context timeout timestamp")

    # Execution state
    current_step: int = Field(default=0, description="Current execution step")
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    execution_mode: str = Field(default="sequential", description="Execution mode")

    # Configuration
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    timeout_seconds: Optional[int] = Field(None, description="Execution timeout in seconds")

    # Agent and tool information
    assigned_agent_id: Optional[str] = Field(None, description="ID of the assigned agent")
    available_tools: List[str] = Field(default_factory=list, description="List of available tools")

    # Data and state
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for execution")
    shared_state: Dict[str, Any] = Field(default_factory=dict, description="Shared state across execution steps")
    intermediate_results: List[Dict[str, Any]] = Field(default_factory=list, description="Intermediate execution results")

    # Quality control
    quality_requirements: Dict[str, Any] = Field(default_factory=dict, description="Quality requirements for execution")
    validation_rules: List[str] = Field(default_factory=list, description="Validation rules to apply")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Performance tracking
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    model_config = ConfigDict()

    @field_serializer('started_at', 'timeout_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None
