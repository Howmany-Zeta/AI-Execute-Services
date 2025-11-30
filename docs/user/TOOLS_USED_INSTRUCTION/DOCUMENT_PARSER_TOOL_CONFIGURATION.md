# Document Parser Tool Configuration Guide

## Overview

The Document Parser Tool provides comprehensive capabilities for parsing various document formats from URLs and files, including PDF, DOCX, XLSX, PPTX, TXT, HTML, RTF, CSV, JSON, XML, Markdown, and images. It supports multiple parsing strategies (text only, structured, full content, metadata only) and output formats (text, JSON, Markdown, HTML). The tool integrates with ScraperTool for URL downloading, OfficeTool for Office document parsing, and ImageTool for image OCR. It also supports cloud storage integration with Google Cloud Storage (GCS). The tool can be configured via environment variables using the `DOC_PARSER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Document Parser Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DOC_PARSER_USER_AGENT=DocumentParser/1.0
DOC_PARSER_MAX_FILE_SIZE=52428800
DOC_PARSER_TEMP_DIR=/path/to/temp
DOC_PARSER_DEFAULT_ENCODING=utf-8
DOC_PARSER_TIMEOUT=30
DOC_PARSER_MAX_PAGES=1000
DOC_PARSER_ENABLE_CLOUD_STORAGE=true
DOC_PARSER_GCS_BUCKET_NAME=aiecs-documents
DOC_PARSER_GCS_PROJECT_ID=your-project-id
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.document_parser_tool import DocumentParserTool

# The tool will automatically use the environment variables
parser_tool = DocumentParserTool()
```

### Multiple Environment Files

You can use different `.env` files for different environments:

```python
import os
from dotenv import load_dotenv

# Load environment-specific configuration
env = os.getenv('APP_ENV', 'development')

if env == 'production':
    load_dotenv('.env.production')
elif env == 'staging':
    load_dotenv('.env.staging')
else:
    load_dotenv('.env.development')

from aiecs.tools.docs.document_parser_tool import DocumentParserTool
parser_tool = DocumentParserTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance and cloud storage
DOC_PARSER_USER_AGENT=DocumentParser/2.0
DOC_PARSER_MAX_FILE_SIZE=104857600
DOC_PARSER_TEMP_DIR=/app/temp/parser
DOC_PARSER_DEFAULT_ENCODING=utf-8
DOC_PARSER_TIMEOUT=60
DOC_PARSER_MAX_PAGES=2000
DOC_PARSER_ENABLE_CLOUD_STORAGE=true
DOC_PARSER_GCS_BUCKET_NAME=prod-aiecs-documents
DOC_PARSER_GCS_PROJECT_ID=production-project-id
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
DOC_PARSER_USER_AGENT=DocumentParser/Dev/1.0
DOC_PARSER_MAX_FILE_SIZE=10485760
DOC_PARSER_TEMP_DIR=./temp/parser
DOC_PARSER_DEFAULT_ENCODING=utf-8
DOC_PARSER_TIMEOUT=15
DOC_PARSER_MAX_PAGES=100
DOC_PARSER_ENABLE_CLOUD_STORAGE=false
DOC_PARSER_GCS_BUCKET_NAME=dev-aiecs-documents
DOC_PARSER_GCS_PROJECT_ID=development-project-id
```

### Best Practices for .env Files

1. **Never commit .env files to version control** - Add `.env` to your `.gitignore`:
   ```gitignore
   # .gitignore
   .env
   .env.local
   .env.*.local
   .env.production
   .env.staging
   ```

2. **Provide a template** - Create `.env.example` with documented dummy values:
   ```bash
   # .env.example
   # Document Parser Tool Configuration
   
   # User agent for HTTP requests
   DOC_PARSER_USER_AGENT=DocumentParser/1.0
   
   # Maximum file size in bytes (50MB)
   DOC_PARSER_MAX_FILE_SIZE=52428800
   
   # Temporary directory for document processing
   DOC_PARSER_TEMP_DIR=/path/to/temp
   
   # Default encoding for text files
   DOC_PARSER_DEFAULT_ENCODING=utf-8
   
   # Timeout for HTTP requests in seconds
   DOC_PARSER_TIMEOUT=30
   
   # Maximum number of pages to process
   DOC_PARSER_MAX_PAGES=1000
   
   # Whether to enable cloud storage integration
   DOC_PARSER_ENABLE_CLOUD_STORAGE=true
   
   # Google Cloud Storage bucket name
   DOC_PARSER_GCS_BUCKET_NAME=aiecs-documents
   
   # Google Cloud Storage project ID (optional)
   DOC_PARSER_GCS_PROJECT_ID=your-project-id
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `utf-8`, `/path/to/dir`
   - Integers: Plain numbers: `52428800`, `30`
   - Booleans: `true` or `false`

## Configuration Options

### 1. User Agent

**Environment Variable:** `DOC_PARSER_USER_AGENT`

**Type:** String

**Default:** `"DocumentParser/1.0"`

**Description:** User agent string used for HTTP requests when downloading documents from URLs. This helps identify the tool to web servers and may be required by some sites.

**Example:**
```bash
export DOC_PARSER_USER_AGENT="DocumentParser/2.0"
```

**Common Values:**
- `DocumentParser/1.0` - Default identifier
- `DocumentParser/2.0` - Updated version
- `CustomParser/1.0` - Custom identifier
- `Mozilla/5.0 (compatible; DocumentParser/1.0)` - Browser-like identifier

### 2. Max File Size

**Environment Variable:** `DOC_PARSER_MAX_FILE_SIZE`

**Type:** Integer

**Default:** `50 * 1024 * 1024` (50MB)

**Description:** Maximum file size in bytes for document processing. Files larger than this will be rejected to prevent memory issues and processing timeouts.

**Common Values:**
- `10 * 1024 * 1024` - 10MB (small files)
- `50 * 1024 * 1024` - 50MB (default)
- `100 * 1024 * 1024` - 100MB (large files)
- `500 * 1024 * 1024` - 500MB (very large files)

**Example:**
```bash
export DOC_PARSER_MAX_FILE_SIZE=104857600
```

**Memory Note:** Larger values allow bigger files but use more memory during processing.

### 3. Temp Directory

**Environment Variable:** `DOC_PARSER_TEMP_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_parser')`

**Description:** Temporary directory used for document processing operations. This directory stores downloaded files, intermediate processing results, and temporary artifacts.

**Example:**
```bash
export DOC_PARSER_TEMP_DIR="/app/temp/parser"
```

**Security Note:** Ensure the directory has appropriate permissions and is not accessible via web servers.

### 4. Default Encoding

**Environment Variable:** `DOC_PARSER_DEFAULT_ENCODING`

**Type:** String

**Default:** `"utf-8"`

**Description:** Default text encoding for processing text files. This encoding is used when the file encoding cannot be automatically detected.

**Supported Encodings:**
- `utf-8` - UTF-8 encoding (default, most common)
- `utf-16` - UTF-16 encoding
- `ascii` - ASCII encoding
- `latin-1` - Latin-1 encoding
- `cp1252` - Windows-1252 encoding
- `iso-8859-1` - ISO-8859-1 encoding

**Example:**
```bash
export DOC_PARSER_DEFAULT_ENCODING=utf-8
```

**Encoding Note:** UTF-8 is recommended for international text support.

### 5. Timeout

**Environment Variable:** `DOC_PARSER_TIMEOUT`

**Type:** Integer

**Default:** `30`

**Description:** Timeout in seconds for HTTP requests when downloading documents from URLs. This prevents hanging requests and improves reliability.

**Common Values:**
- `15` - 15 seconds (fast connections)
- `30` - 30 seconds (default)
- `60` - 60 seconds (slow connections)
- `120` - 120 seconds (very slow connections)

**Example:**
```bash
export DOC_PARSER_TIMEOUT=60
```

**Network Note:** Increase timeout for slower networks or large files.

### 6. Max Pages

**Environment Variable:** `DOC_PARSER_MAX_PAGES`

**Type:** Integer

**Default:** `1000`

**Description:** Maximum number of pages to process for large documents (especially PDFs). This prevents excessive processing time and memory usage.

**Common Values:**
- `100` - 100 pages (small documents)
- `1000` - 1000 pages (default)
- `2000` - 2000 pages (large documents)
- `5000` - 5000 pages (very large documents)

**Example:**
```bash
export DOC_PARSER_MAX_PAGES=2000
```

**Performance Note:** Higher values allow larger documents but increase processing time.

### 7. Enable Cloud Storage

**Environment Variable:** `DOC_PARSER_ENABLE_CLOUD_STORAGE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable cloud storage integration for document retrieval and caching. When enabled, the tool can store and retrieve documents from Google Cloud Storage.

**Values:**
- `true` - Enable cloud storage (default)
- `false` - Disable cloud storage

**Example:**
```bash
export DOC_PARSER_ENABLE_CLOUD_STORAGE=true
```

**Cloud Note:** Requires proper GCS configuration and credentials.

### 8. GCS Bucket Name

**Environment Variable:** `DOC_PARSER_GCS_BUCKET_NAME`

**Type:** String

**Default:** `"aiecs-documents"`

**Description:** Google Cloud Storage bucket name for storing and retrieving documents. This bucket is used for document caching and cloud-based processing.

**Example:**
```bash
export DOC_PARSER_GCS_BUCKET_NAME="my-document-bucket"
```

**Bucket Requirements:**
- Bucket must exist and be accessible
- Proper permissions must be configured
- Bucket name must be globally unique

### 9. GCS Project ID

**Environment Variable:** `DOC_PARSER_GCS_PROJECT_ID`

**Type:** Optional[String]

**Default:** `None`

**Description:** Google Cloud Storage project ID for authentication and billing. This is optional if using default project credentials.

**Example:**
```bash
export DOC_PARSER_GCS_PROJECT_ID="my-gcp-project"
```

**Authentication Note:** Can be omitted if using default project credentials or service account.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic parsing parameters
export DOC_PARSER_USER_AGENT="MyParser/1.0"
export DOC_PARSER_MAX_FILE_SIZE=104857600
export DOC_PARSER_TEMP_DIR="/app/temp/parser"
export DOC_PARSER_TIMEOUT=60

# Run your application
python app.py
```

### Example 2: Cloud Storage Configuration

```bash
# Enable cloud storage with GCS
export DOC_PARSER_ENABLE_CLOUD_STORAGE=true
export DOC_PARSER_GCS_BUCKET_NAME="my-document-bucket"
export DOC_PARSER_GCS_PROJECT_ID="my-gcp-project"
export DOC_PARSER_MAX_FILE_SIZE=209715200
export DOC_PARSER_MAX_PAGES=2000
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DOC_PARSER_USER_AGENT="DevParser/1.0"
export DOC_PARSER_MAX_FILE_SIZE=10485760
export DOC_PARSER_TEMP_DIR="./temp/parser"
export DOC_PARSER_TIMEOUT=15
export DOC_PARSER_MAX_PAGES=100
export DOC_PARSER_ENABLE_CLOUD_STORAGE=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.document_parser_tool import DocumentParserTool

# Initialize with custom configuration
parser_tool = DocumentParserTool(config={
    'user_agent': 'MyParser/2.0',
    'max_file_size': 104857600,
    'temp_dir': '/app/temp/parser',
    'default_encoding': 'utf-8',
    'timeout': 60,
    'max_pages': 2000,
    'enable_cloud_storage': True,
    'gcs_bucket_name': 'my-document-bucket',
    'gcs_project_id': 'my-gcp-project'
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DOC_PARSER_MAX_FILE_SIZE=52428800
export DOC_PARSER_ENABLE_CLOUD_STORAGE=true
```

```python
# Override for specific instance
parser_tool = DocumentParserTool(config={
    'max_file_size': 104857600,  # This overrides the environment variable
    'enable_cloud_storage': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Document Parser Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DOC_PARSER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DOC_PARSER_USER_AGENT=DocumentParser/1.0
export DOC_PARSER_TEMP_DIR=/path/to/temp
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DOC_PARSER_MAX_FILE_SIZE=52428800
export DOC_PARSER_TIMEOUT=30
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DOC_PARSER_ENABLE_CLOUD_STORAGE=true
```

### Optional Values

Optional values can be omitted or set to empty string:

```bash
# Omit optional value
# DOC_PARSER_GCS_PROJECT_ID not set

# Or set to empty string
export DOC_PARSER_GCS_PROJECT_ID=""
```

## Validation

### Automatic Type Validation

Pydantic's BaseSettings automatically validates configuration values:

- `user_agent` must be a non-empty string
- `max_file_size` must be a positive integer
- `temp_dir` must be a non-empty string
- `default_encoding` must be a valid encoding string
- `timeout` must be a positive integer
- `max_pages` must be a positive integer
- `enable_cloud_storage` must be a boolean
- `gcs_bucket_name` must be a non-empty string
- `gcs_project_id` must be a string or None

### Runtime Validation

When processing documents, the tool validates:

1. **Directory accessibility** - Temp directory must be writable
2. **File size limits** - Files must not exceed max_file_size
3. **Network connectivity** - URLs must be accessible within timeout
4. **Cloud storage** - GCS bucket must be accessible if enabled
5. **Document format** - Document type must be supported

## Document Types

The Document Parser Tool supports various document types:

### Office Documents
- **PDF** - Portable Document Format
- **DOCX** - Microsoft Word documents
- **XLSX** - Microsoft Excel spreadsheets
- **PPTX** - Microsoft PowerPoint presentations

### Text Documents
- **TXT** - Plain text files
- **HTML** - HyperText Markup Language
- **RTF** - Rich Text Format
- **Markdown** - Markdown format

### Data Documents
- **CSV** - Comma-Separated Values
- **JSON** - JavaScript Object Notation
- **XML** - Extensible Markup Language

### Media Documents
- **Image** - Various image formats (PNG, JPG, etc.)

### Unknown Documents
- **Unknown** - Unrecognized document types

## Parsing Strategies

### Text Only
- **Purpose** - Extract plain text content only
- **Use Cases** - Text analysis, content indexing
- **Output** - Clean text without formatting

### Structured
- **Purpose** - Extract structured content with metadata
- **Use Cases** - Data extraction, content organization
- **Output** - Structured data with headings, lists, tables

### Full Content
- **Purpose** - Extract all content including formatting
- **Use Cases** - Complete document analysis, content preservation
- **Output** - Rich content with formatting and structure

### Metadata Only
- **Purpose** - Extract document metadata only
- **Use Cases** - Document indexing, cataloging
- **Output** - Document properties and metadata

## Output Formats

### Text
- **Format** - Plain text output
- **Use Cases** - Simple text processing, analysis
- **Features** - Clean, readable text

### JSON
- **Format** - Structured JSON output
- **Use Cases** - API integration, data processing
- **Features** - Structured data with metadata

### Markdown
- **Format** - Markdown formatted output
- **Use Cases** - Documentation, web content
- **Features** - Preserves formatting and structure

### HTML
- **Format** - HTML formatted output
- **Use Cases** - Web display, rich content
- **Features** - Rich formatting and styling

## Cloud Storage

### Google Cloud Storage Integration

The Document Parser Tool supports Google Cloud Storage for:

- **Document Caching** - Store frequently accessed documents
- **Large File Processing** - Process files too large for local storage
- **Distributed Processing** - Share documents across multiple instances
- **Backup and Recovery** - Backup processed documents

### GCS Configuration

**Required Setup:**
1. Create a GCS bucket
2. Configure authentication (service account or default credentials)
3. Set appropriate permissions
4. Configure the tool with bucket name and project ID

**Authentication Methods:**
- Service Account Key
- Default Application Credentials
- Workload Identity
- User Account Credentials

### Cloud Storage Benefits

- **Scalability** - Handle large volumes of documents
- **Reliability** - High availability and durability
- **Performance** - Fast access to cached documents
- **Cost Efficiency** - Pay only for storage used

## Operations Supported

The Document Parser Tool supports comprehensive document parsing operations:

### Document Detection
- `detect_document_type` - Auto-detect document type from URL or file
- `validate_document` - Validate document format and accessibility
- `get_document_info` - Get document metadata and properties

### Document Download
- `download_document` - Download document from URL
- `download_with_retry` - Download with retry logic
- `validate_download` - Validate downloaded document

### Document Parsing
- `parse_document` - Parse document with specified strategy
- `parse_text_only` - Extract text content only
- `parse_structured` - Extract structured content
- `parse_full_content` - Extract all content with formatting
- `parse_metadata_only` - Extract metadata only

### Content Processing
- `extract_text` - Extract plain text from document
- `extract_tables` - Extract table data
- `extract_images` - Extract images and media
- `extract_metadata` - Extract document metadata
- `chunk_content` - Split content into manageable chunks

### Output Generation
- `generate_text_output` - Generate plain text output
- `generate_json_output` - Generate JSON output
- `generate_markdown_output` - Generate Markdown output
- `generate_html_output` - Generate HTML output

### Cloud Storage Operations
- `store_document` - Store document in cloud storage
- `retrieve_document` - Retrieve document from cloud storage
- `cache_document` - Cache document for faster access
- `cleanup_cache` - Clean up cached documents

### Batch Operations
- `batch_parse` - Parse multiple documents
- `batch_download` - Download multiple documents
- `batch_extract` - Extract content from multiple documents
- `batch_convert` - Convert multiple documents to different formats

## Troubleshooting

### Issue: Directory not accessible

**Error:** `PermissionError` when accessing temp directory

**Solutions:**
```bash
# Set accessible directory
export DOC_PARSER_TEMP_DIR="/accessible/temp/path"

# Or create directory with proper permissions
mkdir -p /path/to/directory
chmod 755 /path/to/directory
```

### Issue: File too large

**Error:** `DocumentParserError` for files exceeding size limit

**Solutions:**
```bash
# Increase file size limit
export DOC_PARSER_MAX_FILE_SIZE=104857600

# Or use cloud storage for large files
export DOC_PARSER_ENABLE_CLOUD_STORAGE=true
```

### Issue: Download timeout

**Error:** `DownloadError` for slow downloads

**Solutions:**
```bash
# Increase timeout
export DOC_PARSER_TIMEOUT=60

# Or check network connectivity
ping example.com
```

### Issue: Parsing fails

**Error:** `ParseError` during document parsing

**Solutions:**
1. Check document format support
2. Verify document is not corrupted
3. Try different parsing strategy
4. Check file encoding

### Issue: Cloud storage not working

**Error:** GCS integration fails

**Solutions:**
1. Verify GCS credentials
2. Check bucket permissions
3. Ensure bucket exists
4. Verify project ID

```bash
# Disable cloud storage if not needed
export DOC_PARSER_ENABLE_CLOUD_STORAGE=false
```

### Issue: Encoding errors

**Error:** Text encoding issues

**Solutions:**
```bash
# Set appropriate encoding
export DOC_PARSER_DEFAULT_ENCODING=utf-8

# Or try different encoding
export DOC_PARSER_DEFAULT_ENCODING=latin-1
```

### Issue: Memory errors with large documents

**Error:** `MemoryError` during processing

**Solutions:**
```bash
# Reduce max pages
export DOC_PARSER_MAX_PAGES=500

# Or reduce file size limit
export DOC_PARSER_MAX_FILE_SIZE=26214400
```

## Best Practices

### Performance Optimization

1. **File Size Management** - Set appropriate file size limits
2. **Timeout Configuration** - Configure timeouts based on network speed
3. **Cloud Storage Usage** - Use cloud storage for large files
4. **Caching Strategy** - Implement document caching
5. **Batch Processing** - Use batch operations for multiple documents

### Error Handling

1. **Graceful Degradation** - Handle parsing failures gracefully
2. **Retry Logic** - Implement retry for network operations
3. **Fallback Strategies** - Provide fallback parsing methods
4. **Error Logging** - Log errors for debugging
5. **User Feedback** - Provide clear error messages

### Security

1. **File Validation** - Validate files before processing
2. **Size Limits** - Enforce file size limits
3. **Access Control** - Control access to temp directories
4. **Cloud Security** - Secure cloud storage access
5. **Input Sanitization** - Sanitize user inputs

### Resource Management

1. **Memory Usage** - Monitor memory consumption
2. **Disk Space** - Manage temp directory space
3. **Network Usage** - Optimize network requests
4. **Processing Time** - Set reasonable processing limits
5. **Cleanup** - Regular cleanup of temp files

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance

### Development vs Production

**Development:**
```bash
DOC_PARSER_USER_AGENT=DevParser/1.0
DOC_PARSER_MAX_FILE_SIZE=10485760
DOC_PARSER_TEMP_DIR=./temp/parser
DOC_PARSER_TIMEOUT=15
DOC_PARSER_MAX_PAGES=100
DOC_PARSER_ENABLE_CLOUD_STORAGE=false
```

**Production:**
```bash
DOC_PARSER_USER_AGENT=DocumentParser/2.0
DOC_PARSER_MAX_FILE_SIZE=104857600
DOC_PARSER_TEMP_DIR=/app/temp/parser
DOC_PARSER_TIMEOUT=60
DOC_PARSER_MAX_PAGES=2000
DOC_PARSER_ENABLE_CLOUD_STORAGE=true
DOC_PARSER_GCS_BUCKET_NAME=prod-documents
DOC_PARSER_GCS_PROJECT_ID=production-project
```

### Error Handling

Always wrap document parsing operations in try-except blocks:

```python
from aiecs.tools.docs.document_parser_tool import DocumentParserTool, DocumentParserError, UnsupportedDocumentError, DownloadError, ParseError

parser_tool = DocumentParserTool()

try:
    result = parser_tool.parse_document(
        source="https://example.com/document.pdf",
        strategy="full_content",
        output_format="json"
    )
except UnsupportedDocumentError as e:
    print(f"Unsupported document type: {e}")
except DownloadError as e:
    print(f"Download failed: {e}")
except ParseError as e:
    print(f"Parsing failed: {e}")
except DocumentParserError as e:
    print(f"Document parser error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic pydantic-settings python-dotenv httpx

# Install document processing dependencies
pip install python-docx openpyxl python-pptx

# Install PDF processing dependencies
pip install PyPDF2 pdfplumber

# Install image processing dependencies
pip install pillow pytesseract
```

### Optional Dependencies

```bash
# For cloud storage
pip install google-cloud-storage

# For advanced PDF processing
pip install pdfminer.six

# For HTML processing
pip install beautifulsoup4 lxml

# For Excel processing
pip install xlrd xlsxwriter
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    from pydantic_settings import BaseSettings
    import httpx
    import docx
    import PyPDF2
    import PIL
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test external tool availability
try:
    from aiecs.tools.task_tools.scraper_tool import ScraperTool
    from aiecs.tools.task_tools.office_tool import OfficeTool
    from aiecs.tools.task_tools.image_tool import ImageTool
    print("External tools available")
except ImportError as e:
    print(f"External tool not available: {e}")

# Test cloud storage availability
try:
    from google.cloud import storage
    print("Cloud storage available")
except ImportError:
    print("Cloud storage not available")
```

## Related Documentation

- Tool implementation details in the source code
- ScraperTool documentation for URL downloading
- OfficeTool documentation for Office document parsing
- ImageTool documentation for image OCR
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Document Parser Tool configuration:
- Check the tool source code for implementation details
- Review external tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple documents first to isolate configuration vs. parsing issues
- Monitor directory permissions and disk space
- Verify network connectivity and timeouts
- Check cloud storage configuration and credentials
- Ensure proper file size and page limits
- Validate document format support
