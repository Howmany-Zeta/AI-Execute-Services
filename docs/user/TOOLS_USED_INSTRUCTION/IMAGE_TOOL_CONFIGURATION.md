# Image Tool Configuration Guide

## Overview

The Image Tool provides image processing capabilities including loading, OCR text extraction, metadata retrieval, resizing, and filtering. It can be configured via environment variables using the `IMAGE_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Image Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
IMAGE_TOOL_MAX_FILE_SIZE_MB=50
IMAGE_TOOL_ALLOWED_EXTENSIONS=[".jpg",".jpeg",".png",".bmp",".tiff",".gif"]
IMAGE_TOOL_TESSERACT_POOL_SIZE=2
IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.image_tool import ImageTool

# The tool will automatically use the environment variables
image_tool = ImageTool()
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

from aiecs.tools.task_tools.image_tool import ImageTool
image_tool = ImageTool()
```

**Example `.env.production`:**
```bash
# Production settings - strict limits for security
IMAGE_TOOL_MAX_FILE_SIZE_MB=20
IMAGE_TOOL_ALLOWED_EXTENSIONS=[".jpg",".jpeg",".png"]
IMAGE_TOOL_TESSERACT_POOL_SIZE=4
```

**Example `.env.development`:**
```bash
# Development settings - relaxed limits for testing
IMAGE_TOOL_MAX_FILE_SIZE_MB=100
IMAGE_TOOL_ALLOWED_EXTENSIONS=[".jpg",".jpeg",".png",".bmp",".tiff",".gif"]
IMAGE_TOOL_TESSERACT_POOL_SIZE=1
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
   # Image Tool Configuration
   
   # Maximum file size in megabytes
   IMAGE_TOOL_MAX_FILE_SIZE_MB=50
   
   # Allowed image file extensions (JSON array)
   IMAGE_TOOL_ALLOWED_EXTENSIONS=[".jpg",".jpeg",".png",".bmp",".tiff",".gif"]
   
   # Number of Tesseract OCR processes
   IMAGE_TOOL_TESSERACT_POOL_SIZE=2
   
   # Default OCR language (e.g., 'eng', 'chi_sim', 'eng+chi_sim')
   IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Integers: Plain numbers: `50`, `100`
   - Lists: Use JSON array format with double quotes: `[".jpg",".png"]`

## Configuration Options

### 1. Max File Size (MB)

**Environment Variable:** `IMAGE_TOOL_MAX_FILE_SIZE_MB`

**Type:** Integer

**Default:** `50`

**Description:** Maximum allowed file size in megabytes. Files larger than this limit will be rejected during validation for security and performance reasons.

**Common Values:**
- `10` - Conservative limit for public APIs
- `20` - Moderate limit for web applications
- `50` - Default (balanced)
- `100` - Generous limit for internal tools

**Example:**
```bash
export IMAGE_TOOL_MAX_FILE_SIZE_MB=20
```

**Security Note:** Keep this value as low as practical for your use case to prevent memory exhaustion attacks.

### 2. Allowed Extensions

**Environment Variable:** `IMAGE_TOOL_ALLOWED_EXTENSIONS`

**Type:** List[str]

**Default:** `['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']`

**Description:** List of allowed image file extensions. This is a critical security feature that prevents processing of unauthorized or potentially malicious file types.

**Format:** JSON array string with double quotes

**Supported Formats:**
- `.jpg`, `.jpeg` - JPEG images
- `.png` - PNG images
- `.bmp` - Bitmap images
- `.tiff` - TIFF images
- `.gif` - GIF images

**Example:**
```bash
# Strict - Only common web formats
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png"]'

# Lenient - All supported formats
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png",".bmp",".tiff",".gif"]'
```

**Security Note:** Only allow extensions that your application actually needs to process.

### 3. Tesseract Pool Size

**Environment Variable:** `IMAGE_TOOL_TESSERACT_POOL_SIZE`

**Type:** Integer

**Default:** `2`

**Description:** Number of Tesseract OCR processes to maintain in the pool for parallel text extraction. Higher values allow more concurrent OCR operations but consume more system resources.

**Common Values:**
- `1` - Single process (development/testing)
- `2` - Default (balanced)
- `4` - Higher concurrency for production
- `8` - Maximum concurrency for high-load scenarios

**Example:**
```bash
export IMAGE_TOOL_TESSERACT_POOL_SIZE=4
```

**Performance Note:** Set based on expected concurrent OCR requests and available CPU cores. Each process consumes memory and CPU.

**Requirement:** Tesseract must be installed on the system for OCR functionality to work.

### 4. Default OCR Language

**Environment Variable:** `IMAGE_TOOL_DEFAULT_OCR_LANGUAGE`

**Type:** String

**Default:** `eng`

**Description:** Default language code for OCR text extraction. This value is used when the `lang` parameter is not specified in the `ocr()` method call. Supports single language codes (e.g., `eng`, `chi_sim`) or multi-language format using `+` separator (e.g., `eng+chi_sim`).

**Common Language Codes:**
- `eng` - English (default)
- `chi_sim` - Simplified Chinese
- `chi_tra` - Traditional Chinese
- `spa` - Spanish
- `fra` - French
- `jpn` - Japanese
- `deu` - German

**Multi-Language Support:**
You can specify multiple languages using the `+` separator. Tesseract will try to recognize text in any of the specified languages:
- `eng+chi_sim` - English and Simplified Chinese
- `eng+spa+fra` - English, Spanish, and French

**Examples:**
```bash
# Single language (English)
export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng

# Single language (Simplified Chinese)
export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=chi_sim

# Multi-language (English + Simplified Chinese)
export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng+chi_sim
```

**Usage:**
```python
from aiecs.tools.task_tools.image_tool import ImageTool

# Initialize with default language from config
image_tool = ImageTool()

# Uses default_ocr_language from config (e.g., 'eng+chi_sim')
text = image_tool.ocr('image.png')

# Override default language for this call
text = image_tool.ocr('image.png', lang='chi_sim')

# Use multi-language for this call
text = image_tool.ocr('image.png', lang='eng+jpn')
```

**Note:** Make sure the corresponding Tesseract language data packs are installed on your system. See the "Language Data" section below for installation instructions.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom limits and pool size
export IMAGE_TOOL_MAX_FILE_SIZE_MB=30
export IMAGE_TOOL_TESSERACT_POOL_SIZE=4
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png"]'

# Run your application
python app.py
```

### Example 2: Security-Focused Configuration

```bash
# Strict limits for public-facing applications
export IMAGE_TOOL_MAX_FILE_SIZE_MB=10
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png"]'
export IMAGE_TOOL_TESSERACT_POOL_SIZE=2
```

### Example 3: High-Performance Configuration

```bash
# Optimized for internal high-throughput processing
export IMAGE_TOOL_MAX_FILE_SIZE_MB=100
export IMAGE_TOOL_TESSERACT_POOL_SIZE=8
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png",".bmp",".tiff"]'
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.image_tool import ImageTool

# Initialize with custom configuration
image_tool = ImageTool(config={
    'max_file_size_mb': 30,
    'allowed_extensions': ['.jpg', '.jpeg', '.png'],
    'tesseract_pool_size': 4,
    'default_ocr_language': 'eng+chi_sim'  # Multi-language support
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export IMAGE_TOOL_MAX_FILE_SIZE_MB=50
```

```python
# Override for specific instance
image_tool = ImageTool(config={
    'max_file_size_mb': 20  # This overrides the environment variable
})
```

### Example 6: Dynamic Configuration Update

```python
from aiecs.tools.task_tools.image_tool import ImageTool

# Initialize with defaults
image_tool = ImageTool()

# Update configuration at runtime
image_tool.update_config({
    'max_file_size_mb': 100,
    'tesseract_pool_size': 6,  # Pool will be reinitialized
    'default_ocr_language': 'chi_sim'  # Change default language
})
```

## Configuration Priority

When the Image Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `IMAGE_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Integer Values

Integers should be provided as numeric strings:

```bash
export IMAGE_TOOL_MAX_FILE_SIZE_MB=50
export IMAGE_TOOL_TESSERACT_POOL_SIZE=4
```

### List Values

Lists must be provided as JSON array strings with double quotes:

```bash
# Correct
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".png",".gif"]'

# Incorrect (will not parse)
export IMAGE_TOOL_ALLOWED_EXTENSIONS=".jpg,.png,.gif"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png"]'
#                                    ^                      ^
#                                    Single quotes for shell
#                                       ^     ^     ^
#                                       Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `max_file_size_mb` must be a positive integer
- `allowed_extensions` must be a list of strings
- `tesseract_pool_size` must be a positive integer
- `default_ocr_language` must be a non-empty string

### File Validation

When processing images, the tool validates:

1. **File existence** - File must exist at the specified path
2. **File extension** - Must be in `allowed_extensions` list
3. **File size** - Must not exceed `max_file_size_mb` limit
4. **File integrity** - Must be a valid image file

### Security Validation

The tool includes multiple security layers:

- Extension whitelist prevents processing unauthorized file types
- File size limits prevent memory exhaustion
- Path normalization prevents directory traversal attacks
- Output path validation prevents overwriting existing files

## Tesseract Setup

The Image Tool uses Tesseract OCR for text extraction. Follow these steps to set it up:

### Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Language Data

Install additional language packs as needed:

```bash
# English (usually included by default)
sudo apt-get install tesseract-ocr-eng

# Chinese
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra

# Spanish
sudo apt-get install tesseract-ocr-spa

# French
sudo apt-get install tesseract-ocr-fra
```

### Verify Installation

```bash
tesseract --version
```

You should see output like:
```
tesseract 4.1.1
```

### Using OCR with Different Languages

**Method 1: Configure Default Language**

Set the default language via environment variable or config:

```bash
# Set default to Chinese
export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=chi_sim
```

```python
from aiecs.tools.task_tools.image_tool import ImageTool

image_tool = ImageTool()

# Uses configured default (chi_sim)
text = image_tool.ocr('chinese_image.png')

# Override for specific call
text = image_tool.ocr('english_image.png', lang='eng')
```

**Method 2: Multi-Language Support**

Enable multi-language recognition by configuring multiple languages:

```bash
# Set default to English + Chinese
export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng+chi_sim
```

```python
from aiecs.tools.task_tools.image_tool import ImageTool

image_tool = ImageTool()

# Uses configured default (eng+chi_sim) - recognizes both English and Chinese
text = image_tool.ocr('mixed_image.png')

# Use different multi-language combination for specific call
text = image_tool.ocr('image.png', lang='eng+jpn+spa')
```

**Method 3: Per-Call Language Specification**

Specify language for each OCR call:

```python
from aiecs.tools.task_tools.image_tool import ImageTool

image_tool = ImageTool()

# English (uses default if not configured)
text = image_tool.ocr('image.png')

# Chinese
text = image_tool.ocr('chinese_image.png', lang='chi_sim')

# Spanish
text = image_tool.ocr('spanish_image.png', lang='spa')

# Multi-language
text = image_tool.ocr('mixed_image.png', lang='eng+chi_sim')
```

## Operations Supported

The Image Tool supports the following operations:

### 1. Load
Load an image and return its dimensions and color mode.

```python
info = image_tool.load('photo.jpg')
# Returns: {'size': (width, height), 'mode': 'RGB'}
```

### 2. OCR (Optical Character Recognition)
Extract text from an image.

```python
text = image_tool.ocr('document.png')
# Returns: extracted text as string
```

### 3. Metadata
Retrieve image metadata including EXIF data.

```python
metadata = image_tool.metadata('photo.jpg', include_exif=True)
# Returns: {'size': tuple, 'mode': str, 'exif': dict}
```

### 4. Resize
Resize an image to specified dimensions.

```python
result = image_tool.resize('input.jpg', 'output.jpg', width=800, height=600)
# Returns: {'success': True, 'output_path': 'output.jpg'}
```

### 5. Filter
Apply image filters (blur, sharpen, edge_enhance).

```python
result = image_tool.filter('input.jpg', 'output.jpg', filter_type='sharpen')
# Returns: {'success': True, 'output_path': 'output.jpg'}
```

## Troubleshooting

### Issue: File size validation fails

**Error:** `File too large: 75.3MB, max 50MB`

**Solution:**
```bash
# Increase max file size limit
export IMAGE_TOOL_MAX_FILE_SIZE_MB=100
```

### Issue: Extension not allowed

**Error:** `Extension '.webp' not allowed`

**Solution:**
```bash
# Add the extension to allowed list (if safe)
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png",".webp"]'
```

### Issue: Tesseract not found

**Error:** `Tesseract not found; OCR will be disabled`

**Solution:**
```bash
# Install Tesseract
sudo apt-get install tesseract-ocr  # Ubuntu/Debian
brew install tesseract              # macOS

# Verify installation
tesseract --version
```

### Issue: OCR returns empty or garbled text

**Causes:** Poor image quality, wrong language, unsupported format

**Solutions:**
1. Ensure image has good contrast and resolution
2. Configure default language: `export IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=chi_sim`
3. Specify correct language per call: `ocr('image.png', lang='chi_sim')`
4. Use multi-language format: `ocr('image.png', lang='eng+chi_sim')`
5. Pre-process image (increase contrast, remove noise)
6. Install appropriate language data packs

### Issue: Pool size too small for concurrent requests

**Error:** `No Tesseract processes available`

**Solution:**
```bash
# Increase pool size
export IMAGE_TOOL_TESSERACT_POOL_SIZE=8
```

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_extensions`

**Solution:**
```bash
# Use proper JSON array syntax with double quotes
export IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".png"]'

# NOT: ['.jpg','.png'] or .jpg,.png
```

### Issue: Memory issues with large images

**Causes:** Large image files consuming too much memory

**Solutions:**
1. Reduce `max_file_size_mb` limit
2. Implement image downsampling before processing
3. Reduce `tesseract_pool_size` to free memory
4. Monitor and increase system memory if needed

## Best Practices

### Security

1. **Minimize allowed extensions** - Only allow file types you actually need
2. **Set conservative file size limits** - Use smallest practical value
3. **Validate file content** - Don't trust extensions alone (Pillow handles this)
4. **Sanitize file paths** - Tool automatically normalizes paths
5. **Use output path validation** - Prevents overwriting existing files

### Performance

1. **Tune pool size** - Match `tesseract_pool_size` to expected concurrent OCR load
2. **Optimize file sizes** - Compress images before processing
3. **Cache results** - Leverage BaseTool's built-in caching
4. **Monitor resources** - Watch memory and CPU usage under load
5. **Use appropriate formats** - PNG for text, JPEG for photos

### Development vs Production

**Development:**
```bash
IMAGE_TOOL_MAX_FILE_SIZE_MB=100
IMAGE_TOOL_TESSERACT_POOL_SIZE=1
IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png",".bmp",".tiff",".gif"]'
IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng
```

**Production:**
```bash
IMAGE_TOOL_MAX_FILE_SIZE_MB=20
IMAGE_TOOL_TESSERACT_POOL_SIZE=4
IMAGE_TOOL_ALLOWED_EXTENSIONS='[".jpg",".jpeg",".png"]'
IMAGE_TOOL_DEFAULT_OCR_LANGUAGE=eng+chi_sim  # Multi-language support
```

### Error Handling

Always wrap image operations in try-except blocks:

```python
from aiecs.tools.task_tools.image_tool import ImageTool, FileOperationError, SecurityError

image_tool = ImageTool()

try:
    result = image_tool.load('photo.jpg')
except FileOperationError as e:
    print(f"File operation failed: {e}")
except SecurityError as e:
    print(f"Security validation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- PIL/Pillow documentation: https://pillow.readthedocs.io/
- Tesseract documentation: https://github.com/tesseract-ocr/tesseract
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Image Tool configuration:
- Check the tool source code for implementation details
- Review Pillow and Tesseract documentation for specific functionality
- Consult the main documentation for architecture overview
- Test with simple images first to isolate configuration vs. image quality issues

