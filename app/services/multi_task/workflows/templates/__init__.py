"""
Workflow Templates Module

Collection of workflow templates for different task categories in the multi-task system.
Each template provides specialized workflow definitions optimized for specific task types.
"""

from .answer_workflow import AnswerWorkflow
from .collect_workflow import CollectWorkflow
from .process_workflow import ProcessWorkflow
from .analyze_workflow import AnalyzeWorkflow
from .generate_workflow import GenerateWorkflow

# Template registry for easy access
WORKFLOW_TEMPLATES = {
    "answer": AnswerWorkflow,
    "collect": CollectWorkflow,
    "process": ProcessWorkflow,
    "analyze": AnalyzeWorkflow,
    "generate": GenerateWorkflow
}

def get_workflow_template(workflow_type: str):
    """
    Get a workflow template class by type.

    Args:
        workflow_type: Type of workflow template to retrieve

    Returns:
        Workflow template class or None if not found
    """
    return WORKFLOW_TEMPLATES.get(workflow_type.lower())

def list_available_templates():
    """
    List all available workflow template types.

    Returns:
        List of available workflow template types
    """
    return list(WORKFLOW_TEMPLATES.keys())

def create_workflow_instance(workflow_type: str):
    """
    Create an instance of a workflow template.

    Args:
        workflow_type: Type of workflow template to create

    Returns:
        Workflow template instance or None if type not found
    """
    template_class = get_workflow_template(workflow_type)
    if template_class:
        return template_class()
    return None

__all__ = [
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
