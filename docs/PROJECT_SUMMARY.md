# AIECS 项目转换总结

## 已完成的任务

### 1. 项目重命名 ✓
- 将 "app" 目录成功重命名为 "aiecs" (AI Execute Services)
- 更新了所有内部引用，从 `app.` 改为 `aiecs.`
- 确保所有导入路径正确

### 2. Main.py 入口文件 ✓
创建了完整的 `aiecs/main.py` 文件，包含：
- FastAPI 应用程序设置
- WebSocket 集成
- 健康检查端点
- 任务执行 API
- 工具列表 API
- 服务和提供商信息 API
- 完整的生命周期管理

### 3. README 文档 ✓
创建了专业的 README.md，包含：
- 项目介绍和特性
- 安装说明
- 快速开始指南
- 配置说明
- API 文档
- 架构说明
- 开发指南

### 4. PyProject.toml 配置 ✓
更新了 pyproject.toml：
- 项目名称改为 "aiecs"
- 添加了完整的元数据
- 配置了正确的依赖项
- 添加了分类器和关键词
- 配置了构建系统

### 5. Scripts 依赖补丁 ✓
- 将 scripts 目录移动到 aiecs 包内
- 更新了 `fix_weasel_validator.py` 以适应新结构
- 创建了 `setup.py` 文件，包含 post-install 钩子
- 配置了自动执行 weasel 补丁的机制

### 6. NLP 数据包自动下载 ✓
- 创建了全面的 `download_nlp_data.py` 脚本，自动下载 classfire_tool 所需的 NLP 数据包
- 自动下载 NLTK stopwords、punkt 等数据包（rake-nltk 和文本处理需要）
- 自动下载 spaCy 英文模型 en_core_web_sm（必需）
- 自动下载 spaCy 中文模型 zh_core_web_sm（可选）
- 集成到 post-install 钩子中，安装时自动执行
- 提供多种手动执行方式：
  - `aiecs-download-nlp-data`：Python 脚本命令
  - `./aiecs/scripts/setup_nlp_data.sh`：便捷 shell 脚本
- 包含完整的错误处理、日志记录和安装验证
- 支持虚拟环境自动检测和激活

## 额外完成的工作

1. **创建了 `__main__.py`**
   - 允许通过 `python -m aiecs` 运行服务

2. **创建了 LICENSE 文件**
   - MIT 许可证

3. **创建了 MANIFEST.in**
   - 确保所有必要文件都包含在分发包中

4. **创建了 .gitignore**
   - 防止不必要的文件进入版本控制

5. **创建了 PUBLISH.md**
   - 详细的 PyPI 发布指南

6. **创建了测试脚本**
   - `test_import.py` 用于验证包结构

## 项目结构

```
python-middleware-dev/
├── aiecs/                    # 主包目录（原 app）
│   ├── __init__.py
│   ├── __main__.py          # CLI 入口点
│   ├── main.py              # FastAPI 应用
│   ├── scripts/             # 自动化脚本
│   │   ├── __init__.py
│   │   ├── fix_weasel_validator.py    # weasel 库补丁
│   │   ├── download_nlp_data.py       # NLP 数据包下载
│   │   └── ...
│   └── ... (其他模块)
├── setup.py                 # 安装配置（含 post-install）
├── pyproject.toml          # 项目元数据
├── README.md               # 项目文档
├── LICENSE                 # MIT 许可证
├── MANIFEST.in            # 包含文件清单
├── PUBLISH.md             # 发布指南
└── .gitignore             # Git 忽略文件
```

## 发布准备

项目现在已经准备好发布到 PyPI。发布步骤：

1. **安装构建工具**
   ```bash
   pip install build twine
   ```

2. **构建包**
   ```bash
   python -m build
   ```

3. **测试安装**
   ```bash
   pip install dist/aiecs-1.0.0-py3-none-any.whl
   ```

4. **上传到 TestPyPI**（推荐先测试）
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

5. **上传到 PyPI**
   ```bash
   python -m twine upload dist/*
   ```

## 使用说明

安装后，用户可以：

1. **作为库使用**
   ```python
   from aiecs import AIECS
   from aiecs.domain.task.task_context import TaskContext
   ```

2. **运行服务**
   ```bash
   aiecs  # 或 python -m aiecs
   ```

3. **运行 weasel 补丁**（如果自动补丁失败）
   ```bash
   aiecs-patch-weasel
   ```

4. **下载 NLP 数据包**（如果自动下载失败）
   ```bash
   # 使用 Python 脚本命令（推荐）
   aiecs-download-nlp-data
   
   # 或使用 shell 脚本
   ./aiecs/scripts/setup_nlp_data.sh
   
   # 仅验证已安装的数据包
   ./aiecs/scripts/setup_nlp_data.sh --verify
   ```

## 注意事项

1. 用户需要配置环境变量（.env 文件）才能正常使用
2. 需要 PostgreSQL 和 Redis 服务才能完整运行
3. weasel 补丁会在安装时自动尝试执行
4. NLP 数据包（NLTK stopwords 和 spaCy en_core_web_sm）会在安装时自动下载
5. **Image Tool 需要系统级 Tesseract OCR 才能使用 OCR 功能**
6. **Java 环境和 Apache Tika（可选依赖）**：
   - Office Tool 中的文本提取功能使用 Apache Tika 作为万能后备方案
   - Tika 支持 1000+ 种文档格式的文本提取（包括旧版 Office 格式）
   - 需要 Java Runtime Environment (JRE) 8+ 才能使用
   - 如果没有 Java 环境，会自动跳过 Tika 相关测试，不影响其他功能
   - 推荐在企业环境或需要处理多种文档格式时安装 Java
7. 项目支持 Python 3.10-3.12

## 自动化功能

### NLP 数据包管理
- **自动下载**: 安装时自动下载 classfire_tool 所需的 NLP 数据包
  - NLTK stopwords、punkt 等数据包
  - spaCy 英文模型 en_core_web_sm（必需）
  - spaCy 中文模型 zh_core_web_sm（可选）
- **多种执行方式**:
  - Python 脚本：`aiecs-download-nlp-data`
  - Shell 脚本：`./aiecs/scripts/setup_nlp_data.sh`
  - 验证模式：`./aiecs/scripts/setup_nlp_data.sh --verify`
- **高级功能**:
  - 虚拟环境自动检测和激活
  - 依赖项完整性检查
  - 下载进度和状态日志记录
  - 安装后验证测试
  - 智能检测已存在的数据包
  - 超时保护（防止长时间挂起）
- **错误处理**: 下载失败不会阻止整个安装过程，会生成详细日志

### Java/Tika 集成管理
- **功能定位**: Apache Tika 作为 Office Tool 的万能文本提取后备方案
- **支持格式**: 
  - 专用库处理：DOCX、PPTX、XLSX（使用 python-docx/python-pptx/pandas）
  - PDF 文档（使用 pdfplumber）
  - 图像 OCR（使用 pytesseract）
  - **Tika 处理的格式**：旧版 Office（.doc/.xls/.ppt）、RTF、ODF、电子书等 1000+ 格式
- **环境检测**:
  - 自动检测 Java 运行时环境
  - 测试时优雅跳过（如果 Java 不可用）
  - 运行时提供降级处理
- **部署建议**:
  - **开发环境**: Java 可选，便于完整测试
  - **生产环境**: 根据文档处理需求决定
  - **Docker 部署**: 提供带 Java 和纯 Python 两种镜像选项
- **错误处理**: Tika 不可用时不影响其他文档处理功能，会记录警告日志

## Java 环境配置指南

### 安装 Java 运行时环境

#### Linux (Ubuntu/Debian)
```bash
# 安装 OpenJDK 11 (推荐)
sudo apt update
sudo apt install openjdk-11-jre-headless

# 或安装 OpenJDK 8 (最低要求)
sudo apt install openjdk-8-jre-headless

# 验证安装
java -version
```

#### Linux (CentOS/RHEL/Fedora)
```bash
# CentOS/RHEL
sudo yum install java-11-openjdk-headless

# Fedora
sudo dnf install java-11-openjdk-headless

# 验证安装
java -version
```

#### macOS
```bash
# 使用 Homebrew
brew install openjdk@11

# 或下载 Oracle JDK
# 访问 https://www.oracle.com/java/technologies/downloads/

# 验证安装
java -version
```

#### Windows
```batch
# 使用 Chocolatey
choco install openjdk11

# 或使用 Scoop
scoop install openjdk

# 或手动下载安装
# 访问 https://adoptium.net/ 下载 Eclipse Temurin

# 验证安装
java -version
```

### 验证 Tika 功能

安装 Java 后，可以验证 Tika 功能是否正常：

```python
from aiecs.tools.task_tools.office_tool import OfficeTool

# 创建工具实例
tool = OfficeTool()

# 测试 Tika 文本提取（使用任意文档文件）
try:
    text = tool.extract_text("path/to/your/document.doc")
    print("Tika 功能正常工作")
except Exception as e:
    print(f"Tika 不可用: {e}")
```

## Docker 配置指南

### 基础 Python 镜像（不含 Java）

```dockerfile
# Dockerfile.python-only
FROM python:3.11-slim

# 安装系统依赖（Tesseract OCR）
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install -e .

# 启动命令
CMD ["python", "-m", "aiecs"]
```

### 包含 Java 的完整镜像

```dockerfile
# Dockerfile.with-java
FROM python:3.11-slim

# 安装系统依赖（包括 Java 和 Tesseract）
RUN apt-get update && apt-get install -y \
    openjdk-11-jre-headless \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# 设置 JAVA_HOME 环境变量
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN pip install -e .

# 验证 Java 安装
RUN java -version

# 启动命令
CMD ["python", "-m", "aiecs"]
```

### Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  aiecs-python-only:
    build:
      context: .
      dockerfile: Dockerfile.python-only
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  aiecs-with-java:
    build:
      context: .
      dockerfile: Dockerfile.with-java
    environment:
      - PYTHONPATH=/app
      - JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aiecs
      POSTGRES_USER: aiecs
      POSTGRES_PASSWORD: aiecs_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  redis_data:
```

### 多阶段构建（推荐用于生产）

```dockerfile
# Dockerfile.multi-stage
# 构建阶段
FROM python:3.11 as builder

WORKDIR /app
COPY pyproject.toml setup.py ./
COPY aiecs/ ./aiecs/

# 安装构建依赖
RUN pip install build
RUN python -m build

# 运行阶段 - 纯 Python
FROM python:3.11-slim as python-runtime

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

CMD ["python", "-m", "aiecs"]

# 运行阶段 - 包含 Java
FROM python:3.11-slim as java-runtime

RUN apt-get update && apt-get install -y \
    openjdk-11-jre-headless \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

WORKDIR /app
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

CMD ["python", "-m", "aiecs"]
```

### 构建和运行命令

```bash
# 构建纯 Python 镜像
docker build -f Dockerfile.python-only -t aiecs:python-only .

# 构建包含 Java 的镜像
docker build -f Dockerfile.with-java -t aiecs:with-java .

# 使用多阶段构建
docker build --target python-runtime -t aiecs:python-runtime .
docker build --target java-runtime -t aiecs:java-runtime .

# 运行容器
docker run -p 8000:8000 aiecs:with-java

# 使用 Docker Compose
docker-compose up aiecs-with-java
```

### 环境变量配置

创建 `.env` 文件用于 Docker 环境：

```bash
# .env
# 数据库配置
DATABASE_URL=postgresql://aiecs:aiecs_password@postgres:5432/aiecs

# Redis 配置
REDIS_URL=redis://redis:6379/0

# Java 配置（可选）
JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
TIKA_SERVER_JAR=/usr/share/java/tika-server.jar

# 其他配置
PYTHONPATH=/app
LOG_LEVEL=INFO
```

### 验证 Docker 部署

```bash
# 进入容器验证环境
docker exec -it <container_id> bash

# 验证 Python 环境
python -c "from aiecs import AIECS; print('AIECS OK')"

# 验证 Java 环境（如果安装了）
java -version

# 验证 Tika 功能
python -c "
from aiecs.tools.task_tools.office_tool import OfficeTool
tool = OfficeTool()
print('Tika available:', hasattr(tool, '_extract_tika_text'))
"

# 验证 OCR 功能
tesseract --version
```

### 镜像大小对比

- **纯 Python 镜像**: ~800MB
- **包含 Java 镜像**: ~1.2GB
- **完整功能镜像**: ~1.5GB (包含所有依赖)

根据实际需求选择合适的镜像配置！

项目转换完成！🎉
