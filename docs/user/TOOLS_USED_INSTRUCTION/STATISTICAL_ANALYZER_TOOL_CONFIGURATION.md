# Statistical Analyzer Tool Configuration Guide

## Overview

The Statistical Analyzer Tool is an advanced statistical analysis and hypothesis testing tool that provides comprehensive statistical analysis with descriptive and inferential statistics, hypothesis testing (t-test, ANOVA, chi-square), regression analysis, time series analysis, and correlation and causality analysis. It can perform hypothesis testing, conduct regression analysis, analyze time series, and perform correlation and causal analysis. The tool integrates with stats_tool for core statistical operations and supports various analysis types (descriptive, t_test, anova, chi_square, linear_regression, logistic_regression, correlation, time_series). The tool can be configured via environment variables using the `STATISTICAL_ANALYZER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Statistical Analyzer Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.statistical_analyzer_tool import StatisticalAnalyzerTool

# The tool will automatically use the environment variables
statistical_analyzer = StatisticalAnalyzerTool()
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

from aiecs.tools.statistics.statistical_analyzer_tool import StatisticalAnalyzerTool
statistical_analyzer = StatisticalAnalyzerTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for rigorous statistical analysis
STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.01
STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.99
STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=false
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
   # Statistical Analyzer Tool Configuration
   
   # Significance level for hypothesis testing
   STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
   
   # Confidence level for statistical intervals
   STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
   
   # Whether to calculate effect sizes in analyses
   STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Floats: Decimal numbers: `0.05`, `0.95`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Significance Level

**Environment Variable:** `STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL`

**Type:** Float

**Default:** `0.05`

**Description:** Significance level (alpha) for hypothesis testing. This determines the threshold for rejecting the null hypothesis.

**Common Values:**
- `0.01` - Very strict significance (1% level)
- `0.05` - Standard significance (5% level, default)
- `0.10` - Lenient significance (10% level)
- `0.001` - Extremely strict significance (0.1% level)

**Example:**
```bash
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.01
```

**Significance Note:** Lower values are more strict and require stronger evidence to reject the null hypothesis.

### 2. Confidence Level

**Environment Variable:** `STATISTICAL_ANALYZER_CONFIDENCE_LEVEL`

**Type:** Float

**Default:** `0.95`

**Description:** Confidence level for statistical intervals and confidence intervals. This determines the probability that the true parameter lies within the calculated interval.

**Common Values:**
- `0.90` - 90% confidence level
- `0.95` - 95% confidence level (default)
- `0.99` - 99% confidence level
- `0.999` - 99.9% confidence level

**Example:**
```bash
export STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.99
```

**Confidence Note:** Higher confidence levels provide wider intervals but greater certainty.

### 3. Enable Effect Size

**Environment Variable:** `STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to calculate effect sizes in statistical analyses. Effect sizes provide information about the practical significance of results.

**Values:**
- `true` - Enable effect size calculation (default)
- `false` - Disable effect size calculation

**Example:**
```bash
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

**Effect Size Note:** Effect sizes help interpret the practical significance of statistical results.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic statistical analysis parameters
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
export STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true

# Run your application
python app.py
```

### Example 2: Rigorous Analysis Configuration

```bash
# Optimized for rigorous statistical analysis
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.01
export STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.99
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
export STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.statistical_analyzer_tool import StatisticalAnalyzerTool

# Initialize with custom configuration
statistical_analyzer = StatisticalAnalyzerTool(config={
    'significance_level': 0.05,
    'confidence_level': 0.95,
    'enable_effect_size': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

```python
# Override for specific instance
statistical_analyzer = StatisticalAnalyzerTool(config={
    'significance_level': 0.01,  # This overrides the environment variable
    'enable_effect_size': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Statistical Analyzer Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `STATISTICAL_ANALYZER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Float Values

Floats should be provided as decimal numbers:

```bash
export STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
export STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `significance_level` must be a float between 0 and 1
- `confidence_level` must be a float between 0 and 1
- `enable_effect_size` must be a boolean

### Runtime Validation

When performing statistical analyses, the tool validates:

1. **Significance level** - Level must be appropriate for the analysis type
2. **Confidence level** - Level must be reasonable for interval estimation
3. **Data compatibility** - Data must be compatible with statistical tests
4. **Sample size** - Sample size must be adequate for the analysis
5. **Assumptions** - Data must meet test assumptions

## Analysis Types

The Statistical Analyzer Tool supports various analysis types:

### Descriptive Statistics
- **Descriptive** - Basic descriptive statistics (mean, median, std, etc.)
- **Summary statistics** - Comprehensive data summaries
- **Distribution analysis** - Distribution characteristics

### Hypothesis Testing
- **T-test** - Student's t-test for means
- **ANOVA** - Analysis of variance
- **Chi-square** - Chi-square test for independence

### Regression Analysis
- **Linear Regression** - Linear regression analysis
- **Logistic Regression** - Logistic regression analysis
- **Multiple Regression** - Multiple variable regression

### Correlation Analysis
- **Correlation** - Correlation analysis
- **Partial Correlation** - Partial correlation analysis
- **Causality** - Causal analysis

### Time Series Analysis
- **Time Series** - Time series analysis
- **Trend Analysis** - Trend detection and analysis
- **Seasonality** - Seasonal pattern analysis

## Operations Supported

The Statistical Analyzer Tool supports comprehensive statistical analysis operations:

### Basic Analysis
- `analyze_data` - Perform comprehensive statistical analysis
- `descriptive_statistics` - Generate descriptive statistics
- `summary_statistics` - Create data summaries
- `distribution_analysis` - Analyze data distributions
- `correlation_analysis` - Perform correlation analysis

### Hypothesis Testing
- `t_test` - Perform t-tests
- `anova_test` - Perform ANOVA tests
- `chi_square_test` - Perform chi-square tests
- `mann_whitney_test` - Perform Mann-Whitney U tests
- `wilcoxon_test` - Perform Wilcoxon signed-rank tests

### Regression Analysis
- `linear_regression` - Perform linear regression
- `logistic_regression` - Perform logistic regression
- `multiple_regression` - Perform multiple regression
- `polynomial_regression` - Perform polynomial regression
- `ridge_regression` - Perform ridge regression

### Advanced Analysis
- `time_series_analysis` - Perform time series analysis
- `causal_analysis` - Perform causal analysis
- `effect_size_analysis` - Calculate effect sizes
- `power_analysis` - Perform statistical power analysis
- `meta_analysis` - Perform meta-analysis

### Statistical Tests
- `normality_tests` - Test for normality
- `homogeneity_tests` - Test for homogeneity of variance
- `independence_tests` - Test for independence
- `stationarity_tests` - Test for stationarity
- `cointegration_tests` - Test for cointegration

### Reporting Operations
- `generate_report` - Generate statistical analysis report
- `create_summary` - Create analysis summary
- `export_results` - Export analysis results
- `visualize_results` - Create result visualizations
- `interpret_results` - Provide result interpretations

## Troubleshooting

### Issue: Statistical test assumptions not met

**Error:** Test assumptions violated

**Solutions:**
1. Check data normality
2. Verify homogeneity of variance
3. Use non-parametric alternatives
4. Transform data if needed

### Issue: Insufficient sample size

**Error:** Sample size too small for analysis

**Solutions:**
1. Increase sample size
2. Use appropriate tests for small samples
3. Adjust significance level
4. Consider effect size requirements

### Issue: Multiple comparison problems

**Error:** Multiple testing issues

**Solutions:**
1. Apply Bonferroni correction
2. Use FDR correction
3. Adjust significance level
4. Use appropriate post-hoc tests

### Issue: Non-normal data

**Error:** Data not normally distributed

**Solutions:**
1. Use non-parametric tests
2. Transform data
3. Use robust statistical methods
4. Check for outliers

### Issue: Missing data

**Error:** Missing values in analysis

**Solutions:**
1. Handle missing data appropriately
2. Use complete case analysis
3. Apply imputation methods
4. Use maximum likelihood estimation

### Issue: Correlation vs causation

**Error:** Confusing correlation with causation

**Solutions:**
1. Use causal analysis methods
2. Control for confounding variables
3. Apply appropriate statistical techniques
4. Consider experimental design

### Issue: Effect size interpretation

**Error:** Effect size calculation or interpretation issues

**Solutions:**
```bash
# Enable effect size calculation
export STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true

# Use appropriate effect size measures
statistical_analyzer.calculate_effect_size(data, measure='cohens_d')
```

## Best Practices

### Statistical Rigor

1. **Significance Level** - Choose appropriate significance level
2. **Effect Size** - Always report effect sizes
3. **Assumptions** - Check test assumptions
4. **Multiple Testing** - Account for multiple comparisons
5. **Sample Size** - Ensure adequate sample size

### Error Handling

1. **Graceful Degradation** - Handle analysis failures gracefully
2. **Validation** - Validate data before analysis
3. **Fallback Methods** - Provide alternative analysis methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Data Privacy** - Ensure data privacy during analysis
2. **Access Control** - Control access to analysis results
3. **Audit Logging** - Log analysis activities
4. **Data Sanitization** - Sanitize sensitive data
5. **Compliance** - Ensure compliance with regulations

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during analysis
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
STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.05
STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.95
STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=false
```

**Production:**
```bash
STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL=0.01
STATISTICAL_ANALYZER_CONFIDENCE_LEVEL=0.99
STATISTICAL_ANALYZER_ENABLE_EFFECT_SIZE=true
```

### Error Handling

Always wrap statistical analysis operations in try-except blocks:

```python
from aiecs.tools.statistics.statistical_analyzer_tool import StatisticalAnalyzerTool, StatisticalAnalyzerError, AnalysisError

statistical_analyzer = StatisticalAnalyzerTool()

try:
    result = statistical_analyzer.analyze_data(
        data=df,
        analysis_type='t_test',
        significance_level=0.05
    )
except AnalysisError as e:
    print(f"Analysis error: {e}")
except StatisticalAnalyzerError as e:
    print(f"Statistical analyzer error: {e}")
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

# Install statistical analysis dependencies
pip install scipy statsmodels
```

### Optional Dependencies

```bash
# For advanced statistical analysis
pip install scikit-learn

# For time series analysis
pip install statsmodels

# For effect size calculations
pip install pingouin

# For power analysis
pip install statsmodels
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

# Test statistical libraries availability
try:
    from scipy import stats
    import statsmodels
    print("Statistical libraries available")
except ImportError:
    print("Statistical libraries not available")

# Test advanced analysis availability
try:
    import pingouin
    print("Advanced statistical analysis available")
except ImportError:
    print("Advanced statistical analysis not available")

# Test time series analysis availability
try:
    from statsmodels.tsa import seasonal
    print("Time series analysis available")
except ImportError:
    print("Time series analysis not available")
```

## Related Documentation

- Tool implementation details in the source code
- Stats tool documentation for core statistical operations
- Statistics tool documentation for statistical analysis
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Statistical Analyzer Tool configuration:
- Check the tool source code for implementation details
- Review stats tool documentation for core statistical operations
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. analysis issues
- Verify data compatibility and format requirements
- Check significance and confidence level settings
- Ensure proper statistical test assumptions
- Validate data quality and statistical requirements
