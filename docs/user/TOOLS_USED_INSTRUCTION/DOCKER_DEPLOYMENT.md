# AIECS Docker 部署指南

## 📋 概述

本项目提供完整的 Docker 容器化方案，**所有系统级依赖都已打包在容器中**，无需在宿主机上安装任何额外依赖。

## ✅ 包含的系统依赖

### 完整依赖列表

| 工具类别 | 系统依赖 | 用途 |
|---------|---------|------|
| **Image Tool** | Tesseract OCR + 语言包 | OCR 文字识别 |
| **Image Tool** | libjpeg, libpng, libtiff, libwebp | 图像处理 |
| **Office Tool** | OpenJDK 17 JRE | Apache Tika (文档解析) |
| **Stats Tool** | libreadstat | SAS/SPSS/Stata 文件读取 |
| **Report Tool** | Cairo, Pango, GDK-Pixbuf | PDF 生成 (WeasyPrint) |
| **Chart Tool** | Freetype, Matplotlib 系统库 | 图表生成 |
| **中文支持** | WQY 字体 | 中文字符显示 |
| **Scraper Tool** | Chromium 浏览器依赖 | 网页抓取 |
| **知识图谱** | 图数据库客户端 | Neo4j 连接 |

## 🚀 快速开始

### 1. 基础构建

```bash
# 构建生产镜像
docker build -t aiecs:latest .

# 或使用 docker-compose
docker-compose build aiecs
```

### 2. 运行容器

```bash
# 方式 1: 使用 docker run
docker run -d \
  --name aiecs \
  -p 8000:8000 \
  -v aiecs-data:/app/data \
  -v aiecs-logs:/app/logs \
  --env-file .env \
  aiecs:latest

# 方式 2: 使用 docker-compose (推荐)
docker-compose up -d aiecs
```

### 3. 验证部署

```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f aiecs

# 进入容器
docker-compose exec aiecs bash

# 在容器内运行依赖检查
docker-compose exec aiecs python aiecs/scripts/dependance_check/dependency_checker.py
```

## 📦 多阶段构建说明

### Stage 1: Base (系统依赖层)
```dockerfile
FROM python:3.11-slim as base
# 安装所有系统级依赖
```
- **大小**: ~800MB
- **包含**: 所有 apt 安装的系统库
- **缓存**: 很少变化，可以充分利用 Docker 缓存

### Stage 2: Python Dependencies (Python 依赖层)
```dockerfile
FROM base as python-deps
# 安装 Poetry 和 Python 包
```
- **大小**: +300MB
- **包含**: 所有 Python 包
- **缓存**: pyproject.toml 不变时可复用

### Stage 3: NLP Models (模型层)
```dockerfile
FROM python-deps as nlp-models
# 下载 spaCy 和 NLTK 数据
```
- **大小**: +200MB
- **包含**: 预训练模型和语言数据
- **缓存**: 可以预先构建并推送到镜像仓库

### Stage 4: Production (生产层)
```dockerfile
FROM nlp-models as production
# 复制应用代码
```
- **总大小**: ~1.3GB
- **特点**: 
  - 使用非 root 用户运行
  - 包含健康检查
  - 优化的安全配置

### Stage 5: Development (开发层)
```dockerfile
FROM python-deps as development
# 包含开发工具
```
- **大小**: ~1.5GB
- **包含**: 开发依赖、调试工具
- **用途**: 本地开发和调试

## 🎯 使用场景

### 场景 1: 生产部署

```bash
# 启动完整服务栈
docker-compose up -d

# 包括:
# - AIECS 主服务
# - Redis (缓存)
# - Neo4j (知识图谱)
```

**访问端口**:
- AIECS API: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474`
- Redis: `localhost:6379`

### 场景 2: 开发环境

```bash
# 启动开发服务
docker-compose up -d aiecs-dev

# 代码热重载
# 实时调试
```

**特点**:
- 挂载本地代码目录
- 支持实时修改
- 包含开发工具

### 场景 3: 仅运行依赖检查

```bash
# 运行依赖检查
docker-compose --profile tools run --rm dependency-check

# 查看报告
cat dependency_report.txt
```

### 场景 4: Jupyter 数据分析

```bash
# 启动 Jupyter Lab
docker-compose up -d jupyter

# 访问 http://localhost:8888
```

## 🔧 环境变量配置

创建 `.env` 文件：

```bash
# AIECS 配置
AIECS_ENV=production
AIECS_DATA_DIR=/app/data
AIECS_LOG_DIR=/app/logs

# OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# Google Search API
GOOGLE_SEARCH_API_KEY=...
GOOGLE_SEARCH_ENGINE_ID=...

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# 工具配置
IMAGE_TOOL_TESSERACT_POOL_SIZE=4
OFFICE_TOOL_TIKA_SERVER_URL=http://localhost:9998
REPORT_TOOL_PDF_PAGE_SIZE=A4
```

## 📊 镜像大小优化

### 当前镜像大小

```bash
# 查看镜像大小
docker images aiecs

# 预期大小:
# aiecs:latest (production) ~1.3GB
# aiecs:dev (development)   ~1.5GB
```

### 优化策略

1. **多阶段构建**: 最终镜像只包含必要文件
2. **apt 清理**: 每次安装后清理缓存
3. **Python 缓存**: 禁用 pip 缓存
4. **分层优化**: 把变化少的层放在前面

### 进一步优化选项

```bash
# 方式 1: 使用 Alpine 基础镜像 (不推荐，兼容性问题)
# FROM python:3.11-alpine

# 方式 2: 使用 distroless 镜像 (推荐生产环境)
# FROM gcr.io/distroless/python3-debian11

# 方式 3: 压缩镜像
docker image save aiecs:latest | gzip > aiecs-latest.tar.gz
```

## 🔒 安全最佳实践

### 1. 使用非 root 用户

```dockerfile
# 已在 Dockerfile 中实现
RUN useradd -m -u 1000 aiecs
USER aiecs
```

### 2. 扫描安全漏洞

```bash
# 使用 Trivy 扫描
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image aiecs:latest

# 使用 Docker Scout
docker scout cves aiecs:latest
```

### 3. 更新基础镜像

```bash
# 定期重新构建
docker-compose build --no-cache --pull
```

### 4. 密钥管理

```bash
# 使用 Docker Secrets (Swarm mode)
docker secret create openai_key openai.txt

# 或使用环境变量文件
docker-compose --env-file .env.prod up -d
```

## 📈 监控和日志

### 健康检查

```bash
# 查看健康状态
docker-compose ps

# 手动检查
docker-compose exec aiecs python -c "
from aiecs.scripts.dependance_check.dependency_checker import DependencyChecker
checker = DependencyChecker()
tools = checker.check_all_dependencies()
print(f'✅ All {len(tools)} tools checked')
"
```

### 日志管理

```bash
# 实时查看日志
docker-compose logs -f aiecs

# 查看特定服务日志
docker-compose logs redis

# 导出日志
docker-compose logs --no-color > aiecs.log
```

### 资源监控

```bash
# 查看资源使用
docker stats

# 查看特定容器
docker stats aiecs-prod

# 限制资源使用 (docker-compose.yml)
services:
  aiecs:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          memory: 2G
```

## 🔄 更新和回滚

### 更新服务

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build aiecs

# 3. 停止旧容器并启动新容器
docker-compose up -d aiecs

# 4. 验证更新
docker-compose logs -f aiecs
```

### 回滚

```bash
# 1. 使用之前的镜像标签
docker tag aiecs:backup aiecs:latest

# 2. 重启服务
docker-compose up -d aiecs

# 或者使用 Git 回滚
git checkout <previous-commit>
docker-compose build aiecs
docker-compose up -d aiecs
```

## 🚢 CI/CD 集成

### GitHub Actions 示例

```yaml
# .github/workflows/docker.yml
name: Docker Build and Push

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            aiecs/aiecs:latest
            aiecs/aiecs:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Run dependency check
        run: |
          docker run --rm aiecs/aiecs:latest \
            python aiecs/scripts/dependance_check/dependency_checker.py
```

### GitLab CI 示例

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

test:
  stage: test
  script:
    - docker run --rm $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA \
        python aiecs/scripts/dependance_check/dependency_checker.py

deploy:
  stage: deploy
  script:
    - docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA $CI_REGISTRY_IMAGE:latest
    - docker push $CI_REGISTRY_IMAGE:latest
```

## 📦 镜像发布

### 推送到 Docker Hub

```bash
# 1. 登录
docker login

# 2. 打标签
docker tag aiecs:latest your-username/aiecs:latest
docker tag aiecs:latest your-username/aiecs:v1.0.0

# 3. 推送
docker push your-username/aiecs:latest
docker push your-username/aiecs:v1.0.0
```

### 推送到私有仓库

```bash
# 1. 登录私有仓库
docker login registry.example.com

# 2. 打标签
docker tag aiecs:latest registry.example.com/aiecs:latest

# 3. 推送
docker push registry.example.com/aiecs:latest
```

## 🧪 测试

### 运行单元测试

```bash
# 在容器中运行测试
docker-compose exec aiecs pytest

# 或者构建测试镜像
docker build --target development -t aiecs:test .
docker run --rm aiecs:test pytest
```

### 集成测试

```bash
# 启动完整测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
docker-compose -f docker-compose.test.yml run --rm test

# 清理
docker-compose -f docker-compose.test.yml down -v
```

## 🛠️ 故障排查

### 问题 1: 容器无法启动

```bash
# 查看详细日志
docker-compose logs aiecs

# 检查配置
docker-compose config

# 验证镜像
docker run --rm -it aiecs:latest bash
```

### 问题 2: 依赖缺失

```bash
# 进入容器检查
docker-compose exec aiecs bash

# 运行依赖检查
python aiecs/scripts/dependance_check/dependency_checker.py

# 查看已安装的包
apt list --installed | grep <package-name>
pip list | grep <package-name>
```

### 问题 3: 性能问题

```bash
# 查看资源使用
docker stats

# 增加资源限制
# 编辑 docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
```

### 问题 4: 网络问题

```bash
# 检查网络
docker network ls
docker network inspect aiecs-network

# 重建网络
docker-compose down
docker network prune
docker-compose up -d
```

## 📚 参考资料

### Docker 最佳实践
- [Docker官方最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Dockerfile最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [多阶段构建](https://docs.docker.com/build/building/multi-stage/)

### 安全指南
- [Docker安全](https://docs.docker.com/engine/security/)
- [容器安全最佳实践](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

## 🎉 总结

**所有系统依赖都已打包在 Docker 容器中**，包括：

✅ **30 个工具的完整依赖**
- 系统级依赖 (apt 包)
- Python 包依赖
- NLP 模型和数据
- 浏览器和字体

✅ **即插即用**
- `docker-compose up -d` 即可启动
- 无需在宿主机安装任何依赖
- 环境完全一致

✅ **生产就绪**
- 多阶段构建优化
- 安全配置
- 健康检查
- 日志和监控

✅ **开发友好**
- 开发环境支持
- 热重载
- 调试工具

---

**快速开始**: `docker-compose up -d aiecs`

**问题反馈**: 请在 GitHub Issues 中提交

