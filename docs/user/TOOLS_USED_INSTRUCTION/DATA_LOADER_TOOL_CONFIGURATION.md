# Data Loader Tool Configuration Guide

## Overview

The Data Loader Tool is a universal data loading tool that provides comprehensive data loading capabilities with auto-detection of file formats, multiple loading strategies (full, streaming, chunked, lazy), data quality validation on load, schema inference and validation, and support for CSV, Excel, JSON, Parquet, and other formats. It can load data from multiple file formats, auto-detect data formats and schemas, handle large datasets with streaming, and validate data quality on load. The tool integrates with pandas_tool for core data operations and supports various data source types (CSV, Excel, JSON, Parquet, Feather, HDF5, Stata, SAS, SPSS) and loading strategies (full_load, streaming, chunked, lazy, incremental). The tool can be configured via environment variables using the `DATA_LOADER_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Data Loader Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
DATA_LOADER_MAX_FILE_SIZE_MB=500
DATA_LOADER_DEFAULT_CHUNK_SIZE=10000
DATA_LOADER_MAX_MEMORY_USAGE_MB=2000
DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
DATA_LOADER_DEFAULT_ENCODING=utf-8
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.data_loader_tool import DataLoaderTool

# The tool will automatically use the environment variables
data_loader = DataLoaderTool()
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

from aiecs.tools.statistics.data_loader_tool import DataLoaderTool
data_loader = DataLoaderTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for large datasets
DATA_LOADER_MAX_FILE_SIZE_MB=1000
DATA_LOADER_DEFAULT_CHUNK_SIZE=50000
DATA_LOADER_MAX_MEMORY_USAGE_MB=4000
DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
DATA_LOADER_DEFAULT_ENCODING=utf-8
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
DATA_LOADER_MAX_FILE_SIZE_MB=100
DATA_LOADER_DEFAULT_CHUNK_SIZE=1000
DATA_LOADER_MAX_MEMORY_USAGE_MB=500
DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
DATA_LOADER_ENABLE_QUALITY_VALIDATION=false
DATA_LOADER_DEFAULT_ENCODING=utf-8
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
   # Data Loader Tool Configuration
   
   # Maximum file size in megabytes
   DATA_LOADER_MAX_FILE_SIZE_MB=500
   
   # Default chunk size for chunked loading
   DATA_LOADER_DEFAULT_CHUNK_SIZE=10000
   
   # Maximum memory usage in megabytes
   DATA_LOADER_MAX_MEMORY_USAGE_MB=2000
   
   # Whether to enable automatic schema inference
   DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
   
   # Whether to enable data quality validation
   DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
   
   # Default text encoding for file operations
   DATA_LOADER_DEFAULT_ENCODING=utf-8
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `utf-8`, `latin-1`
   - Integers: Plain numbers: `500`, `10000`, `2000`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Max File Size MB

**Environment Variable:** `DATA_LOADER_MAX_FILE_SIZE_MB`

**Type:** Integer

**Default:** `500`

**Description:** Maximum file size in megabytes that can be loaded. Files larger than this will trigger chunked or streaming loading strategies to prevent memory issues.

**Common Values:**
- `100` - Small files only (development/testing)
- `500` - Standard files (default, balanced)
- `1000` - Large files (production)
- `2000` - Very large files (high-memory systems)

**Example:**
```bash
export DATA_LOADER_MAX_FILE_SIZE_MB=1000
```

**Size Note:** Larger values allow bigger files but require more memory.

### 2. Default Chunk Size

**Environment Variable:** `DATA_LOADER_DEFAULT_CHUNK_SIZE`

**Type:** Integer

**Default:** `10000`

**Description:** Default chunk size for chunked loading operations. This determines how many rows are processed at once when using chunked loading strategies.

**Common Values:**
- `1000` - Small chunks (low memory usage)
- `10000` - Standard chunks (default, balanced)
- `50000` - Large chunks (high performance)
- `100000` - Very large chunks (maximum performance)

**Example:**
```bash
export DATA_LOADER_DEFAULT_CHUNK_SIZE=50000
```

**Chunk Note:** Larger chunks improve performance but use more memory.

### 3. Max Memory Usage MB

**Environment Variable:** `DATA_LOADER_MAX_MEMORY_USAGE_MB`

**Type:** Integer

**Default:** `2000`

**Description:** Maximum memory usage in megabytes for data loading operations. This helps prevent out-of-memory errors by controlling memory consumption.

**Common Values:**
- `500` - Low memory systems
- `2000` - Standard systems (default)
- `4000` - High memory systems
- `8000` - Very high memory systems

**Example:**
```bash
export DATA_LOADER_MAX_MEMORY_USAGE_MB=4000
```

**Memory Note:** Higher values allow larger datasets but require more system memory.

### 4. Enable Schema Inference

**Environment Variable:** `DATA_LOADER_ENABLE_SCHEMA_INFERENCE`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable automatic schema inference when loading data. Schema inference automatically detects data types and structure.

**Values:**
- `true` - Enable schema inference (default)
- `false` - Disable schema inference

**Example:**
```bash
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
```

**Schema Note:** Schema inference improves data quality but may slow down loading.

### 5. Enable Quality Validation

**Environment Variable:** `DATA_LOADER_ENABLE_QUALITY_VALIDATION`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable data quality validation during loading. Quality validation checks for missing values, data type consistency, and other quality issues.

**Values:**
- `true` - Enable quality validation (default)
- `false` - Disable quality validation

**Example:**
```bash
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
```

**Quality Note:** Quality validation improves data reliability but may slow down loading.

### 6. Default Encoding

**Environment Variable:** `DATA_LOADER_DEFAULT_ENCODING`

**Type:** String

**Default:** `"utf-8"`

**Description:** Default text encoding for file operations. This is used when no specific encoding is provided for text-based file formats.

**Common Encodings:**
- `utf-8` - Unicode UTF-8 (default, most common)
- `latin-1` - Latin-1 (ISO-8859-1)
- `cp1252` - Windows-1252
- `ascii` - ASCII (7-bit)

**Example:**
```bash
export DATA_LOADER_DEFAULT_ENCODING=utf-8
```

**Encoding Note:** UTF-8 is recommended for international text, Latin-1 for legacy systems.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic data loading parameters
export DATA_LOADER_MAX_FILE_SIZE_MB=500
export DATA_LOADER_DEFAULT_CHUNK_SIZE=10000
export DATA_LOADER_MAX_MEMORY_USAGE_MB=2000
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
export DATA_LOADER_DEFAULT_ENCODING=utf-8

# Run your application
python app.py
```

### Example 2: High-Performance Configuration

```bash
# Optimized for large datasets and high performance
export DATA_LOADER_MAX_FILE_SIZE_MB=1000
export DATA_LOADER_DEFAULT_CHUNK_SIZE=50000
export DATA_LOADER_MAX_MEMORY_USAGE_MB=4000
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
export DATA_LOADER_DEFAULT_ENCODING=utf-8
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export DATA_LOADER_MAX_FILE_SIZE_MB=100
export DATA_LOADER_DEFAULT_CHUNK_SIZE=1000
export DATA_LOADER_MAX_MEMORY_USAGE_MB=500
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=false
export DATA_LOADER_DEFAULT_ENCODING=utf-8
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.data_loader_tool import DataLoaderTool

# Initialize with custom configuration
data_loader = DataLoaderTool(config={
    'max_file_size_mb': 500,
    'default_chunk_size': 10000,
    'max_memory_usage_mb': 2000,
    'enable_schema_inference': True,
    'enable_quality_validation': True,
    'default_encoding': 'utf-8'
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export DATA_LOADER_DEFAULT_CHUNK_SIZE=10000
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
```

```python
# Override for specific instance
data_loader = DataLoaderTool(config={
    'default_chunk_size': 50000,  # This overrides the environment variable
    'enable_quality_validation': False  # This overrides the environment variable
})
```

## Configuration Priority

When the Data Loader Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `DATA_LOADER_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export DATA_LOADER_DEFAULT_ENCODING=utf-8
export DATA_LOADER_DEFAULT_ENCODING=latin-1
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export DATA_LOADER_MAX_FILE_SIZE_MB=500
export DATA_LOADER_DEFAULT_CHUNK_SIZE=10000
export DATA_LOADER_MAX_MEMORY_USAGE_MB=2000
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `max_file_size_mb` must be a positive integer
- `default_chunk_size` must be a positive integer
- `max_memory_usage_mb` must be a positive integer
- `enable_schema_inference` must be a boolean
- `enable_quality_validation` must be a boolean
- `default_encoding` must be a non-empty string

### Runtime Validation

When loading data, the tool validates:

1. **File size** - Files must not exceed maximum size limit
2. **Memory usage** - Operations must not exceed memory limits
3. **Chunk size** - Chunk size must be reasonable for the dataset
4. **Encoding** - Encoding must be valid for the file format
5. **Schema compatibility** - Schema inference must be compatible with data
6. **Quality standards** - Data must meet quality validation criteria

## Data Source Types

The Data Loader Tool supports various data source types:

### Text Formats
- **CSV** - Comma-separated values
- **JSON** - JavaScript Object Notation
- **Excel** - Microsoft Excel files (.xlsx, .xls)

### Binary Formats
- **Parquet** - Columnar storage format
- **Feather** - Fast binary format
- **HDF5** - Hierarchical Data Format

### Statistical Formats
- **Stata** - Stata data files
- **SAS** - SAS data files
- **SPSS** - SPSS data files

### Auto-Detection
- **AUTO** - Automatically detect file format

## Loading Strategies

### Full Load
- Load entire dataset into memory
- Fastest for small to medium datasets
- Requires sufficient memory

### Streaming
- Process data in continuous stream
- Memory-efficient for large datasets
- Slower but handles unlimited size

### Chunked
- Process data in fixed-size chunks
- Balanced memory usage and performance
- Good for large datasets

### Lazy
- Load data on-demand
- Minimal initial memory usage
- Slower access but memory-efficient

### Incremental
- Load data in incremental batches
- Good for ongoing data processing
- Maintains processing state

## Operations Supported

The Data Loader Tool supports comprehensive data loading operations:

### Basic Loading
- `load_data` - Load data from various file formats
- `load_csv` - Load CSV files with options
- `load_excel` - Load Excel files with sheet selection
- `load_json` - Load JSON files with structure handling
- `load_parquet` - Load Parquet files efficiently

### Advanced Loading
- `load_chunked` - Load data in chunks for large files
- `load_streaming` - Stream data for memory efficiency
- `load_lazy` - Lazy load data on-demand
- `load_incremental` - Incremental data loading
- `auto_detect_format` - Automatically detect file format

### Schema Operations
- `infer_schema` - Infer data schema automatically
- `validate_schema` - Validate data against schema
- `apply_schema` - Apply schema to loaded data
- `get_schema_info` - Get detailed schema information

### Quality Operations
- `validate_quality` - Validate data quality
- `check_missing_values` - Check for missing values
- `validate_data_types` - Validate data type consistency
- `generate_quality_report` - Generate data quality report

### Utility Operations
- `get_file_info` - Get file information and metadata
- `estimate_memory_usage` - Estimate memory requirements
- `check_file_compatibility` - Check file format compatibility
- `optimize_loading_strategy` - Optimize loading strategy

## Troubleshooting

### Issue: File too large error

**Error:** File exceeds maximum size limit

**Solutions:**
```bash
# Increase file size limit
export DATA_LOADER_MAX_FILE_SIZE_MB=1000

# Or use chunked loading
data_loader.load_data(file_path, strategy='chunked')
```

### Issue: Memory usage exceeded

**Error:** Memory usage exceeds limit

**Solutions:**
```bash
# Increase memory limit
export DATA_LOADER_MAX_MEMORY_USAGE_MB=4000

# Or reduce chunk size
export DATA_LOADER_DEFAULT_CHUNK_SIZE=5000
```

### Issue: Schema inference fails

**Error:** Schema inference errors

**Solutions:**
```bash
# Disable schema inference
export DATA_LOADER_ENABLE_SCHEMA_INFERENCE=false

# Or provide explicit schema
data_loader.load_data(file_path, schema=explicit_schema)
```

### Issue: Quality validation fails

**Error:** Data quality validation errors

**Solutions:**
```bash
# Disable quality validation
export DATA_LOADER_ENABLE_QUALITY_VALIDATION=false

# Or fix data quality issues
data_loader.validate_quality(data)
```

### Issue: Encoding problems

**Error:** Text encoding errors

**Solutions:**
```bash
# Set correct encoding
export DATA_LOADER_DEFAULT_ENCODING=latin-1

# Or specify encoding per file
data_loader.load_data(file_path, encoding='utf-8')
```

### Issue: Chunked loading performance

**Error:** Slow chunked loading

**Solutions:**
```bash
# Increase chunk size
export DATA_LOADER_DEFAULT_CHUNK_SIZE=50000

# Or use streaming strategy
data_loader.load_data(file_path, strategy='streaming')
```

### Issue: File format not supported

**Error:** Unsupported file format

**Solutions:**
1. Check file format compatibility
2. Use auto-detection
3. Convert file to supported format
4. Install required dependencies

## Best Practices

### Performance Optimization

1. **Chunk Size Tuning** - Optimize chunk size for your data
2. **Memory Management** - Monitor memory usage and set appropriate limits
3. **Format Selection** - Choose efficient formats (Parquet, Feather)
4. **Strategy Selection** - Use appropriate loading strategy
5. **Schema Optimization** - Disable schema inference when not needed

### Error Handling

1. **Graceful Degradation** - Handle loading failures gracefully
2. **Validation** - Validate data before processing
3. **Fallback Strategies** - Provide fallback loading methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **File Validation** - Validate file paths and permissions
2. **Content Validation** - Validate file content before loading
3. **Access Control** - Control access to data files
4. **Audit Logging** - Log data loading activities
5. **Data Privacy** - Ensure data privacy and compliance

### Resource Management

1. **Memory Monitoring** - Monitor memory usage during loading
2. **File Cleanup** - Clean up temporary files
3. **Connection Management** - Manage database connections efficiently
4. **Processing Time** - Set reasonable timeouts
5. **Storage Optimization** - Optimize data storage formats

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
DATA_LOADER_MAX_FILE_SIZE_MB=100
DATA_LOADER_DEFAULT_CHUNK_SIZE=1000
DATA_LOADER_MAX_MEMORY_USAGE_MB=500
DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
DATA_LOADER_ENABLE_QUALITY_VALIDATION=false
DATA_LOADER_DEFAULT_ENCODING=utf-8
```

**Production:**
```bash
DATA_LOADER_MAX_FILE_SIZE_MB=1000
DATA_LOADER_DEFAULT_CHUNK_SIZE=50000
DATA_LOADER_MAX_MEMORY_USAGE_MB=4000
DATA_LOADER_ENABLE_SCHEMA_INFERENCE=true
DATA_LOADER_ENABLE_QUALITY_VALIDATION=true
DATA_LOADER_DEFAULT_ENCODING=utf-8
```

### Error Handling

Always wrap data loading operations in try-except blocks:

```python
from aiecs.tools.statistics.data_loader_tool import DataLoaderTool, DataLoaderError, FileFormatError, SchemaValidationError, DataQualityError

data_loader = DataLoaderTool()

try:
    data = data_loader.load_data(
        file_path='data.csv',
        source_type='csv',
        strategy='full_load'
    )
except FileFormatError as e:
    print(f"File format error: {e}")
except SchemaValidationError as e:
    print(f"Schema validation error: {e}")
except DataQualityError as e:
    print(f"Data quality error: {e}")
except DataLoaderError as e:
    print(f"Data loader error: {e}")
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

# Install file format dependencies
pip install openpyxl xlrd pyarrow fastparquet
```

### Optional Dependencies

```bash
# For statistical formats
pip install pyreadstat

# For HDF5 support
pip install h5py

# For Feather support
pip install feather-format

# For advanced data types
pip install pandas-stubs
```

### Verification

```python
# Test dependency availability
try:
    import pandas
    import numpy
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test format support
try:
    import openpyxl
    print("Excel support available")
except ImportError:
    print("Excel support not available")

try:
    import pyarrow
    print("Parquet support available")
except ImportError:
    print("Parquet support not available")

# Test statistical format support
try:
    import pyreadstat
    print("Statistical format support available")
except ImportError:
    print("Statistical format support not available")
```

## Related Documentation

- Tool implementation details in the source code
- Pandas tool documentation for core data operations
- Statistics tools documentation for data analysis
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Data Loader Tool configuration:
- Check the tool source code for implementation details
- Review pandas tool documentation for core data operations
- Consult the main aiecs documentation for architecture overview
- Test with simple files first to isolate configuration vs. loading issues
- Verify file format compatibility and dependencies
- Check memory and file size limits
- Ensure proper encoding and schema settings
- Validate data quality and structure requirements
