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

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

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

## Schema 开发要求

**重要：** 所有工具方法必须具有 Schema 定义，以确保 Tool Calling Agent 的正常工作。

### Schema 开发选项

1. **自动生成（推荐）**：如果方法有完整的类型注解和文档字符串，Schema 会自动生成
   - 要求：完整的类型注解 + Google/NumPy 风格的文档字符串
   - 优点：零维护成本，自动同步

2. **手动定义**：对于需要复杂验证的情况，需要手动定义 Schema
   - 使用场景：复杂验证规则、字段约束、自定义验证器
   - 命名规范：`{MethodName}Schema`（例如：`OperationSchema`）

### Schema 开发检查清单

创建新工具时，请确保：

- [ ] 所有方法都有完整的类型注解
- [ ] 所有方法都有文档字符串（Google 或 NumPy 风格）
- [ ] Schema 覆盖率 ≥ 90%
- [ ] 运行 `aiecs tools validate-schemas tool_name` 验证质量
- [ ] 运行 `aiecs tools schema-coverage tool_name` 检查覆盖率

**详细指南：** 请参阅 [Schema 开发指南](../../TOOLS/TOOL_SCHEMA_GUIDELINES.md) 和 [工具创建工作流](../../TOOLS/TOOL_CREATION_WORKFLOW.md)

## 使用装饰器进行性能优化

工具执行器提供了几个装饰器，您可以用它们为方法添加性能优化：

```python
from aiecs.tools.tool_executor import cache_result, run_in_executor, measure_execution_time

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

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import cache_result

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
from aiecs.tools import get_tool

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
from aiecs.services.multi_task.tools import MultiTaskTools

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
from aiecs.tools import get_tool

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
from aiecs.tools import list_tools, discover_tools

# 列出所有已注册的工具
all_tools = list_tools()
print("已注册工具:", all_tools)

# 手动触发工具发现 (通常不需要，系统会自动执行)
discover_tools("aiecs.tools")

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
from aiecs.tools import get_tool
from aiecs.tools.tool_executor import ToolExecutionError

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
from aiecs.services.multi_task.tools import MultiTaskTools

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
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

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


## 工具使用特别说明

### Image Tool (图像处理工具)

Image Tool 提供了全面的图像处理功能，包括加载、OCR文字识别、元数据提取、尺寸调整和滤镜应用。

#### 系统依赖要求

**重要**: Image Tool 需要安装系统级的 Tesseract OCR 引擎和 Pillow 图像处理库的系统依赖。

#### 1. Tesseract OCR 引擎

**Ubuntu/Debian 系统**:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS 系统**:
```bash
brew install tesseract
```

**验证安装**:
```bash
tesseract --version
```

#### 2. Pillow 图像处理库系统依赖

**Ubuntu/Debian 系统**:
```bash
# 基础图像处理库
sudo apt-get install libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev

# 完整图像处理库（推荐）
sudo apt-get install libimageio-dev libfreetype6-dev liblcms2-dev libtiff5-dev libjpeg8-dev libopenjp2-7-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1-dev
```

**macOS 系统**:
```bash
brew install libjpeg zlib libpng libtiff webp openjpeg freetype lcms2
```

**验证安装**:
```bash
python -c "from PIL import Image; print('PIL version:', Image.__version__)"
```

#### 3. 多语言 OCR 支持

**安装额外语言包**:
```bash
# Ubuntu/Debian 系统
sudo apt-get install tesseract-ocr-chi-sim    # 简体中文
sudo apt-get install tesseract-ocr-chi-tra    # 繁体中文
sudo apt-get install tesseract-ocr-fra        # 法语
sudo apt-get install tesseract-ocr-deu        # 德语
sudo apt-get install tesseract-ocr-jpn        # 日语
sudo apt-get install tesseract-ocr-kor        # 韩语
sudo apt-get install tesseract-ocr-rus        # 俄语
sudo apt-get install tesseract-ocr-spa        # 西班牙语
```

**查看已安装的语言包**:
```bash
tesseract --list-langs
```

**使用多语言 OCR**:
```python
# 英文 OCR
text = tool.ocr("/path/to/image.jpg", lang='eng')

# 中文 OCR
text = tool.ocr("/path/to/image.jpg", lang='chi_sim')

# 日文 OCR
text = tool.ocr("/path/to/image.jpg", lang='jpn')
```

#### 功能特性

1. **图像加载**: 支持多种格式 (JPG, PNG, BMP, TIFF, GIF)
2. **OCR 文字识别**: 基于 Tesseract 引擎的文字提取
3. **元数据提取**: 获取图像尺寸、模式和 EXIF 信息
4. **图像调整**: 高质量的尺寸调整
5. **滤镜效果**: 模糊、锐化、边缘增强等效果

#### 使用示例

```python
from aiecs.tools.task_tools.image_tool import ImageTool

# 初始化工具
tool = ImageTool()

# 加载图像信息
result = tool.load("/path/to/image.jpg")
print(f"尺寸: {result['size']}, 模式: {result['mode']}")

# OCR 文字识别
text = tool.ocr("/path/to/image.png", lang='eng')
print(f"识别文字: {text}")

# 提取元数据
metadata = tool.metadata("/path/to/image.jpg", include_exif=True)
print(f"EXIF 信息: {metadata.get('exif', {})}")

# 调整图像尺寸
tool.resize("/path/to/input.jpg", "/path/to/output.jpg", 800, 600)

# 应用滤镜
tool.filter("/path/to/input.jpg", "/path/to/blurred.jpg", "blur")
```

#### 安全特性

- 文件扩展名白名单验证
- 文件大小限制（默认 50MB）
- 路径规范化和安全检查
- 完整的错误处理和日志记录

### ClassFire Tool (文本分类和关键词提取工具)

ClassFire Tool 提供了强大的文本分类、关键词提取和文本摘要功能，支持中英文文本处理。

#### 模型依赖要求

**重要**: ClassFire Tool 需要下载和安装以下模型才能正常工作。

#### 1. spaCy 模型依赖

**使用的模型**:
- **英文模型**: `en_core_web_sm` - 用于英文文本的词性标注、命名实体识别和关键词提取
- **中文模型**: `zh_core_web_sm` - 用于中文文本的词性标注、命名实体识别和关键词提取

**安装方法**:
```bash
# 使用 Poetry 环境安装
poetry run python -m spacy download en_core_web_sm
poetry run python -m spacy download zh_core_web_sm

# 或者使用 pip 安装
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
pip install https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.0/zh_core_web_sm-3.7.0-py3-none-any.whl
```

**使用原因**:
- **词性标注**: 识别名词、动词、形容词等词性，用于关键词提取
- **命名实体识别**: 识别人名、地名、机构名等实体，提高关键词质量
- **语言检测**: 自动检测文本语言，选择合适的处理策略
- **文本预处理**: 提供标准化的文本处理管道

#### 2. Transformers 模型依赖

**使用的模型**:
- **英文摘要模型**: `facebook/bart-large-cnn` - 用于英文文本的摘要生成
- **多语言摘要模型**: `t5-base` - 用于中文文本的摘要生成

**模型下载**:
```bash
# 模型会在首次使用时自动下载到 ~/.cache/huggingface/hub/
# 无需手动安装，但需要确保网络连接正常
```

**安装验证**:
```python
from transformers import pipeline

# 测试英文摘要模型
summarizer_en = pipeline("summarization", model="facebook/bart-large-cnn")
result = summarizer_en("Your text here...", max_length=100, min_length=30)

# 测试多语言摘要模型
summarizer_zh = pipeline("summarization", model="t5-base")
result = summarizer_zh("您的中文文本...", max_new_tokens=50, min_new_tokens=10)
```

**使用原因**:
- **高质量摘要**: BART 和 T5 是当前最先进的摘要模型
- **多语言支持**: T5 支持多种语言，包括中文
- **可配置长度**: 支持自定义摘要长度和最小长度
- **异步处理**: 支持异步调用，提高处理效率

#### 3. NLTK 数据包依赖

**需要的数据包**:
- `stopwords` - 停用词数据，用于关键词过滤
- `punkt` - 句子分割器，用于文本预处理
- `wordnet` - 词汇数据库，用于词汇相似度计算
- `averaged_perceptron_tagger` - 词性标注器

**自动下载**:
```bash
# 使用提供的脚本自动下载所有 NLP 数据
poetry run python aiecs/scripts/download_nlp_data.py
```

#### 功能特性

1. **文本分类**: 基于预训练模型的文本分类
2. **关键词提取**: 支持 RAKE（英文）和 spaCy（中英文）关键词提取
3. **文本摘要**: 支持中英文文本摘要生成
4. **语言检测**: 自动检测文本语言
5. **异步处理**: 支持异步调用，提高性能

#### 使用示例

```python
from aiecs.tools.task_tools.classfire_tool import ClassifierTool

# 初始化工具
tool = ClassifierTool()

# 文本分类
result = await tool.classify("This is a positive review about the product.")
print(f"分类结果: {result}")

# 关键词提取
keywords = await tool.extract_keywords("Natural language processing is important.", top_k=5)
print(f"关键词: {keywords}")

# 文本摘要
summary = await tool.summarize("Your long text here...", max_length=100)
print(f"摘要: {summary}")

# 中文处理
chinese_keywords = await tool.extract_keywords("自然语言处理是人工智能的重要领域。", top_k=3)
print(f"中文关键词: {chinese_keywords}")
```

#### 性能优化

- **模型缓存**: 首次加载后模型会被缓存，提高后续调用速度
- **异步处理**: 所有主要功能都支持异步调用
- **内存管理**: 支持模型卸载和重新加载，节省内存
- **错误处理**: 完善的错误处理和降级机制

#### 注意事项

- **首次使用**: 首次使用时会自动下载模型，可能需要较长时间
- **网络要求**: 需要网络连接下载 Transformers 模型
- **内存需求**: 模型加载需要一定的内存空间
- **语言支持**: 目前主要支持英文和中文，其他语言支持有限

### Office Tool (办公文档处理工具)

Office Tool 提供了全面的办公文档处理功能，支持读取、写入和转换多种文档格式，包括 Word、PowerPoint、Excel、PDF 和图像文件。

#### 系统依赖要求

**重要**: Office Tool 需要安装 Java 运行时环境和 Tesseract OCR 引擎才能正常工作。

#### 1. Java 运行时环境（必需）

**用途**: Apache Tika 文档解析库需要 Java 运行时环境。

**Ubuntu/Debian 系统**:
```bash
# 安装 OpenJDK 11（推荐）
sudo apt-get update
sudo apt-get install openjdk-11-jdk

# 或者安装 OpenJDK 17
sudo apt-get install openjdk-17-jdk

# 验证安装
java -version
javac -version
```

**macOS 系统**:
```bash
# 使用 Homebrew 安装
brew install openjdk@11

# 或者安装 OpenJDK 17
brew install openjdk@17
```

**环境变量设置**:
```bash
# 设置 JAVA_HOME 环境变量
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
# 或者对于 OpenJDK 17
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
```

#### 2. Tesseract OCR 引擎（OCR 功能必需）

**用途**: 图像文件中的文字识别功能。

**Ubuntu/Debian 系统**:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# 中文 OCR 支持
sudo apt-get install tesseract-ocr-chi-sim    # 简体中文
sudo apt-get install tesseract-ocr-chi-tra    # 繁体中文
```

**macOS 系统**:
```bash
brew install tesseract
```

**验证安装**:
```bash
tesseract --version
tesseract --list-langs
```

#### 3. Python 包依赖

**核心文档处理库**:
- **pandas** (>=2.2.3) - Excel 文件数据处理
- **openpyxl** (>=3.1.5) - Excel 文件读写
- **python-docx** (>=1.1.2) - Word 文档处理
- **python-pptx** (>=1.0.2) - PowerPoint 文档处理
- **pdfplumber** (>=0.11.7) - PDF 文本提取

**内容解析库**:
- **tika** (>=3.2.2) - 通用文档解析（需要 Java 11+）
- **pytesseract** (>=0.3.13) - OCR 文字识别
- **Pillow** (>=11.2.1) - 图像处理

#### 功能特性

1. **文档读取**: 支持 DOCX, PPTX, XLSX, PDF 格式
2. **文档写入**: 创建和编辑 Word, PowerPoint, Excel 文档
3. **文本提取**: 从各种文档格式中提取文本内容
4. **OCR 功能**: 从图像文件中识别文字
5. **多格式支持**: 处理旧版 Office 文档和其他格式

#### 使用示例

```python
from aiecs.tools.task_tools.office_tool import OfficeTool

# 初始化工具
tool = OfficeTool()

# 读取 Word 文档
docx_content = tool.read_docx("/path/to/document.docx")
print(f"文档内容: {docx_content['text']}")

# 读取 Excel 文件
xlsx_data = tool.read_xlsx("/path/to/spreadsheet.xlsx")
print(f"表格数据: {xlsx_data}")

# 提取文本（支持多种格式）
text = tool.extract_text("/path/to/document.pdf")
print(f"提取的文本: {text}")

# 创建 Word 文档
tool.write_docx("Hello World!", "/path/to/output.docx")

# 创建 PowerPoint 演示文稿
slides = ["标题页", "内容页1", "内容页2"]
tool.write_pptx(slides, "/path/to/presentation.pptx")
```

#### OCR 功能说明

**支持的图像格式**:
- PNG, JPG, JPEG, TIFF, BMP, GIF

**语言支持**:
- 英文 (eng)
- 中文简体 (chi_sim)
- 中文繁体 (chi_tra)

**使用示例**:
```python
# 从图像中提取文字
image_text = tool.extract_text("/path/to/image.png")
print(f"识别文字: {image_text}")
```

#### 性能优化

- **Tika 缓存**: 首次使用会下载 Tika JAR 文件并缓存
- **内存管理**: 处理大文件时注意内存使用
- **并发限制**: 建议限制同时处理的文档数量
- **错误处理**: 完善的错误处理和降级机制

#### 注意事项

- **Java 版本**: 需要 Java 8 或更高版本
- **内存需求**: Tika 处理大文件时需要足够内存
- **文件大小**: 默认最大文件大小为 100MB
- **编码问题**: 某些文档可能存在编码问题
- **OCR 准确性**: 图像质量影响 OCR 识别准确性

### Stats Tool (统计分析工具)

Stats Tool 提供了全面的统计分析功能，支持多种统计测试、数据预处理、回归分析、时间序列分析等高级统计功能。

#### 系统依赖要求

**重要**: Stats Tool 需要安装系统级的 C 库来支持特殊文件格式的读取，特别是 SAS、SPSS 和 Stata 文件。

#### 1. pyreadstat 系统依赖（特殊文件格式支持）

**用途**: 读取和写入 SAS、SPSS、Stata 文件 (.sav, .sas7bdat, .por 格式)

**Ubuntu/Debian 系统**:
```bash
# 安装 libreadstat 开发库
sudo apt-get update
sudo apt-get install libreadstat-dev

# 安装编译工具（如果尚未安装）
sudo apt-get install build-essential python3-dev

# 重新安装 pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**macOS 系统**:
```bash
# 使用 Homebrew 安装
brew install readstat

# 重新安装 pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**CentOS/RHEL 系统**:
```bash
# 安装开发工具
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# 安装 readstat 库（可能需要从源码编译）
# 或者使用 conda 安装
conda install -c conda-forge readstat
```

**验证安装**:
```python
import pyreadstat
print("pyreadstat version:", pyreadstat.__version__)

# 测试读取功能
try:
    # 这里不需要实际文件，只是测试导入
    print("pyreadstat 安装成功")
except Exception as e:
    print("pyreadstat 安装失败:", e)
```

#### 2. Excel 文件支持系统依赖

**用途**: 读取和写入 Excel 文件 (.xlsx, .xls 格式)

**Ubuntu/Debian 系统**:
```bash
# 安装 openpyxl 所需的系统库
sudo apt-get install libxml2-dev libxslt1-dev

# 验证安装
python -c "import openpyxl; print('openpyxl 可用')"
```

**macOS 系统**:
```bash
# 通常不需要额外安装，系统已包含所需库
brew install libxml2 libxslt
```

#### 3. Python 包依赖

**核心统计库**:
- **pandas** (>=2.2.3) - 数据处理和分析
- **numpy** (>=2.2.6) - 数值计算
- **scipy** (>=1.15.3) - 科学计算和统计函数
- **scikit-learn** (>=1.5.0) - 机器学习库（数据预处理）
- **statsmodels** (>=0.14.4) - 统计模型和测试

**特殊文件格式支持**:
- **pyreadstat** (>=1.2.9) - SAS、SPSS、Stata 文件支持
- **openpyxl** (>=3.1.5) - Excel 文件支持

**配置管理**:
- **pydantic** (>=2.11.5) - 数据验证
- **pydantic-settings** (>=2.9.1) - 设置管理

#### 功能特性

1. **描述性统计**: 基础统计量、偏度、峰度、分位数
2. **假设检验**: t检验、卡方检验、ANOVA、非参数检验
3. **相关分析**: Pearson、Spearman、Kendall 相关系数
4. **回归分析**: OLS、Logit、Probit、Poisson 回归
5. **时间序列**: ARIMA、SARIMA 模型和预测
6. **数据预处理**: 标准化、缺失值处理、数据清洗
7. **多格式支持**: CSV、Excel、JSON、Parquet、Feather、SAS、SPSS、Stata

#### 支持的文件格式

| 格式 | 扩展名 | 依赖库 | 系统要求 |
|------|--------|--------|----------|
| **CSV** | `.csv` | pandas | 无 |
| **Excel** | `.xlsx`, `.xls` | openpyxl | libxml2, libxslt |
| **JSON** | `.json` | pandas | 无 |
| **Parquet** | `.parquet` | pandas | 无 |
| **Feather** | `.feather` | pandas | 无 |
| **SPSS** | `.sav`, `.por` | pyreadstat | libreadstat |
| **SAS** | `.sas7bdat` | pyreadstat | libreadstat |

#### 使用示例

```python
from aiecs.tools import get_tool

# 获取统计工具
stats_tool = get_tool("stats")

# 读取数据
data_info = stats_tool.read_data("data.sav")  # SPSS 文件
print(f"变量数量: {len(data_info['variables'])}")
print(f"观测数量: {data_info['observations']}")

# 描述性统计
desc_stats = stats_tool.describe(
    file_path="data.sav",
    variables=["age", "income", "education"],
    include_percentiles=True,
    percentiles=[0.1, 0.9]
)

# t检验
ttest_result = stats_tool.ttest(
    file_path="data.sav",
    var1="group1_score",
    var2="group2_score",
    equal_var=True
)

# 相关分析
correlation = stats_tool.correlation(
    file_path="data.sav",
    variables=["var1", "var2", "var3"],
    method="pearson"
)

# 回归分析
regression = stats_tool.regression(
    file_path="data.sav",
    formula="y ~ x1 + x2 + x3",
    regression_type="ols"
)

# 数据预处理
preprocessed = stats_tool.preprocess(
    file_path="data.sav",
    variables=["var1", "var2"],
    operation="scale",
    scaler_type="standard"
)
```

#### 环境变量配置

可以通过以下环境变量配置 Stats Tool：

```bash
# 最大文件大小限制 (MB)
export STATS_TOOL_MAX_FILE_SIZE_MB=200

# 允许的文件扩展名
export STATS_TOOL_ALLOWED_EXTENSIONS=".sav,.sas7bdat,.por,.csv,.xlsx,.xls,.json,.parquet,.feather"
```

#### 故障排除

#### pyreadstat 安装问题

**问题**: `ImportError: No module named 'pyreadstat'` 或编译错误

**解决方案**:
```bash
# 1. 安装系统依赖
sudo apt-get install libreadstat-dev build-essential python3-dev

# 2. 重新安装
pip uninstall pyreadstat
pip install --no-cache-dir pyreadstat

# 3. 验证安装
python -c "import pyreadstat; print('Success')"
```

**问题**: `OSError: libreadstat.so: cannot open shared object file`

**解决方案**:
```bash
# 检查库文件位置
ldconfig -p | grep readstat

# 如果找不到，重新安装系统库
sudo apt-get install --reinstall libreadstat0
```

#### Excel 文件读取问题

**问题**: `ImportError: No module named 'openpyxl'`

**解决方案**:
```bash
# 安装 openpyxl
pip install openpyxl

# 安装系统依赖
sudo apt-get install libxml2-dev libxslt1-dev
```

#### 内存使用问题

**问题**: 大文件处理时内存不足

**解决方案**:
```python
# 使用 nrows 参数限制读取行数
data_info = stats_tool.read_data("large_file.csv", nrows=10000)

# 调整环境变量
export STATS_TOOL_MAX_FILE_SIZE_MB=500
```

#### 文件权限问题

**问题**: 无法读取文件

**解决方案**:
```bash
# 检查文件权限
ls -la data.sav

# 修改权限
chmod 644 data.sav

# 检查文件路径
python -c "import os; print(os.path.exists('data.sav'))"
```

### Report Tool (多格式报告生成工具)

Report Tool 提供了全面的报告生成功能，支持 HTML、Excel、PowerPoint、Word、Markdown、图像和 PDF 格式的报告生成。

#### 系统依赖要求

**重要**: Report Tool 的某些功能需要安装系统级的图形库和字体库。

#### 1. WeasyPrint 系统依赖（PDF 功能必需）

**用途**: HTML 转 PDF 功能需要 WeasyPrint 的系统级依赖。

**Ubuntu/Debian 系统**:
```bash
# 安装 WeasyPrint 所需的系统库
sudo apt-get update
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info

# 完整安装（推荐）
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info libxml2-dev libxslt1-dev
```

**macOS 系统**:
```bash
# 使用 Homebrew 安装
brew install cairo pango gdk-pixbuf libffi
```

**验证安装**:
```bash
# 检查系统库
pkg-config --modversion cairo
pkg-config --modversion pango
```

#### 2. Matplotlib 系统依赖（图表功能必需）

**用途**: 图表生成功能需要字体和图像处理库。

**Ubuntu/Debian 系统**:
```bash
# 安装 Matplotlib 所需的系统库
sudo apt-get install libfreetype6-dev libpng-dev libjpeg-dev libtiff-dev libwebp-dev

# 中文字体支持
sudo apt-get install fonts-wqy-zenhei fonts-wqy-microhei
```

**macOS 系统**:
```bash
# 使用 Homebrew 安装
brew install freetype libpng libjpeg libtiff webp
```

**验证安装**:
```bash
python -c "import matplotlib.pyplot as plt; plt.figure(); print('Matplotlib working')"
```

#### 3. Python 包依赖

**核心报告生成库**:
- **jinja2** (>=3.1.6) - 模板引擎
- **weasyprint** (>=65.1) - HTML 转 PDF
- **matplotlib** (>=3.10.3) - 图表生成
- **bleach** (>=6.2.0) - HTML 清理
- **markdown** (>=3.8) - Markdown 处理

**文档处理库**:
- **pandas** (>=2.2.3) - 数据处理
- **openpyxl** (>=3.1.5) - Excel 文件处理
- **python-docx** (>=1.1.2) - Word 文档处理
- **python-pptx** (>=1.0.2) - PowerPoint 文档处理

#### 功能特性

1. **HTML 报告**: 使用 Jinja2 模板引擎生成 ✅
2. **PDF 报告**: 使用 WeasyPrint 将 HTML 转换为 PDF ⚠️ **暂时禁用**
3. **Excel 报告**: 多工作表 Excel 文件生成 ✅
4. **PowerPoint 报告**: 自定义幻灯片演示文稿 ✅
5. **Word 报告**: 带样式的 Word 文档 ✅
6. **Markdown 报告**: Markdown 格式报告 ✅
7. **图像报告**: 使用 Matplotlib 生成图表 ✅

#### 使用示例

```python
from aiecs.tools.task_tools.report_tool import ReportTool

# 初始化工具
tool = ReportTool()

# 生成 HTML 报告
html_result = tool.generate_html(
    template_path="report_template.html",
    context={"title": "月度报告", "data": data},
    output_path="/path/to/report.html"
)

# 生成 PDF 报告（⚠️ 暂时禁用 - 需要安装系统依赖并修改代码）
# pdf_result = tool.generate_pdf(
#     html=html_content,
#     output_path="/path/to/report.pdf",
#     page_size="A4"
# )

# 生成 Excel 报告
excel_result = tool.generate_excel(
    sheets={"数据": df, "汇总": summary_df},
    output_path="/path/to/report.xlsx"
)

# 生成图表
chart_result = tool.generate_image(
    chart_type="bar",
    data=chart_data,
    output_path="/path/to/chart.png",
    title="销售数据"
)
```

#### PDF 功能说明

**⚠️ 重要提示**: HTML 转 PDF 功能因为 WeasyPrint 系统依赖问题而**暂时禁用**。

**当前状态**: 
- PDF 生成功能完全不可用
- 调用 `generate_pdf()` 方法会抛出错误
- 需要手动安装系统依赖并修改代码才能启用

**禁用原因**:
- 缺少 WeasyPrint 所需的系统级图形库
- 部署环境复杂性导致依赖安装困难
- 为了确保其他功能的稳定性

**启用方法**:
1. **安装 WeasyPrint 系统依赖**:
   ```bash
   sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
   ```
2. **修改代码**:
   - 取消注释 `from weasyprint import HTML` 导入语句
   - 取消注释 `generate_pdf` 方法中的实现代码
   - 删除错误抛出语句
3. **验证安装**: 确保所有系统库正确安装

**支持功能**（启用后）:
- HTML 转 PDF
- 自定义页面大小
- CSS 样式支持
- 模板变量替换

**替代方案**:
- 使用 `generate_html()` 生成 HTML 报告
- 使用浏览器手动打印为 PDF
- 使用其他 PDF 生成工具

#### 性能优化

- **模板缓存**: Jinja2 模板自动缓存
- **临时文件管理**: 自动清理临时文件
- **批量生成**: 支持并行生成多个报告
- **内存管理**: 大文件处理优化

#### 注意事项

- **WeasyPrint 依赖**: PDF 功能需要完整的系统库支持
- **字体支持**: 图表生成需要系统字体库
- **模板安全**: 自动清理 HTML 内容防止 XSS 攻击
- **文件大小**: 大文件处理时注意内存使用
- **并发限制**: 建议限制同时生成的报告数量

---

## Scraper Tool (网页抓取工具)

### 功能概述

Scraper Tool 是一个功能强大的网页抓取工具，支持多种 HTTP 客户端、JavaScript 渲染、HTML 解析和高级爬虫功能。

**主要功能**:
- **HTTP 请求**: 支持 httpx、urllib 等多种客户端
- **JavaScript 渲染**: 使用 Playwright 进行动态内容抓取
- **HTML 解析**: 使用 BeautifulSoup 和 lxml 解析内容
- **高级爬虫**: 集成 Scrapy 进行复杂爬虫项目
- **多格式输出**: 支持文本、JSON、HTML、Markdown、CSV 输出

### 特殊依赖说明

#### 1. Playwright 浏览器依赖

**用途**: JavaScript 渲染功能 (`render()` 方法)

**依赖内容**:
- **Python 包**: `playwright` (已安装)
- **浏览器二进制文件**: Chromium、Firefox、WebKit
- **系统依赖**: 浏览器运行所需的系统库

**安装步骤**:

1. **下载浏览器**:
   ```bash
   cd /home/coder1/python-middleware-dev
   poetry run playwright install
   ```

2. **安装系统依赖**:
   ```bash
   # 方法1: 使用 Playwright 自动安装
   poetry run playwright install-deps
   
   # 方法2: 手动安装 (Ubuntu/Debian)
   sudo apt-get install libatk1.0-0 \
       libatk-bridge2.0-0 \
       libcups2 \
       libxkbcommon0 \
       libatspi2.0-0 \
       libxcomposite1 \
       libxdamage1 \
       libxfixes3 \
       libxrandr2 \
       libgbm1 \
       libasound2
   ```

   # 方法3 root账户安装（推荐）
    # 临时安装 playwright-python 包
    pip install playwright

    # 运行 playwright 的命令来安装系统依赖
    python -m playwright install-deps

    # 依赖安装完成后，卸载临时的 playwright-python 包，保持 root 环境干净
    pip uninstall playwright -y

**浏览器存储位置**:
- **路径**: `~/.cache/ms-playwright/`
- **大小**: 约 400-500MB (所有浏览器)
- **包含**: Chromium、Firefox、WebKit、FFMPEG

**功能支持**:
- **页面渲染**: 等待 JavaScript 执行完成
- **元素等待**: 等待特定 CSS 选择器
- **页面滚动**: 滚动到页面底部
- **截图功能**: 保存页面截图
- **多浏览器**: 支持 Chromium、Firefox、WebKit

#### 2. Scrapy 高级爬虫依赖

**用途**: 高级爬虫功能 (`crawl_scrapy()` 方法)

**依赖内容**:
- **Python 包**: `scrapy` (需要安装)
- **项目结构**: 需要完整的 Scrapy 项目

**安装步骤**:
```bash
cd /home/coder1/python-middleware-dev
poetry add scrapy
```

**功能支持**:
- **项目化爬虫**: 支持完整的 Scrapy 项目结构
- **数据管道**: 数据清洗、去重、存储
- **中间件**: 请求/响应处理
- **调度器**: 智能请求调度
- **监控**: 详细的日志和统计

#### 3. 其他依赖

**Python 包依赖**:
- **httpx**: 异步 HTTP 客户端
- **beautifulsoup4**: HTML/XML 解析
- **lxml**: 快速 XML 和 HTML 处理

**系统依赖**:
- **网络连接**: 下载浏览器和访问目标网站
- **内存**: 浏览器运行需要足够内存
- **磁盘空间**: 浏览器文件约 500MB

### 使用示例

#### 基础 HTTP 请求 (无需浏览器)
```python
from aiecs.tools.task_tools.scraper_tool import ScraperTool

scraper = ScraperTool()

# 使用 httpx 进行 HTTP 请求
result = await scraper.get_httpx("https://example.com")

# 解析 HTML 内容
parsed = scraper.parse_html(html_content, "h1")
```

#### JavaScript 渲染 (需要 Playwright)
```python
# 需要先安装 Playwright 浏览器
result = await scraper.render(
    url="https://spa-app.com",
    wait_time=5,
    screenshot=True
)
```

#### 高级爬虫 (需要 Scrapy)
```python
# 需要先安装 Scrapy
result = scraper.crawl_scrapy(
    project_path="/path/to/scrapy/project",
    spider_name="my_spider",
    output_path="output.json"
)
```

### 功能分类

| 功能类型 | 方法名 | 需要浏览器 | 需要 Scrapy | 依赖 |
|---------|--------|-----------|------------|------|
| **基础 HTTP** | `get_httpx()` | ❌ 不需要 | ❌ 不需要 | httpx |
| **基础 HTTP** | `get_urllib()` | ❌ 不需要 | ❌ 不需要 | urllib |
| **HTML 解析** | `parse_html()` | ❌ 不需要 | ❌ 不需要 | BeautifulSoup |
| **JavaScript 渲染** | `render()` | ✅ 需要 | ❌ 不需要 | Playwright + 浏览器 |
| **高级爬虫** | `crawl_scrapy()` | ❌ 不需要 | ✅ 需要 | Scrapy |

### 注意事项

#### Playwright 相关
- **浏览器下载**: 首次使用需要下载浏览器 (约 500MB)
- **系统依赖**: 需要安装系统级图形库
- **内存使用**: 浏览器运行需要足够内存
- **网络要求**: 需要网络连接下载浏览器

#### Scrapy 相关
- **项目结构**: 需要完整的 Scrapy 项目目录
- **Spider 定义**: 需要预先定义爬虫逻辑
- **输出格式**: 支持多种输出格式 (JSON、CSV、XML)

#### 通用注意事项
- **网络限制**: 遵守网站的 robots.txt 和访问频率限制
- **法律合规**: 确保抓取行为符合相关法律法规
- **资源管理**: 合理控制并发请求数量
- **错误处理**: 实现适当的重试和错误处理机制

### 故障排除

#### Playwright 问题
```bash
# 检查浏览器是否安装
poetry run playwright install --list

# 重新安装浏览器
poetry run playwright install --force

# 检查系统依赖
poetry run playwright install-deps
```

#### Scrapy 问题
```bash
# 检查 Scrapy 是否安装
poetry run scrapy --version

# 创建测试项目
poetry run scrapy startproject test_project
```

#### 网络问题
- **代理设置**: 配置 HTTP 代理
- **超时设置**: 调整请求超时时间
- **重试机制**: 实现自动重试逻辑