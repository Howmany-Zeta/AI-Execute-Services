# Pandas Tool Configuration Guide

## Overview

The Pandas Tool provides comprehensive data processing capabilities using pandas, supporting 30+ operations for data manipulation, analysis, and transformation. It can handle CSV, JSON, and Excel files with configurable processing parameters. It can be configured via environment variables using the `PANDAS_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Pandas Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
PANDAS_TOOL_CSV_DELIMITER=,
PANDAS_TOOL_ENCODING=utf-8
PANDAS_TOOL_DEFAULT_AGG={"numeric":"mean","object":"count"}
PANDAS_TOOL_CHUNK_SIZE=10000
PANDAS_TOOL_MAX_CSV_SIZE=1000000
PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=[".csv",".xlsx",".json"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.pandas_tool import PandasTool

# The tool will automatically use the environment variables
pandas_tool = PandasTool()
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

from aiecs.tools.task_tools.pandas_tool import PandasTool
pandas_tool = PandasTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for large datasets
PANDAS_TOOL_CSV_DELIMITER=,
PANDAS_TOOL_ENCODING=utf-8
PANDAS_TOOL_CHUNK_SIZE=50000
PANDAS_TOOL_MAX_CSV_SIZE=5000000
PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=[".csv",".xlsx"]
```

**Example `.env.development`:**
```bash
# Development settings - smaller chunks for testing
PANDAS_TOOL_CSV_DELIMITER=,
PANDAS_TOOL_ENCODING=utf-8
PANDAS_TOOL_CHUNK_SIZE=1000
PANDAS_TOOL_MAX_CSV_SIZE=100000
PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=[".csv",".xlsx",".json"]
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
   # Pandas Tool Configuration
   
   # CSV delimiter character
   PANDAS_TOOL_CSV_DELIMITER=,
   
   # File encoding
   PANDAS_TOOL_ENCODING=utf-8
   
   # Default aggregation functions (JSON object)
   PANDAS_TOOL_DEFAULT_AGG={"numeric":"mean","object":"count"}
   
   # Chunk size for large file processing
   PANDAS_TOOL_CHUNK_SIZE=10000
   
   # Threshold for chunked CSV processing
   PANDAS_TOOL_MAX_CSV_SIZE=1000000
   
   # Allowed file extensions (JSON array)
   PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=[".csv",".xlsx",".json"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `,`, `utf-8`
   - Integers: Plain numbers: `10000`, `1000000`
   - Dictionaries: JSON object format: `{"key":"value"}`
   - Lists: JSON array format: `[".csv",".xlsx"]`

## Configuration Options

### 1. CSV Delimiter

**Environment Variable:** `PANDAS_TOOL_CSV_DELIMITER`

**Type:** String

**Default:** `","`

**Description:** Delimiter character used for CSV file parsing and writing. This affects how CSV files are read and written.

**Common Values:**
- `,` - Comma (default, standard CSV)
- `;` - Semicolon (European CSV format)
- `\t` - Tab (TSV format)
- `|` - Pipe (alternative delimiter)
- ` ` - Space (space-separated values)

**Example:**
```bash
export PANDAS_TOOL_CSV_DELIMITER=";"
```

**Note:** Use semicolon for European CSV files that use comma as decimal separator.

### 2. Encoding

**Environment Variable:** `PANDAS_TOOL_ENCODING`

**Type:** String

**Default:** `"utf-8"`

**Description:** Character encoding used for file operations. This ensures proper handling of international characters and special symbols.

**Common Encodings:**
- `utf-8` - Unicode (default, most common)
- `utf-16` - Unicode 16-bit
- `latin-1` - Western European
- `cp1252` - Windows-1252
- `iso-8859-1` - ISO Latin-1

**Example:**
```bash
export PANDAS_TOOL_ENCODING="utf-8"
```

**Note:** Use `utf-8` unless you have specific requirements for legacy file formats.

### 3. Default Aggregation

**Environment Variable:** `PANDAS_TOOL_DEFAULT_AGG`

**Type:** Dict[str, str]

**Default:** `{"numeric": "mean", "object": "count"}`

**Description:** Default aggregation functions applied to different data types during groupby operations. This provides sensible defaults for statistical operations.

**Format:** JSON object with string keys and values

**Available Functions:**
- `mean` - Average value
- `sum` - Total sum
- `count` - Count of non-null values
- `min` - Minimum value
- `max` - Maximum value
- `std` - Standard deviation
- `median` - Median value
- `first` - First value
- `last` - Last value

**Example:**
```bash
export PANDAS_TOOL_DEFAULT_AGG='{"numeric":"sum","object":"count","datetime":"first"}'
```

### 4. Chunk Size

**Environment Variable:** `PANDAS_TOOL_CHUNK_SIZE`

**Type:** Integer

**Default:** `10000`

**Description:** Number of rows to process at a time when reading large files. This helps manage memory usage for large datasets.

**Common Values:**
- `1000` - Small chunks (development/testing)
- `10000` - Default (balanced)
- `50000` - Large chunks (production)
- `100000` - Very large chunks (high-memory systems)

**Example:**
```bash
export PANDAS_TOOL_CHUNK_SIZE=50000
```

**Performance Note:** Larger chunks use more memory but process faster. Adjust based on available RAM.

### 5. Max CSV Size

**Environment Variable:** `PANDAS_TOOL_MAX_CSV_SIZE`

**Type:** Integer

**Default:** `1000000`

**Description:** Threshold (in characters) for determining when to use chunked processing for CSV files. Files larger than this will be processed in chunks.

**Common Values:**
- `100000` - Small threshold (100KB)
- `1000000` - Default (1MB)
- `10000000` - Large threshold (10MB)
- `100000000` - Very large threshold (100MB)

**Example:**
```bash
export PANDAS_TOOL_MAX_CSV_SIZE=5000000
```

**Memory Management:** Lower values trigger chunked processing earlier, using less memory but potentially slower processing.

### 6. Allowed File Extensions

**Environment Variable:** `PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS`

**Type:** List[str]

**Default:** `['.csv', '.xlsx', '.json']`

**Description:** List of allowed file extensions for data processing. This is a security feature that prevents processing of unauthorized file types.

**Format:** JSON array string with double quotes

**Supported Formats:**
- `.csv` - Comma-separated values
- `.xlsx` - Excel spreadsheets
- `.json` - JSON data files
- `.xls` - Legacy Excel format (if supported)

**Example:**
```bash
# Strict - Only CSV and Excel
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx"]'

# Lenient - All supported formats
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx",".json"]'
```

**Security Note:** Only allow extensions that your application actually needs to process.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom processing parameters
export PANDAS_TOOL_CSV_DELIMITER=";"
export PANDAS_TOOL_CHUNK_SIZE=50000
export PANDAS_TOOL_MAX_CSV_SIZE=5000000
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx"]'

# Run your application
python app.py
```

### Example 2: High-Performance Configuration

```bash
# Optimized for large datasets
export PANDAS_TOOL_CHUNK_SIZE=100000
export PANDAS_TOOL_MAX_CSV_SIZE=10000000
export PANDAS_TOOL_DEFAULT_AGG='{"numeric":"sum","object":"count"}'
```

### Example 3: Memory-Constrained Configuration

```bash
# Conservative memory usage
export PANDAS_TOOL_CHUNK_SIZE=1000
export PANDAS_TOOL_MAX_CSV_SIZE=100000
export PANDAS_TOOL_DEFAULT_AGG='{"numeric":"mean","object":"count"}'
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.pandas_tool import PandasTool

# Initialize with custom configuration
pandas_tool = PandasTool(config={
    'csv_delimiter': ';',
    'encoding': 'utf-8',
    'chunk_size': 50000,
    'max_csv_size': 5000000,
    'allowed_file_extensions': ['.csv', '.xlsx']
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export PANDAS_TOOL_CHUNK_SIZE=10000
```

```python
# Override for specific instance
pandas_tool = PandasTool(config={
    'chunk_size': 50000  # This overrides the environment variable
})
```

## Configuration Priority

When the Pandas Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `PANDAS_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export PANDAS_TOOL_CSV_DELIMITER=,
export PANDAS_TOOL_ENCODING=utf-8
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export PANDAS_TOOL_CHUNK_SIZE=10000
export PANDAS_TOOL_MAX_CSV_SIZE=1000000
```

### Dictionary Values

Dictionaries must be provided as JSON objects with double quotes:

```bash
# Correct
export PANDAS_TOOL_DEFAULT_AGG='{"numeric":"mean","object":"count"}'

# Incorrect (will not parse)
export PANDAS_TOOL_DEFAULT_AGG="numeric:mean,object:count"
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx",".json"]'

# Incorrect (will not parse)
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=".csv,.xlsx,.json"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx"]'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `csv_delimiter` must be a non-empty string
- `encoding` must be a valid encoding string
- `default_agg` must be a dictionary with string keys and values
- `chunk_size` must be a positive integer
- `max_csv_size` must be a positive integer
- `allowed_file_extensions` must be a list of strings

### Runtime Validation

When processing data, the tool validates:

1. **File extensions** - Must be in `allowed_file_extensions` list
2. **Data structure** - Input records must be valid for DataFrame creation
3. **Column existence** - Referenced columns must exist in DataFrames
4. **Data types** - Type conversions are validated
5. **Query syntax** - Filter conditions are validated

## Operations Supported

The Pandas Tool supports 30+ operations across multiple categories:

### Data Reading/Writing
- `read_csv` - Read CSV string into DataFrame
- `read_json` - Read JSON string into DataFrame
- `read_file` - Read data from file (CSV, Excel, JSON)
- `write_file` - Write DataFrame to file

### Descriptive Statistics
- `summary` - Compute summary statistics
- `describe` - Compute descriptive statistics for columns
- `value_counts` - Compute value counts for columns

### Filtering and Selection
- `filter` - Filter DataFrame based on condition
- `select_columns` - Select specified columns
- `drop_columns` - Drop specified columns
- `drop_duplicates` - Drop duplicate rows
- `dropna` - Drop rows/columns with missing values

### Grouping and Aggregation
- `groupby` - Group DataFrame and apply aggregations
- `pivot_table` - Create pivot table

### Merging and Concatenation
- `merge` - Merge two DataFrames
- `concat` - Concatenate multiple DataFrames

### Data Transformation
- `sort_values` - Sort DataFrame by columns
- `rename_columns` - Rename DataFrame columns
- `replace_values` - Replace values in DataFrame
- `fill_na` - Fill missing values
- `astype` - Convert column types
- `apply` - Apply function to columns/rows

### Data Reshaping
- `melt` - Melt DataFrame to long format
- `pivot` - Pivot DataFrame to wide format
- `stack` - Stack DataFrame columns into rows
- `unstack` - Unstack DataFrame rows into columns

### Data Cleaning
- `strip_strings` - Strip whitespace from string columns
- `to_numeric` - Convert columns to numeric type
- `to_datetime` - Convert columns to datetime type

### Statistical Computations
- `mean` - Compute mean of numeric columns
- `sum` - Compute sum of numeric columns
- `count` - Compute count of non-null values
- `min` - Compute minimum values
- `max` - Compute maximum values

### Window Functions
- `rolling` - Apply rolling window function

### Sampling and Viewing
- `head` - Return first n rows
- `tail` - Return last n rows
- `sample` - Return random sample of rows

## Troubleshooting

### Issue: CSV parsing fails

**Error:** `Failed to read CSV: ParserError`

**Solutions:**
1. Check delimiter: `export PANDAS_TOOL_CSV_DELIMITER=";"`
2. Check encoding: `export PANDAS_TOOL_ENCODING="utf-8"`
3. Verify CSV format and structure

### Issue: Memory errors with large files

**Error:** `MemoryError` or system becomes unresponsive

**Solutions:**
```bash
# Reduce chunk size
export PANDAS_TOOL_CHUNK_SIZE=1000

# Lower CSV size threshold
export PANDAS_TOOL_MAX_CSV_SIZE=100000
```

### Issue: File extension not allowed

**Error:** `Unsupported file type`

**Solution:**
```bash
# Add the extension to allowed list
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx",".json"]'
```

### Issue: Dictionary parsing error

**Error:** Configuration parsing fails for `default_agg`

**Solution:**
```bash
# Use proper JSON object syntax
export PANDAS_TOOL_DEFAULT_AGG='{"numeric":"mean","object":"count"}'

# NOT: {"numeric":mean,"object":count} or numeric:mean,object:count
```

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_file_extensions`

**Solution:**
```bash
# Use proper JSON array syntax
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx"]'

# NOT: [.csv,.xlsx] or .csv,.xlsx
```

### Issue: Encoding errors

**Error:** `UnicodeDecodeError` when reading files

**Solutions:**
1. Try different encoding: `export PANDAS_TOOL_ENCODING="latin-1"`
2. Check file encoding: `file -i filename.csv`
3. Use UTF-8 with BOM: `export PANDAS_TOOL_ENCODING="utf-8-sig"`

### Issue: Performance issues

**Causes:** Large datasets, inefficient chunk sizes

**Solutions:**
1. Increase chunk size: `export PANDAS_TOOL_CHUNK_SIZE=50000`
2. Increase CSV threshold: `export PANDAS_TOOL_MAX_CSV_SIZE=5000000`
3. Use appropriate data types
4. Consider data preprocessing

### Issue: Column not found

**Error:** `Columns not found: ['column_name']`

**Solutions:**
1. Check column names (case-sensitive)
2. Use `head()` operation to inspect data structure
3. Verify data format and headers

## Best Practices

### Performance Optimization

1. **Tune chunk sizes** - Match `chunk_size` to available memory
2. **Set appropriate thresholds** - Use `max_csv_size` to trigger chunking
3. **Use efficient data types** - Convert to appropriate types early
4. **Filter early** - Apply filters before expensive operations
5. **Cache results** - Leverage BaseTool's built-in caching

### Memory Management

1. **Monitor memory usage** - Watch for memory spikes
2. **Use chunked processing** - For files larger than `max_csv_size`
3. **Process in batches** - For multiple large files
4. **Clean up DataFrames** - Delete large objects when done
5. **Use appropriate dtypes** - Avoid object dtypes when possible

### Data Quality

1. **Validate input data** - Check for missing values and outliers
2. **Handle encoding properly** - Use correct encoding for your data
3. **Sanitize data** - Clean data before processing
4. **Use consistent delimiters** - Match delimiter to data format
5. **Handle missing values** - Use `fill_na()` or `dropna()` appropriately

### Security

1. **Limit file extensions** - Only allow necessary formats
2. **Validate file paths** - Prevent directory traversal
3. **Sanitize queries** - Validate filter conditions
4. **Monitor resource usage** - Prevent DoS attacks
5. **Use appropriate permissions** - Limit file system access

### Development vs Production

**Development:**
```bash
PANDAS_TOOL_CHUNK_SIZE=1000
PANDAS_TOOL_MAX_CSV_SIZE=100000
PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx",".json"]'
```

**Production:**
```bash
PANDAS_TOOL_CHUNK_SIZE=50000
PANDAS_TOOL_MAX_CSV_SIZE=5000000
PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS='[".csv",".xlsx"]'
```

### Error Handling

Always wrap pandas operations in try-except blocks:

```python
from aiecs.tools.task_tools.pandas_tool import (
    PandasTool, 
    DataFrameError, 
    InputValidationError,
    ValidationError
)

pandas_tool = PandasTool()

try:
    result = pandas_tool.read_csv(csv_data)
except DataFrameError as e:
    print(f"DataFrame operation failed: {e}")
except InputValidationError as e:
    print(f"Input validation failed: {e}")
except ValidationError as e:
    print(f"Validation failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Related Documentation

- Tool implementation details in the source code
- Pandas documentation: https://pandas.pydata.org/docs/
- NumPy documentation: https://numpy.org/doc/
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Pandas Tool configuration:
- Check the tool source code for implementation details
- Review pandas documentation for specific functionality
- Consult the main aiecs documentation for architecture overview
- Test with small datasets first to isolate configuration vs. data issues
- Monitor memory and performance metrics during processing
