"""
Execution Models

Data models for execution-related entities in the multi-task service.
"""

from pydantic import ConfigDict, BaseModel, Field, field_serializer
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ExecutionMode(Enum):
    """Execution mode enumeration."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"


class ToolType(Enum):
    """Tool type enumeration."""
    SCRAPER = "scraper"
    ANALYZER = "analyzer"
    CLASSIFIER = "classifier"
    RESEARCH = "research"
    DATA_PROCESSOR = "data_processor"
    CUSTOM = "custom"


class ExecutionContext(BaseModel):
    """
    Context model for task and workflow execution.
    """
    # Execution identification
    execution_id: str = Field(..., description="Unique identifier for the execution")
    user_id: str = Field(..., description="ID of the user initiating the execution")
    session_id: Optional[str] = Field(None, description="Session ID for the execution")

    # Task context
    task_id: Optional[str] = Field(None, description="ID of the current task")
    workflow_id: Optional[str] = Field(None, description="ID of the current workflow")
    parent_execution_id: Optional[str] = Field(None, description="ID of parent execution")

    # Execution configuration
    execution_mode: ExecutionMode = Field(default=ExecutionMode.SEQUENTIAL, description="Execution mode")
    timeout_seconds: Optional[int] = Field(None, description="Execution timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    # State and data
    variables: Dict[str, Any] = Field(default_factory=dict, description="Execution variables")
    shared_data: Dict[str, Any] = Field(default_factory=dict, description="Shared data across steps")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Original input data")

    # Quality control
    quality_threshold: float = Field(default=0.8, description="Quality threshold for results")
    validation_enabled: bool = Field(default=True, description="Whether to validate results")

    # Monitoring and logging
    trace_enabled: bool = Field(default=True, description="Whether to enable execution tracing")
    metrics_enabled: bool = Field(default=True, description="Whether to collect metrics")
    log_level: str = Field(default="INFO", description="Logging level")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Context creation timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class ExecutionResult(BaseModel):
    """
    Result model for execution outcomes.
    """
    # Identification
    result_id: Optional[str] = Field(None, description="Unique identifier for the result")
    execution_id: str = Field(..., description="Unique identifier for the execution")
    step_id: Optional[str] = Field(None, description="ID of the execution step")
    task_id: Optional[str] = Field(None, description="ID of the executed task")

    # Status and outcome
    status: ExecutionStatus = Field(..., description="Execution status")
    success: bool = Field(..., description="Whether execution was successful")
    message: str = Field(..., description="Human-readable status message")

    # Results
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result data")
    output: Optional[Any] = Field(None, description="Primary output of the execution")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")

    # Quality metrics
    quality_score: Optional[float] = Field(None, description="Quality score (0.0 to 1.0)")
    confidence_score: Optional[float] = Field(None, description="Confidence score (0.0 to 1.0)")
    validation_passed: Optional[bool] = Field(None, description="Whether result passed validation")
    validation_feedback: Optional[str] = Field(None, description="Validation feedback")

    # Error information
    error_code: Optional[str] = Field(None, description="Error code if execution failed")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    stack_trace: Optional[str] = Field(None, description="Stack trace for debugging")

    # Performance metrics
    execution_time_seconds: Optional[float] = Field(None, description="Execution time in seconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")

    # Timestamps
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


class ExecutionPlan(BaseModel):
    """
    Model representing an execution plan for workflows.
    """
    plan_id: str = Field(..., description="Unique identifier for the plan")
    workflow_id: str = Field(..., description="ID of the workflow this plan is for")

    # Plan structure
    steps: List[Dict[str, Any]] = Field(..., description="Ordered list of execution steps")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Step dependencies")
    parallel_groups: List[List[str]] = Field(default_factory=list, description="Groups of steps that can run in parallel")

    # Execution configuration
    execution_mode: ExecutionMode = Field(..., description="Overall execution mode")
    estimated_duration_seconds: Optional[int] = Field(None, description="Estimated execution duration")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")

    # Optimization
    optimized: bool = Field(default=False, description="Whether the plan has been optimized")
    optimization_score: Optional[float] = Field(None, description="Optimization score")

    # Validation
    validated: bool = Field(default=False, description="Whether the plan has been validated")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Plan creation timestamp")
    created_by: str = Field(..., description="ID of the user who created the plan")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class ToolConfig(BaseModel):
    """
    Configuration model for tools.
    """
    # Basic information
    name: str = Field(..., description="Name of the tool")
    tool_type: ToolType = Field(..., description="Type of the tool")
    description: str = Field(..., description="Description of the tool")
    version: str = Field(default="1.0.0", description="Tool version")

    # Configuration
    enabled: bool = Field(default=True, description="Whether the tool is enabled")
    timeout_seconds: Optional[int] = Field(None, description="Tool execution timeout")
    max_retries: int = Field(default=3, description="Maximum number of retries")

    # Operations
    operations: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Available operations")
    default_operation: Optional[str] = Field(None, description="Default operation to use")

    # Parameters and schema
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for parameters")
    required_parameters: List[str] = Field(default_factory=list, description="Required parameters")
    optional_parameters: List[str] = Field(default_factory=list, description="Optional parameters")

    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Tool dependencies")
    required_capabilities: List[str] = Field(default_factory=list, description="Required system capabilities")

    # Authentication and security
    requires_auth: bool = Field(default=False, description="Whether tool requires authentication")
    auth_config: Dict[str, Any] = Field(default_factory=dict, description="Authentication configuration")
    security_level: str = Field(default="low", description="Security level (low, medium, high)")

    # Resource requirements
    memory_limit_mb: Optional[int] = Field(None, description="Memory limit in MB")
    cpu_limit_percent: Optional[int] = Field(None, description="CPU limit percentage")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)


class ToolResult(BaseModel):
    """
    Result model for tool execution.
    """
    # Identification
    tool_name: str = Field(..., description="Name of the executed tool")
    operation: str = Field(..., description="Operation that was executed")
    execution_id: str = Field(..., description="Unique identifier for this execution")

    # Status and outcome
    success: bool = Field(..., description="Whether tool execution was successful")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Human-readable status message")

    # Results
    result: Optional[Any] = Field(None, description="Primary result of the tool execution")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Structured output data")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")

    # Quality metrics
    quality_score: Optional[float] = Field(None, description="Quality score of the result")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the result")

    # Error information
    error_code: Optional[str] = Field(None, description="Error code if execution failed")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

    # Performance metrics
    execution_time_seconds: float = Field(..., description="Tool execution time in seconds")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")

    # Input tracking
    input_parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters used")

    # Timestamps
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: datetime = Field(..., description="Execution completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class ExecutionModel(BaseModel):
    """
    Core execution model representing an execution instance in the system.
    """
    # Identification
    execution_id: str = Field(..., description="Unique identifier for the execution")
    name: Optional[str] = Field(None, description="Human-readable name for the execution")

    # Type and configuration
    execution_type: str = Field(..., description="Type of execution (task, workflow, operation)")
    execution_mode: ExecutionMode = Field(..., description="Execution mode")

    # Status and progress
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Current execution status")
    progress: float = Field(default=0.0, description="Execution progress (0.0 to 1.0)")
    current_step: Optional[str] = Field(None, description="Current execution step")

    # Context and relationships
    context: ExecutionContext = Field(..., description="Execution context")
    parent_execution_id: Optional[str] = Field(None, description="ID of parent execution")
    child_executions: List[str] = Field(default_factory=list, description="IDs of child executions")

    # Results and history
    results: List[ExecutionResult] = Field(default_factory=list, description="Execution results")
    final_result: Optional[ExecutionResult] = Field(None, description="Final execution result")

    # Performance metrics
    total_execution_time: Optional[float] = Field(None, description="Total execution time in seconds")
    peak_memory_usage: Optional[float] = Field(None, description="Peak memory usage in MB")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Execution creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at', 'started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


# Workflow-related models

class WorkflowStatus(Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(Enum):
    """Workflow type enumeration."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    PIPELINE = "pipeline"


class WorkflowStep(BaseModel):
    """Workflow step model."""
    step_id: str = Field(..., description="Unique identifier for the step")
    name: str = Field(..., description="Human-readable name for the step")
    step_type: str = Field(..., description="Type of the step")
    description: Optional[str] = Field(None, description="Description of the step")

    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Step configuration")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")

    # Execution settings
    timeout_seconds: Optional[int] = Field(None, description="Step timeout")
    max_retries: int = Field(default=3, description="Maximum retries")

    # Conditional execution
    condition: Optional[str] = Field(None, description="Execution condition")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)


class WorkflowExecution(BaseModel):
    """Workflow execution model."""
    execution_id: str = Field(..., description="Unique identifier for the workflow execution")
    workflow_id: str = Field(..., description="ID of the workflow being executed")
    name: Optional[str] = Field(None, description="Human-readable name")

    # Status and progress
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Current status")
    progress: float = Field(default=0.0, description="Execution progress (0.0 to 1.0)")
    current_step: Optional[str] = Field(None, description="Currently executing step")

    # Steps and results
    steps: List[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    step_results: Dict[str, ExecutionResult] = Field(default_factory=dict, description="Step execution results")

    # Configuration
    execution_mode: WorkflowType = Field(default=WorkflowType.SEQUENTIAL, description="Execution mode")
    timeout_seconds: Optional[int] = Field(None, description="Overall timeout")

    # Context
    context: ExecutionContext = Field(..., description="Execution context")

    # Results
    final_result: Optional[ExecutionResult] = Field(None, description="Final workflow result")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at', 'started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


# Task-related models for execution

class TaskType(Enum):
    """Task type enumeration."""
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"
    CUSTOM = "custom"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskExecution(BaseModel):
    """Task execution model."""
    execution_id: str = Field(..., description="Unique identifier for the task execution")
    task_id: str = Field(..., description="ID of the task being executed")
    name: Optional[str] = Field(None, description="Human-readable name")

    # Task definition
    task_type: TaskType = Field(..., description="Type of the task")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")

    # Status and progress
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Current status")
    progress: float = Field(default=0.0, description="Execution progress (0.0 to 1.0)")

    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Task configuration")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")

    # Context
    context: ExecutionContext = Field(..., description="Execution context")

    # Results
    result: Optional[ExecutionResult] = Field(None, description="Task execution result")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at', 'started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None


# Parallel execution models

class TaskNode(BaseModel):
    """Task node for parallel execution."""
    task_id: str = Field(..., description="Unique task identifier")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    estimated_duration: Optional[float] = Field(None, description="Estimated duration in seconds")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    model_config = ConfigDict(use_enum_values=True)


class ExecutionBatch(BaseModel):
    """Batch of tasks for parallel execution."""
    batch_id: str = Field(..., description="Unique batch identifier")
    tasks: List[TaskNode] = Field(..., description="Tasks in this batch")
    max_concurrency: int = Field(default=5, description="Maximum concurrent tasks")
    timeout_seconds: Optional[int] = Field(None, description="Batch timeout")

    # Status
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="Batch status")
    completed_tasks: int = Field(default=0, description="Number of completed tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at', 'started_at', 'completed_at')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value else None
