# Report Tool Configuration Guide

## Overview

The Report Tool provides comprehensive multi-format report generation capabilities, supporting HTML, Excel, PowerPoint, Markdown, Word, and image-based reports. It features template-based rendering using Jinja2, data visualization with Matplotlib, and batch processing capabilities. The tool can be configured via environment variables using the `REPORT_TOOL_` prefix or through programmatic configuration when initializing the tool.

**Note:** PDF generation is temporarily disabled due to weasyprint deployment complexity and will be re-enabled in a future release.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Report Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
REPORT_TOOL_TEMPLATES_DIR=/path/to/templates
REPORT_TOOL_DEFAULT_OUTPUT_DIR=/path/to/reports
REPORT_TOOL_ALLOWED_EXTENSIONS=[".html",".xlsx",".pptx",".docx",".md",".png"]
REPORT_TOOL_PDF_PAGE_SIZE=A4
REPORT_TOOL_DEFAULT_FONT=Arial
REPORT_TOOL_DEFAULT_FONT_SIZE=12
REPORT_TOOL_ALLOWED_HTML_TAGS=["h1","h2","h3","p","br","a","ul","ol","li","strong","em","table","tr","td","th","span","div","img","hr","code","pre"]
REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES={"a":["href","title","target"],"img":["src","alt","title","width","height"],"*":["class","id","style"]}
REPORT_TOOL_TEMP_FILES_MAX_AGE=3600
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.report_tool import ReportTool

# The tool will automatically use the environment variables
report_tool = ReportTool()
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

from aiecs.tools.task_tools.report_tool import ReportTool
report_tool = ReportTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for security and performance
REPORT_TOOL_TEMPLATES_DIR=/app/templates
REPORT_TOOL_DEFAULT_OUTPUT_DIR=/app/reports
REPORT_TOOL_ALLOWED_EXTENSIONS=[".html",".xlsx",".pptx",".docx"]
REPORT_TOOL_DEFAULT_FONT=Arial
REPORT_TOOL_DEFAULT_FONT_SIZE=12
REPORT_TOOL_TEMP_FILES_MAX_AGE=1800
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
REPORT_TOOL_TEMPLATES_DIR=./templates
REPORT_TOOL_DEFAULT_OUTPUT_DIR=./reports
REPORT_TOOL_ALLOWED_EXTENSIONS=[".html",".xlsx",".pptx",".docx",".md",".png"]
REPORT_TOOL_DEFAULT_FONT=Arial
REPORT_TOOL_DEFAULT_FONT_SIZE=12
REPORT_TOOL_TEMP_FILES_MAX_AGE=7200
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
   # Report Tool Configuration
   
   # Directory for Jinja2 templates
   REPORT_TOOL_TEMPLATES_DIR=./templates
   
   # Default directory for output files
   REPORT_TOOL_DEFAULT_OUTPUT_DIR=./reports
   
   # Allowed file extensions (JSON array)
   REPORT_TOOL_ALLOWED_EXTENSIONS=[".html",".xlsx",".pptx",".docx",".md",".png"]
   
   # Default PDF page size
   REPORT_TOOL_PDF_PAGE_SIZE=A4
   
   # Default font for documents
   REPORT_TOOL_DEFAULT_FONT=Arial
   
   # Default font size in points
   REPORT_TOOL_DEFAULT_FONT_SIZE=12
   
   # Allowed HTML tags (JSON array)
   REPORT_TOOL_ALLOWED_HTML_TAGS=["h1","h2","h3","p","br","a","ul","ol","li","strong","em","table","tr","td","th","span","div","img","hr","code","pre"]
   
   # Allowed HTML attributes (JSON object)
   REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES={"a":["href","title","target"],"img":["src","alt","title","width","height"],"*":["class","id","style"]}
   
   # Maximum age of temporary files in seconds
   REPORT_TOOL_TEMP_FILES_MAX_AGE=3600
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `Arial`, `A4`
   - Integers: Plain numbers: `12`, `3600`
   - Lists: JSON array format: `[".html",".xlsx"]`
   - Sets: JSON array format: `["h1","h2","p"]`
   - Dictionaries: JSON object format: `{"a":["href","title"]}`

## Configuration Options

### 1. Templates Directory

**Environment Variable:** `REPORT_TOOL_TEMPLATES_DIR`

**Type:** String

**Default:** `os.getcwd()` (current working directory)

**Description:** Directory path where Jinja2 templates are stored. This is used by the template loader for HTML, Markdown, and Word document generation.

**Example:**
```bash
export REPORT_TOOL_TEMPLATES_DIR="/app/templates"
```

**Security Note:** Ensure the templates directory is properly secured and only contains trusted templates to prevent template injection attacks.

### 2. Default Output Directory

**Environment Variable:** `REPORT_TOOL_DEFAULT_OUTPUT_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'reports')`

**Description:** Default directory where generated reports are saved. This is used when no specific output path is provided.

**Example:**
```bash
export REPORT_TOOL_DEFAULT_OUTPUT_DIR="/app/reports"
```

**Note:** The directory will be created automatically if it doesn't exist.

### 3. Allowed Extensions

**Environment Variable:** `REPORT_TOOL_ALLOWED_EXTENSIONS`

**Type:** List[str]

**Default:** `['.html', '.pdf', '.xlsx', '.pptx', '.docx', '.md', '.png']`

**Description:** List of allowed file extensions for report outputs. This is a security feature that prevents generation of unauthorized file types.

**Format:** JSON array string with double quotes

**Supported Formats:**
- `.html` - HTML reports
- `.pdf` - PDF reports (currently disabled)
- `.xlsx` - Excel workbooks
- `.pptx` - PowerPoint presentations
- `.docx` - Word documents
- `.md` - Markdown files
- `.png` - Image charts

**Example:**
```bash
# Strict - Only common formats
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".pptx",".docx"]'

# Lenient - All supported formats
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".pdf",".xlsx",".pptx",".docx",".md",".png"]'
```

**Security Note:** Only allow extensions that your application actually needs to generate.

### 4. PDF Page Size

**Environment Variable:** `REPORT_TOOL_PDF_PAGE_SIZE`

**Type:** String

**Default:** `"A4"`

**Description:** Default page size for PDF generation. This setting is currently not used as PDF generation is disabled, but will be relevant when PDF functionality is restored.

**Common Values:**
- `A4` - Standard A4 size (210 × 297 mm)
- `A3` - A3 size (297 × 420 mm)
- `Letter` - US Letter size (8.5 × 11 inches)
- `Legal` - US Legal size (8.5 × 14 inches)

**Example:**
```bash
export REPORT_TOOL_PDF_PAGE_SIZE="A4"
```

### 5. Default Font

**Environment Variable:** `REPORT_TOOL_DEFAULT_FONT`

**Type:** String

**Default:** `"Arial"`

**Description:** Default font family used for document generation in PowerPoint and Word documents.

**Common Fonts:**
- `Arial` - Sans-serif font (default)
- `Times New Roman` - Serif font
- `Calibri` - Modern sans-serif
- `Helvetica` - Clean sans-serif
- `Georgia` - Readable serif

**Example:**
```bash
export REPORT_TOOL_DEFAULT_FONT="Calibri"
```

**Note:** Font availability depends on the system where the tool is running.

### 6. Default Font Size

**Environment Variable:** `REPORT_TOOL_DEFAULT_FONT_SIZE`

**Type:** Integer

**Default:** `12`

**Description:** Default font size in points for document generation in PowerPoint and Word documents.

**Common Sizes:**
- `10` - Small text
- `12` - Standard text (default)
- `14` - Large text
- `16` - Heading text
- `18` - Title text

**Example:**
```bash
export REPORT_TOOL_DEFAULT_FONT_SIZE=14
```

### 7. Allowed HTML Tags

**Environment Variable:** `REPORT_TOOL_ALLOWED_HTML_TAGS`

**Type:** Set[str]

**Default:** `{'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'a', 'ul', 'ol', 'li', 'strong', 'em', 'b', 'i', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'span', 'div', 'img', 'hr', 'code', 'pre'}`

**Description:** Set of HTML tags allowed during HTML sanitization. This prevents XSS attacks by removing dangerous HTML elements.

**Format:** JSON array string with double quotes

**Security Categories:**
- **Safe tags:** `h1`, `h2`, `h3`, `p`, `br`, `strong`, `em`, `ul`, `ol`, `li`
- **Table tags:** `table`, `tr`, `td`, `th`, `thead`, `tbody`
- **Link tags:** `a` (with href attribute)
- **Image tags:** `img` (with src attribute)
- **Code tags:** `code`, `pre`
- **Layout tags:** `span`, `div`, `hr`

**Example:**
```bash
# Minimal - Only basic formatting
export REPORT_TOOL_ALLOWED_HTML_TAGS='["h1","h2","h3","p","br","strong","em"]'

# Standard - Common HTML elements
export REPORT_TOOL_ALLOWED_HTML_TAGS='["h1","h2","h3","p","br","a","ul","ol","li","strong","em","table","tr","td","th","span","div","img"]'
```

**Security Note:** Be cautious with tags like `script`, `iframe`, `object`, and `embed` as they can execute code.

### 8. Allowed HTML Attributes

**Environment Variable:** `REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES`

**Type:** Dict[str, List[str]]

**Default:** `{'a': ['href', 'title', 'target'], 'img': ['src', 'alt', 'title', 'width', 'height'], 'td': ['colspan', 'rowspan', 'align'], 'th': ['colspan', 'rowspan', 'align'], '*': ['class', 'id', 'style']}`

**Description:** Dictionary specifying which HTML attributes are allowed for each tag during sanitization. The `'*'` key applies to all tags.

**Format:** JSON object with string keys and array values

**Attribute Categories:**
- **Link attributes:** `href`, `title`, `target`
- **Image attributes:** `src`, `alt`, `title`, `width`, `height`
- **Table attributes:** `colspan`, `rowspan`, `align`
- **Global attributes:** `class`, `id`, `style`

**Example:**
```bash
# Strict - Minimal attributes
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href"],"img":["src","alt"],"*":["class"]}'

# Standard - Common attributes
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href","title","target"],"img":["src","alt","title","width","height"],"*":["class","id","style"]}'
```

**Security Note:** Avoid allowing `onclick`, `onload`, `javascript:`, and other event handlers that can execute code.

### 9. Temp Files Max Age

**Environment Variable:** `REPORT_TOOL_TEMP_FILES_MAX_AGE`

**Type:** Integer

**Default:** `3600` (1 hour in seconds)

**Description:** Maximum age in seconds for temporary files before they are automatically cleaned up. This helps manage disk space and prevents accumulation of old report files.

**Common Values:**
- `1800` - 30 minutes (short-lived reports)
- `3600` - 1 hour (default)
- `7200` - 2 hours (development)
- `86400` - 24 hours (long-lived reports)

**Example:**
```bash
export REPORT_TOOL_TEMP_FILES_MAX_AGE=7200
```

**Performance Note:** Shorter cleanup times use more disk space but ensure fresh files. Longer times may accumulate old files.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom template and output directories
export REPORT_TOOL_TEMPLATES_DIR="/app/templates"
export REPORT_TOOL_DEFAULT_OUTPUT_DIR="/app/reports"
export REPORT_TOOL_DEFAULT_FONT="Calibri"
export REPORT_TOOL_DEFAULT_FONT_SIZE=14

# Run your application
python app.py
```

### Example 2: Security-Focused Configuration

```bash
# Strict security settings
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".docx"]'
export REPORT_TOOL_ALLOWED_HTML_TAGS='["h1","h2","h3","p","br","strong","em","ul","ol","li"]'
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"*":["class"]}'
export REPORT_TOOL_TEMP_FILES_MAX_AGE=1800
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export REPORT_TOOL_TEMPLATES_DIR="./templates"
export REPORT_TOOL_DEFAULT_OUTPUT_DIR="./reports"
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".pptx",".docx",".md",".png"]'
export REPORT_TOOL_TEMP_FILES_MAX_AGE=7200
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.report_tool import ReportTool

# Initialize with custom configuration
report_tool = ReportTool(config={
    'templates_dir': '/app/templates',
    'default_output_dir': '/app/reports',
    'default_font': 'Calibri',
    'default_font_size': 14,
    'allowed_extensions': ['.html', '.xlsx', '.docx'],
    'temp_files_max_age': 3600
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export REPORT_TOOL_DEFAULT_FONT="Arial"
export REPORT_TOOL_DEFAULT_FONT_SIZE=12
```

```python
# Override for specific instance
report_tool = ReportTool(config={
    'default_font': 'Calibri',  # This overrides the environment variable
    'default_font_size': 14     # This overrides the environment variable
})
```

## Configuration Priority

When the Report Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `REPORT_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export REPORT_TOOL_DEFAULT_FONT=Arial
export REPORT_TOOL_PDF_PAGE_SIZE=A4
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export REPORT_TOOL_DEFAULT_FONT_SIZE=12
export REPORT_TOOL_TEMP_FILES_MAX_AGE=3600
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".docx"]'

# Incorrect (will not parse)
export REPORT_TOOL_ALLOWED_EXTENSIONS=".html,.xlsx,.docx"
```

### Set Values

Sets are treated as lists and must be provided as JSON arrays:

```bash
# Correct
export REPORT_TOOL_ALLOWED_HTML_TAGS='["h1","h2","h3","p","br","strong","em"]'

# Incorrect (will not parse)
export REPORT_TOOL_ALLOWED_HTML_TAGS="h1,h2,h3,p,br,strong,em"
```

### Dictionary Values

Dictionaries must be provided as JSON objects with double quotes:

```bash
# Correct
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href","title"],"img":["src","alt"],"*":["class","id"]}'

# Incorrect (will not parse)
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES="a:href,title;img:src,alt"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href","title"]}'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `templates_dir` must be a non-empty string
- `default_output_dir` must be a non-empty string
- `allowed_extensions` must be a list of strings
- `pdf_page_size` must be a non-empty string
- `default_font` must be a non-empty string
- `default_font_size` must be a positive integer
- `allowed_html_tags` must be a set of strings
- `allowed_html_attributes` must be a dictionary with string keys and list values
- `temp_files_max_age` must be a positive integer

### Runtime Validation

When generating reports, the tool validates:

1. **File extensions** - Output files must have allowed extensions
2. **Template paths** - Template files must exist and be readable
3. **Output paths** - Output directories must be writable
4. **HTML content** - HTML is sanitized against allowed tags and attributes
5. **Data structures** - Input data is validated for each report type

## Operations Supported

The Report Tool supports multiple report generation operations:

### HTML Reports
- `generate_html` - Render HTML reports using Jinja2 templates
- Supports template inheritance, loops, conditionals
- Automatic HTML sanitization for security
- CSRF protection headers

### Excel Reports
- `generate_excel` - Create Excel workbooks with multiple sheets
- Supports data from pandas DataFrames or dictionaries
- Optional cell styling (bold, font size, background color)
- Multiple worksheet support

### PowerPoint Reports
- `generate_pptx` - Create PowerPoint presentations
- Customizable slide layouts and content
- Font and styling options
- Bullet point support

### Markdown Reports
- `generate_markdown` - Render Markdown reports using Jinja2
- Template-based content generation
- Supports all Markdown features

### Word Reports
- `generate_word` - Create Word documents
- Customizable fonts and styling
- Template-based content generation
- Paragraph and formatting support

### Image Reports
- `generate_image` - Generate charts using Matplotlib
- Supports bar, line, and pie charts
- Customizable dimensions and styling
- Data visualization capabilities

### Batch Processing
- `batch_generate` - Generate multiple reports in parallel
- Supports all report types
- Efficient processing of large datasets
- Consistent error handling

### PDF Reports (Currently Disabled)
- `generate_pdf` - PDF generation is temporarily disabled
- Will be re-enabled in future release
- Currently returns informative error message

## Troubleshooting

### Issue: Template not found

**Error:** `TemplateNotFound: template_name`

**Solutions:**
1. Check template path: `export REPORT_TOOL_TEMPLATES_DIR="/correct/path"`
2. Verify template file exists and is readable
3. Check file permissions

### Issue: Output directory not writable

**Error:** `PermissionError` or `FileNotFoundError`

**Solutions:**
```bash
# Set writable output directory
export REPORT_TOOL_DEFAULT_OUTPUT_DIR="/writable/path"

# Or create directory with proper permissions
mkdir -p /path/to/reports
chmod 755 /path/to/reports
```

### Issue: HTML sanitization too strict

**Error:** Content is being stripped or modified

**Solutions:**
```bash
# Add more allowed tags
export REPORT_TOOL_ALLOWED_HTML_TAGS='["h1","h2","h3","p","br","a","ul","ol","li","strong","em","table","tr","td","th","span","div","img","hr","code","pre"]'

# Add more allowed attributes
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href","title","target"],"img":["src","alt","title","width","height"],"*":["class","id","style"]}'
```

### Issue: File extension not allowed

**Error:** `Unsupported file type`

**Solution:**
```bash
# Add the extension to allowed list
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".pptx",".docx",".md",".png"]'
```

### Issue: Font not available

**Error:** Font rendering issues or fallback fonts

**Solutions:**
1. Use system fonts: `export REPORT_TOOL_DEFAULT_FONT="Arial"`
2. Install required fonts on the system
3. Use web-safe fonts: `Calibri`, `Helvetica`, `Times New Roman`

### Issue: Memory issues with large reports

**Error:** `MemoryError` or system becomes unresponsive

**Solutions:**
```bash
# Reduce temp file retention
export REPORT_TOOL_TEMP_FILES_MAX_AGE=1800

# Process reports in smaller batches
# Use batch_generate with smaller datasets
```

### Issue: PDF generation error

**Error:** PDF generation is currently disabled

**Solution:**
```python
# Use HTML generation instead
html_path = report_tool.generate_html(template_path, template_str, context, output_path)

# Or wait for future release when PDF functionality is restored
```

### Issue: Dictionary parsing error

**Error:** Configuration parsing fails for complex types

**Solution:**
```bash
# Use proper JSON object syntax
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES='{"a":["href","title"],"img":["src","alt"]}'

# NOT: {"a":href,title} or a:href,title
```

### Issue: List parsing error

**Error:** Configuration parsing fails for list types

**Solution:**
```bash
# Use proper JSON array syntax
export REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".docx"]'

# NOT: [.html,.xlsx,.docx] or .html,.xlsx,.docx
```

## Best Practices

### Security

1. **Template Security** - Only use trusted templates from secure directories
2. **HTML Sanitization** - Keep allowed tags and attributes minimal
3. **File Extensions** - Only allow necessary output formats
4. **Path Validation** - Validate all file paths to prevent directory traversal
5. **Content Validation** - Sanitize all user-provided content

### Performance

1. **Template Caching** - Jinja2 templates are cached automatically
2. **Batch Processing** - Use `batch_generate` for multiple reports
3. **Temp File Management** - Set appropriate cleanup intervals
4. **Memory Management** - Process large datasets in chunks
5. **Resource Cleanup** - Let TempFileManager handle file cleanup

### Template Management

1. **Template Organization** - Organize templates in logical directory structure
2. **Template Inheritance** - Use Jinja2 template inheritance for consistency
3. **Template Testing** - Test templates with various data inputs
4. **Template Documentation** - Document template variables and usage
5. **Version Control** - Keep templates in version control

### Error Handling

Always wrap report generation in try-except blocks:

```python
from aiecs.tools.task_tools.report_tool import ReportTool, FileOperationError

report_tool = ReportTool()

try:
    result = report_tool.generate_html(template_path, template_str, context, output_path)
except FileOperationError as e:
    print(f"Report generation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Development vs Production

**Development:**
```bash
REPORT_TOOL_TEMPLATES_DIR=./templates
REPORT_TOOL_DEFAULT_OUTPUT_DIR=./reports
REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".pptx",".docx",".md",".png"]'
REPORT_TOOL_TEMP_FILES_MAX_AGE=7200
```

**Production:**
```bash
REPORT_TOOL_TEMPLATES_DIR=/app/templates
REPORT_TOOL_DEFAULT_OUTPUT_DIR=/app/reports
REPORT_TOOL_ALLOWED_EXTENSIONS='[".html",".xlsx",".docx"]'
REPORT_TOOL_TEMP_FILES_MAX_AGE=1800
```

### Template Examples

**HTML Template (template.html):**
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>{{ description }}</p>
    {% if data %}
    <table>
        {% for row in data %}
        <tr>
            <td>{{ row.name }}</td>
            <td>{{ row.value }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
</body>
</html>
```

**Markdown Template (template.md):**
```markdown
# {{ title }}

{{ description }}

{% if data %}
| Name | Value |
|------|-------|
{% for row in data %}
| {{ row.name }} | {{ row.value }} |
{% endfor %}
{% endif %}
```

## Related Documentation

- Tool implementation details in the source code
- Jinja2 documentation: https://jinja.palletsprojects.com/
- Matplotlib documentation: https://matplotlib.org/
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Report Tool configuration:
- Check the tool source code for implementation details
- Review Jinja2 documentation for template syntax
- Consult the main aiecs documentation for architecture overview
- Test with simple templates first to isolate configuration vs. template issues
- Monitor disk space and temp file cleanup
