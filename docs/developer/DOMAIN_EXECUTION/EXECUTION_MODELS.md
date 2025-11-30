# 执行模型技术文档

## 概述

### 设计动机与问题背景

在构建复杂的 AI 应用系统时，任务执行和状态管理面临以下核心挑战：

**1. 任务状态管理复杂性**
- 需要支持多种任务状态（等待、运行、完成、取消、超时、失败）
- 状态转换需要遵循特定的业务规则
- 缺乏统一的状态定义和验证机制

**2. 错误处理标准化**
- 不同类型的错误需要不同的处理策略
- 错误信息需要结构化和可追踪
- 缺乏统一的错误码体系和分类机制

**3. 执行结果封装**
- 任务执行结果需要包含完整的状态信息
- 需要支持成功和失败两种结果类型
- 缺乏标准化的结果数据模型

**4. 系统集成需求**
- 执行模型需要与多个系统组件集成
- 需要支持序列化和反序列化
- 缺乏统一的数据契约定义

**执行模型系统的解决方案**：
- **枚举类型定义**：基于 Python Enum 的类型安全状态和错误码定义
- **结果模型封装**：结构化的任务步骤结果模型
- **统一错误处理**：标准化的错误码体系和错误信息
- **数据契约支持**：支持序列化和反序列化的数据模型
- **类型安全**：基于 Python 类型系统的类型安全保证

### 组件定位

`execution/model.py` 是 AIECS 系统的领域模型组件，位于领域层 (Domain Layer)，定义了任务执行相关的核心数据模型。作为系统的数据契约层，它提供了类型安全、结构化的执行状态、错误码和结果模型。

## 组件类型与定位

### 组件类型
**领域模型组件** - 位于领域层 (Domain Layer)，属于数据契约定义

### 架构层次
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← 使用执行模型的组件
│  (OperationExecutor, TaskManager)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← 执行模型所在层
│  (ExecutionModels, Data Contracts)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← 执行模型依赖的组件
│  (Database, WebSocket, Celery)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Systems                │  ← 外部系统
│  (Redis, PostgreSQL, MessageQueue)      │
└─────────────────────────────────────────┘
```

## 上游组件（使用方）

### 1. 应用层服务
- **OperationExecutor** (`application/executors/operation_executor.py`)
- **TaskManager** (如果存在)
- **ExecutionService** (如果存在)

### 2. 基础设施层
- **DatabaseManager** (`infrastructure/persistence/database_manager.py`)
- **WebSocketManager** (`infrastructure/messaging/websocket_manager.py`)
- **CeleryTaskManager** (`infrastructure/messaging/celery_task_manager.py`)

### 3. 接口层
- **ExecutionInterface** (`core/interface/execution_interface.py`)
- **API 层** (通过数据转换)
- **消息队列** (通过消息格式)

## 下游组件（被依赖方）

### 1. Python 标准库
- **enum** - 提供枚举类型支持
- **typing** - 提供类型注解支持
- **dataclasses** - 提供数据类支持（如果使用）

### 2. 领域模型
- **TaskContext** (如果存在)
- **其他领域模型** (通过结果字段)

### 3. 工具函数
- **序列化工具** (通过 dict() 方法)
- **验证工具** (通过类型检查)

## 核心模型详解

### 1. TaskStatus - 任务状态枚举

```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"
```

**状态说明**：
- **PENDING**: 等待执行 - 任务已创建但尚未开始执行
- **RUNNING**: 正在执行 - 任务正在执行中
- **COMPLETED**: 已完成 - 任务成功完成
- **CANCELLED**: 已取消 - 任务被用户或系统取消
- **TIMED_OUT**: 执行超时 - 任务执行超时
- **FAILED**: 执行失败 - 任务执行过程中发生错误

**状态转换规则**：
```
PENDING → RUNNING → COMPLETED
       ↘ RUNNING → FAILED
       ↘ RUNNING → TIMED_OUT
       ↘ RUNNING → CANCELLED
```

**使用示例**：
```python
from aiecs.domain.execution.model import TaskStatus

# 创建任务状态
status = TaskStatus.PENDING
print(f"Task status: {status.value}")  # "pending"

# 状态比较
if status == TaskStatus.PENDING:
    print("Task is waiting to start")

# 状态转换
status = TaskStatus.RUNNING
print(f"Task is now: {status.value}")  # "running"

# 获取所有状态
all_statuses = [status.value for status in TaskStatus]
print(f"All statuses: {all_statuses}")
```

### 2. ErrorCode - 错误码枚举

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

**错误码说明**：
- **E001 - VALIDATION_ERROR**: 参数验证错误 - 输入参数不符合要求
- **E002 - TIMEOUT_ERROR**: 执行超时错误 - 任务执行超过时间限制
- **E003 - EXECUTION_ERROR**: 执行错误 - 任务执行过程中发生错误
- **E004 - CANCELLED_ERROR**: 取消错误 - 任务被取消
- **E005 - RETRY_EXHAUSTED**: 重试耗尽错误 - 重试次数用尽
- **E006 - DATABASE_ERROR**: 数据库错误 - 数据库操作失败
- **E007 - DSL_EVALUATION_ERROR**: DSL 评估错误 - DSL 表达式评估失败

**错误分类**：
- **客户端错误** (E001): 参数验证错误
- **超时错误** (E002): 执行超时
- **执行错误** (E003): 业务逻辑错误
- **系统错误** (E004, E005, E006, E007): 系统级错误

**使用示例**：
```python
from aiecs.domain.execution.model import ErrorCode

# 创建错误码
error_code = ErrorCode.VALIDATION_ERROR
print(f"Error code: {error_code.value}")  # "E001"

# 错误码比较
if error_code == ErrorCode.VALIDATION_ERROR:
    print("This is a validation error")

# 获取错误码描述
error_descriptions = {
    ErrorCode.VALIDATION_ERROR: "参数验证错误",
    ErrorCode.TIMEOUT_ERROR: "执行超时错误",
    ErrorCode.EXECUTION_ERROR: "执行错误",
    ErrorCode.CANCELLED_ERROR: "取消错误",
    ErrorCode.RETRY_EXHAUSTED: "重试耗尽错误",
    ErrorCode.DATABASE_ERROR: "数据库错误",
    ErrorCode.DSL_EVALUATION_ERROR: "DSL 评估错误"
}

print(f"Error description: {error_descriptions[error_code]}")
```

### 3. TaskStepResult - 任务步骤结果模型

```python
class TaskStepResult:
    """任务步骤结果模型"""
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

**字段说明**：
- **step**: 操作步骤标识 (如 "pandas_tool.read_csv")
- **result**: 操作执行结果
- **completed**: 是否完成
- **message**: 状态消息
- **status**: 执行状态
- **error_code**: 错误码（可选）
- **error_message**: 错误消息（可选）

**核心方法**：

#### 序列化方法
```python
def dict(self) -> Dict[str, Any]:
    """转换为字典格式"""
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

#### 字符串表示
```python
def __repr__(self) -> str:
    """字符串表示"""
    return f"TaskStepResult(step='{self.step}', status='{self.status}', completed={self.completed})"
```

**使用示例**：
```python
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

# 创建成功结果
success_result = TaskStepResult(
    step="pandas_tool.read_csv",
    result={"rows": 1000, "columns": 5},
    completed=True,
    message="Successfully read CSV file",
    status=TaskStatus.COMPLETED.value
)

print(f"Success result: {success_result}")
print(f"Result data: {success_result.dict()}")

# 创建失败结果
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

## 设计模式详解

### 1. 枚举模式 (Enum Pattern)
```python
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    # ...
```

**优势**：
- **类型安全**：编译时类型检查
- **值约束**：限制可能的取值
- **可读性**：代码更易读和维护
- **扩展性**：易于添加新状态

### 2. 值对象模式 (Value Object Pattern)
```python
class TaskStepResult:
    """不可变的值对象"""
    def __init__(self, step: str, result: Any, ...):
        self.step = step
        self.result = result
        # ...
```

**优势**：
- **不可变性**：对象创建后不可修改
- **相等性**：基于值而非引用的相等性
- **封装性**：封装相关的数据和行为
- **可测试性**：易于单元测试

### 3. 工厂模式 (Factory Pattern)
```python
# 通过构造函数创建实例
result = TaskStepResult(
    step="operation_name",
    result=operation_result,
    completed=True,
    status=TaskStatus.COMPLETED.value
)
```

**优势**：
- **统一创建**：统一的对象创建接口
- **参数验证**：在创建时进行参数验证
- **类型安全**：确保创建的对象类型正确

## 使用示例

### 1. 基本状态管理

```python
from aiecs.domain.execution.model import TaskStatus, ErrorCode, TaskStepResult

# 任务状态管理
def manage_task_lifecycle():
    """管理任务生命周期"""
    # 初始状态
    current_status = TaskStatus.PENDING
    print(f"Task started with status: {current_status.value}")
    
    # 状态转换
    current_status = TaskStatus.RUNNING
    print(f"Task is now: {current_status.value}")
    
    # 检查状态
    if current_status == TaskStatus.RUNNING:
        print("Task is currently running")
    
    # 完成状态
    current_status = TaskStatus.COMPLETED
    print(f"Task finished with status: {current_status.value}")

# 错误处理
def handle_task_errors():
    """处理任务错误"""
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

### 2. 结果模型使用

```python
# 创建成功结果
def create_success_result():
    """创建成功结果"""
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

# 创建失败结果
def create_failure_result():
    """创建失败结果"""
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

# 结果处理
def process_results(results: List[TaskStepResult]):
    """处理结果列表"""
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

### 3. 与系统集成

```python
# 数据库集成
def save_task_result_to_database(result: TaskStepResult, user_id: str, task_id: str):
    """保存任务结果到数据库"""
    from aiecs.infrastructure.persistence.database_manager import DatabaseManager
    
    db_manager = DatabaseManager()
    
    # 保存到数据库
    db_manager.save_task_history(user_id, task_id, 1, result)
    
    print(f"Saved result for task {task_id}: {result.step}")

# WebSocket 集成
def send_result_via_websocket(result: TaskStepResult, user_id: str, task_id: str):
    """通过 WebSocket 发送结果"""
    from aiecs.infrastructure.messaging.websocket_manager import WebSocketManager
    
    ws_manager = WebSocketManager()
    
    # 发送结果
    ws_manager.notify_user(result, user_id, task_id, 1)
    
    print(f"Sent result via WebSocket: {result.step}")

# Celery 集成
def create_celery_task_result(status: TaskStatus, error_code: ErrorCode = None):
    """创建 Celery 任务结果"""
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

### 4. 高级用法

```python
# 结果验证
def validate_result(result: TaskStepResult) -> bool:
    """验证结果有效性"""
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

# 结果转换
def convert_result_to_dict(result: TaskStepResult) -> Dict[str, Any]:
    """转换结果为字典格式"""
    return result.dict()

def convert_dict_to_result(data: Dict[str, Any]) -> TaskStepResult:
    """从字典创建结果对象"""
    return TaskStepResult(
        step=data["step"],
        result=data["result"],
        completed=data["completed"],
        message=data["message"],
        status=data["status"],
        error_code=data.get("error_code"),
        error_message=data.get("error_message")
    )

# 结果比较
def compare_results(result1: TaskStepResult, result2: TaskStepResult) -> bool:
    """比较两个结果是否相等"""
    return (result1.step == result2.step and
            result1.completed == result2.completed and
            result1.status == result2.status)
```

## 维护指南

### 1. 日常维护

#### 模型验证
```python
def validate_models_health():
    """验证模型健康状态"""
    try:
        # 测试状态枚举
        status = TaskStatus.PENDING
        assert status.value == "pending"
        print("✅ TaskStatus validation passed")
        
        # 测试错误码枚举
        error_code = ErrorCode.VALIDATION_ERROR
        assert error_code.value == "E001"
        print("✅ ErrorCode validation passed")
        
        # 测试结果模型
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

#### 数据一致性检查
```python
def check_data_consistency(result: TaskStepResult):
    """检查结果数据一致性"""
    try:
        # 检查基本字段
        if not result.step:
            print("❌ Missing step identifier")
            return False
        
        # 检查状态一致性
        if result.completed and result.status != TaskStatus.COMPLETED.value:
            print("❌ Completed result has wrong status")
            return False
        
        if not result.completed and result.status == TaskStatus.COMPLETED.value:
            print("❌ Incomplete result has completed status")
            return False
        
        # 检查错误信息一致性
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

### 2. 故障排查

#### 常见问题诊断

**问题1: 状态转换错误**
```python
def diagnose_status_transition_error():
    """诊断状态转换错误"""
    try:
        # 测试无效状态转换
        current_status = TaskStatus.PENDING
        next_status = TaskStatus.COMPLETED  # 跳过 RUNNING
        
        if current_status == TaskStatus.PENDING and next_status == TaskStatus.COMPLETED:
            print("❌ Invalid status transition: PENDING → COMPLETED")
            print("   Valid transitions from PENDING: RUNNING")
        
        # 测试有效状态转换
        current_status = TaskStatus.PENDING
        next_status = TaskStatus.RUNNING
        
        if current_status == TaskStatus.PENDING and next_status == TaskStatus.RUNNING:
            print("✅ Valid status transition: PENDING → RUNNING")
        
    except Exception as e:
        print(f"❌ Status transition diagnosis failed: {e}")
```

**问题2: 错误码映射错误**
```python
def diagnose_error_code_mapping_error():
    """诊断错误码映射错误"""
    try:
        # 测试错误码映射
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

### 3. 性能优化

#### 对象创建优化
```python
def optimize_object_creation():
    """优化对象创建性能"""
    import time
    
    # 测试枚举创建性能
    start_time = time.time()
    for i in range(10000):
        status = TaskStatus.PENDING
        error_code = ErrorCode.VALIDATION_ERROR
    enum_time = time.time() - start_time
    
    # 测试结果对象创建性能
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

#### 内存使用优化
```python
def optimize_memory_usage():
    """优化内存使用"""
    import gc
    import sys
    
    # 创建大量对象
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
    
    # 清理对象
    results.clear()
    gc.collect()
    
    print(f"Memory usage after cleanup: {sys.getsizeof(results)} bytes")
```

### 4. 数据迁移

#### 模型版本升级
```python
def migrate_models_to_new_version(old_data: Dict[str, Any]) -> Dict[str, Any]:
    """将模型数据迁移到新版本"""
    # 检查版本
    version = old_data.get("version", "1.0")
    
    if version == "1.0":
        # 从 1.0 升级到 1.1
        if "status" in old_data:
            # 更新状态值
            if old_data["status"] == "success":
                old_data["status"] = "completed"
            elif old_data["status"] == "error":
                old_data["status"] = "failed"
        
        old_data["version"] = "1.1"
    
    return old_data
```

#### 数据格式转换
```python
def convert_data_formats():
    """转换数据格式"""
    # 从旧格式转换到新格式
    old_result = {
        "operation": "data_processing",
        "output": {"rows": 1000},
        "success": True,
        "message": "Processing completed"
    }
    
    # 转换为新格式
    new_result = TaskStepResult(
        step=old_result["operation"],
        result=old_result["output"],
        completed=old_result["success"],
        message=old_result["message"],
        status=TaskStatus.COMPLETED.value if old_result["success"] else TaskStatus.FAILED.value
    )
    
    print(f"Converted result: {new_result}")
```

## 监控与日志

### 模型使用监控
```python
import time
from typing import Dict, Any

class ExecutionModelsMonitor:
    """执行模型监控器"""
    
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
        """记录状态对象创建指标"""
        self.creation_metrics["status_objects"] += 1
        self.performance_metrics["status_creation_time"].append(creation_time)
    
    def record_error_code_creation(self, creation_time: float):
        """记录错误码对象创建指标"""
        self.creation_metrics["error_code_objects"] += 1
        self.performance_metrics["error_code_creation_time"].append(creation_time)
    
    def record_result_creation(self, creation_time: float):
        """记录结果对象创建指标"""
        self.creation_metrics["result_objects"] += 1
        self.performance_metrics["result_creation_time"].append(creation_time)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
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

### 日志记录
```python
import logging
from typing import Dict, Any

class ExecutionModelsLogger:
    """执行模型日志记录器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_status_creation(self, status: TaskStatus):
        """记录状态创建日志"""
        self.logger.info(f"TaskStatus created: {status.value}")
    
    def log_error_code_creation(self, error_code: ErrorCode):
        """记录错误码创建日志"""
        self.logger.info(f"ErrorCode created: {error_code.value}")
    
    def log_result_creation(self, result: TaskStepResult):
        """记录结果创建日志"""
        self.logger.info(f"TaskStepResult created: {result.step} - {result.status}")
    
    def log_validation_error(self, error: Exception, context: str):
        """记录验证错误日志"""
        self.logger.error(f"Validation error in {context}: {error}")
```

## 版本历史

- **v1.0.0**: 初始版本，基础状态和错误码定义
- **v1.1.0**: 添加任务步骤结果模型
- **v1.2.0**: 添加序列化支持
- **v1.3.0**: 添加性能监控和日志记录
- **v1.4.0**: 添加数据迁移支持

## 相关文档

- [AIECS 项目总览](../PROJECT_SUMMARY.md)
- [操作执行器文档](./OPERATION_EXECUTOR.md)
- [执行接口文档](./EXECUTION_INTERFACES.md)
- [配置管理文档](./CONFIG_MANAGEMENT.md)
