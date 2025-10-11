# Document Creator Tool Configuration Guide

## Overview

The Document Creator Tool provides comprehensive capabilities for creating new documents from templates, initializing document structure, and managing document metadata. It supports multiple document types (reports, articles, presentations, manuals, etc.), various output formats (Markdown, HTML, DOCX, PDF, etc.), and different style presets. The tool integrates with DocumentWriterTool, DocumentLayoutTool, and ContentInsertionTool to provide a complete document creation workflow. The tool can be configured via environment variables using the `DOC_CREATOR_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Document Creator Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DOC_CREATOR_TEMPLATES_DIR=/path/to/templates
DOC_CREATOR_OUTPUT_DIR=/path/to/output
DOC_CREATOR_DEFAULT_FORMAT=markdown
DOC_CREATOR_DEFAULT_STYLE=default
DOC_CREATOR_AUTO_BACKUP=true
DOC_CREATOR_INCLUDE_METADATA=true
DOC_CREATOR_GENERATE_TOC=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool

# The tool will automatically use the environment variables
doc_creator = DocumentCreatorTool()
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

from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool
doc_creator = DocumentCreatorTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance and organization
DOC_CREATOR_TEMPLATES_DIR=/app/templates/documents
DOC_CREATOR_OUTPUT_DIR=/app/output/documents
DOC_CREATOR_DEFAULT_FORMAT=html
DOC_CREATOR_DEFAULT_STYLE=corporate
DOC_CREATOR_AUTO_BACKUP=true
DOC_CREATOR_INCLUDE_METADATA=true
DOC_CREATOR_GENERATE_TOC=true
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
DOC_CREATOR_TEMPLATES_DIR=./templates
DOC_CREATOR_OUTPUT_DIR=./output
DOC_CREATOR_DEFAULT_FORMAT=markdown
DOC_CREATOR_DEFAULT_STYLE=default
DOC_CREATOR_AUTO_BACKUP=false
DOC_CREATOR_INCLUDE_METADATA=false
DOC_CREATOR_GENERATE_TOC=false
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
   # Document Creator Tool Configuration
   
   # Directory for document templates
   DOC_CREATOR_TEMPLATES_DIR=/path/to/templates
   
   # Directory for created documents
   DOC_CREATOR_OUTPUT_DIR=/path/to/output
   
   # Default output format
   DOC_CREATOR_DEFAULT_FORMAT=markdown
   
   # Default style preset
   DOC_CREATOR_DEFAULT_STYLE=default
   
   # Whether to automatically backup created documents
   DOC_CREATOR_AUTO_BACKUP=true
   
   # Whether to include metadata in created documents
   DOC_CREATOR_INCLUDE_METADATA=true
   
   # Whether to generate table of contents automatically
   DOC_CREATOR_GENERATE_TOC=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `markdown`, `/path/to/dir`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Templates Directory

**Environment Variable:** `DOC_CREATOR_TEMPLATES_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'document_templates')`

**Description:** Directory where document templates are stored. This includes built-in templates and any custom templates you add.

**Example:**
```bash
export DOC_CREATOR_TEMPLATES_DIR="/app/templates/documents"
```

**Template Organization:** Organize templates by type:
```
templates/
├── business/
│   ├── report.md
│   └── proposal.md
├── academic/
│   ├── paper.md
│   └── thesis.md
└── technical/
    ├── manual.md
    └── spec.md
```

### 2. Output Directory

**Environment Variable:** `DOC_CREATOR_OUTPUT_DIR`

**Type:** String

**Default:** `os.path.join(tempfile.gettempdir(), 'created_documents')`

**Description:** Directory where created documents are saved. This is the default location for all generated documents.

**Example:**
```bash
export DOC_CREATOR_OUTPUT_DIR="/app/output/documents"
```

**Organization:** Consider organizing by date or project:
```
output/
├── 2024/
│   ├── 01/
│   └── 02/
└── projects/
    ├── project-a/
    └── project-b/
```

### 3. Default Format

**Environment Variable:** `DOC_CREATOR_DEFAULT_FORMAT`

**Type:** String

**Default:** `"markdown"`

**Description:** Default output format for created documents. This format is used when no specific format is requested.

**Supported Formats:**
- `markdown` - Markdown format (default, lightweight)
- `html` - HTML format (web-ready)
- `docx` - Microsoft Word format
- `pdf` - PDF format (print-ready)
- `latex` - LaTeX format (academic)
- `txt` - Plain text format
- `json` - JSON format (structured data)
- `xml` - XML format (structured markup)

**Example:**
```bash
export DOC_CREATOR_DEFAULT_FORMAT=html
```

**Format Selection:**
- Use `markdown` for documentation and notes
- Use `html` for web content
- Use `docx` for business documents
- Use `pdf` for final publications
- Use `latex` for academic papers

### 4. Default Style

**Environment Variable:** `DOC_CREATOR_DEFAULT_STYLE`

**Type:** String

**Default:** `"default"`

**Description:** Default style preset for created documents. This style is applied when no specific style is requested.

**Supported Styles:**
- `default` - Standard formatting (default)
- `corporate` - Business/corporate styling
- `academic` - Academic paper styling
- `modern` - Contemporary design
- `classic` - Traditional formatting
- `minimal` - Clean, minimal design
- `colorful` - Vibrant, colorful design
- `professional` - Professional appearance

**Example:**
```bash
export DOC_CREATOR_DEFAULT_STYLE=corporate
```

**Style Selection:**
- Use `default` for general documents
- Use `corporate` for business documents
- Use `academic` for research papers
- Use `modern` for contemporary content
- Use `minimal` for clean presentations

### 5. Auto Backup

**Environment Variable:** `DOC_CREATOR_AUTO_BACKUP`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically backup created documents. When enabled, the tool creates backup copies of documents before making modifications.

**Values:**
- `true` - Enable automatic backup (default)
- `false` - Disable automatic backup

**Example:**
```bash
export DOC_CREATOR_AUTO_BACKUP=true
```

**Backup Strategy:** Backups are stored in a `.backup` subdirectory within the output directory.

### 6. Include Metadata

**Environment Variable:** `DOC_CREATOR_INCLUDE_METADATA`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to include metadata (title, author, date, etc.) in created documents. When enabled, documents include frontmatter or header information.

**Values:**
- `true` - Include metadata (default)
- `false` - Exclude metadata

**Example:**
```bash
export DOC_CREATOR_INCLUDE_METADATA=true
```

**Metadata Format:** Metadata is included as frontmatter (YAML) in Markdown or as headers in other formats.

### 7. Generate Table of Contents

**Environment Variable:** `DOC_CREATOR_GENERATE_TOC`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to automatically generate table of contents for created documents. When enabled, the tool analyzes document structure and creates a TOC.

**Values:**
- `true` - Generate TOC automatically (default)
- `false` - Skip TOC generation

**Example:**
```bash
export DOC_CREATOR_GENERATE_TOC=true
```

**TOC Features:** Automatically detects headings and creates hierarchical table of contents.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom directories and defaults
export DOC_CREATOR_TEMPLATES_DIR="/app/templates"
export DOC_CREATOR_OUTPUT_DIR="/app/output"
export DOC_CREATOR_DEFAULT_FORMAT=html
export DOC_CREATOR_DEFAULT_STYLE=corporate

# Run your application
python app.py
```

### Example 2: Academic Configuration

```bash
# Optimized for academic documents
export DOC_CREATOR_DEFAULT_FORMAT=latex
export DOC_CREATOR_DEFAULT_STYLE=academic
export DOC_CREATOR_AUTO_BACKUP=true
export DOC_CREATOR_INCLUDE_METADATA=true
export DOC_CREATOR_GENERATE_TOC=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DOC_CREATOR_TEMPLATES_DIR="./templates"
export DOC_CREATOR_OUTPUT_DIR="./output"
export DOC_CREATOR_DEFAULT_FORMAT=markdown
export DOC_CREATOR_DEFAULT_STYLE=default
export DOC_CREATOR_AUTO_BACKUP=false
export DOC_CREATOR_INCLUDE_METADATA=false
export DOC_CREATOR_GENERATE_TOC=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool

# Initialize with custom configuration
doc_creator = DocumentCreatorTool(config={
    'templates_dir': '/app/templates',
    'output_dir': '/app/output',
    'default_format': 'html',
    'default_style': 'corporate',
    'auto_backup': True,
    'include_metadata': True,
    'generate_toc': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DOC_CREATOR_DEFAULT_FORMAT=markdown
export DOC_CREATOR_AUTO_BACKUP=true
```

```python
# Override for specific instance
doc_creator = DocumentCreatorTool(config={
    'default_format': 'html',  # This overrides the environment variable
    'auto_backup': False       # This overrides the environment variable
})
```

## Configuration Priority

When the Document Creator Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DOC_CREATOR_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DOC_CREATOR_DEFAULT_FORMAT=markdown
export DOC_CREATOR_TEMPLATES_DIR=/path/to/templates
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DOC_CREATOR_AUTO_BACKUP=true
export DOC_CREATOR_INCLUDE_METADATA=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `templates_dir` must be a non-empty string
- `output_dir` must be a non-empty string
- `default_format` must be a valid format string
- `default_style` must be a valid style string
- `auto_backup` must be a boolean
- `include_metadata` must be a boolean
- `generate_toc` must be a boolean

### Runtime Validation

When creating documents, the tool validates:

1. **Directory accessibility** - Templates and output directories must be accessible
2. **Template availability** - Requested templates must exist
3. **Format support** - Output format must be supported
4. **Style validity** - Style preset must be valid
5. **Metadata structure** - Metadata must be properly formatted

## Document Types

The Document Creator Tool supports various document types:

### Business Documents
- **Report** - Business reports and analysis
- **Proposal** - Project and business proposals
- **Letter** - Business correspondence
- **Invoice** - Billing and invoicing documents

### Academic Documents
- **Academic** - Research papers and academic content
- **Technical** - Technical documentation and specifications

### Creative Documents
- **Article** - Blog posts and articles
- **Creative** - Creative writing and content
- **Presentation** - Slides and presentations

### Reference Documents
- **Manual** - User guides and manuals
- **Custom** - Custom document types

## Supported Formats

### Text Formats
- **Markdown** - Lightweight markup language
- **HTML** - Web markup language
- **Plain Text** - Simple text format
- **LaTeX** - Document preparation system

### Document Formats
- **DOCX** - Microsoft Word format
- **PDF** - Portable Document Format

### Data Formats
- **JSON** - JavaScript Object Notation
- **XML** - Extensible Markup Language

## Template Types

### Built-in Templates
- **Blank** - Empty document template
- **Business Report** - Structured business report
- **Technical Doc** - Technical documentation
- **Academic Paper** - Academic research paper
- **Project Proposal** - Project proposal template
- **User Manual** - User guide template
- **Presentation** - Presentation slides
- **Newsletter** - Newsletter template
- **Invoice** - Invoice template
- **Custom** - Custom template

### Template Structure
Templates include:
- Document structure and sections
- Style definitions
- Metadata placeholders
- Content guidelines
- Format-specific formatting

## Style Presets

### Professional Styles
- **Default** - Standard formatting
- **Corporate** - Business styling
- **Professional** - Professional appearance
- **Academic** - Academic paper styling

### Design Styles
- **Modern** - Contemporary design
- **Classic** - Traditional formatting
- **Minimal** - Clean, minimal design
- **Colorful** - Vibrant, colorful design

### Style Features
- Typography and fonts
- Color schemes
- Layout and spacing
- Header and footer styles
- Table and list formatting

## Operations Supported

The Document Creator Tool supports comprehensive document creation operations:

### Document Creation
- `create_document` - Create new document from template
- `create_from_template` - Create document using specific template
- `create_blank_document` - Create empty document
- `create_from_scratch` - Create document without template

### Template Management
- `list_templates` - List available templates
- `get_template` - Get template details
- `add_template` - Add custom template
- `update_template` - Update existing template
- `remove_template` - Remove template

### Document Structure
- `setup_document_structure` - Initialize document sections
- `add_section` - Add new section to document
- `remove_section` - Remove section from document
- `reorder_sections` - Reorder document sections
- `generate_toc` - Generate table of contents

### Metadata Management
- `configure_metadata` - Set document metadata
- `update_metadata` - Update existing metadata
- `get_metadata` - Retrieve document metadata
- `validate_metadata` - Validate metadata structure

### Style and Formatting
- `apply_style` - Apply style preset to document
- `customize_style` - Customize document styling
- `export_document` - Export to different format
- `convert_format` - Convert between formats

### Document Management
- `save_document` - Save document to file
- `load_document` - Load document from file
- `backup_document` - Create document backup
- `restore_document` - Restore from backup
- `list_documents` - List created documents

### Batch Operations
- `batch_create` - Create multiple documents
- `batch_export` - Export multiple documents
- `batch_convert` - Convert multiple documents
- `batch_backup` - Backup multiple documents

## Troubleshooting

### Issue: Directory not accessible

**Error:** `PermissionError` when accessing directories

**Solutions:**
```bash
# Set accessible directories
export DOC_CREATOR_TEMPLATES_DIR="/accessible/templates/path"
export DOC_CREATOR_OUTPUT_DIR="/accessible/output/path"

# Or create directories with proper permissions
mkdir -p /path/to/directories
chmod 755 /path/to/directories
```

### Issue: Template not found

**Error:** `TemplateError` when template is missing

**Solutions:**
1. Check template directory path
2. Verify template file exists
3. Ensure template format is correct
4. Check template permissions

### Issue: Format conversion fails

**Error:** `DocumentCreationError` during format conversion

**Solutions:**
1. Install required format dependencies:
   ```bash
   pip install python-docx reportlab
   ```
2. Check format support
3. Verify document structure
4. Ensure proper metadata

### Issue: Style not applied

**Error:** Style preset not working correctly

**Solutions:**
1. Verify style preset name
2. Check style definition
3. Ensure format compatibility
4. Validate document structure

### Issue: Metadata validation fails

**Error:** Metadata structure is invalid

**Solutions:**
1. Check metadata format
2. Verify required fields
3. Ensure proper data types
4. Validate against schema

### Issue: TOC generation fails

**Error:** Table of contents not generated

**Solutions:**
1. Enable TOC generation: `export DOC_CREATOR_GENERATE_TOC=true`
2. Check document structure
3. Verify heading format
4. Ensure proper nesting

### Issue: Backup creation fails

**Error:** Backup operation fails

**Solutions:**
1. Check backup directory permissions
2. Ensure sufficient disk space
3. Verify file access rights
4. Check backup directory path

## Best Practices

### Template Organization

1. **Directory Structure** - Organize templates by type and purpose
2. **Naming Convention** - Use consistent naming for templates
3. **Version Control** - Track template changes
4. **Documentation** - Document template usage and variables
5. **Testing** - Test templates with various content

### Document Management

1. **Naming Convention** - Use descriptive file names
2. **Directory Organization** - Organize output by project or date
3. **Backup Strategy** - Implement regular backups
4. **Version Control** - Track document versions
5. **Access Control** - Implement proper permissions

### Style Consistency

1. **Style Guidelines** - Define style standards
2. **Template Usage** - Use appropriate templates
3. **Format Selection** - Choose suitable formats
4. **Metadata Standards** - Standardize metadata
5. **Quality Control** - Review document quality

### Performance Optimization

1. **Template Caching** - Cache frequently used templates
2. **Batch Operations** - Use batch operations for multiple documents
3. **Format Optimization** - Choose efficient formats
4. **Resource Management** - Monitor resource usage
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
DOC_CREATOR_TEMPLATES_DIR=./templates
DOC_CREATOR_OUTPUT_DIR=./output
DOC_CREATOR_DEFAULT_FORMAT=markdown
DOC_CREATOR_DEFAULT_STYLE=default
DOC_CREATOR_AUTO_BACKUP=false
DOC_CREATOR_INCLUDE_METADATA=false
DOC_CREATOR_GENERATE_TOC=false
```

**Production:**
```bash
DOC_CREATOR_TEMPLATES_DIR=/app/templates
DOC_CREATOR_OUTPUT_DIR=/app/output
DOC_CREATOR_DEFAULT_FORMAT=html
DOC_CREATOR_DEFAULT_STYLE=corporate
DOC_CREATOR_AUTO_BACKUP=true
DOC_CREATOR_INCLUDE_METADATA=true
DOC_CREATOR_GENERATE_TOC=true
```

### Error Handling

Always wrap document creation operations in try-except blocks:

```python
from aiecs.tools.docs.document_creator_tool import DocumentCreatorTool, DocumentCreatorError, TemplateError, DocumentCreationError

doc_creator = DocumentCreatorTool()

try:
    result = doc_creator.create_document(
        document_type="report",
        template_type="business_report",
        output_format="html"
    )
except TemplateError as e:
    print(f"Template error: {e}")
except DocumentCreationError as e:
    print(f"Document creation failed: {e}")
except DocumentCreatorError as e:
    print(f"Document creator error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install document processing dependencies
pip install python-docx reportlab markdown

# Install template processing dependencies
pip install jinja2 pyyaml
```

### Optional Dependencies

```bash
# For PDF generation
pip install reportlab weasyprint

# For LaTeX support
pip install pylatex

# For advanced formatting
pip install beautifulsoup4 lxml
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import jinja2
    import yaml
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test external tool availability
try:
    from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
    from aiecs.tools.docs.document_layout_tool import DocumentLayoutTool
    from aiecs.tools.docs.content_insertion_tool import ContentInsertionTool
    print("External tools available")
except ImportError as e:
    print(f"External tool not available: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- DocumentWriterTool documentation for content writing
- DocumentLayoutTool documentation for layout configuration
- ContentInsertionTool documentation for complex content
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Document Creator Tool configuration:
- Check the tool source code for implementation details
- Review external tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple documents first to isolate configuration vs. content issues
- Monitor directory permissions and disk space
- Verify template availability and format
- Check document structure and metadata
- Ensure proper style and format selection
