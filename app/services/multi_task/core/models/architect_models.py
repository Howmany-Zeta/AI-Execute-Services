"""
Architect Models

Data models for the Meta-Architect system, including framework definitions,
strategic plans, and blueprint construction results. Updated to support
recursive blueprint construction with tree-based strategic plans.
"""

from pydantic import field_validator, ConfigDict, BaseModel, Field, validator, model_validator, model_serializer
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class ProblemType(str, Enum):
    """Problem type enumeration for strategic planning."""
    EXTERNAL_MACRO_ENVIRONMENT_ANALYSIS = "external_macro_environment_analysis"
    INTERNAL_AND_EXTERNAL_ASSESSMENT = "internal_and_external_assessment"
    INDUSTRY_COMPETITION_ANALYSIS = "industry_competition_analysis"
    CUSTOMER_JOURNEY_MAPPING = "customer_journey_mapping"
    OPERATIONAL_EFFICIENCY_ANALYSIS = "operational_efficiency_analysis"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    PERFORMANCE_MEASUREMENT = "performance_measurement"
    PROBLEM_DIAGNOSIS = "problem_diagnosis"
    STAKEHOLDER_MANAGEMENT = "stakeholder_management"
    RISK_EVALUATION = "risk_evaluation"
    CUSTOMER_UNDERSTANDING = "customer_understanding"
    IMPROVEMENT_PLANNING = "improvement_planning"
    FULL_BUSINESS_STRATEGY_CREATION = "full_business_strategy_creation"
    MARKET_ENTRY_PLANNING = "market_entry_planning"
    DIGITAL_TRANSFORMATION = "digital_transformation"


class ComplexityLevel(str, Enum):
    """Complexity level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class FrameworkStrategy(str, Enum):
    """Strategy enumeration for framework application in recursive blueprint construction."""
    APPLY_FRAMEWORKS = "apply_frameworks"
    DECOMPOSITION = "decomposition"


# SQLAlchemy Models for Database Storage

class AnalyticalFramework(Base):
    """
    SQLAlchemy model for storing analytical frameworks in the database.
    """
    __tablename__ = 'analytical_frameworks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    framework_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    tags = Column(Text, nullable=False)  # Comma-separated tags
    components = Column(Text, nullable=False)  # Comma-separated components
    solves_problem_type = Column(String(255), nullable=False, index=True)
    complexity_level = Column(String(50), nullable=False)
    estimated_duration = Column(String(100), nullable=False)
    required_data_types = Column(JSON, nullable=False)  # List of required data types
    output_format = Column(String(100), nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    version = Column(String(50), default="1.0.0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AnalyticalFramework(name='{self.name}', problem_type='{self.solves_problem_type}')>"


class MetaFramework(Base):
    """
    SQLAlchemy model for storing meta-frameworks in the database.
    """
    __tablename__ = 'meta_frameworks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    meta_framework_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    component_frameworks = Column(JSON, nullable=False)  # List of framework names
    solves_problem_type = Column(String(255), nullable=False, index=True)
    complexity_level = Column(String(50), nullable=False)
    estimated_duration = Column(String(100), nullable=False)
    strategy = Column(String(50), nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    version = Column(String(50), default="1.0.0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<MetaFramework(name='{self.name}', strategy='{self.strategy}')>"


class StrategicPlanExecution(Base):
    """
    SQLAlchemy model for storing strategic plan execution history.
    Updated to support tree-based plans.
    """
    __tablename__ = 'strategic_plan_executions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), unique=True, nullable=False, index=True)
    problem_description = Column(Text, nullable=False)  # Updated to store problem description
    plan_tree_root = Column(JSON, nullable=False)  # Complete strategic plan tree
    confidence_score = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)

    # Execution metadata
    total_estimated_duration = Column(String(100), nullable=False)
    overall_complexity = Column(String(50), nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    architect_version = Column(String(50), nullable=False)

    # Context
    user_id = Column(String(255), nullable=True, index=True)
    task_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<StrategicPlanExecution(problem='{self.problem_description[:50]}...', confidence={self.confidence_score})>"


# Pydantic Models for API and Business Logic

class FrameworkSelectionCriteria(BaseModel):
    """
    Criteria for framework selection by the Meta-Architect.
    """
    problem_type: str = Field(..., description="Type of problem to solve")
    complexity_preference: Optional[ComplexityLevel] = Field(None, description="Preferred complexity level")
    time_constraint: Optional[str] = Field(None, description="Time constraint for analysis")
    available_data_types: List[str] = Field(default_factory=list, description="Available data types")
    domain_context: Optional[str] = Field(None, description="Domain context for specialization")
    quality_requirements: Dict[str, Any] = Field(default_factory=dict, description="Quality requirements")


class FrameworkMatchResult(BaseModel):
    """
    Result of framework matching operation.
    """
    framework_name: str = Field(..., description="Name of the matched framework")
    match_score: float = Field(..., description="Match score (0.0 to 1.0)")
    match_reasons: List[str] = Field(..., description="Reasons for the match")
    estimated_duration: str = Field(..., description="Estimated duration for this framework")
    complexity_level: ComplexityLevel = Field(..., description="Complexity level")
    required_data_types: List[str] = Field(..., description="Required data types")

    @field_validator('match_score')
    @classmethod
    def validate_match_score(cls, v):
        """Validate match score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Match score must be between 0.0 and 1.0")
        return v


class FrameworkRecommendation(BaseModel):
    """
    Model for framework recommendations in recursive blueprint construction.
    """
    framework_name: str = Field(..., description="Name of the recommended framework")
    rationale: str = Field(..., description="Rationale for recommending this framework")
    application_focus: str = Field(..., description="Specific focus area for framework application")
    expected_outcome: str = Field(..., description="Expected outcome from applying this framework")
    estimated_duration: str = Field(..., description="Estimated duration for framework application")

    # Optional fields for enhanced recommendations
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites for using this framework")
    success_criteria: List[str] = Field(default_factory=list, description="Success criteria for framework application")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors to consider")


class StrategicPlan(BaseModel):
    """
    Pydantic model representing a strategic plan node in the recursive tree structure.
    Updated to support recursive decomposition and tree-based planning.
    """
    problem_description: str = Field(..., description="Description of the problem this plan addresses")
    strategy: FrameworkStrategy = Field(..., description="Strategy used for this plan node")
    reasoning: Optional[str] = Field(None, description="Reasoning for the chosen strategy")

    # Framework application (for leaf nodes)
    selected_frameworks: Optional[List[FrameworkRecommendation]] = Field(
        default_factory=list,
        description="Frameworks selected for direct application"
    )

    # Decomposition (for branch nodes)
    sub_plans: Optional[List['StrategicPlan']] = Field(
        None,
        description="Sub-plans for decomposition strategy"
    )

    # Execution metadata
    estimated_duration: Optional[str] = Field(None, description="Estimated duration for this plan")
    complexity_level: Optional[ComplexityLevel] = Field(None, description="Complexity level of this plan")
    confidence_score: Optional[float] = Field(None, description="Confidence score for this plan")

    # Legacy support for backward compatibility
    phases: Optional[List[Dict[str, Any]]] = Field(None, description="Legacy phases (for backward compatibility)")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Dependencies for this plan")
    risk_factors: Optional[List[str]] = Field(default_factory=list, description="Risk factors")
    success_criteria: Optional[List[str]] = Field(default_factory=list, description="Success criteria")
    resource_requirements: Optional[List[str]] = Field(default_factory=list, description="Resource requirements")
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


# Update forward reference for recursive model
StrategicPlan.model_rebuild()


class BlueprintConstructionRequest(BaseModel):
    """
    Request model for recursive blueprint construction.
    """
    problem_description: str = Field(..., description="Description of the problem to solve")
    domain: str = Field(default="business", description="Problem domain")
    complexity: str = Field(default="medium", description="Problem complexity level")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Additional requirements")

    # Context and constraints
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for decision making")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Constraints for framework selection")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

    # Optional overrides
    force_frameworks: Optional[List[str]] = Field(None, description="Force specific frameworks to be used")
    exclude_frameworks: Optional[List[str]] = Field(None, description="Exclude specific frameworks")
    max_complexity: Optional[ComplexityLevel] = Field(None, description="Maximum allowed complexity")
    max_duration: Optional[str] = Field(None, description="Maximum allowed duration")
    max_recursion_depth: Optional[int] = Field(3, description="Maximum recursion depth for decomposition")


class BlueprintConstructionResult(BaseModel):
    """
    Result model for recursive blueprint construction operations.
    Updated to support tree-based strategic plans.
    """
    # Tree-based plan (new structure)
    plan_tree_root: Optional[StrategicPlan] = Field(None, description="Root node of the strategic plan tree")

    # Legacy support (for backward compatibility)
    strategic_plan: Optional[StrategicPlan] = Field(None, description="Legacy strategic plan (for backward compatibility)")
    framework_recommendations: Optional[List[FrameworkRecommendation]] = Field(
        default_factory=list,
        description="Legacy framework recommendations"
    )

    # Result metadata
    total_estimated_duration: str = Field(..., description="Total estimated duration")
    overall_complexity: str = Field(..., description="Overall complexity level")
    confidence_score: float = Field(..., description="Confidence in the blueprint (0.0 to 1.0)")
    reasoning: str = Field(..., description="Detailed reasoning for the blueprint construction")

    # Alternative options
    alternative_plans: List[StrategicPlan] = Field(default_factory=list, description="Alternative strategic plans")

    # Execution metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    architect_version: str = Field(..., description="Version of the Meta-Architect used")
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique execution identifier")

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v

    @model_validator(mode='after')
    def validate_plan_exists(self) -> 'BlueprintConstructionResult':
        """Ensures that either 'plan_tree_root' or 'strategic_plan' is provided."""
        # Use self to access the model's fields
        plan_tree_root = self.plan_tree_root
        strategic_plan = self.strategic_plan

        if not plan_tree_root and not strategic_plan:
            raise ValueError("Either 'plan_tree_root' or 'strategic_plan' must be provided.")

        # Always return the self instance at the end
        return self


class ArchitectMetrics(BaseModel):
    """
    Metrics model for Meta-Architect performance tracking.
    Updated to include recursive blueprint construction metrics.
    """
    total_blueprints_created: int = Field(default=0, description="Total number of blueprints created")
    successful_blueprints: int = Field(default=0, description="Number of successful blueprints")
    failed_blueprints: int = Field(default=0, description="Number of failed blueprints")
    average_confidence_score: float = Field(default=0.0, description="Average confidence score")
    average_processing_time_ms: float = Field(default=0.0, description="Average processing time in milliseconds")

    # Recursive construction metrics
    total_recursive_constructions: int = Field(default=0, description="Total recursive constructions")
    average_tree_depth: float = Field(default=0.0, description="Average tree depth in recursive constructions")
    average_tree_breadth: float = Field(default=0.0, description="Average tree breadth in recursive constructions")
    decomposition_success_rate: float = Field(default=0.0, description="Success rate of decomposition strategy")

    # Framework usage statistics
    framework_usage_count: Dict[str, int] = Field(default_factory=dict, description="Usage count per framework")
    problem_type_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of problem types")
    complexity_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of complexity levels")
    strategy_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of strategies used")

    # Quality metrics
    high_confidence_blueprints: int = Field(default=0, description="Number of high confidence blueprints (>0.8)")
    low_confidence_blueprints: int = Field(default=0, description="Number of low confidence blueprints (<0.6)")

    # Temporal metrics
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update timestamp")
    model_config = ConfigDict()

    @model_serializer
    def serialize_model(self):
        """Custom serializer for datetime fields."""
        data = self.__dict__.copy()
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


class DecompositionResult(BaseModel):
    """
    Model for decomposition analysis results in recursive blueprint construction.
    """
    should_decompose: bool = Field(..., description="Whether the problem should be decomposed")
    rationale: str = Field(..., description="Rationale for decomposition decision")
    sub_problems: List[str] = Field(default_factory=list, description="List of sub-problems if decomposing")
    recommended_frameworks: List[FrameworkRecommendation] = Field(
        default_factory=list,
        description="Frameworks recommended for direct application"
    )
    estimated_complexity: ComplexityLevel = Field(..., description="Estimated complexity of the problem")
    confidence_score: float = Field(..., description="Confidence in the decomposition decision")

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class TreeAnalysisResult(BaseModel):
    """
    Model for analyzing strategic plan trees.
    """
    total_nodes: int = Field(..., description="Total number of nodes in the tree")
    max_depth: int = Field(..., description="Maximum depth of the tree")
    leaf_nodes: int = Field(..., description="Number of leaf nodes")
    branch_nodes: int = Field(..., description="Number of branch nodes")
    total_frameworks: int = Field(..., description="Total number of frameworks across all nodes")
    estimated_total_duration: str = Field(..., description="Estimated total duration for the entire tree")
    overall_confidence: float = Field(..., description="Overall confidence score for the tree")
    complexity_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of complexity levels across nodes"
    )

    @field_validator('overall_confidence')
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v
