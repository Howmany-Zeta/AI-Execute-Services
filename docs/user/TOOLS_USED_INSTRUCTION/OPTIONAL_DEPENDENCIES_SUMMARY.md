# AIECS 工具可选依赖总结

## 📊 概览

本文档总结了 AIECS 项目中各工具的**可选依赖**情况，帮助用户根据实际需求选择性安装。

## 🎯 可选依赖原则

**可选依赖**是指：
- ✅ 不影响工具的核心功能
- ✅ 仅在使用特定高级功能时需要
- ✅ 通常有复杂的系统级依赖或较大的安装体积
- ✅ 可以在需要时按需安装

## 🔍 已识别的可选依赖工具

### 1. ClassFire Tool (文本分类与 NLP)

#### 核心功能 ✅
- ✅ 文本分类 (spaCy)
- ✅ 分词 (spaCy)
- ✅ 词性标注 (spaCy)
- ✅ 命名实体识别 (spaCy)
- ✅ 词形还原 (spaCy)
- ✅ 依存句法分析 (spaCy)
- ✅ 关键词提取 (RAKE-NLTK)

#### 可选功能 ⚠️

| 功能 | 依赖包 | 用途 | 影响 |
|------|--------|------|------|
| **文本摘要** | `transformers` | 使用 BART/T5 模型进行深度学习摘要 | 高质量摘要生成不可用 |
| **模型后端** | `torch` | Transformers 的 PyTorch 后端 | 摘要功能依赖此包 |
| **中文分词** | `spacy_pkuseg` | 高级中文文本分词 | 使用默认分词器替代 |

#### 可选模型 ⚠️

| 模型 | 用途 | 下载方式 |
|------|------|---------|
| `facebook/bart-large-cnn` | 英文文本摘要 | 首次使用时自动下载 |
| `t5-base` | 多语言文本摘要 | 首次使用时自动下载 |
| `zh_core_web_sm` | 中文 NLP 处理 | `python -m spacy download zh_core_web_sm` |

#### 核心依赖
```bash
pip install spacy nltk rake-nltk
python -m spacy download en_core_web_sm
python -m nltk.downloader stopwords punkt wordnet averaged_perceptron_tagger
```

#### 完整依赖（包含可选）
```bash
# 核心依赖
pip install spacy nltk rake-nltk
python -m spacy download en_core_web_sm

# 可选依赖
pip install transformers torch spacy_pkuseg
python -m spacy download zh_core_web_sm
```

---

### 2. Report Tool (多格式报告生成)

#### 核心功能 ✅
- ✅ HTML 报告 (Jinja2 + Bleach)
- ✅ Excel 报告 (Pandas + OpenPyXL)
- ✅ PowerPoint 报告 (python-pptx)
- ✅ Markdown 报告 (Jinja2 + Markdown)
- ✅ Word 报告 (python-docx)
- ✅ 图表生成 (Matplotlib)

#### 可选功能 ⚠️

| 功能 | 依赖包 | 系统依赖 | 状态 | 影响 |
|------|--------|----------|------|------|
| **PDF 生成** | `weasyprint` | Cairo, Pango, GDK-Pixbuf, libffi | 🚫 **已禁用** | PDF 生成不可用（计划未来重新启用） |

#### 系统依赖详情

**WeasyPrint 系统库** (Ubuntu/Debian):
```bash
sudo apt-get install \
  libcairo2-dev \
  libpango1.0-dev \
  libgdk-pixbuf2.0-dev \
  libffi-dev \
  shared-mime-info
```

**WeasyPrint 系统库** (macOS):
```bash
brew install cairo pango gdk-pixbuf libffi
```

#### 核心依赖
```bash
pip install jinja2 matplotlib bleach markdown pandas openpyxl python-docx python-pptx
```

#### 完整依赖（包含可选 - 未来）
```bash
# 核心依赖
pip install jinja2 matplotlib bleach markdown pandas openpyxl python-docx python-pptx

# 系统依赖（Ubuntu/Debian）
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info

# 可选依赖（当前已禁用）
pip install weasyprint
```

---

## 📈 安装策略推荐

### 🥉 最小安装（仅核心功能）

```bash
# ClassFire Tool - 基础 NLP
pip install spacy nltk rake-nltk
python -m spacy download en_core_web_sm

# Report Tool - 6种格式报告
pip install jinja2 matplotlib bleach markdown pandas openpyxl python-docx python-pptx
```

**适用场景**:
- 快速原型开发
- 资源受限环境
- 只需要基础功能

### 🥈 标准安装（核心 + 常用可选）

```bash
# ClassFire Tool - 添加摘要功能
pip install spacy nltk rake-nltk transformers torch
python -m spacy download en_core_web_sm

# Report Tool - 保持核心依赖
pip install jinja2 matplotlib bleach markdown pandas openpyxl python-docx python-pptx
```

**适用场景**:
- 生产环境
- 需要文本摘要功能
- 不需要 PDF 生成

### 🥇 完整安装（所有依赖）

```bash
# ClassFire Tool - 全功能
pip install spacy nltk rake-nltk transformers torch spacy_pkuseg
python -m spacy download en_core_web_sm zh_core_web_sm

# Report Tool - 系统依赖 + 全功能
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
pip install jinja2 matplotlib bleach markdown pandas openpyxl python-docx python-pptx weasyprint
```

**适用场景**:
- 全功能开发环境
- 需要所有高级功能
- 多语言支持需求
- 未来需要 PDF 生成（待启用）

---

## 🔍 可选依赖检查

使用依赖检查脚本查看当前环境的依赖状态：

```bash
cd /home/coder1/python-middleware-dev
python aiecs/scripts/dependance_check/dependency_checker.py
```

### 输出示例

```
📊 ClassFire Tool
==================================================

🖥️  系统依赖: 0 个

🐍 Python 依赖: 3 个
  ✅ spacy: available
  ✅ nltk: available
  ✅ rake_nltk: available

📦 模型依赖: 5 个
  ✅ spaCy en_core_web_sm: available
  ❌ spaCy zh_core_web_sm: missing
  ✅ NLTK stopwords: available
  ✅ NLTK punkt: available
  ✅ NLTK wordnet: available

🔧 可选依赖: 5 个
  ⚠️  transformers: missing
     影响: Text summarization functionality will be unavailable
  ⚠️  torch: missing
     影响: Backend for transformers (PyTorch) functionality will be unavailable
  ⚠️  spacy_pkuseg: missing
     影响: Advanced Chinese text segmentation functionality will be unavailable
  ⚠️  Transformers facebook/bart-large-cnn: missing
     影响: Text summarization with facebook/bart-large-cnn will be unavailable
  ⚠️  Transformers t5-base: missing
     影响: Text summarization with t5-base will be unavailable

---

📊 Report Tool
==================================================

🖥️  系统依赖: 1 个
  ✅ Matplotlib System Libraries: available

🐍 Python 依赖: 8 个
  ✅ jinja2: available
  ✅ matplotlib: available
  ✅ bleach: available
  ✅ markdown: available
  ✅ pandas: available
  ✅ openpyxl: available
  ✅ python-docx: available
  ✅ python-pptx: available

🔧 可选依赖: 2 个
  ⚠️  WeasyPrint System Libraries: missing
     描述: System libraries for PDF generation (cairo, pango, etc.) - currently disabled
     影响: PDF generation functionality is currently disabled (will be re-enabled in future release)
     安装: sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
  ⚠️  weasyprint: missing
     描述: Python package: weasyprint (HTML to PDF conversion) - currently disabled
     影响: PDF generation functionality is currently disabled (will be re-enabled in future release)
     安装: pip install weasyprint
```

---

## 📊 依赖对比表

| 工具 | 核心 Python 包 | 核心模型 | 可选 Python 包 | 可选模型 | 系统依赖 |
|------|---------------|---------|---------------|---------|---------|
| **ClassFire Tool** | 3 | 4 (NLTK) | 2 | 3 (spaCy + Transformers) | 0 |
| **Report Tool** | 8 | 0 | 1 | 0 | 1 (可选) |

---

## 💡 关键发现

### ClassFire Tool
- ✅ **核心功能完整**: 无需 transformers/torch 即可进行 NLP 处理
- ✅ **摘要功能可选**: transformers 仅用于深度学习摘要
- ✅ **懒加载设计**: 只有调用 `summarize()` 方法时才导入
- ✅ **优雅降级**: 缺少可选依赖时会抛出清晰的错误信息

### Report Tool
- ✅ **6种格式支持**: 无需 weasyprint 即可生成多种格式
- ✅ **PDF 功能已禁用**: 因部署复杂性暂时关闭
- ✅ **HTML 替代方案**: 可使用 `generate_html()` 生成 HTML 后手动转 PDF
- ✅ **未来可扩展**: 预留接口，待解决部署问题后重新启用

---

## 🚀 最佳实践

### 1. **按需安装**
```bash
# 只安装你需要的功能
pip install spacy nltk rake-nltk  # ClassFire 基础功能
pip install transformers torch     # 添加摘要功能
```

### 2. **环境隔离**
```bash
# 使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. **依赖版本锁定**
```bash
# 生成精确的依赖列表
pip freeze > requirements-lock.txt
```

### 4. **定期检查**
```bash
# 运行依赖检查器
python aiecs/scripts/dependance_check/dependency_checker.py
```

---

## 📚 相关文档

1. **ClassFire Tool**
   - 源码: `/home/coder1/python-middleware-dev/aiecs/tools/task_tools/classfire_tool.py`
   - 配置文档: `/home/coder1/python-middleware-dev/docs/user/TOOLS_USED_INSTRUCTION/CLASSFIRE_TOOL_CONFIGURATION.md`

2. **Report Tool**
   - 源码: `/home/coder1/python-middleware-dev/aiecs/tools/task_tools/report_tool.py`
   - 配置文档: `/home/coder1/python-middleware-dev/docs/user/TOOLS_USED_INSTRUCTION/REPORT_TOOL_CONFIGURATION.md`

3. **依赖检查器**
   - 源码: `/home/coder1/python-middleware-dev/aiecs/scripts/dependance_check/dependency_checker.py`
   - 运行: `python aiecs/scripts/dependance_check/dependency_checker.py`

4. **系统依赖总结**
   - 文档: `/home/coder1/python-middleware-dev/SYSTEM_DEPENDENCIES_SUMMARY.md`

---

## ✅ 更新日志

| 日期 | 工具 | 变更 |
|------|------|------|
| 2025-12-20 | ClassFire Tool | 标记 transformers/torch 为可选依赖 |
| 2025-12-20 | Report Tool | 标记 weasyprint 为可选依赖 |
| 2025-12-20 | Dependency Checker | 添加 optional_deps 支持 |

---

**总结**: 通过合理的可选依赖管理，AIECS 项目实现了**灵活部署**和**按需扩展**，用户可以根据实际需求选择安装级别，既能快速启动又能获得完整功能。

