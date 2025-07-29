# Python Middleware for AI Service System

## Architecture Overview

This project follows **Clean Architecture** principles with clear separation of concerns across multiple layers:

- **Domain Layer**: Core business logic and models
- **Application Layer**: Use cases and service orchestration
- **Infrastructure Layer**: External dependencies (database, messaging, monitoring)
- **Config Layer**: Configuration management and service registry
- **Interface Layer**: API endpoints and external interfaces

## Project Structure

```
python-middleware/
├── app/
│   ├── main.py                          # FastAPI application entry point
│   │
│   ├── api/                             # 🌐 API Layer - External interfaces
│   │   ├── stream_router.py             # POST /stream/:mode/:service → StreamingResponse
│   │   ├── graph_router.py              # GET /graph/:docId → vector graph
│   │   └── service_dispatcher.py        # Service routing and dispatch logic
│   │
│   ├── domain/                          # 🏛️ DOMAIN LAYER - Core business logic
│   │   ├── execution/                   # Execution domain
│   │   │   ├── model.py                 # TaskStepResult, TaskStatus, ErrorCode
│   │   │   └── operation_executor.py    # Core execution operations
│   │   └── task/                        # Task domain
│   │       ├── model.py                 # TaskContext, DSLStep models
│   │       ├── task_context.py          # Task context management
│   │       └── dsl_processor.py         # Domain-specific language processing
│   │
│   ├── application/                     # 🔧 APPLICATION LAYER - Use cases
│   │   └── executors/                   # Service execution orchestration
│   │       └── service_executor.py      # Main service execution logic
│   │
│   ├── infrastructure/                  # 🏗️ INFRASTRUCTURE LAYER - External dependencies
│   │   ├── persistence/                 # Data persistence
│   │   │   ├── database_manager.py      # Database operations
│   │   │   └── redis_client.py          # Redis client and operations
│   │   ├── messaging/                   # Message queuing and communication
│   │   │   ├── celery_task_manager.py   # Celery task management
│   │   │   └── websocket_manager.py     # WebSocket communication
│   │   └── monitoring/                  # Observability and metrics
│   │       ├── executor_metrics.py      # Execution metrics collection
│   │       └── tracing_manager.py       # Distributed tracing
│   │
│   ├── config/                          # ⚙️ CONFIG LAYER - Configuration management
│   │   ├── config.py                    # Pydantic settings and environment config
│   │   └── registry.py                  # Service registration and discovery
│   │
│   ├── core/                            # 🔌 CORE INTERFACES - Stable interfaces
│   │   └── interface/                   # Core interface definitions
│   │       └── execution_interface.py   # Execution interface contracts
│   │
│   ├── services/                        # 🤖 SERVICE IMPLEMENTATIONS - AI service modules
│   │   ├── general/                     # General-purpose AI services
│   │   │   ├── base.py                  # General service base class
│   │   │   ├── services/
│   │   │   │   └── summarizer.py        # Text summarization service
│   │   │   ├── prompts.yaml             # General mode prompts
│   │   │   └── tasks.yaml               # Task definitions
│   │   ├── multi_task/                  # Multi-task orchestration services
│   │   │   ├── base.py                  # Multi-task service base class
│   │   │   ├── services/
│   │   │   │   └── summarizer.py        # Multi-task summarization
│   │   │   ├── prompts.yaml             # Multi-task prompts
│   │   │   └── tasks.yaml               # Task definitions
│   │   └── domain/                      # Domain-specific services
│   │       ├── base.py                  # Domain service base class
│   │       ├── services/
│   │       │   └── rag/                 # RAG (Retrieval-Augmented Generation)
│   │       └── kag_core/                # Knowledge-Augmented Generation core
│   │
│   ├── llm/                             # 🧠 LLM CLIENTS - Language model integrations
│   │   ├── base_client.py               # Abstract LLM client interface
│   │   ├── client_factory.py            # LLM client factory
│   │   ├── openai_client.py             # OpenAI API client
│   │   ├── vertex_client.py             # Google Vertex AI client
│   │   └── xai_client.py                # xAI API client
│   │
│   ├── tools/                           # 🛠️ TOOL SYSTEM - Extensible tool plugins
│   │   ├── base_tool.py                 # Abstract tool interface
│   │   ├── tool_executor/               # Tool execution framework
│   │   ├── general_tools/               # General-purpose tools
│   │   ├── rag_tools/                   # RAG-specific tools
│   │   ├── task_tools/                  # Task management tools
│   │   └── out_source/                  # External service integrations
│   │
│   ├── tasks/                           # ⚡ ASYNC PROCESSING - Background task processing
│   │   └── worker.py                    # Celery worker implementation
│   │
│   ├── utils/                           # 🔧 UTILITIES - Helper functions and utilities
│   │   ├── execution_utils.py           # Execution helper functions
│   │   ├── token_usage_repository.py    # Token usage tracking
│   │   └── logging.py                   # Logging configuration
│   │
│   └── ws/                              # 🔌 WEBSOCKET - Real-time communication
│       └── socket_server.py             # Socket.IO server implementation
│
├── scripts/                             # 📜 SCRIPTS - Utility scripts
├── test file/                           # 🧪 TESTS - Test suites
│   ├── api_test/                        # API integration tests
│   ├── core_test/                       # Core functionality tests
│   └── LLM_test/                        # LLM client tests
│
├── Dockerfile                           # 🐳 Docker configuration
├── pyproject.toml                       # 📦 Poetry dependency management
├── docker-compose.yml                   # 🐳 Multi-container setup
└── .env                                 # 🔐 Environment variables
```

## Architecture Principles

### Clean Architecture Benefits
- **Independence**: Business logic is independent of frameworks, UI, and external dependencies
- **Testability**: Core business logic can be tested without external dependencies
- **Flexibility**: Easy to swap out infrastructure components without affecting business logic
- **Maintainability**: Clear separation of concerns makes the codebase easier to understand and modify

### Layer Dependencies
```
API Layer → Application Layer → Domain Layer
Infrastructure Layer → Domain Layer (through interfaces)
Config Layer → All Layers
```

### Key Design Patterns
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Repository Pattern**: Data access abstraction in infrastructure layer
- **Factory Pattern**: LLM client creation and service instantiation
- **Template Method**: Service execution workflow in base classes
- **Registry Pattern**: Service discovery and tool registration

## Getting Started

### Prerequisites
- Python 3.10+
- Poetry for dependency management
- Redis for caching and task queuing
- Docker (optional, for containerized deployment)

### Installation

1. **Install dependencies using Poetry**:
```bash
poetry install
```

2. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start Redis** (if not using Docker):
```bash
redis-server
```

4. **Run the FastAPI application**:
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Start Celery worker** (in a separate terminal):
```bash
poetry run celery -A app.tasks.worker worker --loglevel=info
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Or start in detached mode
docker-compose up -d
```

## Environment Variables

Configure the following environment variables in your `.env` file:

### LLM Provider Configuration
- `OPENAI_API_KEY` - OpenAI API key
- `VERTEX_PROJECT_ID` - Google Cloud project ID for Vertex AI
- `VERTEX_LOCATION` - Vertex AI location (default: us-central1)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google Cloud service account JSON
- `XAI_API_KEY` - xAI API key (optional)

### Infrastructure Configuration
- `CELERY_BROKER_URL` - Redis URL for Celery task queue
- `CORS_ALLOWED_ORIGINS` - Allowed CORS origins (comma-separated)
- `VECTOR_STORE_BACKEND` - Vector store backend (vertex/qdrant)

### Vector Store Configuration
- `VERTEX_INDEX_ID` - Vertex AI Vector Search index ID
- `VERTEX_ENDPOINT_ID` - Vertex AI Vector Search endpoint ID
- `QDRANT_URL` - Qdrant server URL (legacy)
- `QDRANT_COLLECTION` - Qdrant collection name (legacy)

## API Endpoints

### Streaming Services
- `POST /stream/{mode}/{service}` - Stream AI service responses
  - `mode`: general, multi_task, domain
  - `service`: summarizer, etc.

### Graph Operations
- `GET /graph/{doc_id}` - Retrieve document vector graph

### Health Check
- `GET /health` - Application health status

## Service Architecture

### Service Modes
1. **General Services** (`/stream/general/*`)
   - Single-turn AI interactions
   - Text processing, summarization, Q&A
   - Optimized for quick responses

2. **Multi-Task Services** (`/stream/multi_task/*`)
   - Complex workflow orchestration
   - Multi-step task execution
   - User confirmation and feedback loops

3. **Domain Services** (`/stream/domain/*`)
   - Specialized domain knowledge
   - RAG (Retrieval-Augmented Generation)
   - Knowledge graph integration

### Adding New Services

1. **Create service class** in appropriate mode directory:
```python
from app.services.general.base import GeneralServiceBase

@register_ai_service("general", "my_service")
class MyService(GeneralServiceBase):
    async def run(self, input_data, context):
        # Implementation
        pass
```

2. **Add configuration files**:
   - `prompts.yaml` - Service-specific prompts
   - `tasks.yaml` - Task definitions and capabilities

3. **Register tools** (if needed):
```python
from app.tools import register_tool

@register_tool("my_tool")
class MyTool(BaseTool):
    # Implementation
    pass
```

## Development Guidelines

### Code Organization
- Follow clean architecture principles
- Keep domain logic pure (no external dependencies)
- Use dependency injection for infrastructure components
- Implement proper error handling and logging

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test categories
poetry run pytest test_file/api_test/
poetry run pytest test_file/core_test/
poetry run pytest test_file/LLM_test/
```

### Code Quality
```bash
# Format code
poetry run black app/

# Lint code
poetry run flake8 app/

# Type checking
poetry run mypy app/
```

## Monitoring and Observability

### Metrics Collection
- Execution metrics via `infrastructure/monitoring/executor_metrics.py`
- Token usage tracking via `utils/token_usage_repository.py`
- Performance monitoring with distributed tracing

### Logging
- Structured logging with correlation IDs
- Different log levels for development and production
- Centralized logging configuration

### Health Checks
- Application health endpoints
- Dependency health monitoring
- Graceful degradation strategies

## Known Issues & Future Development

### PDF Report Generation (Temporarily Disabled)
**Status**: Disabled due to deployment complexity
**Affected Component**: `app/tools/task_tools/report_tool.py` - `generate_pdf()` method
**Issue**: WeasyPrint dependency has complex system library requirements that cause deployment difficulties.

**Current Workaround**:
- Use `generate_html()` method for HTML reports
- Manual PDF conversion via browser print functionality

**Future Development Plan**:
1. **Phase 1**: Implement alternative PDF generation using playwright or reportlab
2. **Phase 2**: Re-evaluate WeasyPrint with improved Docker setup

### Upcoming Features
- Enhanced multi-modal support (images, audio)
- Advanced workflow orchestration
- Real-time collaboration features
- Enhanced security and authentication
- Performance optimizations and caching strategies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the clean architecture principles
4. Add tests for new functionality
5. Submit a pull request

## License

[Add your license information here]
