# Document Layout Tool Configuration Guide

## Overview

The Document Layout Tool provides comprehensive capabilities for managing document presentation and formatting, including page setup, multi-column layouts, headers, footers, typography control, and break management. It supports various page sizes (A4, A3, A5, Letter, Legal, Tabloid), orientations (Portrait, Landscape), and layout types (single column, multi-column, magazine, newspaper, academic). The tool integrates with DocumentCreatorTool, DocumentWriterTool, and ContentInsertionTool to provide a complete document layout workflow. The tool can be configured via environment variables using the `DOC_LAYOUT_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Document Layout Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DOC_LAYOUT_TEMP_DIR=/path/to/temp
DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
DOC_LAYOUT_DEFAULT_MARGINS={"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}
DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
DOC_LAYOUT_PRESERVE_FORMATTING=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool

# The tool will automatically use the environment variables
layout_tool = DocumentLayoutTool()
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

from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool
layout_tool = DocumentLayoutTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for professional documents
DOC_LAYOUT_TEMP_DIR=/app/temp/layouts
DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
DOC_LAYOUT_DEFAULT_MARGINS={"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}
DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
DOC_LAYOUT_PRESERVE_FORMATTING=true
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
DOC_LAYOUT_TEMP_DIR=./temp/layouts
DOC_LAYOUT_DEFAULT_PAGE_SIZE=letter
DOC_LAYOUT_DEFAULT_ORIENTATION=landscape
DOC_LAYOUT_DEFAULT_MARGINS={"top":1.0,"bottom":1.0,"left":1.0,"right":1.0}
DOC_LAYOUT_AUTO_ADJUST_LAYOUT=false
DOC_LAYOUT_PRESERVE_FORMATTING=false
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
   # Document Layout Tool Configuration
   
   # Temporary directory for layout processing
   DOC_LAYOUT_TEMP_DIR=/path/to/temp
   
   # Default page size
   DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
   
   # Default page orientation
   DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
   
   # Default page margins in centimeters (JSON format)
   DOC_LAYOUT_DEFAULT_MARGINS={"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}
   
   # Whether to automatically adjust layout
   DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
   
   # Whether to preserve existing formatting
   DOC_LAYOUT_PRESERVE_FORMATTING=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `a4`, `/path/to/dir`
   - Booleans: `true` or `false`
   - Dict: JSON format: `{"key":"value"}`

## Configuration Options

### 1. Temp Directory

**Environment Variable:** `DOC_LAYOUT_TEMP_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_layouts')`

**Description:** Temporary directory used for layout processing operations. This directory stores intermediate layout files, temporary formatting data, and processing artifacts.

**Example:**
```bash
export DOC_LAYOUT_TEMP_DIR="/app/temp/layouts"
```

**Security Note:** Ensure the directory has appropriate permissions and is not accessible via web servers.

### 2. Default Page Size

**Environment Variable:** `DOC_LAYOUT_DEFAULT_PAGE_SIZE`

**Type:** String

**Default:** `"a4"`

**Description:** Default page size for document layouts. This size is used when no specific page size is requested.

**Supported Sizes:**
- `a4` - A4 format (210 × 297 mm) - default
- `a3` - A3 format (297 × 420 mm)
- `a5` - A5 format (148 × 210 mm)
- `letter` - US Letter format (8.5 × 11 inches)
- `legal` - US Legal format (8.5 × 14 inches)
- `tabloid` - Tabloid format (11 × 17 inches)
- `custom` - Custom page size

**Example:**
```bash
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=letter
```

**Size Selection:**
- Use `a4` for international documents
- Use `letter` for US documents
- Use `a3` for large presentations
- Use `a5` for small booklets

### 3. Default Orientation

**Environment Variable:** `DOC_LAYOUT_DEFAULT_ORIENTATION`

**Type:** String

**Default:** `"portrait"`

**Description:** Default page orientation for document layouts. This orientation is used when no specific orientation is requested.

**Supported Orientations:**
- `portrait` - Vertical orientation (default)
- `landscape` - Horizontal orientation

**Example:**
```bash
export DOC_LAYOUT_DEFAULT_ORIENTATION=landscape
```

**Orientation Selection:**
- Use `portrait` for standard documents
- Use `landscape` for presentations and wide content

### 4. Default Margins

**Environment Variable:** `DOC_LAYOUT_DEFAULT_MARGINS`

**Type:** Dict[str, float]

**Default:** `{"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}`

**Description:** Default page margins in centimeters for document layouts. These margins are applied when no specific margins are requested.

**Format:** JSON object with four keys: `top`, `bottom`, `left`, `right`

**Common Values:**
- Standard: `{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}` (2.5cm all around)
- Narrow: `{"top":1.0,"bottom":1.0,"left":1.0,"right":1.0}` (1cm all around)
- Wide: `{"top":3.0,"bottom":3.0,"left":3.0,"right":3.0}` (3cm all around)
- Asymmetric: `{"top":2.5,"bottom":2.5,"left":3.0,"right":2.0}` (binding margin)

**Example:**
```bash
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":3.0,"right":2.0}'
```

**Margin Guidelines:**
- Use 2.5cm for standard documents
- Use 3cm left margin for bound documents
- Use 1cm for draft documents
- Use 3cm+ for formal documents

### 5. Auto Adjust Layout

**Environment Variable:** `DOC_LAYOUT_AUTO_ADJUST_LAYOUT`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically adjust layout for optimal presentation. When enabled, the tool automatically optimizes spacing, column widths, and element positioning.

**Values:**
- `true` - Enable automatic layout adjustment (default)
- `false` - Disable automatic layout adjustment

**Example:**
```bash
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
```

**Use Cases:**
- Enable for professional documents
- Disable for precise manual control
- Enable for responsive layouts

### 6. Preserve Formatting

**Environment Variable:** `DOC_LAYOUT_PRESERVE_FORMATTING`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to preserve existing formatting when applying layouts. When enabled, the tool maintains existing text formatting, styles, and custom elements.

**Values:**
- `true` - Preserve existing formatting (default)
- `false` - Override existing formatting

**Example:**
```bash
export DOC_LAYOUT_PRESERVE_FORMATTING=true
```

**Use Cases:**
- Enable when adding layouts to existing documents
- Disable for clean layout application
- Enable for style consistency

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom directories and defaults
export DOC_LAYOUT_TEMP_DIR="/app/temp/layouts"
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
export DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'

# Run your application
python app.py
```

### Example 2: Professional Configuration

```bash
# Optimized for professional documents
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
export DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":3.0,"bottom":3.0,"left":3.5,"right":2.5}'
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
export DOC_LAYOUT_PRESERVE_FORMATTING=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DOC_LAYOUT_TEMP_DIR="./temp/layouts"
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=letter
export DOC_LAYOUT_DEFAULT_ORIENTATION=landscape
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":1.0,"bottom":1.0,"left":1.0,"right":1.0}'
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=false
export DOC_LAYOUT_PRESERVE_FORMATTING=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool

# Initialize with custom configuration
layout_tool = DocumentLayoutTool(config={
    'temp_dir': '/app/temp/layouts',
    'default_page_size': 'a4',
    'default_orientation': 'portrait',
    'default_margins': {'top': 2.5, 'bottom': 2.5, 'left': 2.5, 'right': 2.5},
    'auto_adjust_layout': True,
    'preserve_formatting': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
```

```python
# Override for specific instance
layout_tool = DocumentLayoutTool(config={
    'default_page_size': 'letter',  # This overrides the environment variable
    'auto_adjust_layout': False     # This overrides the environment variable
})
```

## Configuration Priority

When the Document Layout Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DOC_LAYOUT_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
export DOC_LAYOUT_TEMP_DIR=/path/to/temp
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
export DOC_LAYOUT_PRESERVE_FORMATTING=false
```

### Dict Values

Dict values must be provided as JSON strings:

```bash
# Correct
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'

# Incorrect (will not parse)
export DOC_LAYOUT_DEFAULT_MARGINS="top:2.5,bottom:2.5,left:2.5,right:2.5"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'
#                                      ^      ^      ^      ^
#                                      JSON object format
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `temp_dir` must be a non-empty string
- `default_page_size` must be a valid page size string
- `default_orientation` must be a valid orientation string
- `default_margins` must be a valid dict with float values
- `auto_adjust_layout` must be a boolean
- `preserve_formatting` must be a boolean

### Runtime Validation

When applying layouts, the tool validates:

1. **Directory accessibility** - Temp directory must be writable
2. **Page size validity** - Page size must be supported
3. **Orientation validity** - Orientation must be valid
4. **Margin structure** - Margins must have required keys and positive values
5. **Document format** - Document format must support layout operations

## Page Sizes

### Standard Sizes

- **A4** - 210 × 297 mm (8.27 × 11.69 inches) - International standard
- **A3** - 297 × 420 mm (11.69 × 16.54 inches) - Large format
- **A5** - 148 × 210 mm (5.83 × 8.27 inches) - Small format

### US Sizes

- **Letter** - 8.5 × 11 inches (216 × 279 mm) - US standard
- **Legal** - 8.5 × 14 inches (216 × 356 mm) - US legal
- **Tabloid** - 11 × 17 inches (279 × 432 mm) - Large US format

### Custom Sizes

- **Custom** - User-defined dimensions
- Specify width and height in millimeters or inches
- Useful for specialized documents

## Orientations

### Portrait

- **Standard** - Height > Width
- **Use Cases:** Documents, reports, letters, academic papers
- **Advantages:** Better for reading, standard format

### Landscape

- **Wide** - Width > Height
- **Use Cases:** Presentations, charts, tables, wide content
- **Advantages:** More horizontal space, better for visual content

## Layout Types

### Column Layouts

- **Single Column** - Traditional document layout
- **Two Column** - Academic papers, newspapers
- **Three Column** - Magazines, newsletters
- **Multi Column** - Flexible column arrangement

### Specialized Layouts

- **Magazine** - Multi-column with images and text
- **Newspaper** - Multiple columns with headlines
- **Academic** - Structured for research papers
- **Custom** - User-defined layout structure

## Layout Presets

### Built-in Presets

- **Default** - Standard document layout
- **Academic Paper** - Research paper formatting
- **Business Report** - Corporate document layout
- **Magazine** - Multi-column magazine layout
- **Newspaper** - Newspaper-style layout
- **Presentation** - Slide-based layout
- **Technical Doc** - Technical documentation
- **Letter** - Business letter format
- **Invoice** - Invoice and billing layout
- **Brochure** - Marketing brochure layout

### Preset Features

- Pre-configured margins and spacing
- Typography settings
- Column arrangements
- Header and footer templates
- Page numbering styles

## Operations Supported

The Document Layout Tool supports comprehensive layout management operations:

### Page Setup
- `set_page_layout` - Configure page size, orientation, and margins
- `apply_page_preset` - Apply predefined page layouts
- `customize_page_setup` - Create custom page configurations
- `validate_page_setup` - Validate page configuration

### Multi-Column Layouts
- `create_multi_column_layout` - Create multi-column document layouts
- `adjust_column_widths` - Modify column widths and spacing
- `balance_columns` - Balance content across columns
- `add_column_breaks` - Insert column breaks

### Headers and Footers
- `setup_headers_footers` - Configure headers and footers
- `add_page_numbering` - Add page numbering
- `customize_header_footer` - Customize header/footer content
- `apply_header_footer_preset` - Apply predefined styles

### Typography and Spacing
- `set_typography` - Configure font and text formatting
- `adjust_spacing` - Modify line and paragraph spacing
- `apply_text_styles` - Apply text formatting styles
- `optimize_typography` - Optimize text layout

### Break Management
- `add_page_breaks` - Insert page breaks
- `add_section_breaks` - Insert section breaks
- `add_column_breaks` - Insert column breaks
- `manage_breaks` - Manage all break types

### Layout Optimization
- `optimize_layout` - Optimize document layout
- `auto_adjust_layout` - Automatically adjust layout
- `validate_layout` - Validate layout configuration
- `export_layout` - Export layout configuration

### Batch Operations
- `batch_apply_layout` - Apply layout to multiple documents
- `batch_optimize` - Optimize multiple document layouts
- `batch_export` - Export multiple layout configurations
- `batch_validate` - Validate multiple layouts

## Troubleshooting

### Issue: Directory not accessible

**Error:** `PermissionError` when accessing temp directory

**Solutions:**
```bash
# Set accessible directory
export DOC_LAYOUT_TEMP_DIR="/accessible/temp/path"

# Or create directory with proper permissions
mkdir -p /path/to/directory
chmod 755 /path/to/directory
```

### Issue: Page size not supported

**Error:** `LayoutConfigurationError` for invalid page size

**Solutions:**
1. Use supported page sizes: `a4`, `a3`, `a5`, `letter`, `legal`, `tabloid`
2. Check page size spelling
3. Use `custom` for special sizes
4. Verify format support

### Issue: Margin validation fails

**Error:** `LayoutConfigurationError` for invalid margins

**Solutions:**
```bash
# Use proper JSON format
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'

# Ensure all required keys are present
# top, bottom, left, right must all be specified
```

### Issue: Layout application fails

**Error:** `PageSetupError` during layout application

**Solutions:**
1. Check document format support
2. Verify layout compatibility
3. Ensure proper permissions
4. Check document structure

### Issue: Formatting not preserved

**Error:** Existing formatting is lost

**Solutions:**
```bash
# Enable formatting preservation
export DOC_LAYOUT_PRESERVE_FORMATTING=true

# Or disable auto-adjustment
export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=false
```

### Issue: Dict parsing error

**Error:** Configuration parsing fails for `default_margins`

**Solution:**
```bash
# Use proper JSON syntax
export DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'

# NOT: {"top":2.5,"bottom":2.5,"left":2.5,"right":2.5} or "top:2.5,bottom:2.5"
```

### Issue: Layout optimization fails

**Error:** Auto-adjustment not working

**Solutions:**
1. Enable auto-adjustment: `export DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true`
2. Check document structure
3. Verify layout compatibility
4. Ensure proper margins

## Best Practices

### Layout Consistency

1. **Standard Margins** - Use consistent margins across documents
2. **Page Size Standards** - Stick to standard page sizes
3. **Typography Consistency** - Use consistent fonts and spacing
4. **Style Guidelines** - Define and follow style guidelines
5. **Template Usage** - Use layout presets for consistency

### Responsive Design

1. **Flexible Layouts** - Design layouts that adapt to content
2. **Column Management** - Use appropriate column arrangements
3. **Break Management** - Insert breaks strategically
4. **Content Flow** - Ensure logical content flow
5. **Adaptive Spacing** - Use flexible spacing systems

### Format Compatibility

1. **Format Support** - Check format-specific layout support
2. **Cross-Platform** - Ensure layouts work across platforms
3. **Export Testing** - Test layouts in target formats
4. **Fallback Options** - Provide fallback layouts
5. **Validation** - Validate layouts before deployment

### Performance Optimization

1. **Layout Caching** - Cache frequently used layouts
2. **Batch Operations** - Use batch operations for multiple documents
3. **Resource Management** - Monitor resource usage
4. **Efficient Processing** - Optimize layout processing
5. **Error Handling** - Implement robust error handling

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **Workflow Integration** - Integrate with document workflow
3. **API Usage** - Use appropriate APIs and interfaces
4. **Error Handling** - Handle errors gracefully
5. **Logging** - Implement comprehensive logging

### Development vs Production

**Development:**
```bash
DOC_LAYOUT_TEMP_DIR=./temp/layouts
DOC_LAYOUT_DEFAULT_PAGE_SIZE=letter
DOC_LAYOUT_DEFAULT_ORIENTATION=landscape
DOC_LAYOUT_DEFAULT_MARGINS='{"top":1.0,"bottom":1.0,"left":1.0,"right":1.0}'
DOC_LAYOUT_AUTO_ADJUST_LAYOUT=false
DOC_LAYOUT_PRESERVE_FORMATTING=false
```

**Production:**
```bash
DOC_LAYOUT_TEMP_DIR=/app/temp/layouts
DOC_LAYOUT_DEFAULT_PAGE_SIZE=a4
DOC_LAYOUT_DEFAULT_ORIENTATION=portrait
DOC_LAYOUT_DEFAULT_MARGINS='{"top":2.5,"bottom":2.5,"left":2.5,"right":2.5}'
DOC_LAYOUT_AUTO_ADJUST_LAYOUT=true
DOC_LAYOUT_PRESERVE_FORMATTING=true
```

### Error Handling

Always wrap layout operations in try-except blocks:

```python
from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool, DocumentLayoutError, LayoutConfigurationError, PageSetupError

layout_tool = DocumentLayoutTool()

try:
    result = layout_tool.set_page_layout(
        document_path="document.docx",
        page_size="a4",
        orientation="portrait",
        margins={"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5}
    )
except LayoutConfigurationError as e:
    print(f"Layout configuration failed: {e}")
except PageSetupError as e:
    print(f"Page setup failed: {e}")
except DocumentLayoutError as e:
    print(f"Document layout error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install document processing dependencies
pip install python-docx reportlab

# Install layout processing dependencies
pip install pillow
```

### Optional Dependencies

```bash
# For advanced layout features
pip install reportlab weasyprint

# For image processing
pip install pillow opencv-python

# For typography
pip install fonttools
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import reportlab
    import PIL
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test external tool availability
try:
    from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool
    from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
    from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool
    print("External tools available")
except ImportError as e:
    print(f"External tool not available: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- DocumentCreatorTool documentation for document creation
- DocumentWriterTool documentation for content writing
- ContentInsertionTool documentation for complex content
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Document Layout Tool configuration:
- Check the tool source code for implementation details
- Review external tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple layouts first to isolate configuration vs. layout issues
- Monitor directory permissions and disk space
- Verify page size and orientation support
- Check margin format and values
- Ensure proper layout preset usage
- Validate document format compatibility
