# Service Registry Technical Documentation

## Overview

### Design Motivation and Problem Background

When building scalable AI service systems, service management faces the following core challenges:

**1. Service Discovery and Routing Complexity**
- Multiple AI services (different modes, different providers) need unified management
- Dependency and invocation relationships between services are difficult to maintain
- Dynamic service registration and discovery mechanisms are missing

**2. Service Lifecycle Management Difficulties**
- Service registration, instantiation, invocation, and destruction lack unified standards
- Service version management and compatibility control are complex
- Service health checks and failover mechanisms are incomplete

**3. Service Configuration and Metadata Management**
- Service configuration parameters, dependencies, and capability descriptions are scattered
- Lack of automatic service capability discovery and documentation generation
- Interface contracts between services are unclear

**4. Scalability and Maintainability Challenges**
- Adding new services requires modifying multiple files, violating the open-closed principle
- Tight coupling between services makes the system difficult to extend
- Lack of standardized service registration processes

**Service Registry Solution**:
- **Decorator Pattern**: Simplify service registration through `@register_ai_service` decorator
- **Key-Value Mapping**: Use `(mode, service)` tuple as service identifier
- **Lazy Loading**: Support on-demand service registration and instantiation
- **Type Safety**: Service type checking based on Python type system
- **Decoupled Design**: Service registration separated from business logic, supporting plugin architecture

### Component Positioning

`registry.py` is the service registry center of the AIECS system, responsible for unified management of all AI service registration, discovery, and instantiation. As a core component of the infrastructure layer, it provides a decorator-based service registration mechanism.

## Component Type and Positioning

### Component Type
**Infrastructure Component** - Located in the Infrastructure Layer, belongs to system foundation services

### Architecture Layers
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← Components using services
│  (Task Executor, API Endpoints)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │
│  (Service Interfaces, Business Logic)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← Service registry layer
│  (Service Registry, Service Discovery)  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Service Layer                   │  ← Registered services
│  (AI Services, External Integrations)   │
└─────────────────────────────────────────┘
```

## Upstream Components (Consumers)

### 1. Task Executor (`tasks/worker.py`)
- **Purpose**: Celery task execution, needs to get service instances based on mode and service parameters
- **Usage**: Get service class and instantiate via `get_ai_service(mode, service)`
- **Dependency**: Direct dependency, used for dynamic service discovery

### 2. FastAPI Application (`main.py`)
- **Purpose**: Web API service, provides available service list query interface
- **Usage**: Get all registered services via `AI_SERVICE_REGISTRY`
- **Dependency**: Direct dependency, used for service metadata queries

### 3. Service Manager (`infrastructure/messaging/celery_task_manager.py`)
- **Purpose**: Task scheduling and management, needs to select execution strategy based on service type
- **Usage**: Get service information through service registry for task routing
- **Dependency**: Indirect dependency, used through task executor

## Downstream Components (Dependencies)

### 1. Python Decorator System
- **Purpose**: Provide decorator syntax support
- **Functionality**: Function and class decorator mechanisms
- **Dependency Type**: Language feature dependency

### 2. Service Implementation Classes
- **Purpose**: Specific AI service implementations
- **Functionality**: Business logic implementation, external API calls
- **Dependency Type**: Registered service classes

### 3. Type System
- **Purpose**: Provide type checking and type safety
- **Functionality**: Parameter type validation, return value type checking
- **Dependency Type**: Python type system

## Core Features

### 1. Service Registration Mechanism
```python
def register_ai_service(mode: str, service: str):
    """
    Decorator: Register service class to service registry
    
    Args:
        mode: Service mode (e.g., "execute", "analyze", "generate")
        service: Service name (e.g., "openai", "vertex", "custom")
    """
    def decorator(cls):
        AI_SERVICE_REGISTRY[(mode, service)] = cls
        return cls
    return decorator
```

**Features**:
- **Decorator Pattern**: Use `@register_ai_service(mode, service)` syntax
- **Key-Value Mapping**: Use `(mode, service)` tuple as unique identifier
- **Type Preservation**: Decorator does not change original class type and interface
- **Lazy Registration**: Support automatic registration during module import

### 2. Service Discovery Mechanism
```python
def get_ai_service(mode: str, service: str):
    """
    Get registered service class based on mode and service name
    
    Args:
        mode: Service mode
        service: Service name
        
    Returns:
        Registered service class
        
    Raises:
        ValueError: When service is not registered
    """
    key = (mode, service)
    if key not in AI_SERVICE_REGISTRY:
        raise ValueError(f"No registered service for mode '{mode}', service '{service}'")
    return AI_SERVICE_REGISTRY[key]
```

**Features**:
- **Type Safety**: Return type is the registered service class
- **Error Handling**: Throws clear error message when service not found
- **Performance Optimization**: O(1) time complexity dictionary lookup
- **Thread Safety**: Support concurrent access in multi-threaded environments

### 3. Service Registry Management
```python
AI_SERVICE_REGISTRY = {}
```
- **Global Registry**: Store all registered service classes
- **Key-Value Structure**: Mapping relationship of `{(mode, service): service_class}`
- **In-Memory Storage**: Fast lookup based on Python dictionary
- **Lifecycle**: Consistent with application lifecycle

## Design Patterns Explained

### 1. Decorator Pattern
```python
# Service registration example
@register_ai_service("execute", "openai")
class OpenAIExecuteService:
    def __init__(self):
        self.client = OpenAI()
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        # Implement OpenAI task execution logic
        pass
```

**Advantages**:
- **Non-Invasive**: Does not modify original class structure
- **Declarative**: Clearly express service registration intent through decorator
- **Readability**: Clear code intent, easy to understand

### 2. Registry Pattern
```python
# Service discovery example
def create_service_instance(mode: str, service: str):
    """Create service instance"""
    service_class = get_ai_service(mode, service)
    return service_class()
```

**Advantages**:
- **Decoupling**: Service consumers don't need to know specific implementation classes
- **Extensibility**: Adding new services doesn't require modifying existing code
- **Unified Management**: All services accessed through unified interface

### 3. Factory Pattern
```python
# Service factory example
class ServiceFactory:
    @staticmethod
    def create_service(mode: str, service: str, **kwargs):
        """Factory method to create service instance"""
        service_class = get_ai_service(mode, service)
        return service_class(**kwargs)
```

## Service Registration Standards

### 1. Service Naming Conventions
```python
# Mode naming conventions
modes = [
    "execute",    # Task execution service
    "analyze",    # Data analysis service
    "generate",   # Content generation service
    "transform",  # Data transformation service
    "validate",   # Data validation service
    "search",     # Search service
    "recommend"   # Recommendation service
]

# Service naming conventions
services = [
    "openai",     # OpenAI service
    "vertex",     # Google Vertex AI service
    "xai",        # xAI service
    "custom",     # Custom service
    "local",      # Local service
    "hybrid"      # Hybrid service
]
```

### 2. Service Interface Standards
```python
from abc import ABC, abstractmethod

class BaseAIService(ABC):
    """AI service base class"""
    
    @abstractmethod
    def execute_task(self, task_name: str, input_data: dict, context: dict) -> dict:
        """Execute task"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> list:
        """Get service capability list"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Health check"""
        pass

# Service implementation example
@register_ai_service("execute", "openai")
class OpenAIExecuteService(BaseAIService):
    def execute_task(self, task_name: str, input_data: dict, context: dict) -> dict:
        # Implement specific logic
        pass
    
    def get_capabilities(self) -> list:
        return ["text_generation", "text_completion", "chat_completion"]
    
    def health_check(self) -> bool:
        # Implement health check logic
        return True
```

### 3. Service Metadata Standards
```python
@register_ai_service("execute", "openai")
class OpenAIExecuteService(BaseAIService):
    # Service metadata
    SERVICE_NAME = "OpenAI Execute Service"
    SERVICE_VERSION = "1.0.0"
    SERVICE_DESCRIPTION = "Task execution service based on OpenAI API"
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

## Usage Examples

### 1. Basic Service Registration
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

### 2. Service Discovery and Usage
```python
from aiecs.config.registry import get_ai_service

def execute_ai_task(mode: str, service: str, task_name: str, input_data: dict, context: dict):
    """Execute AI task"""
    try:
        # Get service class
        service_class = get_ai_service(mode, service)
        
        # Create service instance
        service_instance = service_class()
        
        # Execute task
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

### 3. Service List Query
```python
from aiecs.config.registry import AI_SERVICE_REGISTRY

def get_available_services():
    """Get all available services"""
    services = []
    for (mode, service), service_class in AI_SERVICE_REGISTRY.items():
        # Create temporary instance to get metadata
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

### 4. Service Factory Pattern
```python
class AIServiceFactory:
    """AI service factory"""
    
    @staticmethod
    def create_service(mode: str, service: str, **kwargs):
        """Create service instance"""
        service_class = get_ai_service(mode, service)
        return service_class(**kwargs)
    
    @staticmethod
    def get_service_info(mode: str, service: str):
        """Get service information"""
        service_class = get_ai_service(mode, service)
        return {
            "class_name": service_class.__name__,
            "module": service_class.__module__,
            "docstring": service_class.__doc__
        }
    
    @staticmethod
    def list_services_by_mode(mode: str):
        """List services by mode"""
        return [
            service for (m, service) in AI_SERVICE_REGISTRY.keys() 
            if m == mode
        ]
```

## Maintenance Guide

### 1. Daily Maintenance

#### Service Registry Health Check
```python
def check_registry_health():
    """Check service registry health status"""
    issues = []
    
    # Check if registry is empty
    if not AI_SERVICE_REGISTRY:
        issues.append("Service registry is empty")
    
    # Check for duplicate registrations
    keys = list(AI_SERVICE_REGISTRY.keys())
    if len(keys) != len(set(keys)):
        issues.append("Duplicate service registrations exist")
    
    # Check if service classes can be instantiated
    for (mode, service), service_class in AI_SERVICE_REGISTRY.items():
        try:
            instance = service_class()
            if not hasattr(instance, 'execute_task'):
                issues.append(f"Service {mode}.{service} missing execute_task method")
        except Exception as e:
            issues.append(f"Service {mode}.{service} instantiation failed: {e}")
    
    return len(issues) == 0, issues
```

#### Service Registry Monitoring
```python
def get_registry_metrics():
    """Get registry metrics"""
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

### 2. Troubleshooting

#### Common Issue Diagnosis

**Issue 1: Service Not Registered**
```python
# Error message
ValueError: No registered service for mode 'execute', service 'openai'

# Diagnosis steps
def diagnose_service_not_found(mode: str, service: str):
    """Diagnose service not found issue"""
    print(f"Looking for service: {mode}.{service}")
    print(f"Services in registry: {list(AI_SERVICE_REGISTRY.keys())}")
    
    # Check mode matching
    mode_services = [s for m, s in AI_SERVICE_REGISTRY.keys() if m == mode]
    print(f"Services under mode '{mode}': {mode_services}")
    
    # Check service name matching
    service_modes = [m for m, s in AI_SERVICE_REGISTRY.keys() if s == service]
    print(f"Modes for service '{service}': {service_modes}")
    
    # Check case sensitivity
    case_insensitive_keys = [(m.lower(), s.lower()) for m, s in AI_SERVICE_REGISTRY.keys()]
    if (mode.lower(), service.lower()) in case_insensitive_keys:
        print("Note: Possible case mismatch issue")
```

**Issue 2: Service Instantiation Failed**
```python
# Error message
TypeError: __init__() missing 1 required positional argument: 'api_key'

# Diagnosis steps
def diagnose_instantiation_failure(mode: str, service: str):
    """Diagnose service instantiation failure issue"""
    try:
        service_class = get_ai_service(mode, service)
        print(f"Service class: {service_class}")
        print(f"Constructor signature: {service_class.__init__.__annotations__}")
        
        # Try to create instance
        instance = service_class()
        print("Service instantiation successful")
    except Exception as e:
        print(f"Service instantiation failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Check constructor parameters
        import inspect
        sig = inspect.signature(service_class.__init__)
        print(f"Constructor parameters: {list(sig.parameters.keys())}")
```

**Issue 3: Circular Dependency**
```python
# Error message
ImportError: cannot import name 'ServiceA' from partially initialized module

# Diagnosis steps
def diagnose_circular_dependency():
    """Diagnose circular dependency issue"""
    import sys
    import importlib
    
    # Check module dependency relationships
    for module_name, module in sys.modules.items():
        if hasattr(module, '__file__') and 'aiecs' in module_name:
            print(f"Module: {module_name}")
            print(f"File: {module.__file__}")
            
            # Check service registrations in module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, '__module__') and attr.__module__ == module_name:
                    if hasattr(attr, '__name__') and 'Service' in attr.__name__:
                        print(f"  Service class: {attr.__name__}")
```

### 3. Configuration Updates

#### Adding New Service Types
```python
# 1. Define new service base class
class BaseDataService(ABC):
    """Data service base class"""
    
    @abstractmethod
    def process_data(self, data: dict) -> dict:
        pass

# 2. Implement specific service
@register_ai_service("process", "etl")
class ETLDataService(BaseDataService):
    def process_data(self, data: dict) -> dict:
        # Implement ETL logic
        pass

# 3. Update service discovery logic
def get_data_service(service: str):
    """Get data service"""
    return get_ai_service("process", service)
```

#### Service Version Management
```python
# Support service versions
@register_ai_service("execute", "openai_v2")
class OpenAIExecuteServiceV2:
    VERSION = "2.0.0"
    
    def execute_task(self, task_name: str, input_data: dict, context: dict):
        # V2 implementation
        pass

# Version compatibility check
def check_service_compatibility(mode: str, service: str, required_version: str = None):
    """Check service version compatibility"""
    service_class = get_ai_service(mode, service)
    
    if hasattr(service_class, 'VERSION'):
        service_version = service_class.VERSION
        if required_version and service_version < required_version:
            raise ValueError(f"Service version incompatible: requires {required_version}, current {service_version}")
    
    return True
```

### 4. Configuration Extension

#### Support Service Configuration
```python
# Service configuration registry
SERVICE_CONFIG_REGISTRY = {}

def register_service_config(mode: str, service: str, config: dict):
    """Register service configuration"""
    SERVICE_CONFIG_REGISTRY[(mode, service)] = config

def get_service_config(mode: str, service: str) -> dict:
    """Get service configuration"""
    return SERVICE_CONFIG_REGISTRY.get((mode, service), {})

# Configuration-based service creation
def create_configured_service(mode: str, service: str):
    """Create configured service instance"""
    service_class = get_ai_service(mode, service)
    config = get_service_config(mode, service)
    
    if config:
        return service_class(**config)
    else:
        return service_class()
```

#### Support Service Lifecycle Management
```python
class ServiceLifecycleManager:
    """Service lifecycle manager"""
    
    def __init__(self):
        self._instances = {}
        self._initialized = set()
    
    def get_service(self, mode: str, service: str, singleton: bool = True):
        """Get service instance"""
        key = (mode, service)
        
        if singleton and key in self._instances:
            return self._instances[key]
        
        service_class = get_ai_service(mode, service)
        instance = service_class()
        
        if singleton:
            self._instances[key] = instance
        
        return instance
    
    def initialize_service(self, mode: str, service: str):
        """Initialize service"""
        key = (mode, service)
        if key not in self._initialized:
            instance = self.get_service(mode, service)
            if hasattr(instance, 'initialize'):
                instance.initialize()
            self._initialized.add(key)
    
    def shutdown_service(self, mode: str, service: str):
        """Shutdown service"""
        key = (mode, service)
        if key in self._instances:
            instance = self._instances[key]
            if hasattr(instance, 'shutdown'):
                instance.shutdown()
            del self._instances[key]
            self._initialized.discard(key)
```

## Performance Optimization

### 1. Service Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_service(mode: str, service: str):
    """Cache service class retrieval"""
    return get_ai_service(mode, service)
```

### 2. Lazy Loading
```python
class LazyServiceRegistry:
    """Lazy loading service registry"""
    
    def __init__(self):
        self._services = {}
        self._loaded = set()
    
    def get_service(self, mode: str, service: str):
        """Lazy load service"""
        key = (mode, service)
        if key not in self._loaded:
            self._load_service(mode, service)
            self._loaded.add(key)
        
        return self._services[key]
    
    def _load_service(self, mode: str, service: str):
        """Load service"""
        # Implement lazy loading logic
        pass
```

### 3. Service Warmup
```python
def warmup_services():
    """Warmup common services"""
    common_services = [
        ("execute", "openai"),
        ("analyze", "custom"),
        ("generate", "vertex")
    ]
    
    for mode, service in common_services:
        try:
            get_ai_service(mode, service)
            print(f"✅ Service {mode}.{service} warmed up successfully")
        except ValueError:
            print(f"⚠️ Service {mode}.{service} not registered")
```

## Monitoring and Logging

### Service Registry Monitoring
```python
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

class ServiceRegistryMonitor:
    """Service registry monitor"""
    
    def __init__(self):
        self.service_calls = defaultdict(int)
        self.service_errors = defaultdict(int)
        self.service_latency = defaultdict(list)
    
    def record_service_call(self, mode: str, service: str, latency: float, success: bool):
        """Record service call"""
        key = f"{mode}.{service}"
        self.service_calls[key] += 1
        
        if not success:
            self.service_errors[key] += 1
        
        self.service_latency[key].append(latency)
        
        logger.info(f"Service call: {key}, latency: {latency:.3f}s, success: {success}")
    
    def get_metrics(self):
        """Get monitoring metrics"""
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

## Version History

- **v1.0.0**: Initial version, basic service registration functionality
- **v1.1.0**: Added service metadata support
- **v1.2.0**: Support service configuration management
- **v1.3.0**: Added service lifecycle management
- **v1.4.0**: Support service version control and compatibility checking
- **v1.5.0**: Added monitoring and performance optimization features

## Related Documentation

- [AIECS Project Overview](../PROJECT_SUMMARY.md)
- [Configuration Management Guide](./CONFIG_MANAGEMENT.md)
- [Usage Guide](../USAGE_GUIDE.md)
