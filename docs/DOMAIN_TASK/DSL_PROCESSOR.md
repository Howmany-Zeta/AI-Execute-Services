# DSL 处理器技术文档

## 概述

### 设计动机与问题背景

在构建复杂的 AI 应用系统时，任务执行和流程控制面临以下核心挑战：

**1. 复杂任务流程管理**
- 需要支持条件分支、并行执行、循环等复杂控制流
- 传统编程方式难以处理动态任务流程
- 缺乏声明式的任务流程定义机制

**2. 条件判断复杂性**
- 需要支持多种条件类型（意图、上下文、输入、结果）
- 条件表达式需要支持逻辑运算（AND、OR）
- 缺乏统一的条件评估机制

**3. 任务执行灵活性**
- 需要支持不同类型的任务步骤（if、parallel、sequence、task、loop）
- 任务执行需要支持异步和并发
- 缺乏标准化的任务执行接口

**4. 错误处理和调试**
- 复杂的 DSL 表达式难以调试
- 错误信息需要精确定位到具体步骤
- 缺乏完善的错误处理和日志记录

**DSL 处理器系统的解决方案**：
- **声明式 DSL**：基于 JSON 的声明式任务流程定义
- **条件评估引擎**：支持多种条件类型和逻辑运算
- **步骤类型支持**：支持 if、parallel、sequence、task、loop 等步骤类型
- **异步执行**：支持异步和并发的任务执行
- **错误处理**：完善的错误处理和调试支持

### 组件定位

`dsl_processor.py` 是 AIECS 系统的领域服务组件，位于领域层 (Domain Layer)，实现了 DSL 解析和执行的核心业务逻辑。作为系统的流程控制核心，它提供了声明式的任务流程定义和执行能力。

## 组件类型与定位

### 组件类型
**领域服务组件** - 位于领域层 (Domain Layer)，属于业务逻辑层

### 架构层次
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← 使用 DSL 处理器的组件
│  (OperationExecutor, TaskManager)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← DSL 处理器所在层
│  (DSLProcessor, Business Logic)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← DSL 处理器依赖的组件
│  (Tracing, Logging, AsyncIO)           │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Systems                │  ← 外部系统
│  (Task Execution, Monitoring)          │
└─────────────────────────────────────────┘
```

## 上游组件（使用方）

### 1. 应用层服务
- **OperationExecutor** (`application/executors/operation_executor.py`)
- **TaskManager** (如果存在)
- **ExecutionService** (如果存在)

### 2. 领域服务
- **TaskContext** (`domain/task/task_context.py`)
- **其他任务相关服务** (如果存在)

### 3. 基础设施层
- **Tracing 系统** (通过 tracer 参数)
- **Logging 系统** (通过 logger)
- **AsyncIO 系统** (通过 asyncio)

## 下游组件（被依赖方）

### 1. 执行模型
- **TaskStepResult** (`domain/execution/model.py`)
- **TaskStatus** (`domain/execution/model.py`)
- **ErrorCode** (`domain/execution/model.py`)

### 2. Python 标准库
- **re** - 正则表达式支持
- **json** - JSON 处理
- **logging** - 日志记录
- **asyncio** - 异步编程支持
- **typing** - 类型注解支持

### 3. 任务执行函数
- **execute_single_task** - 单任务执行函数
- **execute_batch_task** - 批量任务执行函数

## 核心功能详解

### 1. 条件评估引擎 (Condition Evaluation Engine)

#### 支持的条件类型
```python
# 意图条件
"intent.includes('data_analysis')"

# 上下文条件
"context.user_type == 'premium'"
"context.priority > 5"

# 输入条件
"input.file_type == 'csv'"
"input.size > 1000"

# 结果条件
"result[0].status == 'completed'"
"result[1].count > 100"
```

#### 逻辑运算支持
```python
# AND 运算
"intent.includes('data_analysis') AND context.user_type == 'premium'"

# OR 运算
"input.file_type == 'csv' OR input.file_type == 'xlsx'"

# 复合条件
"intent.includes('data_analysis') AND (context.priority > 5 OR input.size > 1000)"
```

#### 条件评估方法
```python
def evaluate_condition(self, condition: str, intent_categories: List[str],
                      context: Dict[str, Any] = None, input_data: Dict[str, Any] = None,
                      results: List[TaskStepResult] = None) -> bool:
    """评估条件表达式，支持多种条件类型"""
    try:
        # 1. 复合条件：支持 AND (最高优先级)
        if " AND " in condition:
            parts = condition.split(" AND ")
            return all(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

        # 2. 复合条件：支持 OR (第二优先级)
        if " OR " in condition:
            parts = condition.split(" OR ")
            return any(self.evaluate_condition(part.strip(), intent_categories, context, input_data, results) for part in parts)

        # 3. 意图条件：intent.includes('category')
        match = re.fullmatch(r"intent\.includes\('([^']+)'\)", condition)
        if match:
            category = match.group(1)
            return category in intent_categories

        # 4. 上下文条件：context.field == value
        match = re.fullmatch(r"context\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
        if match and context:
            field, operator, value = match.groups()
            return self._evaluate_comparison(context.get(field), operator, self._parse_value(value))

        # 5. 输入条件：input.field == value
        match = re.fullmatch(r"input\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
        if match and input_data:
            field, operator, value = match.groups()
            return self._evaluate_comparison(input_data.get(field), operator, self._parse_value(value))

        # 6. 结果条件：result[0].field == value
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

### 2. 步骤类型支持 (Step Type Support)

#### IF 步骤 - 条件分支
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

#### PARALLEL 步骤 - 并行执行
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

#### SEQUENCE 步骤 - 顺序执行
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

#### TASK 步骤 - 单任务执行
```python
{
    "task": "pandas_tool.read_csv",
    "params": {
        "file_path": "data.csv",
        "encoding": "utf-8"
    }
}
```

#### LOOP 步骤 - 循环执行
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

### 3. 值解析和比较 (Value Parsing and Comparison)

#### 值解析方法
```python
def _parse_value(self, value_str: str) -> Any:
    """解析值字符串为适当类型"""
    value_str = value_str.strip()

    # 字符串值
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str.startswith("'") and value_str.endswith("'"):
        return value_str[1:-1]

    # 布尔值
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False

    # 数值
    try:
        if "." in value_str:
            return float(value_str)
        else:
            return int(value_str)
    except ValueError:
        pass

    # 默认返回字符串
    return value_str
```

#### 比较操作支持
```python
def _evaluate_comparison(self, left_value: Any, operator: str, right_value: Any) -> bool:
    """评估比较操作"""
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
        # 类型不匹配时返回 False
        return False
```

### 4. 异步执行支持 (Async Execution Support)

#### 主执行方法
```python
async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                          context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                          results: List[TaskStepResult] = None) -> TaskStepResult:
    """基于步骤类型执行 DSL 步骤"""
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

## 设计模式详解

### 1. 策略模式 (Strategy Pattern)
```python
# 不同步骤类型使用不同的处理策略
if "if" in step:
    return await self._handle_if_step(...)
elif "parallel" in step:
    return await self._handle_parallel_step(...)
elif "sequence" in step:
    return await self._handle_sequence_step(...)
```

**优势**：
- **算法封装**：将不同步骤类型的处理算法封装在独立方法中
- **易于扩展**：新增步骤类型只需添加新的处理方法
- **代码复用**：公共逻辑可以在基类中实现

### 2. 模板方法模式 (Template Method Pattern)
```python
async def execute_dsl_step(self, step: Dict, ...):
    """模板方法 - 定义执行步骤的通用流程"""
    span = self.tracer.start_span("execute_dsl_step") if self.tracer else None
    try:
        # 根据步骤类型选择具体实现
        result = await self._execute_specific_step(step, ...)
        return result
    finally:
        if span:
            span.finish()
```

**优势**：
- **流程统一**：定义统一的执行流程
- **步骤复用**：公共步骤可以在模板方法中复用
- **易于维护**：修改流程只需修改模板方法

### 3. 责任链模式 (Chain of Responsibility Pattern)
```python
def evaluate_condition(self, condition: str, ...):
    """责任链 - 按优先级依次尝试条件评估"""
    # 1. 复合条件：支持 AND (最高优先级)
    if " AND " in condition:
        return self._handle_and_condition(condition, ...)
    
    # 2. 复合条件：支持 OR (第二优先级)
    if " OR " in condition:
        return self._handle_or_condition(condition, ...)
    
    # 3. 意图条件
    if self._is_intent_condition(condition):
        return self._handle_intent_condition(condition, ...)
    
    # 4. 上下文条件
    if self._is_context_condition(condition):
        return self._handle_context_condition(condition, ...)
    
    # 更多条件类型...
```

**优势**：
- **解耦**：将条件评估逻辑解耦到独立方法中
- **扩展性**：新增条件类型只需添加新的处理方法
- **灵活性**：可以动态调整条件评估顺序

## 使用示例

### 1. 基本条件评估

```python
from aiecs.domain.task.dsl_processor import DSLProcessor

# 创建 DSL 处理器
processor = DSLProcessor()

# 评估意图条件
intent_categories = ["data_analysis", "visualization"]
condition = "intent.includes('data_analysis')"
result = processor.evaluate_condition(condition, intent_categories)
print(f"Intent condition result: {result}")  # True

# 评估上下文条件
context = {"user_type": "premium", "priority": 8}
condition = "context.user_type == 'premium' AND context.priority > 5"
result = processor.evaluate_condition(condition, [], context)
print(f"Context condition result: {result}")  # True

# 评估输入条件
input_data = {"file_type": "csv", "size": 1500}
condition = "input.file_type == 'csv' OR input.size > 1000"
result = processor.evaluate_condition(condition, [], None, input_data)
print(f"Input condition result: {result}")  # True
```

### 2. 复杂条件评估

```python
# 复合条件评估
condition = "intent.includes('data_analysis') AND (context.user_type == 'premium' OR input.size > 1000)"
intent_categories = ["data_analysis"]
context = {"user_type": "basic"}
input_data = {"size": 1500}

result = processor.evaluate_condition(condition, intent_categories, context, input_data)
print(f"Complex condition result: {result}")  # True

# 结果条件评估
from aiecs.domain.execution.model import TaskStepResult, TaskStatus

results = [
    TaskStepResult("step1", {"status": "completed", "count": 100}, True, "Step 1 completed", TaskStatus.COMPLETED.value),
    TaskStepResult("step2", {"status": "failed", "count": 0}, False, "Step 2 failed", TaskStatus.FAILED.value)
]

condition = "result[0].status == 'completed' AND result[0].count > 50"
result = processor.evaluate_condition(condition, [], None, None, results)
print(f"Result condition result: {result}")  # True
```

### 3. DSL 步骤执行

```python
import asyncio

async def execute_dsl_example():
    """执行 DSL 示例"""
    
    # 定义执行函数
    async def execute_single_task(task_name: str, params: Dict[str, Any]) -> TaskStepResult:
        """模拟单任务执行"""
        return TaskStepResult(
            step=task_name,
            result={"status": "completed", "data": f"Result of {task_name}"},
            completed=True,
            message=f"Task {task_name} completed",
            status=TaskStatus.COMPLETED.value
        )
    
    async def execute_batch_task(tasks: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """模拟批量任务执行"""
        results = []
        for task in tasks:
            result = await execute_single_task(task["task"], task.get("params", {}))
            results.append(result)
        return results
    
    # 创建 DSL 处理器
    processor = DSLProcessor()
    
    # 执行 IF 步骤
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
    
    # 执行 PARALLEL 步骤
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

# 运行示例
asyncio.run(execute_dsl_example())
```

### 4. 条件语法验证

```python
# 验证条件语法
def validate_conditions():
    """验证条件语法"""
    processor = DSLProcessor()
    
    # 有效条件
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
    
    # 无效条件
    invalid_conditions = [
        "",
        "invalid_condition",
        "context.field == value AND",  # 不完整的 AND
        "result[].field == value"  # 无效的数组索引
    ]
    
    for condition in invalid_conditions:
        is_valid = processor.validate_condition_syntax(condition)
        print(f"Condition '{condition}' is valid: {is_valid}")

validate_conditions()
```

## 维护指南

### 1. 日常维护

#### 条件模式验证
```python
def validate_condition_patterns():
    """验证条件模式"""
    processor = DSLProcessor()
    
    # 测试支持的条件模式
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

#### 步骤类型验证
```python
def validate_step_types():
    """验证步骤类型"""
    processor = DSLProcessor()
    
    # 测试支持的步骤类型
    step_types = ["if", "parallel", "sequence", "task", "loop"]
    
    for step_type in step_types:
        step = {step_type: {"test": "value"}}
        try:
            # 这里只是测试步骤类型识别，不执行实际任务
            if step_type in step:
                print(f"✅ Step type '{step_type}' is supported")
            else:
                print(f"❌ Step type '{step_type}' is not supported")
        except Exception as e:
            print(f"❌ Step type '{step_type}' validation failed: {e}")
```

### 2. 故障排查

#### 常见问题诊断

**问题1: 条件评估失败**
```python
def diagnose_condition_evaluation_error():
    """诊断条件评估错误"""
    processor = DSLProcessor()
    
    # 测试各种条件类型
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

**问题2: 步骤执行失败**
```python
def diagnose_step_execution_error():
    """诊断步骤执行错误"""
    processor = DSLProcessor()
    
    # 测试无效步骤
    invalid_steps = [
        {"unknown": "value"},  # 未知步骤类型
        {"if": "invalid"},     # 无效的 if 步骤
        {"parallel": []},      # 空的 parallel 步骤
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

### 3. 性能优化

#### 条件评估优化
```python
def optimize_condition_evaluation():
    """优化条件评估性能"""
    import time
    
    processor = DSLProcessor()
    
    # 测试条件评估性能
    condition = "intent.includes('test') AND context.field == 'value'"
    intent_categories = ["test"]
    context = {"field": "value"}
    
    # 预热
    for _ in range(100):
        processor.evaluate_condition(condition, intent_categories, context)
    
    # 性能测试
    start_time = time.time()
    for _ in range(10000):
        processor.evaluate_condition(condition, intent_categories, context)
    end_time = time.time()
    
    print(f"Condition evaluation time: {(end_time - start_time) * 1000:.2f}ms for 10000 iterations")
```

#### 内存使用优化
```python
def optimize_memory_usage():
    """优化内存使用"""
    import gc
    import sys
    
    processor = DSLProcessor()
    
    # 创建大量条件
    conditions = []
    for i in range(10000):
        condition = f"intent.includes('test_{i}')"
        conditions.append(condition)
    
    print(f"Memory usage before evaluation: {sys.getsizeof(conditions)} bytes")
    
    # 评估条件
    intent_categories = ["test_0"]
    for condition in conditions[:1000]:  # 只评估前1000个
        processor.evaluate_condition(condition, intent_categories)
    
    # 清理
    conditions.clear()
    gc.collect()
    
    print(f"Memory usage after cleanup: {sys.getsizeof(conditions)} bytes")
```

### 4. 扩展支持

#### 新增条件类型
```python
class ExtendedDSLProcessor(DSLProcessor):
    """扩展的 DSL 处理器，支持新的条件类型"""
    
    def __init__(self, tracer=None):
        super().__init__(tracer)
        # 添加新的条件模式
        self.supported_conditions.extend([
            r"config\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)",  # 配置条件
            r"env\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)"      # 环境变量条件
        ])
    
    def evaluate_condition(self, condition: str, intent_categories: List[str],
                          context: Dict[str, Any] = None, input_data: Dict[str, Any] = None,
                          results: List[TaskStepResult] = None, config: Dict[str, Any] = None,
                          env_vars: Dict[str, str] = None) -> bool:
        """扩展的条件评估方法"""
        try:
            # 调用父类方法
            result = super().evaluate_condition(condition, intent_categories, context, input_data, results)
            if result is not None:
                return result
            
            # 处理配置条件
            match = re.fullmatch(r"config\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and config:
                field, operator, value = match.groups()
                return self._evaluate_comparison(config.get(field), operator, self._parse_value(value))
            
            # 处理环境变量条件
            match = re.fullmatch(r"env\.(\w+)\s*(==|!=|>|<|>=|<=)\s*(.+)", condition)
            if match and env_vars:
                field, operator, value = match.groups()
                return self._evaluate_comparison(env_vars.get(field), operator, self._parse_value(value))
            
            raise ValueError(f"Unsupported condition format: {condition}")
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            raise ValueError(f"Failed to evaluate condition '{condition}': {e}")
```

#### 新增步骤类型
```python
class ExtendedDSLProcessor(DSLProcessor):
    """扩展的 DSL 处理器，支持新的步骤类型"""
    
    async def execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                              context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                              results: List[TaskStepResult] = None) -> TaskStepResult:
        """扩展的步骤执行方法"""
        # 检查新步骤类型
        if "retry" in step:
            return await self._handle_retry_step(step, intent_categories, input_data, context,
                                               execute_single_task, execute_batch_task, results)
        elif "timeout" in step:
            return await self._handle_timeout_step(step, intent_categories, input_data, context,
                                                 execute_single_task, execute_batch_task, results)
        else:
            # 调用父类方法
            return await super().execute_dsl_step(step, intent_categories, input_data, context,
                                                execute_single_task, execute_batch_task, results)
    
    async def _handle_retry_step(self, step: Dict, intent_categories: List[str], input_data: Dict,
                                context: Dict, execute_single_task: Callable, execute_batch_task: Callable,
                                results: List[TaskStepResult] = None) -> TaskStepResult:
        """处理重试步骤"""
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

## 监控与日志

### 性能监控
```python
import time
from typing import Dict, Any

class DSLProcessorMonitor:
    """DSL 处理器监控器"""
    
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
        """记录条件评估指标"""
        self.evaluation_metrics["total_evaluations"] += 1
        if success:
            self.evaluation_metrics["successful_evaluations"] += 1
        else:
            self.evaluation_metrics["failed_evaluations"] += 1
        
        self.performance_metrics["evaluation_times"].append(evaluation_time)
    
    def record_step_execution(self, step_type: str, success: bool, execution_time: float):
        """记录步骤执行指标"""
        self.execution_metrics["total_executions"] += 1
        if success:
            self.execution_metrics["successful_executions"] += 1
        else:
            self.execution_metrics["failed_executions"] += 1
        
        self.performance_metrics["execution_times"].append(execution_time)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "evaluation_metrics": self.evaluation_metrics.copy(),
            "execution_metrics": self.execution_metrics.copy()
        }
        
        # 计算评估性能
        if self.performance_metrics["evaluation_times"]:
            times = self.performance_metrics["evaluation_times"]
            report["evaluation_performance"] = {
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        # 计算执行性能
        if self.performance_metrics["execution_times"]:
            times = self.performance_metrics["execution_times"]
            report["execution_performance"] = {
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times)
            }
        
        return report
```

### 日志记录
```python
import logging
from typing import Dict, Any

class DSLProcessorLogger:
    """DSL 处理器日志记录器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_condition_evaluation(self, condition: str, result: bool, evaluation_time: float):
        """记录条件评估日志"""
        self.logger.info(f"Condition evaluated: '{condition}' -> {result} ({evaluation_time:.3f}s)")
    
    def log_step_execution(self, step_type: str, step: Dict[str, Any], result: TaskStepResult):
        """记录步骤执行日志"""
        if result.completed:
            self.logger.info(f"Step executed successfully: {step_type} -> {result.step}")
        else:
            self.logger.error(f"Step execution failed: {step_type} -> {result.step}: {result.error_message}")
    
    def log_validation_error(self, condition: str, error: Exception):
        """记录验证错误日志"""
        self.logger.error(f"Condition validation failed: '{condition}' - {error}")
    
    def log_execution_error(self, step: Dict[str, Any], error: Exception):
        """记录执行错误日志"""
        self.logger.error(f"Step execution error: {step} - {error}")
```

## 版本历史

- **v1.0.0**: 初始版本，基础条件评估和步骤执行
- **v1.1.0**: 添加并行和顺序步骤支持
- **v1.2.0**: 添加循环步骤支持
- **v1.3.0**: 添加条件语法验证
- **v1.4.0**: 添加性能监控和日志记录
- **v1.5.0**: 添加扩展支持

## 相关文档

- [AIECS 项目总览](../PROJECT_SUMMARY.md)
- [任务上下文文档](./TASK_CONTEXT.md)
- [执行模型文档](./EXECUTION_MODELS.md)
- [操作执行器文档](./OPERATION_EXECUTOR.md)
