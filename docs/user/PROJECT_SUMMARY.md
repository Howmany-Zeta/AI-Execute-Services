# AIECS Project Migration Summary

## Completed Tasks

### 1. Project Renaming ✓
- Successfully renamed "app" directory to "aiecs" (AI Execute Services)
- Updated all internal references from `app.` to `aiecs.`
- Ensured all import paths are correct

### 2. Main.py Entry File ✓
Created complete `aiecs/main.py` file, including:
- FastAPI application setup
- WebSocket integration
- Health check endpoints
- Task execution API
- Tool list API
- Service and provider information API
- Complete lifecycle management

### 3. README Documentation ✓
Created professional README.md, including:
- Project introduction and features
- Installation instructions
- Quick start guide
- Configuration instructions
- API documentation
- Architecture description
- Development guide

### 4. PyProject.toml Configuration ✓
Updated pyproject.toml:
- Changed project name to "aiecs"
- Added complete metadata
- Configured correct dependencies
- Added classifiers and keywords
- Configured build system

### 5. Scripts Dependency Patches ✓
- Moved scripts directory into aiecs package
- Updated `fix_weasel_validator.py` to adapt to new structure
- Created `setup.py` file with post-install hooks
- Configured automatic weasel patch execution mechanism

### 6. NLP Data Package Auto-Download ✓
- Created comprehensive `download_nlp_data.py` script to automatically download NLP data packages required by classfire_tool
- Automatically downloads NLTK stopwords, punkt, and other data packages (required by rake-nltk and text processing)
- Automatically downloads spaCy English model en_core_web_sm (required)
- Automatically downloads spaCy Chinese model zh_core_web_sm (optional)
- Integrated into post-install hooks, automatically executed during installation
- Provides multiple manual execution methods:
  - `aiecs-download-nlp-data`: Python script command
  - `./aiecs/scripts/setup_nlp_data.sh`: Convenient shell script
- Includes complete error handling, logging, and installation verification
- Supports automatic virtual environment detection and activation

## Additional Completed Work

1. **Created `__main__.py`**
   - Allows running service via `python -m aiecs`

2. **Created LICENSE file**
   - MIT License

3. **Created MANIFEST.in**
   - Ensures all necessary files are included in distribution package

4. **Created .gitignore**
   - Prevents unnecessary files from entering version control

5. **Created PUBLISH.md**
   - Detailed PyPI publishing guide

6. **Created test scripts**
   - `test_import.py` for verifying package structure

## Project Structure

```
python-middleware-dev/
├── aiecs/                    # Main package directory (formerly app)
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── main.py              # FastAPI application
│   ├── scripts/             # Automation scripts
│   │   ├── __init__.py
│   │   ├── fix_weasel_validator.py    # weasel library patch
│   │   ├── download_nlp_data.py       # NLP data package download
│   │   └── ...
│   └── ... (other modules)
├── setup.py                 # Installation configuration (with post-install)
├── pyproject.toml          # Project metadata
├── README.md               # Project documentation
├── LICENSE                 # MIT License
├── MANIFEST.in            # Include file manifest
├── PUBLISH.md             # Publishing guide
└── .gitignore             # Git ignore file
```

## Publishing Preparation

The project is now ready to publish to PyPI. Publishing steps:

1. **Install build tools**
   ```bash
   pip install build twine
   ```

2. **Build package**
   ```bash
   python -m build
   ```

3. **Test installation**
   ```bash
   pip install dist/aiecs-1.0.0-py3-none-any.whl
   ```

4. **Upload to TestPyPI** (recommended to test first)
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

5. **Upload to PyPI**
   ```bash
   python -m twine upload dist/*
   ```

## Usage Instructions

After installation, users can:

1. **Use as a library**
   ```python
   from aiecs import AIECS
   from aiecs.domain.task.task_context import TaskContext
   ```

2. **Run service**
   ```bash
   aiecs  # or python -m aiecs
   ```

3. **Run weasel patch** (if automatic patch fails)
   ```bash
   aiecs-patch-weasel
   ```

4. **Download NLP data packages** (if automatic download fails)
   ```bash
   # Use Python script command (recommended)
   aiecs-download-nlp-data
   
   # Or use shell script
   ./aiecs/scripts/setup_nlp_data.sh
   
   # Only verify installed data packages
   ./aiecs/scripts/setup_nlp_data.sh --verify
   ```

## Important Notes

1. Users need to configure environment variables (.env file) to use normally
2. PostgreSQL and Redis services are required for full operation
3. Weasel patch will automatically attempt to execute during installation
4. NLP data packages (NLTK stopwords and spaCy en_core_web_sm) will automatically download during installation
5. **Image Tool requires system-level Tesseract OCR to use OCR functionality**
6. **Java Environment and Apache Tika (Optional Dependency)**:
   - Office Tool's text extraction functionality uses Apache Tika as a universal fallback solution
   - Tika supports text extraction from 1000+ document formats (including legacy Office formats)
   - Requires Java Runtime Environment (JRE) 8+ to use
   - If Java environment is not available, Tika-related tests will be automatically skipped, not affecting other functionality
   - Recommended to install Java in enterprise environments or when processing multiple document formats
7. Project supports Python 3.10-3.12

## Automation Features

### NLP Data Package Management
- **Auto-Download**: Automatically downloads NLP data packages required by classfire_tool during installation
  - NLTK stopwords, punkt, and other data packages
  - spaCy English model en_core_web_sm (required)
  - spaCy Chinese model zh_core_web_sm (optional)
- **Multiple Execution Methods**:
  - Python script: `aiecs-download-nlp-data`
  - Shell script: `./aiecs/scripts/setup_nlp_data.sh`
  - Verification mode: `./aiecs/scripts/setup_nlp_data.sh --verify`
- **Advanced Features**:
  - Automatic virtual environment detection and activation
  - Dependency integrity checking
  - Download progress and status logging
  - Post-installation verification tests
  - Intelligent detection of existing data packages
  - Timeout protection (prevents long hangs)
- **Error Handling**: Download failures do not block the entire installation process, detailed logs are generated

### Java/Tika Integration Management
- **Function Positioning**: Apache Tika serves as Office Tool's universal text extraction fallback solution
- **Supported Formats**: 
  - Dedicated library processing: DOCX, PPTX, XLSX (using python-docx/python-pptx/pandas)
  - PDF documents (using pdfplumber)
  - Image OCR (using pytesseract)
  - **Tika-processed formats**: Legacy Office (.doc/.xls/.ppt), RTF, ODF, e-books, and 1000+ formats
- **Environment Detection**:
  - Automatically detects Java runtime environment
  - Gracefully skips during testing (if Java unavailable)
  - Provides degradation handling at runtime
- **Deployment Recommendations**:
  - **Development Environment**: Java optional, convenient for complete testing
  - **Production Environment**: Decide based on document processing requirements
  - **Docker Deployment**: Provides both Java-enabled and pure Python image options
- **Error Handling**: Tika unavailability does not affect other document processing functionality, warning logs are recorded

## Java Environment Configuration Guide

### Installing Java Runtime Environment

#### Linux (Ubuntu/Debian)
```bash
# Install OpenJDK 11 (recommended)
sudo apt update
sudo apt install openjdk-11-jre-headless

# Or install OpenJDK 8 (minimum requirement)
sudo apt install openjdk-8-jre-headless

# Verify installation
java -version
```

#### Linux (CentOS/RHEL/Fedora)
```bash
# CentOS/RHEL
sudo yum install java-11-openjdk-headless

# Fedora
sudo dnf install java-11-openjdk-headless

# Verify installation
java -version
```

#### macOS
```bash
# Using Homebrew
brew install openjdk@11

# Or download Oracle JDK
# Visit https://www.oracle.com/java/technologies/downloads/

# Verify installation
java -version
```

#### Windows
```batch
# Using Chocolatey
choco install openjdk11

# Or using Scoop
scoop install openjdk

# Or manually download and install
# Visit https://adoptium.net/ to download Eclipse Temurin

# Verify installation
java -version
```

### Verifying Tika Functionality

After installing Java, you can verify if Tika functionality works correctly:

```python
from aiecs.tools.task_tools.office_tool import OfficeTool

# Create tool instance
tool = OfficeTool()

# Test Tika text extraction (using any document file)
try:
    text = tool.extract_text("path/to/your/document.doc")
    print("Tika functionality working correctly")
except Exception as e:
    print(f"Tika unavailable: {e}")
```

## Docker Configuration Guide

### Basic Python Image (Without Java)

```dockerfile
# Dockerfile.python-only
FROM python:3.11-slim

# Install system dependencies (Tesseract OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install -e .

# Start command
CMD ["python", "-m", "aiecs"]
```

### Complete Image with Java

```dockerfile
# Dockerfile.with-java
FROM python:3.11-slim

# Install system dependencies (including Java and Tesseract)
RUN apt-get update && apt-get install -y \
    openjdk-11-jre-headless \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME environment variable
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install -e .

# Verify Java installation
RUN java -version

# Start command
CMD ["python", "-m", "aiecs"]
```

### Docker Compose Configuration

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

### Multi-Stage Build (Recommended for Production)

```dockerfile
# Dockerfile.multi-stage
# Build stage
FROM python:3.11 as builder

WORKDIR /app
COPY pyproject.toml setup.py ./
COPY aiecs/ ./aiecs/

# Install build dependencies
RUN pip install build
RUN python -m build

# Runtime stage - Pure Python
FROM python:3.11-slim as python-runtime

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl

CMD ["python", "-m", "aiecs"]

# Runtime stage - With Java
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

### Build and Run Commands

```bash
# Build pure Python image
docker build -f Dockerfile.python-only -t aiecs:python-only .

# Build image with Java
docker build -f Dockerfile.with-java -t aiecs:with-java .

# Use multi-stage build
docker build --target python-runtime -t aiecs:python-runtime .
docker build --target java-runtime -t aiecs:java-runtime .

# Run container
docker run -p 8000:8000 aiecs:with-java

# Use Docker Compose
docker-compose up aiecs-with-java
```

### Environment Variable Configuration

Create `.env` file for Docker environment:

```bash
# .env
# Database configuration
DATABASE_URL=postgresql://aiecs:aiecs_password@postgres:5432/aiecs

# Redis configuration
REDIS_URL=redis://redis:6379/0

# Java configuration (optional)
JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
TIKA_SERVER_JAR=/usr/share/java/tika-server.jar

# Other configuration
PYTHONPATH=/app
LOG_LEVEL=INFO
```

### Verify Docker Deployment

```bash
# Enter container to verify environment
docker exec -it <container_id> bash

# Verify Python environment
python -c "from aiecs import AIECS; print('AIECS OK')"

# Verify Java environment (if installed)
java -version

# Verify Tika functionality
python -c "
from aiecs.tools.task_tools.office_tool import OfficeTool
tool = OfficeTool()
print('Tika available:', hasattr(tool, '_extract_tika_text'))
"

# Verify OCR functionality
tesseract --version
```

### Image Size Comparison

- **Pure Python Image**: ~800MB
- **Image with Java**: ~1.2GB
- **Full Feature Image**: ~1.5GB (includes all dependencies)

Choose the appropriate image configuration based on actual requirements!

Project migration completed! 🎉
