FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

# 安装系统依赖（包含 OCR、PDF、Textract、WeasyPrint 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential libgl1 libglib2.0-0 \
    libxrender1 libsm6 libxext6 poppler-utils \
    libpango-1.0-0 libpangoft2-1.0-0 libffi-dev \
    libjpeg-dev zlib1g-dev libxml2 libxslt1-dev \
    libpq-dev curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install --upgrade pip && \
    pip install poetry==$POETRY_VERSION

# 配置 Poetry
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true && \
    poetry config cache-dir /tmp/poetry_cache

# 复制 Poetry 配置文件
COPY pyproject.toml poetry.lock* ./

# 安装 Python 依赖
RUN poetry install --only=main --no-root && \
    rm -rf $POETRY_CACHE_DIR

# 下载 spaCy 模型
RUN poetry run python -m spacy download en_core_web_sm && \
    poetry run python -m spacy download zh_core_web_sm

# 复制应用代码
COPY . .

# 安装项目本身
RUN poetry install --only-root

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"," --reload"]
