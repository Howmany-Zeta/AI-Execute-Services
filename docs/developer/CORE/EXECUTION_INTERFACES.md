# 执行接口技术文档

## 概述

### 设计动机与问题背景

在构建大型 AI 应用系统时，执行层面临以下核心挑战：

**1. 接口标准化缺失**
- 不同执行组件（工具执行器、操作执行器、缓存提供者）缺乏统一的接口规范
- 组件间的依赖关系不明确，导致紧耦合和难以测试
- 缺乏抽象层，使得组件替换和扩展变得困难

**2. 依赖倒置原则违反**
- 高层模块直接依赖低层模块的具体实现
- 缺乏抽象接口，导致系统难以扩展和维护
- 测试困难，无法进行有效的单元测试和集成测试

**3. 插件化架构支持不足**
- 新增执行引擎需要修改现有代码
- 缺乏统一的执行接口，无法支持多种执行策略
- 执行组件的注册和发现机制不完善

**4. 类型安全和契约管理**
- 缺乏明确的接口契约定义
- 参数类型和返回值类型不明确
- 接口变更时缺乏向后兼容性保证

**执行接口系统的解决方案**：
- **接口分离原则**：将不同职责的接口分离，提高内聚性
- **依赖倒置**：高层模块依赖抽象接口，低层模块实现接口
- **插件化支持**：通过统一接口支持多种执行引擎
- **类型安全**：基于 Python 类型系统的接口定义
- **契约明确**：通过抽象方法定义清晰的接口契约

### 组件定位

`execution_interface.py` 是 AIECS 系统的核心接口定义，位于领域层 (Domain Layer)，定义了执行相关的所有抽象接口。作为系统的契约层，它提供了类型安全、职责明确的接口规范。

## 组件类型与定位

### 组件类型
**领域接口组件** - 位于领域层 (Domain Layer)，属于系统契约定义

### 架构层次
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← 使用接口的组件
│  (OperationExecutor, ServiceExecutor)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← 执行接口所在层
│  (Execution Interfaces, Contracts)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← 实现接口的组件
│  (ToolExecutor, CacheProvider, etc.)    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Services               │  ← 外部依赖
│  (Tools, Cache, Database, etc.)         │
└─────────────────────────────────────────┘
```

## 上游组件（使用方）

### 1. 应用层执行器
- **OperationExecutor** (`application/executors/operation_executor.py`)
- **ServiceExecutor** (如果存在)
- **TaskExecutor** (如果存在)

### 2. 基础设施层实现
- **ToolExecutor** (`tools/tool_executor/tool_executor.py`)
- **ExecutionUtils** (`utils/execution_utils.py`)
- **CacheProvider** (如果存在)

### 3. 领域服务
- **TaskService** (如果存在)
- **ExecutionService** (如果存在)

## 下游组件（被依赖方）

### 1. Python ABC 系统
- **用途**: 提供抽象基类支持
- **功能**: 接口定义、抽象方法声明
- **依赖类型**: 语言特性依赖

### 2. 领域模型
- **TaskStepResult** (`domain/execution/model.py`)
- **TaskStatus** (`domain/execution/model.py`)
- **ErrorCode** (`domain/execution/model.py`)

### 3. 类型系统
- **用途**: 提供类型检查和类型安全
- **功能**: 参数类型验证、返回值类型检查
- **依赖类型**: Python 类型系统

## 核心接口详解

### 1. IToolProvider - 工具提供者接口

```python
class IToolProvider(ABC):
    """工具提供者接口 - 领域层抽象"""
    
    @abstractmethod
    def get_tool(self, tool_name: str) -> Any:
        """获取工具实例"""
        pass
    
    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        pass
```

**职责**：
- **工具发现**：根据工具名称获取工具实例
- **工具检查**：验证工具是否可用
- **工具管理**：管理工具的生命周期

**实现要求**：
- 必须支持按名称获取工具实例
- 必须提供工具存在性检查
- 应该支持工具的动态注册和注销

### 2. IToolExecutor - 工具执行器接口

```python
class IToolExecutor(ABC):
    """工具执行器接口 - 领域层抽象"""
    
    @abstractmethod
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        """同步执行工具操作"""
        pass
    
    @abstractmethod
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """异步执行工具操作"""
        pass
```

**职责**：
- **同步执行**：支持同步工具操作执行
- **异步执行**：支持异步工具操作执行
- **参数传递**：处理工具操作的参数传递
- **结果返回**：统一工具操作的返回格式

**实现要求**：
- 必须支持同步和异步两种执行模式
- 必须处理参数验证和类型转换
- 应该提供错误处理和重试机制

### 3. ICacheProvider - 缓存提供者接口

```python
class ICacheProvider(ABC):
    """缓存提供者接口 - 领域层抽象"""
    
    @abstractmethod
    def generate_cache_key(self, operation_type: str, user_id: str, task_id: str,
                          args: tuple, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        pass
    
    @abstractmethod
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        pass
    
    @abstractmethod
    def add_to_cache(self, cache_key: str, value: Any) -> None:
        """添加数据到缓存"""
        pass
```

**职责**：
- **缓存键生成**：根据操作上下文生成唯一缓存键
- **缓存读取**：从缓存中获取数据
- **缓存写入**：将数据写入缓存
- **缓存管理**：管理缓存的过期和清理

**实现要求**：
- 必须支持上下文感知的缓存键生成
- 必须提供线程安全的缓存操作
- 应该支持缓存过期和清理策略

### 4. IOperationExecutor - 操作执行器接口

```python
class IOperationExecutor(ABC):
    """操作执行器接口 - 领域层抽象"""
    
    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """执行单个操作"""
        pass
    
    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """批量执行操作"""
        pass
    
    @abstractmethod
    async def execute_operations_sequence(self, operations: List[Dict[str, Any]],
                                        user_id: str, task_id: str,
                                        stop_on_failure: bool = False,
                                        save_callback: Optional[Callable] = None) -> List[TaskStepResult]:
        """顺序执行操作序列"""
        pass
    
    @abstractmethod
    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """并行执行操作"""
        pass
```

**职责**：
- **单操作执行**：执行单个工具操作
- **批量执行**：批量执行多个操作
- **顺序执行**：按顺序执行操作序列
- **并行执行**：并行执行多个操作

**实现要求**：
- 必须支持多种执行模式
- 必须处理操作间的依赖关系
- 应该提供错误处理和恢复机制

### 5. ExecutionInterface - 统一执行接口

```python
class ExecutionInterface(ABC):
    """统一执行接口 - 支持插件化执行引擎"""
    
    @abstractmethod
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """执行单个操作"""
        pass
    
    @abstractmethod
    async def execute_task(self, task_name: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """执行单个任务"""
        pass
    
    @abstractmethod
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """批量执行操作"""
        pass
    
    @abstractmethod
    async def batch_execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[Any]:
        """批量执行任务"""
        pass
    
    def register_executor(self, executor_type: str, executor_instance: Any) -> None:
        """注册新的执行器类型"""
        raise NotImplementedError("Executor registration is not implemented in this interface")
```

**职责**：
- **统一接口**：提供统一的执行接口
- **插件支持**：支持多种执行引擎
- **任务执行**：支持任务和操作两种执行模式
- **批量处理**：支持批量执行操作和任务

## 设计模式详解

### 1. 接口隔离原则 (Interface Segregation Principle)
```python
# 将不同职责的接口分离
class IToolProvider(ABC):      # 工具提供
class IToolExecutor(ABC):      # 工具执行
class ICacheProvider(ABC):     # 缓存管理
class IOperationExecutor(ABC): # 操作执行
```

**优势**：
- **职责单一**：每个接口只负责一个特定功能
- **易于实现**：实现类只需要实现相关接口
- **易于测试**：可以独立测试每个接口

### 2. 依赖倒置原则 (Dependency Inversion Principle)
```python
# 高层模块依赖抽象接口
class OperationExecutor:
    def __init__(self, tool_executor: IToolExecutor, cache_provider: ICacheProvider):
        self.tool_executor = tool_executor
        self.cache_provider = cache_provider
```

**优势**：
- **松耦合**：高层模块不依赖具体实现
- **可扩展**：可以轻松替换实现
- **可测试**：可以使用模拟对象进行测试

### 3. 策略模式 (Strategy Pattern)
```python
# 支持多种执行策略
class ExecutionInterface(ABC):
    def register_executor(self, executor_type: str, executor_instance: Any):
        # 支持注册不同的执行器
        pass
```

**优势**：
- **算法封装**：将执行算法封装在具体实现中
- **动态切换**：可以在运行时切换执行策略
- **易于扩展**：新增执行策略无需修改现有代码

## 接口实现规范

### 1. 接口实现要求

#### 必须实现的方法
```python
class ToolExecutorImpl(IToolExecutor):
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        """必须实现同步执行方法"""
        # 实现逻辑
        pass
    
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """必须实现异步执行方法"""
        # 实现逻辑
        pass
```

#### 类型安全要求
```python
from typing import TypeVar, Generic

T = TypeVar('T')

class TypedToolExecutor(IToolExecutor, Generic[T]):
    def execute(self, tool: Any, operation_name: str, **params) -> T:
        """类型安全的执行方法"""
        # 实现逻辑
        pass
```

### 2. 错误处理规范

#### 异常类型定义
```python
class ExecutionError(Exception):
    """执行错误基类"""
    pass

class ToolNotFoundError(ExecutionError):
    """工具未找到错误"""
    pass

class OperationFailedError(ExecutionError):
    """操作执行失败错误"""
    pass
```

#### 错误处理实现
```python
class RobustToolExecutor(IToolExecutor):
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        try:
            # 执行逻辑
            return result
        except ToolNotFoundError:
            # 处理工具未找到
            raise
        except Exception as e:
            # 处理其他错误
            raise OperationFailedError(f"Operation failed: {e}") from e
```

### 3. 日志和监控规范

#### 日志记录
```python
import logging

class LoggingToolExecutor(IToolExecutor):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        self.logger.info(f"Executing operation: {operation_name}")
        try:
            result = self._do_execute(tool, operation_name, **params)
            self.logger.info(f"Operation completed: {operation_name}")
            return result
        except Exception as e:
            self.logger.error(f"Operation failed: {operation_name}, error: {e}")
            raise
```

#### 性能监控
```python
import time
from functools import wraps

def monitor_execution(func):
    """执行监控装饰器"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            self.logger.info(f"Execution completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Execution failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper
```

## 使用示例

### 1. 基本接口实现

#### 工具提供者实现
```python
from aiecs.core.interface.execution_interface import IToolProvider

class ToolProviderImpl(IToolProvider):
    def __init__(self):
        self._tools = {}
    
    def register_tool(self, name: str, tool: Any):
        """注册工具"""
        self._tools[name] = tool
    
    def get_tool(self, tool_name: str) -> Any:
        """获取工具实例"""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        return self._tools[tool_name]
    
    def has_tool(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._tools
```

#### 工具执行器实现
```python
from aiecs.core.interface.execution_interface import IToolExecutor

class ToolExecutorImpl(IToolExecutor):
    def __init__(self, cache_provider: ICacheProvider = None):
        self.cache_provider = cache_provider
    
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        """同步执行工具操作"""
        # 检查缓存
        if self.cache_provider:
            cache_key = self.cache_provider.generate_cache_key(
                operation_name, params.get('user_id', ''), 
                params.get('task_id', ''), (), params
            )
            cached_result = self.cache_provider.get_from_cache(cache_key)
            if cached_result is not None:
                return cached_result
        
        # 执行操作
        method = getattr(tool, operation_name)
        result = method(**params)
        
        # 缓存结果
        if self.cache_provider:
            self.cache_provider.add_to_cache(cache_key, result)
        
        return result
    
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """异步执行工具操作"""
        # 异步实现逻辑
        method = getattr(tool, operation_name)
        if asyncio.iscoroutinefunction(method):
            return await method(**params)
        else:
            return method(**params)
```

### 2. 缓存提供者实现

```python
from aiecs.core.interface.execution_interface import ICacheProvider
import hashlib
import json
from typing import Optional, Any

class CacheProviderImpl(ICacheProvider):
    def __init__(self, cache_size: int = 1000):
        self._cache = {}
        self._cache_size = cache_size
    
    def generate_cache_key(self, operation_type: str, user_id: str, task_id: str,
                          args: tuple, kwargs: Dict[str, Any]) -> str:
        """生成缓存键"""
        key_data = {
            'operation_type': operation_type,
            'user_id': user_id,
            'task_id': task_id,
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        return self._cache.get(cache_key)
    
    def add_to_cache(self, cache_key: str, value: Any) -> None:
        """添加数据到缓存"""
        if len(self._cache) >= self._cache_size:
            # 简单的 LRU 实现
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = value
```

### 3. 操作执行器实现

```python
from aiecs.core.interface.execution_interface import IOperationExecutor
from aiecs.domain.execution.model import TaskStepResult, TaskStatus, ErrorCode

class OperationExecutorImpl(IOperationExecutor):
    def __init__(self, tool_executor: IToolExecutor, tool_provider: IToolProvider):
        self.tool_executor = tool_executor
        self.tool_provider = tool_provider
    
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> Any:
        """执行单个操作"""
        tool_name, operation_name = operation_spec.split('.', 1)
        tool = self.tool_provider.get_tool(tool_name)
        return await self.tool_executor.execute_async(tool, operation_name, **params)
    
    async def batch_execute_operations(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """批量执行操作"""
        tasks = []
        for op in operations:
            task = self.execute_operation(op['operation'], op.get('params', {}))
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def execute_operations_sequence(self, operations: List[Dict[str, Any]],
                                        user_id: str, task_id: str,
                                        stop_on_failure: bool = False,
                                        save_callback: Optional[Callable] = None) -> List[TaskStepResult]:
        """顺序执行操作序列"""
        results = []
        
        for i, op in enumerate(operations):
            try:
                result = await self.execute_operation(op['operation'], op.get('params', {}))
                step_result = TaskStepResult(
                    step=op['operation'],
                    result=result,
                    completed=True,
                    message=f"Operation {op['operation']} completed",
                    status=TaskStatus.COMPLETED.value
                )
            except Exception as e:
                step_result = TaskStepResult(
                    step=op['operation'],
                    result=None,
                    completed=False,
                    message=f"Operation {op['operation']} failed: {str(e)}",
                    status=TaskStatus.FAILED.value,
                    error_code=ErrorCode.EXECUTION_ERROR.value,
                    error_message=str(e)
                )
                
                if stop_on_failure:
                    results.append(step_result)
                    break
            
            if save_callback:
                await save_callback(user_id, task_id, i, step_result)
            
            results.append(step_result)
        
        return results
    
    async def execute_parallel_operations(self, operations: List[Dict[str, Any]]) -> List[TaskStepResult]:
        """并行执行操作"""
        tasks = []
        for i, op in enumerate(operations):
            task = self._execute_single_operation(op, i)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_single_operation(self, op: Dict[str, Any], index: int) -> TaskStepResult:
        """执行单个操作并返回结果"""
        try:
            result = await self.execute_operation(op['operation'], op.get('params', {}))
            return TaskStepResult(
                step=op['operation'],
                result=result,
                completed=True,
                message=f"Operation {op['operation']} completed",
                status=TaskStatus.COMPLETED.value
            )
        except Exception as e:
            return TaskStepResult(
                step=op['operation'],
                result=None,
                completed=False,
                message=f"Operation {op['operation']} failed: {str(e)}",
                status=TaskStatus.FAILED.value,
                error_code=ErrorCode.EXECUTION_ERROR.value,
                error_message=str(e)
            )
```

## 维护指南

### 1. 日常维护

#### 接口兼容性检查
```python
def check_interface_compatibility(implementation_class, interface_class):
    """检查实现类是否完全实现接口"""
    interface_methods = {
        name for name, method in interface_class.__dict__.items()
        if getattr(method, '__isabstractmethod__', False)
    }
    
    implementation_methods = {
        name for name, method in implementation_class.__dict__.items()
        if callable(method) and not name.startswith('_')
    }
    
    missing_methods = interface_methods - implementation_methods
    if missing_methods:
        raise TypeError(f"Missing methods: {missing_methods}")
    
    return True
```

#### 接口版本管理
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class VersionedInterface(Protocol):
    """版本化接口协议"""
    version: str
    
    def get_version(self) -> str:
        """获取接口版本"""
        return self.version

def check_interface_version(implementation, required_version: str):
    """检查接口版本兼容性"""
    if hasattr(implementation, 'get_version'):
        version = implementation.get_version()
        if version < required_version:
            raise ValueError(f"Interface version {version} is lower than required {required_version}")
```

### 2. 故障排查

#### 常见问题诊断

**问题1: 接口实现不完整**
```python
# 错误信息
TypeError: Can't instantiate abstract class ToolExecutorImpl with abstract methods execute_async

# 诊断步骤
def diagnose_incomplete_implementation(cls):
    """诊断接口实现不完整问题"""
    abstract_methods = []
    for name, method in cls.__dict__.items():
        if getattr(method, '__isabstractmethod__', False):
            abstract_methods.append(name)
    
    if abstract_methods:
        print(f"未实现的抽象方法: {abstract_methods}")
        return False
    return True
```

**问题2: 类型不匹配**
```python
# 错误信息
TypeError: execute_operation() missing 1 required positional argument: 'params'

# 诊断步骤
def diagnose_type_mismatch(implementation, interface):
    """诊断类型不匹配问题"""
    import inspect
    
    for method_name in dir(interface):
        if method_name.startswith('_'):
            continue
            
        interface_method = getattr(interface, method_name)
        if not callable(interface_method):
            continue
            
        if hasattr(implementation, method_name):
            impl_method = getattr(implementation, method_name)
            interface_sig = inspect.signature(interface_method)
            impl_sig = inspect.signature(impl_method)
            
            if interface_sig != impl_sig:
                print(f"方法 {method_name} 签名不匹配:")
                print(f"  接口: {interface_sig}")
                print(f"  实现: {impl_sig}")
```

### 3. 接口更新

#### 添加新方法
```python
# 1. 在接口中添加新方法
class IToolExecutor(ABC):
    # 现有方法...
    
    @abstractmethod
    async def execute_with_retry(self, tool: Any, operation_name: str, 
                                max_retries: int = 3, **params) -> Any:
        """带重试的执行方法"""
        pass

# 2. 更新实现类
class ToolExecutorImpl(IToolExecutor):
    # 现有方法...
    
    async def execute_with_retry(self, tool: Any, operation_name: str, 
                                max_retries: int = 3, **params) -> Any:
        """带重试的执行方法实现"""
        for attempt in range(max_retries):
            try:
                return await self.execute_async(tool, operation_name, **params)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # 指数退避
```

#### 接口版本控制
```python
from abc import ABC, abstractmethod
from typing import Union

class IToolExecutorV1(ABC):
    """工具执行器接口 V1"""
    
    @abstractmethod
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        pass

class IToolExecutorV2(IToolExecutorV1):
    """工具执行器接口 V2 - 继承 V1 并添加新功能"""
    
    @abstractmethod
    async def execute_with_metrics(self, tool: Any, operation_name: str, **params) -> Any:
        """带指标的执行方法"""
        pass

# 支持多版本接口
ToolExecutorInterface = Union[IToolExecutorV1, IToolExecutorV2]
```

### 4. 接口扩展

#### 支持泛型接口
```python
from typing import TypeVar, Generic, Protocol

T = TypeVar('T')
R = TypeVar('R')

class ITypedToolExecutor(Protocol[T, R]):
    """类型化的工具执行器接口"""
    
    def execute(self, tool: T, operation_name: str, **params) -> R:
        """类型安全的执行方法"""
        ...

class ITypedOperationExecutor(Protocol[T]):
    """类型化的操作执行器接口"""
    
    async def execute_operation(self, operation_spec: str, params: Dict[str, Any]) -> T:
        """类型安全的操作执行"""
        ...
```

#### 支持异步上下文管理
```python
from typing import AsyncContextManager

class IAsyncContextExecutor(ABC):
    """支持异步上下文的执行器接口"""
    
    @abstractmethod
    async def __aenter__(self):
        """异步上下文进入"""
        pass
    
    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        pass
    
    @abstractmethod
    async def execute_in_context(self, operation: str, **params) -> Any:
        """在上下文中执行操作"""
        pass

# 使用示例
async def use_async_context_executor():
    async with IAsyncContextExecutor() as executor:
        result = await executor.execute_in_context("some_operation", param1="value1")
```

## 性能优化

### 1. 接口方法缓存
```python
from functools import lru_cache

class CachedToolExecutor(IToolExecutor):
    @lru_cache(maxsize=128)
    def _get_tool_method(self, tool_class: type, operation_name: str):
        """缓存工具方法获取"""
        return getattr(tool_class, operation_name)
    
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        method = self._get_tool_method(type(tool), operation_name)
        return method(**params)
```

### 2. 异步接口优化
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedToolExecutor(IToolExecutor):
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute_async(self, tool: Any, operation_name: str, **params) -> Any:
        """优化的异步执行"""
        method = getattr(tool, operation_name)
        
        if asyncio.iscoroutinefunction(method):
            return await method(**params)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, 
                lambda: method(**params)
            )
```

### 3. 接口性能监控
```python
import time
from typing import Dict, List
from collections import defaultdict

class MonitoredToolExecutor(IToolExecutor):
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def execute(self, tool: Any, operation_name: str, **params) -> Any:
        start_time = time.time()
        try:
            result = self._do_execute(tool, operation_name, **params)
            execution_time = time.time() - start_time
            self.metrics[operation_name].append(execution_time)
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics[f"{operation_name}_error"].append(execution_time)
            raise
    
    def get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """获取性能指标"""
        metrics = {}
        for operation, times in self.metrics.items():
            if times:
                metrics[operation] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "count": len(times)
                }
        return metrics
```

## 监控与日志

### 接口使用监控
```python
import logging
from typing import Dict, Any

class InterfaceMonitor:
    """接口使用监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.usage_stats = defaultdict(int)
        self.error_stats = defaultdict(int)
    
    def record_interface_usage(self, interface_name: str, method_name: str, success: bool):
        """记录接口使用情况"""
        key = f"{interface_name}.{method_name}"
        self.usage_stats[key] += 1
        
        if not success:
            self.error_stats[key] += 1
        
        self.logger.info(f"Interface usage: {key}, success: {success}")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """获取使用报告"""
        return {
            "total_usage": sum(self.usage_stats.values()),
            "total_errors": sum(self.error_stats.values()),
            "error_rate": sum(self.error_stats.values()) / sum(self.usage_stats.values()) if self.usage_stats else 0,
            "usage_by_interface": dict(self.usage_stats),
            "errors_by_interface": dict(self.error_stats)
        }
```

## 版本历史

- **v1.0.0**: 初始版本，基础接口定义
- **v1.1.0**: 添加缓存提供者接口
- **v1.2.0**: 添加操作执行器接口
- **v1.3.0**: 添加统一执行接口
- **v1.4.0**: 支持插件化执行引擎
- **v1.5.0**: 添加类型安全和性能优化

## 相关文档

- [AIECS 项目总览](../PROJECT_SUMMARY.md)
- [操作执行器文档](./OPERATION_EXECUTOR.md)
- [配置管理文档](./CONFIG_MANAGEMENT.md)
- [服务注册表文档](./SERVICE_REGISTRY.md)
