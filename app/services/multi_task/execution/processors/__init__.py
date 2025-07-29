"""
Execution Processors

This module contains specialized processors for different aspects of execution:
- TaskProcessor: Handles individual task processing and execution
- WorkflowProcessor: Manages workflow orchestration and coordination
- QualityProcessor: Implements quality control and validation workflows
"""

from .task_processor import TaskProcessor
from .workflow_processor import WorkflowProcessor
from .quality_processor import QualityProcessor

__all__ = [
    'TaskProcessor',
    'WorkflowProcessor',
    'QualityProcessor'
]
