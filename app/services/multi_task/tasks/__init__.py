"""
Task Layer for Multi-Task Service

This module provides task definition, creation, and management capabilities.
It serves as the bridge between task configuration and execution.

The task layer follows SOLID principles:

1. Single Responsibility Principle (SRP):
   - task_models.py: Only contains data structures and validation
   - task_factory.py: Only handles task object creation

2. Dependency Inversion Principle (DIP):
   - Depends on abstractions (Pydantic models) not concrete implementations
   - CrewAI dependency is isolated in the factory

3. Open/Closed Principle (OCP):
   - New task types can be added by extending base models
   - New creation strategies can be added without modifying existing code

4. Interface Segregation Principle (ISP):
   - Separate models for different task types (System vs Sub-tasks)
   - Focused interfaces for different concerns

Architecture:
- task_models.py: Task definition models (data structures only)
- task_factory.py: Task creation factory (business logic)

Usage Example:
    ```python
    from app.services.multi_task.tasks import TaskFactory, TasksConfig

    # Load and validate configuration
    factory = TaskFactory()
    config = factory.load_configuration()

    # Create tasks with agents
    system_tasks, sub_tasks = factory.create_all_tasks(agents)
    ```
"""

from .task_models import (
    # Enums
    TaskCategory,
    TaskType,

    # Configuration Models
    ConditionConfig,
    ToolOperationConfig,
    ToolConfig,
    TaskConfig,
    SystemTaskConfig,
    SubTaskConfig,
    TasksConfig,

    # Type Aliases
    SystemTasksDict,
    SubTasksDict
)

from .task_factory import (
    TaskFactory,
    create_all_tasks
)

__all__ = [
    # Enums
    'TaskCategory',
    'TaskType',

    # Configuration Models
    'ConditionConfig',
    'ToolOperationConfig',
    'ToolConfig',
    'TaskConfig',
    'SystemTaskConfig',
    'SubTaskConfig',
    'TasksConfig',

    # Type Aliases
    'SystemTasksDict',
    'SubTasksDict',

    # Factory
    'TaskFactory',
    'create_all_tasks'
]
