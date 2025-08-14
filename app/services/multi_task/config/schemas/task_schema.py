"""
Task Configuration Schema

Pydantic schema definitions for task configuration validation.
"""

from pydantic import field_validator, ConfigDict, BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class TaskType(str, Enum):
    """Valid task types."""
    FAST = "fast"
    HEAVY = "heavy"


class ConditionSchema(BaseModel):
    """Schema for task conditions."""

    if_clause: str = Field(..., alias="if", description="Condition expression")
    then_clause: str = Field(..., alias="then", description="Action to take if condition is true")

    @field_validator('if_clause')
    @classmethod
    def validate_condition_expression(cls, v):
        """Validate the condition expression."""
        if not v.strip():
            raise ValueError("Condition expression cannot be empty")

        # Check for valid condition patterns
        valid_patterns = [
            r'data\.\w+', r'input\.\w+', r'resource\.\w+', r'model\.\w+',
            r'query\.\w+', r'task\.\w+', r'\w+\s*(==|!=|>|<|>=|<=)\s*',
            r'\w+\s+in\s+', r'\w+\.contains\(', r'\w+\.includes\('
        ]

        import re
        has_valid_pattern = any(re.search(pattern, v) for pattern in valid_patterns)

        if not has_valid_pattern:
            raise ValueError(f"Invalid condition expression pattern: {v}")

        return v
    model_config = ConfigDict(populate_by_name=True)


class OperationConditionSchema(BaseModel):
    """Schema for operation-level conditions."""

    conditions: List[ConditionSchema] = Field(..., description="List of conditions for this operation")

    @field_validator('conditions')
    @classmethod
    def validate_conditions_list(cls, v):
        """Validate the conditions list."""
        if not v:
            raise ValueError("Conditions list cannot be empty")
        return v


class ToolOperationSchema(BaseModel):
    """Schema for tool operations."""

    operation_name: str = Field(..., description="Name of the operation")
    conditions: Optional[OperationConditionSchema] = Field(None, description="Conditions for this operation")

    @field_validator('operation_name')
    @classmethod
    def validate_operation_name(cls, v):
        """Validate the operation name."""
        if not v.strip():
            raise ValueError("Operation name cannot be empty")

        # Check for valid operation name pattern
        import re
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError(f"Invalid operation name format: {v}")

        return v.strip()


class ToolConfigSchema(BaseModel):
    """Schema for tool configuration."""

    operations: List[Union[str, Dict[str, OperationConditionSchema]]] = Field(
        ..., description="List of operations for this tool"
    )

    @field_validator('operations')
    @classmethod
    def validate_operations(cls, v):
        """Validate the operations list."""
        if not isinstance(v, list):
            raise ValueError("Operations must be a list")

        if not v:
            raise ValueError("Operations list cannot be empty")

        for operation in v:
            if isinstance(operation, str):
                # Simple operation name
                if not operation.strip():
                    raise ValueError("Operation name cannot be empty")
            elif isinstance(operation, dict):
                # Operation with conditions
                if not operation:
                    raise ValueError("Operation dictionary cannot be empty")
            else:
                raise ValueError(f"Invalid operation type: {type(operation)}")

        return v


class TaskConfigSchema(BaseModel):
    """Schema for individual task configuration."""

    description: str = Field(..., min_length=20, description="Task description")
    agent: str = Field(..., description="Agent assigned to this task")
    expected_output: str = Field(..., min_length=10, description="Expected output description")
    task_type: TaskType = Field(default=TaskType.FAST, description="Task execution type")
    tools: Optional[Dict[str, ToolConfigSchema]] = Field(None, description="Tools configuration")
    conditions: Optional[List[ConditionSchema]] = Field(None, description="Task-level conditions")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate the task description."""
        if not v.strip():
            raise ValueError("Description cannot be empty")

        # Check for action words
        action_words = ['analyze', 'create', 'generate', 'process', 'collect', 'extract', 'validate', 'review']
        if not any(word in v.lower() for word in action_words):
            raise ValueError("Description should contain action words")

        return v.strip()

    @field_validator('agent')
    @classmethod
    def validate_agent(cls, v):
        """Validate the agent name."""
        if not v.strip():
            raise ValueError("Agent cannot be empty")

        # Check agent naming convention
        import re
        if not re.match(r'^[a-z_]+$', v):
            raise ValueError(f"Agent name should use lowercase with underscores: {v}")

        return v.strip()

    @field_validator('expected_output')
    @classmethod
    def validate_expected_output(cls, v):
        """Validate the expected output."""
        if not v.strip():
            raise ValueError("Expected output cannot be empty")

        # Check for format specifications
        format_keywords = ['json', 'text', 'list', 'dictionary', 'format']
        if not any(keyword in v.lower() for keyword in format_keywords):
            raise ValueError("Expected output should specify the output format")

        return v.strip()

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v):
        """Validate the tools configuration."""
        if v is None:
            return v

        valid_tools = {
            'chart', 'classifier', 'image', 'office', 'pandas',
            'report', 'research', 'scraper', 'stats', 'search_api'
        }

        for tool_name in v.keys():
            if tool_name not in valid_tools:
                raise ValueError(f"Unknown tool: {tool_name}. Valid tools: {valid_tools}")

        return v
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SystemTasksSchema(BaseModel):
    """Schema for system tasks section."""

    parse_intent: TaskConfigSchema = Field(..., description="Intent parsing task")
    breakdown_subTask: TaskConfigSchema = Field(..., description="Sub-task breakdown task")
    plan_sequence: TaskConfigSchema = Field(..., description="Task sequence planning task")
    examination: TaskConfigSchema = Field(..., description="Result examination task")
    acceptance: TaskConfigSchema = Field(..., description="Result acceptance task")

    @field_validator('examination')
    @classmethod
    def validate_examination_task(cls, v):
        """Validate the examination task."""
        # Should have research tools
        if not v.tools or 'research' not in v.tools:
            raise ValueError("Examination task should use research tools")

        # Should have conditions
        if not v.conditions:
            raise ValueError("Examination task should have conditions")

        return v

    @field_validator('acceptance')
    @classmethod
    def validate_acceptance_task(cls, v):
        """Validate the acceptance task."""
        # Should have research tools
        if not v.tools or 'research' not in v.tools:
            raise ValueError("Acceptance task should use research tools")

        # Should have conditions
        if not v.conditions:
            raise ValueError("Acceptance task should have conditions")

        return v
    model_config = ConfigDict(extra="allow")


class SubTasksSchema(BaseModel):
    """Schema for sub-tasks section."""

    # Answer category tasks
    answer_discuss: Optional[TaskConfigSchema] = Field(None, description="Discussion facilitation task")
    answer_conclusion: Optional[TaskConfigSchema] = Field(None, description="Conclusion writing task")
    answer_questions: Optional[TaskConfigSchema] = Field(None, description="Question answering task")
    answer_brainstorming: Optional[TaskConfigSchema] = Field(None, description="Brainstorming task")

    # Collect category tasks
    collect_scrape: Optional[TaskConfigSchema] = Field(None, description="Web scraping task")
    collect_search: Optional[TaskConfigSchema] = Field(None, description="API search task")
    collect_internalResources: Optional[TaskConfigSchema] = Field(None, description="Internal data collection task")
    collect_externalResources: Optional[TaskConfigSchema] = Field(None, description="External data collection task")

    # Process category tasks
    process_dataCleaning: Optional[TaskConfigSchema] = Field(None, description="Data cleaning task")
    process_dataNormalization: Optional[TaskConfigSchema] = Field(None, description="Data normalization task")
    process_dataStatistics: Optional[TaskConfigSchema] = Field(None, description="Statistical analysis task")
    process_dataModeling: Optional[TaskConfigSchema] = Field(None, description="Data modeling task")
    process_dataIntegration: Optional[TaskConfigSchema] = Field(None, description="Data integration task")
    process_dataCompression: Optional[TaskConfigSchema] = Field(None, description="Data compression task")
    process_dataEnrichment: Optional[TaskConfigSchema] = Field(None, description="Data enrichment task")
    process_dataTransformation: Optional[TaskConfigSchema] = Field(None, description="Data transformation task")
    process_dataFiltering: Optional[TaskConfigSchema] = Field(None, description="Data filtering task")
    process_dataFormatting: Optional[TaskConfigSchema] = Field(None, description="Data formatting task")
    process_dataSorting: Optional[TaskConfigSchema] = Field(None, description="Data sorting task")
    process_documentFormatConversion: Optional[TaskConfigSchema] = Field(None, description="Document conversion task")
    process_documentCleaning: Optional[TaskConfigSchema] = Field(None, description="Document cleaning task")
    process_documentSegmentation: Optional[TaskConfigSchema] = Field(None, description="Document segmentation task")
    process_textProcessing: Optional[TaskConfigSchema] = Field(None, description="Text processing task")
    process_dataExtraction: Optional[TaskConfigSchema] = Field(None, description="Data extraction task")
    process_imageExtraction: Optional[TaskConfigSchema] = Field(None, description="Image extraction task")
    process_imageProcessing: Optional[TaskConfigSchema] = Field(None, description="Image processing task")

    # Analyze category tasks
    analyze_dataoutcome: Optional[TaskConfigSchema] = Field(None, description="Data outcome analysis task")
    analyze_context: Optional[TaskConfigSchema] = Field(None, description="Context analysis task")
    analyze_trend: Optional[TaskConfigSchema] = Field(None, description="Trend analysis task")
    analyze_pattern: Optional[TaskConfigSchema] = Field(None, description="Pattern analysis task")
    analyze_comparison: Optional[TaskConfigSchema] = Field(None, description="Comparison analysis task")
    analyze_correlation: Optional[TaskConfigSchema] = Field(None, description="Correlation analysis task")
    analyze_sentiment: Optional[TaskConfigSchema] = Field(None, description="Sentiment analysis task")
    analyze_classification: Optional[TaskConfigSchema] = Field(None, description="Classification analysis task")

    # Generate category tasks
    generate_report: Optional[TaskConfigSchema] = Field(None, description="Report generation task")
    generate_summary: Optional[TaskConfigSchema] = Field(None, description="Summary generation task")
    generate_visualization: Optional[TaskConfigSchema] = Field(None, description="Visualization generation task")
    generate_recommendation: Optional[TaskConfigSchema] = Field(None, description="Recommendation generation task")
    generate_prediction: Optional[TaskConfigSchema] = Field(None, description="Prediction generation task")
    generate_insight: Optional[TaskConfigSchema] = Field(None, description="Insight generation task")
    generate_content: Optional[TaskConfigSchema] = Field(None, description="Content generation task")
    model_config = ConfigDict(extra="allow")


class TaskSchema(BaseModel):
    """Schema for the complete tasks.yaml configuration."""

    system_tasks: SystemTasksSchema = Field(..., description="System tasks configuration")
    sub_tasks: SubTasksSchema = Field(..., description="Sub-tasks configuration")

    @field_validator('system_tasks')
    @classmethod
    def validate_system_tasks(cls, v):
        """Validate system tasks."""
        if not v:
            raise ValueError("System tasks must be defined")
        return v

    @field_validator('sub_tasks')
    @classmethod
    def validate_sub_tasks(cls, v):
        """Validate sub-tasks."""
        # Check category coverage
        categories = ['answer', 'collect', 'process', 'analyze', 'generate']

        for category in categories:
            category_tasks = [
                field_name for field_name in v.__fields_set__
                if field_name.startswith(f"{category}_")
            ]

            if not category_tasks:
                raise ValueError(f"No sub-tasks found for category: {category}")

        return v
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TaskValidationSchema(BaseModel):
    """Schema for task validation results."""

    is_valid: bool = Field(..., description="Whether the configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    system_tasks_count: int = Field(..., description="Number of system tasks")
    sub_tasks_count: int = Field(..., description="Number of sub-tasks")
    category_coverage: Dict[str, int] = Field(default_factory=dict, description="Tasks per category")
    tool_usage: Dict[str, int] = Field(default_factory=dict, description="Tool usage statistics")
    model_config = ConfigDict(extra="allow")


class TaskConsistencySchema(BaseModel):
    """Schema for task consistency validation."""

    agent_references: Dict[str, List[str]] = Field(default_factory=dict, description="Agent usage by tasks")
    missing_agents: List[str] = Field(default_factory=list, description="Referenced but undefined agents")
    unused_agents: List[str] = Field(default_factory=list, description="Defined but unused agents")
    tool_distribution: Dict[str, List[str]] = Field(default_factory=dict, description="Tool usage by tasks")
    unused_tools: List[str] = Field(default_factory=list, description="Available but unused tools")
    category_gaps: List[str] = Field(default_factory=list, description="Categories with insufficient tasks")
    model_config = ConfigDict(extra="allow")
