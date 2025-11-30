# AI Report Orchestrator Tool Configuration Guide

## Overview

The AI Report Orchestrator Tool is a powerful tool that provides advanced report generation with automated analysis report creation, multiple report types and formats, integration with analysis results, visualization embedding, and export to multiple formats. It can generate comprehensive analysis reports, customize report structure and style, include visualizations and tables, export to multiple formats, and integrate analysis results and insights. The tool integrates with report_tool for document generation and supports various report types (executive_summary, technical_report, business_report, research_paper, data_quality_report) and formats (markdown, html, pdf, word, json). The tool can be configured via environment variables using the `AI_REPORT_ORCHESTRATOR_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The AI Report Orchestrator Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/tmp/reports
AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=20
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.ai_report_orchestrator_tool import AIReportOrchestratorTool

# The tool will automatically use the environment variables
report_tool = AIReportOrchestratorTool()
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

from aiecs.tools.statistics.ai_report_orchestrator_tool import AIReportOrchestratorTool
report_tool = AIReportOrchestratorTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for professional reports
AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=pdf
AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/app/reports
AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=technical_report
AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=./reports
AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=false
AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=10
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
   # AI Report Orchestrator Tool Configuration
   
   # Default report type to generate
   AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
   
   # Default report output format
   AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
   
   # Directory for report output files
   AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/tmp/reports
   
   # Whether to include code snippets in reports
   AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
   
   # Whether to include visualizations in reports
   AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
   
   # Maximum number of insights to include per report
   AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=20
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `business_report`, `markdown`, `/tmp/reports`
   - Integers: Plain numbers: `20`, `30`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Default Report Type

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE`

**Type:** String

**Default:** `"business_report"`

**Description:** Default report type to generate when no specific type is specified. This determines the structure, style, and content focus of the generated reports.

**Supported Types:**
- `executive_summary` - Executive summary reports
- `technical_report` - Technical analysis reports
- `business_report` - Business-focused reports (default)
- `research_paper` - Academic research papers
- `data_quality_report` - Data quality assessment reports

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=technical_report
```

**Type Note:** Choose the type that best fits your typical reporting needs.

### 2. Default Format

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT`

**Type:** String

**Default:** `"markdown"`

**Description:** Default report output format when no specific format is specified. This determines how the report is structured and exported.

**Supported Formats:**
- `markdown` - Markdown format (default, lightweight)
- `html` - HTML format (web-friendly)
- `pdf` - PDF format (professional documents)
- `word` - Microsoft Word format
- `json` - JSON format (structured data)

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=pdf
```

**Format Note:** Choose the format based on your distribution and presentation needs.

### 3. Output Directory

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY`

**Type:** String

**Default:** `tempfile.gettempdir()`

**Description:** Directory where generated reports are saved. This directory must be accessible and writable by the application.

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY="/app/reports"
```

**Directory Note:** Ensure the directory has appropriate permissions and is accessible.

### 4. Include Code

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_INCLUDE_CODE`

**Type:** Boolean

**Default:** `False`

**Description:** Whether to include code snippets and technical implementation details in reports. Useful for technical reports but may not be appropriate for business reports.

**Values:**
- `true` - Include code snippets
- `false` - Exclude code snippets (default)

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
```

**Code Note:** Enable for technical reports, disable for business-focused reports.

### 5. Include Visualizations

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to include charts, graphs, and other visualizations in reports. Visualizations enhance report readability but may increase file size.

**Values:**
- `true` - Include visualizations (default)
- `false` - Exclude visualizations

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
```

**Visualization Note:** Visualizations improve report quality but may impact performance and file size.

### 6. Max Insights Per Report

**Environment Variable:** `AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT`

**Type:** Integer

**Default:** `20`

**Description:** Maximum number of insights to include in each report. This helps control report length and focus on the most important findings.

**Common Values:**
- `10` - Concise reports (key insights only)
- `20` - Standard reports (default, balanced)
- `30` - Comprehensive reports (detailed insights)
- `50` - Extensive reports (maximum detail)

**Example:**
```bash
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

**Insights Note:** Higher values provide more detail but may make reports less focused.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic report generation parameters
export AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/tmp/reports
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=20

# Run your application
python app.py
```

### Example 2: Professional Configuration

```bash
# Optimized for professional business reports
export AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=pdf
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/app/reports
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=technical_report
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=./reports
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=false
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=10
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.ai_report_orchestrator_tool import AIReportOrchestratorTool

# Initialize with custom configuration
report_tool = AIReportOrchestratorTool(config={
    'default_report_type': 'business_report',
    'default_format': 'markdown',
    'output_directory': '/app/reports',
    'include_code': False,
    'include_visualizations': True,
    'max_insights_per_report': 20
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=20
```

```python
# Override for specific instance
report_tool = AIReportOrchestratorTool(config={
    'default_format': 'pdf',  # This overrides the environment variable
    'max_insights_per_report': 30  # This overrides the environment variable
})
```

## Configuration Priority

When the AI Report Orchestrator Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `AI_REPORT_ORCHESTRATOR_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
export AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/app/reports
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=20
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `default_report_type` must be a valid report type string
- `default_format` must be a valid format string
- `output_directory` must be a non-empty string
- `include_code` must be a boolean
- `include_visualizations` must be a boolean
- `max_insights_per_report` must be a positive integer

### Runtime Validation

When generating reports, the tool validates:

1. **Output directory** - Directory must be accessible and writable
2. **Report type** - Type must be supported
3. **Format compatibility** - Format must be compatible with report type
4. **Insight limits** - Number of insights must not exceed maximum
5. **File permissions** - Output directory must have write permissions

## Report Types

The AI Report Orchestrator Tool supports various report types:

### Business Reports
- **Executive Summary** - High-level executive summaries
- **Business Report** - Business-focused analysis reports
- **Data Quality Report** - Data quality assessment reports

### Technical Reports
- **Technical Report** - Technical analysis and implementation reports
- **Research Paper** - Academic-style research papers

## Report Formats

### Document Formats
- **Markdown** - Lightweight, readable format
- **HTML** - Web-friendly format with styling
- **PDF** - Professional document format
- **Word** - Microsoft Word format

### Data Formats
- **JSON** - Structured data format for programmatic use

## Operations Supported

The AI Report Orchestrator Tool supports comprehensive report generation operations:

### Basic Report Generation
- `generate_report` - Generate comprehensive analysis reports
- `generate_executive_summary` - Generate executive summary reports
- `generate_technical_report` - Generate technical analysis reports
- `generate_business_report` - Generate business-focused reports
- `generate_research_paper` - Generate academic research papers

### Advanced Report Operations
- `customize_report_structure` - Customize report structure and layout
- `embed_visualizations` - Embed charts and graphs in reports
- `include_code_snippets` - Include code snippets in reports
- `export_multiple_formats` - Export reports in multiple formats
- `batch_generate_reports` - Generate multiple reports in batch

### Report Management
- `save_report` - Save reports to specified location
- `load_report_template` - Load custom report templates
- `validate_report_content` - Validate report content and structure
- `optimize_report_size` - Optimize report file size
- `archive_reports` - Archive old reports

### Integration Operations
- `integrate_analysis_results` - Integrate analysis results into reports
- `embed_insights` - Embed insights and findings in reports
- `include_metadata` - Include analysis metadata in reports
- `link_visualizations` - Link visualizations to report content

## Troubleshooting

### Issue: Output directory not accessible

**Error:** Permission denied or directory not found

**Solutions:**
```bash
# Set accessible directory
export AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/accessible/path

# Create directory with proper permissions
mkdir -p /path/to/reports
chmod 755 /path/to/reports
```

### Issue: Report generation fails

**Error:** `ReportGenerationError` during report creation

**Solutions:**
1. Check output directory permissions
2. Verify report type and format compatibility
3. Check available disk space
4. Validate input data and analysis results

### Issue: Visualizations not included

**Error:** Visualizations missing from reports

**Solutions:**
```bash
# Enable visualizations
export AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true

# Check visualization generation
# Verify chart and graph creation
```

### Issue: Reports too long or too short

**Error:** Report length not appropriate

**Solutions:**
```bash
# Adjust insights limit
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=15

# Or increase for more detail
export AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

### Issue: Format conversion fails

**Error:** Report format conversion errors

**Solutions:**
1. Check format compatibility
2. Verify required dependencies
3. Check file permissions
4. Validate report content

### Issue: Code inclusion problems

**Error:** Code snippets not properly formatted

**Solutions:**
```bash
# Disable code inclusion for business reports
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false

# Or enable for technical reports
export AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
```

### Issue: Performance issues

**Error:** Slow report generation

**Solutions:**
1. Reduce max insights per report
2. Disable visualizations if not needed
3. Use simpler report formats
4. Check system resources

## Best Practices

### Performance Optimization

1. **Insight Management** - Set appropriate max insights per report
2. **Format Selection** - Choose formats based on use case
3. **Visualization Control** - Enable visualizations only when needed
4. **Directory Management** - Use efficient output directories
5. **Resource Monitoring** - Monitor disk space and memory usage

### Error Handling

1. **Graceful Degradation** - Handle report generation failures gracefully
2. **Validation** - Validate inputs before report generation
3. **Fallback Strategies** - Provide fallback report formats
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Directory Permissions** - Secure output directory access
2. **Content Validation** - Validate report content before saving
3. **Access Control** - Control access to generated reports
4. **Audit Logging** - Log report generation activities
5. **Data Privacy** - Ensure data privacy in reports

### Resource Management

1. **Disk Space** - Monitor disk space usage
2. **File Cleanup** - Clean up temporary files
3. **Memory Usage** - Monitor memory consumption
4. **Processing Time** - Set reasonable timeouts
5. **Storage Optimization** - Optimize report file sizes

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=technical_report
AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=markdown
AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=./reports
AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=true
AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=false
AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=10
```

**Production:**
```bash
AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE=business_report
AI_REPORT_ORCHESTRATOR_DEFAULT_FORMAT=pdf
AI_REPORT_ORCHESTRATOR_OUTPUT_DIRECTORY=/app/reports
AI_REPORT_ORCHESTRATOR_INCLUDE_CODE=false
AI_REPORT_ORCHESTRATOR_INCLUDE_VISUALIZATIONS=true
AI_REPORT_ORCHESTRATOR_MAX_INSIGHTS_PER_REPORT=30
```

### Error Handling

Always wrap report generation operations in try-except blocks:

```python
from aiecs.tools.statistics.ai_report_orchestrator_tool import AIReportOrchestratorTool, ReportOrchestratorError, ReportGenerationError

report_tool = AIReportOrchestratorTool()

try:
    report = report_tool.generate_report(
        analysis_results=results,
        report_type="business_report",
        format="pdf"
    )
except ReportGenerationError as e:
    print(f"Report generation error: {e}")
except ReportOrchestratorError as e:
    print(f"Report orchestrator error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install report generation dependencies
pip install markdown jinja2 weasyprint python-docx

# Install visualization dependencies
pip install matplotlib seaborn plotly
```

### Optional Dependencies

```bash
# For advanced report formats
pip install reportlab fpdf2

# For HTML to PDF conversion
pip install wkhtmltopdf

# For advanced visualization
pip install bokeh altair

# For template processing
pip install mako cheetah3
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import markdown
    import jinja2
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test report generation availability
try:
    import weasyprint
    print("PDF generation available")
except ImportError:
    print("PDF generation not available")

try:
    import docx
    print("Word generation available")
except ImportError:
    print("Word generation not available")

# Test visualization availability
try:
    import matplotlib
    import seaborn
    print("Visualization available")
except ImportError:
    print("Visualization not available")
```

## Related Documentation

- Tool implementation details in the source code
- Report tool documentation for document generation
- Visualization tools documentation for charts and graphs
- Main aiecs documentation for architecture overview

## Support

For issues or questions about AI Report Orchestrator Tool configuration:
- Check the tool source code for implementation details
- Review report tool documentation for document generation
- Consult the main aiecs documentation for architecture overview
- Test with simple reports first to isolate configuration vs. generation issues
- Verify output directory permissions and accessibility
- Check report type and format compatibility
- Ensure proper insight limits and visualization settings
- Validate report content and structure requirements
