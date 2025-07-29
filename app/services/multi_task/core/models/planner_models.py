"""
Planner Layer Models

Data models for planner-related entities in the multi-task service.
These models define the structure and validation for planning operations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum


class IntentCategory(str, Enum):
    """Intent category enumeration."""
    ANSWER = "answer"
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"


class PlanStatus(str, Enum):
    """Plan status enumeration."""
    DRAFT = "draft"
    VALIDATED = "validated"
    OPTIMIZED = "optimized"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DSLStepType(str, Enum):
    """DSL step type enumeration."""
    TASK = "task"
    PARALLEL = "parallel"
    CONDITIONAL = "if"
    SEQUENCE = "sequence"
    LOOP = "loop"


class ValidationSeverity(str, Enum):
    """Validation severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PlannerConfig(BaseModel):
    """
    Configuration model for the planner service.

    Defines all configuration parameters needed to initialize
    and operate the planner service.
    """
    # Service configuration
    service_name: str = Field(default="workflow_planner", description="Name of the planner service")
    version: str = Field(default="1.0.0", description="Version of the planner")

    # Agent configuration
    intent_parser_agent: str = Field(..., description="Agent ID for intent parsing")
    task_decomposer_agent: str = Field(..., description="Agent ID for task decomposition")
    sequence_planner_agent: str = Field(..., description="Agent ID for sequence planning")

    # Timeout settings
    intent_parsing_timeout: int = Field(default=30, description="Timeout for intent parsing in seconds")
    decomposition_timeout: int = Field(default=45, description="Timeout for task decomposition in seconds")
    planning_timeout: int = Field(default=60, description="Timeout for sequence planning in seconds")

    # Quality settings
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold for results")
    validation_enabled: bool = Field(default=True, description="Whether to validate plans")
    optimization_enabled: bool = Field(default=True, description="Whether to optimize plans")

    # Resource limits
    max_subtasks_per_category: int = Field(default=5, description="Maximum sub-tasks per category")
    max_sequence_steps: int = Field(default=20, description="Maximum steps in execution sequence")
    max_parallel_tasks: int = Field(default=3, description="Maximum parallel tasks")

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")

    # Logging and monitoring
    enable_metrics: bool = Field(default=True, description="Whether to collect metrics")
    enable_tracing: bool = Field(default=True, description="Whether to enable tracing")
    log_level: str = Field(default="INFO", description="Logging level")

    # Feature flags
    enable_parallel_optimization: bool = Field(default=True, description="Enable parallel execution optimization")
    enable_conditional_planning: bool = Field(default=True, description="Enable conditional execution planning")
    enable_adaptive_planning: bool = Field(default=False, description="Enable adaptive planning based on context")

    class Config:
        use_enum_values = True


class PlanningContext(BaseModel):
    """
    Context model for planning operations.

    Contains all contextual information needed for planning decisions.
    """
    # Request context
    user_id: str = Field(..., description="ID of the user making the request")
    task_id: str = Field(..., description="Unique task identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

    # Input context
    original_input: Dict[str, Any] = Field(..., description="Original user input")
    input_metadata: Dict[str, Any] = Field(default_factory=dict, description="Input metadata")

    # Resource context
    available_agents: List[str] = Field(default_factory=list, description="Available agent IDs")
    available_tools: List[str] = Field(default_factory=list, description="Available tool names")
    system_constraints: Dict[str, Any] = Field(default_factory=dict, description="System constraints")

    # Execution context
    execution_mode: str = Field(default="standard", description="Execution mode (standard, fast, thorough)")
    priority: str = Field(default="normal", description="Task priority (low, normal, high, urgent)")
    deadline: Optional[datetime] = Field(None, description="Task deadline")

    # Quality context
    quality_requirements: Dict[str, Any] = Field(default_factory=dict, description="Quality requirements")
    validation_rules: List[str] = Field(default_factory=list, description="Validation rules to apply")

    # Historical context
    previous_plans: List[str] = Field(default_factory=list, description="Previous plan IDs for reference")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

    # Temporal context
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Context creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Context expiration timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntentParsingResult(BaseModel):
    """
    Result model for intent parsing operations.
    """
    categories: List[IntentCategory] = Field(..., description="Identified intent categories")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores for each category")
    reasoning: str = Field(..., description="Reasoning for the categorization")
    alternative_interpretations: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative interpretations")

    # Metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    model_version: str = Field(..., description="Version of the parsing model used")

    @field_validator('confidence_scores')
    @classmethod
    def validate_confidence_scores(cls, v, info):
        """Validate that confidence scores match categories."""
        if info.data and 'categories' in info.data:
            categories = [cat.value if hasattr(cat, 'value') else cat for cat in info.data['categories']]
            missing_scores = set(categories) - set(v.keys())
            if missing_scores:
                raise ValueError(f"Missing confidence scores for categories: {missing_scores}")
        return v


class TaskDecompositionResult(BaseModel):
    """
    Result model for task decomposition operations.
    """
    breakdown: Dict[str, List[str]] = Field(..., description="Category to sub-tasks mapping")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Task dependencies")
    complexity_analysis: Dict[str, Any] = Field(..., description="Complexity analysis of the breakdown")
    feasibility_score: float = Field(..., description="Feasibility score (0.0 to 1.0)")

    # Metadata
    total_subtasks: int = Field(..., description="Total number of sub-tasks")
    estimated_duration: str = Field(..., description="Estimated execution duration")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")

    @field_validator('feasibility_score')
    @classmethod
    def validate_feasibility_score(cls, v):
        """Validate feasibility score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Feasibility score must be between 0.0 and 1.0")
        return v


class DSLStep(BaseModel):
    """
    Model representing a single step in the DSL execution plan.
    """
    step_type: DSLStepType = Field(..., description="Type of DSL step")
    step_id: str = Field(..., description="Unique identifier for the step")

    # Task step fields
    task: Optional[str] = Field(None, description="Task name for task steps")
    category: Optional[str] = Field(None, description="Task category")
    tools: List[str] = Field(default_factory=list, description="Tools required for the step")

    # Parallel step fields
    parallel: Optional[List['DSLStep']] = Field(None, description="Parallel sub-steps")

    # Conditional step fields
    condition: Optional[str] = Field(None, description="Condition expression for conditional steps")
    then_steps: Optional[List['DSLStep']] = Field(None, description="Steps to execute if condition is true")
    else_steps: Optional[List['DSLStep']] = Field(None, description="Steps to execute if condition is false")

    # Sequence step fields
    sequence: Optional[List['DSLStep']] = Field(None, description="Sequential sub-steps")

    # Loop step fields
    loop_condition: Optional[str] = Field(None, description="Loop condition")
    loop_steps: Optional[List['DSLStep']] = Field(None, description="Steps to repeat in loop")
    max_iterations: Optional[int] = Field(None, description="Maximum loop iterations")

    # Execution metadata
    estimated_duration_seconds: Optional[float] = Field(None, description="Estimated execution time")
    priority: int = Field(default=0, description="Step priority")
    retry_count: int = Field(default=0, description="Number of retry attempts")

    class Config:
        # Allow forward references for recursive model
        arbitrary_types_allowed = True


# Update forward reference
DSLStep.model_rebuild()


class SequencePlanningResult(BaseModel):
    """
    Result model for sequence planning operations.
    """
    sequence: List[DSLStep] = Field(..., description="Planned execution sequence")
    optimization_applied: List[str] = Field(default_factory=list, description="Optimizations applied")
    parallel_groups: int = Field(default=0, description="Number of parallel execution groups")
    estimated_total_duration: str = Field(..., description="Estimated total execution time")

    # Analysis
    complexity_score: float = Field(..., description="Complexity score of the plan")
    efficiency_score: float = Field(..., description="Efficiency score of the plan")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk assessment")

    # Metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    planner_version: str = Field(..., description="Version of the planner used")


class WorkflowPlan(BaseModel):
    """
    Complete workflow plan model.

    Represents the final output of the planning process,
    containing all information needed for execution.
    """
    # Identification
    plan_id: str = Field(..., description="Unique plan identifier")
    task_id: str = Field(..., description="Associated task identifier")
    user_id: str = Field(..., description="User who requested the plan")

    # Plan content
    intent_result: IntentParsingResult = Field(..., description="Intent parsing result")
    decomposition_result: TaskDecompositionResult = Field(..., description="Task decomposition result")
    sequence_result: SequencePlanningResult = Field(..., description="Sequence planning result")

    # Plan metadata
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="Current plan status")
    version: int = Field(default=1, description="Plan version number")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Plan creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Validation and quality
    validation_results: Dict[str, Any] = Field(default_factory=dict, description="Validation results")
    quality_score: Optional[float] = Field(None, description="Overall quality score")
    confidence_score: float = Field(..., description="Overall confidence in the plan")

    # Execution metadata
    estimated_duration: str = Field(..., description="Estimated total execution time")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Required resources")
    execution_constraints: Dict[str, Any] = Field(default_factory=dict, description="Execution constraints")

    # Context
    planning_context: PlanningContext = Field(..., description="Context used for planning")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlanValidationResult(BaseModel):
    """
    Result model for plan validation operations.
    """
    is_valid: bool = Field(..., description="Whether the plan is valid")
    validation_score: float = Field(..., description="Validation score (0.0 to 1.0)")

    # Validation details
    structural_validation: Dict[str, Any] = Field(..., description="Structural validation results")
    feasibility_validation: Dict[str, Any] = Field(..., description="Feasibility validation results")
    quality_validation: Dict[str, Any] = Field(..., description="Quality validation results")

    # Issues and recommendations
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    validator_version: str = Field(..., description="Version of the validator used")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlanMetrics(BaseModel):
    """
    Metrics model for workflow plans.
    """
    # Complexity metrics
    total_steps: int = Field(..., description="Total number of execution steps")
    parallel_steps: int = Field(..., description="Number of parallel execution groups")
    conditional_steps: int = Field(..., description="Number of conditional steps")
    loop_steps: int = Field(..., description="Number of loop steps")

    # Efficiency metrics
    estimated_duration_seconds: float = Field(..., description="Estimated duration in seconds")
    parallelization_ratio: float = Field(..., description="Ratio of parallelizable steps")
    optimization_score: float = Field(..., description="Optimization effectiveness score")

    # Resource metrics
    required_agents: List[str] = Field(..., description="Required agent types")
    required_tools: List[str] = Field(..., description="Required tools")
    memory_estimate_mb: Optional[float] = Field(None, description="Estimated memory usage in MB")
    cpu_estimate_percent: Optional[float] = Field(None, description="Estimated CPU usage percentage")

    # Quality metrics
    confidence_score: float = Field(..., description="Overall confidence score")
    risk_score: float = Field(..., description="Risk assessment score")
    success_probability: float = Field(..., description="Estimated success probability")

    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="Metrics calculation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
