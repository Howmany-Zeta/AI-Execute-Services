# Execution Models Technical Documentation

## Overview

### Design Motivation and Problem Background

When building complex AI application systems, task execution and state management face the following core challenges:

**1. Task State Management Complexity**
- Need to support multiple task states (pending, running, completed, cancelled, timed out, failed)
- State transitions need to follow specific business rules
- Lack of unified state definition and validation mechanisms

**2. Error Handling Standardization**
- Different types of errors require different handling strategies
- Error information needs to be structured and traceable
- Lack of unified error code system and classification mechanism

**3. Execution Result Encapsulation**
- Task execution results need to contain complete state information
- Need to support both success and failure result types
- Lack of standardized result data model

**4. System Integration Requirements**
- Execution models need to integrate with multiple system components
- Need to support serialization and deserialization
- Lack of unified data contract definitions

**Execution Model System's Solution**:
- **Enum Type Definitions**: Type-safe state and error code definitions based on Python Enum
- **Result Model Encapsulation**: Structured task step result model
- **Unified Error Handling**: Standardized error code system and error information
- **Data Contract Support**: Data models supporting serialization and deserialization
- **Type Safety**: Type safety guarantees based on Python type system

### Component Positioning

`execution/model.py` is a domain model component of the AIECS system, located in the Domain Layer, defining core data models related to task execution. As the system's data contract layer, it provides type-safe, structured execution state, error codes, and result models.

## Component Type and Positioning

### Component Type
**Domain Model Component** - Located in the Domain Layer, belongs to data contract definitions

### Architecture Layers
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← Components using execution models
│  (OperationExecutor, TaskManager)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← Execution models layer
│  (ExecutionModels, Data Contracts)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← Components execution models depend on
│  (Database, WebSocket, Celery)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Systems                │  ← External systems
│  (Redis, PostgreSQL, MessageQueue)      │
└─────────────────────────────────────────┘
```

## Upstream Components (Consumers)

### 1. Application Layer Services
- **OperationExecutor** (`application/executors/operation_executor.py`)
- **TaskManager** (if exists)
- **ExecutionService** (if exists)

### 2. Infrastructure Layer
- **DatabaseManager** (`infrastructure/persistence/database_manager.py`)
- **WebSocketManager** (`infrastructure/messaging/websocket_manager.py`)
- **CeleryTaskManager** (`infrastructure/messaging/celery_task_manager.py`)

### 3. Interface Layer
- **ExecutionInterface** (`core/interface/execution_interface.py`)
- **API Layer** (via data conversion)
- **Message Queue** (via message format)

## Downstream Components (Dependencies)

### 1. Python Standard Library
- **enum** - Provides enum type support
- **typing** - Provides type annotation support
- **dataclasses** - Provides dataclass support (if used)

### 2. Domain Models
- **TaskContext** (if exists)
- **Other Domain Models** (via result fields)

### 3. Utility Functions
- **Serialization Tools** (via dict() method)
- **Validation Tools** (via type checking)

## Core Model Details

### 1. TaskStatus - Task Status Enum

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"
```

**Status Descriptions**:
- **PENDING**: Waiting for execution - Task created but not yet started
- **RUNNING**: Running - Task is currently executing
- **COMPLETED**: Completed - Task completed successfully
- **CANCELLED**: Cancelled - Task cancelled by user or system
- **TIMED_OUT**: Execution timeout - Task execution exceeded time limit
- **FAILED**: Execution failed - Error occurred during task execution

**State Transition Rules**:
```
PENDING → RUNNING → COMPLETED
       ↘ RUNNING → FAILED
       ↘ RUNNING → TIMED_OUT
       ↘ RUNNING → CANCELLED
```

**Usage Examples**:
```python
from aiecs.domain.execution.model import TaskStatus

# Create task status
status = TaskStatus.PENDING
print(f"Task status: {status.value}")  # "pending"

# Status comparison
if status == TaskStatus.PENDING:
    print("Task is waiting to start")

# State transition
status = TaskStatus.RUNNING
print(f"Task is now: {status.value}")  # "running"

# Get all statuses
all_statuses = [status.value for status in TaskStatus]
print(f"All statuses: {all_statuses}")
```

### 2. ErrorCode - Error Code Enum

```python
class ErrorCode(Enum):
    VALIDATION_ERROR = "E001"
    TIMEOUT_ERROR = "E002"
    EXECUTION_ERROR = "E003"
    CANCELLED_ERROR = "E004"
    RETRY_EXHAUSTED = "E005"
    DATABASE_ERROR = "E006"
    DSL_EVALUATION_ERROR = "E007"
```

**Error Code Descriptions**:
- **E001 - VALIDATION_ERROR**: Parameter validation error - Input parameters do not meet requirements
- **E002 - TIMEOUT_ERROR**: Execution timeout error - Task execution exceeded time limit
- **E003 - EXECUTION_ERROR**: Execution error - Error occurred during task execution
- **E004 - CANCELLED_ERROR**: Cancellation error - Task was cancelled
- **E005 - RETRY_EXHAUSTED**: Retry exhausted error - Retry attempts exhausted
- **E006 - DATABASE_ERROR**: Database error - Database operation failed
- **E007 - DSL_EVALUATION_ERROR**: DSL evaluation error - DSL expression evaluation failed

**Error Classification**:
- **Client Errors** (E001): Parameter validation errors
- **Timeout Errors** (E002): Execution timeouts
- **Execution Errors** (E003): Business logic errors
- **System Errors** (E004, E005, E006, E007): System-level errors

**Usage Examples**:
```python
from aiecs.domain.execution.model import ErrorCode

# Create error code
error_code = ErrorCode.VALIDATION_ERROR
print(f"Error code: {error_code.value}")  # "E001"

# Error code comparison
if error_code == ErrorCode.VALIDATION_ERROR:
    print("This is a validation error")

# Get error code descriptions
error_descriptions = {
    ErrorCode.VALIDATION_ERROR: "Parameter validation error",
    ErrorCode.TIMEOUT_ERROR: "Execution timeout error",
    ErrorCode.EXECUTION_ERROR: "Execution error",
    ErrorCode.CANCELLED_ERROR: "Cancellation error",
    ErrorCode.RETRY_EXHAUSTED: "Retry exhausted error",
    ErrorCode.DATABASE_ERROR: "Database error",
    ErrorCode.DSL_EVALUATION_ERROR: "DSL evaluation error"
}

print(f"Error description: {error_descriptions[error_code]}")
```

### 3. TaskStepResult - Task Step Result Model

```python
class TaskStepResult:
    """Task step result model"""
    def __init__(self, step: str, result: Any, completed: bool = False,
                 message: str = "", status: str = "pending",
                 error_code: Optional[str] = None, error_message: Optional[str] = None):
        self.step = step
        self.result = result
        self.completed = completed
        self.message = message
        self.status = status
        self.error_code = error_code
        self.error_message = error_message
```

**Field Descriptions**:
- **step**: Operation step identifier (e.g., "pandas_tool.read_csv")
- **result**: Operation execution result
- **completed**: Whether completed
- **message**: Status message
- **status**: Execution status
- **error_code**: Error code (optional)
- **error_message**: Error message (optional)

**Core Methods**:

#### Serialization Method
```python
def dict(self) -> Dict[str, Any]:
    """Convert to dictionary format"""
    return {
        "step": self.step,
        "result": self.result,
        "completed": self.completed,
        "message": self.message,
        "status": self.status,
        "error_code": self.error_code,
        "error_message": self.error_message
    }
```

#### String Representation
```python
def __repr__(self) -> str:
    """String representation"""
    return f"TaskStepResult(step='{self.step}', status='{self.status}', completed={self.completed})"
```

**Usage Examples**:
```python
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

# Create success result
success_result = TaskStepResult(
    step="pandas_tool.read_csv",
    result={"rows": 1000, "columns": 5},
    completed=True,
    message="Successfully read CSV file",
    status=TaskStatus.COMPLETED.value
)

print(f"Success result: {success_result}")
print(f"Result data: {success_result.dict()}")

# Create failure result
failure_result = TaskStepResult(
    step="pandas_tool.read_csv",
    result=None,
    completed=False,
    message="Failed to read CSV file",
    status=TaskStatus.FAILED.value,
    error_code=ErrorCode.EXECUTION_ERROR.value,
    error_message="File not found: data.csv"
)

print(f"Failure result: {failure_result}")
print(f"Error code: {failure_result.error_code}")
print(f"Error message: {failure_result.error_message}")
```

## Design Patterns Explained

### 1. Enum Pattern
```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    # ...
```

**Advantages**:
- **Type Safety**: Compile-time type checking
- **Value Constraints**: Limits possible values
- **Readability**: Code is easier to read and maintain
- **Extensibility**: Easy to add new states

### 2. Value Object Pattern
```python
class TaskStepResult:
    """Immutable value object"""
    def __init__(self, step: str, result: Any, ...):
        self.step = step
        self.result = result
        # ...
```

**Advantages**:
- **Immutability**: Object cannot be modified after creation
- **Equality**: Value-based rather than reference-based equality
- **Encapsulation**: Encapsulates related data and behavior
- **Testability**: Easy to unit test

### 3. Factory Pattern
```python
# Create instance via constructor
result = TaskStepResult(
    step="operation_name",
    result=operation_result,
    completed=True,
    status=TaskStatus.COMPLETED.value
)
```

**Advantages**:
- **Unified Creation**: Unified object creation interface
- **Parameter Validation**: Parameter validation at creation time
- **Type Safety**: Ensures created objects are of correct type

## Usage Examples

### 1. Basic State Management

```python
from aiecs.domain.execution.model import TaskStatus, ErrorCode, TaskStepResult

# Task state management
def manage_task_lifecycle():
    """Manage task lifecycle"""
    # Initial state
    current_status = TaskStatus.PENDING
    print(f"Task started with status: {current_status.value}")
    
    # State transition
    current_status = TaskStatus.RUNNING
    print(f"Task is now: {current_status.value}")
    
    # Check state
    if current_status == TaskStatus.RUNNING:
        print("Task is currently running")
    
    # Completion state
    current_status = TaskStatus.COMPLETED
    print(f"Task finished with status: {current_status.value}")

# Error handling
def handle_task_errors():
    """Handle task errors"""
    error_codes = [
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.TIMEOUT_ERROR,
        ErrorCode.EXECUTION_ERROR
    ]
    
    for error_code in error_codes:
        print(f"Error code: {error_code.value}")
        
        if error_code == ErrorCode.VALIDATION_ERROR:
            print("This is a validation error - check input parameters")
        elif error_code == ErrorCode.TIMEOUT_ERROR:
            print("This is a timeout error - task took too long")
        elif error_code == ErrorCode.EXECUTION_ERROR:
            print("This is an execution error - check business logic")
```

### 2. Result Model Usage

```python
# Create success result
def create_success_result():
    """Create success result"""
    result = TaskStepResult(
        step="data_processing",
        result={"processed_rows": 1000, "output_file": "result.csv"},
        completed=True,
        message="Data processing completed successfully",
        status=TaskStatus.COMPLETED.value
    )
    
    print(f"Success result: {result}")
    print(f"Result data: {result.dict()}")
    return result

# Create failure result
def create_failure_result():
    """Create failure result"""
    result = TaskStepResult(
        step="data_processing",
        result=None,
        completed=False,
        message="Data processing failed",
        status=TaskStatus.FAILED.value,
        error_code=ErrorCode.EXECUTION_ERROR.value,
        error_message="Invalid data format detected"
    )
    
    print(f"Failure result: {result}")
    print(f"Error details: {result.error_code} - {result.error_message}")
    return result

# Result processing
def process_results(results: List[TaskStepResult]):
    """Process result list"""
    success_count = 0
    failure_count = 0
    
    for result in results:
        if result.completed:
            success_count += 1
            print(f"✅ {result.step}: {result.message}")
        else:
            failure_count += 1
            print(f"❌ {result.step}: {result.message}")
            if result.error_code:
                print(f"   Error: {result.error_code} - {result.error_message}")
    
    print(f"Summary: {success_count} successful, {failure_count} failed")
```

### 3. System Integration

```python
# Database integration
def save_task_result_to_database(result: TaskStepResult, user_id: str, task_id: str):
    """Save task result to database"""
    from aiecs.infrastructure.persistence.database_manager import DatabaseManager
    
    db_manager = DatabaseManager()
    
    # Save to database
    db_manager.save_task_history(user_id, task_id, 1, result)
    
    print(f"Saved result for task {task_id}: {result.step}")

# WebSocket integration
def send_result_via_websocket(result: TaskStepResult, user_id: str, task_id: str):
    """Send result via WebSocket"""
    from aiecs.infrastructure.messaging.websocket_manager import WebSocketManager
    
    ws_manager = WebSocketManager()
    
    # Send result
    ws_manager.notify_user(result, user_id, task_id, 1)
    
    print(f"Sent result via WebSocket: {result.step}")

# Celery integration
def create_celery_task_result(status: TaskStatus, error_code: ErrorCode = None):
    """Create Celery task result"""
    result = {
        "status": status.value,
        "completed": status == TaskStatus.COMPLETED,
        "message": f"Task {status.value}"
    }
    
    if error_code:
        result["error_code"] = error_code.value
        result["error_message"] = f"Task failed with {error_code.value}"
    
    return result
```

### 4. Advanced Usage

```python
# Result validation
def validate_result(result: TaskStepResult) -> bool:
    """Validate result validity"""
    if not result.step:
        print("❌ Result missing step identifier")
        return False
    
    if result.completed and result.result is None:
        print("❌ Completed result missing result data")
        return False
    
    if not result.completed and result.error_code is None:
        print("❌ Failed result missing error code")
        return False
    
    print("✅ Result validation passed")
    return True

# Result conversion
def convert_result_to_dict(result: TaskStepResult) -> Dict[str, Any]:
    """Convert result to dictionary format"""
    return result.dict()

def convert_dict_to_result(data: Dict[str, Any]) -> TaskStepResult:
    """Create result object from dictionary"""
    return TaskStepResult(
        step=data["step"],
        result=data["result"],
        completed=data["completed"],
        message=data["message"],
        status=data["status"],
        error_code=data.get("error_code"),
        error_message=data.get("error_message")
    )

# Result comparison
def compare_results(result1: TaskStepResult, result2: TaskStepResult) -> bool:
    """Compare if two results are equal"""
    return (result1.step == result2.step and
            result1.completed == result2.completed and
            result1.status == result2.status)
```

## Maintenance Guide

### 1. Daily Maintenance

#### Model Validation
```python
def validate_models_health():
    """Validate model health status"""
    try:
        # Test status enum
        status = TaskStatus.PENDING
        assert status.value == "pending"
        print("✅ TaskStatus validation passed")
        
        # Test error code enum
        error_code = ErrorCode.VALIDATION_ERROR
        assert error_code.value == "E001"
        print("✅ ErrorCode validation passed")
        
        # Test result model
        result = TaskStepResult(
            step="test_step",
            result="test_result",
            completed=True,
            status=TaskStatus.COMPLETED.value
        )
        assert result.step == "test_step"
        assert result.completed == True
        print("✅ TaskStepResult validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Model validation failed: {e}")
        return False
```

#### Data Consistency Check
```python
def check_data_consistency(result: TaskStepResult):
    """Check result data consistency"""
    try:
        # Check basic fields
        if not result.step:
            print("❌ Missing step identifier")
            return False
        
        # Check status consistency
        if result.completed and result.status != TaskStatus.COMPLETED.value:
            print("❌ Completed result has wrong status")
            return False
        
        if not result.completed and result.status == TaskStatus.COMPLETED.value:
            print("❌ Incomplete result has completed status")
            return False
        
        # Check error information consistency
        if result.error_code and not result.error_message:
            print("❌ Error code without error message")
            return False
        
        if result.error_message and not result.error_code:
            print("❌ Error message without error code")
            return False
        
        print("✅ Data consistency check passed")
        return True
        
    except Exception as e:
        print(f"❌ Data consistency check failed: {e}")
        return False
```

### 2. Troubleshooting

#### Common Issue Diagnosis

**Issue 1: State Transition Error**
```python
def diagnose_status_transition_error():
    """Diagnose state transition errors"""
    try:
        # Test invalid state transition
        current_status = TaskStatus.PENDING
        next_status = TaskStatus.COMPLETED  # Skipping RUNNING
        
        if current_status == TaskStatus.PENDING and next_status == TaskStatus.COMPLETED:
            print("❌ Invalid status transition: PENDING → COMPLETED")
            print("   Valid transitions from PENDING: RUNNING")
        
        # Test valid state transition
        current_status = TaskStatus.PENDING
        next_status = TaskStatus.RUNNING
        
        if current_status == TaskStatus.PENDING and next_status == TaskStatus.RUNNING:
            print("✅ Valid status transition: PENDING → RUNNING")
        
    except Exception as e:
        print(f"❌ Status transition diagnosis failed: {e}")
```

**Issue 2: Error Code Mapping Error**
```python
def diagnose_error_code_mapping_error():
    """Diagnose error code mapping errors"""
    try:
        # Test error code mapping
        error_mappings = {
            "validation_error": ErrorCode.VALIDATION_ERROR,
            "timeout_error": ErrorCode.TIMEOUT_ERROR,
            "execution_error": ErrorCode.EXECUTION_ERROR,
            "cancelled_error": ErrorCode.CANCELLED_ERROR,
            "retry_exhausted": ErrorCode.RETRY_EXHAUSTED,
            "database_error": ErrorCode.DATABASE_ERROR,
            "dsl_evaluation_error": ErrorCode.DSL_EVALUATION_ERROR
        }
        
        for error_name, error_code in error_mappings.items():
            if error_code.value != f"E{error_code.value[1:].zfill(3)}":
                print(f"❌ Invalid error code format: {error_code.value}")
            else:
                print(f"✅ Valid error code: {error_code.value}")
        
    except Exception as e:
        print(f"❌ Error code mapping diagnosis failed: {e}")
```

### 3. Performance Optimization

#### Object Creation Optimization
```python
def optimize_object_creation():
    """Optimize object creation performance"""
    import time
    
    # Test enum creation performance
    start_time = time.time()
    for i in range(10000):
        status = TaskStatus.PENDING
        error_code = ErrorCode.VALIDATION_ERROR
    enum_time = time.time() - start_time
    
    # Test result object creation performance
    start_time = time.time()
    for i in range(10000):
        result = TaskStepResult(
            step=f"step_{i}",
            result=f"result_{i}",
            completed=True,
            status=TaskStatus.COMPLETED.value
        )
    result_time = time.time() - start_time
    
    print(f"Enum creation time: {enum_time:.4f}s")
    print(f"Result creation time: {result_time:.4f}s")
```

#### Memory Usage Optimization
```python
def optimize_memory_usage():
    """Optimize memory usage"""
    import gc
    import sys
    
    # Create many objects
    results = []
    for i in range(10000):
        result = TaskStepResult(
            step=f"step_{i}",
            result=f"result_{i}",
            completed=True,
            status=TaskStatus.COMPLETED.value
        )
        results.append(result)
    
    print(f"Memory usage before cleanup: {sys.getsizeof(results)} bytes")
    
    # Clean up objects
    results.clear()
    gc.collect()
    
    print(f"Memory usage after cleanup: {sys.getsizeof(results)} bytes")
```

### 4. Data Migration

#### Model Version Upgrade
```python
def migrate_models_to_new_version(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate model data to new version"""
    # Check version
    version = old_data.get("version", "1.0")
    
    if version == "1.0":
        # Upgrade from 1.0 to 1.1
        if "status" in old_data:
            # Update status values
            if old_data["status"] == "success":
                old_data["status"] = "completed"
            elif old_data["status"] == "error":
                old_data["status"] = "failed"
        
        old_data["version"] = "1.1"
    
    return old_data
```

#### Data Format Conversion
```python
def convert_data_formats():
    """Convert data formats"""
    # Convert from old format to new format
    old_result = {
        "operation": "data_processing",
        "output": {"rows": 1000},
        "success": True,
        "message": "Processing completed"
    }
    
    # Convert to new format
    new_result = TaskStepResult(
        step=old_result["operation"],
        result=old_result["output"],
        completed=old_result["success"],
        message=old_result["message"],
        status=TaskStatus.COMPLETED.value if old_result["success"] else TaskStatus.FAILED.value
    )
    
    print(f"Converted result: {new_result}")
```

## Monitoring and Logging

### Model Usage Monitoring
```python
import time
from typing import Dict, Any

class ExecutionModelsMonitor:
    """Execution Models Monitor"""
    
    def __init__(self):
        self.creation_metrics = {
            "status_objects": 0,
            "error_code_objects": 0,
            "result_objects": 0
        }
        self.performance_metrics = {
            "status_creation_time": [],
            "error_code_creation_time": [],
            "result_creation_time": []
        }
    
    def record_status_creation(self, creation_time: float):
        """Record status object creation metrics"""
        self.creation_metrics["status_objects"] += 1
        self.performance_metrics["status_creation_time"].append(creation_time)
    
    def record_error_code_creation(self, creation_time: float):
        """Record error code object creation metrics"""
        self.creation_metrics["error_code_objects"] += 1
        self.performance_metrics["error_code_creation_time"].append(creation_time)
    
    def record_result_creation(self, creation_time: float):
        """Record result object creation metrics"""
        self.creation_metrics["result_objects"] += 1
        self.performance_metrics["result_creation_time"].append(creation_time)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        report = {}
        
        for metric_name, times in self.performance_metrics.items():
            if times:
                report[metric_name] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times)
                }
        
        return report
```

### Logging
```python
import logging
from typing import Dict, Any

class ExecutionModelsLogger:
    """Execution Models Logger"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_status_creation(self, status: TaskStatus):
        """Log status creation"""
        self.logger.info(f"TaskStatus created: {status.value}")
    
    def log_error_code_creation(self, error_code: ErrorCode):
        """Log error code creation"""
        self.logger.info(f"ErrorCode created: {error_code.value}")
    
    def log_result_creation(self, result: TaskStepResult):
        """Log result creation"""
        self.logger.info(f"TaskStepResult created: {result.step} - {result.status}")
    
    def log_validation_error(self, error: Exception, context: str):
        """Log validation error"""
        self.logger.error(f"Validation error in {context}: {error}")
```

## Version History

- **v1.0.0**: Initial version, basic state and error code definitions
- **v1.1.0**: Added task step result model
- **v1.2.0**: Added serialization support
- **v1.3.0**: Added performance monitoring and logging
- **v1.4.0**: Added data migration support

## Related Documentation

- [AIECS Project Overview](../PROJECT_SUMMARY.md)
- [Operation Executor Documentation](../APPLICATION/OPERATION_EXECUTOR.md)
- [Execution Interfaces Documentation](../CORE/EXECUTION_INTERFACES.md)
- [Configuration Management Documentation](../CONFIG/CONFIG_MANAGEMENT.md)
