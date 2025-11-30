# DSL Processor Technical Documentation

## Overview

### Design Motivation and Problem Background

When building complex AI application systems, task execution and flow control face the following core challenges:

**1. Complex Task Flow Management**
- Need to support complex control flows such as conditional branches, parallel execution, and loops
- Traditional programming approaches struggle with dynamic task flows
- Lack of declarative task flow definition mechanisms

**2. Condition Evaluation Complexity**
- Need to support multiple condition types (intent, context, input, result)
- Condition expressions need to support logical operations (AND, OR)
- Lack of unified condition evaluation mechanism

**3. Task Execution Flexibility**
- Need to support different types of task steps (if, parallel, sequence, task, loop)
- Task execution needs to support asynchronous and concurrent execution
- Lack of standardized task execution interface

**4. Error Handling and Debugging**
- Complex DSL expressions are difficult to debug
- Error information needs to precisely locate specific steps
- Lack of comprehensive error handling and logging

**DSL Processor System Solution**:
- **Declarative DSL**: JSON-based declarative task flow definition
- **Condition Evaluation Engine**: Supports multiple condition types and logical operations
- **Step Type Support**: Supports step types such as if, parallel, sequence, task, loop
- **Asynchronous Execution**: Supports asynchronous and concurrent task execution
- **Error Handling**: Comprehensive error handling and debugging support

### Component Positioning

`dsl_processor.py` is a domain service component of the AIECS system, located in the Domain Layer, implementing core business logic for DSL parsing and execution. As the system's flow control core, it provides declarative task flow definition and execution capabilities.

## Component Type and Positioning

### Component Type
**Domain Service Component** - Located in the Domain Layer, belongs to the business logic layer

### Architecture Layers
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← Components using DSL processor
│  (OperationExecutor, TaskManager)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← DSL processor layer
│  (DSLProcessor, Business Logic)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← Components DSL processor depends on
│  (Tracing, Logging, AsyncIO)           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Systems                │  ← External systems
│  (Task Execution, Monitoring)          │
└─────────────────────────────────────────┘
```

## Upstream Components (Consumers)

### 1. Application Layer Services
- **OperationExecutor** (`application/executors/operation_executor.py`)
- **TaskManager** (if exists)
- **ExecutionService** (if exists)

### 2. Domain Services
- **TaskContext** (`domain/task/task_context.py`)
- **Other task-related services** (if exists)

### 3. Infrastructure Layer
- **Tracing System** (via tracer parameter)
- **Logging System** (via logger)
- **AsyncIO System** (via asyncio)

## Downstream Components (Dependencies)

### 1. Execution Models
- **TaskStepResult** (`domain/execution/model.py`)
- **TaskStatus** (`domain/execution/model.py`)
- **ErrorCode** (`domain/execution/model.py`)

### 2. Python Standard Library
- **re** - Regular expression support
- **json** - JSON processing
- **logging** - Logging
- **asyncio** - Asynchronous programming support
- **typing** - Type annotation support

### 3. Task Execution Functions
- **execute_single_task** - Single task execution function
- **execute_batch_task** - Batch task execution function

## Core Functionality Details

### 1. Condition Evaluation Engine

#### Supported Condition Types
```python
# Intent condition
"intent.includes('data_analysis')"

# Context condition
"context.user_type == 'premium'"
"context.priority > 5"

# Input condition
"input.file_type == 'csv'"
"input.size > 1000"

# Result condition
"result[0].status == 'completed'"
"result[1].count > 100"
```

#### Logical Operation Support
```python
# AND operation
"intent.includes('data_analysis') AND context.user_type == 'premium'"

# OR operation
"input.file_type == 'csv' OR input.file_type == 'xlsx'"

# Complex condition
"intent.includes('data_analysis') AND (context.priority > 5 OR input.size > 1000)"
```

#### Condition Evaluation Method
```python
def evaluate_condition(self, condition: str, intent_categories: List[str],
                      context: Dict[str, Any] = None, input_data: Dict[str, Any] = None,
                      results: List[TaskStepResult] = None) -> bool:
    """Evaluate condition expression, supporting multiple condition types"""
    try:
        # 1. Complex condition: support AND (highest priority)
        if " AND " in condition:
            parts = condition.split(" AND ")
            return all(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

        # 2. Complex condition: support OR (second priority)
        if " OR " in condition:
            parts = condition.split(" OR ")
            return any(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

        # 3. Intent condition: intent.includes('category')
        match = re.fullmatch(r"intent\.includes\('([^']+)'\)", condition)
        if match:
            category = match.group(1)
            return category in intent_categories

        # 4. Context condition: context.field == value
        match = re.fullmatch(r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
        if match and context:
            field, operator, value = match.groups()
            return self._evaluate_comparison(context.get(field), operator, self._parse_value(value))

        # 5. Input condition: input.field == value
        match = re.fullmatch(r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
        if match and input_data:
            field, operator, value = match.groups()
            return self._evaluate_comparison(input_data.get(field), operator, self._parse_value(value))

        # 6. Result condition: result[0].field == value
        match = re.fullmatch(r"result\[(\d+)\]\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
        if match and results:
            index, field, operator, value = match.groups()
            index = int(index)
            if index < len(results) and results[index].result:
                result_value = results[index].result.get(field) if isinstance(results[index].result, dict) else None
                return self._evaluate_comparison(result_value, operator, self._parse_value(value))

        raise ValueError(f"Unsupported condition format: {condition}")

    except Exception as e:
        logger.error(f"Failed to evaluate condition '{condition}': {e}")
        raise ValueError(f"Failed to evaluate condition '{condition}': {e}")
```

### 2. Step Type Support

#### IF Step - Conditional Branch
```python
{
    "if": {
        "condition": "intent.includes('data_analysis')",
        "then": {
            "task": "pandas_tool.read_csv",
            "params": {"file_path": "data.csv"}
        },
        "else": {
            "task": "json_tool.read_json",
            "params": {"file_path": "data.json"}
        }
    }
}
```

#### PARALLEL Step - Parallel Execution
```python
{
    "parallel": {
        "tasks": [
            {
                "task": "pandas_tool.read_csv",
                "params": {"file_path": "data1.csv"}
            },
            {
                "task": "pandas_tool.read_csv",
                "params": {"file_path": "data2.csv"}
            }
        ]
    }
}
```

#### SEQUENCE Step - Sequential Execution
```python
{
    "sequence": {
        "steps": [
            {
                "task": "pandas_tool.read_csv",
                "params": {"file_path": "data.csv"}
            },
            {
                "task": "pandas_tool.clean_data",
                "params": {"data": "{{result[0].result}}"}
            }
        ]
    }
}
```

#### TASK Step - Single Task Execution
```python
{
    "task": "pandas_tool.read_csv",
    "params": {
        "file_path": "data.csv",
        "encoding": "utf-8"
    }
}
```

#### LOOP Step - Loop Execution
```python
{
    "loop": {
        "condition": "result[0].count > 0",
        "steps": [
            {
                "task": "pandas_tool.process_batch",
                "params": {"batch_size": 100}
            }
        ]
    }
}
```

### 3. Value Parsing and Comparison

#### Value Parsing Method
```python
def _parse_value(self, value_str: str) -> Any:
    """Parse value string to appropriate type"""
    value_str = value_str.strip()

    # String value
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str.startswith("'") and value_str.endswith("'"):
        return value_str[1:-1]

    # Boolean value
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # Numeric value
    try:
        if "." in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # Default return string
    return value_str
```

#### Comparison Operation Support
```python
def _evaluate_comparison(self, left_value: Any, operator: str, right_value: Any) -> bool:
    """Evaluate comparison operation"""
    try:
        if operator == "==":
            return left_value == right_value
        elif operator == "!=":
            return left_value != right_value
        elif operator == ">":
            return left_value > right_value
        elif operator == "<":
            return left_value < right_value
        elif operator == ">=":
            return left_value >= right_value
        elif operator == "<=":
            return left_value <= right_value
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    except TypeError:
        # Return False when types don't match
        return False
```

### 4. Async Execution Support

#### Main Execution Method
```python
async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                          context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                          results: List[TaskStepResult] = None) -> TaskStepResult:
    """Execute DSL step based on step type"""
    span = self.tracer.start_span("execute_dsl_step") if self.tracer else None
    if span:
        span.set_tag("step", json.dumps(step))

    try:
        if "if" in step:
            return await self._handle_if_step(step, intent_categories, input_data, context,
                                            execute_single_task, execute_batch_task, span, results)
        elif "parallel" in step:
            return await self._handle_parallel_step(step, input_data, context, execute_batch_task, span)
        elif "sequence" in step:
            return await self._handle_sequence_step(step, intent_categories, input_data, context,
                                                  execute_single_task, execute_batch_task, span, results)
        elif "task" in step:
            return await self._handle_task_step(step, input_data, context, execute_single_task, span)
        elif "loop" in step:
            return await self._handle_loop_step(step, intent_categories, input_data, context,
                                              execute_single_task, execute_batch_task, span, results)
        else:
            if span:
                span.set_tag("error", True)
                span.log_kv({"error_message": "Invalid DSL step"})
            return TaskStepResult(
                step="unknown",
                result=None,
                completed=False,
                message="Invalid DSL step",
                status=TaskStatus.FAILED.value,
                error_code=ErrorCode.EXECUTION_ERROR.value,
                error_message="Unknown DSL step type"
            )
    finally:
        if span:
            span.finish()
```

## Design Patterns Explained

### 1. Strategy Pattern
```python
# Different step types use different processing strategies
if "if" in step:
    return await self._handle_if_step(...)
elif "parallel" in step:
    return await self._handle_parallel_step(...)
elif "sequence" in step:
    return await self._handle_sequence_step(...)
```

**Advantages**:
- **Algorithm Encapsulation**: Encapsulates processing algorithms for different step types in independent methods
- **Easy Extension**: Adding new step types only requires adding new processing methods
- **Code Reuse**: Common logic can be implemented in base classes

### 2. Template Method Pattern
```python
async def execute_dsl_step(self, step: Dict, ...):
    """Template method - defines common flow for executing steps"""
    span = self.tracer.start_span("execute_dsl_step") if self.tracer else None
    try:
        # Select specific implementation based on step type
        result = await self._execute_specific_step(step, ...)
        return result
    finally:
        if span:
            span.finish()
```

**Advantages**:
- **Unified Flow**: Defines unified execution flow
- **Step Reuse**: Common steps can be reused in template methods
- **Easy Maintenance**: Modifying flow only requires modifying template method

### 3. Chain of Responsibility Pattern
```python
def evaluate_condition(self, condition: str, ...):
    """Chain of responsibility - try condition evaluation in priority order"""
    # 1. Complex condition: support AND (highest priority)
    if " AND " in condition:
        return self._handle_and_condition(condition, ...)
    
    # 2. Complex condition: support OR (second priority)
    if " OR " in condition:
        return self._handle_or_condition(condition, ...)
    
    # 3. Intent condition
    if self._is_intent_condition(condition):
        return self._handle_intent_condition(condition, ...)
    
    # 4. Context condition
    if self._is_context_condition(condition):
        return self._handle_context_condition(condition, ...)
    
    # More condition types...
```

**Advantages**:
- **Decoupling**: Decouples condition evaluation logic into independent methods
- **Extensibility**: Adding new condition types only requires adding new processing methods
- **Flexibility**: Can dynamically adjust condition evaluation order

## Usage Examples

### 1. Basic Condition Evaluation

```python
from aiecs.domain.task.dsl_processor import DSLProcessor

# Create DSL processor
processor = DSLProcessor()

# Evaluate intent condition
intent_categories = ["data_analysis", "visualization"]
condition = "intent.includes('data_analysis')"
result = processor.evaluate_condition(condition, intent_categories)
print(f"Intent condition result: {result}")  # True

# Evaluate context condition
context = {"user_type": "premium", "priority": 8}
condition = "context.user_type == 'premium' AND context.priority > 5"
result = processor.evaluate_condition(condition, [], context)
print(f"Context condition result: {result}")  # True

# Evaluate input condition
input_data = {"file_type": "csv", "size": 1500}
condition = "input.file_type == 'csv' OR input.size > 1000"
result = processor.evaluate_condition(condition, [], None, input_data)
print(f"Input condition result: {result}")  # True
```

### 2. Complex Condition Evaluation

```python
# Complex condition evaluation
condition = "intent.includes('data_analysis') AND (context.user_type == 'premium' OR input.size > 1000)"
intent_categories = ["data_analysis"]
context = {"user_type": "basic"}
input_data = {"size": 1500}

result = processor.evaluate_condition(condition, intent_categories, context, input_data)
print(f"Complex condition result: {result}")  # True

# Result condition evaluation
from aiecs.domain.execution.model import TaskStepResult, TaskStatus

results = [
    TaskStepResult("step1", {"status": "completed", "count": 100}, True, "Step 1 completed", TaskStatus.COMPLETED.value),
    TaskStepResult("step2", {"status": "failed", "count": 0}, False, "Step 2 failed", TaskStatus.FAILED.value)
]

condition = "result[0].status == 'completed' AND result[0].count > 50"
result = processor.evaluate_condition(condition, [], None, None, results)
print(f"Result condition result: {result}")  # True
```

### 3. DSL Step Execution

```python
import asyncio

async def execute_dsl_example():
    """Execute DSL example"""
    
    # Define execution functions
    async def execute_single_task(task_name: str, params: Dict[str, Any]) -> TaskStepResult:
        """Simulate single task execution"""
        return TaskStepResult(
            step=task_name,
            result={"status": "completed", "data": f"Result of {task_name}"},
            completed=True,
            message=f"Task {task_name} completed",
            status=TaskStatus.COMPLETED.value
        )
    
    async def execute_batch_task(tasks: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """Simulate batch task execution"""
        results = []
        for task in tasks:
            result = await execute_single_task(task["task"], task.get("params", {}))
            results.append(result)
        return results
    
    # Create DSL processor
    processor = DSLProcessor()
    
    # Execute IF step
    if_step = {
        "if": {
            "condition": "intent.includes('data_analysis')",
            "then": {
                "task": "pandas_tool.read_csv",
                "params": {"file_path": "data.csv"}
            },
            "else": {
                "task": "json_tool.read_json",
                "params": {"file_path": "data.json"}
            }
        }
    }
    
    intent_categories = ["data_analysis"]
    input_data = {}
    context = {}
    
    result = await processor.execute_dsl_step(
        if_step, intent_categories, input_data, context,
        execute_single_task, execute_batch_task
    )
    
    print(f"IF step result: {result}")
    
    # Execute PARALLEL step
    parallel_step = {
        "parallel": {
            "tasks": [
                {
                    "task": "pandas_tool.read_csv",
                    "params": {"file_path": "data1.csv"}
                },
                {
                    "task": "pandas_tool.read_csv",
                    "params": {"file_path": "data2.csv"}
                }
            ]
        }
    }
    
    result = await processor.execute_dsl_step(
        parallel_step, intent_categories, input_data, context,
        execute_single_task, execute_batch_task
    )
    
    print(f"Parallel step result: {result}")

# Run example
asyncio.run(execute_dsl_example())
```

### 4. Condition Syntax Validation

```python
# Validate condition syntax
def validate_conditions():
    """Validate condition syntax"""
    processor = DSLProcessor()
    
    # Valid conditions
    valid_conditions = [
        "intent.includes('data_analysis')",
        "context.user_type == 'premium'",
        "input.file_type == 'csv'",
        "result[0].status == 'completed'",
        "intent.includes('data_analysis') AND context.user_type == 'premium'",
        "input.file_type == 'csv' OR input.file_type == 'xlsx'"
    ]
    
    for condition in valid_conditions:
        is_valid = processor.validate_condition_syntax(condition)
        print(f"Condition '{condition}' is valid: {is_valid}")
    
    # Invalid conditions
    invalid_conditions = [
        "",
        "invalid_condition",
        "context.field == value AND",  # Incomplete AND
        "result[].field == value"  # Invalid array index
    ]
    
    for condition in invalid_conditions:
        is_valid = processor.validate_condition_syntax(condition)
        print(f"Condition '{condition}' is valid: {is_valid}")

validate_conditions()
```

## Maintenance Guide

### 1. Daily Maintenance

#### Condition Pattern Validation
```python
def validate_condition_patterns():
    """Validate condition patterns"""
    processor = DSLProcessor()
    
    # Test supported condition patterns
    test_conditions = [
        "intent.includes('test')",
        "context.field == 'value'",
        "input.field > 100",
        "result[0].field != 'error'"
    ]
    
    for condition in test_conditions:
        try:
            result = processor.evaluate_condition(condition, ["test"], {"field": "value"}, {"field": 100})
            print(f"✅ Condition '{condition}' evaluated successfully")
        except Exception as e:
            print(f"❌ Condition '{condition}' failed: {e}")
```

#### Step Type Validation
```python
def validate_step_types():
    """Validate step types"""
    processor = DSLProcessor()
    
    # Test supported step types
    step_types = ["if", "parallel", "sequence", "task", "loop"]
    
    for step_type in step_types:
        step = {step_type: {"test": "value"}}
        try:
            # This only tests step type recognition, doesn't execute actual tasks
            if step_type in step:
                print(f"✅ Step type '{step_type}' is supported")
            else:
                print(f"❌ Step type '{step_type}' is not supported")
        except Exception as e:
            print(f"❌ Step type '{step_type}' validation failed: {e}")
```

### 2. Troubleshooting

#### Common Issue Diagnosis

**Issue 1: Condition Evaluation Failure**
```python
def diagnose_condition_evaluation_error():
    """Diagnose condition evaluation errors"""
    processor = DSLProcessor()
    
    # Test various condition types
    test_cases = [
        {
            "condition": "intent.includes('test')",
            "intent_categories": ["test"],
            "expected": True
        },
        {
            "condition": "context.field == 'value'",
            "context": {"field": "value"},
            "expected": True
        },
        {
            "condition": "input.field > 100",
            "input_data": {"field": 150},
            "expected": True
        }
    ]
    
    for test_case in test_cases:
        try:
            result = processor.evaluate_condition(
                test_case["condition"],
                test_case.get("intent_categories", []),
                test_case.get("context"),
                test_case.get("input_data")
            )
            expected = test_case["expected"]
            if result == expected:
                print(f"✅ Condition '{test_case['condition']}' evaluated correctly")
            else:
                print(f"❌ Condition '{test_case['condition']}' evaluated incorrectly: {result} != {expected}")
        except Exception as e:
            print(f"❌ Condition '{test_case['condition']}' failed: {e}")
```

**Issue 2: Step Execution Failure**
```python
def diagnose_step_execution_error():
    """Diagnose step execution errors"""
    processor = DSLProcessor()
    
    # Test invalid steps
    invalid_steps = [
        {"unknown": "value"},  # Unknown step type
        {"if": "invalid"},     # Invalid if step
        {"parallel": []},      # Empty parallel step
    ]
    
    async def mock_execute_single_task(task_name: str, params: Dict[str, Any]):
        return TaskStepResult(task_name, "mock_result", True, "Mock completed", TaskStatus.COMPLETED.value)
    
    async def mock_execute_batch_task(tasks: List[Dict[str, Any]]):
        return [TaskStepResult(task["task"], "mock_result", True, "Mock completed", TaskStatus.COMPLETED.value) for task in tasks]
    
    async def test_steps():
        for step in invalid_steps:
            try:
                result = await processor.execute_dsl_step(
                    step, [], {}, {}, mock_execute_single_task, mock_execute_batch_task
                )
                if result.completed:
                    print(f"✅ Step executed successfully: {step}")
                else:
                    print(f"❌ Step execution failed: {result.message}")
            except Exception as e:
                print(f"❌ Step execution error: {e}")
    
    import asyncio
    asyncio.run(test_steps())
```

### 3. Performance Optimization

#### Condition Evaluation Optimization
```python
def optimize_condition_evaluation():
    """Optimize condition evaluation performance"""
    import time
    
    processor = DSLProcessor()
    
    # Test condition evaluation performance
    condition = "intent.includes('test') AND context.field == 'value'"
    intent_categories = ["test"]
    context = {"field": "value"}
    
    # Warm-up
    for _ in range(100):
        processor.evaluate_condition(condition, intent_categories, context)
    
    # Performance test
    start_time = time.time()
    for _ in range(10000):
        processor.evaluate_condition(condition, intent_categories, context)
    end_time = time.time()
    
    print(f"Condition evaluation time: {(end_time - start_time) * 1000:.2f}ms for 10000 iterations")
```

#### Memory Usage Optimization
```python
def optimize_memory_usage():
    """Optimize memory usage"""
    import gc
    import sys
    
    processor = DSLProcessor()
    
    # Create many conditions
    conditions = []
    for i in range(10000):
        condition = f"intent.includes('test_{i}')"
        conditions.append(condition)
    
    print(f"Memory usage before evaluation: {sys.getsizeof(conditions)} bytes")
    
    # Evaluate conditions
    intent_categories = ["test_0"]
    for condition in conditions[:1000]:  # Only evaluate first 1000
        processor.evaluate_condition(condition, intent_categories)
    
    # Cleanup
    conditions.clear()
    gc.collect()
    
    print(f"Memory usage after cleanup: {sys.getsizeof(conditions)} bytes")
```

### 4. Extension Support

#### Adding New Condition Types
```python
class ExtendedDSLProcessor(DSLProcessor):
    """Extended DSL processor supporting new condition types"""
    
    def __init__(self, tracer=None):
        super().__init__(tracer)
        # Add new condition patterns
        self.supported_conditions.extend([
            r"config\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",  # Config condition
            r"env\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)"      # Environment variable condition
        ])
    
    def evaluate_condition(self, condition: str, intent_categories: List[str],
                          context: Dict[str, Any] = None, input_data: Dict[str, Any] = None,
                          results: List[TaskStepResult] = None, config: Dict[str, Any] = None,
                          env_vars: Dict[str, str] = None) -> bool:
        """Extended condition evaluation method"""
        try:
            # Call parent method
            result = super().evaluate_condition(condition, intent_categories, context, input_data, results)
            if result is not None:
                return result
            
            # Handle config condition
            match = re.fullmatch(r"config\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and config:
                field, operator, value = match.groups()
                return self._evaluate_comparison(config.get(field), operator, self._parse_value(value))
            
            # Handle environment variable condition
            match = re.fullmatch(r"env\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and env_vars:
                field, operator, value = match.groups()
                return self._evaluate_comparison(env_vars.get(field), operator, self._parse_value(value))
            
            raise ValueError(f"Unsupported condition format: {condition}")
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            raise ValueError(f"Failed to evaluate condition '{condition}': {e}")
```

#### Adding New Step Types
```python
class ExtendedDSLProcessor(DSLProcessor):
    """Extended DSL processor supporting new step types"""
    
    async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                              context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                              results: List[TaskStepResult] = None) -> TaskStepResult:
        """Extended step execution method"""
        # Check new step types
        if "retry" in step:
            return await self._handle_retry_step(step, intent_categories, input_data, context,
                                               execute_single_task, execute_batch_task, results)
        elif "timeout" in step:
            return await self._handle_timeout_step(step, intent_categories, input_data, context,
                                                 execute_single_task, execute_batch_task, results)
        else:
            # Call parent method
            return await super().execute_dsl_step(step, intent_categories, input_data, context,
                                                execute_single_task, execute_batch_task, results)
    
    async def _handle_retry_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                                context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                                results: List[TaskStepResult] = None) -> TaskStepResult:
        """Handle retry step"""
        retry_config = step["retry"]
        max_retries = retry_config.get("max_retries", 3)
        delay = retry_config.get("delay", 1.0)
        
        for attempt in range(max_retries + 1):
            try:
                result = await execute_single_task(retry_config["task"], retry_config.get("params", {}))
                if result.completed:
                    return result
            except Exception as e:
                if attempt == max_retries:
                    return TaskStepResult(
                        step=retry_config["task"],
                        result=None,
                        completed=False,
                        message=f"Retry exhausted after {max_retries} attempts",
                        status=TaskStatus.FAILED.value,
                        error_code=ErrorCode.RETRY_EXHAUSTED.value,
                        error_message=str(e)
                    )
                await asyncio.sleep(delay)
        
        return TaskStepResult(
            step=retry_config["task"],
            result=None,
            completed=False,
            message="Retry step failed",
            status=TaskStatus.FAILED.value,
            error_code=ErrorCode.EXECUTION_ERROR.value
        )
```

## Monitoring and Logging

### Performance Monitoring
```python
import time
from typing import Dict, Any

class DSLProcessorMonitor:
    """DSL Processor Monitor"""
    
    def __init__(self):
        self.evaluation_metrics = {
            "total_evaluations": 0,
            "successful_evaluations": 0,
            "failed_evaluations": 0
        }
        self.execution_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0
        }
        self.performance_metrics = {
            "evaluation_times": [],
            "execution_times": []
        }
    
    def record_condition_evaluation(self, condition: str, success: bool, evaluation_time: float):
        """Record condition evaluation metrics"""
        self.evaluation_metrics["total_evaluations"] += 1
        if success:
            self.evaluation_metrics["successful_evaluations"] += 1
        else:
            self.evaluation_metrics["failed_evaluations"] += 1
        
        self.performance_metrics["evaluation_times"].append(evaluation_time)
    
    def record_step_execution(self, step_type: str, success: bool, execution_time: float):
        """Record step execution metrics"""
        self.execution_metrics["total_executions"] += 1
        if success:
            self.execution_metrics["successful_executions"] += 1
        else:
            self.execution_metrics["failed_executions"] += 1
        
        self.performance_metrics["execution_times"].append(execution_time)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        report = {
            "evaluation_metrics": self.evaluation_metrics.copy(),
            "execution_metrics": self.execution_metrics.copy()
        }
        
        # Calculate evaluation performance
        if self.performance_metrics["evaluation_times"]:
            times = self.performance_metrics["evaluation_times"]
            report["evaluation_performance"] = {
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        # Calculate execution performance
        if self.performance_metrics["execution_times"]:
            times = self.performance_metrics["execution_times"]
            report["execution_performance"] = {
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

class DSLProcessorLogger:
    """DSL Processor Logger"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_condition_evaluation(self, condition: str, result: bool, evaluation_time: float):
        """Log condition evaluation"""
        self.logger.info(f"Condition evaluated: '{condition}' -> {result} ({evaluation_time:.3f}s)")
    
    def log_step_execution(self, step_type: str, step: Dict[str, Any], result: TaskStepResult):
        """Log step execution"""
        if result.completed:
            self.logger.info(f"Step executed successfully: {step_type} -> {result.step}")
        else:
            self.logger.error(f"Step execution failed: {step_type} -> {result.step}: {result.error_message}")
    
    def log_validation_error(self, condition: str, error: Exception):
        """Log validation error"""
        self.logger.error(f"Condition validation failed: '{condition}' - {error}")
    
    def log_execution_error(self, step: Dict[str, Any], error: Exception):
        """Log execution error"""
        self.logger.error(f"Step execution error: {step} - {error}")
```

## Version History

- **v1.0.0**: Initial version, basic condition evaluation and step execution
- **v1.1.0**: Added parallel and sequential step support
- **v1.2.0**: Added loop step support
- **v1.3.0**: Added condition syntax validation
- **v1.4.0**: Added performance monitoring and logging
- **v1.5.0**: Added extension support

## Related Documentation

- [AIECS Project Overview](../PROJECT_SUMMARY.md)
- [Task Context Documentation](./TASK_CONTEXT.md)
- [Execution Models Documentation](../DOMAIN_EXECUTION/EXECUTION_MODELS.md)
- [Operation Executor Documentation](../APPLICATION/OPERATION_EXECUTOR.md)
