# AIECS Document Creation System - Quick Reference

## 🚀 Quick Start

### Simplest Way (One Line of Code)

```python
from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator

orchestrator = AIDocumentWriterOrchestrator()
result = orchestrator.create_rich_document("business_report", {"metadata": {"title": "My Report"}}, ai_assistance=True)
```

---

## 📋 5 Core Tools

| Tool | Purpose | Import Path |
|------|---------|-------------|
| **DocumentCreatorTool** | Create documents | `aiecs.tools.docs.document_creator_tool` |
| **DocumentLayoutTool** | Layout & formatting | `aiecs.tools.docs.document_layout_tool` |
| **ContentInsertionTool** | Insert content | `aiecs.tools.docs.content_insertion_tool` |
| **DocumentWriterTool** | Text editing | `aiecs.tools.docs.document_writer_tool` |
| **AIDocumentWriterOrchestrator** | AI orchestration | `aiecs.tools.docs.ai_document_writer_orchestrator` |

---

## 🎯 Common Operations Quick Reference

### 1. Create Document

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

**9 Templates**: blank, business_report, technical_doc, academic_paper, project_proposal, user_manual, presentation, newsletter, invoice

### 2. Configure Layout

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

**10 Layout Presets**: default, academic_paper, business_report, magazine, newspaper, presentation, technical_doc, letter, invoice, brochure

### 3. Insert Chart

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

**10 Chart Types**: bar, line, pie, scatter, histogram, box, heatmap, area, bubble, gantt

### 4. Insert Table

```python
content.insert_table(
    document_path="doc.md",
    table_data=[[1, 2], [3, 4]],
    position={"line": 15},
    table_style="corporate",
    headers=["Col1", "Col2"]
)
```

**8 Table Styles**: default, simple, grid, striped, bordered, corporate, academic, minimal

### 5. Text Editing

```python
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool

writer = DocumentWriterTool()

# Write
writer.write_document("doc.md", "Content", "markdown", mode="create")

# Format
writer.edit_document("doc.md", operation="bold", selection={"start_offset": 0, "end_offset": 10})

# Find & Replace
writer.find_replace("doc.md", "old", "new", replace_all=True)
```

**15 Edit Operations**: bold, italic, underline, strikethrough, highlight, insert_text, delete_text, replace_text, copy_text, cut_text, paste_text, find_replace, insert_line, delete_line, move_line

### 6. AI Enhancement

```python
from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator

orchestrator = AIDocumentWriterOrchestrator()

# AI Edit
orchestrator.ai_edit_document(
    target_path="doc.md",
    operation="smart_format",
    edit_instructions="Improve formatting"
)

# Generate document with charts
orchestrator.generate_document_with_charts(
    requirements="Sales report with charts",
    data_sources=[{"data": {...}, "chart_type": "bar"}],
    document_type="report"
)
```

**7 AI Operations**: smart_format, style_enhance, content_restructure, intelligent_highlight, auto_bold_keywords, smart_paragraph, ai_proofreading

---

## 🔄 Typical Workflows

### Workflow 1: Basic Document (No AI)

```python
# 1. Create
creator.create_document(template_type="blank", ...)

# 2. Write
writer.write_document(content="...", mode="create")

# 3. Format
writer.edit_document(operation="bold", ...)
```

### Workflow 2: Professional Document (With Layout)

```python
# 1. Create
creator.create_document(template_type="business_report", ...)

# 2. Layout
layout.set_page_layout(...)
layout.setup_headers_footers(...)

# 3. Content
writer.write_document(...)
```

### Workflow 3: Rich Media Document (With Charts & Tables)

```python
# 1. Create
creator.create_document(...)

# 2. Layout
layout.set_page_layout(...)

# 3. Insert
content.insert_chart(...)
content.insert_table(...)

# 4. Edit
writer.edit_document(...)
```

### Workflow 4: AI Intelligent Document (Fully Automated)

```python
# One-click completion
orchestrator.create_rich_document(
    document_template="business_report",
    content_plan={...},
    layout_config={...},
    ai_assistance=True
)
```

---

## 📊 Feature Comparison

| Feature | Creator | Layout | Content | Writer | Orchestrator |
|---------|---------|--------|---------|--------|--------------|
| Create Document | ✅ | ❌ | ❌ | ❌ | ✅ |
| Template Management | ✅ | ❌ | ❌ | ❌ | ✅ |
| Page Layout | ❌ | ✅ | ❌ | ❌ | ✅ |
| Multi-Column Layout | ❌ | ✅ | ❌ | ❌ | ✅ |
| Insert Chart | ❌ | ❌ | ✅ | ❌ | ✅ |
| Insert Table | ❌ | ❌ | ✅ | ❌ | ✅ |
| Text Editing | ❌ | ❌ | ❌ | ✅ | ✅ |
| AI Enhancement | ❌ | ❌ | ❌ | ❌ | ✅ |
| Standalone Use | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🎨 Supported Formats

### Output Formats (11 types)
- Text: TXT, MARKDOWN, HTML, XML
- Office: DOCX, XLSX, PDF
- Data: JSON, YAML, CSV
- Other: LATEX, BINARY

### Chart Types (10 types)
- Basic: bar, line, pie
- Analysis: scatter, histogram, box
- Advanced: heatmap, area, bubble, gantt

### Table Styles (8 types)
- default, simple, grid, striped
- bordered, corporate, academic, minimal

### Document Templates (9 types)
- blank, business_report, technical_doc
- academic_paper, project_proposal, user_manual
- presentation, newsletter, invoice

### Layout Presets (10 types)
- default, academic_paper, business_report
- magazine, newspaper, presentation
- technical_doc, letter, invoice, brochure

---

## ⚙️ Configuration Options

### Page Sizes
- A4, A3, A5
- Letter, Legal, Tabloid
- Custom

### Page Orientation
- Portrait (vertical)
- Landscape (horizontal)

### Alignment
- Left, Center, Right
- Justify

### Image Alignment
- left, center, right
- inline, float_left, float_right

### Write Modes (9 types)
- create, overwrite, append, update
- backup_write, version_write
- insert, replace, delete

---

## 💡 Practical Tips

### Tip 1: Choose the Right Tool

- **Simple text**? → DocumentWriterTool
- **Need layout**? → DocumentLayoutTool
- **Have charts/tables**? → ContentInsertionTool
- **Complex document**? → AIDocumentWriterOrchestrator
- **Create from scratch**? → DocumentCreatorTool

### Tip 2: Use Templates

```python
# Don't start from blank
creator.create_document(template_type="blank", ...)  # ❌

# Use appropriate template
creator.create_document(template_type="business_report", ...)  # ✅
```

### Tip 3: Batch Operations

```python
# Don't insert one by one
for item in items:
    content.insert_chart(...)  # ❌

# Use batch insertion
content.batch_insert_content(content_items=items)  # ✅
```

### Tip 4: Enable Backup

```python
# Backup before dangerous operations
writer.write_document(..., mode="backup_write")  # ✅
```

### Tip 5: Use AI Optimization

```python
# Manual optimization is tedious
writer.edit_document(...)
writer.find_replace(...)
writer.format_text(...)  # ❌

# AI one-click optimization
orchestrator.ai_edit_document(operation="smart_format", ...)  # ✅
```

---

## 🔍 Common Questions

### Q: How to choose which tool to use?
**A**: 
- Simple task → Use single tool
- Complex task → Use Orchestrator
- Not sure → Use Orchestrator

### Q: How do tools work together?
**A**: 
- Can be used independently
- Can be used in combination
- Orchestrator automatically coordinates

### Q: Which cloud storage is supported?
**A**: 
- Google Cloud Storage (gs://)
- AWS S3 (s3://)
- Azure Blob Storage (azure://)
- Generic storage ID

### Q: How to handle large files?
**A**: 
- Enable streaming processing
- Use batch operations
- Configure memory optimization

### Q: What's needed for AI features?
**A**: 
- AIECS client configuration
- AI Provider settings
- Optional (has fallback)

---

## 📚 More Resources

- **Detailed Architecture**: [DOCUMENT_CREATION_ARCHITECTURE.md](./DOCUMENT_CREATION_ARCHITECTURE.md)
- **Complete Examples**: See [DOCUMENT_CREATION_ARCHITECTURE.md](./DOCUMENT_CREATION_ARCHITECTURE.md) for detailed examples
- **Tool Documentation**: See individual tool documentation files in this directory

---

## 🎯 Quick Reference Code Snippets

### Create Business Report
```python
creator = DocumentCreatorTool()
creator.create_document(
    document_type="report",
    template_type="business_report",
    output_format="markdown",
    metadata={"title": "Q4 Report"}
)
```

### Add Chart
```python
content = ContentInsertionTool()
content.insert_chart(
    document_path="report.md",
    chart_data={"labels": ["Q1", "Q2"], "values": [100, 150]},
    chart_type="bar",
    position={"line": 10}
)
```

### AI Optimize Document
```python
orchestrator = AIDocumentWriterOrchestrator()
orchestrator.optimize_document_layout(
    document_path="report.md",
    optimization_goals=["professional", "readability"]
)
```

### Batch Content
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

**Tip**: Remember this architecture = "5 independent tools + 1 AI orchestrator" ✨
