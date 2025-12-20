# AIECS Tools 系统级依赖汇总

本文档汇总了 `/home/coder1/python-middleware-dev/docs/user/TOOLS_USED_INSTRUCTION` 目录下所有工具需要的系统级依赖。

## 目录
- [1. Tesseract OCR](#1-tesseract-ocr)
- [2. Java Runtime Environment (JRE)](#2-java-runtime-environment-jre)
- [3. Playwright 浏览器](#3-playwright-浏览器)
- [4. 图像处理库](#4-图像处理库)
- [5. PDF 生成库](#5-pdf-生成库)
- [6. 统计文件格式支持库](#6-统计文件格式支持库)
- [7. XML/XSLT 处理库](#7-xmlxslt-处理库)
- [8. 字体支持](#8-字体支持)
- [9. 其他依赖](#9-其他依赖)
- [10. 完整安装脚本](#10-完整安装脚本)

---

## 1. Tesseract OCR

### 用途
- **Image Tool**: OCR文本提取
- **Office Tool**: 图像文档OCR处理
- **Document Parser Tool**: 图像文档解析

### 依赖工具
**核心引擎:**
- `tesseract-ocr` - Tesseract OCR引擎
- `pytesseract` - Python接口 (通过pip安装)

**语言包:**
- `tesseract-ocr-eng` - 英语
- `tesseract-ocr-chi-sim` - 简体中文
- `tesseract-ocr-chi-tra` - 繁体中文
- `tesseract-ocr-fra` - 法语
- `tesseract-ocr-deu` - 德语
- `tesseract-ocr-jpn` - 日语
- `tesseract-ocr-kor` - 韩语
- `tesseract-ocr-rus` - 俄语
- `tesseract-ocr-spa` - 西班牙语

### 安装命令

**Ubuntu/Debian:**
```bash
# 安装核心引擎和英语支持
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# 安装多语言支持
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra
sudo apt-get install tesseract-ocr-fra tesseract-ocr-deu
sudo apt-get install tesseract-ocr-jpn tesseract-ocr-kor
sudo apt-get install tesseract-ocr-rus tesseract-ocr-spa
```

**macOS:**
```bash
# 安装核心引擎
brew install tesseract

# 安装语言包
brew install tesseract-lang
```

**验证安装:**
```bash
tesseract --version
tesseract --list-langs
```

---

## 2. Java Runtime Environment (JRE)

### 用途
- **Office Tool**: Apache Tika 文档解析 (需要Java运行时)
- **Document Parser Tool**: 通过Tika进行文档提取

### 依赖版本
- OpenJDK 11 (推荐)
- OpenJDK 17 (也支持)

### 安装命令

**Ubuntu/Debian:**
```bash
# 安装 OpenJDK 11 (推荐)
sudo apt-get update
sudo apt-get install openjdk-11-jdk

# 或安装 OpenJDK 17
sudo apt-get install openjdk-17-jdk

# 设置环境变量
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install openjdk@11

# 或安装 OpenJDK 17
brew install openjdk@17

# 设置环境变量
echo 'export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"' >> ~/.zshrc
```

**验证安装:**
```bash
java -version
javac -version
echo $JAVA_HOME
```

---

## 3. Playwright 浏览器

### 用途
- **Scraper Tool**: JavaScript渲染、浏览器自动化

### 依赖组件
- Chromium 浏览器
- Firefox 浏览器
- WebKit 浏览器

### 安装命令

**所有平台:**
```bash
# 安装 Playwright Python包
pip install playwright

# 安装浏览器二进制文件 (所有浏览器)
playwright install

# 安装特定浏览器
playwright install chromium
playwright install firefox
playwright install webkit

# 安装浏览器依赖
playwright install-deps
```

**Ubuntu/Debian 手动安装依赖:**
```bash
# Playwright浏览器所需的系统库
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2
```

**验证安装:**
```python
# 测试 Playwright 安装
python -c "import playwright; print('Playwright installed successfully')"
```

---

## 4. 图像处理库

### 用途
- **Image Tool**: 图像加载、处理、过滤
- **Office Tool**: 图像嵌入文档
- **Chart Tool**: 图表导出为图像
- **Data Visualizer Tool**: 可视化导出

### 依赖库
**PIL/Pillow 系统依赖:**
- `libjpeg-dev` - JPEG支持
- `zlib1g-dev` - PNG压缩支持
- `libpng-dev` - PNG支持
- `libtiff-dev` - TIFF支持
- `libwebp-dev` - WebP支持
- `libopenjp2-7-dev` - JPEG2000支持
- `libfreetype6-dev` - 字体渲染
- `liblcms2-dev` - 颜色管理
- `libharfbuzz-dev` - 文本塑形
- `libfribidi-dev` - 双向文本
- `libxcb1-dev` - X11连接

### 安装命令

**Ubuntu/Debian:**
```bash
# 完整安装 (推荐)
sudo apt-get update
sudo apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev

# 基础安装 (最小化)
sudo apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install \
    libjpeg \
    zlib \
    libpng \
    libtiff \
    webp \
    openjpeg \
    freetype \
    lcms2 \
    harfbuzz
```

**验证安装:**
```python
from PIL import Image
print(Image.__version__)
```

---

## 5. PDF 生成库

### 用途
- **Report Tool**: HTML转PDF
- **Document Creator Tool**: PDF文档生成
- **Office Tool**: PDF文档处理

### 依赖库
**WeasyPrint 系统依赖:**
- `libcairo2-dev` - Cairo图形库
- `libpango1.0-dev` - Pango文本布局
- `libgdk-pixbuf2.0-dev` - 图像加载
- `libffi-dev` - 外部函数接口
- `shared-mime-info` - MIME类型信息
- `libxml2-dev` - XML解析
- `libxslt1-dev` - XSLT转换

### 安装命令

**Ubuntu/Debian:**
```bash
# WeasyPrint 完整依赖
sudo apt-get update
sudo apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    libxml2-dev \
    libxslt1-dev
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install \
    cairo \
    pango \
    gdk-pixbuf \
    libffi
```

**验证安装:**
```bash
# 检查系统库
pkg-config --modversion cairo
pkg-config --modversion pango
pkg-config --modversion gdk-pixbuf-2.0
```

---

## 6. 统计文件格式支持库

### 用途
- **Stats Tool**: SAS、SPSS、Stata文件读取
- **Data Loader Tool**: 统计数据格式支持
- **Pandas Tool**: 特殊格式数据加载

### 依赖库
**pyreadstat 系统依赖:**
- `libreadstat-dev` - ReadStat库 (SAS/SPSS/Stata支持)
- `build-essential` - 编译工具
- `python3-dev` - Python开发头文件

### 支持的格式
- `.sav` - SPSS文件
- `.sas7bdat` - SAS文件
- `.por` - SPSS Portable文件
- `.dta` - Stata文件

### 安装命令

**Ubuntu/Debian:**
```bash
# 安装 ReadStat 库
sudo apt-get update
sudo apt-get install -y \
    libreadstat-dev \
    build-essential \
    python3-dev

# 重新安装 pyreadstat (如果已安装)
pip uninstall -y pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**macOS:**
```bash
# 使用 Homebrew 安装
brew install readstat

# 重新安装 pyreadstat
pip uninstall -y pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**CentOS/RHEL:**
```bash
# 安装开发工具
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# 使用 conda 安装
conda install -c conda-forge readstat pyreadstat
```

**验证安装:**
```python
try:
    import pyreadstat
    print("pyreadstat installed successfully")
    print(f"Version: {pyreadstat.__version__}")
except ImportError as e:
    print("pyreadstat installation failed:", e)
```

---

## 7. XML/XSLT 处理库

### 用途
- **Office Tool**: Excel文件处理
- **Data Loader Tool**: XML数据加载
- **Report Tool**: XML模板处理

### 依赖库
- `libxml2-dev` - XML解析库
- `libxslt1-dev` - XSLT转换库

### 安装命令

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y \
    libxml2-dev \
    libxslt1-dev
```

**macOS:**
```bash
# 通常已预装，如需可手动安装
brew install libxml2 libxslt
```

**验证安装:**
```bash
xml2-config --version
xslt-config --version
```

---

## 8. 字体支持

### 用途
- **Report Tool**: PDF中文字体
- **Chart Tool**: 图表中文标签
- **Document Creator Tool**: 文档中文支持
- **Data Visualizer Tool**: 可视化中文标签

### 依赖库
**中文字体:**
- `fonts-wqy-zenhei` - 文泉驿正黑体
- `fonts-wqy-microhei` - 文泉驿微米黑
- `fonts-noto-cjk` - Noto CJK字体

**其他常用字体:**
- `fonts-liberation` - Liberation字体 (Arial/Times替代)
- `fonts-dejavu` - DejaVu字体

### 安装命令

**Ubuntu/Debian:**
```bash
# 安装中文字体
sudo apt-get update
sudo apt-get install -y \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk

# 安装其他常用字体
sudo apt-get install -y \
    fonts-liberation \
    fonts-dejavu
```

**macOS:**
```bash
# macOS 通常已包含中文字体
# 如需额外字体，可手动安装或使用 Homebrew
brew tap homebrew/cask-fonts
brew install --cask font-wqy-zenhei
```

**刷新字体缓存 (Linux):**
```bash
fc-cache -f -v
```

**验证安装:**
```bash
# 列出已安装的中文字体
fc-list :lang=zh
```

---

## 9. 其他依赖

### Matplotlib 系统依赖

**用途:**
- **Chart Tool**: 图表生成
- **Data Visualizer Tool**: 数据可视化
- **Stats Tool**: 统计图表

**依赖库:**
- `libfreetype6-dev` - 字体渲染
- `libpng-dev` - PNG支持

**安装命令 (Ubuntu/Debian):**
```bash
sudo apt-get install -y \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    libwebp-dev
```

### Scrapy 依赖

**用途:**
- **Scraper Tool**: 高级爬虫功能

**依赖库:**
- `libxml2-dev`
- `libxslt1-dev`
- `libssl-dev`

**安装命令 (Ubuntu/Debian):**
```bash
sudo apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev
```

---

## 10. 完整安装脚本

### Ubuntu/Debian 一键安装脚本

```bash
#!/bin/bash

# AIECS Tools 系统依赖一键安装脚本 (Ubuntu/Debian)

echo "======================================"
echo "AIECS Tools 系统依赖安装"
echo "======================================"

# 更新包索引
echo "正在更新包索引..."
sudo apt-get update

# 1. Tesseract OCR
echo "安装 Tesseract OCR..."
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra

# 2. Java Runtime
echo "安装 Java Runtime..."
sudo apt-get install -y openjdk-11-jdk

# 3. 图像处理库
echo "安装图像处理库..."
sudo apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev

# 4. PDF 生成库
echo "安装 PDF 生成库..."
sudo apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info

# 5. XML/XSLT 库
echo "安装 XML/XSLT 库..."
sudo apt-get install -y \
    libxml2-dev \
    libxslt1-dev

# 6. 统计文件格式支持
echo "安装统计文件格式支持库..."
sudo apt-get install -y \
    libreadstat-dev \
    build-essential \
    python3-dev

# 7. 中文字体
echo "安装中文字体..."
sudo apt-get install -y \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk \
    fonts-liberation \
    fonts-dejavu

# 8. Playwright 浏览器依赖
echo "安装 Playwright 浏览器依赖..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

# 9. 其他依赖
echo "安装其他依赖..."
sudo apt-get install -y \
    libssl-dev \
    git \
    curl \
    wget

# 刷新字体缓存
echo "刷新字体缓存..."
fc-cache -f -v

echo ""
echo "======================================"
echo "系统依赖安装完成！"
echo "======================================"
echo ""
echo "请继续执行以下步骤："
echo "1. 安装 Python 包依赖: pip install -r requirements.txt"
echo "2. 安装 Playwright 浏览器: playwright install"
echo "3. 重新安装 pyreadstat: pip install --no-cache-dir --force-reinstall pyreadstat"
echo ""
echo "验证安装:"
echo "  - Tesseract: tesseract --version"
echo "  - Java: java -version"
echo "  - 字体: fc-list :lang=zh"
echo ""
```

### macOS 一键安装脚本

```bash
#!/bin/bash

# AIECS Tools 系统依赖一键安装脚本 (macOS)

echo "======================================"
echo "AIECS Tools 系统依赖安装 (macOS)"
echo "======================================"

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo "错误: 未检测到 Homebrew，请先安装 Homebrew"
    echo "安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# 1. Tesseract OCR
echo "安装 Tesseract OCR..."
brew install tesseract tesseract-lang

# 2. Java Runtime
echo "安装 Java Runtime..."
brew install openjdk@11

# 3. 图像处理库
echo "安装图像处理库..."
brew install \
    libjpeg \
    zlib \
    libpng \
    libtiff \
    webp \
    openjpeg \
    freetype \
    lcms2 \
    harfbuzz

# 4. PDF 生成库
echo "安装 PDF 生成库..."
brew install \
    cairo \
    pango \
    gdk-pixbuf \
    libffi

# 5. XML/XSLT 库
echo "安装 XML/XSLT 库..."
brew install libxml2 libxslt

# 6. 统计文件格式支持
echo "安装统计文件格式支持库..."
brew install readstat

# 7. 其他依赖
echo "安装其他依赖..."
brew install \
    git \
    curl \
    wget

# 设置环境变量
echo "设置环境变量..."
echo 'export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"' >> ~/.zshrc

echo ""
echo "======================================"
echo "系统依赖安装完成！"
echo "======================================"
echo ""
echo "请继续执行以下步骤："
echo "1. 安装 Python 包依赖: pip install -r requirements.txt"
echo "2. 安装 Playwright 浏览器: playwright install"
echo "3. 重新安装 pyreadstat: pip install --no-cache-dir --force-reinstall pyreadstat"
echo "4. 重新加载 shell 配置: source ~/.zshrc"
echo ""
echo "验证安装:"
echo "  - Tesseract: tesseract --version"
echo "  - Java: java -version"
echo ""
```

---

## 按工具分类的依赖关系

### Image Tool
- ✅ Tesseract OCR + 语言包
- ✅ PIL/Pillow 系统库 (libjpeg, libpng, libtiff等)

### Office Tool
- ✅ Java Runtime (OpenJDK 11/17)
- ✅ Apache Tika (自动下载，需要Java)
- ✅ Tesseract OCR (用于图像OCR)
- ✅ PIL/Pillow 系统库

### Scraper Tool
- ✅ Playwright 浏览器 (chromium, firefox, webkit)
- ✅ Scrapy 依赖 (libxml2, libxslt, libssl)

### Document Parser Tool
- ✅ 依赖于 Office Tool (Java, Tika, Tesseract)
- ✅ 依赖于 Image Tool (Tesseract, PIL)
- ✅ 依赖于 Scraper Tool (Playwright)

### Chart Tool & Data Visualizer Tool
- ✅ Matplotlib 系统库 (libfreetype, libpng等)
- ✅ 中文字体 (fonts-wqy-zenhei等)

### Stats Tool & Data Loader Tool
- ✅ pyreadstat 系统库 (libreadstat-dev)
- ✅ Excel 支持 (libxml2-dev, libxslt1-dev)

### Report Tool & Document Creator Tool
- ✅ WeasyPrint 依赖 (cairo, pango, gdk-pixbuf等)
- ✅ Matplotlib 系统库
- ✅ 中文字体

### Model Trainer Tool
- ✅ 无特殊系统级依赖 (仅Python包)

### Search Tool & APISource Tool
- ✅ 无特殊系统级依赖 (仅Python包)

---

## 故障排查

### Tesseract 问题

**问题:** `tesseract: command not found`
```bash
# 检查安装
which tesseract
tesseract --version

# 重新安装
sudo apt-get install --reinstall tesseract-ocr
```

**问题:** 语言包未找到
```bash
# 列出已安装语言包
tesseract --list-langs

# 安装缺失的语言包
sudo apt-get install tesseract-ocr-chi-sim
```

### Java 问题

**问题:** `java: command not found`
```bash
# 检查安装
java -version
echo $JAVA_HOME

# 设置环境变量
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

### Pillow 问题

**问题:** JPEG/PNG 支持缺失
```bash
# 重新安装系统库
sudo apt-get install libjpeg-dev libpng-dev

# 重新安装 Pillow
pip uninstall Pillow
pip install --no-cache-dir Pillow

# 验证
python -c "from PIL import Image; print(Image.PILLOW_VERSION)"
```

### pyreadstat 问题

**问题:** 编译失败
```bash
# 安装完整的开发依赖
sudo apt-get install libreadstat-dev build-essential python3-dev

# 清除缓存并重新安装
pip cache purge
pip uninstall pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

### Playwright 问题

**问题:** 浏览器启动失败
```bash
# 安装浏览器依赖
playwright install-deps

# 重新安装浏览器
playwright install --force

# 检查浏览器路径
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path)"
```

---

## 最小安装建议

如果只需要运行特定工具，可以进行最小化安装：

### 仅文档处理 (Office, Document Parser)
```bash
sudo apt-get install -y \
    openjdk-11-jdk \
    tesseract-ocr \
    tesseract-ocr-eng \
    libxml2-dev \
    libxslt1-dev
```

### 仅数据分析 (Stats, Data Loader, Chart)
```bash
sudo apt-get install -y \
    libreadstat-dev \
    build-essential \
    python3-dev \
    libfreetype6-dev \
    libpng-dev \
    fonts-wqy-zenhei
```

### 仅网页抓取 (Scraper)
```bash
sudo apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev

# 然后安装 Playwright
pip install playwright
playwright install
playwright install-deps
```

### 仅报告生成 (Report, Document Creator)
```bash
sudo apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    libfreetype6-dev \
    fonts-wqy-zenhei \
    fonts-wqy-microhei
```

---

## 总结

### 核心依赖 (所有工具共同需要)
1. **Python 开发环境**: `python3-dev`, `build-essential`
2. **基础库**: `libxml2-dev`, `libxslt1-dev`

### 关键依赖 (大多数工具需要)
1. **图像处理**: PIL/Pillow 系统库
2. **文本处理**: Tesseract OCR
3. **字体支持**: 中文字体

### 可选依赖 (特定功能需要)
1. **Java Runtime**: Office 文档处理
2. **Playwright**: JavaScript 渲染
3. **ReadStat**: 统计文件格式
4. **WeasyPrint**: PDF 生成

---

## 参考文档

- Image Tool: `IMAGE_TOOL_CONFIGURATION.md`
- Office Tool: `OFFICE_TOOL_CONFIGURATION.md`
- Scraper Tool: `SCRAPER_TOOL_CONFIGURATION.md`
- Document Parser Tool: `DOCUMENT_PARSER_TOOL_CONFIGURATION.md`
- Stats Tool: `TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md` (Stats Tool部分)
- Report Tool: `TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md` (Report Tool部分)

---

**文档版本**: 1.0  
**最后更新**: 2025-12-20  
**维护者**: AIECS Tools Team

