# Global Metrics Manager Technical Documentation

## 1. Overview

### Purpose
`GlobalMetricsManager` is a global singleton metrics manager used to uniformly manage all metrics collection in the AIECS system. It solves the port conflict issue caused by multiple components simultaneously creating `ExecutorMetrics` instances, providing a unified metrics collection interface.

### Core Value
- **Unified Metrics Management**: Global singleton pattern, avoiding port conflicts
- **Simplified Usage**: Provides convenient global access interface
- **Graceful Degradation**: Metrics collection failures do not affect main business functionality
- **Flexible Configuration**: Supports environment variables and parameter configuration

## 2. Problem Background & Design Motivation

### Problem Background
In the AIECS system, multiple components require metrics collection functionality:
- **FileStorage** - Storage operation metrics
- **ToolExecutor** - Tool execution metrics
- **DatabaseManager** - Database operation metrics
- **Other Components** - Various business metrics

Each component creating independent `ExecutorMetrics` instances leads to:
- **Port Conflicts**: Multiple instances attempting to bind to the same port 8001
- **Resource Waste**: Duplicate Prometheus server instances
- **Management Complexity**: Difficult to uniformly configure and manage metrics

### Design Motivation
1. **Solve Port Conflicts**: Global singleton ensures only one metrics server
2. **Unified Configuration Management**: Centralized management of metrics collection configuration
3. **Simplify Component Integration**: Components only need to obtain the global instance
4. **Improve Maintainability**: Unified metrics collection logic

## 3. Architecture Positioning & Context

### System Architecture Location
```
┌─────────────────────────────────────────────────────────────┐
│                    AIECS System Architecture                │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                         │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ FileStorage     │  │ ToolExecutor    │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ GlobalMetrics   │  │ ExecutorMetrics │                  │
│  │ Manager         │  │ (Prometheus)    │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Monitoring Layer                                          │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Prometheus      │  │ Grafana         │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies
- **Dependents**: `ExecutorMetrics`, `Prometheus Client`
- **Dependees**: `FileStorage`, `ToolExecutor`, `DatabaseManager`, and all other components requiring metrics collection

## 4. Core Features & Characteristics

### 4.1 Global Singleton Management
```python
# Global unique instance
_global_metrics: Optional[ExecutorMetrics] = None
_initialization_lock = asyncio.Lock()
_initialized = False
```

### 4.2 Thread-Safe Initialization
```python
async def initialize_global_metrics(
    enable_metrics: bool = True,
    metrics_port: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[ExecutorMetrics]:
    """Thread-safe global metrics initialization"""
    async with _initialization_lock:
        # Double-check locking pattern
        if _initialized and _global_metrics:
            return _global_metrics
        # ... initialization logic
```

### 4.3 Convenient Access Interface
```python
def get_global_metrics() -> Optional[ExecutorMetrics]:
    """Get global metrics instance"""
    return _global_metrics

# Convenience function
def record_operation(operation_type: str, success: bool = True, duration: Optional[float] = None, **kwargs):
    """Record operation metrics"""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_operation(operation_type, success, duration, **kwargs)
```

## 5. Usage Guide

### 5.1 Initialize at Application Startup

#### Initialize in main.py
```python
from aiecs.infrastructure.monitoring import (
    initialize_global_metrics,
    close_global_metrics
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize at startup
    try:
        await initialize_global_metrics()
        logger.info("Global metrics initialized")
    except Exception as e:
        logger.warning(f"Global metrics initialization failed: {e}")
    
    yield
    
    # Cleanup at shutdown
    try:
        await close_global_metrics()
        logger.info("Global metrics closed")
    except Exception as e:
        logger.warning(f"Error closing global metrics: {e}")
```

### 5.2 Usage in Components

#### Method 1: Directly Get Global Instance
```python
from aiecs.infrastructure.monitoring.global_metrics_manager import get_global_metrics

class MyComponent:
    def __init__(self):
        self.metrics = get_global_metrics()
    
    def do_operation(self):
        if self.metrics:
            self.metrics.record_operation('my_operation', success=True)
```

#### Method 2: Use Convenience Functions
```python
from aiecs.infrastructure.monitoring import record_operation, record_duration

class MyComponent:
    def do_operation(self):
        start_time = time.time()
        try:
            # ... business logic ...
            duration = time.time() - start_time
            record_operation('my_operation', success=True, duration=duration)
        except Exception as e:
            record_operation('my_operation', success=False)
            raise
```

### 5.3 Configuration Options

#### Environment Variable Configuration
```bash
# Enable/disable metrics collection
export ENABLE_METRICS=true

# Specify metrics server port
export METRICS_PORT=8001
```

#### Code Configuration
```python
# Custom configuration initialization
await initialize_global_metrics(
    enable_metrics=True,
    metrics_port=8002,
    config={
        'custom_setting': 'value'
    }
)
```

## 6. Migration Guide

### 6.1 Migrating from Independent ExecutorMetrics

#### Before Migration
```python
# Old way - each component creates independent instance
class FileStorage:
    def __init__(self):
        self.metrics = ExecutorMetrics(enable_metrics=True)  # May cause port conflicts
```

#### After Migration
```python
# New way - use global manager
from aiecs.infrastructure.monitoring.global_metrics_manager import get_global_metrics

class FileStorage:
    def __init__(self):
        self.metrics = get_global_metrics()  # Use global instance
```

### 6.2 Batch Migration Steps

1. **Update Import Statements**
```python
# Old import
from ..monitoring.executor_metrics import ExecutorMetrics

# New import
from ..monitoring.global_metrics_manager import get_global_metrics
```

2. **Update Instantiation Code**
```python
# Old instantiation
self.metrics = ExecutorMetrics(enable_metrics=True)

# New instantiation
self.metrics = get_global_metrics()
```

3. **Add Null Checks**
```python
# Add null checks
if self.metrics:
    self.metrics.record_operation('operation', success=True)
```

## 7. Best Practices

### 7.1 Initialization Order
```python
# Correct initialization order
async def lifespan(app: FastAPI):
    # 1. First initialize global metrics
    await initialize_global_metrics()
    
    # 2. Then initialize other components
    await initialize_database()
    await initialize_redis()
    # ...
```

### 7.2 Error Handling
```python
# Graceful error handling
def record_metrics_safely(operation: str, success: bool):
    try:
        metrics = get_global_metrics()
        if metrics:
            metrics.record_operation(operation, success)
    except Exception as e:
        logger.warning(f"Failed to record metrics: {e}")
        # Don't raise exception, avoid affecting main business
```

### 7.3 Performance Optimization
```python
# Cache global instance reference
class MyComponent:
    def __init__(self):
        self._metrics = get_global_metrics()  # Cache reference
    
    def do_operation(self):
        if self._metrics:  # Use cached reference
            self._metrics.record_operation('operation', success=True)
```

## 8. Troubleshooting

### 8.1 Common Issues

#### Issue 1: Metrics Not Initialized
**Symptoms**: `get_global_metrics()` returns `None`

**Solution**:
```python
# Check initialization status
from aiecs.infrastructure.monitoring import is_metrics_initialized

if not is_metrics_initialized():
    logger.warning("Global metrics not initialized")
    # Ensure initialize_global_metrics() was called at application startup
```

#### Issue 2: Port Still in Use
**Symptoms**: `Address already in use` error

**Solution**:
```python
# Use different port
await initialize_global_metrics(metrics_port=8002)

# Or via environment variable
export METRICS_PORT=8002
```

#### Issue 3: Metrics Recording Failed
**Symptoms**: Metrics data not updating

**Solution**:
```python
# Check metrics status
from aiecs.infrastructure.monitoring import get_metrics_summary

summary = get_metrics_summary()
print(f"Metrics status: {summary}")
```

### 8.2 Debugging Tips

#### Enable Verbose Logging
```python
import logging
logging.getLogger('aiecs.infrastructure.monitoring').setLevel(logging.DEBUG)
```

#### Check Metrics Endpoint
```bash
# Check if metrics server is running
curl http://localhost:8001/metrics
```

## 9. Performance Considerations

### 9.1 Memory Usage
- Global singleton pattern reduces memory usage
- Avoid duplicate Prometheus client instances

### 9.2 Network Overhead
- Single metrics server reduces network connections
- Unified metrics collection reduces network requests

### 9.3 Startup Time
- Early initialization reduces component startup delay
- Asynchronous initialization does not block application startup

## 10. Future Extensions

### 10.1 Multi-Instance Support
```python
# Future may support multiple metrics instances
await initialize_global_metrics(
    instance_name="primary",
    metrics_port=8001
)

await initialize_global_metrics(
    instance_name="secondary", 
    metrics_port=8002
)
```

### 10.2 Dynamic Configuration
```python
# Runtime configuration updates
def update_metrics_config(new_config: Dict[str, Any]):
    """Dynamically update metrics configuration"""
    pass
```

### 10.3 Metrics Aggregation
```python
# Cross-instance metrics aggregation
def aggregate_metrics(instances: List[str]) -> Dict[str, Any]:
    """Aggregate metrics from multiple instances"""
    pass
```

## Summary

`GlobalMetricsManager` solves the metrics collection port conflict issue in the AIECS system through the global singleton pattern, providing a unified, efficient, and easy-to-use metrics management solution. It follows the system's existing architectural patterns, ensuring good maintainability and extensibility.
