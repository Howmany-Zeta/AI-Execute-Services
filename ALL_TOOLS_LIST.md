# AIECS 所有工具列表

## 工具统计
- **总计**: 30 个工具
- **依赖检查覆盖**: 6 个工具 (20%)
- **未覆盖**: 24 个工具 (80%)

## 已在依赖检查器中的工具 ✅

| # | 工具名 | 注册名 | 文件路径 | 依赖检查状态 |
|---|--------|--------|----------|------------|
| 1 | ImageTool | image | task_tools/image_tool.py | ✅ 已覆盖 |
| 2 | ClassifierTool | classifier | task_tools/classfire_tool.py | ✅ 已覆盖 |
| 3 | OfficeTool | office | task_tools/office_tool.py | ✅ 已覆盖 |
| 4 | StatsTool | stats | task_tools/stats_tool.py | ✅ 已覆盖 |
| 5 | ReportTool | report | task_tools/report_tool.py | ✅ 已覆盖 |
| 6 | ScraperTool | scraper | task_tools/scraper_tool.py | ✅ 已覆盖 |

## 未在依赖检查器中的工具 ❌

### 基础任务工具 (3个)
| # | 工具名 | 注册名 | 文件路径 | 主要依赖 |
|---|--------|--------|----------|----------|
| 7 | ChartTool | chart | task_tools/chart_tool.py | pandas, matplotlib, seaborn |
| 8 | PandasTool | pandas | task_tools/pandas_tool.py | pandas, numpy |
| 9 | ResearchTool | research | task_tools/research_tool.py | httpx, beautifulsoup4 |

### 文档处理工具 (6个)
| # | 工具名 | 注册名 | 文件路径 | 主要依赖 |
|---|--------|--------|----------|----------|
| 10 | DocumentParserTool | document_parser | docs/document_parser_tool.py | pdfplumber, docx, pptx, pytesseract |
| 11 | DocumentCreatorTool | document_creator | docs/document_creator_tool.py | jinja2, python-docx, python-pptx |
| 12 | DocumentWriterTool | document_writer | docs/document_writer_tool.py | python-docx, python-pptx |
| 13 | DocumentLayoutTool | document_layout | docs/document_layout_tool.py | python-docx, python-pptx |
| 14 | ContentInsertionTool | content_insertion | docs/content_insertion_tool.py | python-docx, python-pptx |
| 15 | AIDocumentOrchestrator | ai_document_orchestrator | docs/ai_document_orchestrator.py | 依赖其他文档工具 |
| 16 | AIDocumentWriterOrchestrator | ai_document_writer_orchestrator | docs/ai_document_writer_orchestrator.py | 依赖其他文档工具 |

### 统计分析工具 (9个)
| # | 工具名 | 注册名 | 文件路径 | 主要依赖 |
|---|--------|--------|----------|----------|
| 17 | DataLoaderTool | data_loader | statistics/data_loader_tool.py | pandas, pyreadstat, openpyxl |
| 18 | DataTransformerTool | data_transformer | statistics/data_transformer_tool.py | pandas, numpy, sklearn |
| 19 | DataProfilerTool | data_profiler | statistics/data_profiler_tool.py | pandas, numpy |
| 20 | DataVisualizerTool | data_visualizer | statistics/data_visualizer_tool.py | matplotlib, seaborn, plotly |
| 21 | ModelTrainerTool | model_trainer | statistics/model_trainer_tool.py | sklearn, xgboost, lightgbm |
| 22 | StatisticalAnalyzerTool | statistical_analyzer | statistics/statistical_analyzer_tool.py | scipy, statsmodels |
| 23 | AIInsightGeneratorTool | ai_insight_generator | statistics/ai_insight_generator_tool.py | pandas, numpy |
| 24 | AIReportOrchestratorTool | ai_report_orchestrator | statistics/ai_report_orchestrator_tool.py | 依赖其他统计工具 |
| 25 | AIDataAnalysisOrchestrator | ai_data_analysis_orchestrator | statistics/ai_data_analysis_orchestrator.py | 依赖其他统计工具 |

### 知识图谱工具 (3个)
| # | 工具名 | 注册名 | 文件路径 | 主要依赖 |
|---|--------|--------|----------|----------|
| 26 | KnowledgeGraphBuilderTool | kg_builder | knowledge_graph/kg_builder_tool.py | networkx, neo4j (optional) |
| 27 | GraphSearchTool | graph_search | knowledge_graph/graph_search_tool.py | networkx |
| 28 | GraphReasoningTool | graph_reasoning | knowledge_graph/graph_reasoning_tool.py | networkx |

### API和搜索工具 (2个)
| # | 工具名 | 注册名 | 文件路径 | 主要依赖 |
|---|--------|--------|----------|----------|
| 29 | APISourceTool | apisource | apisource/tool.py | httpx, requests |
| 30 | SearchTool | search | search_tool/core.py | google-api-python-client |

## 依赖分类统计

### 系统级依赖需求

| 系统依赖 | 需要的工具数量 | 工具列表 |
|---------|--------------|---------|
| Tesseract OCR | 3 | ImageTool, OfficeTool, DocumentParserTool |
| Java JRE | 2 | OfficeTool, DocumentParserTool |
| Playwright 浏览器 | 1 | ScraperTool |
| PIL/Pillow 系统库 | 5 | ImageTool, OfficeTool, ReportTool, ChartTool, DataVisualizerTool |
| WeasyPrint 系统库 | 2 | ReportTool, DocumentCreatorTool |
| libreadstat | 2 | StatsTool, DataLoaderTool |
| 中文字体 | 4 | ReportTool, ChartTool, DataVisualizerTool, DocumentCreatorTool |

### Python包依赖需求

| Python包类别 | 包名 | 需要的工具数量 |
|------------|------|--------------|
| **数据处理** | pandas | 10+ |
| | numpy | 10+ |
| **可视化** | matplotlib | 5 |
| | seaborn | 3 |
| | plotly | 2 |
| **机器学习** | scikit-learn | 4 |
| | xgboost | 1 |
| | lightgbm | 1 |
| **文档处理** | python-docx | 6 |
| | python-pptx | 6 |
| | pdfplumber | 2 |
| | openpyxl | 4 |
| **NLP** | spacy | 1 |
| | transformers | 1 (可选) |
| | nltk | 1 |
| **网络请求** | httpx | 3 |
| | requests | 2 |
| | beautifulsoup4 | 2 |
| | playwright | 1 |
| | scrapy | 1 |
| **统计分析** | scipy | 2 |
| | statsmodels | 2 |
| **知识图谱** | networkx | 3 |
| | neo4j | 1 (可选) |

## 优先级分类

### 核心工具 (高优先级 - 需要系统依赖)
这些工具需要系统级依赖，应该优先在依赖检查器中覆盖：

1. ✅ **ImageTool** - 需要 Tesseract OCR + PIL系统库
2. ✅ **OfficeTool** - 需要 Java + Tesseract + PIL系统库
3. ✅ **ScraperTool** - 需要 Playwright 浏览器
4. ✅ **StatsTool** - 需要 libreadstat
5. ✅ **ReportTool** - 需要 WeasyPrint系统库 + 中文字体
6. ✅ **ClassifierTool** - 需要 spaCy模型 + NLTK数据
7. ❌ **DocumentParserTool** - 需要 Java + Tesseract (依赖 OfficeTool + ImageTool)
8. ❌ **DocumentCreatorTool** - 需要 WeasyPrint系统库 + 中文字体
9. ❌ **ChartTool** - 需要 PIL系统库 + 中文字体
10. ❌ **DataVisualizerTool** - 需要 PIL系统库 + 中文字体
11. ❌ **DataLoaderTool** - 需要 libreadstat

### 标准工具 (中优先级 - 仅Python包)
这些工具只需要Python包，相对简单：

1. ❌ **PandasTool** - pandas, numpy
2. ❌ **DataTransformerTool** - pandas, numpy, sklearn
3. ❌ **DataProfilerTool** - pandas, numpy
4. ❌ **ModelTrainerTool** - sklearn, xgboost, lightgbm
5. ❌ **StatisticalAnalyzerTool** - scipy, statsmodels
6. ❌ **ResearchTool** - httpx, beautifulsoup4
7. ❌ **APISourceTool** - httpx, requests
8. ❌ **SearchTool** - google-api-python-client
9. ❌ **DocumentWriterTool** - python-docx, python-pptx
10. ❌ **DocumentLayoutTool** - python-docx, python-pptx
11. ❌ **ContentInsertionTool** - python-docx, python-pptx
12. ❌ **KnowledgeGraphBuilderTool** - networkx
13. ❌ **GraphSearchTool** - networkx
14. ❌ **GraphReasoningTool** - networkx

### 编排工具 (低优先级 - 依赖其他工具)
这些是高层编排工具，依赖其他基础工具：

1. ❌ **AIDocumentOrchestrator** - 编排文档工具
2. ❌ **AIDocumentWriterOrchestrator** - 编排文档写入
3. ❌ **AIReportOrchestratorTool** - 编排报告生成
4. ❌ **AIDataAnalysisOrchestrator** - 编排数据分析
5. ❌ **AIInsightGeneratorTool** - 生成洞察

## 建议行动

### 立即行动 (高优先级工具)
需要立即添加到依赖检查器的工具：

```python
def check_document_parser_tool_dependencies(self) -> ToolDependencies:
    """依赖 OfficeTool + ImageTool + ScraperTool"""
    
def check_document_creator_tool_dependencies(self) -> ToolDependencies:
    """需要 WeasyPrint系统库 + 中文字体"""
    
def check_chart_tool_dependencies(self) -> ToolDependencies:
    """需要 PIL系统库 + 中文字体 + matplotlib"""
    
def check_data_visualizer_tool_dependencies(self) -> ToolDependencies:
    """需要 PIL系统库 + 中文字体 + matplotlib/seaborn/plotly"""
    
def check_data_loader_tool_dependencies(self) -> ToolDependencies:
    """需要 libreadstat + openpyxl"""
```

### 短期行动 (标准工具)
可以批量添加的纯Python包工具：

```python
def check_pandas_tool_dependencies(self) -> ToolDependencies:
def check_model_trainer_tool_dependencies(self) -> ToolDependencies:
def check_statistical_analyzer_tool_dependencies(self) -> ToolDependencies:
def check_research_tool_dependencies(self) -> ToolDependencies:
def check_apisource_tool_dependencies(self) -> ToolDependencies:
def check_search_tool_dependencies(self) -> ToolDependencies:
def check_knowledge_graph_tools_dependencies(self) -> ToolDependencies:
```

### 长期优化
编排工具的依赖检查可以通过检查其依赖的基础工具来实现。

---

**文档版本**: 1.0  
**最后更新**: 2025-12-20  
**状态**: ❌ 依赖检查覆盖率仅 20% (6/30)

