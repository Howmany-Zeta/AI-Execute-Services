# Data Visualizer Tool Configuration Guide

## Overview

The Data Visualizer Tool is an intelligent data visualization tool that provides smart data visualization and chart generation capabilities with auto chart type recommendation, multiple chart types support, interactive and static visualizations, and export in multiple formats. It can auto-recommend appropriate chart types, generate interactive visualizations, create multi-dimensional plots, and export in multiple formats. The tool integrates with chart_tool for core visualization operations and supports various chart types (basic charts, advanced charts, statistical charts, time series) and visualization styles (static, interactive, animated). The tool can be configured via environment variables using the `DATA_VISUALIZER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Data Visualizer Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DATA_VISUALIZER_DEFAULT_STYLE=static
DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/tmp/visualizations
DATA_VISUALIZER_DEFAULT_DPI=100
DATA_VISUALIZER_DEFAULT_FIGSIZE=[10,6]
DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.data_visualizer_tool import DataVisualizerTool

# The tool will automatically use the environment variables
data_visualizer = DataVisualizerTool()
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

from aiecs.tools.statistics.data_visualizer_tool import DataVisualizerTool
data_visualizer = DataVisualizerTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for high-quality visualizations
DATA_VISUALIZER_DEFAULT_STYLE=interactive
DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/app/visualizations
DATA_VISUALIZER_DEFAULT_DPI=300
DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
DATA_VISUALIZER_DEFAULT_STYLE=static
DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=./visualizations
DATA_VISUALIZER_DEFAULT_DPI=100
DATA_VISUALIZER_DEFAULT_FIGSIZE=[8,6]
DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=false
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
   # Data Visualizer Tool Configuration
   
   # Default visualization style
   DATA_VISUALIZER_DEFAULT_STYLE=static
   
   # Default directory for output files
   DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/tmp/visualizations
   
   # Default DPI for image exports
   DATA_VISUALIZER_DEFAULT_DPI=100
   
   # Default figure size in inches (width, height)
   DATA_VISUALIZER_DEFAULT_FIGSIZE=[10,6]
   
   # Whether to enable automatic chart type recommendation
   DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `static`, `interactive`, `animated`
   - Integers: Plain numbers: `100`, `300`
   - Lists: JSON format: `[10,6]`, `[12,8]`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Default Style

**Environment Variable:** `DATA_VISUALIZER_DEFAULT_STYLE`

**Type:** String

**Default:** `"static"`

**Description:** Default visualization style when no specific style is specified. This determines the type of visualization output generated.

**Supported Styles:**
- `static` - Static images (PNG, JPG, PDF)
- `interactive` - Interactive plots (HTML, JavaScript)
- `animated` - Animated visualizations (GIF, MP4)

**Example:**
```bash
export DATA_VISUALIZER_DEFAULT_STYLE=interactive
```

**Style Note:** Interactive styles provide better user experience but require more resources.

### 2. Default Output Directory

**Environment Variable:** `DATA_VISUALIZER_DEFAULT_OUTPUT_DIR`

**Type:** String

**Default:** `tempfile.gettempdir()`

**Description:** Default directory where visualization files are saved. This directory must be accessible and writable by the application.

**Example:**
```bash
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR="/app/visualizations"
```

**Directory Note:** Ensure the directory has appropriate permissions and is accessible.

### 3. Default DPI

**Environment Variable:** `DATA_VISUALIZER_DEFAULT_DPI`

**Type:** Integer

**Default:** `100`

**Description:** Default DPI (dots per inch) for image exports. Higher DPI values produce higher quality images but larger file sizes.

**Common Values:**
- `72` - Screen resolution (web use)
- `100` - Standard resolution (default)
- `150` - Print quality
- `300` - High print quality

**Example:**
```bash
export DATA_VISUALIZER_DEFAULT_DPI=300
```

**DPI Note:** Higher DPI values improve image quality but increase file size and processing time.

### 4. Default Figure Size

**Environment Variable:** `DATA_VISUALIZER_DEFAULT_FIGSIZE`

**Type:** List of Integers

**Default:** `[10, 6]`

**Description:** Default figure size in inches (width, height) for visualizations. This determines the dimensions of generated charts and plots.

**Common Values:**
- `[8, 6]` - Standard size (web use)
- `[10, 6]` - Default size (balanced)
- `[12, 8]` - Large size (presentations)
- `[16, 10]` - Extra large size (posters)

**Example:**
```bash
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
```

**Size Note:** Larger figures provide more detail but may be harder to display on smaller screens.

### 5. Enable Auto Recommendation

**Environment Variable:** `DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable automatic chart type recommendation. When enabled, the tool analyzes data characteristics and suggests appropriate chart types.

**Values:**
- `true` - Enable auto recommendation (default)
- `false` - Disable auto recommendation

**Example:**
```bash
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

**Recommendation Note:** Auto recommendation helps users choose appropriate visualizations but may slow down processing.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic data visualization parameters
export DATA_VISUALIZER_DEFAULT_STYLE=static
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/tmp/visualizations
export DATA_VISUALIZER_DEFAULT_DPI=100
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[10,6]
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true

# Run your application
python app.py
```

### Example 2: High-Quality Production Configuration

```bash
# Optimized for high-quality visualizations
export DATA_VISUALIZER_DEFAULT_STYLE=interactive
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/app/visualizations
export DATA_VISUALIZER_DEFAULT_DPI=300
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DATA_VISUALIZER_DEFAULT_STYLE=static
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=./visualizations
export DATA_VISUALIZER_DEFAULT_DPI=100
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[8,6]
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.data_visualizer_tool import DataVisualizerTool

# Initialize with custom configuration
data_visualizer = DataVisualizerTool(config={
    'default_style': 'static',
    'default_output_dir': '/tmp/visualizations',
    'default_dpi': 100,
    'default_figsize': [10, 6],
    'enable_auto_recommendation': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DATA_VISUALIZER_DEFAULT_STYLE=static
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

```python
# Override for specific instance
data_visualizer = DataVisualizerTool(config={
    'default_style': 'interactive',  # This overrides the environment variable
    'enable_auto_recommendation': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Data Visualizer Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DATA_VISUALIZER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DATA_VISUALIZER_DEFAULT_STYLE=static
export DATA_VISUALIZER_DEFAULT_STYLE=interactive
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/app/visualizations
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DATA_VISUALIZER_DEFAULT_DPI=100
export DATA_VISUALIZER_DEFAULT_DPI=300
```

### List Values

Lists should be provided in JSON format:

```bash
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[10,6]
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `default_style` must be a valid style string
- `default_output_dir` must be a non-empty string
- `default_dpi` must be a positive integer
- `default_figsize` must be a list of two positive integers
- `enable_auto_recommendation` must be a boolean

### Runtime Validation

When creating visualizations, the tool validates:

1. **Output directory** - Directory must be accessible and writable
2. **Figure size** - Size must be reasonable for the display medium
3. **DPI settings** - DPI must be appropriate for the output format
4. **Style compatibility** - Style must be compatible with chart type
5. **Data compatibility** - Data must be compatible with visualization operations

## Chart Types

The Data Visualizer Tool supports various chart types:

### Basic Charts
- **Line** - Line plots for trends and time series
- **Bar** - Bar charts for categorical comparisons
- **Scatter** - Scatter plots for correlation analysis
- **Histogram** - Histograms for distribution analysis
- **Box** - Box plots for statistical summaries
- **Violin** - Violin plots for distribution shapes

### Advanced Charts
- **Heatmap** - Heatmaps for correlation matrices
- **Correlation Matrix** - Correlation visualization
- **Pair Plot** - Multi-dimensional scatter plots
- **Parallel Coordinates** - Multi-dimensional data visualization

### Statistical Charts
- **Distribution** - Distribution plots
- **QQ Plot** - Quantile-quantile plots
- **Residual Plot** - Residual analysis plots

### Time Series
- **Time Series** - Time series visualization

### Auto-Detection
- **Auto** - Automatically detect appropriate chart type

## Visualization Styles

### Static Style
- **PNG** - Portable Network Graphics
- **JPG** - JPEG images
- **PDF** - Portable Document Format
- **SVG** - Scalable Vector Graphics

### Interactive Style
- **HTML** - Interactive HTML plots
- **JavaScript** - JavaScript-based visualizations
- **Plotly** - Interactive Plotly charts
- **Bokeh** - Interactive Bokeh plots

### Animated Style
- **GIF** - Animated GIF images
- **MP4** - Video format animations
- **WebM** - Web video format

## Operations Supported

The Data Visualizer Tool supports comprehensive data visualization operations:

### Basic Visualization
- `create_visualization` - Create comprehensive data visualization
- `create_chart` - Create specific chart type
- `auto_recommend_chart` - Auto-recommend appropriate chart type
- `generate_plot` - Generate plot from data
- `create_dashboard` - Create multi-panel dashboard

### Chart Type Operations
- `create_line_chart` - Create line charts
- `create_bar_chart` - Create bar charts
- `create_scatter_plot` - Create scatter plots
- `create_histogram` - Create histograms
- `create_box_plot` - Create box plots
- `create_heatmap` - Create heatmaps

### Advanced Visualization
- `create_correlation_matrix` - Create correlation matrix visualization
- `create_pair_plot` - Create pair plots
- `create_distribution_plot` - Create distribution plots
- `create_time_series_plot` - Create time series plots
- `create_multi_dimensional_plot` - Create multi-dimensional visualizations

### Export Operations
- `export_static` - Export static images
- `export_interactive` - Export interactive plots
- `export_animated` - Export animated visualizations
- `save_visualization` - Save visualization to file
- `export_multiple_formats` - Export in multiple formats

### Style Operations
- `apply_style` - Apply visualization style
- `customize_appearance` - Customize chart appearance
- `set_color_scheme` - Set color scheme
- `adjust_layout` - Adjust plot layout
- `add_annotations` - Add annotations to plots

### Analysis Operations
- `analyze_data_for_visualization` - Analyze data for visualization
- `detect_best_chart_type` - Detect best chart type for data
- `validate_visualization_compatibility` - Validate data-visualization compatibility
- `optimize_visualization_parameters` - Optimize visualization parameters
- `generate_visualization_report` - Generate visualization analysis report

## Troubleshooting

### Issue: Output directory not accessible

**Error:** Permission denied or directory not found

**Solutions:**
```bash
# Set accessible directory
export DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/accessible/path

# Create directory with proper permissions
mkdir -p /path/to/visualizations
chmod 755 /path/to/visualizations
```

### Issue: Visualization generation fails

**Error:** `VisualizationError` during chart creation

**Solutions:**
1. Check data compatibility with chart type
2. Verify output directory permissions
3. Check available disk space
4. Validate data format and structure

### Issue: Low image quality

**Error:** Poor quality visualizations

**Solutions:**
```bash
# Increase DPI
export DATA_VISUALIZER_DEFAULT_DPI=300

# Increase figure size
export DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
```

### Issue: Interactive visualizations not working

**Error:** Interactive features not functioning

**Solutions:**
```bash
# Enable interactive style
export DATA_VISUALIZER_DEFAULT_STYLE=interactive

# Check interactive dependencies
pip install plotly bokeh
```

### Issue: Auto recommendation not working

**Error:** Chart type recommendation fails

**Solutions:**
```bash
# Enable auto recommendation
export DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true

# Check data characteristics
data_visualizer.analyze_data_for_visualization(data)
```

### Issue: Memory usage exceeded

**Error:** Out of memory during visualization

**Solutions:**
1. Reduce figure size
2. Lower DPI settings
3. Process data in chunks
4. Use simpler chart types

### Issue: Slow visualization generation

**Error:** Slow chart creation

**Solutions:**
1. Disable auto recommendation
2. Use static style instead of interactive
3. Reduce figure size and DPI
4. Optimize data preprocessing

## Best Practices

### Performance Optimization

1. **Style Selection** - Choose appropriate style for use case
2. **Figure Size** - Set reasonable figure dimensions
3. **DPI Settings** - Use appropriate DPI for output medium
4. **Auto Recommendation** - Disable for better performance
5. **Caching** - Cache frequently used visualizations

### Error Handling

1. **Graceful Degradation** - Handle visualization failures gracefully
2. **Validation** - Validate data before visualization
3. **Fallback Strategies** - Provide fallback visualization methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Output Directory** - Secure output directory access
2. **File Permissions** - Set appropriate file permissions
3. **Access Control** - Control access to generated visualizations
4. **Audit Logging** - Log visualization generation activities
5. **Data Privacy** - Ensure data privacy in visualizations

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during visualization
2. **File Cleanup** - Clean up temporary visualization files
3. **Storage Optimization** - Optimize visualization file sizes
4. **Processing Time** - Set reasonable timeouts
5. **Resource Limits** - Set appropriate resource limits

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
DATA_VISUALIZER_DEFAULT_STYLE=static
DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=./visualizations
DATA_VISUALIZER_DEFAULT_DPI=100
DATA_VISUALIZER_DEFAULT_FIGSIZE=[8,6]
DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=false
```

**Production:**
```bash
DATA_VISUALIZER_DEFAULT_STYLE=interactive
DATA_VISUALIZER_DEFAULT_OUTPUT_DIR=/app/visualizations
DATA_VISUALIZER_DEFAULT_DPI=300
DATA_VISUALIZER_DEFAULT_FIGSIZE=[12,8]
DATA_VISUALIZER_ENABLE_AUTO_RECOMMENDATION=true
```

### Error Handling

Always wrap visualization operations in try-except blocks:

```python
from aiecs.tools.statistics.data_visualizer_tool import DataVisualizerTool, DataVisualizerError, VisualizationError

data_visualizer = DataVisualizerTool()

try:
    chart = data_visualizer.create_visualization(
        data=df,
        chart_type='auto',
        style='interactive'
    )
except VisualizationError as e:
    print(f"Visualization error: {e}")
except DataVisualizerError as e:
    print(f"Data visualizer error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install data processing dependencies
pip install pandas numpy

# Install visualization dependencies
pip install matplotlib seaborn plotly
```

### Optional Dependencies

```bash
# For interactive visualizations
pip install bokeh altair

# For advanced statistical plots
pip install scipy statsmodels

# For animation support
pip install imageio pillow

# For web-based visualizations
pip install dash streamlit
```

### Verification

```python
# Test dependency availability
try:
    import pandas
    import numpy
    import matplotlib
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test visualization availability
try:
    import seaborn
    import plotly
    print("Visualization libraries available")
except ImportError:
    print("Visualization libraries not available")

# Test interactive visualization availability
try:
    import bokeh
    import altair
    print("Interactive visualization available")
except ImportError:
    print("Interactive visualization not available")

# Test animation availability
try:
    import imageio
    from PIL import Image
    print("Animation support available")
except ImportError:
    print("Animation support not available")
```

## Related Documentation

- Tool implementation details in the source code
- Chart tool documentation for core visualization operations
- Statistics tool documentation for statistical analysis
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Data Visualizer Tool configuration:
- Check the tool source code for implementation details
- Review chart tool documentation for core visualization operations
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. visualization issues
- Verify data compatibility and format requirements
- Check visualization style and output settings
- Ensure proper dependencies and libraries
- Validate data structure and visualization requirements
