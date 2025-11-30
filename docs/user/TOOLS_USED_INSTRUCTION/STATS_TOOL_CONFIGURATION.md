# Stats Tool Configuration Guide

## Overview

The Stats Tool provides comprehensive statistical analysis capabilities for various data formats including SPSS (.sav, .sas7bdat, .por), CSV, Excel, JSON, Parquet, and Feather files. It supports descriptive statistics, hypothesis testing (t-tests, ANOVA), correlation analysis, regression analysis, and advanced statistical operations. The tool can be configured via environment variables using the `STATS_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Stats Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
STATS_TOOL_MAX_FILE_SIZE_MB=200
STATS_TOOL_ALLOWED_EXTENSIONS=[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.stats_tool import StatsTool

# The tool will automatically use the environment variables
stats_tool = StatsTool()
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

from aiecs.tools.task_tools.stats_tool import StatsTool
stats_tool = StatsTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for large datasets
STATS_TOOL_MAX_FILE_SIZE_MB=500
STATS_TOOL_ALLOWED_EXTENSIONS=[".sav",".sas7bdat",".csv",".xlsx",".parquet"]
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
STATS_TOOL_MAX_FILE_SIZE_MB=100
STATS_TOOL_ALLOWED_EXTENSIONS=[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]
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
   # Stats Tool Configuration
   
   # Maximum file size in megabytes
   STATS_TOOL_MAX_FILE_SIZE_MB=200
   
   # Allowed file extensions (JSON array)
   STATS_TOOL_ALLOWED_EXTENSIONS=[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Integers: Plain numbers: `200`, `500`
   - Lists: JSON array format: `[".sav",".csv",".xlsx"]`

## Configuration Options

### 1. Max File Size MB

**Environment Variable:** `STATS_TOOL_MAX_FILE_SIZE_MB`

**Type:** Integer

**Default:** `200`

**Description:** Maximum file size in megabytes for data files. This prevents memory issues with extremely large datasets and ensures reasonable processing times.

**Common Values:**
- `50` - Small datasets (development)
- `100` - Medium datasets (testing)
- `200` - Large datasets (default)
- `500` - Very large datasets (production)
- `1000` - Massive datasets (enterprise)

**Example:**
```bash
export STATS_TOOL_MAX_FILE_SIZE_MB=500
```

**Memory Note:** Larger values allow processing bigger files but use more memory. Adjust based on available system resources.

### 2. Allowed Extensions

**Environment Variable:** `STATS_TOOL_ALLOWED_EXTENSIONS`

**Type:** List[str]

**Default:** `['.sav', '.sas7bdat', '.por', '.csv', '.xlsx', '.xls', '.json', '.parquet', '.feather']`

**Description:** List of allowed file extensions for statistical analysis. This is a security feature that prevents processing of unauthorized file types.

**Format:** JSON array string with double quotes

**Supported Formats:**
- `.sav` - SPSS data files
- `.sas7bdat` - SAS data files
- `.por` - SPSS portable files
- `.csv` - Comma-separated values
- `.xlsx` - Excel 2007+ files
- `.xls` - Excel 97-2003 files
- `.json` - JSON data files
- `.parquet` - Apache Parquet files
- `.feather` - Feather format files

**Example:**
```bash
# Allow all supported formats
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]'

# Restrict to common formats only
export STATS_TOOL_ALLOWED_EXTENSIONS='[".csv",".xlsx",".json"]'

# SPSS/SAS only
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".por"]'
```

**Security Note:** Only allow extensions that your application actually needs to process.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom file size limit
export STATS_TOOL_MAX_FILE_SIZE_MB=500
export STATS_TOOL_ALLOWED_EXTENSIONS='[".csv",".xlsx",".sav"]'

# Run your application
python app.py
```

### Example 2: Production Configuration

```bash
# Production settings - optimized for large datasets
export STATS_TOOL_MAX_FILE_SIZE_MB=1000
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".csv",".xlsx",".parquet"]'
```

### Example 3: Development Configuration

```bash
# Development settings - permissive for testing
export STATS_TOOL_MAX_FILE_SIZE_MB=100
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]'
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.stats_tool import StatsTool

# Initialize with custom configuration
stats_tool = StatsTool(config={
    'max_file_size_mb': 500,
    'allowed_extensions': ['.sav', '.sas7bdat', '.csv', '.xlsx']
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export STATS_TOOL_MAX_FILE_SIZE_MB=200
export STATS_TOOL_ALLOWED_EXTENSIONS='[".csv",".xlsx"]'
```

```python
# Override for specific instance
stats_tool = StatsTool(config={
    'max_file_size_mb': 500,  # This overrides the environment variable
    'allowed_extensions': ['.sav', '.sas7bdat']  # This overrides the environment variable
})
```

## Configuration Priority

When the Stats Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `STATS_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Integer Values

Integers should be provided as numeric strings:

```bash
export STATS_TOOL_MAX_FILE_SIZE_MB=200
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".csv",".xlsx"]'

# Incorrect (will not parse)
export STATS_TOOL_ALLOWED_EXTENSIONS=".sav,.sas7bdat,.csv,.xlsx"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".csv",".xlsx"]'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `max_file_size_mb` must be a positive integer
- `allowed_extensions` must be a list of strings

### Runtime Validation

When processing data, the tool validates:

1. **File extensions** - Files must have allowed extensions
2. **File size limits** - Files must not exceed max_file_size_mb
3. **Data structure** - Input data must be valid for statistical analysis
4. **Variable existence** - Referenced variables must exist in datasets
5. **Data types** - Statistical operations validate appropriate data types

## Operations Supported

The Stats Tool supports comprehensive statistical analysis operations:

### Data Loading and Inspection
- `read_data` - Load data from various file formats
- `describe` - Generate descriptive statistics
- Support for SPSS, SAS, CSV, Excel, JSON, Parquet, and Feather formats

### Descriptive Statistics
- **Basic statistics** - Mean, median, mode, standard deviation, variance
- **Distribution measures** - Skewness, kurtosis
- **Percentiles** - Custom percentile calculations
- **Summary statistics** - Comprehensive data summaries

### Hypothesis Testing
- **t-tests** - Independent and paired t-tests
- **ANOVA** - One-way and two-way analysis of variance
- **Chi-square tests** - Goodness of fit and independence tests
- **Mann-Whitney U test** - Non-parametric alternative to t-test
- **Kruskal-Wallis test** - Non-parametric alternative to ANOVA

### Correlation Analysis
- **Pearson correlation** - Linear correlation coefficient
- **Spearman correlation** - Rank-based correlation
- **Kendall's tau** - Alternative rank correlation
- **Partial correlation** - Controlling for other variables

### Regression Analysis
- **Linear regression** - Simple and multiple linear regression
- **Logistic regression** - Binary and multinomial logistic regression
- **Polynomial regression** - Non-linear relationship modeling
- **Ridge/Lasso regression** - Regularized regression methods

### Advanced Statistical Operations
- **Factor analysis** - Dimensionality reduction
- **Cluster analysis** - K-means and hierarchical clustering
- **Principal component analysis (PCA)** - Data transformation
- **Time series analysis** - Trend and seasonal analysis
- **Survival analysis** - Time-to-event analysis

### Data Transformation
- **Scaling and normalization** - Standard, MinMax, Robust scaling
- **Missing value handling** - Imputation and deletion strategies
- **Outlier detection** - Statistical and machine learning methods
- **Data encoding** - Categorical variable encoding

## Troubleshooting

### Issue: File format not supported

**Error:** `Unsupported file format: .xyz`

**Solutions:**
1. Add extension to allowed list: `export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".csv",".xyz"]'`
2. Convert file to supported format
3. Check file extension spelling

### Issue: File too large

**Error:** `File size exceeds maximum limit`

**Solutions:**
```bash
# Increase file size limit
export STATS_TOOL_MAX_FILE_SIZE_MB=1000

# Or process file in chunks
# Use sampling for large datasets
```

### Issue: Missing dependencies

**Error:** `ModuleNotFoundError: No module named 'pyreadstat'`

**Solutions:**
```bash
# Install required dependencies
pip install pyreadstat scipy statsmodels

# For SPSS files
pip install pyreadstat

# For advanced statistics
pip install scipy statsmodels scikit-learn
```

### Issue: Memory errors

**Error:** `MemoryError` or system becomes unresponsive

**Solutions:**
```bash
# Reduce file size limit
export STATS_TOOL_MAX_FILE_SIZE_MB=100

# Process data in chunks
# Use sampling techniques
# Increase system memory
```

### Issue: Statistical computation errors

**Error:** `AnalysisError: Statistical computation failed`

**Solutions:**
1. Check data quality and missing values
2. Verify variable types and distributions
3. Ensure sufficient sample size
4. Check for outliers and extreme values
5. Validate statistical assumptions

### Issue: Variable not found

**Error:** `Variables not found in dataset: ['variable_name']`

**Solutions:**
1. Check variable names (case-sensitive)
2. Use `read_data` to inspect available variables
3. Verify column names in the dataset
4. Check for typos in variable names

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_extensions`

**Solution:**
```bash
# Use proper JSON array syntax
export STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".csv",".xlsx"]'

# NOT: [.sav,.sas7bdat,.csv,.xlsx] or .sav,.sas7bdat,.csv,.xlsx
```

### Issue: SPSS file reading errors

**Error:** `Error reading SPSS file`

**Solutions:**
1. Verify file is not corrupted
2. Check file encoding
3. Ensure pyreadstat is properly installed
4. Try converting to CSV format
5. Check file permissions

## Best Practices

### Data Quality

1. **Data validation** - Always validate data before analysis
2. **Missing value handling** - Implement appropriate strategies
3. **Outlier detection** - Identify and handle outliers appropriately
4. **Data types** - Ensure correct data types for statistical operations
5. **Sample size** - Verify adequate sample sizes for tests

### Statistical Analysis

1. **Assumption checking** - Verify statistical assumptions before tests
2. **Multiple testing** - Apply corrections for multiple comparisons
3. **Effect sizes** - Report effect sizes alongside p-values
4. **Confidence intervals** - Include confidence intervals in results
5. **Interpretation** - Provide clear interpretation of results

### Performance

1. **File size management** - Use appropriate file size limits
2. **Memory optimization** - Process large datasets in chunks
3. **Caching** - Cache results for repeated analyses
4. **Sampling** - Use sampling for exploratory analysis
5. **Parallel processing** - Use parallel processing for large datasets

### Security

1. **File validation** - Validate file types and sizes
2. **Path sanitization** - Sanitize file paths to prevent directory traversal
3. **Access control** - Implement proper file access controls
4. **Data privacy** - Handle sensitive data appropriately
5. **Audit logging** - Log statistical operations for compliance

### Development vs Production

**Development:**
```bash
STATS_TOOL_MAX_FILE_SIZE_MB=100
STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".por",".csv",".xlsx",".xls",".json",".parquet",".feather"]'
```

**Production:**
```bash
STATS_TOOL_MAX_FILE_SIZE_MB=500
STATS_TOOL_ALLOWED_EXTENSIONS='[".sav",".sas7bdat",".csv",".xlsx",".parquet"]'
```

### Error Handling

Always wrap statistical operations in try-except blocks:

```python
from aiecs.tools.task_tools.stats_tool import StatsTool, StatsToolError, FileOperationError, AnalysisError

stats_tool = StatsTool()

try:
    result = stats_tool.ttest("data.csv", "var1", "var2")
except FileOperationError as e:
    print(f"File operation failed: {e}")
except AnalysisError as e:
    print(f"Statistical analysis failed: {e}")
except StatsToolError as e:
    print(f"Stats tool error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core statistical dependencies
pip install pandas numpy scipy

# Install optional dependencies for advanced features
pip install statsmodels scikit-learn
```

### SPSS/SAS Support

```bash
# Install pyreadstat for SPSS and SAS files
pip install pyreadstat

# Verify installation
python -c "import pyreadstat; print('pyreadstat installed successfully')"
```

### Excel Support

```bash
# Install openpyxl for Excel files
pip install openpyxl

# For older Excel files
pip install xlrd
```

### Parquet/Feather Support

```bash
# Install for Parquet files
pip install pyarrow

# Install for Feather files
pip install feather-format
```

### Verification

```python
# Test dependency availability
try:
    import pandas as pd
    import numpy as np
    import scipy
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

try:
    import pyreadstat
    print("SPSS/SAS support available")
except ImportError:
    print("SPSS/SAS support not available")

try:
    import statsmodels
    print("Advanced statistics available")
except ImportError:
    print("Advanced statistics not available")
```

## Statistical Interpretation Guide

### Effect Sizes

**Cohen's d (t-tests):**
- 0.2 = Small effect
- 0.5 = Medium effect
- 0.8 = Large effect

**Cramer's V (chi-square):**
- 0.1 = Small effect
- 0.3 = Medium effect
- 0.5 = Large effect

**R² (regression):**
- 0.02 = Small effect
- 0.13 = Medium effect
- 0.26 = Large effect

### P-value Interpretation

- p < 0.001 = Highly significant
- p < 0.01 = Very significant
- p < 0.05 = Significant
- p < 0.1 = Marginally significant
- p ≥ 0.1 = Not significant

### Sample Size Guidelines

**t-tests:** Minimum 30 per group
**ANOVA:** Minimum 20 per group
**Correlation:** Minimum 30 observations
**Regression:** Minimum 10 observations per predictor

## Related Documentation

- Tool implementation details in the source code
- Pandas documentation: https://pandas.pydata.org/docs/
- SciPy documentation: https://docs.scipy.org/
- Statsmodels documentation: https://www.statsmodels.org/
- Pyreadstat documentation: https://ofajardo.github.io/pyreadstat_documentation/
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Stats Tool configuration:
- Check the tool source code for implementation details
- Review statistical method documentation for specific operations
- Consult the main aiecs documentation for architecture overview
- Test with small datasets first to isolate configuration vs. data issues
- Monitor memory usage and file size limits
- Validate statistical assumptions and data quality
- Check dependency installation and compatibility
