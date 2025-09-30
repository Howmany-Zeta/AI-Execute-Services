# AIECS 文档创建系统 - 快速参考

## 🚀 快速开始

### 最简单的方式（一行代码）

```python
from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator

orchestrator = AIDocumentWriterOrchestrator()
result = orchestrator.create_rich_document("business_report", {"metadata": {"title": "My Report"}}, ai_assistance=True)
```

---

## 📋 5大核心工具

| 工具 | 用途 | 导入路径 |
|------|------|----------|
| **DocumentCreatorTool** | 创建文档 | `aiecs.tools.docs.document_creator_tool` |
| **DocumentLayoutTool** | 布局排版 | `aiecs.tools.docs.document_layout_tool` |
| **ContentInsertionTool** | 插入内容 | `aiecs.tools.docs.content_insertion_tool` |
| **DocumentWriterTool** | 文本编辑 | `aiecs.tools.docs.document_writer_tool` |
| **AIDocumentWriterOrchestrator** | AI编排 | `aiecs.tools.docs.ai_document_writer_orchestrator` |

---

## 🎯 常用操作速查

### 1. 创建文档

```python
from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool, TemplateType

creator = DocumentCreatorTool()
result = creator.create_document(
    document_type="report",
    template_type=TemplateType.BUSINESS_REPORT,
    output_format="markdown",
    metadata={"title": "Report", "author": "Me"}
)
```

**9种模板**: blank, business_report, technical_doc, academic_paper, project_proposal, user_manual, presentation, newsletter, invoice

### 2. 配置布局

```python
from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool, PageSize

layout = DocumentLayoutTool()
layout.set_page_layout(
    document_path="doc.md",
    page_size=PageSize.A4,
    orientation="portrait",
    margins={"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
)
```

**10种布局预设**: default, academic_paper, business_report, magazine, newspaper, presentation, technical_doc, letter, invoice, brochure

### 3. 插入图表

```python
from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool, ChartType

content = ContentInsertionTool()
content.insert_chart(
    document_path="doc.md",
    chart_data={"labels": ["A", "B"], "values": [10, 20]},
    chart_type=ChartType.BAR,
    position={"line": 10},
    caption="My Chart"
)
```

**10种图表**: bar, line, pie, scatter, histogram, box, heatmap, area, bubble, gantt

### 4. 插入表格

```python
content.insert_table(
    document_path="doc.md",
    table_data=[[1, 2], [3, 4]],
    position={"line": 15},
    table_style="corporate",
    headers=["Col1", "Col2"]
)
```

**8种表格样式**: default, simple, grid, striped, bordered, corporate, academic, minimal

### 5. 文本编辑

```python
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool

writer = DocumentWriterTool()

# 写入
writer.write_document("doc.md", "Content", "markdown", mode="create")

# 格式化
writer.edit_document("doc.md", operation="bold", selection={"start_offset": 0, "end_offset": 10})

# 查找替换
writer.find_replace("doc.md", "old", "new", replace_all=True)
```

**15种编辑操作**: bold, italic, underline, strikethrough, highlight, insert_text, delete_text, replace_text, copy_text, cut_text, paste_text, find_replace, insert_line, delete_line, move_line

### 6. AI增强

```python
from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator

orchestrator = AIDocumentWriterOrchestrator()

# AI编辑
orchestrator.ai_edit_document(
    target_path="doc.md",
    operation="smart_format",
    edit_instructions="Improve formatting"
)

# 生成带图表的文档
orchestrator.generate_document_with_charts(
    requirements="Sales report with charts",
    data_sources=[{"data": {...}, "chart_type": "bar"}],
    document_type="report"
)
```

**7种AI操作**: smart_format, style_enhance, content_restructure, intelligent_highlight, auto_bold_keywords, smart_paragraph, ai_proofreading

---

## 🔄 典型工作流

### 流程1: 基础文档（无AI）

```python
# 1. 创建
creator.create_document(template_type="blank", ...)

# 2. 写入
writer.write_document(content="...", mode="create")

# 3. 格式化
writer.edit_document(operation="bold", ...)
```

### 流程2: 专业文档（有布局）

```python
# 1. 创建
creator.create_document(template_type="business_report", ...)

# 2. 布局
layout.set_page_layout(...)
layout.setup_headers_footers(...)

# 3. 内容
writer.write_document(...)
```

### 流程3: 富媒体文档（有图表表格）

```python
# 1. 创建
creator.create_document(...)

# 2. 布局
layout.set_page_layout(...)

# 3. 插入
content.insert_chart(...)
content.insert_table(...)

# 4. 编辑
writer.edit_document(...)
```

### 流程4: AI智能文档（完全自动化）

```python
# 一键完成
orchestrator.create_rich_document(
    document_template="business_report",
    content_plan={...},
    layout_config={...},
    ai_assistance=True
)
```

---

## 📊 功能对比

| 功能 | Creator | Layout | Content | Writer | Orchestrator |
|------|---------|--------|---------|--------|--------------|
| 创建文档 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 模板管理 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 页面布局 | ❌ | ✅ | ❌ | ❌ | ✅ |
| 多列布局 | ❌ | ✅ | ❌ | ❌ | ✅ |
| 插入图表 | ❌ | ❌ | ✅ | ❌ | ✅ |
| 插入表格 | ❌ | ❌ | ✅ | ❌ | ✅ |
| 文本编辑 | ❌ | ❌ | ❌ | ✅ | ✅ |
| AI增强 | ❌ | ❌ | ❌ | ❌ | ✅ |
| 独立使用 | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🎨 支持的格式

### 输出格式（11种）
- 文本: TXT, MARKDOWN, HTML, XML
- 办公: DOCX, XLSX, PDF
- 数据: JSON, YAML, CSV
- 其他: LATEX, BINARY

### 图表类型（10种）
- 基础: bar, line, pie
- 分析: scatter, histogram, box
- 高级: heatmap, area, bubble, gantt

### 表格样式（8种）
- default, simple, grid, striped
- bordered, corporate, academic, minimal

### 文档模板（9种）
- blank, business_report, technical_doc
- academic_paper, project_proposal, user_manual
- presentation, newsletter, invoice

### 布局预设（10种）
- default, academic_paper, business_report
- magazine, newspaper, presentation
- technical_doc, letter, invoice, brochure

---

## ⚙️ 配置选项

### 页面尺寸
- A4, A3, A5
- Letter, Legal, Tabloid
- Custom

### 页面方向
- Portrait（纵向）
- Landscape（横向）

### 对齐方式
- Left, Center, Right
- Justify

### 图片对齐
- left, center, right
- inline, float_left, float_right

### 写入模式（9种）
- create, overwrite, append, update
- backup_write, version_write
- insert, replace, delete

---

## 💡 实用技巧

### 技巧1: 选择正确的工具

- **简单文本**? → DocumentWriterTool
- **需要布局**? → DocumentLayoutTool
- **有图表表格**? → ContentInsertionTool
- **复杂文档**? → AIDocumentWriterOrchestrator
- **从头创建**? → DocumentCreatorTool

### 技巧2: 使用模板

```python
# 不要从空白开始
creator.create_document(template_type="blank", ...)  # ❌

# 使用合适的模板
creator.create_document(template_type="business_report", ...)  # ✅
```

### 技巧3: 批量操作

```python
# 不要一个个插入
for item in items:
    content.insert_chart(...)  # ❌

# 使用批量插入
content.batch_insert_content(content_items=items)  # ✅
```

### 技巧4: 启用备份

```python
# 危险操作前备份
writer.write_document(..., mode="backup_write")  # ✅
```

### 技巧5: 使用AI优化

```python
# 手动优化很麻烦
writer.edit_document(...)
writer.find_replace(...)
writer.format_text(...)  # ❌

# AI一键优化
orchestrator.ai_edit_document(operation="smart_format", ...)  # ✅
```

---

## 🔍 常见问题

### Q: 如何选择使用哪个工具?
**A**: 
- 简单任务 → 使用单个工具
- 复杂任务 → 使用Orchestrator
- 不确定 → 使用Orchestrator

### Q: 工具之间如何配合?
**A**: 
- 可以独立使用
- 可以组合使用
- Orchestrator自动协调

### Q: 支持哪些云存储?
**A**: 
- Google Cloud Storage (gs://)
- AWS S3 (s3://)
- Azure Blob Storage (azure://)
- 通用存储ID

### Q: 如何处理大文件?
**A**: 
- 启用流式处理
- 使用批量操作
- 配置内存优化

### Q: AI功能需要什么?
**A**: 
- AIECS客户端配置
- AI Provider设置
- 可选（有fallback）

---

## 📚 更多资源

- **详细架构**: [DOCUMENT_CREATION_ARCHITECTURE.md](./DOCUMENT_CREATION_ARCHITECTURE.md)
- **完整示例**: [comprehensive_document_creation_example.py](../examples/comprehensive_document_creation_example.py)
- **工具文档**: [TOOLS_USED_INSTRUCTION/](./TOOLS_USED_INSTRUCTION/)

---

## 🎯 速查代码片段

### 创建商业报告
```python
creator = DocumentCreatorTool()
creator.create_document(
    document_type="report",
    template_type="business_report",
    output_format="markdown",
    metadata={"title": "Q4 Report"}
)
```

### 添加图表
```python
content = ContentInsertionTool()
content.insert_chart(
    document_path="report.md",
    chart_data={"labels": ["Q1", "Q2"], "values": [100, 150]},
    chart_type="bar",
    position={"line": 10}
)
```

### AI优化文档
```python
orchestrator = AIDocumentWriterOrchestrator()
orchestrator.optimize_document_layout(
    document_path="report.md",
    optimization_goals=["professional", "readability"]
)
```

### 批量内容
```python
orchestrator.batch_content_insertion(
    document_path="report.md",
    content_plan=[
        {"content_type": "chart", ...},
        {"content_type": "table", ...}
    ]
)
```

---

**提示**: 记住这个架构 = "5个独立工具 + 1个AI编排器" ✨
