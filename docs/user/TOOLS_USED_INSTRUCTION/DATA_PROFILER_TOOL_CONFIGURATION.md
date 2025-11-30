# Data Profiler Tool Configuration Guide

## Overview

The Data Profiler Tool is a comprehensive data profiling and quality assessment tool that provides advanced data profiling capabilities with statistical summaries and distributions, data quality issue detection, pattern and anomaly identification, preprocessing recommendations, and column-level and dataset-level analysis. It can generate statistical summaries, detect data quality issues, identify patterns and anomalies, and recommend preprocessing steps. The tool integrates with stats_tool and pandas_tool for core operations and supports various profiling levels (basic, standard, comprehensive, deep) and data quality checks (missing_values, duplicates, outliers, inconsistencies, data_types, distributions, correlations). The tool can be configured via environment variables using the `DATA_PROFILER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Data Profiler Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DATA_PROFILER_DEFAULT_PROFILE_LEVEL=standard
DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
DATA_PROFILER_CORRELATION_THRESHOLD=0.7
DATA_PROFILER_MISSING_THRESHOLD=0.5
DATA_PROFILER_ENABLE_VISUALIZATIONS=true
DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=50
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.data_profiler_tool import DataProfilerTool

# The tool will automatically use the environment variables
data_profiler = DataProfilerTool()
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

from aiecs.tools.statistics.data_profiler_tool import DataProfilerTool
data_profiler = DataProfilerTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for comprehensive analysis
DATA_PROFILER_DEFAULT_PROFILE_LEVEL=comprehensive
DATA_PROFILER_OUTLIER_STD_THRESHOLD=2.5
DATA_PROFILER_CORRELATION_THRESHOLD=0.8
DATA_PROFILER_MISSING_THRESHOLD=0.3
DATA_PROFILER_ENABLE_VISUALIZATIONS=true
DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
DATA_PROFILER_DEFAULT_PROFILE_LEVEL=basic
DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
DATA_PROFILER_CORRELATION_THRESHOLD=0.7
DATA_PROFILER_MISSING_THRESHOLD=0.5
DATA_PROFILER_ENABLE_VISUALIZATIONS=false
DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=20
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
   # Data Profiler Tool Configuration
   
   # Default profiling depth level
   DATA_PROFILER_DEFAULT_PROFILE_LEVEL=standard
   
   # Standard deviation threshold for outlier detection
   DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
   
   # Correlation threshold for identifying strong relationships
   DATA_PROFILER_CORRELATION_THRESHOLD=0.7
   
   # Missing value threshold for quality assessment
   DATA_PROFILER_MISSING_THRESHOLD=0.5
   
   # Whether to enable visualization generation
   DATA_PROFILER_ENABLE_VISUALIZATIONS=true
   
   # Maximum unique values for categorical analysis
   DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=50
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `standard`, `comprehensive`, `basic`
   - Floats: Decimal numbers: `3.0`, `0.7`, `0.5`
   - Integers: Plain numbers: `50`, `100`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Default Profile Level

**Environment Variable:** `DATA_PROFILER_DEFAULT_PROFILE_LEVEL`

**Type:** String

**Default:** `"standard"`

**Description:** Default profiling depth level when no specific level is specified. This determines the comprehensiveness of the data profiling analysis.

**Supported Levels:**
- `basic` - Basic statistical summaries and simple quality checks
- `standard` - Standard profiling with quality assessment (default)
- `comprehensive` - Comprehensive analysis with detailed patterns
- `deep` - Deep analysis with advanced statistical methods

**Example:**
```bash
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=comprehensive
```

**Level Note:** Higher levels provide more detail but take longer to process.

### 2. Outlier STD Threshold

**Environment Variable:** `DATA_PROFILER_OUTLIER_STD_THRESHOLD`

**Type:** Float

**Default:** `3.0`

**Description:** Standard deviation threshold for outlier detection. Values beyond this threshold are considered outliers using the Z-score method.

**Common Values:**
- `2.0` - Strict outlier detection (more outliers detected)
- `2.5` - Moderate outlier detection
- `3.0` - Standard outlier detection (default)
- `3.5` - Lenient outlier detection (fewer outliers detected)

**Example:**
```bash
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=2.5
```

**Threshold Note:** Lower values detect more outliers, higher values are more lenient.

### 3. Correlation Threshold

**Environment Variable:** `DATA_PROFILER_CORRELATION_THRESHOLD`

**Type:** Float

**Default:** `0.7`

**Description:** Correlation threshold for identifying strong relationships between variables. Correlations above this threshold are considered significant.

**Common Values:**
- `0.5` - Moderate correlation threshold
- `0.7` - Strong correlation threshold (default)
- `0.8` - Very strong correlation threshold
- `0.9` - Extremely strong correlation threshold

**Example:**
```bash
export DATA_PROFILER_CORRELATION_THRESHOLD=0.8
```

**Correlation Note:** Higher thresholds identify only the strongest relationships.

### 4. Missing Threshold

**Environment Variable:** `DATA_PROFILER_MISSING_THRESHOLD`

**Type:** Float

**Default:** `0.5`

**Description:** Missing value threshold for quality assessment. Columns with missing values above this threshold are flagged as having quality issues.

**Common Values:**
- `0.1` - Strict missing value threshold (10% missing)
- `0.3` - Moderate missing value threshold (30% missing)
- `0.5` - Standard missing value threshold (50% missing, default)
- `0.7` - Lenient missing value threshold (70% missing)

**Example:**
```bash
export DATA_PROFILER_MISSING_THRESHOLD=0.3
```

**Missing Note:** Lower thresholds are more strict about missing values.

### 5. Enable Visualizations

**Environment Variable:** `DATA_PROFILER_ENABLE_VISUALIZATIONS`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable visualization generation during profiling. Visualizations include histograms, correlation matrices, and distribution plots.

**Values:**
- `true` - Enable visualizations (default)
- `false` - Disable visualizations

**Example:**
```bash
export DATA_PROFILER_ENABLE_VISUALIZATIONS=true
```

**Visualization Note:** Visualizations improve analysis but may slow down profiling.

### 6. Max Unique Values Categorical

**Environment Variable:** `DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL`

**Type:** Integer

**Default:** `50`

**Description:** Maximum number of unique values for categorical analysis. Columns with more unique values are treated as text rather than categorical.

**Common Values:**
- `20` - Small categorical threshold
- `50` - Standard categorical threshold (default)
- `100` - Large categorical threshold
- `200` - Very large categorical threshold

**Example:**
```bash
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100
```

**Categorical Note:** Higher values allow more categories but may impact performance.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic data profiling parameters
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=standard
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
export DATA_PROFILER_CORRELATION_THRESHOLD=0.7
export DATA_PROFILER_MISSING_THRESHOLD=0.5
export DATA_PROFILER_ENABLE_VISUALIZATIONS=true
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=50

# Run your application
python app.py
```

### Example 2: Comprehensive Analysis Configuration

```bash
# Optimized for comprehensive data analysis
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=comprehensive
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=2.5
export DATA_PROFILER_CORRELATION_THRESHOLD=0.8
export DATA_PROFILER_MISSING_THRESHOLD=0.3
export DATA_PROFILER_ENABLE_VISUALIZATIONS=true
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=basic
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
export DATA_PROFILER_CORRELATION_THRESHOLD=0.7
export DATA_PROFILER_MISSING_THRESHOLD=0.5
export DATA_PROFILER_ENABLE_VISUALIZATIONS=false
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=20
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.data_profiler_tool import DataProfilerTool

# Initialize with custom configuration
data_profiler = DataProfilerTool(config={
    'default_profile_level': 'standard',
    'outlier_std_threshold': 3.0,
    'correlation_threshold': 0.7,
    'missing_threshold': 0.5,
    'enable_visualizations': True,
    'max_unique_values_categorical': 50
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=standard
export DATA_PROFILER_ENABLE_VISUALIZATIONS=true
```

```python
# Override for specific instance
data_profiler = DataProfilerTool(config={
    'default_profile_level': 'comprehensive',  # This overrides the environment variable
    'enable_visualizations': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Data Profiler Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DATA_PROFILER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=standard
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=comprehensive
```

### Float Values

Floats should be provided as decimal numbers:

```bash
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
export DATA_PROFILER_CORRELATION_THRESHOLD=0.7
export DATA_PROFILER_MISSING_THRESHOLD=0.5
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=50
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DATA_PROFILER_ENABLE_VISUALIZATIONS=true
export DATA_PROFILER_ENABLE_VISUALIZATIONS=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `default_profile_level` must be a valid profile level string
- `outlier_std_threshold` must be a positive float
- `correlation_threshold` must be a float between 0 and 1
- `missing_threshold` must be a float between 0 and 1
- `enable_visualizations` must be a boolean
- `max_unique_values_categorical` must be a positive integer

### Runtime Validation

When profiling data, the tool validates:

1. **Profile level** - Level must be supported and appropriate for data size
2. **Threshold values** - Thresholds must be reasonable for the analysis
3. **Data compatibility** - Data must be compatible with profiling operations
4. **Memory requirements** - Profiling must not exceed memory limits
5. **Processing time** - Profiling must complete within reasonable time

## Profile Levels

The Data Profiler Tool supports various profiling levels:

### Basic Level
- Basic statistical summaries (mean, median, std, etc.)
- Simple quality checks (missing values, duplicates)
- Fast processing for large datasets
- Minimal resource usage

### Standard Level
- Standard statistical analysis
- Quality assessment with thresholds
- Pattern identification
- Balanced performance and detail

### Comprehensive Level
- Detailed statistical analysis
- Advanced quality checks
- Pattern and anomaly detection
- Correlation analysis
- Preprocessing recommendations

### Deep Level
- Advanced statistical methods
- Machine learning-based analysis
- Complex pattern recognition
- Detailed anomaly detection
- Comprehensive preprocessing recommendations

## Data Quality Checks

### Missing Values
- Count and percentage of missing values
- Missing value patterns
- Impact assessment
- Imputation recommendations

### Duplicates
- Duplicate row detection
- Duplicate column identification
- Deduplication strategies
- Impact analysis

### Outliers
- Statistical outlier detection
- Domain-specific outlier identification
- Outlier impact assessment
- Treatment recommendations

### Inconsistencies
- Data type inconsistencies
- Format inconsistencies
- Value inconsistencies
- Cross-field validation

### Data Types
- Automatic type inference
- Type validation
- Type conversion recommendations
- Type optimization

### Distributions
- Distribution analysis
- Normality testing
- Skewness and kurtosis
- Transformation recommendations

### Correlations
- Correlation matrix generation
- Strong relationship identification
- Multicollinearity detection
- Feature selection recommendations

## Operations Supported

The Data Profiler Tool supports comprehensive data profiling operations:

### Basic Profiling
- `profile_data` - Generate comprehensive data profile
- `profile_column` - Profile individual columns
- `profile_dataset` - Profile entire dataset
- `generate_summary` - Generate statistical summary
- `detect_quality_issues` - Detect data quality problems

### Advanced Profiling
- `analyze_distributions` - Analyze data distributions
- `detect_outliers` - Detect statistical outliers
- `analyze_correlations` - Analyze variable correlations
- `identify_patterns` - Identify data patterns
- `assess_data_quality` - Comprehensive quality assessment

### Quality Operations
- `validate_data_types` - Validate data type consistency
- `check_missing_values` - Check missing value patterns
- `detect_duplicates` - Detect duplicate records
- `analyze_inconsistencies` - Analyze data inconsistencies
- `generate_quality_report` - Generate quality assessment report

### Visualization Operations
- `create_histograms` - Create distribution histograms
- `create_correlation_matrix` - Create correlation heatmap
- `create_box_plots` - Create outlier box plots
- `create_missing_heatmap` - Create missing value heatmap
- `create_summary_plots` - Create summary visualizations

### Recommendation Operations
- `recommend_preprocessing` - Recommend preprocessing steps
- `suggest_transformations` - Suggest data transformations
- `recommend_cleaning` - Recommend data cleaning steps
- `suggest_feature_engineering` - Suggest feature engineering
- `generate_action_plan` - Generate data improvement plan

## Troubleshooting

### Issue: Profiling takes too long

**Error:** Profiling operation times out or is very slow

**Solutions:**
```bash
# Use basic profile level
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=basic

# Disable visualizations
export DATA_PROFILER_ENABLE_VISUALIZATIONS=false

# Reduce categorical threshold
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=20
```

### Issue: Memory usage exceeded

**Error:** Out of memory during profiling

**Solutions:**
```bash
# Use basic profile level
export DATA_PROFILER_DEFAULT_PROFILE_LEVEL=basic

# Disable visualizations
export DATA_PROFILER_ENABLE_VISUALIZATIONS=false

# Process data in chunks
data_profiler.profile_data(data, chunk_size=10000)
```

### Issue: Too many outliers detected

**Error:** Excessive outlier detection

**Solutions:**
```bash
# Increase outlier threshold
export DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.5

# Or use domain-specific outlier detection
data_profiler.detect_outliers(data, method='domain_specific')
```

### Issue: Missing correlation detection

**Error:** No correlations detected

**Solutions:**
```bash
# Lower correlation threshold
export DATA_PROFILER_CORRELATION_THRESHOLD=0.5

# Check data types and distributions
data_profiler.analyze_distributions(data)
```

### Issue: Categorical analysis issues

**Error:** Categorical analysis problems

**Solutions:**
```bash
# Increase categorical threshold
export DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100

# Or specify categorical columns explicitly
data_profiler.profile_data(data, categorical_columns=['col1', 'col2'])
```

### Issue: Visualization generation fails

**Error:** Visualization creation errors

**Solutions:**
```bash
# Disable visualizations
export DATA_PROFILER_ENABLE_VISUALIZATIONS=false

# Check visualization dependencies
pip install matplotlib seaborn plotly
```

### Issue: Quality assessment too strict

**Error:** Too many quality issues detected

**Solutions:**
```bash
# Increase missing threshold
export DATA_PROFILER_MISSING_THRESHOLD=0.7

# Adjust quality criteria
data_profiler.assess_data_quality(data, strict_mode=False)
```

## Best Practices

### Performance Optimization

1. **Profile Level Selection** - Choose appropriate profile level for your needs
2. **Visualization Control** - Disable visualizations for large datasets
3. **Categorical Threshold** - Set appropriate categorical threshold
4. **Chunk Processing** - Process large datasets in chunks
5. **Memory Management** - Monitor memory usage during profiling

### Error Handling

1. **Graceful Degradation** - Handle profiling failures gracefully
2. **Validation** - Validate data before profiling
3. **Fallback Strategies** - Provide fallback profiling methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Data Privacy** - Ensure data privacy during profiling
2. **Access Control** - Control access to profiling results
3. **Audit Logging** - Log profiling activities
4. **Data Sanitization** - Sanitize sensitive data
5. **Compliance** - Ensure compliance with data regulations

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during profiling
2. **Processing Time** - Set reasonable timeouts
3. **Storage Optimization** - Optimize result storage
4. **Cleanup** - Clean up temporary files
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
DATA_PROFILER_DEFAULT_PROFILE_LEVEL=basic
DATA_PROFILER_OUTLIER_STD_THRESHOLD=3.0
DATA_PROFILER_CORRELATION_THRESHOLD=0.7
DATA_PROFILER_MISSING_THRESHOLD=0.5
DATA_PROFILER_ENABLE_VISUALIZATIONS=false
DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=20
```

**Production:**
```bash
DATA_PROFILER_DEFAULT_PROFILE_LEVEL=comprehensive
DATA_PROFILER_OUTLIER_STD_THRESHOLD=2.5
DATA_PROFILER_CORRELATION_THRESHOLD=0.8
DATA_PROFILER_MISSING_THRESHOLD=0.3
DATA_PROFILER_ENABLE_VISUALIZATIONS=true
DATA_PROFILER_MAX_UNIQUE_VALUES_CATEGORICAL=100
```

### Error Handling

Always wrap profiling operations in try-except blocks:

```python
from aiecs.tools.statistics.data_profiler_tool import DataProfilerTool, DataProfilerError, ProfilingError

data_profiler = DataProfilerTool()

try:
    profile = data_profiler.profile_data(
        data=df,
        profile_level='standard',
        enable_visualizations=True
    )
except ProfilingError as e:
    print(f"Profiling error: {e}")
except DataProfilerError as e:
    print(f"Data profiler error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install data processing dependencies
pip install pandas numpy scipy

# Install visualization dependencies
pip install matplotlib seaborn plotly
```

### Optional Dependencies

```bash
# For advanced statistical analysis
pip install scikit-learn statsmodels

# For enhanced visualization
pip install bokeh altair

# For data quality assessment
pip install great-expectations

# For advanced profiling
pip install pandas-profiling ydata-profiling
```

### Verification

```python
# Test dependency availability
try:
    import pandas
    import numpy
    import scipy
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test visualization availability
try:
    import matplotlib
    import seaborn
    print("Visualization available")
except ImportError:
    print("Visualization not available")

# Test advanced analysis availability
try:
    import sklearn
    import statsmodels
    print("Advanced analysis available")
except ImportError:
    print("Advanced analysis not available")

# Test profiling libraries availability
try:
    import ydata_profiling
    print("Advanced profiling available")
except ImportError:
    print("Advanced profiling not available")
```

## Related Documentation

- Tool implementation details in the source code
- Statistics tool documentation for statistical analysis
- Pandas tool documentation for data operations
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Data Profiler Tool configuration:
- Check the tool source code for implementation details
- Review statistics tool documentation for statistical analysis
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. profiling issues
- Verify data compatibility and format requirements
- Check profile level and threshold settings
- Ensure proper visualization dependencies
- Validate data quality and structure requirements
