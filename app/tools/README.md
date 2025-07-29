# Tools Architecture

本目录包含为应用程序提供各种功能的工具。工具架构已经重构，将业务逻辑与性能优化关注点分离，并采用分层架构组织不同类型的工具。

## 目录结构

```
app/tools/
├── __init__.py              # 工具注册表和发现机制
├── base_tool.py            # 基础工具类
├── temp_file_manager.py    # 临时文件管理工具
├── README.md               # 本文档
├── task_tools/             # 任务导向工具
│   ├── __init__.py
│   ├── chart_tool.py       # 图表和可视化工具
│   ├── classfire_tool.py   # 分类和归类工具
│   ├── image_tool.py       # 图像处理工具
│   ├── office_tool.py      # Office文档处理工具
│   ├── pandas_tool.py      # 数据分析和处理工具
│   ├── report_tool.py      # 报告生成工具
│   ├── research_tool.py    # 研究和信息收集工具
│   ├── scraper_tool.py     # 网页抓取工具
│   ├── search_api.py       # 搜索API集成工具
│   └── stats_tool.py       # 统计分析工具
├── general_tools/          # 通用工具 (预留)
├── rag_tools/             # RAG相关工具 (预留)
└── out_source/            # 外部集成工具 (预留)
```

## 新架构

新架构包含以下组件：

1. **工具执行器** (`app/core/tool_executor.py`): 一个集中式执行框架，处理以下横切关注点：
   - 输入验证
   - 缓存
   - 并发
   - 错误处理
   - 性能优化
   - 日志记录

2. **基础工具类** (`app/tools/base_tool.py`): 所有工具都应继承的基类，提供：
   - 与工具执行器的集成
   - 基于模式的输入验证
   - 标准化错误处理
   - 自动模式发现

3. **工具注册表** (`app/tools/__init__.py`): 处理工具的注册和检索：
   - 工具注册
   - 工具检索
   - 自动工具发现
   - 分层模块导入

4. **分层工具组织**:
   - **task_tools**: 专门的任务导向工具，用于特定的业务场景
   - **general_tools**: 通用工具，提供基础功能
   - **rag_tools**: RAG (检索增强生成) 相关工具
   - **out_source**: 外部服务集成工具

## 工具分类

### Task Tools (任务工具)
位于 `task_tools/` 目录，包含专门用于特定任务的工具：

- **chart_tool**: 图表生成和数据可视化
- **classfire_tool**: 数据分类和归类
- **image_tool**: 图像处理和操作
- **office_tool**: Office文档处理 (Word, Excel, PowerPoint)
- **pandas_tool**: 数据分析和DataFrame操作
- **report_tool**: 报告生成和格式化
- **research_tool**: 研究和信息收集
- **scraper_tool**: 网页数据抓取
- **search_api**: 搜索引擎API集成
- **stats_tool**: 统计分析和计算

## 使用基础工具类

要创建新工具，继承 `BaseTool` 类并实现您的业务逻辑方法：

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.tools import register_tool
from app.tools.base_tool import BaseTool

@register_tool("my_tool")
class MyTool(BaseTool):
    """我的工具描述"""

    # 为操作定义输入模式
    class OperationSchema(BaseModel):
        """操作的模式"""
        param1: str = Field(description="参数1")
        param2: int = Field(description="参数2")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化工具"""
        super().__init__(config)
        # 额外的初始化

    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        在这里实现您的业务逻辑

        Args:
            param1: 参数1
            param2: 参数2

        Returns:
            操作结果
        """
        # 您的业务逻辑
        return {"result": f"处理 {param1} 和 {param2}"}
```

## 使用装饰器进行性能优化

工具执行器提供了几个装饰器，您可以用它们为方法添加性能优化：

```python
from app.tools.tool_executor import cache_result, run_in_executor, measure_execution_time

@cache_result()  # 缓存此方法的结果
def cached_operation(self, param1: str) -> Dict[str, Any]:
    # 此结果将基于param1进行缓存
    return {"result": f"缓存的结果 {param1}"}

@run_in_executor  # 在线程池中运行此方法
def cpu_intensive_operation(self, param1: str) -> Dict[str, Any]:
    # 此方法将在单独的线程中执行
    return {"result": f"CPU密集型结果 {param1}"}

@measure_execution_time  # 记录此方法的执行时间
def monitored_operation(self, param1: str) -> Dict[str, Any]:
    # 此方法的执行时间将被记录
    return {"result": f"监控的结果 {param1}"}
```

## 迁移现有工具

要将现有工具迁移到新架构：

1. 使您的工具类继承 `BaseTool`
2. 为您的操作定义 Pydantic 模式
3. 删除任何自定义缓存、验证或错误处理代码
4. 使用装饰器进行性能优化
5. 更新 `run` 方法以使用基类实现

### 之前：

```python
@register_tool("example")
class ExampleTool:
    def __init__(self):
        self._cache = {}

    def run(self, op: str, **kwargs):
        if op == "operation":
            return self.operation(**kwargs)
        else:
            raise ValueError(f"不支持的操作: {op}")

    def operation(self, param1: str, param2: int):
        # 自定义缓存
        cache_key = f"{param1}_{param2}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 自定义验证
        if not isinstance(param1, str):
            raise ValueError("param1必须是字符串")
        if not isinstance(param2, int):
            raise ValueError("param2必须是整数")

        # 业务逻辑
        result = {"result": f"处理 {param1} 和 {param2}"}

        # 缓存结果
        self._cache[cache_key] = result

        return result
```

### 之后：

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.tools import register_tool
from app.tools.base_tool import BaseTool
from app.tools.tool_executor import cache_result

@register_tool("example")
class ExampleTool(BaseTool):
    """示例工具"""

    class OperationSchema(BaseModel):
        """操作的模式"""
        param1: str = Field(description="参数1")
        param2: int = Field(description="参数2")

    @cache_result()
    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        处理参数

        Args:
            param1: 参数1
            param2: 参数2

        Returns:
            操作结果
        """
        # 只关注业务逻辑
        return {"result": f"处理 {param1} 和 {param2}"}
```

## 新架构的好处

新架构提供了几个好处：

1. **关注点分离**：业务逻辑与缓存、验证和错误处理等横切关注点分离。

2. **减少重复**：常见功能在工具执行器和基础工具中实现一次，而不是在各个工具中重复。

3. **行为一致**：所有工具在验证、错误处理和性能优化方面表现一致。

4. **提高可维护性**：工具更容易维护，因为它们只关注特定的业务逻辑。

5. **增强性能**：工具执行器提供缓存、并发和其他性能特性的优化实现。

6. **更好的测试**：业务逻辑可以独立于横切关注点进行测试。

7. **更容易上手**：新开发人员可以专注于实现业务逻辑，而不必担心性能优化的细节。

## 使用示例

```python
# 获取工具实例
from app.tools import get_tool

# 获取图表工具
chart_tool = get_tool("chart")

# 使用工具
result = chart_tool.run("visualize",
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="年龄分布"
)

# 或直接调用方法
result = chart_tool.visualize(
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="年龄分布"
)

```

## Multi-Task Service 集成

工具系统与 `app/services/multi_task/tools.py` 中的 MultiTaskTools 服务完全集成：

```python
from app.services.multi_task.tools import MultiTaskTools

# 初始化多任务工具服务
multi_tools = MultiTaskTools()

# 获取所有可用工具
available_tools = multi_tools.get_available_tools()
print("可用工具:", available_tools)

# 获取特定工具的操作
chart_operations = multi_tools.get_available_operations("chart")
print("图表工具操作:", chart_operations)

# 获取操作详细信息
operation_info = multi_tools.get_operation_info("chart.visualize")
print("操作信息:", operation_info)

# 执行工具操作
result = await multi_tools.execute_tool(
    "chart",
    "visualize",
    file_path="data.csv",
    plot_type="histogram",
    x="age"
)
```

## 使用任务工具示例

### 数据处理流水线

```python
from app.tools import get_tool

# 1. 数据分析工具
pandas_tool = get_tool("pandas")
df_result = pandas_tool.read_csv(file_path="data.csv")

# 2. 统计分析工具
stats_tool = get_tool("stats")
stats_result = stats_tool.descriptive_stats(data=df_result["data"])

# 3. 图表生成工具
chart_tool = get_tool("chart")
chart_result = chart_tool.visualize(
    data=df_result["data"],
    plot_type="histogram",
    x="age"
)

# 4. 报告生成工具
report_tool = get_tool("report")
report_result = report_tool.generate_report(
    data=stats_result,
    charts=[chart_result],
    template="statistical_summary"
)
```

### 研究和信息收集

```python
# 研究工具
research_tool = get_tool("research")
research_result = research_tool.search_papers(
    query="machine learning",
    max_results=10
)

# 网页抓取工具
scraper_tool = get_tool("scraper")
web_data = scraper_tool.scrape_url(
    url="https://example.com",
    selectors=["h1", "p"]
)

# 搜索API工具
search_tool = get_tool("search_api")
search_results = search_tool.web_search(
    query="artificial intelligence trends 2024",
    num_results=5
)
```

### Office文档处理

```python
# Office工具
office_tool = get_tool("office")

# 处理Excel文件
excel_result = office_tool.read_excel(
    file_path="data.xlsx",
    sheet_name="Sheet1"
)

# 生成Word报告
word_result = office_tool.create_word_document(
    content=report_result["content"],
    template="business_report"
)

# 创建PowerPoint演示
ppt_result = office_tool.create_presentation(
    slides_data=chart_result["charts"],
    template="data_analysis"
)
```

## 工具发现和注册

系统会自动发现和注册所有工具：

```python
from app.tools import list_tools, discover_tools

# 列出所有已注册的工具
all_tools = list_tools()
print("已注册工具:", all_tools)

# 手动触发工具发现 (通常不需要，系统会自动执行)
discover_tools("app.tools")

# 按类别查看工具
task_tools = [tool for tool in all_tools if "task_tools" in str(type(get_tool(tool)))]
print("任务工具:", task_tools)
```

## 最佳实践

### 1. 工具组合使用
将多个工具组合使用以完成复杂任务：

```python
def data_analysis_pipeline(csv_file: str):
    """完整的数据分析流水线"""

    # 数据加载和清理
    pandas_tool = get_tool("pandas")
    data = pandas_tool.read_csv(csv_file)
    cleaned_data = pandas_tool.clean_data(data["data"])

    # 统计分析
    stats_tool = get_tool("stats")
    statistics = stats_tool.comprehensive_analysis(cleaned_data["data"])

    # 可视化
    chart_tool = get_tool("chart")
    charts = chart_tool.create_dashboard(
        data=cleaned_data["data"],
        chart_types=["histogram", "boxplot", "correlation"]
    )

    # 生成报告
    report_tool = get_tool("report")
    final_report = report_tool.generate_comprehensive_report(
        data=statistics,
        visualizations=charts,
        template="data_analysis"
    )

    return final_report
```

### 2. 错误处理
使用适当的错误处理：

```python
from app.tools import get_tool
from app.tools.tool_executor import ToolExecutionError

try:
    tool = get_tool("pandas")
    result = tool.read_csv("nonexistent.csv")
except ToolExecutionError as e:
    print(f"工具执行错误: {e}")
except ValueError as e:
    print(f"工具不存在: {e}")
```

### 3. 异步操作
对于耗时操作使用异步执行：

```python
import asyncio
from app.services.multi_task.tools import MultiTaskTools

async def async_data_processing():
    multi_tools = MultiTaskTools()

    # 并行执行多个操作
    tasks = [
        multi_tools.execute_tool("scraper", "scrape_url", url="https://site1.com"),
        multi_tools.execute_tool("scraper", "scrape_url", url="https://site2.com"),
        multi_tools.execute_tool("research", "search_papers", query="AI")
    ]

    results = await asyncio.gather(*tasks)
    return results
```

## 扩展工具系统

### 添加新的任务工具

1. 在 `task_tools/` 目录创建新的工具文件
2. 继承 `BaseTool` 类
3. 使用 `@register_tool` 装饰器注册
4. 在 `task_tools/__init__.py` 中添加导入

```python
# task_tools/my_new_tool.py
from app.tools import register_tool
from app.tools.base_tool import BaseTool

@register_tool("my_new_tool")
class MyNewTool(BaseTool):
    """新工具描述"""

    def my_operation(self, param: str) -> dict:
        """操作描述"""
        return {"result": f"处理 {param}"}
```

### 创建新的工具类别

1. 在 `app/tools/` 下创建新目录
2. 添加 `__init__.py` 文件
3. 在主 `__init__.py` 中添加导入
4. 工具会自动被发现和注册
