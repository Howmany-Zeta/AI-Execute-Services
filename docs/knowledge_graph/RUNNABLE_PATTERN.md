# Runnable Pattern Guide

## Overview

The **Runnable Pattern** provides a formal base class for async task components with standardized lifecycle management, configuration, error handling, and retry logic. It's designed to make building robust, production-ready async components easier and more consistent.

## Table of Contents

- [Why Use Runnable?](#why-use-runnable)
- [Core Features](#core-features)
- [Quick Start](#quick-start)
- [Lifecycle Management](#lifecycle-management)
- [Configuration](#configuration)
- [Error Handling & Retry Logic](#error-handling--retry-logic)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Metrics & Monitoring](#metrics--monitoring)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)

## Why Use Runnable?

Building async components often requires implementing the same patterns repeatedly:
- Setup and teardown of resources
- Error handling and retry logic
- Configuration management
- Metrics collection
- Circuit breaker for fault tolerance

The Runnable pattern provides all of this out-of-the-box, letting you focus on your component's core logic.

## Core Features

✅ **Lifecycle Management**: Standardized setup → execute → teardown pattern  
✅ **Configuration**: Type-safe configuration with validation  
✅ **Retry Logic**: Exponential backoff with configurable retries  
✅ **Circuit Breaker**: Prevent cascading failures  
✅ **Timeout Support**: Automatic timeout handling  
✅ **Metrics**: Built-in execution metrics collection  
✅ **Async Context Manager**: Clean resource management with `async with`  

## Quick Start

### Basic Example

```python
from dataclasses import dataclass
from typing import Dict, Any
from aiecs.common.knowledge_graph import Runnable, RunnableConfig

# 1. Define your configuration
@dataclass
class MyConfig(RunnableConfig):
    api_key: str = ""
    max_items: int = 100

# 2. Implement your component
class MyComponent(Runnable[MyConfig, Dict[str, Any]]):
    async def _setup(self) -> None:
        """Initialize resources"""
        self.client = APIClient(self.config.api_key)
        print("Component initialized")
    
    async def _execute(self, **kwargs) -> Dict[str, Any]:
        """Main execution logic"""
        query = kwargs.get("query", "")
        results = await self.client.search(query, limit=self.config.max_items)
        return {"results": results, "count": len(results)}
    
    async def _teardown(self) -> None:
        """Cleanup resources"""
        await self.client.close()
        print("Component cleaned up")

# 3. Use your component
async def main():
    config = MyConfig(api_key="your-key", max_items=50)
    
    # Option 1: Manual lifecycle
    component = MyComponent(config)
    await component.setup()
    result = await component.run(query="knowledge graph")
    await component.teardown()
    
    # Option 2: Context manager (recommended)
    async with MyComponent(config) as component:
        result = await component.run(query="knowledge graph")
    
    print(f"Found {result['count']} results")
```

## Lifecycle Management

The Runnable pattern enforces a clear lifecycle:

```
CREATED → INITIALIZING → READY → RUNNING → COMPLETED/FAILED → STOPPED
```

### Lifecycle Methods

#### `setup()` - Initialize Resources

Called once before execution. Use this to:
- Initialize connections (database, API clients, etc.)
- Load models or data
- Validate configuration
- Allocate resources

```python
async def _setup(self) -> None:
    self.db = await connect_to_database(self.config.db_url)
    self.model = load_model(self.config.model_path)
```

#### `execute()` - Core Logic

The main execution method. Implement your component's logic here:

```python
async def _execute(self, **kwargs) -> ResultType:
    # Your logic here
    data = await self.db.query(kwargs["query"])
    predictions = self.model.predict(data)
    return {"predictions": predictions}
```

#### `teardown()` - Cleanup

Called after execution completes. Use this to:
- Close connections
- Release resources
- Save state
- Cleanup temporary files

```python
async def _teardown(self) -> None:
    await self.db.close()
    self.model.cleanup()
```

### State Transitions

```python
component = MyComponent(config)
print(component.state)  # RunnableState.CREATED

await component.setup()
print(component.state)  # RunnableState.READY

result = await component.execute()
print(component.state)  # RunnableState.COMPLETED

await component.teardown()
print(component.state)  # RunnableState.STOPPED
```

## Configuration

### Basic Configuration

All Runnable components use `RunnableConfig` as the base configuration class:

```python
@dataclass
class RunnableConfig:
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    max_retry_delay: float = 30.0
    
    # Timeout configuration
    timeout: Optional[float] = None
    
    # Circuit breaker configuration
    enable_circuit_breaker: bool = False
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    
    # Custom configuration
    custom_config: Dict[str, Any] = field(default_factory=dict)
```

### Custom Configuration

Extend `RunnableConfig` to add your own configuration:

```python
@dataclass
class DataProcessorConfig(RunnableConfig):
    # Your custom fields
    input_path: str = ""
    output_path: str = ""
    batch_size: int = 100
    
    # Override defaults
    max_retries: int = 5
    timeout: float = 300.0
```

### Configuration Validation

Override `_validate_config()` to add custom validation:

```python
class MyComponent(Runnable[MyConfig, ResultType]):
    def _validate_config(self) -> None:
        # Call parent validation
        super()._validate_config()
        
        # Add custom validation
        if not self.config.api_key:
            raise ValueError("api_key is required")
        
        if self.config.batch_size <= 0:
            raise ValueError("batch_size must be positive")
```

## Error Handling & Retry Logic

### Automatic Retries

The `run()` method automatically retries on failure with exponential backoff:

```python
config = MyConfig(
    max_retries=3,           # Retry up to 3 times
    retry_delay=1.0,         # Initial delay: 1 second
    retry_backoff=2.0,       # Double delay each retry
    max_retry_delay=30.0     # Cap delay at 30 seconds
)

component = MyComponent(config)
await component.setup()

# Will retry automatically on failure
# Delays: 1s, 2s, 4s (then fail)
result = await component.run(query="test")
```

### Retry Behavior

```
Attempt 1: Execute immediately
  ↓ (fails)
Wait 1.0 seconds
  ↓
Attempt 2: Retry
  ↓ (fails)
Wait 2.0 seconds (1.0 * 2.0)
  ↓
Attempt 3: Retry
  ↓ (fails)
Wait 4.0 seconds (2.0 * 2.0)
  ↓
Attempt 4: Final retry
  ↓ (fails)
Raise exception
```

### Execute vs Run

- **`execute()`**: Low-level execution without retry logic
- **`run()`**: Production-ready execution with retries and circuit breaker

```python
# For testing or when you don't want retries
result = await component.execute(query="test")

# For production (recommended)
result = await component.run(query="test")
```

### Custom Error Handling

```python
class MyComponent(Runnable[MyConfig, ResultType]):
    async def _execute(self, **kwargs) -> ResultType:
        try:
            result = await self.risky_operation()
            return result
        except TemporaryError as e:
            # Let retry logic handle it
            raise
        except PermanentError as e:
            # Don't retry permanent errors
            logger.error(f"Permanent error: {e}")
            raise RuntimeError(f"Cannot recover from: {e}")
```

## Circuit Breaker Pattern

The circuit breaker prevents cascading failures by stopping execution after repeated failures.

### How It Works

```
CLOSED (normal operation)
  ↓ (threshold failures)
OPEN (reject all requests)
  ↓ (timeout expires)
HALF-OPEN (try one request)
  ↓ (success)
CLOSED
```

### Configuration

```python
config = MyConfig(
    enable_circuit_breaker=True,
    circuit_breaker_threshold=5,    # Open after 5 failures
    circuit_breaker_timeout=60.0    # Try again after 60 seconds
)

component = MyComponent(config)
await component.setup()

# After 5 failures, circuit opens
for i in range(10):
    try:
        result = await component.run()
    except RuntimeError as e:
        if "Circuit breaker is open" in str(e):
            print("Circuit breaker protecting system")
            await asyncio.sleep(60)  # Wait for timeout
```

### Use Cases

- **API Rate Limiting**: Stop calling an API that's returning errors
- **Database Failures**: Prevent overwhelming a struggling database
- **Downstream Service Issues**: Fail fast when a dependency is down

## Timeout Support

### Execution Timeout

```python
config = MyConfig(
    timeout=30.0  # Timeout after 30 seconds
)

component = MyComponent(config)
await component.setup()

try:
    result = await component.run(query="long-running")
except asyncio.TimeoutError:
    print("Execution timed out")
```

### No Timeout

```python
config = MyConfig(
    timeout=None  # No timeout (default)
)
```

## Metrics & Monitoring

### Built-in Metrics

Every execution collects metrics automatically:

```python
component = MyComponent(config)
await component.setup()
result = await component.run(query="test")

# Access metrics
metrics = component.metrics
print(f"Duration: {metrics.duration_seconds}s")
print(f"Retries: {metrics.retry_count}")
print(f"Success: {metrics.success}")
print(f"Error: {metrics.error}")

# Export as dictionary
metrics_dict = component.get_metrics_dict()
# {
#     "start_time": "2025-11-15T10:30:00",
#     "end_time": "2025-11-15T10:30:05",
#     "duration_seconds": 5.2,
#     "retry_count": 1,
#     "success": True,
#     "error": None,
#     "state": "completed"
# }
```

### Reset Metrics

```python
# Reset metrics between runs
component.reset_metrics()
```

### Integration with Monitoring Systems

```python
class MonitoredComponent(Runnable[MyConfig, ResultType]):
    async def _execute(self, **kwargs) -> ResultType:
        result = await self.do_work()

        # Send metrics to monitoring system
        metrics = self.get_metrics_dict()
        await monitoring_system.send(metrics)

        return result
```

## Advanced Usage

### Async Context Manager

The recommended way to use Runnable components:

```python
async with MyComponent(config) as component:
    result1 = await component.run(query="first")
    result2 = await component.run(query="second")
    # Automatic teardown on exit
```

### Multiple Executions

```python
component = MyComponent(config)
await component.setup()

# Execute multiple times
for query in queries:
    component.reset_metrics()  # Reset metrics for each run
    result = await component.run(query=query)
    print(f"Query: {query}, Duration: {component.metrics.duration_seconds}s")

await component.teardown()
```

### Composition

```python
class PipelineComponent(Runnable[PipelineConfig, ResultType]):
    async def _setup(self) -> None:
        # Setup sub-components
        self.extractor = ExtractorComponent(self.config.extractor_config)
        self.processor = ProcessorComponent(self.config.processor_config)

        await self.extractor.setup()
        await self.processor.setup()

    async def _execute(self, **kwargs) -> ResultType:
        # Compose components
        extracted = await self.extractor.run(**kwargs)
        processed = await self.processor.run(data=extracted)
        return processed

    async def _teardown(self) -> None:
        await self.extractor.teardown()
        await self.processor.teardown()
```

## Best Practices

### 1. Use Context Managers

Always prefer async context managers for automatic cleanup:

```python
# ✅ Good
async with MyComponent(config) as component:
    result = await component.run()

# ❌ Avoid
component = MyComponent(config)
await component.setup()
result = await component.run()
await component.teardown()  # Easy to forget!
```

### 2. Use `run()` in Production

Use `run()` instead of `execute()` to get retry and circuit breaker support:

```python
# ✅ Production
result = await component.run(query="test")

# ⚠️ Testing only
result = await component.execute(query="test")
```

### 3. Configure Retries Appropriately

```python
# For idempotent operations (safe to retry)
config = MyConfig(max_retries=5, retry_delay=1.0)

# For non-idempotent operations (be careful)
config = MyConfig(max_retries=0)  # No retries

# For critical operations
config = MyConfig(
    max_retries=10,
    retry_delay=2.0,
    enable_circuit_breaker=True
)
```

### 4. Validate Configuration Early

```python
class MyComponent(Runnable[MyConfig, ResultType]):
    def _validate_config(self) -> None:
        super()._validate_config()

        # Fail fast on invalid config
        if not self.config.required_field:
            raise ValueError("required_field must be set")
```

### 5. Handle Resources Properly

```python
class MyComponent(Runnable[MyConfig, ResultType]):
    async def _setup(self) -> None:
        # Acquire resources
        self.connection = await create_connection()

    async def _teardown(self) -> None:
        # Always cleanup, even on error
        if hasattr(self, 'connection'):
            await self.connection.close()
```

### 6. Log Appropriately

The Runnable pattern logs automatically, but you can add custom logging:

```python
import logging

logger = logging.getLogger(__name__)

class MyComponent(Runnable[MyConfig, ResultType]):
    async def _execute(self, **kwargs) -> ResultType:
        logger.info(f"Processing query: {kwargs.get('query')}")
        result = await self.process()
        logger.info(f"Processed {len(result)} items")
        return result
```

## Real-World Examples

### Example 1: API Client Component

```python
from dataclasses import dataclass
from typing import Dict, Any, List
import httpx
from aiecs.common.knowledge_graph import Runnable, RunnableConfig

@dataclass
class APIClientConfig(RunnableConfig):
    base_url: str = ""
    api_key: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

class APIClient(Runnable[APIClientConfig, Dict[str, Any]]):
    """Robust API client with retry and circuit breaker"""

    async def _setup(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=self.config.timeout
        )

    async def _execute(self, endpoint: str, **params) -> Dict[str, Any]:
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def _teardown(self) -> None:
        await self.client.aclose()

# Usage
async def main():
    config = APIClientConfig(
        base_url="https://api.example.com",
        api_key="your-key",
        max_retries=5,
        enable_circuit_breaker=True
    )

    async with APIClient(config) as client:
        data = await client.run(endpoint="/users", limit=100)
        print(f"Fetched {len(data['users'])} users")
```

### Example 2: Data Processing Pipeline

```python
from dataclasses import dataclass
from typing import List
import pandas as pd
from aiecs.common.knowledge_graph import Runnable, RunnableConfig

@dataclass
class DataProcessorConfig(RunnableConfig):
    input_path: str = ""
    output_path: str = ""
    batch_size: int = 1000
    max_retries: int = 3

class DataProcessor(Runnable[DataProcessorConfig, int]):
    """Process large datasets in batches"""

    async def _setup(self) -> None:
        # Load data
        self.df = pd.read_csv(self.config.input_path)
        self.processed_count = 0

    async def _execute(self, transform_fn=None) -> int:
        # Process in batches
        for i in range(0, len(self.df), self.config.batch_size):
            batch = self.df.iloc[i:i + self.config.batch_size]

            if transform_fn:
                batch = transform_fn(batch)

            self.processed_count += len(batch)

        return self.processed_count

    async def _teardown(self) -> None:
        # Save results
        if hasattr(self, 'df'):
            self.df.to_csv(self.config.output_path, index=False)

# Usage
async def main():
    config = DataProcessorConfig(
        input_path="data.csv",
        output_path="processed.csv",
        batch_size=5000
    )

    def clean_data(df):
        return df.dropna().drop_duplicates()

    async with DataProcessor(config) as processor:
        count = await processor.run(transform_fn=clean_data)
        print(f"Processed {count} records")
```

### Example 3: Knowledge Graph Builder Component

```python
from dataclasses import dataclass
from typing import Dict, Any
from aiecs.common.knowledge_graph import Runnable, RunnableConfig
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.application.knowledge_graph.builder import GraphBuilder

@dataclass
class KGBuilderConfig(RunnableConfig):
    enable_deduplication: bool = True
    enable_linking: bool = True
    max_retries: int = 3
    timeout: float = 300.0

class KGBuilderComponent(Runnable[KGBuilderConfig, Dict[str, Any]]):
    """Knowledge graph builder with robust error handling"""

    async def _setup(self) -> None:
        # Initialize graph store
        self.graph_store = InMemoryGraphStore()
        await self.graph_store.initialize()

        # Initialize builder
        self.builder = GraphBuilder(
            graph_store=self.graph_store,
            enable_deduplication=self.config.enable_deduplication,
            enable_linking=self.config.enable_linking
        )

    async def _execute(self, text: str, source: str = "unknown") -> Dict[str, Any]:
        # Build graph from text
        result = await self.builder.build_from_text(text, source)

        return {
            "entities_added": result.entities_added,
            "relations_added": result.relations_added,
            "success": result.success,
            "errors": result.errors
        }

    async def _teardown(self) -> None:
        # Cleanup graph store
        if hasattr(self, 'graph_store'):
            # Save state if needed
            pass

# Usage
async def main():
    config = KGBuilderConfig(
        enable_deduplication=True,
        max_retries=5,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3
    )

    texts = [
        "Alice works at Tech Corp in San Francisco.",
        "Bob is a colleague of Alice at Tech Corp.",
        "Tech Corp is a technology company."
    ]

    async with KGBuilderComponent(config) as builder:
        for i, text in enumerate(texts):
            result = await builder.run(text=text, source=f"doc_{i}")
            print(f"Added {result['entities_added']} entities, "
                  f"{result['relations_added']} relations")

            # Check metrics
            metrics = builder.get_metrics_dict()
            print(f"Duration: {metrics['duration_seconds']:.2f}s")
```

## Summary

The Runnable pattern provides:

✅ **Standardized lifecycle** - Setup, execute, teardown
✅ **Automatic retries** - Exponential backoff
✅ **Circuit breaker** - Fault tolerance
✅ **Configuration** - Type-safe and validated
✅ **Metrics** - Built-in monitoring
✅ **Clean code** - Less boilerplate

Use it to build robust, production-ready async components with minimal effort!

## See Also

- [Knowledge Graph Builder](./tools/GRAPH_BUILDER_TOOL.md)
- [Graph Search Tool](./tools/GRAPH_SEARCH_TOOL.md)
- [Performance Guide](./performance/PERFORMANCE_GUIDE.md)


