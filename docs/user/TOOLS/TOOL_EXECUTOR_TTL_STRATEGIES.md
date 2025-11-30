# Tool Executor TTL Strategies Guide

## Overview

`tool_executor` now supports **flexible TTL (Time-To-Live) strategies**, allowing tools to dynamically calculate cache expiration times based on the context of execution results. This enables the caching system to intelligently adapt to different types of data and query scenarios.

---

## Core Features

### 1. Multiple TTL Strategy Types

| Strategy Type | Description | Use Cases |
|---------------|-------------|-----------|
| **None** | Use default TTL | Simple scenarios, no special handling needed |
| **int** | Fixed TTL (seconds) | All results use the same cache time |
| **Callable** | Dynamic TTL calculation function | Calculate TTL based on result content, query parameters, etc. |

### 2. Decorator Support

```python
from aiecs.tools.tool_executor import cache_result_with_strategy

# Method 1: Fixed TTL
@cache_result_with_strategy(ttl_strategy=3600)
def simple_operation(self, data):
    return process(data)

# Method 2: Dynamic TTL
def calculate_ttl(result, args, kwargs):
    if result.get('type') == 'permanent':
        return 86400 * 30  # 30 days
    return 3600  # 1 hour

@cache_result_with_strategy(ttl_strategy=calculate_ttl)
def smart_operation(self, query):
    return search(query)

# Method 3: Use default TTL
@cache_result_with_strategy()
def default_operation(self, data):
    return process(data)
```

---

## TTL Strategy Function Signature

### Standard Signature

```python
def ttl_strategy_function(
    result: Any,        # Function execution result
    args: tuple,        # Positional arguments
    kwargs: dict        # Keyword arguments
) -> int:               # Return TTL (seconds)
    """
    Calculate TTL based on result and context.
    
    Args:
        result: The return value from the decorated function
        args: Positional arguments passed to the function
        kwargs: Keyword arguments passed to the function
        
    Returns:
        int: TTL in seconds (must be positive integer)
    """
    # Your TTL calculation logic here
    return ttl_seconds
```

### Parameter Description

- **result**: Return value from the decorated function
  - Can be any type: dict, list, object, etc.
  - Usually contains metadata for TTL calculation
  
- **args**: Positional arguments tuple
  - Example: `(arg1, arg2, arg3)`
  - Can be used to calculate TTL based on input parameters
  
- **kwargs**: Keyword arguments dictionary
  - Example: `{'query': 'AI', 'num_results': 10}`
  - Contains all named parameters passed to the function

---

## Practical Examples

### Example 1: SearchTool Intelligent TTL

```python
from aiecs.tools.tool_executor import cache_result_with_strategy
from aiecs.tools.base_tool import BaseTool

class SearchTool(BaseTool):
    
    def _create_search_ttl_strategy(self):
        """Create search-specific TTL strategy"""
        def calculate_search_ttl(result, args, kwargs):
            # Extract metadata from result
            metadata = result.get('_metadata', {})
            intent_type = metadata.get('intent_type', 'GENERAL')
            results_list = result.get('results', [])
            
            # Base TTL based on intent type
            ttl_map = {
                'DEFINITION': 86400 * 30,  # Definition queries: 30 days
                'FACTUAL': 86400 * 7,      # Factual queries: 7 days
                'GENERAL': 86400,          # General queries: 1 day
                'RECENT_NEWS': 3600,       # News queries: 1 hour
                'REAL_TIME': 300           # Real-time queries: 5 minutes
            }
            base_ttl = ttl_map.get(intent_type, 3600)
            
            # Adjust based on result quality
            if results_list:
                avg_quality = sum(
                    r.get('_quality', {}).get('quality_score', 0.5)
                    for r in results_list
                ) / len(results_list)
                
                if avg_quality > 0.8:
                    base_ttl = int(base_ttl * 1.5)  # High-quality results cache longer
                elif avg_quality < 0.3:
                    base_ttl = base_ttl // 2  # Low-quality results cache shorter
            
            # Adjust based on result freshness
            if results_list:
                avg_freshness = sum(
                    r.get('_quality', {}).get('freshness_score', 0.5)
                    for r in results_list
                ) / len(results_list)
                
                if avg_freshness > 0.9:
                    base_ttl = int(base_ttl * 2)  # Very fresh results can cache longer
                elif avg_freshness < 0.3:
                    base_ttl = base_ttl // 2  # Stale results cache shorter
            
            return base_ttl
        
        return calculate_search_ttl
    
    @cache_result_with_strategy(
        ttl_strategy=lambda self, result, args, kwargs: 
            self._create_search_ttl_strategy()(result, args, kwargs)
    )
    def search_web(self, query: str, **kwargs) -> dict:
        """Execute search and return results with metadata"""
        # Execute search
        results = self._execute_search(query, **kwargs)
        
        # Analyze query intent
        intent_analysis = self.intent_analyzer.analyze(query)
        
        # Return results + metadata (for TTL calculation)
        return {
            'results': results,
            '_metadata': {
                'intent_type': intent_analysis['intent_type'],
                'query': query,
                'timestamp': time.time()
            }
        }
```

### Example 2: TTL Based on Data Type

```python
def data_type_ttl_strategy(result, args, kwargs):
    """Calculate TTL based on data type"""
    data_type = result.get('type', 'unknown')
    
    ttl_map = {
        'static': 86400 * 365,  # Static data: 1 year
        'config': 86400 * 7,    # Configuration data: 7 days
        'user_data': 3600,      # User data: 1 hour
        'real_time': 60         # Real-time data: 1 minute
    }
    
    return ttl_map.get(data_type, 3600)

@cache_result_with_strategy(ttl_strategy=data_type_ttl_strategy)
def fetch_data(self, data_id: str):
    data = self.database.get(data_id)
    return {
        'data': data,
        'type': data.type  # For TTL calculation
    }
```

### Example 3: TTL Based on Query Parameters

```python
def query_param_ttl_strategy(result, args, kwargs):
    """Calculate TTL based on query parameters"""
    # Extract parameters from kwargs
    include_history = kwargs.get('include_history', False)
    user_id = kwargs.get('user_id', 'anonymous')
    
    # Historical data can cache longer
    if include_history:
        return 86400 * 7  # 7 days
    
    # Anonymous user queries can cache longer
    if user_id == 'anonymous':
        return 3600  # 1 hour
    
    # Personalized queries cache shorter
    return 300  # 5 minutes

@cache_result_with_strategy(ttl_strategy=query_param_ttl_strategy)
def get_recommendations(self, user_id: str, include_history: bool = False):
    return self.recommendation_engine.get(user_id, include_history)
```

---

## Integration with Dual-Layer Cache

### Configure Dual-Layer Cache

```python
from aiecs.tools.tool_executor import ToolExecutor, ExecutorConfig

# Configure dual-layer cache
config = ExecutorConfig(
    enable_cache=True,
    enable_dual_cache=True,      # Enable dual-layer cache
    enable_redis_cache=True,     # Enable Redis as L2
    cache_size=1000,             # L1 cache size
    cache_ttl=3600               # Default TTL
)

executor = ToolExecutor(config)
```

### Cache Flow

```
Query Request
    ↓
Check L1 (LRU memory cache)
    ↓ (miss)
Check L2 (Redis persistent cache)
    ↓ (miss)
Execute Function
    ↓
Calculate Intelligent TTL (based on result and context)
    ↓
Write to L2 (using intelligent TTL)
    ↓
Write to L1 (using fixed short TTL, e.g., 5 minutes)
    ↓
Return Result
```

### L1 and L2 TTL Strategies

- **L1 (LRU)**: Fixed short TTL (e.g., 5 minutes)
  - Purpose: Fast response to recent queries
  - Automatic eviction: LRU strategy
  
- **L2 (Redis)**: Intelligent TTL (based on strategy function)
  - Purpose: Long-term caching of stable content
  - Automatic expiration: Based on calculated TTL

---

## Best Practices

### 1. Return Value Design

**Recommended**: Return dictionary containing metadata

```python
@cache_result_with_strategy(ttl_strategy=my_strategy)
def my_operation(self, query):
    result = perform_operation(query)
    
    return {
        'data': result,
        '_metadata': {
            'type': 'factual',
            'quality': 0.95,
            'timestamp': time.time()
        }
    }
```

**Not Recommended**: Directly return data (difficult to calculate TTL)

```python
@cache_result_with_strategy(ttl_strategy=my_strategy)
def my_operation(self, query):
    return perform_operation(query)  # Missing metadata
```

### 2. TTL Strategy Function Design

**Recommended**: Robust error handling

```python
def robust_ttl_strategy(result, args, kwargs):
    try:
        # Try to extract metadata
        metadata = result.get('_metadata', {})
        data_type = metadata.get('type', 'unknown')
        
        # Calculate TTL
        ttl = calculate_ttl_from_type(data_type)
        
        # Validate TTL
        if ttl < 0:
            return 3600  # Default value
        
        return ttl
        
    except Exception as e:
        logger.warning(f"TTL calculation failed: {e}")
        return 3600  # Default value
```

### 3. Cache Key Generation

**Automatic**: tool_executor automatically generates cache keys

```python
# Cache key includes:
# - Function name
# - user_id (from kwargs)
# - task_id (from kwargs)
# - Hash value of all parameters

# Same query → Same cache key
search_tool.search_web(query="AI", num_results=10)
search_tool.search_web(query="AI", num_results=10)  # Cache hit

# Different query → Different cache key
search_tool.search_web(query="AI", num_results=5)   # Cache miss
```

---

## Monitoring and Debugging

### Get Cache Statistics

```python
# Get executor statistics
stats = tool._executor.get_stats()
print(f"Cache Hit Rate: {stats['hit_rate']:.1%}")
print(f"Total Requests: {stats['total_requests']}")
print(f"Cache Hits: {stats['cache_hits']}")

# Get cache provider statistics
cache_stats = tool._executor.cache_provider.get_stats()
print(f"Cache Size: {cache_stats.get('size', 0)}")
```

### Logging

```python
import logging

# Enable tool_executor logging
logging.getLogger('aiecs.tools.tool_executor').setLevel(logging.DEBUG)

# View cache hits/misses
# DEBUG: Cache hit for search_web
# DEBUG: Cache miss for search_web, executing function
```

---

## Summary

### Advantages

✅ **Flexibility**: Supports fixed, dynamic, and default TTL strategies  
✅ **Context-Aware**: Calculate TTL based on result content and query parameters  
✅ **Easy to Extend**: Simple function signature, easy to implement custom strategies  
✅ **Unified Architecture**: All tools use the same caching infrastructure  
✅ **Dual-Layer Cache**: L1 fast response + L2 long-term storage  

### Applicable Scenarios

- Search tools: Based on query intent and result quality
- Data retrieval: Based on data type and freshness
- API calls: Based on response status and quotas
- Compute-intensive operations: Based on computation complexity and result stability

### Next Steps

1. Check `examples/search_tool_intelligent_caching_demo.py` for complete examples
2. Read `docs/TOOLS/TOOLS_TOOL_EXECUTOR.md` to learn about other tool_executor features
3. Implement your own TTL strategy function
