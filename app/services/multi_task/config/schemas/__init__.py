"""
Configuration Schemas

Schema definitions for different types of configuration data
in the multi-task service.
"""

from .prompt_schema import PromptSchema
from .task_schema import TaskSchema
from .domain_schema import DomainSchema
from .config_schema import ConfigSchema

__all__ = [
    'PromptSchema',
    'TaskSchema',
    'DomainSchema',
    'ConfigSchema'
]
