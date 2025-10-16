# Tool Executor TTL Strategies Guide

## 概述

`tool_executor` 现在支持**灵活的 TTL（Time-To-Live）策略**，允许工具根据执行结果的上下文动态计算缓存过期时间。这使得缓存系统能够智能地适应不同类型的数据和查询场景。

---

## 核心特性

### 1. 多种 TTL 策略类型

| 策略类型 | 描述 | 使用场景 |
|---------|------|---------|
| **None** | 使用默认 TTL | 简单场景，不需要特殊处理 |
| **int** | 固定 TTL（秒） | 所有结果使用相同的缓存时间 |
| **Callable** | 动态 TTL 计算函数 | 根据结果内容、查询参数等计算 TTL |

### 2. 装饰器支持

```python
from aiecs.tools.tool_executor import cache_result_with_strategy

# 方式1：固定 TTL
@cache_result_with_strategy(ttl_strategy=3600)
def simple_operation(self, data):
    return process(data)

# 方式2：动态 TTL
def calculate_ttl(result, args, kwargs):
    if result.get('type') == 'permanent':
        return 86400 * 30  # 30 days
    return 3600  # 1 hour

@cache_result_with_strategy(ttl_strategy=calculate_ttl)
def smart_operation(self, query):
    return search(query)

# 方式3：使用默认 TTL
@cache_result_with_strategy()
def default_operation(self, data):
    return process(data)
```

---

## TTL 策略函数签名

### 标准签名

```python
def ttl_strategy_function(
    result: Any,        # 函数执行结果
    args: tuple,        # 位置参数
    kwargs: dict        # 关键字参数
) -> int:               # 返回 TTL（秒）
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

### 参数说明

- **result**: 被装饰函数的返回值
  - 可以是任何类型：dict, list, object, etc.
  - 通常包含元数据用于 TTL 计算
  
- **args**: 位置参数元组
  - 例如：`(arg1, arg2, arg3)`
  - 可用于基于输入参数计算 TTL
  
- **kwargs**: 关键字参数字典
  - 例如：`{'query': 'AI', 'num_results': 10}`
  - 包含所有传递给函数的命名参数

---

## 实战示例

### 示例1：SearchTool 的智能 TTL

```python
from aiecs.tools.tool_executor import cache_result_with_strategy
from aiecs.tools.base_tool import BaseTool

class SearchTool(BaseTool):
    
    def _create_search_ttl_strategy(self):
        """创建搜索专用的 TTL 策略"""
        def calculate_search_ttl(result, args, kwargs):
            # 从结果中提取元数据
            metadata = result.get('_metadata', {})
            intent_type = metadata.get('intent_type', 'GENERAL')
            results_list = result.get('results', [])
            
            # 基于意图类型的基础 TTL
            ttl_map = {
                'DEFINITION': 86400 * 30,  # 定义类查询：30天
                'FACTUAL': 86400 * 7,      # 事实类查询：7天
                'GENERAL': 86400,          # 一般查询：1天
                'RECENT_NEWS': 3600,       # 新闻查询：1小时
                'REAL_TIME': 300           # 实时查询：5分钟
            }
            base_ttl = ttl_map.get(intent_type, 3600)
            
            # 根据结果质量调整
            if results_list:
                avg_quality = sum(
                    r.get('_quality', {}).get('quality_score', 0.5)
                    for r in results_list
                ) / len(results_list)
                
                if avg_quality > 0.8:
                    base_ttl = int(base_ttl * 1.5)  # 高质量结果缓存更久
                elif avg_quality < 0.3:
                    base_ttl = base_ttl // 2  # 低质量结果缓存更短
            
            # 根据结果新鲜度调整
            if results_list:
                avg_freshness = sum(
                    r.get('_quality', {}).get('freshness_score', 0.5)
                    for r in results_list
                ) / len(results_list)
                
                if avg_freshness > 0.9:
                    base_ttl = int(base_ttl * 2)  # 非常新鲜的结果可以缓存更久
                elif avg_freshness < 0.3:
                    base_ttl = base_ttl // 2  # 陈旧的结果缓存更短
            
            return base_ttl
        
        return calculate_search_ttl
    
    @cache_result_with_strategy(
        ttl_strategy=lambda self, result, args, kwargs: 
            self._create_search_ttl_strategy()(result, args, kwargs)
    )
    def search_web(self, query: str, **kwargs) -> dict:
        """执行搜索并返回带元数据的结果"""
        # 执行搜索
        results = self._execute_search(query, **kwargs)
        
        # 分析查询意图
        intent_analysis = self.intent_analyzer.analyze(query)
        
        # 返回结果 + 元数据（用于 TTL 计算）
        return {
            'results': results,
            '_metadata': {
                'intent_type': intent_analysis['intent_type'],
                'query': query,
                'timestamp': time.time()
            }
        }
```

### 示例2：基于数据类型的 TTL

```python
def data_type_ttl_strategy(result, args, kwargs):
    """根据数据类型计算 TTL"""
    data_type = result.get('type', 'unknown')
    
    ttl_map = {
        'static': 86400 * 365,  # 静态数据：1年
        'config': 86400 * 7,    # 配置数据：7天
        'user_data': 3600,      # 用户数据：1小时
        'real_time': 60         # 实时数据：1分钟
    }
    
    return ttl_map.get(data_type, 3600)

@cache_result_with_strategy(ttl_strategy=data_type_ttl_strategy)
def fetch_data(self, data_id: str):
    data = self.database.get(data_id)
    return {
        'data': data,
        'type': data.type  # 用于 TTL 计算
    }
```

### 示例3：基于查询参数的 TTL

```python
def query_param_ttl_strategy(result, args, kwargs):
    """根据查询参数计算 TTL"""
    # 从 kwargs 中提取参数
    include_history = kwargs.get('include_history', False)
    user_id = kwargs.get('user_id', 'anonymous')
    
    # 历史数据可以缓存更久
    if include_history:
        return 86400 * 7  # 7天
    
    # 匿名用户的查询可以缓存更久
    if user_id == 'anonymous':
        return 3600  # 1小时
    
    # 个性化查询缓存时间较短
    return 300  # 5分钟

@cache_result_with_strategy(ttl_strategy=query_param_ttl_strategy)
def get_recommendations(self, user_id: str, include_history: bool = False):
    return self.recommendation_engine.get(user_id, include_history)
```

---

## 与双层缓存集成

### 配置双层缓存

```python
from aiecs.tools.tool_executor import ToolExecutor, ExecutorConfig

# 配置双层缓存
config = ExecutorConfig(
    enable_cache=True,
    enable_dual_cache=True,      # 启用双层缓存
    enable_redis_cache=True,     # 启用 Redis 作为 L2
    cache_size=1000,             # L1 缓存大小
    cache_ttl=3600               # 默认 TTL
)

executor = ToolExecutor(config)
```

### 缓存流程

```
查询请求
    ↓
检查 L1 (LRU 内存缓存)
    ↓ (未命中)
检查 L2 (Redis 持久化缓存)
    ↓ (未命中)
执行函数
    ↓
计算智能 TTL (基于结果和上下文)
    ↓
写入 L2 (使用智能 TTL)
    ↓
写入 L1 (使用固定短 TTL，如 5 分钟)
    ↓
返回结果
```

### L1 和 L2 的 TTL 策略

- **L1 (LRU)**: 固定短 TTL（如 5 分钟）
  - 目的：快速响应最近的查询
  - 自动淘汰：LRU 策略
  
- **L2 (Redis)**: 智能 TTL（基于策略函数）
  - 目的：长期缓存稳定内容
  - 自动过期：基于计算的 TTL

---

## 最佳实践

### 1. 返回值设计

**推荐**：返回包含元数据的字典

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

**不推荐**：直接返回数据（难以计算 TTL）

```python
@cache_result_with_strategy(ttl_strategy=my_strategy)
def my_operation(self, query):
    return perform_operation(query)  # 缺少元数据
```

### 2. TTL 策略函数设计

**推荐**：健壮的错误处理

```python
def robust_ttl_strategy(result, args, kwargs):
    try:
        # 尝试提取元数据
        metadata = result.get('_metadata', {})
        data_type = metadata.get('type', 'unknown')
        
        # 计算 TTL
        ttl = calculate_ttl_from_type(data_type)
        
        # 验证 TTL
        if ttl < 0:
            return 3600  # 默认值
        
        return ttl
        
    except Exception as e:
        logger.warning(f"TTL calculation failed: {e}")
        return 3600  # 默认值
```

### 3. 缓存键生成

**自动生成**：tool_executor 会自动生成缓存键

```python
# 缓存键包含：
# - 函数名
# - user_id (从 kwargs)
# - task_id (从 kwargs)
# - 所有参数的哈希值

# 相同的查询 → 相同的缓存键
search_tool.search_web(query="AI", num_results=10)
search_tool.search_web(query="AI", num_results=10)  # 命中缓存

# 不同的查询 → 不同的缓存键
search_tool.search_web(query="AI", num_results=5)   # 不命中缓存
```

---

## 监控和调试

### 获取缓存统计

```python
# 获取 executor 统计
stats = tool._executor.get_stats()
print(f"Cache Hit Rate: {stats['hit_rate']:.1%}")
print(f"Total Requests: {stats['total_requests']}")
print(f"Cache Hits: {stats['cache_hits']}")

# 获取 cache provider 统计
cache_stats = tool._executor.cache_provider.get_stats()
print(f"Cache Size: {cache_stats.get('size', 0)}")
```

### 日志记录

```python
import logging

# 启用 tool_executor 日志
logging.getLogger('aiecs.tools.tool_executor').setLevel(logging.DEBUG)

# 查看缓存命中/未命中
# DEBUG: Cache hit for search_web
# DEBUG: Cache miss for search_web, executing function
```

---

## 总结

### 优势

✅ **灵活性**：支持固定、动态、默认三种 TTL 策略  
✅ **上下文感知**：基于结果内容和查询参数计算 TTL  
✅ **易于扩展**：简单的函数签名，易于实现自定义策略  
✅ **统一架构**：所有工具使用相同的缓存基础设施  
✅ **双层缓存**：L1 快速响应 + L2 长期存储  

### 适用场景

- 搜索工具：基于查询意图和结果质量
- 数据获取：基于数据类型和新鲜度
- API 调用：基于响应状态和配额
- 计算密集型操作：基于计算复杂度和结果稳定性

### 下一步

1. 查看 `examples/search_tool_intelligent_caching_demo.py` 了解完整示例
2. 阅读 `docs/TOOLS/TOOLS_TOOL_EXECUTOR.md` 了解 tool_executor 的其他功能
3. 实现自己的 TTL 策略函数

