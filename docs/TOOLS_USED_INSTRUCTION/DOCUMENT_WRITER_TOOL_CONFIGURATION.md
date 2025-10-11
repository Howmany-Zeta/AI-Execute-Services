# Document Writer Tool Configuration Guide

## Overview

The Document Writer Tool provides comprehensive capabilities for writing documents in various formats with production-grade features including atomic writes, content validation, security scanning, automatic backup, versioning, and cloud storage integration. It supports multiple document formats (TXT, JSON, CSV, XML, Markdown, HTML, YAML, PDF, DOCX, XLSX, Binary), various write modes (create, overwrite, append, update, backup_write, version_write, insert, replace, delete), and advanced edit operations. The tool integrates with Google Cloud Storage (GCS) for cloud-based document storage and provides enterprise-level security and validation features. The tool can be configured via environment variables using the `DOC_WRITER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Document Writer Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DOC_WRITER_TEMP_DIR=/path/to/temp
DOC_WRITER_BACKUP_DIR=/path/to/backups
DOC_WRITER_OUTPUT_DIR=/path/to/output
DOC_WRITER_MAX_FILE_SIZE=104857600
DOC_WRITER_MAX_BACKUP_VERSIONS=10
DOC_WRITER_DEFAULT_ENCODING=utf-8
DOC_WRITER_ENABLE_BACKUP=true
DOC_WRITER_ENABLE_VERSIONING=true
DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
DOC_WRITER_ENABLE_SECURITY_SCAN=true
DOC_WRITER_ATOMIC_WRITE=true
DOC_WRITER_VALIDATION_LEVEL=basic
DOC_WRITER_TIMEOUT_SECONDS=60
DOC_WRITER_AUTO_BACKUP=true
DOC_WRITER_ATOMIC_WRITES=true
DOC_WRITER_DEFAULT_FORMAT=md
DOC_WRITER_VERSION_CONTROL=true
DOC_WRITER_SECURITY_SCAN=true
DOC_WRITER_ENABLE_CLOUD_STORAGE=true
DOC_WRITER_GCS_BUCKET_NAME=aiecs-documents
DOC_WRITER_GCS_PROJECT_ID=your-project-id
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool

# The tool will automatically use the environment variables
writer_tool = DocumentWriterTool()
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

from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
writer_tool = DocumentWriterTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for security and performance
DOC_WRITER_TEMP_DIR=/app/temp/writer
DOC_WRITER_BACKUP_DIR=/app/backups/documents
DOC_WRITER_OUTPUT_DIR=/app/output/documents
DOC_WRITER_MAX_FILE_SIZE=209715200
DOC_WRITER_MAX_BACKUP_VERSIONS=20
DOC_WRITER_DEFAULT_ENCODING=utf-8
DOC_WRITER_ENABLE_BACKUP=true
DOC_WRITER_ENABLE_VERSIONING=true
DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
DOC_WRITER_ENABLE_SECURITY_SCAN=true
DOC_WRITER_ATOMIC_WRITE=true
DOC_WRITER_VALIDATION_LEVEL=enterprise
DOC_WRITER_TIMEOUT_SECONDS=120
DOC_WRITER_AUTO_BACKUP=true
DOC_WRITER_ATOMIC_WRITES=true
DOC_WRITER_DEFAULT_FORMAT=md
DOC_WRITER_VERSION_CONTROL=true
DOC_WRITER_SECURITY_SCAN=true
DOC_WRITER_ENABLE_CLOUD_STORAGE=true
DOC_WRITER_GCS_BUCKET_NAME=prod-aiecs-documents
DOC_WRITER_GCS_PROJECT_ID=production-project-id
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
DOC_WRITER_TEMP_DIR=./temp/writer
DOC_WRITER_BACKUP_DIR=./backups/documents
DOC_WRITER_OUTPUT_DIR=./output/documents
DOC_WRITER_MAX_FILE_SIZE=52428800
DOC_WRITER_MAX_BACKUP_VERSIONS=5
DOC_WRITER_DEFAULT_ENCODING=utf-8
DOC_WRITER_ENABLE_BACKUP=false
DOC_WRITER_ENABLE_VERSIONING=false
DOC_WRITER_ENABLE_CONTENT_VALIDATION=false
DOC_WRITER_ENABLE_SECURITY_SCAN=false
DOC_WRITER_ATOMIC_WRITE=true
DOC_WRITER_VALIDATION_LEVEL=none
DOC_WRITER_TIMEOUT_SECONDS=30
DOC_WRITER_AUTO_BACKUP=false
DOC_WRITER_ATOMIC_WRITES=true
DOC_WRITER_DEFAULT_FORMAT=md
DOC_WRITER_VERSION_CONTROL=false
DOC_WRITER_SECURITY_SCAN=false
DOC_WRITER_ENABLE_CLOUD_STORAGE=false
DOC_WRITER_GCS_BUCKET_NAME=dev-aiecs-documents
DOC_WRITER_GCS_PROJECT_ID=development-project-id
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
   # Document Writer Tool Configuration
   
   # Temporary directory for document processing
   DOC_WRITER_TEMP_DIR=/path/to/temp
   
   # Directory for document backups
   DOC_WRITER_BACKUP_DIR=/path/to/backups
   
   # Default output directory for documents
   DOC_WRITER_OUTPUT_DIR=/path/to/output
   
   # Maximum file size in bytes (100MB)
   DOC_WRITER_MAX_FILE_SIZE=104857600
   
   # Maximum number of backup versions to keep
   DOC_WRITER_MAX_BACKUP_VERSIONS=10
   
   # Default text encoding for documents
   DOC_WRITER_DEFAULT_ENCODING=utf-8
   
   # Whether to enable automatic backup functionality
   DOC_WRITER_ENABLE_BACKUP=true
   
   # Whether to enable document versioning
   DOC_WRITER_ENABLE_VERSIONING=true
   
   # Whether to enable content validation
   DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
   
   # Whether to enable security scanning
   DOC_WRITER_ENABLE_SECURITY_SCAN=true
   
   # Whether to use atomic write operations
   DOC_WRITER_ATOMIC_WRITE=true
   
   # Content validation level
   DOC_WRITER_VALIDATION_LEVEL=basic
   
   # Operation timeout in seconds
   DOC_WRITER_TIMEOUT_SECONDS=60
   
   # Whether to automatically backup before write operations
   DOC_WRITER_AUTO_BACKUP=true
   
   # Whether to use atomic write operations
   DOC_WRITER_ATOMIC_WRITES=true
   
   # Default document format
   DOC_WRITER_DEFAULT_FORMAT=md
   
   # Whether to enable version control
   DOC_WRITER_VERSION_CONTROL=true
   
   # Whether to enable security scanning
   DOC_WRITER_SECURITY_SCAN=true
   
   # Whether to enable cloud storage integration
   DOC_WRITER_ENABLE_CLOUD_STORAGE=true
   
   # Google Cloud Storage bucket name
   DOC_WRITER_GCS_BUCKET_NAME=aiecs-documents
   
   # Google Cloud Storage project ID (optional)
   DOC_WRITER_GCS_PROJECT_ID=your-project-id
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `utf-8`, `/path/to/dir`
   - Integers: Plain numbers: `104857600`, `60`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Temp Directory

**Environment Variable:** `DOC_WRITER_TEMP_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_writer')`

**Description:** Temporary directory used for document processing operations. This directory stores intermediate files, temporary processing results, and processing artifacts.

**Example:**
```bash
export DOC_WRITER_TEMP_DIR="/app/temp/writer"
```

**Security Note:** Ensure the directory has appropriate permissions and is not accessible via web servers.

### 2. Backup Directory

**Environment Variable:** `DOC_WRITER_BACKUP_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_backups')`

**Description:** Directory where document backups are stored. This directory contains backup copies of documents before modifications.

**Example:**
```bash
export DOC_WRITER_BACKUP_DIR="/app/backups/documents"
```

**Backup Strategy:** Backups are organized by date and document type for easy retrieval.

### 3. Output Directory

**Environment Variable:** `DOC_WRITER_OUTPUT_DIR`

**Type:** Optional[String]

**Default:** `None`

**Description:** Default output directory for created documents. When set, documents are written to this directory unless a specific path is provided.

**Example:**
```bash
export DOC_WRITER_OUTPUT_DIR="/app/output/documents"
```

**Organization:** Consider organizing by project, date, or document type.

### 4. Max File Size

**Environment Variable:** `DOC_WRITER_MAX_FILE_SIZE`

**Type:** Integer

**Default:** `100 * 1024 * 1024` (100MB)

**Description:** Maximum file size in bytes for document writing operations. Files larger than this will be rejected to prevent memory issues.

**Common Values:**
- `50 * 1024 * 1024` - 50MB (small documents)
- `100 * 1024 * 1024` - 100MB (default)
- `200 * 1024 * 1024` - 200MB (large documents)
- `500 * 1024 * 1024` - 500MB (very large documents)

**Example:**
```bash
export DOC_WRITER_MAX_FILE_SIZE=209715200
```

**Memory Note:** Larger values allow bigger files but use more memory during processing.

### 5. Max Backup Versions

**Environment Variable:** `DOC_WRITER_MAX_BACKUP_VERSIONS`

**Type:** Integer

**Default:** `10`

**Description:** Maximum number of backup versions to keep for each document. Older backups are automatically cleaned up.

**Common Values:**
- `5` - 5 versions (minimal storage)
- `10` - 10 versions (default)
- `20` - 20 versions (extensive history)
- `50` - 50 versions (maximum history)

**Example:**
```bash
export DOC_WRITER_MAX_BACKUP_VERSIONS=20
```

**Storage Note:** Higher values provide more history but use more storage space.

### 6. Default Encoding

**Environment Variable:** `DOC_WRITER_DEFAULT_ENCODING`

**Type:** String

**Default:** `"utf-8"`

**Description:** Default text encoding for document writing operations. This encoding is used when no specific encoding is specified.

**Supported Encodings:**
- `utf-8` - UTF-8 encoding (default, most common)
- `utf-16` - UTF-16 encoding
- `ascii` - ASCII encoding
- `gbk` - GBK encoding (Chinese)
- `auto` - Automatic encoding detection

**Example:**
```bash
export DOC_WRITER_DEFAULT_ENCODING=utf-8
```

**Encoding Note:** UTF-8 is recommended for international text support.

### 7. Enable Backup

**Environment Variable:** `DOC_WRITER_ENABLE_BACKUP`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable automatic backup functionality. When enabled, the tool creates backup copies before making modifications.

**Values:**
- `true` - Enable backup functionality (default)
- `false` - Disable backup functionality

**Example:**
```bash
export DOC_WRITER_ENABLE_BACKUP=true
```

**Backup Note:** Essential for data protection and recovery.

### 8. Enable Versioning

**Environment Variable:** `DOC_WRITER_ENABLE_VERSIONING`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable document versioning. When enabled, the tool tracks document versions and maintains version history.

**Values:**
- `true` - Enable versioning (default)
- `false` - Disable versioning

**Example:**
```bash
export DOC_WRITER_ENABLE_VERSIONING=true
```

**Versioning Note:** Provides document history and rollback capabilities.

### 9. Enable Content Validation

**Environment Variable:** `DOC_WRITER_ENABLE_CONTENT_VALIDATION`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable content validation. When enabled, the tool validates document content before writing.

**Values:**
- `true` - Enable content validation (default)
- `false` - Disable content validation

**Example:**
```bash
export DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
```

**Validation Note:** Ensures document integrity and format compliance.

### 10. Enable Security Scan

**Environment Variable:** `DOC_WRITER_ENABLE_SECURITY_SCAN`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable security scanning. When enabled, the tool scans documents for security threats and malicious content.

**Values:**
- `true` - Enable security scanning (default)
- `false` - Disable security scanning

**Example:**
```bash
export DOC_WRITER_ENABLE_SECURITY_SCAN=true
```

**Security Note:** Essential for enterprise environments and compliance.

### 11. Atomic Write

**Environment Variable:** `DOC_WRITER_ATOMIC_WRITE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to use atomic write operations. When enabled, writes are atomic (all-or-nothing) to prevent partial writes.

**Values:**
- `true` - Enable atomic writes (default)
- `false` - Disable atomic writes

**Example:**
```bash
export DOC_WRITER_ATOMIC_WRITE=true
```

**Atomic Note:** Prevents data corruption from interrupted writes.

### 12. Validation Level

**Environment Variable:** `DOC_WRITER_VALIDATION_LEVEL`

**Type:** String

**Default:** `"basic"`

**Description:** Content validation level for document writing operations. Determines the depth and strictness of validation.

**Supported Levels:**
- `none` - No validation
- `basic` - Basic validation (format, size) - default
- `strict` - Strict validation (content, structure)
- `enterprise` - Enterprise validation (security, compliance)

**Example:**
```bash
export DOC_WRITER_VALIDATION_LEVEL=strict
```

**Validation Note:** Higher levels provide more security but may impact performance.

### 13. Timeout Seconds

**Environment Variable:** `DOC_WRITER_TIMEOUT_SECONDS`

**Type:** Integer

**Default:** `60`

**Description:** Operation timeout in seconds for document writing operations. Operations that exceed this timeout will be cancelled.

**Common Values:**
- `30` - 30 seconds (fast operations)
- `60` - 60 seconds (default)
- `120` - 120 seconds (slow operations)
- `300` - 300 seconds (very slow operations)

**Example:**
```bash
export DOC_WRITER_TIMEOUT_SECONDS=120
```

**Timeout Note:** Increase for large files or slow storage systems.

### 14. Auto Backup

**Environment Variable:** `DOC_WRITER_AUTO_BACKUP`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically backup documents before write operations. When enabled, backups are created automatically.

**Values:**
- `true` - Enable auto backup (default)
- `false` - Disable auto backup

**Example:**
```bash
export DOC_WRITER_AUTO_BACKUP=true
```

**Auto Backup Note:** Provides automatic data protection.

### 15. Atomic Writes

**Environment Variable:** `DOC_WRITER_ATOMIC_WRITES`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to use atomic write operations. This is a duplicate of `atomic_write` for compatibility.

**Values:**
- `true` - Enable atomic writes (default)
- `false` - Disable atomic writes

**Example:**
```bash
export DOC_WRITER_ATOMIC_WRITES=true
```

### 16. Default Format

**Environment Variable:** `DOC_WRITER_DEFAULT_FORMAT`

**Type:** String

**Default:** `"md"`

**Description:** Default document format for writing operations. This format is used when no specific format is specified.

**Supported Formats:**
- `txt` - Plain text format
- `json` - JSON format
- `csv` - CSV format
- `xml` - XML format
- `md` - Markdown format (default)
- `html` - HTML format
- `yaml` - YAML format
- `pdf` - PDF format
- `docx` - Microsoft Word format
- `xlsx` - Microsoft Excel format
- `binary` - Binary format

**Example:**
```bash
export DOC_WRITER_DEFAULT_FORMAT=html
```

**Format Note:** Choose based on your primary use case.

### 17. Version Control

**Environment Variable:** `DOC_WRITER_VERSION_CONTROL`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable version control. This is a duplicate of `enable_versioning` for compatibility.

**Values:**
- `true` - Enable version control (default)
- `false` - Disable version control

**Example:**
```bash
export DOC_WRITER_VERSION_CONTROL=true
```

### 18. Security Scan

**Environment Variable:** `DOC_WRITER_SECURITY_SCAN`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable security scanning. This is a duplicate of `enable_security_scan` for compatibility.

**Values:**
- `true` - Enable security scanning (default)
- `false` - Disable security scanning

**Example:**
```bash
export DOC_WRITER_SECURITY_SCAN=true
```

### 19. Enable Cloud Storage

**Environment Variable:** `DOC_WRITER_ENABLE_CLOUD_STORAGE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable cloud storage integration. When enabled, the tool can store documents in Google Cloud Storage.

**Values:**
- `true` - Enable cloud storage (default)
- `false` - Disable cloud storage

**Example:**
```bash
export DOC_WRITER_ENABLE_CLOUD_STORAGE=true
```

**Cloud Note:** Requires proper GCS configuration and credentials.

### 20. GCS Bucket Name

**Environment Variable:** `DOC_WRITER_GCS_BUCKET_NAME`

**Type:** String

**Default:** `"aiecs-documents"`

**Description:** Google Cloud Storage bucket name for storing documents. This bucket is used for cloud-based document storage.

**Example:**
```bash
export DOC_WRITER_GCS_BUCKET_NAME="my-document-bucket"
```

**Bucket Requirements:**
- Bucket must exist and be accessible
- Proper permissions must be configured
- Bucket name must be globally unique

### 21. GCS Project ID

**Environment Variable:** `DOC_WRITER_GCS_PROJECT_ID`

**Type:** Optional[String]

**Default:** `None`

**Description:** Google Cloud Storage project ID for authentication and billing. This is optional if using default project credentials.

**Example:**
```bash
export DOC_WRITER_GCS_PROJECT_ID="my-gcp-project"
```

**Authentication Note:** Can be omitted if using default project credentials or service account.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic writing parameters
export DOC_WRITER_TEMP_DIR="/app/temp/writer"
export DOC_WRITER_BACKUP_DIR="/app/backups/documents"
export DOC_WRITER_MAX_FILE_SIZE=104857600
export DOC_WRITER_DEFAULT_ENCODING=utf-8
export DOC_WRITER_ATOMIC_WRITE=true

# Run your application
python app.py
```

### Example 2: Enterprise Configuration

```bash
# Optimized for enterprise use
export DOC_WRITER_ENABLE_BACKUP=true
export DOC_WRITER_ENABLE_VERSIONING=true
export DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
export DOC_WRITER_ENABLE_SECURITY_SCAN=true
export DOC_WRITER_VALIDATION_LEVEL=enterprise
export DOC_WRITER_MAX_BACKUP_VERSIONS=20
export DOC_WRITER_ENABLE_CLOUD_STORAGE=true
export DOC_WRITER_GCS_BUCKET_NAME="enterprise-documents"
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DOC_WRITER_TEMP_DIR="./temp/writer"
export DOC_WRITER_BACKUP_DIR="./backups/documents"
export DOC_WRITER_MAX_FILE_SIZE=52428800
export DOC_WRITER_ENABLE_BACKUP=false
export DOC_WRITER_ENABLE_VERSIONING=false
export DOC_WRITER_ENABLE_CONTENT_VALIDATION=false
export DOC_WRITER_ENABLE_SECURITY_SCAN=false
export DOC_WRITER_VALIDATION_LEVEL=none
export DOC_WRITER_ENABLE_CLOUD_STORAGE=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool

# Initialize with custom configuration
writer_tool = DocumentWriterTool(config={
    'temp_dir': '/app/temp/writer',
    'backup_dir': '/app/backups/documents',
    'output_dir': '/app/output/documents',
    'max_file_size': 104857600,
    'max_backup_versions': 10,
    'default_encoding': 'utf-8',
    'enable_backup': True,
    'enable_versioning': True,
    'enable_content_validation': True,
    'enable_security_scan': True,
    'atomic_write': True,
    'validation_level': 'basic',
    'timeout_seconds': 60,
    'auto_backup': True,
    'atomic_writes': True,
    'default_format': 'md',
    'version_control': True,
    'security_scan': True,
    'enable_cloud_storage': True,
    'gcs_bucket_name': 'my-document-bucket',
    'gcs_project_id': 'my-gcp-project'
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DOC_WRITER_MAX_FILE_SIZE=104857600
export DOC_WRITER_ENABLE_BACKUP=true
```

```python
# Override for specific instance
writer_tool = DocumentWriterTool(config={
    'max_file_size': 209715200,  # This overrides the environment variable
    'enable_backup': False       # This overrides the environment variable
})
```

## Configuration Priority

When the Document Writer Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DOC_WRITER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DOC_WRITER_DEFAULT_ENCODING=utf-8
export DOC_WRITER_TEMP_DIR=/path/to/temp
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DOC_WRITER_MAX_FILE_SIZE=104857600
export DOC_WRITER_TIMEOUT_SECONDS=60
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DOC_WRITER_ENABLE_BACKUP=true
export DOC_WRITER_ATOMIC_WRITE=false
```

### Optional Values

Optional values can be omitted or set to empty string:

```bash
# Omit optional value
# DOC_WRITER_OUTPUT_DIR not set
# DOC_WRITER_GCS_PROJECT_ID not set

# Or set to empty string
export DOC_WRITER_OUTPUT_DIR=""
export DOC_WRITER_GCS_PROJECT_ID=""
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `temp_dir` must be a non-empty string
- `backup_dir` must be a non-empty string
- `output_dir` must be a string or None
- `max_file_size` must be a positive integer
- `max_backup_versions` must be a positive integer
- `default_encoding` must be a valid encoding string
- All boolean fields must be boolean values
- `validation_level` must be a valid validation level
- `timeout_seconds` must be a positive integer
- `default_format` must be a valid format string
- `gcs_bucket_name` must be a non-empty string
- `gcs_project_id` must be a string or None

### Runtime Validation

When writing documents, the tool validates:

1. **Directory accessibility** - Temp, backup, and output directories must be accessible
2. **File size limits** - Documents must not exceed max_file_size
3. **Cloud storage** - GCS bucket must be accessible if enabled
4. **Content validation** - Document content must pass validation if enabled
5. **Security scanning** - Documents must pass security scan if enabled

## Document Formats

The Document Writer Tool supports various document formats:

### Text Formats
- **TXT** - Plain text format
- **JSON** - JavaScript Object Notation
- **CSV** - Comma-Separated Values
- **XML** - Extensible Markup Language
- **Markdown** - Markdown format
- **HTML** - HyperText Markup Language
- **YAML** - YAML Ain't Markup Language

### Document Formats
- **PDF** - Portable Document Format
- **DOCX** - Microsoft Word format
- **XLSX** - Microsoft Excel format

### Binary Formats
- **Binary** - Raw binary data

## Write Modes

### Basic Modes
- **Create** - Create new file, fail if exists
- **Overwrite** - Overwrite existing file
- **Append** - Append to existing file
- **Update** - Update existing file (smart merge)

### Advanced Modes
- **Backup Write** - Backup before writing
- **Version Write** - Versioned writing
- **Insert** - Insert at specified position
- **Replace** - Replace specified content
- **Delete** - Delete specified content

## Edit Operations

### Text Formatting
- **Bold** - Bold text formatting
- **Italic** - Italic text formatting
- **Underline** - Underline text formatting
- **Strikethrough** - Strikethrough text formatting
- **Highlight** - Highlight text formatting

### Text Operations
- **Insert Text** - Insert text at position
- **Delete Text** - Delete specified text
- **Replace Text** - Replace specified text
- **Copy Text** - Copy text to clipboard
- **Cut Text** - Cut text to clipboard
- **Paste Text** - Paste text from clipboard

### Advanced Operations
- **Find Replace** - Find and replace text
- **Insert Line** - Insert new line
- **Delete Line** - Delete specified line
- **Move Line** - Move line to new position

## Encoding Types

### Standard Encodings
- **UTF-8** - UTF-8 encoding (default, most common)
- **UTF-16** - UTF-16 encoding
- **ASCII** - ASCII encoding
- **GBK** - GBK encoding (Chinese)

### Special Encodings
- **Auto** - Automatic encoding detection

## Validation Levels

### Validation Types
- **None** - No validation
- **Basic** - Basic validation (format, size)
- **Strict** - Strict validation (content, structure)
- **Enterprise** - Enterprise validation (security, compliance)

## Cloud Storage

### Google Cloud Storage Integration

The Document Writer Tool supports Google Cloud Storage for:

- **Document Storage** - Store documents in cloud storage
- **Backup Storage** - Store backups in cloud storage
- **Version Storage** - Store document versions in cloud storage
- **Distributed Access** - Access documents from multiple locations

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
- **Performance** - Fast access to stored documents
- **Cost Efficiency** - Pay only for storage used

## Operations Supported

The Document Writer Tool supports comprehensive document writing operations:

### Basic Writing
- `write_document` - Write document to file
- `write_text` - Write text content
- `write_json` - Write JSON content
- `write_csv` - Write CSV content
- `write_xml` - Write XML content
- `write_markdown` - Write Markdown content
- `write_html` - Write HTML content
- `write_yaml` - Write YAML content

### Advanced Writing
- `write_with_backup` - Write with automatic backup
- `write_with_versioning` - Write with version control
- `write_atomic` - Atomic write operation
- `write_secure` - Write with security validation
- `write_cloud` - Write to cloud storage

### Document Operations
- `create_document` - Create new document
- `update_document` - Update existing document
- `append_document` - Append to document
- `overwrite_document` - Overwrite document
- `delete_document` - Delete document

### Edit Operations
- `edit_text` - Edit text content
- `format_text` - Format text (bold, italic, etc.)
- `find_replace` - Find and replace text
- `insert_content` - Insert content at position
- `delete_content` - Delete specified content

### Backup and Versioning
- `create_backup` - Create document backup
- `restore_backup` - Restore from backup
- `list_backups` - List available backups
- `create_version` - Create document version
- `list_versions` - List document versions
- `restore_version` - Restore document version

### Validation and Security
- `validate_content` - Validate document content
- `scan_security` - Scan for security threats
- `check_permissions` - Check write permissions
- `validate_format` - Validate document format

### Cloud Operations
- `upload_to_cloud` - Upload document to cloud
- `download_from_cloud` - Download document from cloud
- `sync_with_cloud` - Sync with cloud storage
- `list_cloud_documents` - List cloud documents

### Batch Operations
- `batch_write` - Write multiple documents
- `batch_backup` - Backup multiple documents
- `batch_validate` - Validate multiple documents
- `batch_upload` - Upload multiple documents

## Troubleshooting

### Issue: Directory not accessible

**Error:** `PermissionError` when accessing directories

**Solutions:**
```bash
# Set accessible directories
export DOC_WRITER_TEMP_DIR="/accessible/temp/path"
export DOC_WRITER_BACKUP_DIR="/accessible/backup/path"
export DOC_WRITER_OUTPUT_DIR="/accessible/output/path"

# Or create directories with proper permissions
mkdir -p /path/to/directories
chmod 755 /path/to/directories
```

### Issue: File too large

**Error:** `WriteError` for files exceeding size limit

**Solutions:**
```bash
# Increase file size limit
export DOC_WRITER_MAX_FILE_SIZE=209715200

# Or use cloud storage for large files
export DOC_WRITER_ENABLE_CLOUD_STORAGE=true
```

### Issue: Backup creation fails

**Error:** `StorageError` during backup operations

**Solutions:**
1. Check backup directory permissions
2. Ensure sufficient disk space
3. Verify backup directory path
4. Check backup version limits

### Issue: Validation fails

**Error:** `ValidationError` during content validation

**Solutions:**
```bash
# Disable validation for testing
export DOC_WRITER_ENABLE_CONTENT_VALIDATION=false
export DOC_WRITER_VALIDATION_LEVEL=none

# Or use less strict validation
export DOC_WRITER_VALIDATION_LEVEL=basic
```

### Issue: Security scan fails

**Error:** `SecurityError` during security scanning

**Solutions:**
```bash
# Disable security scanning for testing
export DOC_WRITER_ENABLE_SECURITY_SCAN=false
export DOC_WRITER_SECURITY_SCAN=false

# Or check security scan configuration
```

### Issue: Cloud storage not working

**Error:** GCS integration fails

**Solutions:**
1. Verify GCS credentials
2. Check bucket permissions
3. Ensure bucket exists
4. Verify project ID

```bash
# Disable cloud storage if not needed
export DOC_WRITER_ENABLE_CLOUD_STORAGE=false
```

### Issue: Atomic write fails

**Error:** `WriteError` during atomic operations

**Solutions:**
```bash
# Disable atomic writes for testing
export DOC_WRITER_ATOMIC_WRITE=false
export DOC_WRITER_ATOMIC_WRITES=false

# Or check file system support for atomic operations
```

### Issue: Timeout errors

**Error:** Operations timeout

**Solutions:**
```bash
# Increase timeout
export DOC_WRITER_TIMEOUT_SECONDS=120

# Or optimize file size and operations
export DOC_WRITER_MAX_FILE_SIZE=52428800
```

## Best Practices

### Performance Optimization

1. **File Size Management** - Set appropriate file size limits
2. **Timeout Configuration** - Configure timeouts based on operations
3. **Cloud Storage Usage** - Use cloud storage for large files
4. **Backup Strategy** - Implement efficient backup strategies
5. **Batch Operations** - Use batch operations for multiple documents

### Data Protection

1. **Backup Strategy** - Enable automatic backups
2. **Version Control** - Use versioning for important documents
3. **Atomic Operations** - Use atomic writes for data integrity
4. **Validation** - Enable content validation
5. **Security Scanning** - Enable security scanning

### Error Handling

1. **Graceful Degradation** - Handle write failures gracefully
2. **Retry Logic** - Implement retry for transient failures
3. **Fallback Strategies** - Provide fallback write methods
4. **Error Logging** - Log errors for debugging
5. **User Feedback** - Provide clear error messages

### Security

1. **Content Validation** - Validate all document content
2. **Security Scanning** - Scan for security threats
3. **Access Control** - Control access to directories
4. **Cloud Security** - Secure cloud storage access
5. **Input Sanitization** - Sanitize all inputs

### Resource Management

1. **Memory Usage** - Monitor memory consumption
2. **Disk Space** - Manage temp and backup directories
3. **Network Usage** - Optimize cloud operations
4. **Processing Time** - Set reasonable timeouts
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
DOC_WRITER_TEMP_DIR=./temp/writer
DOC_WRITER_BACKUP_DIR=./backups/documents
DOC_WRITER_OUTPUT_DIR=./output/documents
DOC_WRITER_MAX_FILE_SIZE=52428800
DOC_WRITER_MAX_BACKUP_VERSIONS=5
DOC_WRITER_ENABLE_BACKUP=false
DOC_WRITER_ENABLE_VERSIONING=false
DOC_WRITER_ENABLE_CONTENT_VALIDATION=false
DOC_WRITER_ENABLE_SECURITY_SCAN=false
DOC_WRITER_VALIDATION_LEVEL=none
DOC_WRITER_TIMEOUT_SECONDS=30
DOC_WRITER_ENABLE_CLOUD_STORAGE=false
```

**Production:**
```bash
DOC_WRITER_TEMP_DIR=/app/temp/writer
DOC_WRITER_BACKUP_DIR=/app/backups/documents
DOC_WRITER_OUTPUT_DIR=/app/output/documents
DOC_WRITER_MAX_FILE_SIZE=209715200
DOC_WRITER_MAX_BACKUP_VERSIONS=20
DOC_WRITER_ENABLE_BACKUP=true
DOC_WRITER_ENABLE_VERSIONING=true
DOC_WRITER_ENABLE_CONTENT_VALIDATION=true
DOC_WRITER_ENABLE_SECURITY_SCAN=true
DOC_WRITER_VALIDATION_LEVEL=enterprise
DOC_WRITER_TIMEOUT_SECONDS=120
DOC_WRITER_ENABLE_CLOUD_STORAGE=true
DOC_WRITER_GCS_BUCKET_NAME=prod-documents
DOC_WRITER_GCS_PROJECT_ID=production-project
```

### Error Handling

Always wrap document writing operations in try-except blocks:

```python
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool, DocumentWriterError, WriteError, ValidationError, SecurityError, WritePermissionError, ContentValidationError, StorageError

writer_tool = DocumentWriterTool()

try:
    result = writer_tool.write_document(
        content="Hello, World!",
        file_path="document.txt",
        format="txt",
        mode="create"
    )
except WriteError as e:
    print(f"Write operation failed: {e}")
except ValidationError as e:
    print(f"Validation failed: {e}")
except SecurityError as e:
    print(f"Security scan failed: {e}")
except WritePermissionError as e:
    print(f"Write permission denied: {e}")
except ContentValidationError as e:
    print(f"Content validation failed: {e}")
except StorageError as e:
    print(f"Storage operation failed: {e}")
except DocumentWriterError as e:
    print(f"Document writer error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install document processing dependencies
pip install python-docx openpyxl python-pptx

# Install PDF processing dependencies
pip install reportlab

# Install cloud storage dependencies
pip install google-cloud-storage
```

### Optional Dependencies

```bash
# For advanced document processing
pip install PyPDF2 pdfplumber

# For image processing
pip install pillow

# For advanced validation
pip install jsonschema

# For security scanning
pip install python-magic
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import docx
    import openpyxl
    import reportlab
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test cloud storage availability
try:
    from google.cloud import storage
    print("Cloud storage available")
except ImportError:
    print("Cloud storage not available")

# Test document processing availability
try:
    import docx
    import openpyxl
    import reportlab
    print("Document processing available")
except ImportError as e:
    print(f"Document processing not available: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- DocumentCreatorTool documentation for document creation
- DocumentLayoutTool documentation for layout management
- ContentInsertionTool documentation for complex content
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Document Writer Tool configuration:
- Check the tool source code for implementation details
- Review external tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple documents first to isolate configuration vs. writing issues
- Monitor directory permissions and disk space
- Verify cloud storage configuration and credentials
- Ensure proper file size and timeout limits
- Check validation and security scan settings
- Validate document format support
