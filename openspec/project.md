# Project Context

## Purpose
AIECS (AI Execute Services) is a powerful Python middleware framework for building AI-powered applications with tool orchestration, task execution, and multi-provider LLM support. The project aims to provide an enterprise-ready platform for integrating AI capabilities into applications through a clean architecture with extensible tools, asynchronous task processing, and real-time communication.

## Tech Stack

### Core Framework
- **Python**: 3.10+ (primary language)
- **FastAPI**: 0.115.x (modern web framework for building APIs)
- **Uvicorn**: 0.34.x (ASGI server with WebSocket support)
- **Pydantic**: 2.11.x (data validation and settings management)

### Task Queue and Messaging
- **Celery**: 5.5.x (distributed task queue)
- **Redis**: 6.2.x (in-memory data store for Celery broker/backend)
- **Socket.IO**: 5.13.x (WebSocket for real-time communication)
- **Flower**: 2.0.x (Celery monitoring)

### AI and LLM Services
- **OpenAI**: 1.68.x+ (GPT models)
- **Google Cloud AI Platform**: 1.80.x (Vertex AI)
- **Google Generative AI**: 0.8.x (Gemini models)
- **xAI**: Support for xAI models
- **LangChain**: 0.3.x (LLM application framework)
- **LangGraph**: 0.5.x (graph-based state machine)

### Data Processing
- **NumPy**: 2.2.x (numerical computing)
- **Pandas**: 2.2.x (data analysis)
- **SciPy**: 1.15.x (scientific computing)
- **scikit-learn**: 1.5.x (machine learning)
- **Statsmodels**: 0.14.x (statistical models)

### NLP and Language Processing
- **spaCy**: 3.8.x (industrial-strength NLP)
- **RAKE-NLTK**: 1.0.x (keyword extraction)
- **Weasel**: 0.4.1 (spaCy's configuration system)

### Document Processing
- **python-docx**: 1.1.x (Word documents)
- **python-pptx**: 1.0.x (PowerPoint presentations)
- **openpyxl**: 3.1.x (Excel files)
- **pdfplumber**: 0.11.x (PDF extraction)
- **pdfminer-six**: 20250506 (PDF parsing)
- **Apache Tika**: 2.6.x (content analysis)

### Web Scraping and Content
- **BeautifulSoup4**: 4.13.x (HTML/XML parsing)
- **lxml**: 5.4.x (XML/HTML processing)
- **Playwright**: 1.52.x (browser automation)
- **Scrapy**: 2.13.x (web scraping framework)
- **PyTesseract**: 0.3.x (OCR wrapper)
- **Pillow**: 11.2.x (image processing)

### Visualization
- **Matplotlib**: 3.10.x (plotting library)
- **Seaborn**: 0.13.x (statistical visualization)

### Database and Storage
- **SQLAlchemy**: 2.0.x (SQL toolkit and ORM)
- **asyncpg**: 0.30.x (PostgreSQL async driver)
- **PostgreSQL**: (primary database)
- **Google Cloud Storage**: (file storage)

### Monitoring and Observability
- **Prometheus**: 0.21.x (metrics client)
- **Jaeger**: 4.8.x (distributed tracing)
- **OpenTracing**: 2.4.x (tracing API)
- **psutil**: 7.0.x (system monitoring)

### Development Tools
- **pytest**: 8.3.x+ (testing framework)
- **pytest-asyncio**: 1.0.x+ (async testing)
- **pytest-cov**: 4.0.x+ (coverage reporting)
- **pytest-xdist**: 3.0.x+ (parallel testing)
- **black**: 25.1.x+ (code formatter)
- **flake8**: 7.2.x+ (linter)
- **mypy**: 1.15.x+ (type checker)

## Project Conventions

### Code Style
- **Line Length**: 100 characters (enforced by black)
- **Formatting**: Black formatter with Python 3.8+ target
- **Type Hints**: Strongly encouraged, validated with mypy
- **Naming Conventions**:
  - Snake_case for functions, variables, and module names
  - PascalCase for class names
  - UPPER_CASE for constants
- **Imports**: Organized by standard library, third-party, and local imports
- **Docstrings**: Use for all public modules, classes, and functions

### Architecture Patterns
- **Clean Architecture**: Clear separation of concerns with layered architecture
  - `domain/`: Core business logic (entities, value objects)
  - `application/`: Use cases and application services
  - `infrastructure/`: External services and adapters (database, messaging, monitoring)
  - `llm/`: LLM provider implementations
  - `tools/`: Tool implementations and orchestration
  - `config/`: Configuration management
  - `main.py`: FastAPI application entry point

- **Dependency Injection**: Minimal dependencies between layers
- **Async First**: Async/await patterns throughout for better performance
- **Event-Driven**: WebSocket for real-time updates and events
- **Tool Pattern**: Extensible tool system using decorator-based registration
- **Provider Pattern**: Multi-provider support for LLM services

### Testing Strategy
- **Testing Framework**: pytest with asyncio support
- **Test Organization**:
  - `test/unit_tests/`: Unit tests for individual components
  - `test/community_test/`: Community and integration tests
  - `test/reference/`: Reference implementations and examples
- **Test Markers**:
  - `asyncio`: Async tests
  - `slow`: Long-running tests
  - `integration`: Integration tests
  - `unit`: Unit tests
  - `network`: Tests requiring network
  - `ai_required`: Tests requiring AI services
  - `cloud`: Tests requiring cloud services
  - `security`: Security-related tests
  - `performance`: Performance tests
- **Coverage**: Use pytest-cov for coverage reports
- **Test Execution**: 
  - Parallel execution supported via pytest-xdist
  - 300-second timeout for tests
  - Verbose output with short traceback format
- **Async Testing**: Auto mode with function-scoped event loops

### Git Workflow
- **Branch Strategy**: Feature branches merged to main
- **Commit Conventions**: Clear, descriptive commit messages
- **Exclusions**: Tests, logs, build artifacts, credentials are gitignored
- **Code Review**: All changes should be reviewed before merging
- **CI/CD**: Automated testing and validation on pull requests

## Domain Context

### AI Middleware Framework
AIECS serves as middleware between applications and AI services. It provides:
- **Tool Orchestration**: Extensible system for various tasks (web scraping, data analysis, document processing, image processing, research)
- **Task Execution**: Asynchronous processing via Celery with progress tracking
- **Multi-Provider LLM**: Seamless switching between OpenAI, Google Vertex AI, xAI, and other providers
- **Real-time Communication**: WebSocket support for live task updates
- **Task Context**: Rich context management for task execution with user preferences, metadata, and service configuration

### Key Capabilities
1. **Tool System**: Registry-based tool management with declarative tool registration
2. **LLM Abstraction**: Provider-agnostic interface for different AI services
3. **Task Queue**: Scalable background task processing with Celery
4. **Document Processing**: Extract content from PDF, Word, PowerPoint, Excel
5. **Web Scraping**: Static and dynamic content extraction
6. **Data Analysis**: Statistical analysis and visualization
7. **Research Tools**: Academic research and report generation
8. **Monitoring**: Prometheus metrics and Jaeger tracing

### Command-Line Tools
- `aiecs`: Start the AIECS server
- `aiecs-check-deps`: Comprehensive dependency checker
- `aiecs-quick-check`: Quick dependency validation
- `aiecs-fix-deps`: Automated dependency fixing
- `aiecs-download-nlp-data`: Download required NLP models
- `aiecs-patch-weasel`: Fix Weasel library validator conflicts
- `aiecs-tools-check-annotations`: Validate tool type annotations
- `aiecs-tools-validate-schemas`: Validate tool schemas

## Important Constraints

### Technical Constraints
- **Python Version**: Requires Python 3.10 or higher, but must be < 3.13
- **Memory**: NLP models and data require ~110MB+ of disk space
- **Dependencies**: Complex dependency tree with potential conflicts (e.g., Weasel validator issues)
- **Async Requirements**: All I/O operations should be async where possible
- **Database**: PostgreSQL required for persistence
- **Cache/Queue**: Redis required for Celery task queue

### Operational Constraints
- **Environment Variables**: Extensive configuration via .env files
- **API Keys**: Requires API keys for OpenAI, Google Cloud, xAI
- **Google Cloud**: Requires GCP credentials for Vertex AI and Cloud Storage
- **Browser Dependencies**: Playwright requires browser installation for web scraping
- **OCR Requirements**: Tesseract must be installed separately for OCR functionality
- **Apache Tika**: May require Java runtime for some document processing features

### Security Constraints
- **API Keys**: Never commit .env files or API keys to version control
- **CORS**: Configure allowed origins properly for production
- **Input Validation**: All user inputs validated via Pydantic models
- **HTML Sanitization**: Use bleach for sanitizing HTML content

### Performance Constraints
- **Async Processing**: Long-running tasks must use Celery workers
- **WebSocket**: Real-time updates for task progress
- **Caching**: Use Redis for caching when appropriate
- **Resource Limits**: Monitor system resources with psutil

## External Dependencies

### Cloud Services
- **Google Cloud Platform**:
  - Vertex AI (LLM inference)
  - Cloud Storage (file storage)
  - Custom Search API (web search)
  - Application credentials required
- **OpenAI**: API access for GPT models
- **xAI**: API access for xAI models

### Infrastructure Services
- **PostgreSQL**: Primary database for persistence
- **Redis**: Cache and Celery broker/backend
- **Apache Tika Server**: (optional) For advanced document parsing

### External APIs
- **Google Custom Search**: For web search functionality
- **OpenAI API**: For GPT model access
- **Vertex AI API**: For Google model access
- **xAI API**: For xAI model access

### System Dependencies
- **Tesseract OCR**: For optical character recognition
- **Playwright browsers**: Chromium/Firefox/WebKit for browser automation
- **System libraries**: Various C libraries for image processing, PDF parsing
