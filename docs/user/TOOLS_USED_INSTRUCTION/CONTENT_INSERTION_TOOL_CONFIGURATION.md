# Content Insertion Tool Configuration Guide

## Overview

The Content Insertion Tool provides comprehensive capabilities for adding complex content elements to documents, including charts, tables, images, media, and interactive elements. It integrates with ChartTool, PandasTool, and ImageTool to generate and process content, then inserts it into documents with proper formatting and cross-referencing. The tool can be configured via environment variables using the `CONTENT_INSERT_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Content Insertion Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
CONTENT_INSERT_TEMP_DIR=/path/to/temp
CONTENT_INSERT_ASSETS_DIR=/path/to/assets
CONTENT_INSERT_MAX_IMAGE_SIZE=10485760
CONTENT_INSERT_MAX_CHART_SIZE=[1200,800]
CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
CONTENT_INSERT_OPTIMIZE_IMAGES=true
CONTENT_INSERT_AUTO_RESIZE=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool

# The tool will automatically use the environment variables
content_tool = ContentInsertionTool()
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

from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool
content_tool = ContentInsertionTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance and storage
CONTENT_INSERT_TEMP_DIR=/app/temp/content_insertion
CONTENT_INSERT_ASSETS_DIR=/app/assets/documents
CONTENT_INSERT_MAX_IMAGE_SIZE=20971520
CONTENT_INSERT_MAX_CHART_SIZE=[1600,1200]
CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
CONTENT_INSERT_OPTIMIZE_IMAGES=true
CONTENT_INSERT_AUTO_RESIZE=true
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
CONTENT_INSERT_TEMP_DIR=./temp/content_insertion
CONTENT_INSERT_ASSETS_DIR=./assets/documents
CONTENT_INSERT_MAX_IMAGE_SIZE=5242880
CONTENT_INSERT_MAX_CHART_SIZE=[800,600]
CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
CONTENT_INSERT_OPTIMIZE_IMAGES=false
CONTENT_INSERT_AUTO_RESIZE=false
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
   # Content Insertion Tool Configuration
   
   # Temporary directory for content processing
   CONTENT_INSERT_TEMP_DIR=/path/to/temp
   
   # Directory for document assets
   CONTENT_INSERT_ASSETS_DIR=/path/to/assets
   
   # Maximum image size in bytes (10MB)
   CONTENT_INSERT_MAX_IMAGE_SIZE=10485760
   
   # Maximum chart size in pixels (width, height)
   CONTENT_INSERT_MAX_CHART_SIZE=[1200,800]
   
   # Default image format for generated content
   CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
   
   # Whether to optimize images automatically
   CONTENT_INSERT_OPTIMIZE_IMAGES=true
   
   # Whether to automatically resize content to fit
   CONTENT_INSERT_AUTO_RESIZE=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `png`, `/path/to/dir`
   - Integers: Plain numbers: `10485760`, `1200`
   - Booleans: `true` or `false`
   - Tuples: JSON array format: `[1200,800]`

## Configuration Options

### 1. Temp Directory

**Environment Variable:** `CONTENT_INSERT_TEMP_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'content_insertion')`

**Description:** Temporary directory used for processing content during insertion operations. This directory stores intermediate files, temporary charts, and processing artifacts.

**Example:**
```bash
export CONTENT_INSERT_TEMP_DIR="/app/temp/content_insertion"
```

**Security Note:** Ensure the directory has appropriate permissions and is not accessible via web servers.

### 2. Assets Directory

**Environment Variable:** `CONTENT_INSERT_ASSETS_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_assets')`

**Description:** Directory where document assets (images, charts, media files) are stored permanently. This is where final processed content is saved for document integration.

**Example:**
```bash
export CONTENT_INSERT_ASSETS_DIR="/app/assets/documents"
```

**Storage Note:** This directory should have sufficient space for all document assets and be backed up regularly.

### 3. Max Image Size

**Environment Variable:** `CONTENT_INSERT_MAX_IMAGE_SIZE`

**Type:** Integer

**Default:** `10 * 1024 * 1024` (10MB)

**Description:** Maximum image size in bytes for processing. Images larger than this will be rejected or resized to prevent memory issues.

**Common Values:**
- `5 * 1024 * 1024` - 5MB (small images)
- `10 * 1024 * 1024` - 10MB (default)
- `20 * 1024 * 1024` - 20MB (large images)
- `50 * 1024 * 1024` - 50MB (very large images)

**Example:**
```bash
export CONTENT_INSERT_MAX_IMAGE_SIZE=20971520
```

**Memory Note:** Larger values allow bigger images but use more memory during processing.

### 4. Max Chart Size

**Environment Variable:** `CONTENT_INSERT_MAX_CHART_SIZE`

**Type:** Tuple[int, int]

**Default:** `(1200, 800)`

**Description:** Maximum chart dimensions in pixels (width, height). Charts larger than these dimensions will be resized to fit within these limits.

**Format:** JSON array with two integers: `[width, height]`

**Common Values:**
- `[800, 600]` - Small charts (development)
- `[1200, 800]` - Standard charts (default)
- `[1600, 1200]` - Large charts (presentations)
- `[2400, 1800]` - Very large charts (publications)

**Example:**
```bash
export CONTENT_INSERT_MAX_CHART_SIZE=[1600,1200]
```

**Quality Note:** Higher resolutions provide better quality but use more memory and storage.

### 5. Default Image Format

**Environment Variable:** `CONTENT_INSERT_DEFAULT_IMAGE_FORMAT`

**Type:** String

**Default:** `"png"`

**Description:** Default image format for generated content (charts, processed images). This format is used when no specific format is requested.

**Supported Formats:**
- `png` - PNG format (default, lossless)
- `jpg` - JPEG format (lossy, smaller files)
- `jpeg` - JPEG format (alternative extension)
- `svg` - SVG format (vector, scalable)
- `webp` - WebP format (modern, efficient)

**Example:**
```bash
export CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=jpg
```

**Quality Note:** PNG provides lossless quality, JPEG provides smaller file sizes.

### 6. Optimize Images

**Environment Variable:** `CONTENT_INSERT_OPTIMIZE_IMAGES`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically optimize images during processing. This includes compression, format conversion, and size reduction while maintaining quality.

**Values:**
- `true` - Enable image optimization (default)
- `false` - Disable image optimization

**Example:**
```bash
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
```

**Performance Note:** Optimization improves file sizes but may increase processing time.

### 7. Auto Resize

**Environment Variable:** `CONTENT_INSERT_AUTO_RESIZE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically resize content to fit within specified limits. This ensures content fits properly in documents and doesn't exceed size constraints.

**Values:**
- `true` - Enable automatic resizing (default)
- `false` - Disable automatic resizing

**Example:**
```bash
export CONTENT_INSERT_AUTO_RESIZE=true
```

**Layout Note:** Auto-resize ensures content fits properly but may change aspect ratios.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom directories and limits
export CONTENT_INSERT_TEMP_DIR="/app/temp/content"
export CONTENT_INSERT_ASSETS_DIR="/app/assets/documents"
export CONTENT_INSERT_MAX_IMAGE_SIZE=20971520
export CONTENT_INSERT_MAX_CHART_SIZE=[1600,1200]

# Run your application
python app.py
```

### Example 2: High-Quality Configuration

```bash
# Optimized for high-quality content
export CONTENT_INSERT_MAX_IMAGE_SIZE=52428800
export CONTENT_INSERT_MAX_CHART_SIZE=[2400,1800]
export CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
export CONTENT_INSERT_AUTO_RESIZE=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export CONTENT_INSERT_TEMP_DIR="./temp/content"
export CONTENT_INSERT_ASSETS_DIR="./assets/documents"
export CONTENT_INSERT_MAX_IMAGE_SIZE=5242880
export CONTENT_INSERT_MAX_CHART_SIZE=[800,600]
export CONTENT_INSERT_OPTIMIZE_IMAGES=false
export CONTENT_INSERT_AUTO_RESIZE=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool

# Initialize with custom configuration
content_tool = ContentInsertionTool(config={
    'temp_dir': '/app/temp/content',
    'assets_dir': '/app/assets/documents',
    'max_image_size': 20971520,
    'max_chart_size': (1600, 1200),
    'default_image_format': 'png',
    'optimize_images': True,
    'auto_resize': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export CONTENT_INSERT_MAX_IMAGE_SIZE=10485760
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
```

```python
# Override for specific instance
content_tool = ContentInsertionTool(config={
    'max_image_size': 20971520,  # This overrides the environment variable
    'optimize_images': False     # This overrides the environment variable
})
```

## Configuration Priority

When the Content Insertion Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `CONTENT_INSERT_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export CONTENT_INSERT_DEFAULT_IMAGE_FORMAT=png
export CONTENT_INSERT_TEMP_DIR=/path/to/temp
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export CONTENT_INSERT_MAX_IMAGE_SIZE=10485760
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
export CONTENT_INSERT_AUTO_RESIZE=false
```

### Tuple Values

Tuples must be provided as JSON arrays with integers:

```bash
# Correct
export CONTENT_INSERT_MAX_CHART_SIZE=[1200,800]

# Incorrect (will not parse)
export CONTENT_INSERT_MAX_CHART_SIZE="1200,800"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export CONTENT_INSERT_MAX_CHART_SIZE=[1200,800]
#                                      ^      ^
#                                      JSON array format
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `temp_dir` must be a non-empty string
- `assets_dir` must be a non-empty string
- `max_image_size` must be a positive integer
- `max_chart_size` must be a tuple of two positive integers
- `default_image_format` must be a non-empty string
- `optimize_images` must be a boolean
- `auto_resize` must be a boolean

### Runtime Validation

When processing content, the tool validates:

1. **Directory accessibility** - Temp and assets directories must be writable
2. **File size limits** - Images must not exceed max_image_size
3. **Chart dimensions** - Charts must fit within max_chart_size
4. **Format support** - Image formats must be supported
5. **External tool availability** - ChartTool, PandasTool, ImageTool must be available

## Operations Supported

The Content Insertion Tool supports comprehensive content insertion operations:

### Chart Insertion
- `insert_chart` - Generate and insert various chart types
- Supports bar, line, pie, scatter, histogram, box, heatmap, area, bubble, and Gantt charts
- Automatic sizing and optimization
- Integration with ChartTool

### Table Insertion
- `insert_table` - Format and insert data tables
- Multiple styling options (default, simple, grid, striped, bordered, corporate, academic, minimal, colorful)
- Automatic formatting and alignment
- Integration with PandasTool

### Image Insertion
- `insert_image` - Process and insert images
- Multiple alignment options (left, center, right, inline, float_left, float_right)
- Automatic optimization and resizing
- Integration with ImageTool

### Media Insertion
- `insert_video` - Embed video content
- `insert_audio` - Embed audio content
- Support for various media formats
- Automatic format detection and optimization

### Interactive Elements
- `insert_form` - Create interactive forms
- `insert_button` - Add clickable buttons
- `insert_link` - Create hyperlinks and cross-references
- Support for various interaction types

### Document Elements
- `insert_citation` - Add academic citations
- `insert_footnote` - Create footnotes
- `insert_callout` - Add highlighted callout boxes
- `insert_code_block` - Format code snippets
- `insert_equation` - Render mathematical equations
- `insert_gallery` - Create image galleries

### Content Management
- `register_content` - Register content for cross-referencing
- `update_content` - Update existing content
- `remove_content` - Remove content elements
- `list_content` - List all inserted content

### Batch Operations
- `batch_insert` - Insert multiple content elements
- `batch_update` - Update multiple content elements
- `batch_remove` - Remove multiple content elements
- Efficient processing of multiple operations

## Troubleshooting

### Issue: Directory not writable

**Error:** `PermissionError` when creating directories

**Solutions:**
```bash
# Set writable directories
export CONTENT_INSERT_TEMP_DIR="/writable/temp/path"
export CONTENT_INSERT_ASSETS_DIR="/writable/assets/path"

# Or create directories with proper permissions
mkdir -p /path/to/directories
chmod 755 /path/to/directories
```

### Issue: Image too large

**Error:** `Image size exceeds maximum limit`

**Solutions:**
```bash
# Increase image size limit
export CONTENT_INSERT_MAX_IMAGE_SIZE=20971520

# Or enable auto-resize
export CONTENT_INSERT_AUTO_RESIZE=true
```

### Issue: Chart generation fails

**Error:** `ChartTool not available` or chart generation errors

**Solutions:**
1. Install ChartTool dependencies: `pip install matplotlib seaborn plotly`
2. Check ChartTool configuration
3. Verify data format and structure
4. Check chart size limits

### Issue: External tool not available

**Error:** `ExternalTool not available`

**Solutions:**
1. Install required dependencies:
   ```bash
   pip install pandas matplotlib pillow
   ```
2. Check tool initialization in logs
3. Verify tool configurations
4. Ensure proper import paths

### Issue: Tuple parsing error

**Error:** Configuration parsing fails for `max_chart_size`

**Solution:**
```bash
# Use proper JSON array syntax
export CONTENT_INSERT_MAX_CHART_SIZE=[1200,800]

# NOT: [1200,800] or "1200,800"
```

### Issue: Boolean parsing error

**Error:** Configuration parsing fails for boolean values

**Solution:**
```bash
# Use lowercase boolean strings
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
export CONTENT_INSERT_AUTO_RESIZE=false

# NOT: True, False, 1, 0, yes, no
```

### Issue: Memory errors with large content

**Error:** `MemoryError` during content processing

**Solutions:**
```bash
# Reduce size limits
export CONTENT_INSERT_MAX_IMAGE_SIZE=5242880
export CONTENT_INSERT_MAX_CHART_SIZE=[800,600]

# Enable optimization
export CONTENT_INSERT_OPTIMIZE_IMAGES=true
export CONTENT_INSERT_AUTO_RESIZE=true
```

### Issue: Content insertion fails

**Error:** `ContentInsertionError` during insertion

**Solutions:**
1. Check directory permissions
2. Verify file formats and sizes
3. Ensure external tools are available
4. Check content data structure
5. Validate insertion parameters

## Best Practices

### Performance Optimization

1. **Directory Management** - Use fast storage for temp and assets directories
2. **Size Limits** - Set appropriate limits based on available memory
3. **Image Optimization** - Enable optimization for better performance
4. **Batch Operations** - Use batch operations for multiple content elements
5. **Caching** - Cache processed content when possible

### Content Quality

1. **Format Selection** - Choose appropriate formats for different content types
2. **Size Optimization** - Balance quality and file size
3. **Auto-resize** - Enable auto-resize for consistent layouts
4. **Image Optimization** - Use optimization for better compression
5. **Chart Sizing** - Set appropriate chart dimensions for target medium

### Asset Management

1. **Directory Organization** - Organize assets in logical directory structures
2. **Backup Strategy** - Implement regular backups of assets directory
3. **Cleanup** - Regularly clean up temporary files
4. **Access Control** - Implement proper access controls for assets
5. **Version Control** - Track changes to important assets

### Integration

1. **Tool Dependencies** - Ensure all required tools are properly configured
2. **Error Handling** - Implement comprehensive error handling
3. **Logging** - Use detailed logging for debugging
4. **Testing** - Test with various content types and sizes
5. **Documentation** - Document custom configurations and workflows

### Development vs Production

**Development:**
```bash
CONTENT_INSERT_TEMP_DIR=./temp/content
CONTENT_INSERT_ASSETS_DIR=./assets/documents
CONTENT_INSERT_MAX_IMAGE_SIZE=5242880
CONTENT_INSERT_MAX_CHART_SIZE=[800,600]
CONTENT_INSERT_OPTIMIZE_IMAGES=false
CONTENT_INSERT_AUTO_RESIZE=false
```

**Production:**
```bash
CONTENT_INSERT_TEMP_DIR=/app/temp/content
CONTENT_INSERT_ASSETS_DIR=/app/assets/documents
CONTENT_INSERT_MAX_IMAGE_SIZE=20971520
CONTENT_INSERT_MAX_CHART_SIZE=[1600,1200]
CONTENT_INSERT_OPTIMIZE_IMAGES=true
CONTENT_INSERT_AUTO_RESIZE=true
```

### Error Handling

Always wrap content insertion operations in try-except blocks:

```python
from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool, ContentInsertionError, ChartInsertionError, ImageInsertionError

content_tool = ContentInsertionTool()

try:
    result = content_tool.insert_chart(chart_data, chart_type="bar")
except ChartInsertionError as e:
    print(f"Chart insertion failed: {e}")
except ImageInsertionError as e:
    print(f"Image insertion failed: {e}")
except ContentInsertionError as e:
    print(f"Content insertion failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pandas numpy pillow

# Install chart generation dependencies
pip install matplotlib seaborn plotly

# Install image processing dependencies
pip install pillow opencv-python
```

### Optional Dependencies

```bash
# For advanced chart types
pip install plotly dash

# For image optimization
pip install pillow-simd

# For media processing
pip install moviepy pydub
```

### Verification

```python
# Test dependency availability
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import PIL
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test external tool availability
try:
    from aiecs.tools.task_tools.chart_tool import ChartTool
    from aiecs.tools.task_tools.pandas_tool import PandasTool
    from aiecs.tools.task_tools.image_tool import ImageTool
    print("External tools available")
except ImportError as e:
    print(f"External tool not available: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- ChartTool documentation for chart generation
- PandasTool documentation for table processing
- ImageTool documentation for image processing
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Content Insertion Tool configuration:
- Check the tool source code for implementation details
- Review external tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple content first to isolate configuration vs. content issues
- Monitor directory permissions and disk space
- Verify external tool availability and configuration
- Check content format and size constraints
