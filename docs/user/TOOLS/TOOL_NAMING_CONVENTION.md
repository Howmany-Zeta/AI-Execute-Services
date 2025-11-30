# Tool Naming Convention

## 📋 Core Rules

When using tools in configuration files or code, **you must use lowercase + underscore format, without the `Tool` suffix**.

---

## ✅ Correct Tool Names

### Format Rules

- **Lowercase letters**
- **Use underscores** to separate words
- **No `Tool` suffix**

### Complete Tool Name List

| Name Used in Config | Corresponding Class Name | Description |
|---------------------|--------------------------|-------------|
| `ai_document_orchestrator` | `AIDocumentOrchestrator` | AI Document Orchestrator |
| `ai_document_writer_orchestrator` | `AIDocumentWriterOrchestrator` | AI Document Writer Orchestrator |
| `chart` | `ChartTool` | Chart Tool |
| `classifier` | `ClassifierTool` | Classifier Tool |
| `content_insertion` | `ContentInsertionTool` | Content Insertion Tool |
| `document_creator` | `DocumentCreatorTool` | Document Creator Tool |
| `document_layout` | `DocumentLayoutTool` | Document Layout Tool |
| `document_parser` | `DocumentParserTool` | Document Parser Tool |
| `document_writer` | `DocumentWriterTool` | Document Writer Tool |
| `image` | `ImageTool` | Image Processing Tool |
| `office` | `OfficeTool` | Office Document Tool |
| `pandas` | `PandasTool` | Data Analysis Tool |
| `report` | `ReportTool` | Report Generation Tool |
| `research` | `ResearchTool` | Research Tool |
| `scraper` | `ScraperTool` | Web Scraping Tool |
| `search_api` | `SearchAPITool` | Search API Tool |
| `stats` | `StatsTool` | Statistical Analysis Tool |

---

## 📝 Usage Examples

### 1. Get Tool in Python Code

```python
from aiecs.tools import get_tool

# ✅ Correct
tool = get_tool("ai_document_orchestrator")
tool = get_tool("office")
tool = get_tool("pandas")

# ❌ Wrong - will raise exception
tool = get_tool("AIDocumentOrchestrator")  # Error: used class name
tool = get_tool("OfficeTool")              # Error: has Tool suffix
tool = get_tool("PandasTool")              # Error: has Tool suffix
```

### 2. Get LangChain Tools

```python
from aiecs.tools.langchain_adapter import get_langchain_tools

# ✅ Correct - get specific tools
tools = get_langchain_tools(['pandas', 'chart', 'office'])

# ✅ Correct - get all tools
tools = get_langchain_tools()

# ❌ Wrong - used class names
tools = get_langchain_tools(['PandasTool', 'ChartTool'])  # will fail
```

### 3. Specify Tools in Configuration Files

#### YAML Configuration Example

```yaml
# config/agent_config.yaml

agent:
  name: "data_analysis_agent"
  type: "react"
  
  # ✅ Correct - use lowercase + underscore
  tools:
    - pandas
    - chart
    - stats
    - office
  
  # ❌ Wrong - don't use these
  # tools:
  #   - PandasTool      # Error
  #   - ChartTool       # Error
  #   - OfficeTool      # Error
```

#### JSON Configuration Example

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

#### Python Configuration Example

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

### 4. Create LangChain Agent

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from aiecs.tools.langchain_adapter import get_langchain_tools

# ✅ Correct - use tool name list
tool_names = ['pandas', 'chart', 'stats']
tools = get_langchain_tools(tool_names)

llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)
```

---

## ❌ Common Errors

### Error 1: Using Class Name Instead of Tool Name

```python
# ❌ Wrong
tool = get_tool("PandasTool")
# Error message: Tool 'PandasTool' is not registered

# ✅ Correct
tool = get_tool("pandas")
```

### Error 2: Using Uppercase Letters

```python
# ❌ Wrong
tool = get_tool("Pandas")
tool = get_tool("PANDAS")
# Error message: Tool 'Pandas' is not registered

# ✅ Correct
tool = get_tool("pandas")
```

### Error 3: Adding Tool Suffix

```python
# ❌ Wrong
tool = get_tool("office_tool")
tool = get_tool("chart_tool")
# Error message: Tool 'office_tool' is not registered

# ✅ Correct
tool = get_tool("office")
tool = get_tool("chart")
```

### Error 4: Using CamelCase

```python
# ❌ Wrong
tool = get_tool("aiDocumentOrchestrator")
tool = get_tool("documentParser")
# Error message: Tool 'aiDocumentOrchestrator' is not registered

# ✅ Correct
tool = get_tool("ai_document_orchestrator")
tool = get_tool("document_parser")
```

---

## 🔍 How to View All Available Tool Names

### Method 1: Use list_tools()

```python
from aiecs.tools import discover_tools, list_tools

discover_tools()
tools = list_tools()

for tool in tools:
    print(f"Tool name: {tool['name']}")
```

### Method 2: Use TOOL_CLASSES

```python
from aiecs.tools import discover_tools, TOOL_CLASSES

discover_tools()

for tool_name in sorted(TOOL_CLASSES.keys()):
    print(f"Tool name: {tool_name}")
```

### Method 3: Use Command Line

```bash
# View all tools
poetry run python -c "from aiecs.tools import discover_tools, list_tools; discover_tools(); [print(t['name']) for t in list_tools()]"
```

---

## 📚 Naming Convention Explanation

### Why Use Lowercase + Underscore?

1. **Python Convention**: Follows Python naming conventions (snake_case)
2. **Configuration Friendly**: More readable in YAML/JSON configuration files
3. **Avoid Ambiguity**: Unified naming rules, reducing confusion
4. **Tool Registration**: This is the format used when registering tools

### Class Name vs Tool Name

| Purpose | Format | Example |
|---------|--------|---------|
| **Tool Registration/Config** | lowercase + underscore | `pandas`, `office`, `ai_document_orchestrator` |
| **Python Class Definition** | PascalCase + Tool suffix | `PandasTool`, `OfficeTool`, `AIDocumentOrchestrator` |
| **Import Class** | PascalCase + Tool suffix | `from aiecs.tools.task_tools.pandas_tool import PandasTool` |
| **Get Tool Instance** | lowercase + underscore | `get_tool("pandas")` |

---

## 🎯 Quick Reference

### Common Tool Names Quick Reference

**Data Processing**:
- `pandas` - Data analysis
- `stats` - Statistical analysis
- `chart` - Chart generation

**Document Processing**:
- `office` - Office documents
- `document_parser` - Document parsing
- `document_writer` - Document writing
- `ai_document_orchestrator` - AI document orchestration

**Content Retrieval**:
- `scraper` - Web scraping
- `research` - Research tool
- `search_api` - Search API

**Others**:
- `image` - Image processing
- `classifier` - Text classification
- `report` - Report generation

---

## ✅ Verify Tool Name

If you're not sure if a tool name is correct, you can use the following method to verify:

```python
from aiecs.tools import get_tool

def verify_tool_name(name):
    """Verify if tool name is correct"""
    try:
        tool = get_tool(name)
        print(f"✅ '{name}' is a correct tool name")
        print(f"   Corresponding class: {tool.__class__.__name__}")
        return True
    except ValueError as e:
        print(f"❌ '{name}' is not a valid tool name")
        print(f"   Error: {e}")
        return False

# Test
verify_tool_name("pandas")              # ✅ Correct
verify_tool_name("PandasTool")          # ❌ Wrong
verify_tool_name("office")              # ✅ Correct
verify_tool_name("ai_document_orchestrator")  # ✅ Correct
```

---

## 📖 Related Documentation

- [Tool Registration Mechanism](TOOLS_BASE_TOOL.md)
- [LangChain Adapter](TOOLS_LANGCHAIN_ADAPTER.md)
- [Tool Development Guide](./TOOLS_BASE_TOOL.md)

---

**Last Updated**: 2025-10-02  
**Maintainer**: AIECS Tools Team
