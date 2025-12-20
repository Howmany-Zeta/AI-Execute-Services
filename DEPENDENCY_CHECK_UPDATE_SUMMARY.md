# 依赖检查器更新总结

## 📊 更新概况

### 更新前状态
- **工具总数**: 30个
- **已覆盖**: 6个工具 (20%)
- **未覆盖**: 24个工具 (80%)

### 更新后状态
- **工具总数**: 30个
- **已覆盖**: 12个工具 (40%) ✅
- **未覆盖**: 18个工具 (60%)

### 覆盖率提升
- **提升**: +20% (从20%提升到40%)
- **新增检查**: 6个工具

---

## ✅ 本次更新内容

### 1. ClassifierTool 依赖优化

#### 变更内容
将 `transformers` 和 `torch` 从核心依赖改为**可选依赖**：

**修改前:**
```python
python_packages = [
    "spacy",
    "transformers",  # 核心依赖
    "nltk",
    "rake_nltk",
    "spacy_pkuseg",
]
```

**修改后:**
```python
# 核心依赖 (必须)
core_packages = ["spacy", "nltk", "rake_nltk"]

# 可选依赖
optional_packages = {
    "transformers": "Text summarization (BART/T5 models)",
    "torch": "Backend for transformers (PyTorch)",
    "spacy_pkuseg": "Advanced Chinese text segmentation",
}
```

#### 影响分析

| 功能 | transformers/torch | 替代方案 |
|------|-------------------|---------|
| 文本分类 | ❌ 不需要 | spaCy + 词典 |
| 分词 | ❌ 不需要 | spaCy |
| 词性标注 | ❌ 不需要 | spaCy |
| 命名实体识别 | ❌ 不需要 | spaCy |
| 关键词提取 | ❌ 不需要 | RAKE + spaCy |
| **文本摘要** | ✅ **需要** | 可降级到提取式摘要 |

#### 资源对比

```bash
# 最小安装 (不含 transformers/torch)
磁盘占用: ~200MB
内存占用: ~500MB
启动时间: ~2秒

# 完整安装 (含 transformers/torch)
磁盘占用: ~3-5GB
内存占用: ~2-4GB
启动时间: ~10-20秒
```

### 2. 新增工具依赖检查

#### 新增的6个工具检查方法

1. **ChartTool** (`check_chart_tool_dependencies`)
   - 系统依赖: Matplotlib系统库
   - Python包: pandas, matplotlib, seaborn, plotly

2. **PandasTool** (`check_pandas_tool_dependencies`)
   - Python包: pandas, numpy

3. **DocumentParserTool** (`check_document_parser_tool_dependencies`)
   - 系统依赖: Java JRE, Tesseract OCR
   - Python包: pdfplumber, python-docx, python-pptx, openpyxl, pytesseract, PIL, beautifulsoup4, lxml

4. **DataLoaderTool** (`check_data_loader_tool_dependencies`)
   - 系统依赖: libreadstat
   - Python包: pandas, numpy, pyreadstat, openpyxl, pyarrow

5. **DataVisualizerTool** (`check_data_visualizer_tool_dependencies`)
   - 系统依赖: Matplotlib系统库
   - Python包: pandas, numpy, matplotlib, seaborn, plotly

6. **ModelTrainerTool** (`check_model_trainer_tool_dependencies`)
   - Python包: pandas, numpy, scikit-learn, xgboost, lightgbm

---

## 📋 当前依赖检查覆盖情况

### 已覆盖的12个工具 ✅

| # | 工具名 | 注册名 | 系统依赖 | 检查方法 |
|---|--------|--------|---------|---------|
| 1 | ImageTool | image | Tesseract, PIL库 | `check_image_tool_dependencies()` |
| 2 | ClassifierTool | classifier | spaCy模型, NLTK数据 | `check_classfire_tool_dependencies()` |
| 3 | OfficeTool | office | Java, Tesseract | `check_office_tool_dependencies()` |
| 4 | StatsTool | stats | libreadstat | `check_stats_tool_dependencies()` |
| 5 | ReportTool | report | WeasyPrint库 | `check_report_tool_dependencies()` |
| 6 | ScraperTool | scraper | Playwright浏览器 | `check_scraper_tool_dependencies()` |
| 7 | **ChartTool** | chart | Matplotlib库 | `check_chart_tool_dependencies()` ⭐ 新增 |
| 8 | **PandasTool** | pandas | 无 | `check_pandas_tool_dependencies()` ⭐ 新增 |
| 9 | **DocumentParserTool** | document_parser | Java, Tesseract | `check_document_parser_tool_dependencies()` ⭐ 新增 |
| 10 | **DataLoaderTool** | data_loader | libreadstat | `check_data_loader_tool_dependencies()` ⭐ 新增 |
| 11 | **DataVisualizerTool** | data_visualizer | Matplotlib库 | `check_data_visualizer_tool_dependencies()` ⭐ 新增 |
| 12 | **ModelTrainerTool** | model_trainer | 无 | `check_model_trainer_tool_dependencies()` ⭐ 新增 |

### 未覆盖的18个工具 ❌

#### 基础工具 (1个)
- ResearchTool

#### 文档处理工具 (6个)
- DocumentCreatorTool
- DocumentWriterTool
- DocumentLayoutTool
- ContentInsertionTool
- AIDocumentOrchestrator
- AIDocumentWriterOrchestrator

#### 统计分析工具 (6个)
- DataTransformerTool
- DataProfilerTool
- StatisticalAnalyzerTool
- AIInsightGeneratorTool
- AIReportOrchestratorTool
- AIDataAnalysisOrchestrator

#### 知识图谱工具 (3个)
- KnowledgeGraphBuilderTool
- GraphSearchTool
- GraphReasoningTool

#### API和搜索工具 (2个)
- APISourceTool
- SearchTool

---

## 🎯 使用方式

### 运行依赖检查

```bash
# 方式1: 直接运行脚本
cd /home/coder1/python-middleware-dev
python aiecs/scripts/dependance_check/dependency_checker.py

# 方式2: 使用模块方式
python -m aiecs.scripts.dependance_check.dependency_checker

# 方式3: 如果已安装为命令
aiecs-check-dependencies
```

### 检查输出示例

```
🔍 Checking AIECS dependencies...
This may take a few minutes for model checks...

================================================================================
AIECS DEPENDENCY CHECK REPORT
================================================================================
System: Linux x86_64
Python: 3.10
Package Manager: apt-get

🔧 CLASSIFIER TOOL
----------------------------------------
📦 System Dependencies:
  (No system dependencies)

🐍 Python Dependencies:
  ✅ spacy: available
  ✅ nltk: available
  ✅ rake_nltk: available

🤖 Model Dependencies:
  ✅ spaCy en_core_web_sm: available
  ⚠️  spaCy zh_core_web_sm: missing
     Install: python -m spacy download zh_core_web_sm
     Impact: Text processing in zh language will be unavailable

🔧 Optional Dependencies:
  ❌ transformers: missing
     Install: pip install transformers
     Impact: Text summarization (BART/T5 models) will be unavailable
  ❌ torch: missing
     Install: pip install torch (or pip install aiecs[summarization])
     Impact: Backend for transformers (PyTorch) will be unavailable
  ⚠️  spacy_pkuseg: missing
     Install: pip install spacy_pkuseg
     Impact: Advanced Chinese text segmentation will be unavailable

...

================================================================================
SUMMARY
================================================================================
Total Issues: 15
Critical Issues: 3
Optional Issues: 12

⚠️  Some critical dependencies are missing.
Please install the missing dependencies to enable full functionality.
```

---

## 📈 依赖统计

### 系统级依赖需求统计

| 系统依赖 | 需要的工具数量 | 工具列表 |
|---------|--------------|---------|
| **Tesseract OCR** | 3 | ImageTool, OfficeTool, DocumentParserTool |
| **Java JRE** | 2 | OfficeTool, DocumentParserTool |
| **Playwright 浏览器** | 1 | ScraperTool |
| **PIL/Pillow 系统库** | 6 | ImageTool, OfficeTool, ReportTool, ChartTool, DataVisualizerTool, DocumentParserTool |
| **WeasyPrint 系统库** | 1 | ReportTool |
| **libreadstat** | 2 | StatsTool, DataLoaderTool |
| **Matplotlib 系统库** | 3 | ReportTool, ChartTool, DataVisualizerTool |

### Python包依赖需求统计

| Python包 | 需要的工具数量 | 是否可选 |
|---------|--------------|---------|
| **pandas** | 7 | 核心依赖 |
| **numpy** | 7 | 核心依赖 |
| **matplotlib** | 3 | 核心依赖 |
| **seaborn** | 2 | 可选依赖 |
| **plotly** | 2 | 可选依赖 |
| **scikit-learn** | 2 | 核心依赖 |
| **transformers** | 1 | ⭐ **可选依赖** |
| **torch** | 1 | ⭐ **可选依赖** |
| **spacy** | 1 | 核心依赖 |
| **openpyxl** | 4 | 核心依赖 |

---

## 🔄 下一步计划

### 短期目标 (优先级高)
添加以下工具的依赖检查：

1. **DocumentCreatorTool** - 需要 WeasyPrint系统库
2. **ResearchTool** - 需要 httpx, beautifulsoup4
3. **DataTransformerTool** - 需要 pandas, sklearn
4. **DataProfilerTool** - 需要 pandas, numpy
5. **StatisticalAnalyzerTool** - 需要 scipy, statsmodels

### 中期目标
添加知识图谱和API工具：

1. **KnowledgeGraphBuilderTool** - 需要 networkx
2. **GraphSearchTool** - 需要 networkx
3. **GraphReasoningTool** - 需要 networkx
4. **APISourceTool** - 需要 httpx, requests
5. **SearchTool** - 需要 google-api-python-client

### 长期目标
完善编排工具的依赖检查（通过检查其依赖的基础工具）。

---

## 📝 相关文档

- **系统依赖汇总**: `/home/coder1/python-middleware-dev/SYSTEM_DEPENDENCIES_SUMMARY.md`
- **所有工具列表**: `/home/coder1/python-middleware-dev/ALL_TOOLS_LIST.md`
- **依赖检查器**: `/home/coder1/python-middleware-dev/aiecs/scripts/dependance_check/dependency_checker.py`
- **依赖检查README**: `/home/coder1/python-middleware-dev/aiecs/scripts/dependance_check/README_DEPENDENCY_CHECKER.md`

---

## 🎉 总结

### 主要成果

1. ✅ **ClassifierTool优化**: 将 transformers/torch 改为可选依赖
   - 减少核心依赖体积 ~3-5GB
   - 保持核心功能完整
   - 提供降级方案

2. ✅ **覆盖率提升**: 从20%提升到40%
   - 新增6个工具的依赖检查
   - 覆盖更多关键工具

3. ✅ **文档完善**: 创建3份详细文档
   - 系统依赖汇总
   - 所有工具列表
   - 更新总结

### 用户影响

**正面影响:**
- 🎯 更清晰的依赖关系
- 📦 更小的最小安装体积
- 🚀 更快的启动速度
- 📊 更完整的依赖检查

**注意事项:**
- ⚠️ 使用 `summarize` 功能需要安装 `transformers` 和 `torch`
- 💡 可通过 `pip install aiecs[summarization]` 安装可选依赖

---

**文档版本**: 1.0  
**最后更新**: 2025-12-20  
**维护者**: AIECS Development Team

