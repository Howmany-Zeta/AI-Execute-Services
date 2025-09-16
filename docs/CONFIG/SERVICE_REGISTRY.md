# 服务注册表技术文档

## 概述

### 设计动机与问题背景

在构建可扩展的 AI 服务系统时，服务管理面临以下核心挑战：

**1. 服务发现与路由复杂性**
- 多种 AI 服务（不同模式、不同提供商）需要统一管理
- 服务间的依赖关系和调用关系难以维护
- 动态服务注册和发现机制缺失

**2. 服务生命周期管理困难**
- 服务的注册、实例化、调用、销毁缺乏统一标准
- 服务版本管理和兼容性控制复杂
- 服务健康检查和故障转移机制不完善

**3. 服务配置与元数据管理**
- 服务的配置参数、依赖关系、能力描述分散管理
- 缺乏服务能力的自动发现和文档生成
- 服务间的接口契约不明确

**4. 扩展性和可维护性挑战**
- 新增服务需要修改多个文件，违反开闭原则
- 服务间的紧耦合导致系统难以扩展
- 缺乏服务注册的标准化流程

**服务注册表的解决方案**：
- **装饰器模式**：通过 `@register_ai_service` 装饰器简化服务注册
- **键值映射**：使用 `(mode, service)` 元组作为服务标识
- **延迟加载**：支持服务的按需注册和实例化
- **类型安全**：基于 Python 类型系统的服务类型检查
- **解耦设计**：服务注册与业务逻辑分离，支持插件化架构

### 组件定位

`registry.py` 是 AIECS 系统的服务注册中心，负责统一管理所有 AI 服务的注册、发现和实例化。作为基础设施层的核心组件，它提供了基于装饰器模式的服务注册机制。

## 组件类型与定位

### 组件类型
**基础设施组件** - 位于基础设施层 (Infrastructure Layer)，属于系统基础服务

### 架构层次
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← 使用服务的组件
│  (Task Executor, API Endpoints)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │
│  (Service Interfaces, Business Logic)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← 服务注册表所在层
│  (Service Registry, Service Discovery)  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Service Layer                   │  ← 被注册的服务
│  (AI Services, External Integrations)   │
└─────────────────────────────────────────┘
```

## 上游组件（使用方）

### 1. 任务执行器 (`tasks/worker.py`)
- **用途**: Celery 任务执行，需要根据 mode 和 service 参数获取服务实例
- **使用方式**: 通过 `get_ai_service(mode, service)` 获取服务类并实例化
- **依赖关系**: 直接依赖，用于动态服务发现

### 2. FastAPI 应用 (`main.py`)
- **用途**: Web API 服务，提供可用服务列表查询接口
- **使用方式**: 通过 `AI_SERVICE_REGISTRY` 获取所有注册的服务
- **依赖关系**: 直接依赖，用于服务元数据查询

### 3. 服务管理器 (`infrastructure/messaging/celery_task_manager.py`)
- **用途**: 任务调度和管理，需要根据服务类型选择执行策略
- **使用方式**: 通过服务注册表获取服务信息进行任务路由
- **依赖关系**: 间接依赖，通过任务执行器使用

## 下游组件（被依赖方）

### 1. Python 装饰器系统
- **用途**: 提供装饰器语法支持
- **功能**: 函数和类的装饰器机制
- **依赖类型**: 语言特性依赖

### 2. 服务实现类
- **用途**: 具体的 AI 服务实现
- **功能**: 业务逻辑实现、外部 API 调用
- **依赖类型**: 被注册的服务类

### 3. 类型系统
- **用途**: 提供类型检查和类型安全
- **功能**: 参数类型验证、返回值类型检查
- **依赖类型**: Python 类型系统

## 核心功能

### 1. 服务注册机制
```python
def register_ai_service(mode: str, service: str):
    """
    装饰器：将服务类注册到服务注册中心
    
    Args:
        mode: 服务模式 (如 "execute", "analyze", "generate")
        service: 服务名称 (如 "openai", "vertex", "custom")
    """
    def decorator(cls):
        AI_SERVICE_REGISTRY[(mode, service)] = cls
        return cls
    return decorator
```

**特性**：
- **装饰器模式**：使用 `@register_ai_service(mode, service)` 语法
- **键值映射**：使用 `(mode, service)` 元组作为唯一标识
- **类型保持**：装饰器不改变原类的类型和接口
- **延迟注册**：支持模块导入时的自动注册

### 2. 服务发现机制
```python
def get_ai_service(mode: str, service: str):
    """
    根据模式和服务名获取注册的服务类
    
    Args:
        mode: 服务模式
        service: 服务名称
        
    Returns:
        注册的服务类
        
    Raises:
        ValueError: 当服务未注册时
    """
    key = (mode, service)
    if key not in AI_SERVICE_REGISTRY:
        raise ValueError(f"No registered service for mode '{mode}', service '{service}'")
    return AI_SERVICE_REGISTRY[key]
```

**特性**：
- **类型安全**：返回类型为注册的服务类
- **错误处理**：未找到服务时抛出明确的错误信息
- **性能优化**：O(1) 时间复杂度的字典查找
- **线程安全**：支持多线程环境下的并发访问

### 3. 服务注册表管理
```python
AI_SERVICE_REGISTRY = {}
```
- **全局注册表**：存储所有注册的服务类
- **键值结构**：`{(mode, service): service_class}` 的映射关系
- **内存存储**：基于 Python 字典的快速查找
- **生命周期**：与应用程序生命周期一致

## 设计模式详解

### 1. 装饰器模式 (Decorator Pattern)
```python
# 服务注册示例
@register_ai_service("execute", "openai")
class OpenAIExecuteService:
    def __init__(self):
        self.client = OpenAI()
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        # 实现 OpenAI 任务执行逻辑
        pass
```

**优势**：
- **非侵入性**：不修改原有类的结构
- **声明式**：通过装饰器明确表达服务注册意图
- **可读性**：代码意图清晰，易于理解

### 2. 注册表模式 (Registry Pattern)
```python
# 服务发现示例
def create_service_instance(mode: str, service: str):
    """创建服务实例"""
    service_class = get_ai_service(mode, service)
    return service_class()
```

**优势**：
- **解耦**：服务使用者不需要知道具体实现类
- **扩展性**：新增服务无需修改现有代码
- **统一管理**：所有服务通过统一接口访问

### 3. 工厂模式 (Factory Pattern)
```python
# 服务工厂示例
class ServiceFactory:
    @staticmethod
    def create_service(mode: str, service: str, **kwargs):
        """创建服务实例的工厂方法"""
        service_class = get_ai_service(mode, service)
        return service_class(**kwargs)
```

## 服务注册规范

### 1. 服务命名规范
```python
# 模式命名规范
modes = [
    "execute",    # 任务执行服务
    "analyze",    # 数据分析服务
    "generate",   # 内容生成服务
    "transform",  # 数据转换服务
    "validate",   # 数据验证服务
    "search",     # 搜索服务
    "recommend"   # 推荐服务
]

# 服务命名规范
services = [
    "openai",     # OpenAI 服务
    "vertex",     # Google Vertex AI 服务
    "xai",        # xAI 服务
    "custom",     # 自定义服务
    "local",      # 本地服务
    "hybrid"      # 混合服务
]
```

### 2. 服务接口规范
```python
from abc import ABC, abstractmethod

class BaseAIService(ABC):
    """AI 服务基类"""
    
    @abstractmethod
    def execute_task(self, task_name: str, input_data: dict, context: dict) -> dict:
        """执行任务"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> list:
        """获取服务能力列表"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass

# 服务实现示例
@register_ai_service("execute", "openai")
class OpenAIExecuteService(BaseAIService):
    def execute_task(self, task_name: str, input_data: dict, context: dict) -> dict:
        # 实现具体逻辑
        pass
    
    def get_capabilities(self) -> list:
        return ["text_generation", "text_completion", "chat_completion"]
    
    def health_check(self) -> bool:
        # 实现健康检查逻辑
        return True
```

### 3. 服务元数据规范
```python
@register_ai_service("execute", "openai")
class OpenAIExecuteService(BaseAIService):
    # 服务元数据
    SERVICE_NAME = "OpenAI Execute Service"
    SERVICE_VERSION = "1.0.0"
    SERVICE_DESCRIPTION = "基于 OpenAI API 的任务执行服务"
    SERVICE_CAPABILITIES = ["text_generation", "text_completion"]
    SERVICE_REQUIREMENTS = ["openai_api_key"]
    
    def __init__(self):
        self.metadata = {
            "name": self.SERVICE_NAME,
            "version": self.SERVICE_VERSION,
            "description": self.SERVICE_DESCRIPTION,
            "capabilities": self.SERVICE_CAPABILITIES,
            "requirements": self.SERVICE_REQUIREMENTS
        }
```

## 使用示例

### 1. 基本服务注册
```python
from aiecs.config.registry import register_ai_service

@register_ai_service("execute", "openai")
class OpenAIExecuteService:
    def __init__(self):
        self.client = OpenAI()
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        if task_name == "text_generation":
            return self.client.completions.create(
                model="gpt-3.5-turbo",
                prompt=input_data.get("prompt", ""),
                max_tokens=input_data.get("max_tokens", 100)
            )
        else:
            raise ValueError(f"Unsupported task: {task_name}")

@register_ai_service("analyze", "custom")
class CustomAnalyzeService:
    def __init__(self):
        self.analyzer = CustomAnalyzer()
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        return self.analyzer.analyze(input_data)
```

### 2. 服务发现和使用
```python
from aiecs.config.registry import get_ai_service

def execute_ai_task(mode: str, service: str, task_name: str, input_data: dict, context: dict):
    """执行 AI 任务"""
    try:
        # 获取服务类
        service_class = get_ai_service(mode, service)
        
        # 创建服务实例
        service_instance = service_class()
        
        # 执行任务
        result = service_instance.execute_task(task_name, input_data, context)
        
        return {
            "success": True,
            "result": result,
            "service": f"{mode}.{service}"
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "service": f"{mode}.{service}"
        }
```

### 3. 服务列表查询
```python
from aiecs.config.registry import AI_SERVICE_REGISTRY

def get_available_services():
    """获取所有可用服务"""
    services = []
    for (mode, service), service_class in AI_SERVICE_REGISTRY.items():
        # 创建临时实例获取元数据
        instance = service_class()
        metadata = getattr(instance, 'metadata', {})
        
        services.append({
            "mode": mode,
            "service": service,
            "class_name": service_class.__name__,
            "metadata": metadata
        })
    
    return services
```

### 4. 服务工厂模式
```python
class AIServiceFactory:
    """AI 服务工厂"""
    
    @staticmethod
    def create_service(mode: str, service: str, **kwargs):
        """创建服务实例"""
        service_class = get_ai_service(mode, service)
        return service_class(**kwargs)
    
    @staticmethod
    def get_service_info(mode: str, service: str):
        """获取服务信息"""
        service_class = get_ai_service(mode, service)
        return {
            "class_name": service_class.__name__,
            "module": service_class.__module__,
            "docstring": service_class.__doc__
        }
    
    @staticmethod
    def list_services_by_mode(mode: str):
        """按模式列出服务"""
        return [
            service for (m, service) in AI_SERVICE_REGISTRY.keys() 
            if m == mode
        ]
```

## 维护指南

### 1. 日常维护

#### 服务注册表健康检查
```python
def check_registry_health():
    """检查服务注册表健康状态"""
    issues = []
    
    # 检查注册表是否为空
    if not AI_SERVICE_REGISTRY:
        issues.append("服务注册表为空")
    
    # 检查重复注册
    keys = list(AI_SERVICE_REGISTRY.keys())
    if len(keys) != len(set(keys)):
        issues.append("存在重复的服务注册")
    
    # 检查服务类是否可实例化
    for (mode, service), service_class in AI_SERVICE_REGISTRY.items():
        try:
            instance = service_class()
            if not hasattr(instance, 'execute_task'):
                issues.append(f"服务 {mode}.{service} 缺少 execute_task 方法")
        except Exception as e:
            issues.append(f"服务 {mode}.{service} 实例化失败: {e}")
    
    return len(issues) == 0, issues
```

#### 服务注册表监控
```python
def get_registry_metrics():
    """获取注册表指标"""
    return {
        "total_services": len(AI_SERVICE_REGISTRY),
        "services_by_mode": {
            mode: len([s for m, s in AI_SERVICE_REGISTRY.keys() if m == mode])
            for mode in set(m for m, s in AI_SERVICE_REGISTRY.keys())
        },
        "services_by_name": {
            service: len([m for m, s in AI_SERVICE_REGISTRY.keys() if s == service])
            for service in set(s for m, s in AI_SERVICE_REGISTRY.keys())
        }
    }
```

### 2. 故障排查

#### 常见问题诊断

**问题1: 服务未注册**
```python
# 错误信息
ValueError: No registered service for mode 'execute', service 'openai'

# 诊断步骤
def diagnose_service_not_found(mode: str, service: str):
    """诊断服务未找到问题"""
    print(f"查找服务: {mode}.{service}")
    print(f"注册表中的服务: {list(AI_SERVICE_REGISTRY.keys())}")
    
    # 检查模式匹配
    mode_services = [s for m, s in AI_SERVICE_REGISTRY.keys() if m == mode]
    print(f"模式 '{mode}' 下的服务: {mode_services}")
    
    # 检查服务名匹配
    service_modes = [m for m, s in AI_SERVICE_REGISTRY.keys() if s == service]
    print(f"服务 '{service}' 的模式: {service_modes}")
    
    # 检查大小写
    case_insensitive_keys = [(m.lower(), s.lower()) for m, s in AI_SERVICE_REGISTRY.keys()]
    if (mode.lower(), service.lower()) in case_insensitive_keys:
        print("注意: 可能存在大小写不匹配问题")
```

**问题2: 服务实例化失败**
```python
# 错误信息
TypeError: __init__() missing 1 required positional argument: 'api_key'

# 诊断步骤
def diagnose_instantiation_failure(mode: str, service: str):
    """诊断服务实例化失败问题"""
    try:
        service_class = get_ai_service(mode, service)
        print(f"服务类: {service_class}")
        print(f"构造函数签名: {service_class.__init__.__annotations__}")
        
        # 尝试创建实例
        instance = service_class()
        print("服务实例化成功")
    except Exception as e:
        print(f"服务实例化失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        
        # 检查构造函数参数
        import inspect
        sig = inspect.signature(service_class.__init__)
        print(f"构造函数参数: {list(sig.parameters.keys())}")
```

**问题3: 循环依赖**
```python
# 错误信息
ImportError: cannot import name 'ServiceA' from partially initialized module

# 诊断步骤
def diagnose_circular_dependency():
    """诊断循环依赖问题"""
    import sys
    import importlib
    
    # 检查模块依赖关系
    for module_name, module in sys.modules.items():
        if hasattr(module, '__file__') and 'aiecs' in module_name:
            print(f"模块: {module_name}")
            print(f"文件: {module.__file__}")
            
            # 检查模块中的服务注册
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, '__module__') and attr.__module__ == module_name:
                    if hasattr(attr, '__name__') and 'Service' in attr.__name__:
                        print(f"  服务类: {attr.__name__}")
```

### 3. 配置更新

#### 添加新服务类型
```python
# 1. 定义新的服务基类
class BaseDataService(ABC):
    """数据服务基类"""
    
    @abstractmethod
    def process_data(self, data: dict) -> dict:
        pass

# 2. 实现具体服务
@register_ai_service("process", "etl")
class ETLDataService(BaseDataService):
    def process_data(self, data: dict) -> dict:
        # 实现 ETL 逻辑
        pass

# 3. 更新服务发现逻辑
def get_data_service(service: str):
    """获取数据服务"""
    return get_ai_service("process", service)
```

#### 服务版本管理
```python
# 支持服务版本
@register_ai_service("execute", "openai_v2")
class OpenAIExecuteServiceV2:
    VERSION = "2.0.0"
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        # V2 实现
        pass

# 版本兼容性检查
def check_service_compatibility(mode: str, service: str, required_version: str = None):
    """检查服务版本兼容性"""
    service_class = get_ai_service(mode, service)
    
    if hasattr(service_class, 'VERSION'):
        service_version = service_class.VERSION
        if required_version and service_version < required_version:
            raise ValueError(f"服务版本不兼容: 需要 {required_version}, 当前 {service_version}")
    
    return True
```

### 4. 配置扩展

#### 支持服务配置
```python
# 服务配置注册表
SERVICE_CONFIG_REGISTRY = {}

def register_service_config(mode: str, service: str, config: dict):
    """注册服务配置"""
    SERVICE_CONFIG_REGISTRY[(mode, service)] = config

def get_service_config(mode: str, service: str) -> dict:
    """获取服务配置"""
    return SERVICE_CONFIG_REGISTRY.get((mode, service), {})

# 配置化服务创建
def create_configured_service(mode: str, service: str):
    """创建配置化服务实例"""
    service_class = get_ai_service(mode, service)
    config = get_service_config(mode, service)
    
    if config:
        return service_class(**config)
    else:
        return service_class()
```

#### 支持服务生命周期管理
```python
class ServiceLifecycleManager:
    """服务生命周期管理器"""
    
    def __init__(self):
        self._instances = {}
        self._initialized = set()
    
    def get_service(self, mode: str, service: str, singleton: bool = True):
        """获取服务实例"""
        key = (mode, service)
        
        if singleton and key in self._instances:
            return self._instances[key]
        
        service_class = get_ai_service(mode, service)
        instance = service_class()
        
        if singleton:
            self._instances[key] = instance
        
        return instance
    
    def initialize_service(self, mode: str, service: str):
        """初始化服务"""
        key = (mode, service)
        if key not in self._initialized:
            instance = self.get_service(mode, service)
            if hasattr(instance, 'initialize'):
                instance.initialize()
            self._initialized.add(key)
    
    def shutdown_service(self, mode: str, service: str):
        """关闭服务"""
        key = (mode, service)
        if key in self._instances:
            instance = self._instances[key]
            if hasattr(instance, 'shutdown'):
                instance.shutdown()
            del self._instances[key]
            self._initialized.discard(key)
```

## 性能优化

### 1. 服务缓存
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_service(mode: str, service: str):
    """缓存服务类获取"""
    return get_ai_service(mode, service)
```

### 2. 延迟加载
```python
class LazyServiceRegistry:
    """延迟加载服务注册表"""
    
    def __init__(self):
        self._services = {}
        self._loaded = set()
    
    def get_service(self, mode: str, service: str):
        """延迟加载服务"""
        key = (mode, service)
        if key not in self._loaded:
            self._load_service(mode, service)
            self._loaded.add(key)
        
        return self._services[key]
    
    def _load_service(self, mode: str, service: str):
        """加载服务"""
        # 实现延迟加载逻辑
        pass
```

### 3. 服务预热
```python
def warmup_services():
    """预热常用服务"""
    common_services = [
        ("execute", "openai"),
        ("analyze", "custom"),
        ("generate", "vertex")
    ]
    
    for mode, service in common_services:
        try:
            get_ai_service(mode, service)
            print(f"✅ 服务 {mode}.{service} 预热成功")
        except ValueError:
            print(f"⚠️ 服务 {mode}.{service} 未注册")
```

## 监控与日志

### 服务注册表监控
```python
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class ServiceRegistryMonitor:
    """服务注册表监控器"""
    
    def __init__(self):
        self.service_calls = defaultdict(int)
        self.service_errors = defaultdict(int)
        self.service_latency = defaultdict(list)
    
    def record_service_call(self, mode: str, service: str, latency: float, success: bool):
        """记录服务调用"""
        key = f"{mode}.{service}"
        self.service_calls[key] += 1
        
        if not success:
            self.service_errors[key] += 1
        
        self.service_latency[key].append(latency)
        
        logger.info(f"服务调用: {key}, 延迟: {latency:.3f}s, 成功: {success}")
    
    def get_metrics(self):
        """获取监控指标"""
        return {
            "total_calls": sum(self.service_calls.values()),
            "total_errors": sum(self.service_errors.values()),
            "service_stats": {
                service: {
                    "calls": self.service_calls[service],
                    "errors": self.service_errors[service],
                    "avg_latency": sum(self.service_latency[service]) / len(self.service_latency[service]) if self.service_latency[service] else 0
                }
                for service in self.service_calls.keys()
            }
        }
```

## 版本历史

- **v1.0.0**: 初始版本，基础服务注册功能
- **v1.1.0**: 添加服务元数据支持
- **v1.2.0**: 支持服务配置管理
- **v1.3.0**: 添加服务生命周期管理
- **v1.4.0**: 支持服务版本控制和兼容性检查
- **v1.5.0**: 添加监控和性能优化功能

## 相关文档

- [AIECS 项目总览](../PROJECT_SUMMARY.md)
- [配置管理指南](./CONFIG_MANAGEMENT.md)
- [服务开发指南](./SERVICE_DEVELOPMENT_GUIDE.md)
- [API 使用指南](./USAGE_GUIDE.md)
