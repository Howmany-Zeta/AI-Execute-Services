# AIECS 依赖检查系统实现总结

## 概述

基于 `/home/coder1/python-middleware-dev/docs/TOOLS_USED_INSTRUCTION/TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md` 文档中的工具特殊使用说明，我们为 AIECS 包实现了一个全面的依赖检查系统。

## 实现的功能

### 1. 综合依赖检查脚本 (`dependency_checker.py`)

**功能**:
- 检查所有 AIECS 工具的系统级依赖、Python包依赖和模型文件
- 支持 6 个主要工具：Image Tool、ClassFire Tool、Office Tool、Stats Tool、Report Tool、Scraper Tool
- 生成详细的依赖状态报告
- 提供安装命令和影响说明

**特点**:
- 跨平台支持 (Linux、macOS、Windows)
- 详细的错误处理和日志记录
- 可扩展的架构，易于添加新工具

### 2. 快速依赖检查脚本 (`quick_dependency_check.py`)

**功能**:
- 快速检查关键依赖项
- 适合安装后验证
- 生成简洁的状态报告
- 提供基本的安装命令

**特点**:
- 轻量级，执行速度快
- 专注于关键依赖
- 适合自动化场景

### 3. 自动依赖修复脚本 (`dependency_fixer.py`)

**功能**:
- 自动安装缺失的依赖项
- 支持交互和非交互模式
- 智能的依赖分组和安装顺序
- 详细的修复报告

**特点**:
- 用户友好的确认机制
- 支持多种包管理器 (apt、brew、pip)
- 完整的错误处理和回滚

### 4. 集成到安装流程

**setup.py 更新**:
- 在 `run_post_install()` 函数中集成依赖检查
- 添加了 3 个新的命令行工具入口点
- 提供安装后的自动验证

**命令行工具**:
- `aiecs-check-deps`: 完整依赖检查
- `aiecs-quick-check`: 快速依赖检查  
- `aiecs-fix-deps`: 自动依赖修复

## 支持的依赖类型

### 系统级依赖

1. **Java 运行时环境** (Office Tool)
   - 用于 Apache Tika 文档解析
   - 支持 OpenJDK 11+

2. **Tesseract OCR 引擎** (Image Tool, Office Tool)
   - 图像文字识别
   - 支持多语言包

3. **图像处理库** (Image Tool, Report Tool)
   - libjpeg, libpng, libtiff 等
   - Pillow 系统依赖

4. **统计文件格式库** (Stats Tool)
   - libreadstat (SAS/SPSS/Stata 文件)
   - Excel 处理库

5. **PDF 生成库** (Report Tool)
   - WeasyPrint 系统依赖
   - cairo, pango, gdk-pixbuf 等

6. **浏览器自动化库** (Scraper Tool)
   - Playwright 浏览器二进制文件
   - 系统图形库

### Python 包依赖

- **核心框架**: FastAPI, uvicorn, pydantic, httpx
- **任务队列**: celery, redis
- **数据处理**: pandas, numpy, scipy, scikit-learn
- **文档处理**: python-docx, python-pptx, openpyxl, pdfplumber
- **NLP 处理**: spacy, transformers, nltk
- **图像处理**: pillow, pytesseract
- **网页抓取**: playwright, scrapy, beautifulsoup4
- **报告生成**: jinja2, matplotlib, weasyprint

### 模型文件依赖

1. **spaCy 模型**
   - en_core_web_sm (英文)
   - zh_core_web_sm (中文)

2. **Transformers 模型**
   - facebook/bart-large-cnn (英文摘要)
   - t5-base (多语言摘要)

3. **NLTK 数据包**
   - stopwords, punkt, wordnet, averaged_perceptron_tagger

4. **Playwright 浏览器**
   - Chromium, Firefox, WebKit

## 安装后自动检查流程

当用户运行 `pip install aiecs` 时：

1. **Weasel 库补丁应用**
   - 修复 weasel 库的验证问题
   - 确保 spaCy 配置正常工作

2. **NLP 数据下载**
   - 下载 NLTK 数据包
   - 下载 spaCy 模型

3. **系统依赖检查**
   - 运行快速依赖检查
   - 显示缺失的依赖项
   - 提供安装指导

4. **安装总结**
   - 显示所有步骤的状态
   - 提供后续操作建议

## 使用方法

### 安装后验证

```bash
# 快速检查
aiecs-quick-check

# 完整检查
aiecs-check-deps

# 自动修复
aiecs-fix-deps
```

### 开发环境设置

```bash
# 检查所有依赖
aiecs-check-deps

# 自动修复缺失依赖
aiecs-fix-deps --non-interactive

# 仅检查不修复
aiecs-fix-deps --check-only
```

## 故障排除

### 常见问题解决

1. **Java 未安装**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install openjdk-11-jdk
   
   # macOS
   brew install openjdk@11
   ```

2. **Tesseract OCR 未安装**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-eng
   
   # macOS
   brew install tesseract
   ```

3. **spaCy 模型未下载**
   ```bash
   python -m spacy download en_core_web_sm
   python -m spacy download zh_core_web_sm
   ```

4. **Playwright 浏览器未安装**
   ```bash
   playwright install
   ```

## 扩展性

### 添加新工具依赖检查

1. 在 `DependencyChecker` 类中添加新的检查方法
2. 在 `check_all_dependencies()` 中注册新工具
3. 更新安装命令映射

### 自定义检查逻辑

```python
from aiecs.scripts.dependency_checker import DependencyChecker

checker = DependencyChecker()
tools = checker.check_all_dependencies()
report = checker.generate_report(tools)
```

## 文件结构

```
aiecs/scripts/
├── dependency_checker.py          # 完整依赖检查
├── quick_dependency_check.py      # 快速依赖检查
├── dependency_fixer.py            # 自动依赖修复
├── test_dependency_checker.py     # 测试脚本
├── README_DEPENDENCY_CHECKER.md   # 使用说明
└── DEPENDENCY_SYSTEM_SUMMARY.md   # 系统总结
```

## 总结

这个依赖检查系统解决了 AIECS 包作为项目依赖时的关键问题：

1. **自动检查**: 安装后自动验证所有依赖
2. **详细报告**: 清楚显示缺失的依赖和影响
3. **自动修复**: 提供一键修复功能
4. **跨平台支持**: 支持主流操作系统
5. **易于扩展**: 可以轻松添加新工具的依赖检查

通过这个系统，用户可以在安装 AIECS 后立即了解哪些功能可用，哪些需要额外安装依赖，以及如何获得这些依赖。这大大提高了用户体验和包的可用性。





