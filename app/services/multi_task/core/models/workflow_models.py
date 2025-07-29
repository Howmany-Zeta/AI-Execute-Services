"""
Workflow Models

Core data models for workflow execution, DSL parsing, validation, and orchestration.
Extracted from workflow files for unified maintenance.
"""

import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# DSL Execution Models

class ExecutionState(Enum):
    """Execution state for DSL nodes."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class NodeExecutionContext:
    """Execution context for a DSL node."""
    node_id: str
    state: ExecutionState = ExecutionState.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class DSLExecutionContext:
    """Global execution context for DSL workflow."""
    workflow_id: str
    execution_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    node_contexts: Dict[str, NodeExecutionContext] = field(default_factory=dict)
    cancelled: bool = False
    start_time: float = field(default_factory=time.time)

    def get_node_context(self, node_id: str) -> NodeExecutionContext:
        """Get or create node execution context."""
        if node_id not in self.node_contexts:
            self.node_contexts[node_id] = NodeExecutionContext(node_id=node_id)
        return self.node_contexts[node_id]


# DSL Parser Models

class DSLNodeType(Enum):
    """DSL node types."""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    LOOP = "loop"
    WAIT = "wait"


@dataclass
class DSLNode:
    """Represents a node in the DSL tree."""
    node_type: DSLNodeType
    node_id: str
    config: Dict[str, Any]
    children: List['DSLNode']
    parent: Optional['DSLNode'] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DSLParseResult:
    """Result of DSL parsing."""
    success: bool
    root_node: Optional[DSLNode]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


# DSL Validator Models

class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: ValidationSeverity
    message: str
    node_id: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of DSL validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    dependency_graph: Dict[str, List[str]]
    execution_order: List[str]
    estimated_duration: Optional[float] = None


# Workflow Orchestrator Models

class WorkflowExecutionMode(Enum):
    """Workflow execution modes."""
    VALIDATE_ONLY = "validate_only"
    DRY_RUN = "dry_run"
    EXECUTE = "execute"


@dataclass
class WorkflowExecutionRequest:
    """Request for workflow execution."""
    workflow_definition: Dict[str, Any]
    execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.EXECUTE
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[float] = None
    max_retries: int = 0
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecutionResponse:
    """Response from workflow execution."""
    execution_id: str
    workflow_id: str
    status: Any  # WorkflowStatus from execution_models - using Any to avoid circular import
    result: Optional[Any] = None
    error: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Utility Classes

class DictWrapper:
    """Wrapper to allow dot notation access to dictionary values."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, name: str):
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return DictWrapper(value)
            return value
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]


class ConditionEvaluator:
    """Evaluates condition expressions in DSL workflows."""

    def evaluate(self, condition: str, context: DSLExecutionContext) -> bool:
        """
        Evaluate a condition expression.

        Args:
            condition: Condition expression string
            context: Execution context

        Returns:
            Boolean result of condition evaluation
        """
        try:
            # Create evaluation environment with wrapped dictionaries for dot notation access
            env = {
                'result': DictWrapper(context.results),
                'context': DictWrapper(context.variables),
                'subtasks': self._create_subtasks_helper(context),
                'true': True,
                'false': False,
                'and': lambda a, b: a and b,
                'or': lambda a, b: a or b,
                'not': lambda a: not a
            }

            # Simple expression evaluation
            # Note: In production, use a proper expression parser for security
            return bool(eval(condition, {"__builtins__": {}}, env))

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Condition evaluation failed: {condition}, error: {e}")
            return False

    def _create_subtasks_helper(self, context: DSLExecutionContext) -> Dict[str, Any]:
        """Create helper object for subtask checks."""
        return {
            'includes': lambda task_name: any(
                task_name in str(result) for result in context.results.values()
            )
        }


class VariableResolver:
    """Resolves variables and expressions in DSL parameters."""

    def resolve_variables(self, parameters: Dict[str, Any], context: DSLExecutionContext) -> Dict[str, Any]:
        """
        Resolve variables in parameters.

        Args:
            parameters: Parameters dictionary
            context: Execution context

        Returns:
            Parameters with resolved variables
        """
        resolved = {}

        for key, value in parameters.items():
            resolved[key] = self._resolve_value(value, context)

        return resolved

    def _resolve_value(self, value: Any, context: DSLExecutionContext) -> Any:
        """Resolve a single value."""
        if isinstance(value, str):
            return self._resolve_string(value, context)
        elif isinstance(value, dict):
            return {k: self._resolve_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_value(item, context) for item in value]
        else:
            return value

    def _resolve_string(self, value: str, context: DSLExecutionContext) -> str:
        """Resolve variables in a string value."""
        import re

        # Replace ${result.node_id.field} patterns
        def replace_result(match):
            parts = match.group(1).split('.')
            if len(parts) >= 2 and parts[0] == 'result':
                node_id = parts[1]
                if node_id in context.results:
                    result = context.results[node_id]
                    if len(parts) > 2:
                        # Navigate nested fields
                        for field in parts[2:]:
                            if isinstance(result, dict) and field in result:
                                result = result[field]
                            else:
                                return match.group(0)  # Return original if field not found
                    return str(result)
            return match.group(0)  # Return original if not found

        # Replace ${context.variable} patterns
        def replace_context(match):
            var_name = match.group(1).replace('context.', '')
            if var_name in context.variables:
                return str(context.variables[var_name])
            return match.group(0)  # Return original if not found

        # Apply replacements
        value = re.sub(r'\$\{([^}]+)\}', replace_result, value)
        value = re.sub(r'\$\{(context\.[^}]+)\}', replace_context, value)

        return value
