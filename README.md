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

### From PyPI (Recommended)

```bash
pip install aiecs
```

### From Source

```bash
# Clone the repository
git clone https://github.com/aiecs-team/aiecs.git
cd aiecs

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Post-Installation Setup

After installation, you can use the built-in tools to set up dependencies and verify your installation:

```bash
# Check all dependencies
aiecs-check-deps

# Quick dependency check
aiecs-quick-check

# Download required NLP models and data
aiecs-download-nlp-data

# Fix common dependency issues automatically
aiecs-fix-deps

# Apply Weasel library patch (if needed)
aiecs-patch-weasel
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

## Command Line Tools

AIECS provides several command-line tools for setup and maintenance:

### Dependency Management

```bash
# Check all dependencies (comprehensive)
aiecs-check-deps

# Quick dependency check
aiecs-quick-check

# Automatically fix missing dependencies
aiecs-fix-deps --non-interactive

# Fix dependencies interactively (default)
aiecs-fix-deps
```

### Setup and Configuration

```bash
# Download required NLP models and data
aiecs-download-nlp-data

# Apply Weasel library patch (fixes validator conflicts)
aiecs-patch-weasel
```

### Main Application

```bash
# Start the AIECS server
aiecs

# Or start with custom configuration
aiecs --host 0.0.0.0 --port 8000
```

## Running as a Service

### Start the API Server

```bash
# Using the aiecs command (recommended)
aiecs

# Using uvicorn directly
uvicorn aiecs.main:app --host 0.0.0.0 --port 8000

# Or using the Python module
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

1. **Missing Dependencies**: Use the built-in dependency checker and fixer:
   ```bash
   # Check what's missing
   aiecs-check-deps

   # Automatically fix issues
   aiecs-fix-deps --non-interactive
   ```

2. **Weasel Library Validator Error**: If you encounter duplicate validator function errors:
   ```bash
   aiecs-patch-weasel
   ```

3. **Missing NLP Models**: Download required models and data:
   ```bash
   aiecs-download-nlp-data
   ```

4. **Database Connection Issues**: Ensure PostgreSQL is running and credentials are correct

5. **Redis Connection Issues**: Verify Redis is running for Celery task queue

### Dependency Check Output

The dependency checker provides detailed information about:
- ✅ Available dependencies
- ❌ Missing critical dependencies
- ⚠️ Missing optional dependencies
- 📦 System-level requirements
- 🤖 AI models and data files

Example output:
```
🔍 AIECS Quick Dependency Check
==================================================

📦 Critical Dependencies:
✅ All critical dependencies are available

🔧 Tool-Specific Dependencies:
   ✅ Image Tool
   ✅ Classfire Tool
   ✅ Office Tool
   ✅ Stats Tool
   ✅ Report Tool
   ✅ Scraper Tool

✅ All dependencies are satisfied!
```

## Development and Packaging

### Building the Package

To build the distribution packages:

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build both wheel and source distribution
python3 -m build --sdist --wheel
```

### Environment Cleanup

For development and before releasing, you may want to clean up the environment completely. Here's the comprehensive cleanup process:

#### 1. Clean Python Cache and Build Files

```bash
# Remove Python cache files
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove build and packaging artifacts
rm -rf build/ *.egg-info/ .eggs/

# Remove test and coverage cache
rm -rf .pytest_cache/ .coverage*
```

#### 2. Clean Log and Temporary Files

```bash
# Remove log files
rm -f *.log dependency_report.txt

# Remove temporary directories
rm -rf /tmp/wheel_*

# Remove backup files
find . -name "*.backup.*" -delete 2>/dev/null || true
```

#### 3. Uninstall AIECS Package (if installed)

```bash
# Uninstall the package completely
pip uninstall aiecs -y

# Verify removal
pip list | grep aiecs || echo "✅ aiecs package completely removed"
```

#### 4. Clean Downloaded NLP Data and Models

If you've used the AIECS NLP tools, you may want to remove downloaded data:

```bash
# Remove NLTK data (stopwords, punkt, wordnet, etc.)
rm -rf ~/nltk_data

# Remove spaCy models
pip uninstall en-core-web-sm zh-core-web-sm spacy-pkuseg -y 2>/dev/null || true

# Verify spaCy models removal
python3 -c "import spacy; print('spaCy models:', spacy.util.get_installed_models())" 2>/dev/null || echo "✅ spaCy models removed"
```

#### 5. Complete Cleanup Script

For convenience, here's a complete cleanup script:

```bash
#!/bin/bash
echo "🧹 Starting complete AIECS environment cleanup..."

# Python cache and build files
echo "📁 Cleaning Python cache and build files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
rm -rf build/ *.egg-info/ .eggs/ .pytest_cache/ .coverage*

# Log and temporary files
echo "📝 Cleaning log and temporary files..."
rm -f *.log dependency_report.txt
rm -rf /tmp/wheel_*
find . -name "*.backup.*" -delete 2>/dev/null || true

# Uninstall package
echo "🗑️ Uninstalling AIECS package..."
pip uninstall aiecs -y 2>/dev/null || true

# Clean NLP data
echo "🤖 Cleaning NLP data and models..."
rm -rf ~/nltk_data
pip uninstall en-core-web-sm zh-core-web-sm spacy-pkuseg -y 2>/dev/null || true

# Verify final state
echo "✅ Cleanup complete! Final package state:"
ls -la dist/ 2>/dev/null || echo "No dist/ directory found"
echo "Environment is now clean and ready for release."
```

#### What Gets Preserved

The cleanup process preserves:
- ✅ Source code files
- ✅ Test files and coverage reports (for maintenance)
- ✅ Configuration files (`.gitignore`, `pyproject.toml`, etc.)
- ✅ Documentation files
- ✅ Final distribution packages in `dist/`

#### What Gets Removed

The cleanup removes:
- ❌ Python cache files (`__pycache__/`, `*.pyc`)
- ❌ Build artifacts (`build/`, `*.egg-info/`)
- ❌ Log files (`*.log`, `dependency_report.txt`)
- ❌ Installed AIECS package and command-line tools
- ❌ Downloaded NLP data and models (~110MB)
- ❌ Temporary and backup files

### Release Preparation

After cleanup, your `dist/` directory should contain only:

```
dist/
├── aiecs-1.0.0-py3-none-any.whl  # Production-ready wheel package
└── aiecs-1.0.0.tar.gz            # Production-ready source package
```

These packages are ready for:
- PyPI publication: `twine upload dist/*`
- GitHub Releases
- Private repository distribution

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
