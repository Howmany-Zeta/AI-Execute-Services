# Tools Architecture

This directory contains tools that provide various functionalities for the application. The tools architecture has been refactored to separate business logic from performance optimization concerns and uses a layered architecture to organize different types of tools.

## Directory Structure

```
app/tools/
├── __init__.py              # Tool registry and discovery mechanism
├── base_tool.py            # Base tool class
├── temp_file_manager.py    # Temporary file management tool
├── README.md               # This document
├── task_tools/             # Task-oriented tools
│   ├── __init__.py
│   ├── chart_tool.py       # Chart and visualization tools
│   ├── classfire_tool.py   # Classification and categorization tools
│   ├── image_tool.py       # Image processing tools
│   ├── office_tool.py      # Office document processing tools
│   ├── pandas_tool.py      # Data analysis and processing tools
│   ├── report_tool.py      # Report generation tools
│   ├── research_tool.py    # Research and information gathering tools
│   ├── scraper_tool.py     # Web scraping tools
│   ├── search_api.py       # Search engine API integration tools
│   └── stats_tool.py       # Statistical analysis tools
├── general_tools/          # General tools (reserved)
├── rag_tools/             # RAG-related tools (reserved)
└── out_source/            # External integration tools (reserved)
```

## New Architecture

The new architecture includes the following components:

1. **Tool Executor** (`app/core/tool_executor.py`): A centralized execution framework that handles the following cross-cutting concerns:
   - Input validation
   - Caching
   - Concurrency
   - Error handling
   - Performance optimization
   - Logging

2. **Base Tool Class** (`app/tools/base_tool.py`): A base class that all tools should inherit from, providing:
   - Integration with the tool executor
   - Schema-based input validation
   - Standardized error handling
   - Automatic schema discovery

3. **Tool Registry** (`app/tools/__init__.py`): Handles tool registration and retrieval:
   - Tool registration
   - Tool retrieval
   - Automatic tool discovery
   - Layered module imports

4. **Layered Tool Organization**:
   - **task_tools**: Specialized task-oriented tools for specific business scenarios
   - **general_tools**: General tools providing basic functionality
   - **rag_tools**: RAG (Retrieval-Augmented Generation) related tools
   - **out_source**: External service integration tools

## Tool Categories

### Task Tools
Located in the `task_tools/` directory, containing tools specialized for specific tasks:

- **chart_tool**: Chart generation and data visualization
- **classfire_tool**: Data classification and categorization
- **image_tool**: Image processing and manipulation
- **office_tool**: Office document processing (Word, Excel, PowerPoint)
- **pandas_tool**: Data analysis and DataFrame operations
- **report_tool**: Report generation and formatting
- **research_tool**: Research and information gathering
- **scraper_tool**: Web data scraping
- **search_api**: Search engine API integration
- **stats_tool**: Statistical analysis and computation

## Using Base Tool Class

To create a new tool, inherit from the `BaseTool` class and implement your business logic methods:

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

@register_tool("my_tool")
class MyTool(BaseTool):
    """My tool description"""

    # Define input schema for operations
    class OperationSchema(BaseModel):
        """Operation schema"""
        param1: str = Field(description="Parameter 1")
        param2: int = Field(description="Parameter 2")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize tool"""
        super().__init__(config)
        # Additional initialization

    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        Implement your business logic here

        Args:
            param1: Parameter 1
            param2: Parameter 2

        Returns:
            Operation result
        """
        # Your business logic
        return {"result": f"Processing {param1} and {param2}"}
```

## Using Decorators for Performance Optimization

The tool executor provides several decorators that you can use to add performance optimizations to methods:

```python
from aiecs.tools.tool_executor import cache_result, run_in_executor, measure_execution_time

@cache_result()  # Cache the result of this method
def cached_operation(self, param1: str) -> Dict[str, Any]:
    # This result will be cached based on param1
    return {"result": f"Cached result {param1}"}

@run_in_executor  # Run this method in a thread pool
def cpu_intensive_operation(self, param1: str) -> Dict[str, Any]:
    # This method will be executed in a separate thread
    return {"result": f"CPU-intensive result {param1}"}

@measure_execution_time  # Record the execution time of this method
def monitored_operation(self, param1: str) -> Dict[str, Any]:
    # The execution time of this method will be recorded
    return {"result": f"Monitored result {param1}"}
```

## Migrating Existing Tools

To migrate existing tools to the new architecture:

1. Make your tool class inherit from `BaseTool`
2. Define Pydantic schemas for your operations
3. Remove any custom caching, validation, or error handling code
4. Use decorators for performance optimization
5. Update the `run` method to use the base class implementation

### Before:

```python
@register_tool("example")
class ExampleTool:
    def __init__(self):
        self._cache = {}

    def run(self, op: str, **kwargs):
        if op == "operation":
            return self.operation(**kwargs)
        else:
            raise ValueError(f"Unsupported operation: {op}")

    def operation(self, param1: str, param2: int):
        # Custom caching
        cache_key = f"{param1}_{param2}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Custom validation
        if not isinstance(param1, str):
            raise ValueError("param1 must be a string")
        if not isinstance(param2, int):
            raise ValueError("param2 must be an integer")

        # Business logic
        result = {"result": f"Processing {param1} and {param2}"}

        # Cache result
        self._cache[cache_key] = result

        return result
```

### After:

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import cache_result

@register_tool("example")
class ExampleTool(BaseTool):
    """Example tool"""

    class OperationSchema(BaseModel):
        """Operation schema"""
        param1: str = Field(description="Parameter 1")
        param2: int = Field(description="Parameter 2")

    @cache_result()
    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        Process parameters

        Args:
            param1: Parameter 1
            param2: Parameter 2

        Returns:
            Operation result
        """
        # Focus only on business logic
        return {"result": f"Processing {param1} and {param2}"}
```

## Benefits of the New Architecture

The new architecture provides several benefits:

1. **Separation of Concerns**: Business logic is separated from cross-cutting concerns like caching, validation, and error handling.

2. **Reduced Duplication**: Common functionality is implemented once in the tool executor and base tool, rather than being duplicated across individual tools.

3. **Consistent Behavior**: All tools behave consistently in terms of validation, error handling, and performance optimization.

4. **Improved Maintainability**: Tools are easier to maintain because they focus only on specific business logic.

5. **Enhanced Performance**: The tool executor provides optimized implementations of caching, concurrency, and other performance features.

6. **Better Testing**: Business logic can be tested independently of cross-cutting concerns.

7. **Easier Onboarding**: New developers can focus on implementing business logic without worrying about performance optimization details.

## Usage Examples

```python
# Get tool instance
from aiecs.tools import get_tool

# Get chart tool
chart_tool = get_tool("chart")

# Use tool
result = chart_tool.run("visualize",
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="Age Distribution"
)

# Or call method directly
result = chart_tool.visualize(
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="Age Distribution"
)

```

## Multi-Task Service Integration

The tool system is fully integrated with the MultiTaskTools service in `app/services/multi_task/tools.py`:

```python
from aiecs.services.multi_task.tools import MultiTaskTools

# Initialize multi-task tools service
multi_tools = MultiTaskTools()

# Get all available tools
available_tools = multi_tools.get_available_tools()
print("Available tools:", available_tools)

# Get operations for a specific tool
chart_operations = multi_tools.get_available_operations("chart")
print("Chart tool operations:", chart_operations)

# Get operation details
operation_info = multi_tools.get_operation_info("chart.visualize")
print("Operation info:", operation_info)

# Execute tool operation
result = await multi_tools.execute_tool(
    "chart",
    "visualize",
    file_path="data.csv",
    plot_type="histogram",
    x="age"
)
```

## Task Tool Usage Examples

### Data Processing Pipeline

```python
from aiecs.tools import get_tool

# 1. Data analysis tool
pandas_tool = get_tool("pandas")
df_result = pandas_tool.read_csv(file_path="data.csv")

# 2. Statistical analysis tool
stats_tool = get_tool("stats")
stats_result = stats_tool.descriptive_stats(data=df_result["data"])

# 3. Chart generation tool
chart_tool = get_tool("chart")
chart_result = chart_tool.visualize(
    data=df_result["data"],
    plot_type="histogram",
    x="age"
)

# 4. Report generation tool
report_tool = get_tool("report")
report_result = report_tool.generate_report(
    data=stats_result,
    charts=[chart_result],
    template="statistical_summary"
)
```

### Research and Information Gathering

```python
# Research tool
research_tool = get_tool("research")
research_result = research_tool.search_papers(
    query="machine learning",
    max_results=10
)

# Web scraping tool
scraper_tool = get_tool("scraper")
web_data = scraper_tool.scrape_url(
    url="https://example.com",
    selectors=["h1", "p"]
)

# Search API tool
search_tool = get_tool("search_api")
search_results = search_tool.web_search(
    query="artificial intelligence trends 2024",
    num_results=5
)
```

### Office Document Processing

```python
# Office tool
office_tool = get_tool("office")

# Process Excel file
excel_result = office_tool.read_excel(
    file_path="data.xlsx",
    sheet_name="Sheet1"
)

# Generate Word report
word_result = office_tool.create_word_document(
    content=report_result["content"],
    template="business_report"
)

# Create PowerPoint presentation
ppt_result = office_tool.create_presentation(
    slides_data=chart_result["charts"],
    template="data_analysis"
)
```

## Tool Discovery and Registration

The system automatically discovers and registers all tools:

```python
from aiecs.tools import list_tools, discover_tools

# List all registered tools
all_tools = list_tools()
print("Registered tools:", all_tools)

# Manually trigger tool discovery (usually not needed, system does this automatically)
discover_tools("aiecs.tools")

# View tools by category
task_tools = [tool for tool in all_tools if "task_tools" in str(type(get_tool(tool)))]
print("Task tools:", task_tools)
```

## Best Practices

### 1. Tool Composition
Combine multiple tools to complete complex tasks:

```python
def data_analysis_pipeline(csv_file: str):
    """Complete data analysis pipeline"""

    # Data loading and cleaning
    pandas_tool = get_tool("pandas")
    data = pandas_tool.read_csv(csv_file)
    cleaned_data = pandas_tool.clean_data(data["data"])

    # Statistical analysis
    stats_tool = get_tool("stats")
    statistics = stats_tool.comprehensive_analysis(cleaned_data["data"])

    # Visualization
    chart_tool = get_tool("chart")
    charts = chart_tool.create_dashboard(
        data=cleaned_data["data"],
        chart_types=["histogram", "boxplot", "correlation"]
    )

    # Generate report
    report_tool = get_tool("report")
    final_report = report_tool.generate_comprehensive_report(
        data=statistics,
        visualizations=charts,
        template="data_analysis"
    )

    return final_report
```

### 2. Error Handling
Use appropriate error handling:

```python
from aiecs.tools import get_tool
from aiecs.tools.tool_executor import ToolExecutionError

try:
    tool = get_tool("pandas")
    result = tool.read_csv("nonexistent.csv")
except ToolExecutionError as e:
    print(f"Tool execution error: {e}")
except ValueError as e:
    print(f"Tool does not exist: {e}")
```

### 3. Asynchronous Operations
Use asynchronous execution for time-consuming operations:

```python
import asyncio
from aiecs.services.multi_task.tools import MultiTaskTools

async def async_data_processing():
    multi_tools = MultiTaskTools()

    # Execute multiple operations in parallel
    tasks = [
        multi_tools.execute_tool("scraper", "scrape_url", url="https://site1.com"),
        multi_tools.execute_tool("scraper", "scrape_url", url="https://site2.com"),
        multi_tools.execute_tool("research", "search_papers", query="AI")
    ]

    results = await asyncio.gather(*tasks)
    return results
```

## Extending the Tool System

### Adding New Task Tools

1. Create a new tool file in the `task_tools/` directory
2. Inherit from the `BaseTool` class
3. Register using the `@register_tool` decorator
4. Add import in `task_tools/__init__.py`

```python
# task_tools/my_new_tool.py
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

@register_tool("my_new_tool")
class MyNewTool(BaseTool):
    """New tool description"""

    def my_operation(self, param: str) -> dict:
        """Operation description"""
        return {"result": f"Processing {param}"}
```

### Creating New Tool Categories

1. Create a new directory under `app/tools/`
2. Add an `__init__.py` file
3. Add import in the main `__init__.py`
4. Tools will be automatically discovered and registered


## Special Tool Usage Instructions

### Image Tool

The Image Tool provides comprehensive image processing capabilities, including loading, OCR text recognition, metadata extraction, resizing, and filter application.

#### System Dependency Requirements

**Important**: The Image Tool requires system-level Tesseract OCR engine and Pillow image processing library system dependencies.

#### 1. Tesseract OCR Engine

**Ubuntu/Debian systems**:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS systems**:
```bash
brew install tesseract
```

**Verify installation**:
```bash
tesseract --version
```

#### 2. Pillow Image Processing Library System Dependencies

**Ubuntu/Debian systems**:
```bash
# Basic image processing libraries
sudo apt-get install libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev

# Complete image processing libraries (recommended)
sudo apt-get install libimageio-dev libfreetype6-dev liblcms2-dev libtiff5-dev libjpeg8-dev libopenjp2-7-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1-dev
```

**macOS systems**:
```bash
brew install libjpeg zlib libpng libtiff webp openjpeg freetype lcms2
```

**Verify installation**:
```bash
python -c "from PIL import Image; print('PIL version:', Image.__version__)"
```

#### 3. Multi-language OCR Support

**Install additional language packs**:
```bash
# Ubuntu/Debian systems
sudo apt-get install tesseract-ocr-chi-sim    # Simplified Chinese
sudo apt-get install tesseract-ocr-chi-tra    # Traditional Chinese
sudo apt-get install tesseract-ocr-fra        # French
sudo apt-get install tesseract-ocr-deu        # German
sudo apt-get install tesseract-ocr-jpn        # Japanese
sudo apt-get install tesseract-ocr-kor        # Korean
sudo apt-get install tesseract-ocr-rus        # Russian
sudo apt-get install tesseract-ocr-spa        # Spanish
```

**View installed language packs**:
```bash
tesseract --list-langs
```

**Using multi-language OCR**:
```python
# English OCR
text = tool.ocr("/path/to/image.jpg", lang='eng')

# Chinese OCR
text = tool.ocr("/path/to/image.jpg", lang='chi_sim')

# Japanese OCR
text = tool.ocr("/path/to/image.jpg", lang='jpn')
```

#### Features

1. **Image Loading**: Supports multiple formats (JPG, PNG, BMP, TIFF, GIF)
2. **OCR Text Recognition**: Text extraction based on Tesseract engine
3. **Metadata Extraction**: Get image dimensions, mode, and EXIF information
4. **Image Resizing**: High-quality resizing
5. **Filter Effects**: Blur, sharpen, edge enhancement, and other effects

#### Usage Examples

```python
from aiecs.tools.task_tools.image_tool import ImageTool

# Initialize tool
tool = ImageTool()

# Load image information
result = tool.load("/path/to/image.jpg")
print(f"Size: {result['size']}, Mode: {result['mode']}")

# OCR text recognition
text = tool.ocr("/path/to/image.png", lang='eng')
print(f"Recognized text: {text}")

# Extract metadata
metadata = tool.metadata("/path/to/image.jpg", include_exif=True)
print(f"EXIF info: {metadata.get('exif', {})}")

# Resize image
tool.resize("/path/to/input.jpg", "/path/to/output.jpg", 800, 600)

# Apply filter
tool.filter("/path/to/input.jpg", "/path/to/blurred.jpg", "blur")
```

#### Security Features

- File extension whitelist validation
- File size limits (default 50MB)
- Path normalization and security checks
- Complete error handling and logging

### ClassFire Tool (Text Classification and Keyword Extraction Tool)

The ClassFire Tool provides powerful text classification, keyword extraction, and text summarization capabilities, supporting both English and Chinese text processing.

#### Model Dependency Requirements

**Important**: The ClassFire Tool requires downloading and installing the following models to function properly.

#### 1. spaCy Model Dependencies

**Models Used**:
- **English Model**: `en_core_web_sm` - Used for part-of-speech tagging, named entity recognition, and keyword extraction for English text
- **Chinese Model**: `zh_core_web_sm` - Used for part-of-speech tagging, named entity recognition, and keyword extraction for Chinese text

**Installation Method**:
```bash
# Install using Poetry environment
poetry run python -m spacy download en_core_web_sm
poetry run python -m spacy download zh_core_web_sm

# Or install using pip
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
pip install https://github.com/explosion/spacy-models/releases/download/zh_core_web_sm-3.7.0/zh_core_web_sm-3.7.0-py3-none-any.whl
```

**Usage Reasons**:
- **Part-of-Speech Tagging**: Identifies nouns, verbs, adjectives, etc., for keyword extraction
- **Named Entity Recognition**: Identifies entities like person names, place names, organization names, improving keyword quality
- **Language Detection**: Automatically detects text language and selects appropriate processing strategy
- **Text Preprocessing**: Provides standardized text processing pipeline

#### 2. Transformers Model Dependencies

**Models Used**:
- **English Summarization Model**: `facebook/bart-large-cnn` - Used for English text summarization
- **Multilingual Summarization Model**: `t5-base` - Used for Chinese text summarization

**Model Download**:
```bash
# Models will be automatically downloaded to ~/.cache/huggingface/hub/ on first use
# No manual installation needed, but ensure network connection is available
```

**Installation Verification**:
```python
from transformers import pipeline

# Test English summarization model
summarizer_en = pipeline("summarization", model="facebook/bart-large-cnn")
result = summarizer_en("Your text here...", max_length=100, min_length=30)

# Test multilingual summarization model
summarizer_zh = pipeline("summarization", model="t5-base")
result = summarizer_zh("您的中文文本...", max_new_tokens=50, min_new_tokens=10)
```

**Usage Reasons**:
- **High-Quality Summarization**: BART and T5 are state-of-the-art summarization models
- **Multilingual Support**: T5 supports multiple languages, including Chinese
- **Configurable Length**: Supports custom summary length and minimum length
- **Asynchronous Processing**: Supports asynchronous calls, improving processing efficiency

#### 3. NLTK Data Package Dependencies

**Required Data Packages**:
- `stopwords` - Stopword data for keyword filtering
- `punkt` - Sentence tokenizer for text preprocessing
- `wordnet` - Lexical database for word similarity calculation
- `averaged_perceptron_tagger` - Part-of-speech tagger

**Automatic Download**:
```bash
# Use the provided script to automatically download all NLP data
poetry run python aiecs/scripts/download_nlp_data.py
```

#### Features

1. **Text Classification**: Text classification based on pre-trained models
2. **Keyword Extraction**: Supports RAKE (English) and spaCy (English/Chinese) keyword extraction
3. **Text Summarization**: Supports English and Chinese text summarization
4. **Language Detection**: Automatically detects text language
5. **Asynchronous Processing**: Supports asynchronous calls, improving performance

#### Usage Examples

```python
from aiecs.tools.task_tools.classfire_tool import ClassifierTool

# Initialize tool
tool = ClassifierTool()

# Text classification
result = await tool.classify("This is a positive review about the product.")
print(f"Classification result: {result}")

# Keyword extraction
keywords = await tool.extract_keywords("Natural language processing is important.", top_k=5)
print(f"Keywords: {keywords}")

# Text summarization
summary = await tool.summarize("Your long text here...", max_length=100)
print(f"Summary: {summary}")

# Chinese processing
chinese_keywords = await tool.extract_keywords("自然语言处理是人工智能的重要领域。", top_k=3)
print(f"Chinese keywords: {chinese_keywords}")
```

#### Performance Optimization

- **Model Caching**: Models are cached after first load, improving subsequent call speed
- **Asynchronous Processing**: All main features support asynchronous calls
- **Memory Management**: Supports model unloading and reloading to save memory
- **Error Handling**: Comprehensive error handling and fallback mechanisms

#### Notes

- **First Use**: Models will be automatically downloaded on first use, which may take some time
- **Network Requirements**: Network connection required to download Transformers models
- **Memory Requirements**: Model loading requires certain memory space
- **Language Support**: Currently mainly supports English and Chinese, limited support for other languages

### Office Tool (Office Document Processing Tool)

The Office Tool provides comprehensive office document processing capabilities, supporting reading, writing, and conversion of various document formats, including Word, PowerPoint, Excel, PDF, and image files.

#### System Dependency Requirements

**Important**: The Office Tool requires Java Runtime Environment and Tesseract OCR engine to function properly.

#### 1. Java Runtime Environment (Required)

**Purpose**: Apache Tika document parsing library requires Java Runtime Environment.

**Ubuntu/Debian systems**:
```bash
# Install OpenJDK 11 (recommended)
sudo apt-get update
sudo apt-get install openjdk-11-jdk

# Or install OpenJDK 17
sudo apt-get install openjdk-17-jdk

# Verify installation
java -version
javac -version
```

**macOS systems**:
```bash
# Install using Homebrew
brew install openjdk@11

# Or install OpenJDK 17
brew install openjdk@17
```

**Environment Variable Setup**:
```bash
# Set JAVA_HOME environment variable
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
# Or for OpenJDK 17
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Add to ~/.bashrc or ~/.zshrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
```

#### 2. Tesseract OCR Engine (Required for OCR Functionality)

**Purpose**: Text recognition functionality in image files.

**Ubuntu/Debian systems**:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# Chinese OCR support
sudo apt-get install tesseract-ocr-chi-sim    # Simplified Chinese
sudo apt-get install tesseract-ocr-chi-tra    # Traditional Chinese
```

**macOS systems**:
```bash
brew install tesseract
```

**Verify installation**:
```bash
tesseract --version
tesseract --list-langs
```

#### 3. Python Package Dependencies

**Core Document Processing Libraries**:
- **pandas** (>=2.2.3) - Excel file data processing
- **openpyxl** (>=3.1.5) - Excel file read/write
- **python-docx** (>=1.1.2) - Word document processing
- **python-pptx** (>=1.0.2) - PowerPoint document processing
- **pdfplumber** (>=0.11.7) - PDF text extraction

**Content Parsing Libraries**:
- **tika** (>=3.2.2) - Universal document parsing (requires Java 11+)
- **pytesseract** (>=0.3.13) - OCR text recognition
- **Pillow** (>=11.2.1) - Image processing

#### Features

1. **Document Reading**: Supports DOCX, PPTX, XLSX, PDF formats
2. **Document Writing**: Create and edit Word, PowerPoint, Excel documents
3. **Text Extraction**: Extract text content from various document formats
4. **OCR Functionality**: Recognize text from image files
5. **Multi-format Support**: Process legacy Office documents and other formats

#### Usage Examples

```python
from aiecs.tools.task_tools.office_tool import OfficeTool

# Initialize tool
tool = OfficeTool()

# Read Word document
docx_content = tool.read_docx("/path/to/document.docx")
print(f"Document content: {docx_content['text']}")

# Read Excel file
xlsx_data = tool.read_xlsx("/path/to/spreadsheet.xlsx")
print(f"Spreadsheet data: {xlsx_data}")

# Extract text (supports multiple formats)
text = tool.extract_text("/path/to/document.pdf")
print(f"Extracted text: {text}")

# Create Word document
tool.write_docx("Hello World!", "/path/to/output.docx")

# Create PowerPoint presentation
slides = ["Title Slide", "Content Page 1", "Content Page 2"]
tool.write_pptx(slides, "/path/to/presentation.pptx")
```

#### OCR Functionality

**Supported Image Formats**:
- PNG, JPG, JPEG, TIFF, BMP, GIF

**Language Support**:
- English (eng)
- Simplified Chinese (chi_sim)
- Traditional Chinese (chi_tra)

**Usage Example**:
```python
# Extract text from image
image_text = tool.extract_text("/path/to/image.png")
print(f"Recognized text: {image_text}")
```

#### Performance Optimization

- **Tika Caching**: Tika JAR file will be downloaded and cached on first use
- **Memory Management**: Pay attention to memory usage when processing large files
- **Concurrency Limits**: Recommend limiting the number of documents processed simultaneously
- **Error Handling**: Comprehensive error handling and fallback mechanisms

#### Notes

- **Java Version**: Requires Java 11 or higher (Tika 3.x requirement)
- **Memory Requirements**: Tika requires sufficient memory when processing large files
- **File Size**: Default maximum file size is 100MB
- **Encoding Issues**: Some documents may have encoding issues
- **OCR Accuracy**: Image quality affects OCR recognition accuracy

### Stats Tool (Statistical Analysis Tool)

The Stats Tool provides comprehensive statistical analysis capabilities, supporting various statistical tests, data preprocessing, regression analysis, time series analysis, and other advanced statistical functions.

#### System Dependency Requirements

**Important**: The Stats Tool requires system-level C libraries to support reading special file formats, particularly SAS, SPSS, and Stata files.

#### 1. pyreadstat System Dependencies (Special File Format Support)

**Purpose**: Read and write SAS, SPSS, Stata files (.sav, .sas7bdat, .por formats)

**Ubuntu/Debian systems**:
```bash
# Install libreadstat development library
sudo apt-get update
sudo apt-get install libreadstat-dev

# Install build tools (if not already installed)
sudo apt-get install build-essential python3-dev

# Reinstall pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**macOS systems**:
```bash
# Install using Homebrew
brew install readstat

# Reinstall pyreadstat
pip install --no-cache-dir --force-reinstall pyreadstat
```

**CentOS/RHEL systems**:
```bash
# Install development tools
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# Install readstat library (may need to compile from source)
# Or use conda to install
conda install -c conda-forge readstat
```

**Verify installation**:
```python
import pyreadstat
print("pyreadstat version:", pyreadstat.__version__)

# Test read functionality
try:
    # No actual file needed here, just testing import
    print("pyreadstat installed successfully")
except Exception as e:
    print("pyreadstat installation failed:", e)
```

#### 2. Excel File Support System Dependencies

**Purpose**: Read and write Excel files (.xlsx, .xls formats)

**Ubuntu/Debian systems**:
```bash
# Install system libraries required by openpyxl
sudo apt-get install libxml2-dev libxslt1-dev

# Verify installation
python -c "import openpyxl; print('openpyxl available')"
```

**macOS systems**:
```bash
# Usually no additional installation needed, system already includes required libraries
brew install libxml2 libxslt
```

#### 3. Python Package Dependencies

**Core Statistical Libraries**:
- **pandas** (>=2.2.3) - Data processing and analysis
- **numpy** (>=2.2.6) - Numerical computation
- **scipy** (>=1.15.3) - Scientific computing and statistical functions
- **scikit-learn** (>=1.5.0) - Machine learning library (data preprocessing)
- **statsmodels** (>=0.14.4) - Statistical models and tests

**Special File Format Support**:
- **pyreadstat** (>=1.2.9) - SAS, SPSS, Stata file support
- **openpyxl** (>=3.1.5) - Excel file support

**Configuration Management**:
- **pydantic** (>=2.11.5) - Data validation
- **pydantic-settings** (>=2.9.1) - Settings management

#### Features

1. **Descriptive Statistics**: Basic statistics, skewness, kurtosis, percentiles
2. **Hypothesis Testing**: t-tests, chi-square tests, ANOVA, non-parametric tests
3. **Correlation Analysis**: Pearson, Spearman, Kendall correlation coefficients
4. **Regression Analysis**: OLS, Logit, Probit, Poisson regression
5. **Time Series**: ARIMA, SARIMA models and forecasting
6. **Data Preprocessing**: Standardization, missing value handling, data cleaning
7. **Multi-format Support**: CSV, Excel, JSON, Parquet, Feather, SAS, SPSS, Stata

#### Supported File Formats

| Format | Extension | Dependency Library | System Requirements |
|--------|-----------|-------------------|---------------------|
| **CSV** | `.csv` | pandas | None |
| **Excel** | `.xlsx`, `.xls` | openpyxl | libxml2, libxslt |
| **JSON** | `.json` | pandas | None |
| **Parquet** | `.parquet` | pandas | None |
| **Feather** | `.feather` | pandas | None |
| **SPSS** | `.sav`, `.por` | pyreadstat | libreadstat |
| **SAS** | `.sas7bdat` | pyreadstat | libreadstat |

#### Usage Examples

```python
from aiecs.tools import get_tool

# Get statistics tool
stats_tool = get_tool("stats")

# Read data
data_info = stats_tool.read_data("data.sav")  # SPSS file
print(f"Number of variables: {len(data_info['variables'])}")
print(f"Number of observations: {data_info['observations']}")

# Descriptive statistics
desc_stats = stats_tool.describe(
    file_path="data.sav",
    variables=["age", "income", "education"],
    include_percentiles=True,
    percentiles=[0.1, 0.9]
)

# t-test
ttest_result = stats_tool.ttest(
    file_path="data.sav",
    var1="group1_score",
    var2="group2_score",
    equal_var=True
)

# Correlation analysis
correlation = stats_tool.correlation(
    file_path="data.sav",
    variables=["var1", "var2", "var3"],
    method="pearson"
)

# Regression analysis
regression = stats_tool.regression(
    file_path="data.sav",
    formula="y ~ x1 + x2 + x3",
    regression_type="ols"
)

# Data preprocessing
preprocessed = stats_tool.preprocess(
    file_path="data.sav",
    variables=["var1", "var2"],
    operation="scale",
    scaler_type="standard"
)
```

#### Environment Variable Configuration

Stats Tool can be configured via the following environment variables:

```bash
# Maximum file size limit (MB)
export STATS_TOOL_MAX_FILE_SIZE_MB=200

# Allowed file extensions
export STATS_TOOL_ALLOWED_EXTENSIONS=".sav,.sas7bdat,.por,.csv,.xlsx,.xls,.json,.parquet,.feather"
```

#### Troubleshooting

#### pyreadstat Installation Issues

**Problem**: `ImportError: No module named 'pyreadstat'` or compilation errors

**Solution**:
```bash
# 1. Install system dependencies
sudo apt-get install libreadstat-dev build-essential python3-dev

# 2. Reinstall
pip uninstall pyreadstat
pip install --no-cache-dir pyreadstat

# 3. Verify installation
python -c "import pyreadstat; print('Success')"
```

**Problem**: `OSError: libreadstat.so: cannot open shared object file`

**Solution**:
```bash
# Check library file location
ldconfig -p | grep readstat

# If not found, reinstall system library
sudo apt-get install --reinstall libreadstat0
```

#### Excel File Reading Issues

**Problem**: `ImportError: No module named 'openpyxl'`

**Solution**:
```bash
# Install openpyxl
pip install openpyxl

# Install system dependencies
sudo apt-get install libxml2-dev libxslt1-dev
```

#### Memory Usage Issues

**Problem**: Insufficient memory when processing large files

**Solution**:
```python
# Use nrows parameter to limit number of rows read
data_info = stats_tool.read_data("large_file.csv", nrows=10000)

# Adjust environment variable
export STATS_TOOL_MAX_FILE_SIZE_MB=500
```

#### File Permission Issues

**Problem**: Cannot read file

**Solution**:
```bash
# Check file permissions
ls -la data.sav

# Modify permissions
chmod 644 data.sav

# Check file path
python -c "import os; print(os.path.exists('data.sav'))"
```

### Report Tool (Multi-format Report Generation Tool)

The Report Tool provides comprehensive report generation capabilities, supporting HTML, Excel, PowerPoint, Word, Markdown, image, and PDF format report generation.

#### System Dependency Requirements

**Important**: Some features of the Report Tool require system-level graphics libraries and font libraries.

#### 1. WeasyPrint System Dependencies (Required for PDF Functionality)

**Purpose**: HTML to PDF functionality requires WeasyPrint system-level dependencies.

**Ubuntu/Debian systems**:
```bash
# Install system libraries required by WeasyPrint
sudo apt-get update
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info

# Complete installation (recommended)
sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info libxml2-dev libxslt1-dev
```

**macOS systems**:
```bash
# Install using Homebrew
brew install cairo pango gdk-pixbuf libffi
```

**Verify installation**:
```bash
# Check system libraries
pkg-config --modversion cairo
pkg-config --modversion pango
```

#### 2. Matplotlib System Dependencies (Required for Chart Functionality)

**Purpose**: Chart generation functionality requires font and image processing libraries.

**Ubuntu/Debian systems**:
```bash
# Install system libraries required by Matplotlib
sudo apt-get install libfreetype6-dev libpng-dev libjpeg-dev libtiff-dev libwebp-dev

# Chinese font support
sudo apt-get install fonts-wqy-zenhei fonts-wqy-microhei
```

**macOS systems**:
```bash
# Install using Homebrew
brew install freetype libpng libjpeg libtiff webp
```

**Verify installation**:
```bash
python -c "import matplotlib.pyplot as plt; plt.figure(); print('Matplotlib working')"
```

#### 3. Python Package Dependencies

**Core Report Generation Libraries**:
- **jinja2** (>=3.1.6) - Template engine
- **weasyprint** (>=65.1) - HTML to PDF
- **matplotlib** (>=3.10.3) - Chart generation
- **bleach** (>=6.2.0) - HTML sanitization
- **markdown** (>=3.8) - Markdown processing

**Document Processing Libraries**:
- **pandas** (>=2.2.3) - Data processing
- **openpyxl** (>=3.1.5) - Excel file processing
- **python-docx** (>=1.1.2) - Word document processing
- **python-pptx** (>=1.0.2) - PowerPoint document processing

#### Features

1. **HTML Reports**: Generated using Jinja2 template engine ✅
2. **PDF Reports**: HTML to PDF conversion using WeasyPrint ⚠️ **Temporarily Disabled**
3. **Excel Reports**: Multi-sheet Excel file generation ✅
4. **PowerPoint Reports**: Custom slide presentations ✅
5. **Word Reports**: Styled Word documents ✅
6. **Markdown Reports**: Markdown format reports ✅
7. **Image Reports**: Chart generation using Matplotlib ✅

#### Usage Examples

```python
from aiecs.tools.task_tools.report_tool import ReportTool

# Initialize tool
tool = ReportTool()

# Generate HTML report
html_result = tool.generate_html(
    template_path="report_template.html",
    context={"title": "Monthly Report", "data": data},
    output_path="/path/to/report.html"
)

# Generate PDF report (⚠️ Temporarily disabled - requires system dependencies and code modification)
# pdf_result = tool.generate_pdf(
#     html=html_content,
#     output_path="/path/to/report.pdf",
#     page_size="A4"
# )

# Generate Excel report
excel_result = tool.generate_excel(
    sheets={"Data": df, "Summary": summary_df},
    output_path="/path/to/report.xlsx"
)

# Generate chart
chart_result = tool.generate_image(
    chart_type="bar",
    data=chart_data,
    output_path="/path/to/chart.png",
    title="Sales Data"
)
```

#### PDF Functionality Notes

**⚠️ Important Notice**: HTML to PDF functionality is **temporarily disabled** due to WeasyPrint system dependency issues.

**Current Status**: 
- PDF generation functionality is completely unavailable
- Calling `generate_pdf()` method will throw an error
- Requires manual installation of system dependencies and code modification to enable

**Disable Reason**:
- Missing system-level graphics libraries required by WeasyPrint
- Deployment environment complexity makes dependency installation difficult
- To ensure stability of other features

**Enable Method**:
1. **Install WeasyPrint system dependencies**:
   ```bash
   sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info
   ```
2. **Modify code**:
   - Uncomment `from weasyprint import HTML` import statement
   - Uncomment implementation code in `generate_pdf` method
   - Remove error throwing statements
3. **Verify installation**: Ensure all system libraries are correctly installed

**Supported Features** (after enabling):
- HTML to PDF conversion
- Custom page sizes
- CSS style support
- Template variable substitution

**Alternatives**:
- Use `generate_html()` to generate HTML reports
- Use browser to manually print to PDF
- Use other PDF generation tools

#### Performance Optimization

- **Template Caching**: Jinja2 templates are automatically cached
- **Temporary File Management**: Automatic cleanup of temporary files
- **Batch Generation**: Supports parallel generation of multiple reports
- **Memory Management**: Optimized for large file processing

#### Notes

- **WeasyPrint Dependencies**: PDF functionality requires complete system library support
- **Font Support**: Chart generation requires system font libraries
- **Template Security**: Automatic HTML content sanitization to prevent XSS attacks
- **File Size**: Pay attention to memory usage when processing large files
- **Concurrency Limits**: Recommend limiting the number of reports generated simultaneously

---

## Scraper Tool (Web Scraping Tool)

### Feature Overview

The Scraper Tool is a powerful web scraping tool that supports multiple HTTP clients, JavaScript rendering, HTML parsing, and advanced crawling functionality.

**Main Features**:
- **HTTP Requests**: Supports httpx, urllib, and other clients
- **JavaScript Rendering**: Uses Playwright for dynamic content scraping
- **HTML Parsing**: Uses BeautifulSoup and lxml for content parsing
- **Advanced Crawling**: Integrates Scrapy for complex crawling projects
- **Multi-format Output**: Supports text, JSON, HTML, Markdown, CSV output

### Special Dependency Instructions

#### 1. Playwright Browser Dependencies

**Purpose**: JavaScript rendering functionality (`render()` method)

**Dependency Contents**:
- **Python Package**: `playwright` (already installed)
- **Browser Binaries**: Chromium, Firefox, WebKit
- **System Dependencies**: System libraries required for browser operation

**Installation Steps**:

1. **Download Browsers**:
   ```bash
   cd /home/coder1/python-middleware-dev
   poetry run playwright install
   ```

2. **Install System Dependencies**:
   ```bash
   # Method 1: Use Playwright automatic installation
   poetry run playwright install-deps
   
   # Method 2: Manual installation (Ubuntu/Debian)
   sudo apt-get install libatk1.0-0 \
       libatk-bridge2.0-0 \
       libcups2 \
       libxkbcommon0 \
       libatspi2.0-0 \
       libxcomposite1 \
       libxdamage1 \
       libxfixes3 \
       libxrandr2 \
       libgbm1 \
       libasound2
   ```

   # Method 3: Root account installation (recommended)
    # Temporarily install playwright-python package
    pip install playwright

    # Run playwright command to install system dependencies
    python -m playwright install-deps

    # After dependencies are installed, uninstall temporary playwright-python package to keep root environment clean
    pip uninstall playwright -y

**Browser Storage Location**:
- **Path**: `~/.cache/ms-playwright/`
- **Size**: Approximately 400-500MB (all browsers)
- **Contains**: Chromium, Firefox, WebKit, FFMPEG

**Feature Support**:
- **Page Rendering**: Waits for JavaScript execution to complete
- **Element Waiting**: Waits for specific CSS selectors
- **Page Scrolling**: Scrolls to bottom of page
- **Screenshot Functionality**: Saves page screenshots
- **Multi-browser**: Supports Chromium, Firefox, WebKit

#### 2. Scrapy Advanced Crawling Dependencies

**Purpose**: Advanced crawling functionality (`crawl_scrapy()` method)

**Dependency Contents**:
- **Python Package**: `scrapy` (needs to be installed)
- **Project Structure**: Requires complete Scrapy project

**Installation Steps**:
```bash
cd /home/coder1/python-middleware-dev
poetry add scrapy
```

**Feature Support**:
- **Project-based Crawling**: Supports complete Scrapy project structure
- **Data Pipelines**: Data cleaning, deduplication, storage
- **Middlewares**: Request/response processing
- **Scheduler**: Intelligent request scheduling
- **Monitoring**: Detailed logging and statistics

#### 3. Other Dependencies

**Python Package Dependencies**:
- **httpx**: Asynchronous HTTP client
- **beautifulsoup4**: HTML/XML parsing
- **lxml**: Fast XML and HTML processing

**System Dependencies**:
- **Network Connection**: Download browsers and access target websites
- **Memory**: Browser operation requires sufficient memory
- **Disk Space**: Browser files approximately 500MB

### Usage Examples

#### Basic HTTP Requests (No Browser Required)
```python
from aiecs.tools.task_tools.scraper_tool import ScraperTool

scraper = ScraperTool()

# Use httpx for HTTP requests
result = await scraper.get_httpx("https://example.com")

# Parse HTML content
parsed = scraper.parse_html(html_content, "h1")
```

#### JavaScript Rendering (Requires Playwright)
```python
# Need to install Playwright browsers first
result = await scraper.render(
    url="https://spa-app.com",
    wait_time=5,
    screenshot=True
)
```

#### Advanced Crawling (Requires Scrapy)
```python
# Need to install Scrapy first
result = scraper.crawl_scrapy(
    project_path="/path/to/scrapy/project",
    spider_name="my_spider",
    output_path="output.json"
)
```

### Feature Classification

| Feature Type | Method Name | Requires Browser | Requires Scrapy | Dependencies |
|-------------|-------------|------------------|------------------|--------------|
| **Basic HTTP** | `get_httpx()` | ❌ Not required | ❌ Not required | httpx |
| **Basic HTTP** | `get_urllib()` | ❌ Not required | ❌ Not required | urllib |
| **HTML Parsing** | `parse_html()` | ❌ Not required | ❌ Not required | BeautifulSoup |
| **JavaScript Rendering** | `render()` | ✅ Required | ❌ Not required | Playwright + browsers |
| **Advanced Crawling** | `crawl_scrapy()` | ❌ Not required | ✅ Required | Scrapy |

### Notes

#### Playwright Related
- **Browser Download**: First use requires downloading browsers (approximately 500MB)
- **System Dependencies**: Requires installation of system-level graphics libraries
- **Memory Usage**: Browser operation requires sufficient memory
- **Network Requirements**: Network connection required to download browsers

#### Scrapy Related
- **Project Structure**: Requires complete Scrapy project directory
- **Spider Definition**: Requires pre-defined crawling logic
- **Output Format**: Supports multiple output formats (JSON, CSV, XML)

#### General Notes
- **Network Limits**: Comply with website robots.txt and access frequency limits
- **Legal Compliance**: Ensure scraping behavior complies with relevant laws and regulations
- **Resource Management**: Reasonably control concurrent request numbers
- **Error Handling**: Implement appropriate retry and error handling mechanisms

### Troubleshooting

#### Playwright Issues
```bash
# Check if browsers are installed
poetry run playwright install --list

# Reinstall browsers
poetry run playwright install --force

# Check system dependencies
poetry run playwright install-deps
```

#### Scrapy Issues
```bash
# Check if Scrapy is installed
poetry run scrapy --version

# Create test project
poetry run scrapy startproject test_project
```

#### Network Issues
- **Proxy Settings**: Configure HTTP proxy
- **Timeout Settings**: Adjust request timeout duration
- **Retry Mechanism**: Implement automatic retry logic