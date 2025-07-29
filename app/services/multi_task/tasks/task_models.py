"""
Task Definition Models

This module serves as the single source of truth for task-related data structures.
It contains only data models and enums, with no business logic.

Following the Single Responsibility Principle (SRP), this module is responsible
solely for defining the structure and validation of task configurations.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser
from langchain.prompts import PromptTemplate


class TaskCategory(str, Enum):
    """
    Task category enumeration defining the five main intent categories.

    These categories represent the fundamental types of operations
    that the multi-task system can perform.
    """
    ANSWER = "answer"
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"


class TaskType(str, Enum):
    """
    Task execution type enumeration.

    Defines the computational complexity and resource requirements.
    """
    FAST = "fast"    # Lightweight tasks, quick execution
    HEAVY = "heavy"  # Resource-intensive tasks, longer execution


class ConditionConfig(BaseModel):
    """
    Configuration model for task execution conditions.

    Represents conditional logic that determines when operations
    or tasks should be executed.
    """
    if_clause: str = Field(..., alias="if", description="Condition expression to evaluate")
    then_clause: str = Field(..., alias="then", description="Action to take when condition is true")

    @validator('if_clause')
    def validate_condition_expression(cls, v):
        """Validate that the condition expression is not empty."""
        if not v or not v.strip():
            raise ValueError("Condition expression cannot be empty")
        return v.strip()

    @validator('then_clause')
    def validate_then_clause(cls, v):
        """Validate that the then clause is not empty."""
        if not v or not v.strip():
            raise ValueError("Then clause cannot be empty")
        return v.strip()

    class Config:
        populate_by_name = True


class ToolOperationConfig(BaseModel):
    """
    Configuration model for tool operations.

    Represents a specific operation that can be performed by a tool,
    along with its execution conditions.
    """
    operation_name: str = Field(..., description="Name of the operation")
    conditions: Optional[List[ConditionConfig]] = Field(
        None,
        description="List of conditions that must be met for this operation to execute"
    )

    @validator('operation_name')
    def validate_operation_name(cls, v):
        """Validate operation name format."""
        if not v or not v.strip():
            raise ValueError("Operation name cannot be empty")

        # Ensure operation name follows snake_case convention
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v.strip()):
            raise ValueError(f"Operation name must follow snake_case convention: {v}")

        return v.strip()


class ToolConfig(BaseModel):
    """
    Configuration model for tools used by tasks.

    Represents a tool and its available operations with their conditions.
    """
    tool_name: str = Field(..., description="Name of the tool")
    operations: Union[List[str], List[Dict[str, Any]], Dict[str, Any]] = Field(
        ...,
        description="Operations configuration - can be list of strings, list of dicts, or dict"
    )

    @validator('tool_name')
    def validate_tool_name(cls, v):
        """Validate tool name format."""
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v.strip()

    @validator('operations')
    def validate_operations(cls, v):
        """Validate operations configuration."""
        if v is None:
            raise ValueError("Operations cannot be None")

        # Handle different operation formats from YAML
        if isinstance(v, list):
            if not v:
                raise ValueError("Operations list cannot be empty")
        elif isinstance(v, dict):
            if not v:
                raise ValueError("Operations dict cannot be empty")
        else:
            raise ValueError("Operations must be a list or dict")

        return v


class TaskConfig(BaseModel):
    """
    Base configuration model for all tasks.

    This model defines the common structure for both system tasks and sub-tasks,
    serving as the foundation for task configuration validation.
    """
    description: str = Field(..., min_length=10, description="Detailed description of what the task does")
    agent: str = Field(..., description="Agent responsible for executing this task")
    expected_output: str = Field(..., min_length=5, description="Description of expected task output")
    task_type: TaskType = Field(default=TaskType.FAST, description="Execution type of the task")
    tools: Optional[Dict[str, Any]] = Field(
        None,
        description="Tools configuration with operations and conditions"
    )
    conditions: Optional[List[ConditionConfig]] = Field(
        None,
        description="Task-level execution conditions"
    )

    @validator('description')
    def validate_description(cls, v):
        """Validate task description contains action words."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")

        # Ensure description contains action-oriented language
        action_indicators = [
            'analyze', 'create', 'generate', 'process', 'collect', 'extract',
            'validate', 'review', 'examine', 'break down', 'identify', 'determine',
            'provide', 'engage', 'answer', 'scrape', 'search', 'clean', 'normalize',
            'compute', 'apply', 'integrate', 'compress', 'enrich', 'transform',
            'filter', 'format', 'sort', 'convert', 'segment', 'tokenize', 'link',
            'classify', 'perform', 'refine', 'iterate', 'improve', 'forecast'
        ]

        description_lower = v.lower()
        if not any(indicator in description_lower for indicator in action_indicators):
            raise ValueError("Description should contain action-oriented language")

        return v.strip()

    @validator('agent')
    def validate_agent(cls, v):
        """Validate agent name follows naming convention."""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty")

        # Agent names should follow snake_case pattern (allow single words or underscore-separated)
        import re
        if not re.match(r'^[a-z]+(_[a-z]+)*$', v.strip()):
            raise ValueError(f"Agent name should follow snake_case pattern: {v}")

        return v.strip()

    @validator('expected_output')
    def validate_expected_output(cls, v):
        """Validate expected output description."""
        if not v or not v.strip():
            raise ValueError("Expected output cannot be empty")
        return v.strip()


class SystemTaskConfig(TaskConfig):
    """
    Configuration model for system tasks.

    System tasks orchestrate the overall workflow and are responsible
    for high-level coordination and quality control.
    """
    pass  # Inherits all validation from TaskConfig


class SubTaskConfig(TaskConfig):
    """
    Configuration model for sub-tasks.

    Sub-tasks perform specific operations within the workflow
    and are organized by intent categories.
    """
    pass  # Inherits all validation from TaskConfig


class TasksConfig(BaseModel):
    """
    Root configuration model for all tasks.

    This model represents the complete task configuration structure
    as defined in the tasks.yaml file, providing validation for
    the entire task ecosystem.
    """
    system_tasks: Dict[str, SystemTaskConfig] = Field(
        ...,
        description="System tasks that orchestrate the workflow"
    )
    sub_tasks: Dict[str, SubTaskConfig] = Field(
        ...,
        description="Sub-tasks organized by intent categories"
    )

    @validator('system_tasks')
    def validate_system_tasks(cls, v):
        """Validate system tasks configuration."""
        if not v:
            raise ValueError("System tasks cannot be empty")

        # Ensure required system tasks are present
        required_system_tasks = {
            'parse_intent', 'breakdown_subTask', 'plan_sequence',
            'examination', 'acceptance'
        }

        missing_tasks = required_system_tasks - set(v.keys())
        if missing_tasks:
            raise ValueError(f"Missing required system tasks: {missing_tasks}")

        return v

    @validator('sub_tasks')
    def validate_sub_tasks(cls, v):
        """Validate sub-tasks configuration."""
        if not v:
            raise ValueError("Sub-tasks cannot be empty")

        # Group sub-tasks by category to ensure coverage
        categories = {}
        for task_name, task_config in v.items():
            # Extract category from task name (e.g., 'answer_discuss' -> 'answer')
            if '_' in task_name:
                category = task_name.split('_')[0]
                if category in TaskCategory.__members__.values():
                    categories.setdefault(category, []).append(task_name)

        # Ensure all categories have at least one sub-task
        missing_categories = set(TaskCategory.__members__.values()) - set(categories.keys())
        if missing_categories:
            raise ValueError(f"Missing sub-tasks for categories: {missing_categories}")

        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True


# Type aliases for better code readability
SystemTasksDict = Dict[str, SystemTaskConfig]
SubTasksDict = Dict[str, SubTaskConfig]


class LangChainTaskWrapper:
    """
    Wrapper class for LangChain-based task execution that includes custom metadata.

    This wrapper allows us to attach additional metadata to tasks and provides
    a unified interface for task execution using LangChain components.
    """

    def __init__(
        self,
        task_name: str,
        task_category: Optional[str],
        task_config: TaskConfig,
        llm_chain: Optional[LLMChain] = None,
        prompt_template: Optional[PromptTemplate] = None,
        output_parser: Optional[BaseOutputParser] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the LangChain task wrapper.

        Args:
            task_name: Name identifier for the task
            task_category: Category/type of the task
            task_config: Original configuration used to create the task
            llm_chain: LangChain LLMChain for task execution
            prompt_template: Prompt template for the task
            output_parser: Output parser for processing results
            metadata: Additional metadata for the task
        """
        self.task_name = task_name
        self.task_category = task_category
        self.task_config = task_config
        self.llm_chain = llm_chain
        self.prompt_template = prompt_template
        self.output_parser = output_parser
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"LangChainTaskWrapper(task_name='{self.task_name}', category='{self.task_category}')"

    def __str__(self) -> str:
        return f"LangChainTaskWrapper: {self.task_name} ({self.task_category})"

    @property
    def description(self) -> str:
        """Get the task description from the configuration."""
        return self.task_config.description if self.task_config else ""

    @property
    def expected_output(self) -> str:
        """Get the expected output from the configuration."""
        return self.task_config.expected_output if self.task_config else ""

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key."""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self.metadata[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        if hasattr(self.task_config, key):
            return getattr(self.task_config, key, default)
        return default

    async def execute(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Execute the task using the LangChain components.

        Args:
            inputs: Input data for the task
            **kwargs: Additional execution parameters

        Returns:
            Task execution result
        """
        if not self.llm_chain:
            raise ValueError(f"No LLM chain configured for task: {self.task_name}")

        try:
            # Execute the LangChain chain
            result = await self.llm_chain.arun(**inputs, **kwargs)

            # Parse output if parser is available
            if self.output_parser:
                parsed_result = self.output_parser.parse(result)
                return {
                    "output": parsed_result,
                    "raw_output": result,
                    "task_name": self.task_name,
                    "success": True
                }
            else:
                return {
                    "output": result,
                    "task_name": self.task_name,
                    "success": True
                }

        except Exception as e:
            return {
                "output": None,
                "error": str(e),
                "task_name": self.task_name,
                "success": False
            }

    def execute_sync(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Synchronous version of execute for compatibility.

        Args:
            inputs: Input data for the task
            **kwargs: Additional execution parameters

        Returns:
            Task execution result
        """
        if not self.llm_chain:
            raise ValueError(f"No LLM chain configured for task: {self.task_name}")

        try:
            # Execute the LangChain chain synchronously
            result = self.llm_chain.run(**inputs, **kwargs)

            # Parse output if parser is available
            if self.output_parser:
                parsed_result = self.output_parser.parse(result)
                return {
                    "output": parsed_result,
                    "raw_output": result,
                    "task_name": self.task_name,
                    "success": True
                }
            else:
                return {
                    "output": result,
                    "task_name": self.task_name,
                    "success": True
                }

        except Exception as e:
            return {
                "output": None,
                "error": str(e),
                "task_name": self.task_name,
                "success": False
            }


# Backward compatibility alias
TaskWrapper = LangChainTaskWrapper
