# Chart Tool Configuration Guide

## Overview

The Chart Tool provides data visualization and export capabilities. It can be configured via environment variables using the `CHART_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Chart Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
CHART_TOOL_EXPORT_DIR=/data/exports
CHART_TOOL_PLOT_DPI=150
CHART_TOOL_PLOT_FIGSIZE=(12,8)
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.chart_tool import ChartTool

# The tool will automatically use the environment variables
chart_tool = ChartTool()
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

from aiecs.tools.task_tools.chart_tool import ChartTool
chart_tool = ChartTool()
```

### Best Practices for .env Files

1. **Never commit .env files to version control** - Add `.env` to your `.gitignore`:
   ```gitignore
   # .gitignore
   .env
   .env.local
   .env.*.local
   ```

2. **Provide a template** - Create `.env.example` with dummy values:
   ```bash
   # .env.example
   CHART_TOOL_EXPORT_DIR=/path/to/exports
   CHART_TOOL_PLOT_DPI=100
   CHART_TOOL_PLOT_FIGSIZE=(10,6)
   ```

3. **Document your variables** - Add comments in your `.env.example` file

4. **Use load_dotenv() early** - Call it before importing any aiecs tools

## Configuration Options

### 1. Export Directory

**Environment Variable:** `CHART_TOOL_EXPORT_DIR`

**Type:** String (path)

**Default:** `{temp_directory}/chart_exports`

**Description:** Directory where exported files and plots will be saved. If the directory doesn't exist, it will be created automatically.

**Example:**
```bash
export CHART_TOOL_EXPORT_DIR="/var/app/exports"
```

### 2. Plot DPI

**Environment Variable:** `CHART_TOOL_PLOT_DPI`

**Type:** Integer

**Default:** `100`

**Description:** DPI (dots per inch) resolution for exported plot images. Higher values produce higher quality images but larger file sizes.

**Common Values:**
- `72` - Screen resolution (low quality)
- `100` - Default (good balance)
- `150` - High quality
- `300` - Print quality

**Example:**
```bash
export CHART_TOOL_PLOT_DPI=150
```

### 3. Plot Figure Size

**Environment Variable:** `CHART_TOOL_PLOT_FIGSIZE`

**Type:** Tuple[int, int]

**Default:** `(10, 6)`

**Description:** Default figure size in inches (width, height) for plots. This affects the aspect ratio and overall size of generated visualizations.

**Format:** Pydantic will parse tuples from strings in the format `(width,height)`

**Example:**
```bash
export CHART_TOOL_PLOT_FIGSIZE="(12,8)"
```

### 4. Allowed Extensions

**Environment Variable:** `CHART_TOOL_ALLOWED_EXTENSIONS`

**Type:** List[str]

**Default:** `['.csv', '.xlsx', '.xls', '.json', '.parquet', '.feather', '.sav', '.sas7bdat', '.por']`

**Description:** List of file extensions that are allowed to be read by the tool. This is a security feature to prevent reading unauthorized file types.

**Format:** JSON array string

**Example:**
```bash
export CHART_TOOL_ALLOWED_EXTENSIONS='[".csv",".xlsx",".json"]'
```

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom export directory and high-quality DPI
export CHART_TOOL_EXPORT_DIR="/data/visualizations"
export CHART_TOOL_PLOT_DPI=300

# Run your application
python app.py
```

### Example 2: Programmatic Configuration

```python
from aiecs.tools.task_tools.chart_tool import ChartTool

# Initialize with custom configuration
chart_tool = ChartTool(config={
    'export_dir': '/custom/exports',
    'plot_dpi': 150,
    'plot_figsize': (12, 8),
    'allowed_extensions': ['.csv', '.xlsx', '.json']
})
```

### Example 3: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export CHART_TOOL_PLOT_DPI=100
```

```python
# Override for specific instance
chart_tool = ChartTool(config={
    'plot_dpi': 300  # This overrides the environment variable
})
```

## Configuration Priority

When the Chart Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `CHART_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Validation

### Type Validation

Pydantic automatically validates the types of configuration values:

- `export_dir` must be a valid string path
- `plot_dpi` must be a positive integer
- `plot_figsize` must be a tuple of two positive integers
- `allowed_extensions` must be a list of strings

### Runtime Validation

- The `export_dir` will be created if it doesn't exist
- File operations will verify that file extensions are in `allowed_extensions`

## Best Practices

1. **Security**: Limit `allowed_extensions` to only the file types you need
2. **Performance**: Use lower DPI values (100-150) for web displays, higher values (300) only for print
3. **Storage**: Monitor the `export_dir` size and implement cleanup policies for old files
4. **Figure Size**: Adjust `plot_figsize` based on your display requirements:
   - Smaller figures (8, 6) for dashboards
   - Larger figures (12, 8) or (16, 10) for reports

## Troubleshooting

### Issue: Exports not found

**Cause:** Custom `export_dir` doesn't exist or lacks write permissions

**Solution:**
```bash
# Ensure directory exists and is writable
mkdir -p /path/to/exports
chmod 755 /path/to/exports
export CHART_TOOL_EXPORT_DIR="/path/to/exports"
```

### Issue: Environment variable not recognized

**Cause:** Variable set after application started or incorrect format

**Solution:**
- Set variables before running the application
- Check variable name has correct prefix: `CHART_TOOL_`
- Verify format for complex types (tuples, lists)

### Issue: Invalid figure size

**Cause:** Incorrect tuple format in environment variable

**Solution:**
```bash
# Correct format with parentheses and no spaces
export CHART_TOOL_PLOT_FIGSIZE="(10,6)"

# NOT: "10,6" or "(10, 6)" with spaces
```

## Related Tools

- **Statistics Tool**: For statistical analysis of data
- **Document Parser Tool**: For extracting data from documents before visualization

## Support

For issues or questions about Chart Tool configuration, refer to:
- Main documentation in `IMPLEMENTATION_SUMMARY.md`
- Tool-specific instructions in `TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md`

