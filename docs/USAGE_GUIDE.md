# AIECS 使用指南

## 🔧 三种使用方式详解

### 1️⃣ **独立服务模式**（Standalone Service）

适用场景：
- 需要运行完整的 AI 中间件服务
- 支持多个客户端连接
- 需要 WebSocket 实时通信
- 需要分布式任务处理

#### 🚀 启动服务

```bash
# 方式1：使用命令行入口（推荐）
aiecs

# 方式2：使用 Python 模块
python -m aiecs

# 方式3：使用 uvicorn 直接启动
uvicorn aiecs.main:app --host 0.0.0.0 --port 8000

# 方式4：使用 poetry
poetry run python -m aiecs
```

#### 🔧 启动完整的分布式环境

```bash
# 1. 启动 Redis（消息队列）
redis-server

# 2. 启动 PostgreSQL 数据库
sudo systemctl start postgresql

# 3. 启动主服务（FastAPI + WebSocket）
aiecs

# 4. 启动 Celery Worker（处理异步任务）
celery -A aiecs.tasks.worker.celery_app worker --loglevel=info

# 5. 启动 Celery Beat（定时任务调度）
celery -A aiecs.tasks.worker.celery_app beat --loglevel=info

# 6. 启动 Flower（Celery 监控界面）
celery -A aiecs.tasks.worker.celery_app flower --port=5555
```

#### 📡 客户端调用

```python
import httpx
import asyncio

async def call_aiecs_service():
    async with httpx.AsyncClient() as client:
        # 调用健康检查
        health = await client.get("http://localhost:8000/health")
        print(health.json())
        
        # 获取可用工具
        tools = await client.get("http://localhost:8000/api/tools")
        print(tools.json())
        
        # 执行任务
        task_data = {
            "type": "task",
            "mode": "execute", 
            "service": "default",
            "userId": "user123",
            "context": {
                "metadata": {
                    "aiPreference": {
                        "provider": "OpenAI",
                        "model": "gpt-4"
                    }
                },
                "data": {
                    "task": "Analyze this text",
                    "content": "Hello world"
                }
            }
        }
        
        response = await client.post(
            "http://localhost:8000/api/execute",
            json=task_data
        )
        result = response.json()
        print(f"Task ID: {result['taskId']}")

# 运行
asyncio.run(call_aiecs_service())
```

#### 🌐 WebSocket 客户端

```javascript
// Node.js 或浏览器
const io = require('socket.io-client');

const socket = io('http://localhost:8000');

socket.on('connect', () => {
    console.log('连接到 AIECS');
    
    // 注册用户接收更新
    socket.emit('register', { user_id: 'user123' });
});

socket.on('progress', (data) => {
    console.log('任务进度:', data);
});

socket.on('task_complete', (data) => {
    console.log('任务完成:', data);
});
```

---

### 2️⃣ **库导入模式**（Library Import）

适用场景：
- 集成到现有 Python 应用
- 需要细粒度控制
- 自定义配置和初始化
- 嵌入式使用

#### 📦 基础库使用

```python
import asyncio
from aiecs import AIECS, TaskContext, validate_required_settings

async def main():
    # 检查配置（可选）
    try:
        validate_required_settings("llm")
        print("LLM 配置检查通过")
    except ValueError as e:
        print(f"配置缺失: {e}")
        return
    
    # 创建客户端
    client = AIECS()
    
    try:
        # 初始化服务
        await client.initialize()
        
        # 创建任务上下文
        context = TaskContext({
            "user_id": "user123",
            "metadata": {
                "aiPreference": {
                    "provider": "OpenAI",
                    "model": "gpt-4"
                }
            },
            "data": {
                "task": "分析这段文本的情感",
                "content": "今天天气真好，心情很愉快！"
            }
        })
        
        # 执行任务
        result = await client.execute(context)
        print(f"任务结果: {result}")
        
        # 直接执行工具
        tools = await client.get_available_tools()
        print(f"可用工具: {len(tools)} 个")
        
        # 执行具体工具
        if tools:
            tool_result = await client.execute_tool(
                "scraper_tool", 
                "scrape_url", 
                {"url": "https://example.com"}
            )
            print(f"工具执行结果: {tool_result}")
    
    finally:
        # 清理资源
        await client.close()

# 运行
asyncio.run(main())
```

#### 🎯 使用 Session Context Manager（推荐）

```python
import asyncio
from aiecs import AIECS, TaskContext

async def main():
    # 使用 context manager 自动管理资源
    async with AIECS().session() as client:
        # 获取工具
        scraper_tool = await client.get_tool("scraper_tool")
        
        # 直接调用工具方法
        result = await scraper_tool.execute({
            "url": "https://news.ycombinator.com",
            "extract": ["title", "links"]
        })
        
        print(f"抓取结果: {result}")

asyncio.run(main())
```

#### 🔧 自定义配置

```python
from aiecs import AIECS

# 自定义配置
custom_config = {
    "rate_limit_requests_per_second": 10,
    "max_retries": 3,
    "timeout": 60
}

async with AIECS(config=custom_config).session() as client:
    # 使用自定义配置的客户端
    result = await client.execute_tool(
        "research_tool",
        "search",
        {"query": "AI middleware patterns", "max_results": 5}
    )
```

---

### 3️⃣ **FastAPI 集成模式**（FastAPI Integration）

适用场景：
- 已有 FastAPI 应用，想集成 AI 功能
- 需要自定义路由和中间件
- 想要完全控制应用架构
- 微服务架构中的一个组件

#### 🏗️ 子应用挂载方式

```python
# your_main_app.py
from fastapi import FastAPI
from aiecs import get_fastapi_app

# 创建主应用
app = FastAPI(title="我的主应用")

# 挂载 AIECS 应用
aiecs_app = get_fastapi_app()
app.mount("/ai", aiecs_app)

# 添加自己的路由
@app.get("/")
async def root():
    return {"message": "主应用首页"}

@app.get("/custom")  
async def custom_endpoint():
    return {"service": "custom", "status": "active"}

# 现在可以访问：
# http://localhost:8000/          -> 主应用
# http://localhost:8000/custom    -> 自定义端点
# http://localhost:8000/ai/health -> AIECS 健康检查
# http://localhost:8000/ai/api/tools -> AIECS 工具列表
```

#### 🔗 组件级集成

```python
# advanced_integration.py
from fastapi import FastAPI, HTTPException, Depends
from aiecs import AIECS, TaskContext, get_settings, validate_required_settings
from aiecs.tools import get_tool
from typing import Dict, Any

app = FastAPI(title="AI 增强应用")

# 全局 AIECS 客户端
aiecs_client = None

@app.on_event("startup")
async def startup():
    global aiecs_client
    # 验证必要的配置
    try:
        validate_required_settings("llm")
    except ValueError as e:
        print(f"配置缺失，AI 功能将不可用: {e}")
        return
    
    # 初始化 AIECS 客户端
    aiecs_client = AIECS()
    await aiecs_client.initialize()

@app.on_event("shutdown") 
async def shutdown():
    global aiecs_client
    if aiecs_client:
        await aiecs_client.close()

# 依赖注入
async def get_aiecs_client():
    if not aiecs_client:
        raise HTTPException(status_code=503, detail="AI 服务不可用")
    return aiecs_client

# 自定义 AI 端点
@app.post("/api/analyze")
async def analyze_text(
    data: Dict[str, Any],
    client: AIECS = Depends(get_aiecs_client)
):
    """文本分析 API"""
    context = TaskContext({
        "user_id": data.get("user_id", "anonymous"),
        "metadata": {
            "aiPreference": {
                "provider": "OpenAI", 
                "model": "gpt-4"
            }
        },
        "data": {
            "task": "分析文本情感和关键词",
            "content": data["text"]
        }
    })
    
    result = await client.execute(context)
    return {"analysis": result}

@app.post("/api/scrape")
async def scrape_website(
    data: Dict[str, Any],
    client: AIECS = Depends(get_aiecs_client)
):
    """网页抓取 API"""
    result = await client.execute_tool(
        "scraper_tool",
        "scrape_url", 
        {
            "url": data["url"],
            "extract": data.get("extract", ["title", "content"])
        }
    )
    return {"scraped_data": result}

@app.get("/api/tools")
async def get_available_tools(client: AIECS = Depends(get_aiecs_client)):
    """获取可用工具"""
    tools = await client.get_available_tools()
    return {"tools": tools}
```

#### 🎛️ 选择性功能集成

```python
# selective_integration.py
from fastapi import FastAPI
from aiecs.tools import discover_tools, get_tool
from aiecs.config.config import get_settings

app = FastAPI(title="轻量级 AI 应用")

# 只使用工具系统，不启动完整服务
@app.on_event("startup")
async def startup():
    # 发现并注册工具
    discover_tools("aiecs.tools")
    print("工具系统已初始化")

@app.post("/api/quick-scrape")
async def quick_scrape(url: str):
    """快速网页抓取（不使用完整的任务队列）"""
    try:
        scraper = get_tool("scraper_tool")
        result = await scraper.execute({"url": url})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/analyze-document")
async def analyze_document(file_path: str):
    """文档分析"""
    try:
        office_tool = get_tool("office_tool") 
        result = await office_tool.execute({
            "op": "extract_text",
            "file_path": file_path
        })
        return {"text": result}
    except Exception as e:
        return {"error": str(e)}
```

---

## 🔄 **使用方式对比**

| 特性 | 独立服务 | 库导入 | FastAPI 集成 |
|------|----------|--------|-------------|
| **复杂度** | 简单 | 中等 | 高 |
| **控制级别** | 低 | 高 | 最高 |
| **资源消耗** | 高 | 中 | 可控 |
| **分布式支持** | ✅ 完整 | ✅ 完整 | 🔧 可选 |
| **WebSocket** | ✅ 内置 | ❌ 需手动 | 🔧 可选 |
| **自定义路由** | ❌ 固定 | ❌ 无 | ✅ 完全 |
| **启动时间** | 慢 | 快 | 可控 |

---

## ⚙️ **环境配置**

### **最小配置（库使用）**
```env
# 至少配置一个 LLM 提供商
OPENAI_API_KEY=your_openai_key

# Redis（如果使用异步任务）
CELERY_BROKER_URL=redis://localhost:6379/0
```

### **完整配置（独立服务）**
```env
# LLM 提供商
OPENAI_API_KEY=your_openai_key
VERTEX_PROJECT_ID=your_gcp_project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
XAI_API_KEY=your_xai_key

# 基础设施
CELERY_BROKER_URL=redis://localhost:6379/0
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=aiecs
DB_PORT=5432

# Google Cloud Storage（可选）
GOOGLE_CLOUD_PROJECT_ID=your_project
GOOGLE_CLOUD_STORAGE_BUCKET=your_bucket

# CORS（生产环境设置具体域名）
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### **Docker 快速启动**
```yaml
# docker-compose.yml
version: '3.8'
services:
  aiecs:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - DB_HOST=postgres
      - DB_USER=aiecs
      - DB_PASSWORD=password
      - DB_NAME=aiecs
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aiecs
      POSTGRES_USER: aiecs  
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 🎯 **选择建议**

### **选择独立服务，当：**
- 需要为多个应用提供 AI 服务
- 需要 WebSocket 实时通信
- 团队希望即开即用的解决方案
- 需要 Celery 分布式任务处理

### **选择库导入，当：**
- 集成到现有 Python 应用
- 需要细粒度控制和自定义
- 只需要核心 AI 功能
- 希望轻量级部署

### **选择 FastAPI 集成，当：**
- 已有 FastAPI 应用
- 需要自定义 API 端点
- 想要完全控制架构
- 需要混合 AI 和业务逻辑

---

## 🛠️ **开发和调试**

```bash
# 开发模式启动（自动重载）
RELOAD=true aiecs

# 或
uvicorn aiecs.main:app --reload --host 0.0.0.0 --port 8000

# 检查工具可用性
python -c "from aiecs import list_tools; print(list_tools())"

# 验证特定配置
python -c "from aiecs import validate_required_settings; validate_required_settings('llm')"

# 检查版本
python -c "import aiecs; print(aiecs.__version__)"
```

---

## 🔍 **故障排除**

### **常见问题：**

1. **导入失败**：
   ```bash
   # 检查依赖
   pip install aiecs
   
   # 检查版本
   python -c "import aiecs; print('OK')"
   ```

2. **配置错误**：
   ```python
   from aiecs import validate_required_settings
   validate_required_settings("basic")  # 只检查基础功能
   ```

3. **服务启动失败**：
   ```bash
   # 检查端口
   netstat -tulpn | grep :8000
   
   # 检查 Redis
   redis-cli ping
   
   # 检查数据库
   psql -h localhost -U postgres -d aiecs -c "\dt"
   ```

4. **工具执行失败**：
   ```python
   # 检查具体工具
   from aiecs import get_tool
   tool = get_tool("scraper_tool")
   print(tool.describe())  # 查看工具说明
   ```

这样，用户可以根据自己的需求选择最合适的使用方式！
