# AI Insight Generator Tool Configuration Guide

## Overview

The AI Insight Generator Tool is a powerful tool that provides advanced insight generation with pattern discovery and anomaly detection, trend analysis and forecasting, actionable insight generation, and integration with research_tool reasoning methods. It can discover hidden patterns in data, generate actionable insights, detect anomalies and outliers, predict trends and forecast, and apply reasoning methods (Mill's methods, induction, deduction). The tool integrates with research_tool for reasoning capabilities and supports various insight types including pattern, anomaly, trend, correlation, segmentation, and causation analysis. The tool can be configured via environment variables using the `AI_INSIGHT_GENERATOR_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The AI Insight Generator Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.7
AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.0
AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.5
AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.ai_insight_generator_tool import AIInsightGeneratorTool

# The tool will automatically use the environment variables
insight_tool = AIInsightGeneratorTool()
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

from aiecs.tools.statistics.ai_insight_generator_tool import AIInsightGeneratorTool
insight_tool = AIInsightGeneratorTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for accuracy and reliability
AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.8
AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=2.5
AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.6
AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.5
AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.5
AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.3
AI_INSIGHT_GENERATOR_ENABLE_REASONING=false
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
   # AI Insight Generator Tool Configuration
   
   # Minimum confidence threshold for insights
   AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.7
   
   # Standard deviation threshold for anomaly detection
   AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.0
   
   # Correlation threshold for significant relationships
   AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.5
   
   # Whether to enable reasoning methods integration
   AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Floats: Decimal numbers: `0.7`, `3.0`, `0.5`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Min Confidence

**Environment Variable:** `AI_INSIGHT_GENERATOR_MIN_CONFIDENCE`

**Type:** Float

**Default:** `0.7`

**Description:** Minimum confidence threshold for insights. Only insights with confidence scores above this threshold will be considered valid and actionable.

**Common Values:**
- `0.5` - Low confidence (more insights, lower quality)
- `0.7` - Standard confidence (default, balanced)
- `0.8` - High confidence (fewer insights, higher quality)
- `0.9` - Very high confidence (very selective)

**Example:**
```bash
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.8
```

**Confidence Note:** Higher values provide more reliable insights but may miss some valid patterns.

### 2. Anomaly Std Threshold

**Environment Variable:** `AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD`

**Type:** Float

**Default:** `3.0`

**Description:** Standard deviation threshold for anomaly detection. Data points that are more than this many standard deviations from the mean are considered anomalies.

**Common Values:**
- `2.0` - Sensitive (detects more anomalies)
- `2.5` - Moderate sensitivity
- `3.0` - Standard threshold (default)
- `3.5` - Less sensitive (fewer false positives)

**Example:**
```bash
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=2.5
```

**Threshold Note:** Lower values detect more anomalies but may include false positives.

### 3. Correlation Threshold

**Environment Variable:** `AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD`

**Type:** Float

**Default:** `0.5`

**Description:** Correlation threshold for significant relationships. Only correlations with absolute values above this threshold are considered significant.

**Common Values:**
- `0.3` - Weak correlation (more relationships)
- `0.5` - Moderate correlation (default)
- `0.7` - Strong correlation (fewer relationships)
- `0.8` - Very strong correlation (very selective)

**Example:**
```bash
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.6
```

**Correlation Note:** Higher values focus on stronger relationships but may miss weaker but meaningful patterns.

### 4. Enable Reasoning

**Environment Variable:** `AI_INSIGHT_GENERATOR_ENABLE_REASONING`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable reasoning methods integration. When enabled, the tool integrates with research_tool to apply Mill's methods, induction, and deduction for deeper insight analysis.

**Values:**
- `true` - Enable reasoning methods (default)
- `false` - Disable reasoning methods

**Example:**
```bash
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
```

**Reasoning Note:** Enabling reasoning provides deeper analysis but requires research_tool availability.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic insight generation parameters
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.7
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.0
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.5
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=true

# Run your application
python app.py
```

### Example 2: High-Accuracy Configuration

```bash
# Optimized for high accuracy and reliability
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.8
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=2.5
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.6
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.5
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.5
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.3
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.ai_insight_generator_tool import AIInsightGeneratorTool

# Initialize with custom configuration
insight_tool = AIInsightGeneratorTool(config={
    'min_confidence': 0.7,
    'anomaly_std_threshold': 3.0,
    'correlation_threshold': 0.5,
    'enable_reasoning': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.7
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.5
```

```python
# Override for specific instance
insight_tool = AIInsightGeneratorTool(config={
    'min_confidence': 0.8,  # This overrides the environment variable
    'correlation_threshold': 0.6  # This overrides the environment variable
})
```

## Configuration Priority

When the AI Insight Generator Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `AI_INSIGHT_GENERATOR_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Float Values

Floats should be provided as decimal strings:

```bash
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.7
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.0
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.5
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `min_confidence` must be a float between 0.0 and 1.0
- `anomaly_std_threshold` must be a positive float
- `correlation_threshold` must be a float between 0.0 and 1.0
- `enable_reasoning` must be a boolean

### Runtime Validation

When generating insights, the tool validates:

1. **Confidence thresholds** - Insights must meet minimum confidence
2. **Anomaly detection** - Anomalies must exceed std threshold
3. **Correlation significance** - Correlations must exceed threshold
4. **Reasoning availability** - Research tool must be available if enabled

## Insight Types

The AI Insight Generator Tool supports various insight types:

### Basic Insights
- **Pattern** - Discover hidden patterns in data
- **Anomaly** - Detect anomalies and outliers
- **Trend** - Identify trends and patterns over time
- **Correlation** - Find relationships between variables

### Advanced Insights
- **Segmentation** - Identify distinct data segments
- **Causation** - Determine cause-and-effect relationships

## Operations Supported

The AI Insight Generator Tool supports comprehensive insight generation operations:

### Basic Insight Generation
- `generate_insights` - Generate comprehensive insights from data
- `detect_patterns` - Discover patterns in data
- `detect_anomalies` - Identify anomalies and outliers
- `analyze_trends` - Analyze trends and patterns
- `find_correlations` - Find correlations between variables

### Advanced Analysis
- `segment_data` - Segment data into distinct groups
- `analyze_causation` - Analyze cause-and-effect relationships
- `generate_actionable_insights` - Generate actionable business insights
- `forecast_trends` - Forecast future trends
- `validate_insights` - Validate insight quality and reliability

### Reasoning Integration
- `apply_mills_methods` - Apply Mill's methods for causal analysis
- `inductive_reasoning` - Apply inductive reasoning
- `deductive_reasoning` - Apply deductive reasoning
- `abductive_reasoning` - Apply abductive reasoning

### Utility Operations
- `get_insight_confidence` - Get confidence scores for insights
- `filter_insights` - Filter insights by criteria
- `export_insights` - Export insights to various formats
- `visualize_insights` - Create visualizations of insights

## Troubleshooting

### Issue: Low confidence insights

**Error:** Insights below confidence threshold

**Solutions:**
```bash
# Lower confidence threshold
export AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.5

# Check data quality
# Verify insight generation parameters
```

### Issue: Too many anomalies detected

**Error:** Excessive anomaly detection

**Solutions:**
```bash
# Increase anomaly threshold
export AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.5

# Check data distribution
# Verify anomaly detection logic
```

### Issue: Weak correlations found

**Error:** No significant correlations detected

**Solutions:**
```bash
# Lower correlation threshold
export AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.3

# Check data relationships
# Verify correlation calculation
```

### Issue: Reasoning methods not available

**Error:** Research tool integration fails

**Solutions:**
```bash
# Disable reasoning for testing
export AI_INSIGHT_GENERATOR_ENABLE_REASONING=false

# Check research tool availability
# Verify research tool configuration
```

### Issue: Insight generation fails

**Error:** `InsightGenerationError` during processing

**Solutions:**
1. Check data format and quality
2. Verify configuration parameters
3. Check external tool dependencies
4. Validate input data structure

### Issue: Performance issues

**Error:** Slow insight generation

**Solutions:**
1. Optimize data size and complexity
2. Adjust confidence thresholds
3. Disable reasoning if not needed
4. Check system resources

## Best Practices

### Performance Optimization

1. **Confidence Management** - Balance confidence thresholds for optimal results
2. **Threshold Tuning** - Adjust anomaly and correlation thresholds based on data
3. **Reasoning Usage** - Enable reasoning only when needed
4. **Data Preparation** - Ensure clean, well-structured input data
5. **Resource Management** - Monitor memory and CPU usage

### Error Handling

1. **Graceful Degradation** - Handle insight generation failures gracefully
2. **Validation** - Validate insights before using them
3. **Fallback Strategies** - Provide fallback insight methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Data Privacy** - Ensure data privacy in insight generation
2. **Access Control** - Control access to insight generation
3. **Audit Logging** - Log insight generation activities
4. **Data Validation** - Validate input data before processing
5. **Result Sanitization** - Sanitize insight results

### Resource Management

1. **Memory Usage** - Monitor memory consumption during processing
2. **Processing Time** - Set reasonable timeouts
3. **Data Size** - Manage data size for optimal performance
4. **Cleanup** - Clean up temporary data and resources
5. **Caching** - Implement caching for repeated analyses

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.5
AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=3.5
AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.3
AI_INSIGHT_GENERATOR_ENABLE_REASONING=false
```

**Production:**
```bash
AI_INSIGHT_GENERATOR_MIN_CONFIDENCE=0.8
AI_INSIGHT_GENERATOR_ANOMALY_STD_THRESHOLD=2.5
AI_INSIGHT_GENERATOR_CORRELATION_THRESHOLD=0.6
AI_INSIGHT_GENERATOR_ENABLE_REASONING=true
```

### Error Handling

Always wrap insight generation operations in try-except blocks:

```python
from aiecs.tools.statistics.ai_insight_generator_tool import AIInsightGeneratorTool, InsightGeneratorError, InsightGenerationError

insight_tool = AIInsightGeneratorTool()

try:
    insights = insight_tool.generate_insights(
        data=df,
        insight_types=['pattern', 'anomaly', 'correlation']
    )
except InsightGenerationError as e:
    print(f"Insight generation error: {e}")
except InsightGeneratorError as e:
    print(f"Insight generator error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv pandas numpy scipy

# Install statistical analysis dependencies
pip install scikit-learn statsmodels

# Install visualization dependencies
pip install matplotlib seaborn plotly
```

### Optional Dependencies

```bash
# For advanced statistical analysis
pip install pingouin lifelines

# For machine learning insights
pip install xgboost lightgbm

# For time series analysis
pip install prophet statsforecast

# For research tool integration
pip install spacy nltk
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import pandas
    import numpy
    import scipy
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test statistical analysis availability
try:
    import sklearn
    import statsmodels
    print("Statistical analysis available")
except ImportError:
    print("Statistical analysis not available")

# Test research tool availability
try:
    from aiecs.tools.task_tools.research_tool import ResearchTool
    print("Research tool available")
except ImportError:
    print("Research tool not available")
```

## Related Documentation

- Tool implementation details in the source code
- Research tool documentation for reasoning methods
- Statistical analysis tools documentation
- Main aiecs documentation for architecture overview

## Support

For issues or questions about AI Insight Generator Tool configuration:
- Check the tool source code for implementation details
- Review research tool documentation for reasoning methods
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. insight issues
- Verify confidence and threshold settings
- Check research tool availability and configuration
- Ensure proper data format and quality
- Validate insight generation parameters
