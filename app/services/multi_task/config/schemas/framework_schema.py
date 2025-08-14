"""
Framework Schema

Defines the Pydantic models for validating framework.yaml configuration.
This ensures that all framework definitions follow the correct structure
and contain all required fields.
"""

from pydantic import field_validator, ConfigDict, BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum


class ComplexityLevel(str, Enum):
    """Framework complexity level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class OutputFormat(str, Enum):
    """Framework output format enumeration."""
    STRUCTURED_ANALYSIS = "structured_analysis"
    MATRIX_ANALYSIS = "matrix_analysis"
    FORCE_ANALYSIS = "force_analysis"
    JOURNEY_MAP = "journey_map"
    VALUE_CHAIN_DIAGRAM = "value_chain_diagram"
    SCORECARD = "scorecard"
    CAUSE_TREE = "cause_tree"
    STAKEHOLDER_MAP = "stakeholder_map"
    RISK_MATRIX = "risk_matrix"
    PERSONA_PROFILES = "persona_profiles"
    GAP_ANALYSIS_REPORT = "gap_analysis_report"
    # New output formats for enhanced frameworks
    DESIGN_SOLUTION = "design_solution"
    VALIDATION_REPORT = "validation_report"
    OKR_FRAMEWORK = "okr_framework"
    IMPROVEMENT_PLAN = "improvement_plan"
    FINANCIAL_ANALYSIS_REPORT = "financial_analysis_report"
    DATA_INSIGHTS_REPORT = "data_insights_report"
    CHANGE_MANAGEMENT_PLAN = "change_management_plan"
    SUPPLY_CHAIN_REPORT = "supply_chain_report"
    TECHNOLOGY_ASSESSMENT_REPORT = "technology_assessment_report"
    COMPETITIVE_INTELLIGENCE_REPORT = "competitive_intelligence_report"
    PROCESS_OPTIMIZATION_PLAN = "process_optimization_plan"


class FrameworkStrategy(str, Enum):
    """Strategy for handling frameworks."""
    APPLY_FRAMEWORKS = "apply_frameworks"
    DECOMPOSITION = "decomposition"


class FrameworkModel(BaseModel):
    """
    Model representing a single analytical framework.
    """
    name: str = Field(..., description="Name of the framework")
    description: str = Field(..., description="Detailed description of the framework")
    tags: str = Field(..., description="Comma-separated tags for categorization and search")
    components: str = Field(..., description="Comma-separated list of framework components")
    solves_problem_type: str = Field(..., description="Type of problem this framework solves")
    complexity_level: ComplexityLevel = Field(..., description="Complexity level of the framework")
    estimated_duration: str = Field(..., description="Estimated time to complete analysis")
    required_data_types: List[str] = Field(..., description="Types of data required for this framework")
    output_format: OutputFormat = Field(..., description="Expected output format")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate that tags are properly formatted."""
        if not v or not v.strip():
            raise ValueError("Tags cannot be empty")
        # Ensure no empty tags after splitting
        tags = [tag.strip() for tag in v.split(',')]
        if any(not tag for tag in tags):
            raise ValueError("Tags cannot contain empty values")
        return v

    @field_validator('components')
    @classmethod
    def validate_components(cls, v):
        """Validate that components are properly formatted."""
        if not v or not v.strip():
            raise ValueError("Components cannot be empty")
        # Ensure no empty components after splitting
        components = [comp.strip() for comp in v.split(',')]
        if any(not comp for comp in components):
            raise ValueError("Components cannot contain empty values")
        return v

    @field_validator('required_data_types')
    @classmethod
    def validate_required_data_types(cls, v):
        """Validate that required data types are not empty."""
        if not v:
            raise ValueError("Required data types cannot be empty")
        return v

    def get_tags_list(self) -> List[str]:
        """Get tags as a list."""
        return [tag.strip() for tag in self.tags.split(',')]

    def get_components_list(self) -> List[str]:
        """Get components as a list."""
        return [comp.strip() for comp in self.components.split(',')]


class MetaFrameworkModel(BaseModel):
    """
    Model representing a meta-framework that combines multiple frameworks.
    """
    name: str = Field(..., description="Name of the meta-framework")
    description: str = Field(..., description="Description of the meta-framework")
    component_frameworks: List[str] = Field(..., description="List of framework names that compose this meta-framework")
    solves_problem_type: str = Field(..., description="Type of problem this meta-framework solves")
    complexity_level: ComplexityLevel = Field(..., description="Complexity level of the meta-framework")
    estimated_duration: str = Field(..., description="Estimated time to complete analysis")
    strategy: FrameworkStrategy = Field(..., description="Strategy for handling this meta-framework")

    @field_validator('component_frameworks')
    @classmethod
    def validate_component_frameworks(cls, v):
        """Validate that component frameworks are not empty."""
        if not v:
            raise ValueError("Component frameworks cannot be empty")
        if len(v) < 2:
            raise ValueError("Meta-framework must contain at least 2 component frameworks")
        return v


class FrameworkConfigModel(BaseModel):
    """
    Model representing the complete framework configuration.
    """
    frameworks: List[FrameworkModel] = Field(..., description="List of available frameworks")
    meta_frameworks: Optional[List[MetaFrameworkModel]] = Field(default_factory=list, description="List of meta-frameworks")

    @field_validator('frameworks')
    @classmethod
    def validate_frameworks(cls, v):
        """Validate that frameworks list is not empty and names are unique."""
        if not v:
            raise ValueError("Frameworks list cannot be empty")

        # Check for duplicate names
        names = [framework.name for framework in v]
        if len(names) != len(set(names)):
            raise ValueError("Framework names must be unique")

        return v

    @model_validator(mode='after')
    def validate_meta_frameworks(self) -> 'FrameworkConfigModel':
        """Validate that meta-frameworks and their component frameworks are valid."""
        # Use self to access the model's fields
        meta_frameworks = self.meta_frameworks
        frameworks = self.frameworks

        if not meta_frameworks or not frameworks:
            return self

        # Get available framework names
        available_names = {framework.name for framework in frameworks}

        # Check meta-framework names are unique
        meta_names = [meta.name for meta in meta_frameworks]
        if len(meta_names) != len(set(meta_names)):
            raise ValueError("Meta-framework names must be unique")

        # Check that component frameworks exist
        for meta_framework in meta_frameworks:
            for component_name in meta_framework.component_frameworks:
                if component_name not in available_names:
                    raise ValueError(f"Meta-framework '{meta_framework.name}' references an unknown component framework '{component_name}'")

        # Always return the self instance at the end
        return self

    def get_framework_by_name(self, name: str) -> Optional[FrameworkModel]:
        """Get a framework by name."""
        for framework in self.frameworks:
            if framework.name == name:
                return framework
        return None

    def get_meta_framework_by_name(self, name: str) -> Optional[MetaFrameworkModel]:
        """Get a meta-framework by name."""
        for meta_framework in self.meta_frameworks:
            if meta_framework.name == name:
                return meta_framework
        return None

    def get_frameworks_by_problem_type(self, problem_type: str) -> List[FrameworkModel]:
        """Get frameworks that solve a specific problem type."""
        return [framework for framework in self.frameworks if framework.solves_problem_type == problem_type]

    def get_frameworks_by_tag(self, tag: str) -> List[FrameworkModel]:
        """Get frameworks that contain a specific tag."""
        return [framework for framework in self.frameworks if tag in framework.get_tags_list()]

    def get_frameworks_by_complexity(self, complexity: ComplexityLevel) -> List[FrameworkModel]:
        """Get frameworks by complexity level."""
        return [framework for framework in self.frameworks if framework.complexity_level == complexity]


class StrategicPlan(BaseModel):
    """
    Model representing a strategic plan created by the Meta-Architect.
    """
    problem_type: str = Field(..., description="Type of problem being solved")
    strategy: FrameworkStrategy = Field(..., description="Strategy used for this plan")
    frameworks: Optional[List[str]] = Field(None, description="List of framework names for direct application")
    sub_plans: Optional[List['StrategicPlan']] = Field(None, description="Sub-plans for decomposition strategy")
    estimated_duration: Optional[str] = Field(None, description="Estimated duration for this plan")
    complexity_level: Optional[ComplexityLevel] = Field(None, description="Complexity level of this plan")
    reasoning: Optional[str] = Field(None, description="Reasoning for framework selection")
    model_config = ConfigDict(arbitrary_types_allowed=True)


# Update forward reference
StrategicPlan.model_rebuild()


class BlueprintConstructionResult(BaseModel):
    """
    Result model for blueprint construction operations.
    """
    strategic_plan: StrategicPlan = Field(..., description="The constructed strategic plan")
    selected_frameworks: List[str] = Field(..., description="All frameworks selected in the plan")
    total_estimated_duration: str = Field(..., description="Total estimated duration")
    overall_complexity: ComplexityLevel = Field(..., description="Overall complexity level")
    confidence_score: float = Field(..., description="Confidence in the blueprint (0.0 to 1.0)")
    reasoning: str = Field(..., description="Detailed reasoning for the blueprint construction")

    # Metadata
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    architect_version: str = Field(..., description="Version of the Meta-Architect used")

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v
