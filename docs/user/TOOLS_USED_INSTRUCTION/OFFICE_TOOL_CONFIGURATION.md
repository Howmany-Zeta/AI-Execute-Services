# Office Tool Configuration Guide

## Overview

The Office Tool provides comprehensive document processing capabilities for Microsoft Office formats (DOCX, PPTX, XLSX) and PDF files. It supports reading, writing, and text extraction from various document formats. It can be configured via environment variables using the `OFFICE_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Office Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
OFFICE_TOOL_MAX_FILE_SIZE_MB=100
OFFICE_TOOL_DEFAULT_FONT=Arial
OFFICE_TOOL_DEFAULT_FONT_SIZE=12
OFFICE_TOOL_ALLOWED_EXTENSIONS=[".docx",".pptx",".xlsx",".pdf",".png",".jpg",".jpeg",".tiff",".bmp",".gif"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.office_tool import OfficeTool

# The tool will automatically use the environment variables
office_tool = OfficeTool()
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

from aiecs.tools.task_tools.office_tool import OfficeTool
office_tool = OfficeTool()
```

**Example `.env.production`:**
```bash
# Production settings - strict limits for security
OFFICE_TOOL_MAX_FILE_SIZE_MB=50
OFFICE_TOOL_DEFAULT_FONT=Arial
OFFICE_TOOL_DEFAULT_FONT_SIZE=11
OFFICE_TOOL_ALLOWED_EXTENSIONS=[".docx",".pptx",".xlsx",".pdf"]
```

**Example `.env.development`:**
```bash
# Development settings - relaxed limits for testing
OFFICE_TOOL_MAX_FILE_SIZE_MB=200
OFFICE_TOOL_DEFAULT_FONT=Calibri
OFFICE_TOOL_DEFAULT_FONT_SIZE=12
OFFICE_TOOL_ALLOWED_EXTENSIONS=[".docx",".pptx",".xlsx",".pdf",".png",".jpg",".jpeg",".tiff",".bmp",".gif"]
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
   # Office Tool Configuration
   
   # Maximum file size in megabytes
   OFFICE_TOOL_MAX_FILE_SIZE_MB=100
   
   # Default font for documents
   OFFICE_TOOL_DEFAULT_FONT=Arial
   
   # Default font size in points
   OFFICE_TOOL_DEFAULT_FONT_SIZE=12
   
   # Allowed document file extensions (JSON array)
   OFFICE_TOOL_ALLOWED_EXTENSIONS=[".docx",".pptx",".xlsx",".pdf",".png",".jpg",".jpeg",".tiff",".bmp",".gif"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Integers: Plain numbers: `100`, `12`
   - Strings: Plain text: `Arial`, `Calibri`
   - Lists: Use JSON array format with double quotes: `[".docx",".pdf"]`

## Configuration Options

### 1. Max File Size (MB)

**Environment Variable:** `OFFICE_TOOL_MAX_FILE_SIZE_MB`

**Type:** Integer

**Default:** `100`

**Description:** Maximum allowed file size in megabytes. Files larger than this limit will be rejected during validation for security and performance reasons.

**Common Values:**
- `10` - Conservative limit for public APIs
- `50` - Moderate limit for web applications
- `100` - Default (balanced)
- `200` - Generous limit for internal tools
- `500` - Large files for enterprise applications

**Example:**
```bash
export OFFICE_TOOL_MAX_FILE_SIZE_MB=50
```

**Security Note:** Keep this value as low as practical for your use case to prevent memory exhaustion and DoS attacks.

### 2. Default Font

**Environment Variable:** `OFFICE_TOOL_DEFAULT_FONT`

**Type:** String

**Default:** `"Arial"`

**Description:** Default font to use when creating DOCX documents. This font will be applied to the Normal style of generated documents.

**Common Fonts:**
- `Arial` - Default, widely available
- `Calibri` - Modern Microsoft default
- `Times New Roman` - Traditional serif font
- `Verdana` - Web-friendly sans-serif
- `Helvetica` - Classic sans-serif

**Example:**
```bash
export OFFICE_TOOL_DEFAULT_FONT=Calibri
```

**Note:** Ensure the specified font is installed on the system where documents will be opened, otherwise a fallback font will be used.

### 3. Default Font Size

**Environment Variable:** `OFFICE_TOOL_DEFAULT_FONT_SIZE`

**Type:** Integer

**Default:** `12`

**Description:** Default font size in points to use when creating DOCX documents. This size will be applied to the Normal style of generated documents.

**Common Sizes:**
- `10` - Small, compact text
- `11` - Common for business documents
- `12` - Default, standard size
- `14` - Large, easy to read
- `16` - Headings or emphasis

**Example:**
```bash
export OFFICE_TOOL_DEFAULT_FONT_SIZE=11
```

### 4. Allowed Extensions

**Environment Variable:** `OFFICE_TOOL_ALLOWED_EXTENSIONS`

**Type:** List[str]

**Default:** `['.docx', '.pptx', '.xlsx', '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']`

**Description:** List of allowed file extensions for document processing. This is a critical security feature that prevents processing of unauthorized or potentially malicious file types.

**Format:** JSON array string with double quotes

**Supported Formats:**
- `.docx` - Microsoft Word documents
- `.pptx` - Microsoft PowerPoint presentations
- `.xlsx` - Microsoft Excel spreadsheets
- `.pdf` - PDF documents
- `.png`, `.jpg`, `.jpeg` - Image formats (for OCR)
- `.tiff`, `.bmp`, `.gif` - Additional image formats

**Example:**
```bash
# Strict - Only Office formats
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx"]'

# Moderate - Office and PDF
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf"]'

# Lenient - All supported formats
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf",".png",".jpg",".jpeg",".tiff",".bmp",".gif"]'
```

**Security Note:** Only allow extensions that your application actually needs to process. Images should only be included if OCR functionality is required.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom limits and fonts
export OFFICE_TOOL_MAX_FILE_SIZE_MB=50
export OFFICE_TOOL_DEFAULT_FONT=Calibri
export OFFICE_TOOL_DEFAULT_FONT_SIZE=11
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf"]'

# Run your application
python app.py
```

### Example 2: Security-Focused Configuration

```bash
# Strict limits for public-facing applications
export OFFICE_TOOL_MAX_FILE_SIZE_MB=20
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pdf"]'
export OFFICE_TOOL_DEFAULT_FONT=Arial
export OFFICE_TOOL_DEFAULT_FONT_SIZE=12
```

### Example 3: High-Capacity Configuration

```bash
# Optimized for internal high-volume processing
export OFFICE_TOOL_MAX_FILE_SIZE_MB=500
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf",".png",".jpg"]'
export OFFICE_TOOL_DEFAULT_FONT=Calibri
export OFFICE_TOOL_DEFAULT_FONT_SIZE=11
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.office_tool import OfficeTool

# Initialize with custom configuration
office_tool = OfficeTool(config={
    'max_file_size_mb': 75,
    'default_font': 'Calibri',
    'default_font_size': 11,
    'allowed_extensions': ['.docx', '.pptx', '.xlsx', '.pdf']
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export OFFICE_TOOL_MAX_FILE_SIZE_MB=100
export OFFICE_TOOL_DEFAULT_FONT=Arial
```

```python
# Override for specific instance
office_tool = OfficeTool(config={
    'max_file_size_mb': 50,  # Override
    'default_font': 'Calibri'  # Override
})
```

## Configuration Priority

When the Office Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `OFFICE_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Integer Values

Integers should be provided as numeric strings:

```bash
export OFFICE_TOOL_MAX_FILE_SIZE_MB=100
export OFFICE_TOOL_DEFAULT_FONT_SIZE=12
```

### String Values

Strings should be provided as plain text without quotes:

```bash
export OFFICE_TOOL_DEFAULT_FONT=Arial
```

### List Values

Lists must be provided as JSON array strings with double quotes:

```bash
# Correct
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pdf"]'

# Incorrect (will not parse)
export OFFICE_TOOL_ALLOWED_EXTENSIONS=".docx,.pdf"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx"]'
#                                      ^                          ^
#                                      Single quotes for shell
#                                         ^      ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `max_file_size_mb` must be a positive integer
- `default_font` must be a non-empty string
- `default_font_size` must be a positive integer
- `allowed_extensions` must be a list of strings

### File Validation

When processing documents, the tool validates:

1. **File existence** - File must exist at the specified path
2. **File extension** - Must be in `allowed_extensions` list
3. **File size** - Must not exceed `max_file_size_mb` limit
4. **Path traversal** - Prevents directory traversal attacks (../, ~, %)
5. **Allowed directories** - Files must be in allowed locations (cwd, /tmp, ./data, ./uploads)
6. **Document structure** - Validates document integrity before processing

### Security Validation

The tool includes multiple security layers:

- **Extension whitelist** prevents processing unauthorized file types
- **File size limits** prevent memory exhaustion
- **Path validation** prevents directory traversal attacks
- **Content sanitization** removes control characters and enforces limits
- **Directory restrictions** limits file access to safe locations

## Dependencies Setup

The Office Tool requires several external dependencies for full functionality:

### Required Python Packages

```bash
pip install pandas pdfplumber pytesseract python-docx python-pptx pillow tika
```

### Apache Tika Setup

Tika is used as a fallback for text extraction from various formats:

**Requirements:**
- Java 11 or higher (Java 8 is no longer supported in Tika 3.x)

**Automatic (recommended):**
```python
# Tika will download automatically on first use
# Downloads Java server to ~/.tika-server.jar
```

**Manual:**
```bash
# Download Tika server JAR manually (version 3.2.2+ recommended for security fixes)
wget https://repo1.maven.org/maven2/org/apache/tika/tika-server/3.2.2/tika-server-3.2.2.jar
export TIKA_SERVER_JAR=/path/to/tika-server-3.2.2.jar
```

### Tesseract OCR Setup

Required for extracting text from images:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # For additional languages
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Verify installation:**
```bash
tesseract --version
```

### Language Data

For multi-language OCR support:

```bash
# English (usually included)
sudo apt-get install tesseract-ocr-eng

# Chinese Simplified
sudo apt-get install tesseract-ocr-chi-sim

# Chinese Traditional
sudo apt-get install tesseract-ocr-chi-tra

# Spanish
sudo apt-get install tesseract-ocr-spa

# French
sudo apt-get install tesseract-ocr-fra
```

### Java Runtime

Required for Apache Tika:

```bash
# Ubuntu/Debian
sudo apt-get install openjdk-11-jre

# macOS
brew install openjdk@11

# Verify
java -version
```

## Operations Supported

The Office Tool supports the following operations:

### 1. Read DOCX
Read content and optionally tables from Word documents.

```python
content = office_tool.read_docx('document.docx', include_tables=True)
# Returns: {'paragraphs': [...], 'tables': [...]}
```

### 2. Write DOCX
Create Word documents with text and optional tables.

```python
result = office_tool.write_docx(
    text="Hello World\nSecond line",
    output_path='output.docx',
    table_data=[['Header1', 'Header2'], ['Row1Col1', 'Row1Col2']]
)
# Returns: {'success': True, 'file_path': 'output.docx'}
```

### 3. Read PPTX
Extract text content from PowerPoint presentations.

```python
slides = office_tool.read_pptx('presentation.pptx')
# Returns: ['Slide 1 text', 'Slide 2 text', ...]
```

### 4. Write PPTX
Create PowerPoint presentations with text slides.

```python
result = office_tool.write_pptx(
    slides=['Slide 1 content', 'Slide 2 content'],
    output_path='output.pptx',
    image_path='logo.png'  # Optional image for first slide
)
# Returns: {'success': True, 'file_path': 'output.pptx'}
```

### 5. Read XLSX
Read data from Excel spreadsheets.

```python
data = office_tool.read_xlsx('spreadsheet.xlsx', sheet_name='Sheet1')
# Returns: [{'col1': val1, 'col2': val2}, ...]
```

### 6. Write XLSX
Create Excel spreadsheets from data.

```python
result = office_tool.write_xlsx(
    data=[{'Name': 'John', 'Age': 30}, {'Name': 'Jane', 'Age': 25}],
    output_path='output.xlsx',
    sheet_name='Data'
)
# Returns: {'success': True, 'file_path': 'output.xlsx'}
```

### 7. Extract Text
Universal text extraction from various formats.

```python
text = office_tool.extract_text('document.pdf')
# Works with: .docx, .pptx, .xlsx, .pdf, .png, .jpg, .jpeg, .tiff, .bmp, .gif
# Returns: extracted text as string
```

## Troubleshooting

### Issue: File size validation fails

**Error:** `File too large: 150.3MB, max 100MB`

**Solution:**
```bash
# Increase max file size limit
export OFFICE_TOOL_MAX_FILE_SIZE_MB=200
```

### Issue: Extension not allowed

**Error:** `Extension '.doc' not allowed`

**Solution:**
```bash
# Add the extension if it's safe and supported
# Note: .doc (old format) is NOT supported, use .docx
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf"]'
```

### Issue: Tika server not starting

**Error:** `Failed to extract text with Tika`

**Solutions:**
1. Check Java installation: `java -version`
2. Clear Tika cache: `rm -rf ~/.tika-server.jar`
3. Set TIKA_LOG_PATH: Already configured in tool
4. Check internet connection (first run downloads Tika)

### Issue: Tesseract not found

**Error:** `Failed to extract image text`

**Solution:**
```bash
# Install Tesseract
sudo apt-get install tesseract-ocr  # Ubuntu/Debian
brew install tesseract              # macOS

# Verify installation
tesseract --version
```

### Issue: Font not found in generated documents

**Cause:** Specified font not installed on the system

**Solution:**
```bash
# Use a standard font available on all systems
export OFFICE_TOOL_DEFAULT_FONT=Arial

# Or install the font system-wide
# Ubuntu/Debian
sudo apt-get install fonts-liberation

# macOS - fonts usually pre-installed
```

### Issue: Path not in allowed directories

**Error:** `Path not in allowed directories`

**Solution:**
Files must be in one of the allowed locations:
- Current working directory and subdirectories
- `/tmp` directory
- `./data` directory
- `./uploads` directory

Move files to an allowed location or adjust your working directory.

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_extensions`

**Solution:**
```bash
# Use proper JSON array syntax with double quotes
export OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pdf"]'

# NOT: ['.docx','.pdf'] or .docx,.pdf
```

### Issue: Memory issues with large documents

**Causes:** Large documents consuming too much memory

**Solutions:**
1. Reduce `max_file_size_mb` limit
2. Process documents in chunks
3. Increase system memory
4. Use streaming processing for very large files

### Issue: Corrupted document

**Error:** `Invalid DOCX/PPTX/XLSX structure`

**Causes:** Corrupted or malformed document file

**Solutions:**
1. Try opening the file in Microsoft Office/LibreOffice
2. Repair the document using office software
3. Re-export/re-save the document
4. Check if file was properly uploaded/transferred

## Best Practices

### Security

1. **Minimize allowed extensions** - Only allow file types you actually need
2. **Set conservative file size limits** - Use smallest practical value
3. **Validate file content** - Tool automatically validates document structure
4. **Sanitize output** - Tool sanitizes text to remove control characters
5. **Restrict file paths** - Tool enforces directory restrictions
6. **Monitor file operations** - Log all document processing activities

### Performance

1. **Set appropriate size limits** - Balance between usability and performance
2. **Cache results** - Leverage BaseTool's built-in caching
3. **Process in batches** - For multiple documents, use batch processing
4. **Monitor memory usage** - Large documents can consume significant memory
5. **Use appropriate fonts** - Standard fonts render faster

### Document Quality

1. **Use standard fonts** - Arial, Calibri, Times New Roman
2. **Appropriate font sizes** - 10-12pt for body text, 14-16pt for headings
3. **Sanitize input** - Tool automatically sanitizes text
4. **Validate structure** - Tool validates before processing
5. **Handle tables carefully** - Ensure consistent column counts

### Development vs Production

**Development:**
```bash
OFFICE_TOOL_MAX_FILE_SIZE_MB=200
OFFICE_TOOL_DEFAULT_FONT=Calibri
OFFICE_TOOL_DEFAULT_FONT_SIZE=12
OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf",".png",".jpg"]'
```

**Production:**
```bash
OFFICE_TOOL_MAX_FILE_SIZE_MB=50
OFFICE_TOOL_DEFAULT_FONT=Arial
OFFICE_TOOL_DEFAULT_FONT_SIZE=11
OFFICE_TOOL_ALLOWED_EXTENSIONS='[".docx",".pptx",".xlsx",".pdf"]'
```

### Error Handling

Always wrap office operations in try-except blocks:

```python
from aiecs.tools.task_tools.office_tool import (
    OfficeTool, 
    FileOperationError, 
    SecurityError,
    ContentValidationError
)

office_tool = OfficeTool()

try:
    content = office_tool.read_docx('document.docx')
except FileOperationError as e:
    print(f"File operation failed: {e}")
except SecurityError as e:
    print(f"Security validation failed: {e}")
except ContentValidationError as e:
    print(f"Document validation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- Python-docx documentation: https://python-docx.readthedocs.io/
- Python-pptx documentation: https://python-pptx.readthedocs.io/
- Pandas documentation: https://pandas.pydata.org/docs/
- PDFPlumber documentation: https://github.com/jsvine/pdfplumber
- Tika documentation: https://tika.apache.org/
- Tesseract documentation: https://github.com/tesseract-ocr/tesseract

## Support

For issues or questions about Office Tool configuration:
- Check the tool source code for implementation details
- Review library-specific documentation for document formats
- Consult the main aiecs documentation for architecture overview
- Test with simple documents first to isolate configuration vs. document issues
- Check dependency installation and versions

