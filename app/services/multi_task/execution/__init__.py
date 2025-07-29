"""
Execution Layer

The execution layer provides comprehensive task and workflow execution capabilities
for the multi-task architecture. It implements the execution interfaces defined in
the core layer and provides multiple execution engines, processors, and monitors.

## Architecture

The execution layer follows SOLID design principles and consists of:

### Engines
- **DSLEngine**: Executes Domain Specific Language (DSL) workflows with support for
  conditional branching, parallel blocks, and single tasks
- **CrewEngine**: Provides CrewAI-based agent execution for collaborative workflows
- **ParallelEngine**: Optimized parallel execution with dependency management and
  resource coordination

### Processors
- **TaskProcessor**: Handles individual task processing, validation, and lifecycle management
- **WorkflowProcessor**: Manages workflow orchestration, coordination, and execution flow
- **QualityProcessor**: Implements quality control workflows including examination
  (for collect/process tasks) and acceptance (for analyze/generate tasks)

### Monitors
- **ExecutionMonitor**: Tracks execution progress, status, and events in real-time
- **PerformanceMonitor**: Monitors performance metrics, resource usage, and provides
  optimization recommendations

## Key Features

- **Multi-Engine Support**: Different execution strategies for various use cases
- **Quality Control**: Built-in quality assurance workflows
- **Real-time Monitoring**: Comprehensive execution and performance tracking
- **SOLID Design**: Follows Single Responsibility, Dependency Inversion, Open/Closed,
  and Interface Segregation principles
- **Extensibility**: Easy to add new engines, processors, and monitors
- **Resource Management**: Intelligent resource allocation and coordination
- **Error Handling**: Robust error handling and recovery mechanisms

## Usage

```python
from app.services.multi_task.execution import (
    DSLEngine, CrewEngine, ParallelEngine,
    TaskProcessor, WorkflowProcessor, QualityProcessor,
    ExecutionMonitor, PerformanceMonitor
)

# Create execution engine
engine = DSLEngine()

# Create processors
task_processor = TaskProcessor(engine)
workflow_processor = WorkflowProcessor(engine, task_processor)
quality_processor = QualityProcessor(engine)

# Create monitors
execution_monitor = ExecutionMonitor()
performance_monitor = PerformanceMonitor()

# Start monitoring
await execution_monitor.start_monitoring()
await performance_monitor.start_monitoring()

# Execute workflow
async for result in workflow_processor.execute_workflow(workflow_definition):
    print(f"Step completed: {result.message}")
```

## Integration with Multi-Task Summarizer

The execution layer is designed to integrate seamlessly with the existing
MultiTaskSummarizerRefactored class, providing a more modular and maintainable
execution architecture while preserving all existing functionality.
"""

# Base executor
from .base_executor import BaseExecutor

# Execution engines
from .engines import DSLEngine, CrewEngine, ParallelEngine

# Processors
from .processors import TaskProcessor, WorkflowProcessor, QualityProcessor

# Monitors
from .monitors import ExecutionMonitor, PerformanceMonitor

__all__ = [
    # Base
    'BaseExecutor',

    # Engines
    'DSLEngine',
    'CrewEngine',
    'ParallelEngine',

    # Processors
    'TaskProcessor',
    'WorkflowProcessor',
    'QualityProcessor',

    # Monitors
    'ExecutionMonitor',
    'PerformanceMonitor'
]

# Version information
__version__ = '1.0.0'
__author__ = 'Multi-Task Architecture Team'
__description__ = 'Execution layer for multi-task architecture'
