# Python Middleware for AI Service System

## Structure Overview
- `api/`: FastAPI route handlers
- `core/`: Core framework (prompt loader, registry, config)
- `services/`: Modular AI services (general, multi-task, domain)
- `tools/`: Tool plugins, registered globally
- `rag/`: Embedding, vector store, graph builder
- `tasks/`: Celery async worker
- `utils/`: Logging, helpers

## detial structure
python-middleware/
├── app/
│   ├── main.py                          # FastAPI 启动入口
│   ├── api/
│   │   ├── task_router.py               # POST /tasks 异步入队（Celery）
│   │   ├── stream_router.py             # POST /stream/:mode/:service → StreamingResponse
│   │   └── graph_router.py              # GET /graph/:docId → 向量图谱
│
│   ├── core/
│   │   ├── config.py                    # Pydantic Settings配置管理
│   │   ├── registry.py                  # (mode, service) 注册调度
│   │   ├── prompt_loader.py             # 加载各模式 Prompt
│   │   └── task_context.py              # 用户请求上下文封装（userId, chatId 等）
│
│   ├── services/                        # ✅ 三种模式解耦为 service 模块
│   │   ├── general/
|   |   |   ├── base.py                  # 定义 General 服务接口
│   │   │   ├── services/
│   │   │   │   ├── summarizer.py        # 完整处理链：prompt + tool + respond()
│   │   │   ├── tools.py                 # 模式专属工具选择逻辑（使用统一 tool 注册器）
│   │   │   ├── prompts.yaml             # general 模式专属 prompt
│   │   │   └── tasks.yaml               # 模式 task preset 定义
│   │   ├── multi_task/
|   |   |   ├── base.py                  # 定义 multi-task 服务接口
│   │   │   ├── services/
│   │   │   │   ├── summarizer.py        # 完整处理链：prompt + tool + respond()
│   │   │   ├── tools.py                 # 模式专属工具选择逻辑（使用统一 tool 注册器）
│   │   │   ├── prompts.yaml             # general 模式专属 prompt
│   │   │   └── tasks.yaml               # 模式 task preset 定义
│   │   └── domain/
|   |   |   ├── base.py                  # 定义 domain 服务接口
│   │   │   ├── services/
│   │   │   │   ├── summarizer.py        # 完整处理链：prompt + tool + respond()
│   │   │   ├── tools.py                 # 模式专属工具选择逻辑（使用统一 tool 注册器）
│   │   │   ├── prompts.yaml             # general 模式专属 prompt
│   │   │   └── tasks.yaml               # 模式 task preset 定义
│
│   ├── tools/                           # ✅ 工具系统：注册 + 执行
│   │   ├── base_tool.py                 # 抽象基类 ToolInterface
│   │   ├── __init__.py                  # 注册中心（TOOL_REGISTRY）
│   │   ├── rag.py                       # 文档检索类
│   │   ├── embed.py                     # 向量生成器
│   │   ├── vector_search.py             # 向量检索器
│   │   ├── search_api.py                # 调用外部搜索接口
│   │   └── db_api.py                    # 查询外部数据库
│
│   ├── rag/
│   │   ├── embedding.py                # 文本嵌入封装（Vertex AI）
│   │   ├── vector_store.py             # 向量数据库（Matching Engine 或 Qdrant）
│   │   └── graph_builder.py            # 构建图谱结构
│
│   ├── tasks/
│   │   └── worker.py                   # Celery 异步执行入口（执行 mode + service 逻辑）
│
│   └── utils/
│       └── logging.py
├── Dockerfile
├── requirements.txt
├── celery_worker.py
└── .env

## Getting Started
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run FastAPI:
```bash
uvicorn app.main:app --reload
```

3. Start Celery Worker:
```bash
celery -A app.tasks.worker worker --loglevel=info
```

## Environment Variables
Copy `.env.example` to `.env` and configure the following:

- `OPENAI_API_KEY`
- `VECTOR_DB_PROJECT_ID`
- `CELERY_BROKER_URL`

## Streaming
Call `/stream/:mode/:service` for streamText, yielded chunk-by-chunk from model service.

## Extending
- Add new AI mode in `services/`
- Register tools in `tools/`
- Use RAG modules for vector storage and graph building
