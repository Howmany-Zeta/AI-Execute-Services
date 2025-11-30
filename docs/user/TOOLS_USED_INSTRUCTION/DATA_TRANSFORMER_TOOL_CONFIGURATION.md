# Data Transformer Tool Configuration Guide

## Overview

The Data Transformer Tool is an advanced data transformation tool that provides comprehensive data transformation capabilities with data cleaning and preprocessing, feature engineering and encoding, normalization and standardization, transformation pipelines, and missing value handling. It can clean and preprocess data, engineer features, transform and normalize data, and build transformation pipelines. The tool integrates with pandas_tool for core operations and supports various transformation types (cleaning operations, transformation operations, encoding operations, feature engineering) and missing value strategies (drop, mean, median, mode, forward_fill, backward_fill, interpolate, constant). The tool can be configured via environment variables using the `DATA_TRANSFORMER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Data Transformer Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=10
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.data_transformer_tool import DataTransformerTool

# The tool will automatically use the environment variables
data_transformer = DataTransformerTool()
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

from aiecs.tools.statistics.data_transformer_tool import DataTransformerTool
data_transformer = DataTransformerTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for robust transformations
DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=2.5
DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median
DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=20
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false
DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=5
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
   # Data Transformer Tool Configuration
   
   # Standard deviation threshold for outlier detection
   DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
   
   # Default strategy for handling missing values
   DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
   
   # Whether to enable transformation pipeline caching
   DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
   
   # Maximum number of categories for one-hot encoding
   DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=10
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `mean`, `median`, `mode`
   - Floats: Decimal numbers: `3.0`, `2.5`
   - Integers: Plain numbers: `10`, `20`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Outlier STD Threshold

**Environment Variable:** `DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD`

**Type:** Float

**Default:** `3.0`

**Description:** Standard deviation threshold for outlier detection. Values beyond this threshold are considered outliers using the Z-score method during data cleaning operations.

**Common Values:**
- `2.0` - Strict outlier detection (more outliers detected)
- `2.5` - Moderate outlier detection
- `3.0` - Standard outlier detection (default)
- `3.5` - Lenient outlier detection (fewer outliers detected)

**Example:**
```bash
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=2.5
```

**Threshold Note:** Lower values detect more outliers, higher values are more lenient.

### 2. Default Missing Strategy

**Environment Variable:** `DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY`

**Type:** String

**Default:** `"mean"`

**Description:** Default strategy for handling missing values when no specific strategy is provided. This determines how missing values are imputed or handled.

**Supported Strategies:**
- `drop` - Drop rows/columns with missing values
- `mean` - Fill with mean value (default)
- `median` - Fill with median value
- `mode` - Fill with most frequent value
- `forward_fill` - Forward fill missing values
- `backward_fill` - Backward fill missing values
- `interpolate` - Interpolate missing values
- `constant` - Fill with constant value

**Example:**
```bash
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median
```

**Strategy Note:** Choose based on your data characteristics and domain knowledge.

### 3. Enable Pipeline Caching

**Environment Variable:** `DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable transformation pipeline caching. Caching improves performance for repeated transformations but uses additional memory.

**Values:**
- `true` - Enable pipeline caching (default)
- `false` - Disable pipeline caching

**Example:**
```bash
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
```

**Caching Note:** Enable for better performance, disable to save memory.

### 4. Max One Hot Categories

**Environment Variable:** `DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES`

**Type:** Integer

**Default:** `10`

**Description:** Maximum number of categories for one-hot encoding. Columns with more unique values will use alternative encoding methods to prevent excessive dimensionality.

**Common Values:**
- `5` - Conservative encoding (few categories)
- `10` - Standard encoding (default)
- `20` - Liberal encoding (many categories)
- `50` - Very liberal encoding (maximum categories)

**Example:**
```bash
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=20
```

**Categories Note:** Higher values allow more categories but increase dimensionality.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic data transformation parameters
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=10

# Run your application
python app.py
```

### Example 2: Robust Production Configuration

```bash
# Optimized for robust data transformations
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=2.5
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=20
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=5
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.data_transformer_tool import DataTransformerTool

# Initialize with custom configuration
data_transformer = DataTransformerTool(config={
    'outlier_std_threshold': 3.0,
    'default_missing_strategy': 'mean',
    'enable_pipeline_caching': True,
    'max_one_hot_categories': 10
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
```

```python
# Override for specific instance
data_transformer = DataTransformerTool(config={
    'default_missing_strategy': 'median',  # This overrides the environment variable
    'enable_pipeline_caching': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Data Transformer Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DATA_TRANSFORMER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mode
```

### Float Values

Floats should be provided as decimal numbers:

```bash
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=2.5
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=10
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=20
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `outlier_std_threshold` must be a positive float
- `default_missing_strategy` must be a valid strategy string
- `enable_pipeline_caching` must be a boolean
- `max_one_hot_categories` must be a positive integer

### Runtime Validation

When transforming data, the tool validates:

1. **Outlier threshold** - Threshold must be reasonable for the data distribution
2. **Missing strategy** - Strategy must be appropriate for the data type
3. **Category limits** - Category limits must be reasonable for encoding
4. **Data compatibility** - Data must be compatible with transformation operations
5. **Memory requirements** - Transformations must not exceed memory limits

## Transformation Types

The Data Transformer Tool supports various transformation types:

### Cleaning Operations
- **Remove Duplicates** - Remove duplicate rows or columns
- **Fill Missing** - Fill missing values using various strategies
- **Remove Outliers** - Remove statistical outliers

### Transformation Operations
- **Normalize** - Min-max normalization
- **Standardize** - Z-score standardization
- **Log Transform** - Logarithmic transformation
- **Box-Cox** - Box-Cox power transformation

### Encoding Operations
- **One-Hot Encode** - One-hot encoding for categorical variables
- **Label Encode** - Label encoding for ordinal variables
- **Target Encode** - Target encoding for high-cardinality variables

### Feature Engineering
- **Polynomial Features** - Generate polynomial features
- **Interaction Features** - Create feature interactions
- **Binning** - Create bins for continuous variables
- **Aggregation** - Aggregate features by groups

## Missing Value Strategies

### Statistical Strategies
- **Mean** - Fill with mean value (default)
- **Median** - Fill with median value
- **Mode** - Fill with most frequent value

### Interpolation Strategies
- **Forward Fill** - Forward fill missing values
- **Backward Fill** - Backward fill missing values
- **Interpolate** - Linear interpolation

### Other Strategies
- **Drop** - Drop rows/columns with missing values
- **Constant** - Fill with constant value

## Operations Supported

The Data Transformer Tool supports comprehensive data transformation operations:

### Basic Transformations
- `transform_data` - Apply comprehensive data transformations
- `clean_data` - Clean and preprocess data
- `handle_missing_values` - Handle missing values
- `remove_outliers` - Remove statistical outliers
- `remove_duplicates` - Remove duplicate records

### Feature Engineering
- `engineer_features` - Engineer new features
- `create_polynomial_features` - Create polynomial features
- `create_interaction_features` - Create feature interactions
- `create_bins` - Create bins for continuous variables
- `aggregate_features` - Aggregate features by groups

### Encoding Operations
- `encode_categorical` - Encode categorical variables
- `one_hot_encode` - One-hot encode categorical variables
- `label_encode` - Label encode ordinal variables
- `target_encode` - Target encode high-cardinality variables
- `handle_high_cardinality` - Handle high-cardinality categorical variables

### Normalization and Scaling
- `normalize_data` - Normalize data to [0,1] range
- `standardize_data` - Standardize data to mean=0, std=1
- `robust_scale` - Robust scaling using median and IQR
- `min_max_scale` - Min-max scaling
- `z_score_scale` - Z-score standardization

### Pipeline Operations
- `create_pipeline` - Create transformation pipeline
- `fit_pipeline` - Fit transformation pipeline
- `transform_pipeline` - Apply transformation pipeline
- `inverse_transform` - Inverse transform data
- `save_pipeline` - Save transformation pipeline
- `load_pipeline` - Load transformation pipeline

### Advanced Operations
- `log_transform` - Apply logarithmic transformation
- `box_cox_transform` - Apply Box-Cox transformation
- `power_transform` - Apply power transformation
- `quantile_transform` - Apply quantile transformation
- `robust_transform` - Apply robust transformation

## Troubleshooting

### Issue: Outlier removal too aggressive

**Error:** Too many data points removed as outliers

**Solutions:**
```bash
# Increase outlier threshold
export DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.5

# Or use domain-specific outlier detection
data_transformer.remove_outliers(data, method='domain_specific')
```

### Issue: Missing value strategy fails

**Error:** Missing value imputation errors

**Solutions:**
```bash
# Change missing strategy
export DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median

# Or specify strategy per column
data_transformer.handle_missing_values(data, strategies={'col1': 'mean', 'col2': 'median'})
```

### Issue: One-hot encoding creates too many columns

**Error:** Excessive dimensionality from one-hot encoding

**Solutions:**
```bash
# Reduce max categories
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=5

# Or use alternative encoding
data_transformer.encode_categorical(data, method='target_encoding')
```

### Issue: Pipeline caching issues

**Error:** Pipeline caching problems

**Solutions:**
```bash
# Disable caching
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false

# Or clear cache
data_transformer.clear_pipeline_cache()
```

### Issue: Transformation performance issues

**Error:** Slow transformation operations

**Solutions:**
1. Enable pipeline caching
2. Use appropriate data types
3. Process data in chunks
4. Optimize transformation order

### Issue: Memory usage exceeded

**Error:** Out of memory during transformations

**Solutions:**
```bash
# Disable caching
export DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false

# Reduce max categories
export DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=5

# Process data in chunks
data_transformer.transform_data(data, chunk_size=10000)
```

### Issue: Data type compatibility

**Error:** Data type incompatibility with transformations

**Solutions:**
1. Check data types before transformation
2. Convert data types appropriately
3. Use compatible transformation methods
4. Validate data structure

## Best Practices

### Performance Optimization

1. **Pipeline Caching** - Enable caching for repeated transformations
2. **Category Management** - Set appropriate category limits
3. **Chunk Processing** - Process large datasets in chunks
4. **Memory Management** - Monitor memory usage during transformations
5. **Transformation Order** - Optimize transformation sequence

### Error Handling

1. **Graceful Degradation** - Handle transformation failures gracefully
2. **Validation** - Validate data before transformation
3. **Fallback Strategies** - Provide fallback transformation methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **Data Privacy** - Ensure data privacy during transformations
2. **Access Control** - Control access to transformation results
3. **Audit Logging** - Log transformation activities
4. **Data Sanitization** - Sanitize sensitive data
5. **Compliance** - Ensure compliance with data regulations

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during transformations
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
DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=3.0
DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=mean
DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=false
DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=5
```

**Production:**
```bash
DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD=2.5
DATA_TRANSFORMER_DEFAULT_MISSING_STRATEGY=median
DATA_TRANSFORMER_ENABLE_PIPELINE_CACHING=true
DATA_TRANSFORMER_MAX_ONE_HOT_CATEGORIES=20
```

### Error Handling

Always wrap transformation operations in try-except blocks:

```python
from aiecs.tools.statistics.data_transformer_tool import DataTransformerTool, DataTransformerError, TransformationError

data_transformer = DataTransformerTool()

try:
    transformed_data = data_transformer.transform_data(
        data=df,
        transformations=['normalize', 'encode_categorical'],
        missing_strategy='mean'
    )
except TransformationError as e:
    print(f"Transformation error: {e}")
except DataTransformerError as e:
    print(f"Data transformer error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install data processing dependencies
pip install pandas numpy scikit-learn

# Install transformation dependencies
pip install scipy statsmodels
```

### Optional Dependencies

```bash
# For advanced transformations
pip install category-encoders feature-engine

# For feature selection
pip install sklearn-feature-selection

# For advanced scaling
pip install scikit-learn-extra

# For pipeline optimization
pip install optuna hyperopt
```

### Verification

```python
# Test dependency availability
try:
    import pandas
    import numpy
    import sklearn
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test transformation availability
try:
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.impute import SimpleImputer
    print("Transformation dependencies available")
except ImportError:
    print("Transformation dependencies not available")

# Test advanced encoding availability
try:
    import category_encoders
    print("Advanced encoding available")
except ImportError:
    print("Advanced encoding not available")

# Test feature engineering availability
try:
    import feature_engine
    print("Feature engineering available")
except ImportError:
    print("Feature engineering not available")
```

## Related Documentation

- Tool implementation details in the source code
- Pandas tool documentation for core data operations
- Statistics tool documentation for statistical analysis
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Data Transformer Tool configuration:
- Check the tool source code for implementation details
- Review pandas tool documentation for core data operations
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. transformation issues
- Verify data compatibility and format requirements
- Check transformation parameters and strategies
- Ensure proper encoding and scaling settings
- Validate data quality and structure requirements
