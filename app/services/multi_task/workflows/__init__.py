"""
Workflows Module

Complete workflow layer for the multi-task system providing DSL-based workflow
execution with comprehensive parsing, validation, and orchestration capabilities.
"""

# Core workflow components
from .base_workflow import IWorkflow, BaseWorkflow

# DSL components
from .dsl import (
    DSLParser, DSLValidator, DSLExecutor,
    DSLNode, DSLNodeType, DSLParseResult,
    ValidationResult, ValidationIssue, ValidationSeverity,
    DSLExecutionContext, NodeExecutionContext, ExecutionState
)

# Orchestration
from .workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowExecutionMode
)

# Workflow templates
from .templates import (
    AnswerWorkflow, CollectWorkflow, ProcessWorkflow,
    AnalyzeWorkflow, GenerateWorkflow,
    WORKFLOW_TEMPLATES, get_workflow_template,
    list_available_templates, create_workflow_instance
)

__all__ = [
    # Base workflow
    "IWorkflow",
    "BaseWorkflow",

    # DSL components
    "DSLParser",
    "DSLValidator",
    "DSLExecutor",
    "DSLNode",
    "DSLNodeType",
    "DSLParseResult",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "DSLExecutionContext",
    "NodeExecutionContext",
    "ExecutionState",

    # Orchestration
    "WorkflowOrchestrator",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowExecutionMode",

    # Templates
    "AnswerWorkflow",
    "CollectWorkflow",
    "ProcessWorkflow",
    "AnalyzeWorkflow",
    "GenerateWorkflow",
    "WORKFLOW_TEMPLATES",
    "get_workflow_template",
    "list_available_templates",
    "create_workflow_instance"
]
