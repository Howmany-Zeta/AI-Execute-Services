# 工具名称使用规范

## 📋 核心规则

在配置文件或代码中使用工具时，**必须使用小写 + 下划线格式，不带 `Tool` 后缀**。

---

## ✅ 正确的工具名称

### 格式规则

- **小写字母**
- **使用下划线** 分隔单词
- **不带 `Tool` 后缀**

### 完整工具名称列表

| 配置中使用的名称 | 对应的类名 | 说明 |
|-----------------|-----------|------|
| `ai_document_orchestrator` | `AIDocumentOrchestrator` | AI 文档编排器 |
| `ai_document_writer_orchestrator` | `AIDocumentWriterOrchestrator` | AI 文档写作编排器 |
| `chart` | `ChartTool` | 图表工具 |
| `classifier` | `ClassifierTool` | 分类器工具 |
| `content_insertion` | `ContentInsertionTool` | 内容插入工具 |
| `document_creator` | `DocumentCreatorTool` | 文档创建工具 |
| `document_layout` | `DocumentLayoutTool` | 文档布局工具 |
| `document_parser` | `DocumentParserTool` | 文档解析工具 |
| `document_writer` | `DocumentWriterTool` | 文档写作工具 |
| `image` | `ImageTool` | 图像处理工具 |
| `office` | `OfficeTool` | Office 文档工具 |
| `pandas` | `PandasTool` | 数据分析工具 |
| `report` | `ReportTool` | 报告生成工具 |
| `research` | `ResearchTool` | 研究工具 |
| `scraper` | `ScraperTool` | 网页抓取工具 |
| `search_api` | `SearchAPITool` | 搜索 API 工具 |
| `stats` | `StatsTool` | 统计分析工具 |

---

## 📝 使用示例

### 1. 在 Python 代码中获取工具

```python
from aiecs.tools import get_tool

# ✅ 正确
tool = get_tool("ai_document_orchestrator")
tool = get_tool("office")
tool = get_tool("pandas")

# ❌ 错误 - 会抛出异常
tool = get_tool("AIDocumentOrchestrator")  # 错误：使用了类名
tool = get_tool("OfficeTool")              # 错误：带了 Tool 后缀
tool = get_tool("PandasTool")              # 错误：带了 Tool 后缀
```

### 2. 获取 LangChain 工具

```python
from aiecs.tools.langchain_adapter import get_langchain_tools

# ✅ 正确 - 获取特定工具
tools = get_langchain_tools(['pandas', 'chart', 'office'])

# ✅ 正确 - 获取所有工具
tools = get_langchain_tools()

# ❌ 错误 - 使用了类名
tools = get_langchain_tools(['PandasTool', 'ChartTool'])  # 会失败
```

### 3. 在配置文件中指定工具

#### YAML 配置示例

```yaml
# config/agent_config.yaml

agent:
  name: "data_analysis_agent"
  type: "react"
  
  # ✅ 正确 - 使用小写 + 下划线
  tools:
    - pandas
    - chart
    - stats
    - office
  
  # ❌ 错误 - 不要使用这些
  # tools:
  #   - PandasTool      # 错误
  #   - ChartTool       # 错误
  #   - OfficeTool      # 错误
```

#### JSON 配置示例

```json
{
  "agent": {
    "name": "document_agent",
    "type": "tool_calling",
    "tools": [
      "ai_document_orchestrator",
      "document_parser",
      "document_writer",
      "office"
    ]
  }
}
```

#### Python 配置示例

```python
# config.py

AGENT_CONFIG = {
    'name': 'research_agent',
    'type': 'react',
    'tools': [
        'research',
        'scraper',
        'classifier',
        'pandas'
    ]
}
```

### 4. 创建 LangChain Agent

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from aiecs.tools.langchain_adapter import get_langchain_tools

# ✅ 正确 - 使用工具名称列表
tool_names = ['pandas', 'chart', 'stats']
tools = get_langchain_tools(tool_names)

llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
```

---

## ❌ 常见错误

### 错误 1: 使用类名而不是工具名

```python
# ❌ 错误
tool = get_tool("PandasTool")
# 错误信息: Tool 'PandasTool' is not registered

# ✅ 正确
tool = get_tool("pandas")
```

### 错误 2: 使用大写字母

```python
# ❌ 错误
tool = get_tool("Pandas")
tool = get_tool("PANDAS")
# 错误信息: Tool 'Pandas' is not registered

# ✅ 正确
tool = get_tool("pandas")
```

### 错误 3: 添加 Tool 后缀

```python
# ❌ 错误
tool = get_tool("office_tool")
tool = get_tool("chart_tool")
# 错误信息: Tool 'office_tool' is not registered

# ✅ 正确
tool = get_tool("office")
tool = get_tool("chart")
```

### 错误 4: 使用驼峰命名

```python
# ❌ 错误
tool = get_tool("aiDocumentOrchestrator")
tool = get_tool("documentParser")
# 错误信息: Tool 'aiDocumentOrchestrator' is not registered

# ✅ 正确
tool = get_tool("ai_document_orchestrator")
tool = get_tool("document_parser")
```

---

## 🔍 如何查看所有可用工具名称

### 方法 1: 使用 list_tools()

```python
from aiecs.tools import discover_tools, list_tools

discover_tools()
tools = list_tools()

for tool in tools:
    print(f"工具名: {tool['name']}")
```

### 方法 2: 使用 TOOL_CLASSES

```python
from aiecs.tools import discover_tools, TOOL_CLASSES

discover_tools()

for tool_name in sorted(TOOL_CLASSES.keys()):
    print(f"工具名: {tool_name}")
```

### 方法 3: 使用命令行

```bash
# 查看所有工具
poetry run python -c "from aiecs.tools import discover_tools, list_tools; discover_tools(); [print(t['name']) for t in list_tools()]"
```

---

## 📚 命名规则说明

### 为什么使用小写 + 下划线？

1. **Python 惯例**: 符合 Python 的命名规范（snake_case）
2. **配置友好**: 在 YAML/JSON 配置文件中更易读
3. **避免歧义**: 统一的命名规则，减少混淆
4. **工具注册**: 工具注册时使用的就是这种格式

### 类名 vs 工具名

| 用途 | 使用格式 | 示例 |
|------|---------|------|
| **工具注册/配置** | 小写 + 下划线 | `pandas`, `office`, `ai_document_orchestrator` |
| **Python 类定义** | 大驼峰 + Tool 后缀 | `PandasTool`, `OfficeTool`, `AIDocumentOrchestrator` |
| **导入类** | 大驼峰 + Tool 后缀 | `from aiecs.tools.task_tools.pandas_tool import PandasTool` |
| **获取工具实例** | 小写 + 下划线 | `get_tool("pandas")` |

---

## 🎯 快速参考

### 常用工具名称速查

**数据处理**:
- `pandas` - 数据分析
- `stats` - 统计分析
- `chart` - 图表生成

**文档处理**:
- `office` - Office 文档
- `document_parser` - 文档解析
- `document_writer` - 文档写作
- `ai_document_orchestrator` - AI 文档编排

**内容获取**:
- `scraper` - 网页抓取
- `research` - 研究工具
- `search_api` - 搜索 API

**其他**:
- `image` - 图像处理
- `classifier` - 文本分类
- `report` - 报告生成

---

## ✅ 验证工具名称

如果不确定工具名称是否正确，可以使用以下方法验证：

```python
from aiecs.tools import get_tool

def verify_tool_name(name):
    """验证工具名称是否正确"""
    try:
        tool = get_tool(name)
        print(f"✅ '{name}' 是正确的工具名称")
        print(f"   对应类: {tool.__class__.__name__}")
        return True
    except ValueError as e:
        print(f"❌ '{name}' 不是有效的工具名称")
        print(f"   错误: {e}")
        return False

# 测试
verify_tool_name("pandas")              # ✅ 正确
verify_tool_name("PandasTool")          # ❌ 错误
verify_tool_name("office")              # ✅ 正确
verify_tool_name("ai_document_orchestrator")  # ✅ 正确
```

---

## 📖 相关文档

- [工具注册机制](TOOLS_BASE_TOOL.md)
- [LangChain 适配器](TOOLS_LANGCHAIN_ADAPTER.md)
- [工具开发指南](../../aiecs/scripts/tools_develop/README.md)

---

**最后更新**: 2025-10-02  
**维护者**: AIECS Tools Team

