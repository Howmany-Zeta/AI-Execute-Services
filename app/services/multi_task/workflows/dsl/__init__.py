"""
DSL Module

Domain Specific Language components for multi-task workflows.
Provides parsing, validation, and execution capabilities for workflow DSL.
"""

from .dsl_parser import (
    DSLParser,
    DSLNode,
    DSLNodeType,
    DSLParseResult
)

from .dsl_validator import (
    DSLValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity
)

from .dsl_executor import (
    DSLExecutor,
    DSLExecutionContext,
    NodeExecutionContext,
    ExecutionState,
    ConditionEvaluator,
    VariableResolver
)

__all__ = [
    # Parser
    "DSLParser",
    "DSLNode",
    "DSLNodeType",
    "DSLParseResult",

    # Validator
    "DSLValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",

    # Executor
    "DSLExecutor",
    "DSLExecutionContext",
    "NodeExecutionContext",
    "ExecutionState",
    "ConditionEvaluator",
    "VariableResolver"
]
