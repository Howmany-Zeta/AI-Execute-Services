# APISource Tool - 结构化文档

## 📁 目录结构

```
aiecs/tools/apisource/
├── __init__.py              # 主入口，导出所有公共API
├── tool.py                  # APISourceTool主类
├── README.md               # 本文档
│
├── providers/              # API提供者模块
│   ├── __init__.py        # Provider注册和管理
│   ├── base.py            # BaseAPIProvider基类
│   ├── fred.py            # Federal Reserve Economic Data
│   ├── worldbank.py       # World Bank API
│   ├── newsapi.py         # News API
│   └── census.py          # US Census Bureau
│
├── intelligence/           # 智能分析模块
│   ├── __init__.py
│   ├── query_analyzer.py  # 查询意图分析和参数增强
│   ├── data_fusion.py     # 跨provider数据融合
│   └── search_enhancer.py # 搜索结果排序和过滤
│
├── reliability/            # 可靠性模块
│   ├── __init__.py
│   ├── error_handler.py   # 智能错误处理和重试
│   └── fallback_strategy.py # Provider自动降级
│
├── monitoring/             # 监控模块
│   ├── __init__.py
│   └── metrics.py         # 详细性能指标
│
└── utils/                  # 工具模块
    ├── __init__.py
    └── validators.py      # 数据验证工具
```

---

## 🎯 模块职责

### 1. Providers（提供者模块）

**职责**：管理所有外部API提供者的实现

**核心组件**：
- `base.py` - 所有provider的基类，提供：
  - 统一的执行接口
  - 速率限制
  - 错误处理集成
  - 指标收集
  - 数据质量评估

- `fred.py`, `worldbank.py`, `newsapi.py`, `census.py` - 具体provider实现：
  - API特定的操作
  - 参数验证
  - 数据验证和清洗
  - 操作schema定义

**使用示例**：
```python
from aiecs.tools.apisource.providers import get_provider

# 获取provider实例
fred = get_provider('fred', {'api_key': 'YOUR_KEY'})

# 执行操作
result = fred.execute('get_series_observations', {
    'series_id': 'GDP',
    'observation_start': '2020-01-01'
})
```

### 2. Intelligence（智能模块）

**职责**：提供查询理解、数据融合和搜索增强能力

**核心组件**：
- `query_analyzer.py` - 分析查询意图：
  - 检测查询类型（时间序列、对比、搜索等）
  - 提取实体和时间范围
  - 建议合适的provider和操作
  
- `data_fusion.py` - 融合多provider数据：
  - 多种融合策略（best_quality, merge_all, consensus）
  - 重复数据检测
  - 冲突解决

- `search_enhancer.py` - 增强搜索结果：
  - 相关性评分
  - 复合排序（相关性+流行度+新鲜度）
  - 智能过滤

**使用示例**：
```python
from aiecs.tools.apisource.intelligence import QueryIntentAnalyzer

analyzer = QueryIntentAnalyzer()
intent = analyzer.analyze_intent("GDP trends over last 5 years")
# 返回: {intent_type: 'time_series', entities: [...], suggested_providers: ['fred']}
```

### 3. Reliability（可靠性模块）

**职责**：确保系统稳定运行，处理错误和故障

**核心组件**：
- `error_handler.py` - 智能错误处理：
  - 自动重试（指数退避）
  - 错误分类（可重试vs不可重试）
  - 生成恢复建议

- `fallback_strategy.py` - Provider降级：
  - Provider间fallback链
  - 操作映射
  - 参数转换

**使用示例**：
```python
from aiecs.tools.apisource.reliability import SmartErrorHandler

handler = SmartErrorHandler(max_retries=3)
result = handler.execute_with_retry(
    operation_func=lambda: fetch_data(),
    operation_name='get_data'
)
# 自动重试失败的操作，并提供恢复建议
```

### 4. Monitoring（监控模块）

**职责**：收集和报告系统性能指标

**核心组件**：
- `metrics.py` - 详细指标：
  - 响应时间百分位（p50, p95, p99）
  - 成功率和错误率
  - 数据量统计
  - 健康评分（0-1）

**使用示例**：
```python
from aiecs.tools.apisource.monitoring import DetailedMetrics

metrics = DetailedMetrics()
metrics.record_request(
    success=True,
    response_time_ms=245,
    record_count=100
)

health_score = metrics.get_health_score()  # 0.85
```

### 5. Utils（工具模块）

**职责**：提供共享的验证和工具函数

**核心组件**：
- `validators.py` - 数据验证：
  - 异常值检测（IQR方法）
  - 时间序列gap检测
  - 数据完整性检查
  - 值范围计算

**使用示例**：
```python
from aiecs.tools.apisource.utils import DataValidator

validator = DataValidator()
outliers = validator.detect_outliers(values, method='iqr')
gaps = validator.detect_time_gaps(time_series_data)
```

---

## 🚀 使用示例

### 基础使用

```python
from aiecs.tools.apisource import APISourceTool

# 初始化工具
tool = APISourceTool({
    'fred_api_key': 'YOUR_API_KEY',
    'enable_fallback': True,
    'enable_query_enhancement': True,
    'enable_data_fusion': True
})

# 1. 简单查询
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'}
)

# 2. 带自然语言的智能查询
result = tool.query(
    provider='fred',
    operation='get_series_observations',
    params={'series_id': 'GDP'},
    query_text="Get GDP data for the last 5 years"
    # 自动添加observation_start和observation_end参数
)

# 3. 多provider搜索（带融合）
search_results = tool.search(
    query="unemployment trends",
    enable_fusion=True,
    fusion_strategy='best_quality',
    search_options={
        'relevance_threshold': 0.3,
        'sort_by': 'composite',
        'max_results': 10
    }
)

# 4. 获取监控指标
metrics = tool.get_metrics_report()
print(f"Overall Health: {metrics['overall_status']}")
for provider, stats in metrics['providers'].items():
    print(f"{provider}: {stats['health']['score']:.2f}")
```

### 高级使用

```python
# 直接使用intelligence组件
from aiecs.tools.apisource.intelligence import (
    QueryIntentAnalyzer,
    DataFusionEngine
)

# 分析查询意图
analyzer = QueryIntentAnalyzer()
intent = analyzer.analyze_intent("Compare GDP between US and China")
print(intent['intent_type'])  # 'comparison'
print(intent['suggested_providers'])  # ['fred', 'worldbank']

# 融合多个数据源
fusion = DataFusionEngine()
fused_result = fusion.fuse_multi_provider_results(
    results=[fred_result, worldbank_result],
    fusion_strategy='best_quality'
)

# 直接使用provider
from aiecs.tools.apisource.providers import get_provider

fred = get_provider('fred', {'api_key': 'YOUR_KEY'})
result = fred.execute('search_series', {'search_text': 'gdp'})

# 查看provider健康状态
metadata = fred.get_metadata()
print(metadata['health'])  # {'score': 0.95, 'status': 'healthy'}
```

---

## 📊 数据流

### 查询流程

```
用户请求
    ↓
APISourceTool.query()
    ↓
1. QueryEnhancer（参数增强）
    ↓
2. FallbackStrategy（选择provider）
    ↓
3. Provider.execute()
    ↓
4. SmartErrorHandler（错误处理+重试）
    ↓
5. 数据验证和清洗
    ↓
6. 质量元数据计算
    ↓
7. DetailedMetrics（记录指标）
    ↓
返回结果（含丰富的元数据）
```

### 搜索流程

```
搜索请求
    ↓
1. QueryIntentAnalyzer（意图分析）
    ↓
2. 多Provider并行查询
    ↓
3. DataFusionEngine（数据融合）
    ↓
4. SearchEnhancer（排序和过滤）
    ↓
返回增强的搜索结果
```

---

## 🔧 配置选项

```python
config = {
    # API Keys
    'fred_api_key': str,
    'newsapi_api_key': str,
    'census_api_key': str,
    
    # 功能开关
    'enable_fallback': bool,          # 启用自动fallback
    'enable_data_fusion': bool,       # 启用数据融合
    'enable_query_enhancement': bool, # 启用查询增强
    
    # 性能配置
    'default_timeout': int,           # 默认超时（秒）
    'max_retries': int,               # 最大重试次数
    'cache_ttl': int,                 # 缓存TTL（秒）
}
```

---

## 🎯 设计原则

1. **模块化**：每个模块职责单一，高内聚低耦合
2. **可扩展**：添加新provider或功能无需修改现有代码
3. **可测试**：每个模块都可以独立测试
4. **向后兼容**：保持与原API的兼容性
5. **错误友好**：提供详细的错误信息和恢复建议

---

## 📈 性能特性

- ✅ **响应时间跟踪**：p50, p95, p99百分位
- ✅ **自动重试**：指数退避，智能错误分类
- ✅ **健康监控**：实时健康评分（0-1）
- ✅ **数据质量**：完整性、新鲜度、可信度评估
- ✅ **智能缓存**：基于数据类型和质量的TTL策略

---

## 🔄 迁移指南

### 从旧版本迁移

**旧代码**：
```python
from aiecs.tools.task_tools.apisource_tool import APISourceTool
from aiecs.tools.api_sources import get_provider
```

**新代码**：
```python
from aiecs.tools.apisource import APISourceTool, get_provider
```

所有API保持兼容，只需更新import路径！

---

## 📝 贡献指南

### 添加新Provider

1. 在`providers/`目录创建新文件（如`new_provider.py`）
2. 继承`BaseAPIProvider`
3. 实现必需方法：`name`, `description`, `supported_operations`, `validate_params`, `fetch`
4. 可选实现：`get_operation_schema`, `validate_and_clean_data`, `calculate_data_quality`
5. 在`providers/__init__.py`中注册

### 添加新功能模块

1. 在相应目录（intelligence/reliability/monitoring/utils）创建文件
2. 在该目录的`__init__.py`中导出
3. 在主`__init__.py`中添加到`__all__`

---

## 📚 相关文档

- [优化分析报告](../../../docs/APISOURCE_OPTIMIZATION_ANALYSIS.md)
- [实现完成文档](../../../docs/APISOURCE_UPGRADE_COMPLETE.md)
- [Tool Executor TTL策略](../../../docs/TOOLS/TOOL_EXECUTOR_TTL_STRATEGIES.md)

---

**版本**: 2.0.0  
**状态**: ✅ 生产就绪  
**最后更新**: 2025-10-17

