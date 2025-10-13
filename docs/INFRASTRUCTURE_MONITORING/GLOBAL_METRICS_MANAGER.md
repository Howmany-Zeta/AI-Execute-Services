# Global Metrics Manager 技术文档

## 1. 概述 (Overview)

### 目的
`GlobalMetricsManager` 是一个全局单例指标管理器，用于统一管理 AIECS 系统中的所有指标收集。它解决了多个组件同时创建 `ExecutorMetrics` 实例导致的端口冲突问题，提供了统一的指标收集接口。

### 核心价值
- **统一指标管理**：全局单例模式，避免端口冲突
- **简化使用**：提供便捷的全局访问接口
- **优雅降级**：指标收集失败时不影响主业务功能
- **配置灵活**：支持环境变量和参数配置

## 2. 问题背景与设计动机 (Problem & Motivation)

### 问题背景
在 AIECS 系统中，多个组件都需要指标收集功能：
- **FileStorage** - 存储操作指标
- **ToolExecutor** - 工具执行指标
- **DatabaseManager** - 数据库操作指标
- **其他组件** - 各种业务指标

每个组件都创建独立的 `ExecutorMetrics` 实例会导致：
- **端口冲突**：多个实例尝试绑定同一个端口 8001
- **资源浪费**：重复的 Prometheus 服务器实例
- **管理复杂**：难以统一配置和管理指标

### 设计动机
1. **解决端口冲突**：全局单例确保只有一个指标服务器
2. **统一配置管理**：集中管理指标收集配置
3. **简化组件集成**：组件只需获取全局实例即可
4. **提高可维护性**：统一的指标收集逻辑

## 3. 架构定位与上下文 (Architecture & Context)

### 系统架构位置
```
┌─────────────────────────────────────────────────────────────┐
│                    AIECS 系统架构                           │
├─────────────────────────────────────────────────────────────┤
│  应用层 (Application Layer)                                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ FileStorage     │  │ ToolExecutor    │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  基础设施层 (Infrastructure Layer)                         │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ GlobalMetrics   │  │ ExecutorMetrics │                  │
│  │ Manager         │  │ (Prometheus)    │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  监控层 (Monitoring Layer)                                 │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Prometheus      │  │ Grafana         │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### 依赖关系
- **被依赖方**：`ExecutorMetrics`、`Prometheus Client`
- **依赖方**：`FileStorage`、`ToolExecutor`、`DatabaseManager` 等所有需要指标收集的组件

## 4. 核心功能与特性 (Core Features)

### 4.1 全局单例管理
```python
# 全局唯一实例
_global_metrics: Optional[ExecutorMetrics] = None
_initialization_lock = asyncio.Lock()
_initialized = False
```

### 4.2 线程安全初始化
```python
async def initialize_global_metrics(
    enable_metrics: bool = True,
    metrics_port: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[ExecutorMetrics]:
    """线程安全的全局指标初始化"""
    async with _initialization_lock:
        # 双重检查锁定模式
        if _initialized and _global_metrics:
            return _global_metrics
        # ... 初始化逻辑
```

### 4.3 便捷访问接口
```python
def get_global_metrics() -> Optional[ExecutorMetrics]:
    """获取全局指标实例"""
    return _global_metrics

# 便捷函数
def record_operation(operation_type: str, success: bool = True, duration: Optional[float] = None, **kwargs):
    """记录操作指标"""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_operation(operation_type, success, duration, **kwargs)
```

## 5. 使用指南 (Usage Guide)

### 5.1 应用启动时初始化

#### 在 main.py 中初始化
```python
from aiecs.infrastructure.monitoring import (
    initialize_global_metrics,
    close_global_metrics
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    try:
        await initialize_global_metrics()
        logger.info("Global metrics initialized")
    except Exception as e:
        logger.warning(f"Global metrics initialization failed: {e}")
    
    yield
    
    # 关闭时清理
    try:
        await close_global_metrics()
        logger.info("Global metrics closed")
    except Exception as e:
        logger.warning(f"Error closing global metrics: {e}")
```

### 5.2 在组件中使用

#### 方式 1：直接获取全局实例
```python
from aiecs.infrastructure.monitoring.global_metrics_manager import get_global_metrics

class MyComponent:
    def __init__(self):
        self.metrics = get_global_metrics()
    
    def do_operation(self):
        if self.metrics:
            self.metrics.record_operation('my_operation', success=True)
```

#### 方式 2：使用便捷函数
```python
from aiecs.infrastructure.monitoring import record_operation, record_duration

class MyComponent:
    def do_operation(self):
        start_time = time.time()
        try:
            # ... 业务逻辑 ...
            duration = time.time() - start_time
            record_operation('my_operation', success=True, duration=duration)
        except Exception as e:
            record_operation('my_operation', success=False)
            raise
```

### 5.3 配置选项

#### 环境变量配置
```bash
# 启用/禁用指标收集
export ENABLE_METRICS=true

# 指定指标服务器端口
export METRICS_PORT=8001
```

#### 代码配置
```python
# 自定义配置初始化
await initialize_global_metrics(
    enable_metrics=True,
    metrics_port=8002,
    config={
        'custom_setting': 'value'
    }
)
```

## 6. 迁移指南 (Migration Guide)

### 6.1 从独立 ExecutorMetrics 迁移

#### 迁移前
```python
# 旧方式 - 每个组件创建独立实例
class FileStorage:
    def __init__(self):
        self.metrics = ExecutorMetrics(enable_metrics=True)  # 可能导致端口冲突
```

#### 迁移后
```python
# 新方式 - 使用全局管理器
from aiecs.infrastructure.monitoring.global_metrics_manager import get_global_metrics

class FileStorage:
    def __init__(self):
        self.metrics = get_global_metrics()  # 使用全局实例
```

### 6.2 批量迁移步骤

1. **更新导入语句**
```python
# 旧导入
from ..monitoring.executor_metrics import ExecutorMetrics

# 新导入
from ..monitoring.global_metrics_manager import get_global_metrics
```

2. **更新实例化代码**
```python
# 旧实例化
self.metrics = ExecutorMetrics(enable_metrics=True)

# 新实例化
self.metrics = get_global_metrics()
```

3. **添加空值检查**
```python
# 添加空值检查
if self.metrics:
    self.metrics.record_operation('operation', success=True)
```

## 7. 最佳实践 (Best Practices)

### 7.1 初始化顺序
```python
# 正确的初始化顺序
async def lifespan(app: FastAPI):
    # 1. 首先初始化全局指标
    await initialize_global_metrics()
    
    # 2. 然后初始化其他组件
    await initialize_database()
    await initialize_redis()
    # ...
```

### 7.2 错误处理
```python
# 优雅的错误处理
def record_metrics_safely(operation: str, success: bool):
    try:
        metrics = get_global_metrics()
        if metrics:
            metrics.record_operation(operation, success)
    except Exception as e:
        logger.warning(f"Failed to record metrics: {e}")
        # 不抛出异常，避免影响主业务
```

### 7.3 性能优化
```python
# 缓存全局实例引用
class MyComponent:
    def __init__(self):
        self._metrics = get_global_metrics()  # 缓存引用
    
    def do_operation(self):
        if self._metrics:  # 使用缓存的引用
            self._metrics.record_operation('operation', success=True)
```

## 8. 故障排除 (Troubleshooting)

### 8.1 常见问题

#### 问题 1：指标未初始化
**症状**：`get_global_metrics()` 返回 `None`

**解决方案**：
```python
# 检查初始化状态
from aiecs.infrastructure.monitoring import is_metrics_initialized

if not is_metrics_initialized():
    logger.warning("Global metrics not initialized")
    # 确保在应用启动时调用了 initialize_global_metrics()
```

#### 问题 2：端口仍然被占用
**症状**：`Address already in use` 错误

**解决方案**：
```python
# 使用不同的端口
await initialize_global_metrics(metrics_port=8002)

# 或者通过环境变量
export METRICS_PORT=8002
```

#### 问题 3：指标记录失败
**症状**：指标数据不更新

**解决方案**：
```python
# 检查指标状态
from aiecs.infrastructure.monitoring import get_metrics_summary

summary = get_metrics_summary()
print(f"Metrics status: {summary}")
```

### 8.2 调试技巧

#### 启用详细日志
```python
import logging
logging.getLogger('aiecs.infrastructure.monitoring').setLevel(logging.DEBUG)
```

#### 检查指标端点
```bash
# 检查指标服务器是否运行
curl http://localhost:8001/metrics
```

## 9. 性能考虑 (Performance Considerations)

### 9.1 内存使用
- 全局单例模式减少内存占用
- 避免重复的 Prometheus 客户端实例

### 9.2 网络开销
- 单一指标服务器减少网络连接
- 统一的指标收集减少网络请求

### 9.3 启动时间
- 早期初始化减少组件启动延迟
- 异步初始化不阻塞应用启动

## 10. 未来扩展 (Future Extensions)

### 10.1 多实例支持
```python
# 未来可能支持多个指标实例
await initialize_global_metrics(
    instance_name="primary",
    metrics_port=8001
)

await initialize_global_metrics(
    instance_name="secondary", 
    metrics_port=8002
)
```

### 10.2 动态配置
```python
# 运行时配置更新
def update_metrics_config(new_config: Dict[str, Any]):
    """动态更新指标配置"""
    pass
```

### 10.3 指标聚合
```python
# 跨实例指标聚合
def aggregate_metrics(instances: List[str]) -> Dict[str, Any]:
    """聚合多个实例的指标"""
    pass
```

## 总结

`GlobalMetricsManager` 通过全局单例模式解决了 AIECS 系统中的指标收集端口冲突问题，提供了统一、高效、易用的指标管理解决方案。它遵循了系统现有的架构模式，确保了良好的可维护性和扩展性。
