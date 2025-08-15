# AIECS - AI Execute Services

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/aiecs.svg)](https://badge.fury.io/py/aiecs)

AIECS (AI Execute Services) is a powerful Python middleware framework for building AI-powered applications with tool orchestration, task execution, and multi-provider LLM support.

## Features

- **Multi-Provider LLM Support**: Seamlessly integrate with OpenAI, Google Vertex AI, and xAI
- **Tool Orchestration**: Extensible tool system for various tasks (web scraping, data analysis, document processing, etc.)
- **Asynchronous Task Execution**: Built on Celery for scalable task processing
- **Real-time Communication**: WebSocket support for live updates and progress tracking
- **Enterprise-Ready**: Production-grade architecture with PostgreSQL, Redis, and Google Cloud Storage integration
- **Extensible Architecture**: Easy to add custom tools and AI providers

## Installation

```bash
pip install aiecs
```

## Quick Start

### Basic Usage

```python
from aiecs import AIECS
from aiecs.domain.task.task_context import TaskContext

# Initialize AIECS
aiecs = AIECS()

# Create a task context
context = TaskContext(
    mode="execute",
    service="default",
    user_id="user123",
    metadata={
        "aiPreference": {
            "provider": "OpenAI",
            "model": "gpt-4"
        }
    },
    data={
        "task": "Analyze this text and extract key points",
        "content": "Your text here..."
    }
)

# Execute task
result = await aiecs.execute(context)
print(result)
```

### Using Tools

```python
from aiecs.tools import get_tool

# Get a specific tool
scraper = get_tool("scraper_tool")

# Execute tool
result = await scraper.execute({
    "url": "https://example.com",
    "extract": ["title", "content"]
})
```

### Custom Tool Development

```python
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

@register_tool("my_custom_tool")
class MyCustomTool(BaseTool):
    """Custom tool for specific tasks"""
    
    name = "my_custom_tool"
    description = "Does something specific"
    
    async def execute(self, params: dict) -> dict:
        # Your tool logic here
        return {"result": "success"}
```

## Configuration

Create a `.env` file with the following variables:

```env
# LLM Providers
OPENAI_API_KEY=your_openai_key
VERTEX_PROJECT_ID=your_gcp_project
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
XAI_API_KEY=your_xai_key

# Database
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=aiecs_db
DB_PORT=5432

# Redis (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0

# Google Cloud Storage
GOOGLE_CLOUD_PROJECT_ID=your_project_id
GOOGLE_CLOUD_STORAGE_BUCKET=your_bucket_name

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Running as a Service

### Start the API Server

```bash
# Using uvicorn directly
uvicorn aiecs.main:app --host 0.0.0.0 --port 8000

# Or using the entry point
python -m aiecs
```

### Start Celery Workers

```bash
# Start worker
celery -A aiecs.tasks.worker.celery_app worker --loglevel=info

# Start beat scheduler (for periodic tasks)
celery -A aiecs.tasks.worker.celery_app beat --loglevel=info

# Start Flower (Celery monitoring)
celery -A aiecs.tasks.worker.celery_app flower
```

## API Endpoints

- `GET /health` - Health check
- `GET /api/tools` - List available tools
- `GET /api/services` - List available AI services
- `GET /api/providers` - List LLM providers
- `POST /api/execute` - Execute a task
- `GET /api/task/{task_id}` - Get task status
- `DELETE /api/task/{task_id}` - Cancel a task

## WebSocket Events

Connect to the WebSocket endpoint for real-time updates:

```javascript
const socket = io('http://localhost:8000');

socket.on('connect', () => {
    console.log('Connected to AIECS');
    
    // Register user for updates
    socket.emit('register', { user_id: 'user123' });
});

socket.on('progress', (data) => {
    console.log('Task progress:', data);
});
```

## Available Tools

AIECS comes with a comprehensive set of pre-built tools:

- **Web Tools**: Web scraping, search API integration
- **Data Analysis**: Pandas operations, statistical analysis
- **Document Processing**: PDF, Word, PowerPoint handling
- **Image Processing**: OCR, image manipulation
- **Research Tools**: Academic research, report generation
- **Chart Generation**: Data visualization tools

## Architecture

AIECS follows a clean architecture pattern with clear separation of concerns:

```
aiecs/
├── domain/         # Core business logic
├── application/    # Use cases and application services
├── infrastructure/ # External services and adapters
├── llm/           # LLM provider implementations
├── tools/         # Tool implementations
├── config/        # Configuration management
└── main.py        # FastAPI application entry point
```

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/aiecs.git
cd aiecs

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
flake8 aiecs/
mypy aiecs/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

1. **Weasel Library Validator Error**: If you encounter duplicate validator function errors, run the included patch:
   ```bash
   python -m aiecs.scripts.fix_weasel_validator
   ```

2. **Database Connection Issues**: Ensure PostgreSQL is running and credentials are correct

3. **Redis Connection Issues**: Verify Redis is running for Celery task queue

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with FastAPI, Celery, and modern Python async patterns
- Integrates with leading AI providers
- Inspired by enterprise-grade middleware architectures

## Support

- Documentation: [https://aiecs.readthedocs.io](https://aiecs.readthedocs.io)
- Issues: [GitHub Issues](https://github.com/yourusername/aiecs/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/aiecs/discussions)

---

Made with ❤️ by the AIECS Team
