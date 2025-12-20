# AIECS Project - Multi-stage Docker Build
# 包含所有工具的系统级依赖

# ============================================================================
# Stage 1: Base Image with System Dependencies
# ============================================================================
FROM python:3.11-slim as base

LABEL maintainer="AIECS Team"
LABEL description="AIECS - AI-Enhanced Computing System with all dependencies"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 更新包列表
RUN apt-get update && apt-get upgrade -y

# ============================================================================
# 安装所有系统级依赖
# ============================================================================

# 1. 基础构建工具
RUN apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    git \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Image Tool 依赖: Tesseract OCR + 语言包
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    && rm -rf /var/lib/apt/lists/*

# 3. Image Tool & Document Writer 依赖: Pillow 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libfreetype6-dev \
    liblcms2-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Office Tool 依赖: Java Runtime (Apache Tika)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# 5. Stats Tool & Data Loader 依赖: pyreadstat 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreadstat-dev \
    libreadline-dev \
    && rm -rf /var/lib/apt/lists/*

# 6. Report Tool 依赖 (可选): WeasyPrint 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 7. Data Visualizer & Chart Tool 依赖: Matplotlib 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 8. 中文字体支持 (用于图表和报告)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# 9. Scraper Tool 依赖: Playwright 系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 10. XML/XSLT 处理库 (lxml)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 11. 数据库客户端 (可选 - 用于知识图谱)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# Stage 2: Python Dependencies
# ============================================================================
FROM base as python-deps

# 安装 Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 配置 Poetry (不创建虚拟环境，因为已经在容器中)
RUN poetry config virtualenvs.create false

# 安装 Python 依赖 (仅生产环境依赖)
RUN poetry install --no-dev --no-interaction --no-ansi

# 安装 Playwright 浏览器
RUN playwright install chromium --with-deps

# ============================================================================
# Stage 3: Download NLP Models & Data
# ============================================================================
FROM python-deps as nlp-models

# 下载 spaCy 模型
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download zh_core_web_sm || true

# 下载 NLTK 数据
RUN python -c "import nltk; \
    nltk.download('stopwords', quiet=True); \
    nltk.download('punkt', quiet=True); \
    nltk.download('wordnet', quiet=True); \
    nltk.download('averaged_perceptron_tagger', quiet=True); \
    nltk.download('omw-1.4', quiet=True)"

# ============================================================================
# Stage 4: Final Production Image
# ============================================================================
FROM nlp-models as production

# 创建非 root 用户
RUN useradd -m -u 1000 aiecs && \
    mkdir -p /app/data /app/logs /app/temp && \
    chown -R aiecs:aiecs /app

# 设置工作目录
WORKDIR /app

# 复制项目代码
COPY --chown=aiecs:aiecs . .

# 切换到非 root 用户
USER aiecs

# 设置环境变量
ENV PYTHONPATH=/app \
    AIECS_DATA_DIR=/app/data \
    AIECS_LOG_DIR=/app/logs \
    AIECS_TEMP_DIR=/app/temp

# 暴露端口 (根据实际需要调整)
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from aiecs.scripts.dependance_check.dependency_checker import DependencyChecker; \
    checker = DependencyChecker(); \
    tools = checker.check_all_dependencies(); \
    exit(0 if len(tools) == 30 else 1)"

# 默认命令 (可以被 docker run 覆盖)
CMD ["python", "-m", "aiecs"]

# ============================================================================
# Stage 5: Development Image (包含开发工具)
# ============================================================================
FROM python-deps as development

# 安装开发依赖
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi

# 安装开发工具
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    black \
    flake8 \
    mypy \
    pytest \
    pytest-cov

# 创建非 root 用户
RUN useradd -m -u 1000 aiecs && \
    mkdir -p /app/data /app/logs /app/temp && \
    chown -R aiecs:aiecs /app

WORKDIR /app
COPY --chown=aiecs:aiecs . .

USER aiecs

ENV PYTHONPATH=/app \
    AIECS_ENV=development

# 开发模式不需要健康检查
CMD ["bash"]

