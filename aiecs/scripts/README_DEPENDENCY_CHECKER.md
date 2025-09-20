# AIECS Dependency Checker

AIECS 包含一个全面的依赖检查系统，用于验证所有工具所需的系统级依赖、Python包和模型文件。

## 概述

AIECS 的各个工具需要不同的依赖项才能正常工作：

- **系统级依赖**: Java、Tesseract OCR、图像处理库等
- **Python包依赖**: 各种Python库和框架
- **模型文件**: spaCy模型、NLTK数据、Transformers模型等

## 命令行工具

### 1. 快速依赖检查

```bash
aiecs-quick-check
```

快速检查关键依赖项，适合安装后验证。

### 2. 完整依赖检查

```bash
aiecs-check-deps
```

执行完整的依赖检查，包括所有工具的所有依赖项。

### 3. 自动依赖修复

```bash
aiecs-fix-deps
```

自动安装缺失的依赖项（需要用户确认）。

```bash
aiecs-fix-deps --non-interactive
```

非交互模式，自动批准所有修复。

### 4. 仅检查模式

```bash
aiecs-fix-deps --check-only
```

只检查依赖项，不执行修复。

## 工具特定依赖

### Image Tool (图像处理工具)

**系统依赖**:
- Tesseract OCR 引擎
- Pillow 图像处理库的系统依赖

**Python包**:
- PIL (Pillow)
- pytesseract

**模型文件**:
- Tesseract 语言包 (eng, chi_sim, chi_tra, 等)

**安装命令**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng
sudo apt-get install libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev

# macOS
brew install tesseract
brew install libjpeg zlib libpng libtiff webp openjpeg
```

### ClassFire Tool (文本分类工具)

**Python包**:
- spacy
- transformers
- nltk
- rake_nltk

**模型文件**:
- spaCy 模型: en_core_web_sm, zh_core_web_sm
- Transformers 模型: facebook/bart-large-cnn, t5-base
- NLTK 数据: stopwords, punkt, wordnet, averaged_perceptron_tagger

**安装命令**:
```bash
# spaCy 模型
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm

# NLTK 数据
python -c "import nltk; nltk.download('stopwords')"
python -c "import nltk; nltk.download('punkt')"
python -c "import nltk; nltk.download('wordnet')"
python -c "import nltk; nltk.download('averaged_perceptron_tagger')"
```

### Office Tool (办公文档处理工具)

**系统依赖**:
- Java 运行时环境 (OpenJDK 11+)
- Tesseract OCR (可选)

**Python包**:
- tika
- python-docx
- python-pptx
- openpyxl
- pdfplumber
- pytesseract
- PIL

**安装命令**:
```bash
# Ubuntu/Debian
sudo apt-get install openjdk-11-jdk
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install openjdk@11
brew install tesseract
```

### Stats Tool (统计分析工具)

**系统依赖**:
- libreadstat (用于SAS/SPSS/Stata文件)
- Excel处理库

**Python包**:
- pandas
- numpy
- scipy
- scikit-learn
- statsmodels
- pyreadstat
- openpyxl

**安装命令**:
```bash
# Ubuntu/Debian
sudo apt-get install libreadstat-dev
sudo apt-get install libxml2-dev libxslt1-dev

# macOS
brew install readstat
brew install libxml2 libxslt
```

### Report Tool (报告生成工具)

**系统依赖**:
- WeasyPrint 依赖 (PDF生成)
- Matplotlib 依赖 (图表生成)

**Python包**:
- jinja2
- matplotlib
- weasyprint
- bleach
- markdown
- pandas
- openpyxl
- python-docx
- python-pptx

**安装命令**:
```bash
# Ubuntu/Debian
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
sudo apt-get install libfreetype6-dev libpng-dev libjpeg-dev libtiff-dev libwebp-dev

# macOS
brew install cairo pango gdk-pixbuf libffi
brew install freetype libpng libjpeg libtiff webp
```

### Scraper Tool (网页抓取工具)

**系统依赖**:
- Playwright 浏览器二进制文件
- Playwright 系统依赖

**Python包**:
- playwright
- scrapy
- httpx
- beautifulsoup4
- lxml

**安装命令**:
```bash
# 安装 Playwright 浏览器
playwright install

# 安装系统依赖
playwright install-deps
```

## 安装后自动检查

当您安装 AIECS 时，系统会自动运行依赖检查：

```bash
pip install aiecs
```

安装过程中会显示：
1. Weasel 库补丁应用
2. NLP 数据下载
3. 系统依赖检查

## 故障排除

### 常见问题

1. **Java 未安装**
   ```bash
   # 检查 Java 版本
   java -version
   
   # 安装 Java
   sudo apt-get install openjdk-11-jdk  # Ubuntu/Debian
   brew install openjdk@11              # macOS
   ```

2. **Tesseract OCR 未安装**
   ```bash
   # 检查 Tesseract
   tesseract --version
   
   # 安装 Tesseract
   sudo apt-get install tesseract-ocr tesseract-ocr-eng  # Ubuntu/Debian
   brew install tesseract                                # macOS
   ```

3. **spaCy 模型未下载**
   ```bash
   # 下载 spaCy 模型
   python -m spacy download en_core_web_sm
   python -m spacy download zh_core_web_sm
   ```

4. **Playwright 浏览器未安装**
   ```bash
   # 安装 Playwright 浏览器
   playwright install
   ```

### 手动修复

如果自动修复失败，您可以手动安装缺失的依赖：

1. 运行完整检查：
   ```bash
   aiecs-check-deps
   ```

2. 根据报告中的安装命令手动安装

3. 重新运行检查验证

### 日志文件

依赖检查会生成以下日志文件：
- `dependency_check.log` - 详细检查日志
- `dependency_fix.log` - 修复过程日志
- `dependency_report.txt` - 检查报告

## 开发人员说明

### 添加新的依赖检查

1. 在 `dependency_checker.py` 中添加新的检查函数
2. 在相应的工具依赖检查函数中调用
3. 更新安装命令映射

### 自定义检查

您可以创建自定义的依赖检查脚本：

```python
from aiecs.scripts.dependency_checker import DependencyChecker

checker = DependencyChecker()
tools = checker.check_all_dependencies()
report = checker.generate_report(tools)
print(report)
```

## 支持

如果您遇到依赖问题，请：

1. 运行 `aiecs-check-deps` 获取详细报告
2. 查看生成的日志文件
3. 尝试使用 `aiecs-fix-deps` 自动修复
4. 如果问题仍然存在，请提交 issue 到项目仓库





