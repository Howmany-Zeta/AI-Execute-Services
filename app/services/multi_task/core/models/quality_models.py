"""
Quality Models

Data models for quality control and validation in the multi-task service.
"""

from pydantic import ConfigDict, BaseModel, Field, field_serializer
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass


class QualityCheckType(Enum):
    """Quality check type enumeration."""
    VALIDATION = "validation"
    EXAMINATION = "examination"
    ACCEPTANCE = "acceptance"
    VERIFICATION = "verification"


class QualityLevel(Enum):
    """Quality level enumeration."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


class TaskCategory(Enum):
    """Task category for quality control."""
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"


@dataclass
class QualityCheck:
    """Quality check configuration."""
    check_id: str
    check_type: QualityCheckType
    task_category: 'TaskCategory'
    quality_level: QualityLevel
    criteria: Dict[str, Any]
    weight: float = 1.0
    required: bool = True
    timeout_seconds: int = 60


@dataclass
class QualityResult:
    """Quality check result."""
    check_id: str
    passed: bool
    score: float
    details: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]
    execution_time: timedelta
    checked_at: datetime


class QualityProfile(BaseModel):
    """Quality profile configuration."""
    profile_id: str = Field(..., description="Unique identifier for the quality profile")
    name: str = Field(..., description="Human-readable name for the profile")
    description: Optional[str] = Field(None, description="Description of the quality profile")

    # Quality settings
    quality_level: QualityLevel = Field(default=QualityLevel.STANDARD, description="Overall quality level")
    minimum_score: float = Field(default=0.8, description="Minimum quality score required")

    # Check configuration
    checks: List[Dict[str, Any]] = Field(default_factory=list, description="Quality checks to perform")
    check_timeout_seconds: int = Field(default=30, description="Default timeout for quality checks")

    # Category-specific settings
    category_settings: Dict[TaskCategory, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Category-specific quality settings"
    )

    # Validation rules
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    required_fields: List[str] = Field(default_factory=list, description="Required result fields")
    field_types: Dict[str, str] = Field(default_factory=dict, description="Expected field types")

    # Thresholds
    warning_threshold: float = Field(default=0.7, description="Warning threshold for quality scores")
    critical_threshold: float = Field(default=0.5, description="Critical threshold for quality scores")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation timestamp")
    created_by: str = Field(..., description="ID of the user who created the profile")
    version: str = Field(default="1.0.0", description="Profile version")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class QualityAssessment(BaseModel):
    """Quality assessment result."""
    assessment_id: str = Field(..., description="Unique identifier for the assessment")
    execution_id: str = Field(..., description="ID of the execution being assessed")
    profile_id: str = Field(..., description="ID of the quality profile used")

    # Assessment results
    overall_score: float = Field(..., description="Overall quality score (0.0 to 1.0)")
    passed: bool = Field(..., description="Whether the assessment passed")
    check_results: List[Dict[str, Any]] = Field(default_factory=list, description="Individual check results")

    # Categories assessed
    category: TaskCategory = Field(..., description="Task category assessed")
    quality_level: QualityLevel = Field(..., description="Quality level used")

    # Feedback and recommendations
    feedback: str = Field(..., description="Quality assessment feedback")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    # Performance metrics
    assessment_time_seconds: float = Field(..., description="Time taken for assessment")
    checks_performed: int = Field(..., description="Number of checks performed")
    checks_passed: int = Field(..., description="Number of checks passed")

    # Timestamps
    started_at: datetime = Field(..., description="Assessment start timestamp")
    completed_at: datetime = Field(..., description="Assessment completion timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('started_at', 'completed_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class ValidationCriteria(BaseModel):
    """Validation criteria configuration."""
    criteria_id: str = Field(..., description="Unique identifier for the criteria")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Description of the criteria")

    # Basic validation
    require_result: bool = Field(default=True, description="Whether result is required")
    require_success: bool = Field(default=True, description="Whether success flag must be true")

    # Field validation
    required_fields: List[str] = Field(default_factory=list, description="Required fields in result")
    optional_fields: List[str] = Field(default_factory=list, description="Optional fields in result")
    field_types: Dict[str, str] = Field(default_factory=dict, description="Expected field types")
    field_patterns: Dict[str, str] = Field(default_factory=dict, description="Regex patterns for fields")

    # Value validation
    min_values: Dict[str, float] = Field(default_factory=dict, description="Minimum values for numeric fields")
    max_values: Dict[str, float] = Field(default_factory=dict, description="Maximum values for numeric fields")
    allowed_values: Dict[str, List[Any]] = Field(default_factory=dict, description="Allowed values for fields")

    # Quality thresholds
    min_quality_score: Optional[float] = Field(None, description="Minimum quality score")
    min_confidence_score: Optional[float] = Field(None, description="Minimum confidence score")

    # Custom validation
    custom_validators: List[str] = Field(default_factory=list, description="Custom validator function names")
    validation_scripts: Dict[str, str] = Field(default_factory=dict, description="Custom validation scripts")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Criteria creation timestamp")
    version: str = Field(default="1.0.0", description="Criteria version")
    model_config = ConfigDict()

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()


class QualityMetrics(BaseModel):
    """Quality metrics summary."""
    metrics_id: str = Field(..., description="Unique identifier for the metrics")
    time_period_start: datetime = Field(..., description="Start of the metrics period")
    time_period_end: datetime = Field(..., description="End of the metrics period")

    # Overall metrics
    total_assessments: int = Field(default=0, description="Total number of assessments")
    passed_assessments: int = Field(default=0, description="Number of passed assessments")
    failed_assessments: int = Field(default=0, description="Number of failed assessments")
    average_score: float = Field(default=0.0, description="Average quality score")

    # Category breakdown
    category_metrics: Dict[TaskCategory, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metrics by task category"
    )

    # Quality level breakdown
    level_metrics: Dict[QualityLevel, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Metrics by quality level"
    )

    # Trend analysis
    score_trend: List[float] = Field(default_factory=list, description="Quality score trend over time")
    pass_rate_trend: List[float] = Field(default_factory=list, description="Pass rate trend over time")

    # Performance metrics
    average_assessment_time: float = Field(default=0.0, description="Average assessment time in seconds")
    total_assessment_time: float = Field(default=0.0, description="Total assessment time in seconds")

    # Top issues
    common_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Most common failure reasons")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas needing improvement")

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Metrics generation timestamp")
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('time_period_start', 'time_period_end', 'generated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime fields to ISO format."""
        return value.isoformat()
