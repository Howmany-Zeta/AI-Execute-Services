"""
Services Models

This module contains all the data models used across the multi-task services.
These models have been extracted from individual service files for unified maintenance.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Annotated
from datetime import datetime

# Import for LangGraph message handling
try:
    from langgraph.graph.message import add_messages
except ImportError:
    # Fallback if langgraph is not available
    def add_messages(x):
        return x


# Enums
class RequestType(Enum):
    """Types of user requests"""
    SUBSTANTIAL = "substantial"
    NON_SUBSTANTIAL = "non_substantial"
    INAPPROPRIATE = "inappropriate"
    REDIRECT_GENERAL = "redirect_general"


class DemandState(Enum):
    """User demand states according to SMART criteria"""
    SMART_COMPLIANT = "SMART_COMPLIANT"  # Clear, specific, meets SMART criteria
    SMART_LARGE_SCOPE = "SMART_LARGE_SCOPE"  # Clear but too broad in scope
    VAGUE_UNCLEAR = "VAGUE_UNCLEAR"  # Vague, unclear, needs clarification


class ValidationRuleType(Enum):
    """Types of validation rules."""
    SYNTAX = "syntax"
    LOGIC = "logic"
    DEPENDENCY = "dependency"
    PERFORMANCE = "performance"
    SECURITY = "security"


# QC Service Models
@dataclass
class ExaminationRequest:
    """Request for task outcome examination"""
    task_name: str
    category: str
    task_result: Dict[str, Any]
    quality_level: Any = None  # QualityLevel enum from core.models.quality_models
    context: Optional[Dict[str, Any]] = None


@dataclass
class ExaminationResult:
    """Result of task outcome examination"""
    task_name: str
    category: str
    passed: bool
    overall_score: float
    criteria_scores: Dict[str, float]
    issues: List[str]
    recommendations: List[str]
    confidence: float
    reasoning: str
    quality_result: Optional[Any] = None  # QualityResult from core.models.quality_models
    examination_time: float = 0.0


@dataclass
class AcceptanceRequest:
    """Request for task outcome acceptance"""
    task_name: str
    category: str
    task_result: Dict[str, Any]
    original_requirements: Optional[Dict[str, Any]] = None
    quality_level: Any = None  # QualityLevel enum from core.models.quality_models
    context: Optional[Dict[str, Any]] = None


@dataclass
class AcceptanceResult:
    """Result of task outcome acceptance"""
    task_name: str
    category: str
    passed: bool
    overall_score: float
    criteria: Dict[str, bool]
    criteria_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    confidence: float
    reasoning: str
    quality_result: Optional[Any] = None  # QualityResult from core.models.quality_models
    acceptance_time: float = 0.0


# Workflow Planning Models
@dataclass
class WorkflowPlanningState:
    """State object for LangGraph workflow planning."""
    task_id: str
    user_id: str

    # Input from mining.py
    intent_categories: List[str] = None
    intent_confidence: float = 0.0
    intent_reasoning: str = ""
    strategic_blueprint: Dict[str, Any] = None

    # Task decomposition results
    subtask_breakdown: Dict[str, List[str]] = None
    agent_mapping: Dict[str, str] = None
    decomposition_confidence: float = 0.0

    # Planning results
    workflow_plan: List[Dict[str, Any]] = None
    execution_order: List[str] = None
    parallel_groups: List[List[str]] = None
    dependencies: Dict[str, List[str]] = None

    # Validation results
    validation_result: Dict[str, Any] = None
    is_valid: bool = False

    # Meta information
    complexity_assessment: Dict[str, Any] = None
    estimated_duration: str = ""
    confidence_score: float = 0.0

    # Error handling
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


# Interacter Service Models
@dataclass
class InteractionResult:
    """Result of user interaction validation"""
    request_type: RequestType
    is_valid: bool
    confidence: float
    reasoning: str
    guidance_message: Optional[str] = None
    should_proceed: bool = False


# Mining Service Models
@dataclass
class MiningContext:
    """Context for mining operations"""
    user_id: str = "anonymous"
    session_id: str = ""
    domain: str = "general"
    timestamp: Optional[str] = None
    task_id: str = ""
    max_clarification_rounds: int = 3
    current_round: int = 0


@dataclass
class MiningState:
    """State object for langgraph workflow"""
    user_input: str
    demand_state: Optional[str] = None
    smart_analysis: Optional[Dict[str, Any]] = None
    clarification_questions: List[str] = None
    user_responses: List[str] = None
    context: Optional[MiningContext] = None
    messages: Annotated[List[Dict], add_messages] = None
    error: Optional[str] = None
    completed: bool = False

    # New fields for enhanced workflow
    intent_analysis: Optional[Dict[str, Any]] = None
    meta_architect_result: Optional[Dict[str, Any]] = None
    simple_strategy_result: Optional[Dict[str, Any]] = None
    summarizer_result: Optional[Dict[str, Any]] = None


@dataclass
class MiningResult:
    """Result of mining operation"""
    original_input: str
    final_requirements: List[str]
    demand_state: str
    smart_analysis: Dict[str, Any]
    clarification_history: List[Dict[str, str]]
    processing_time_ms: float


# Summarizer Service Models
class TaskCategory(Enum):
    """Task categories for multi-task processing"""
    ANSWER = "answer"
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"


class SummarizerStepStatus(Enum):
    """Status for each step in the summarizer workflow"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SummarizerState:
    """
    Top-Level State Object for LangGraph Summarizer

    This state object manages the entire request lifecycle from Mining to Planning to Execution,
    including all intermediate states and results from sub-services.
    """
    # Request identification
    session_id: str
    user_id: str
    task_id: str

    # Input data
    user_input: str
    input_data: Dict[str, Any]
    context: Dict[str, Any]

    # Workflow step tracking
    current_step: str = "initialization"
    step_status: Dict[str, SummarizerStepStatus] = None
    step_results: Dict[str, Any] = None

    # User interaction validation
    interaction_result: Optional[Any] = None  # InteractionResult from services_models
    should_proceed: bool = True

    # Mining service state and results
    mining_context: Optional[MiningContext] = None
    mining_result: Optional[MiningResult] = None
    mining_state: Optional[Dict[str, Any]] = None  # Store MiningService's LangGraph state

    # Workflow planning state and results
    planning_input: Optional[Dict[str, Any]] = None
    planning_result: Optional[Dict[str, Any]] = None
    planning_state: Optional[WorkflowPlanningState] = None  # Store WorkflowPlanningService's LangGraph state

    # Execution results
    workflow_execution_request: Optional[Any] = None  # WorkflowExecutionRequest
    execution_results: List[Dict[str, Any]] = None

    # Quality control results
    qc_results: Dict[str, Any] = None

    # Streaming and user feedback
    messages: Annotated[List[Dict], add_messages] = None
    streaming_updates: List[Dict[str, Any]] = None
    user_feedback: Optional[Dict[str, Any]] = None
    feedback_requested: bool = False

    # Error handling and completion
    error: Optional[str] = None
    warnings: List[str] = None
    completed: bool = False

    # Performance metrics
    start_time: Optional[datetime] = None
    step_timings: Dict[str, float] = None

    def __post_init__(self):
        if self.step_status is None:
            self.step_status = {}
        if self.step_results is None:
            self.step_results = {}
        if self.execution_results is None:
            self.execution_results = []
        if self.qc_results is None:
            self.qc_results = {}
        if self.messages is None:
            self.messages = []
        if self.streaming_updates is None:
            self.streaming_updates = []
        if self.warnings is None:
            self.warnings = []
        if self.step_timings is None:
            self.step_timings = {}

    def add_streaming_update(self, step: str, message: str, status: str = "in_progress",
                           result: Optional[Dict] = None, error: Optional[str] = None):
        """Add a streaming update to the state"""
        update = {
            "session_id": self.session_id,
            "step": step,
            "message": message,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result or {},
            "error": error
        }
        self.streaming_updates.append(update)

        # Update step status
        if status == "in_progress":
            self.step_status[step] = SummarizerStepStatus.IN_PROGRESS
        elif status == "completed":
            self.step_status[step] = SummarizerStepStatus.COMPLETED
        elif status == "failed":
            self.step_status[step] = SummarizerStepStatus.FAILED

    def get_step_status(self, step: str) -> SummarizerStepStatus:
        """Get the status of a specific step"""
        return self.step_status.get(step, SummarizerStepStatus.PENDING)

    def is_step_completed(self, step: str) -> bool:
        """Check if a step is completed"""
        return self.get_step_status(step) == SummarizerStepStatus.COMPLETED
