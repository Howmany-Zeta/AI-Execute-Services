# Classifier Tool Configuration Guide

## Overview

The Classifier Tool provides text classification, NLP operations, and analysis capabilities. It supports multiple languages (English and Chinese) and can be configured via environment variables using the `CLASSIFIER_TOOL_` prefix or through programmatic configuration.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Classifier Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
CLASSIFIER_TOOL_MAX_WORKERS=16
CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=3600
CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=10
CLASSIFIER_TOOL_MAX_TEXT_LENGTH=10000
CLASSIFIER_TOOL_SPACY_MODEL_EN=en_core_web_sm
CLASSIFIER_TOOL_SPACY_MODEL_ZH=zh_core_web_sm
CLASSIFIER_TOOL_ALLOWED_MODELS=["en_core_web_sm","zh_core_web_sm"]
CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true
CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=100
CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=60
CLASSIFIER_TOOL_USE_RAKE_FOR_ENGLISH=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.classfire_tool import ClassifierTool

# The tool will automatically use the environment variables
classifier = ClassifierTool()
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

from aiecs.tools.task_tools.classfire_tool import ClassifierTool
classifier = ClassifierTool()
```

**Example `.env.production`:**
```bash
# Production settings - stricter limits and better models
CLASSIFIER_TOOL_MAX_WORKERS=32
CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true
CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=100
CLASSIFIER_TOOL_SPACY_MODEL_EN=en_core_web_md
CLASSIFIER_TOOL_MAX_TEXT_LENGTH=8000
```

**Example `.env.development`:**
```bash
# Development settings - relaxed limits for testing
CLASSIFIER_TOOL_MAX_WORKERS=4
CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=false
CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=300
CLASSIFIER_TOOL_SPACY_MODEL_EN=en_core_web_sm
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
   # Classifier Tool Configuration
   
   # Maximum number of worker threads
   CLASSIFIER_TOOL_MAX_WORKERS=16
   
   # Cache settings (in seconds)
   CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=3600
   CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=10
   
   # Text processing limits
   CLASSIFIER_TOOL_MAX_TEXT_LENGTH=10000
   
   # SpaCy models
   CLASSIFIER_TOOL_SPACY_MODEL_EN=en_core_web_sm
   CLASSIFIER_TOOL_SPACY_MODEL_ZH=zh_core_web_sm
   
   # Security settings
   CLASSIFIER_TOOL_ALLOWED_MODELS=["en_core_web_sm","zh_core_web_sm"]
   
   # Rate limiting
   CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true
   CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=100
   CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=60
   
   # Feature flags
   CLASSIFIER_TOOL_USE_RAKE_FOR_ENGLISH=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Booleans: `true`, `false`, `1`, `0`, `yes`, `no`
   - Lists: Use JSON array format with double quotes: `["item1","item2"]`
   - Numbers: Plain integers or floats: `100`, `3600`

## Configuration Options

### 1. Max Workers

**Environment Variable:** `CLASSIFIER_TOOL_MAX_WORKERS`

**Type:** Integer

**Default:** `min(32, (os.cpu_count() or 4) * 2)`

**Description:** Maximum number of worker threads for parallel processing. The default dynamically adjusts based on CPU count.

**Example:**
```bash
export CLASSIFIER_TOOL_MAX_WORKERS=16
```

### 2. Pipeline Cache TTL

**Environment Variable:** `CLASSIFIER_TOOL_PIPELINE_CACHE_TTL`

**Type:** Integer

**Default:** `3600` (1 hour)

**Description:** Time-to-live for pipeline cache in seconds. Pipelines are expensive to load, so caching improves performance.

**Example:**
```bash
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=7200  # 2 hours
```

### 3. Pipeline Cache Size

**Environment Variable:** `CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE`

**Type:** Integer

**Default:** `10`

**Description:** Maximum number of pipeline entries to cache. Each pipeline can consume significant memory.

**Example:**
```bash
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=5
```

### 4. Max Text Length

**Environment Variable:** `CLASSIFIER_TOOL_MAX_TEXT_LENGTH`

**Type:** Integer

**Default:** `10000` characters

**Description:** Maximum allowed text length for processing. This is a security and performance constraint.

**Example:**
```bash
export CLASSIFIER_TOOL_MAX_TEXT_LENGTH=5000
```

### 5. SpaCy Model (English)

**Environment Variable:** `CLASSIFIER_TOOL_SPACY_MODEL_EN`

**Type:** String

**Default:** `"en_core_web_sm"`

**Description:** SpaCy model to use for English text processing.

**Available Models:**
- `en_core_web_sm` - Small model (default, faster)
- `en_core_web_md` - Medium model (more accurate)
- `en_core_web_lg` - Large model (most accurate, slower)

**Example:**
```bash
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_md"
```

### 6. SpaCy Model (Chinese)

**Environment Variable:** `CLASSIFIER_TOOL_SPACY_MODEL_ZH`

**Type:** String

**Default:** `"zh_core_web_sm"`

**Description:** SpaCy model to use for Chinese text processing.

**Available Models:**
- `zh_core_web_sm` - Small model (default)
- `zh_core_web_md` - Medium model
- `zh_core_web_lg` - Large model

**Example:**
```bash
export CLASSIFIER_TOOL_SPACY_MODEL_ZH="zh_core_web_md"
```

### 7. Allowed Models

**Environment Variable:** `CLASSIFIER_TOOL_ALLOWED_MODELS`

**Type:** List[str]

**Default:** `["en_core_web_sm", "zh_core_web_sm"]`

**Description:** List of allowed spaCy models that can be loaded. This is a security feature to prevent arbitrary model loading.

**Format:** JSON array string

**Example:**
```bash
export CLASSIFIER_TOOL_ALLOWED_MODELS='["en_core_web_sm","en_core_web_md","zh_core_web_sm"]'
```

### 8. Rate Limit Enabled

**Environment Variable:** `CLASSIFIER_TOOL_RATE_LIMIT_ENABLED`

**Type:** Boolean

**Default:** `true`

**Description:** Enable or disable rate limiting for API requests.

**Format:** Pydantic accepts various boolean representations: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`

**Example:**
```bash
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=false
```

### 9. Rate Limit Requests

**Environment Variable:** `CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS`

**Type:** Integer

**Default:** `100`

**Description:** Maximum number of requests allowed per rate limit window.

**Example:**
```bash
export CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=200
```

### 10. Rate Limit Window

**Environment Variable:** `CLASSIFIER_TOOL_RATE_LIMIT_WINDOW`

**Type:** Integer

**Default:** `60` seconds

**Description:** Time window (in seconds) for rate limiting.

**Example:**
```bash
export CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=120  # 2 minutes
```

### 11. Use RAKE for English

**Environment Variable:** `CLASSIFIER_TOOL_USE_RAKE_FOR_ENGLISH`

**Type:** Boolean

**Default:** `true`

**Description:** Use RAKE (Rapid Automatic Keyword Extraction) algorithm for English keyword extraction. If disabled, falls back to spaCy-based extraction.

**Example:**
```bash
export CLASSIFIER_TOOL_USE_RAKE_FOR_ENGLISH=false
```

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Configure for high-performance processing
export CLASSIFIER_TOOL_MAX_WORKERS=32
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=20
export CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=500

# Use larger models for better accuracy
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_md"

# Run your application
python app.py
```

### Example 2: Development Environment

```bash
# Disable rate limiting for testing
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=false

# Use smaller cache for memory-constrained systems
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=3
export CLASSIFIER_TOOL_MAX_WORKERS=4

# Shorter cache TTL for rapid iteration
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=300  # 5 minutes
```

### Example 3: Production Environment

```bash
# Strict rate limiting
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true
export CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=100
export CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=60

# Optimized performance
export CLASSIFIER_TOOL_MAX_WORKERS=24
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=15
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=7200

# Security: limit text length
export CLASSIFIER_TOOL_MAX_TEXT_LENGTH=8000
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.classfire_tool import ClassifierTool

# Initialize with custom configuration
classifier = ClassifierTool(config={
    'max_workers': 16,
    'pipeline_cache_ttl': 3600,
    'pipeline_cache_size': 10,
    'max_text_length': 5000,
    'spacy_model_en': 'en_core_web_md',
    'spacy_model_zh': 'zh_core_web_sm',
    'rate_limit_enabled': True,
    'rate_limit_requests': 200,
    'rate_limit_window': 60,
    'use_rake_for_english': True
})
```

### Example 5: Mixed Configuration

```bash
# Set environment defaults
export CLASSIFIER_TOOL_MAX_WORKERS=20
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true
```

```python
# Override specific settings programmatically
classifier = ClassifierTool(config={
    'rate_limit_enabled': False,  # Override env var
    'spacy_model_en': 'en_core_web_lg'  # Use larger model
})
```

## Configuration Priority

Configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `CLASSIFIER_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### Boolean Values

Pydantic accepts multiple boolean representations:
- **True:** `true`, `1`, `yes`, `on`, `True`, `TRUE`
- **False:** `false`, `0`, `no`, `off`, `False`, `FALSE`

Example:
```bash
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=yes  # Parsed as True
```

### List Values

Lists must be provided as JSON array strings:

```bash
# Correct
export CLASSIFIER_TOOL_ALLOWED_MODELS='["en_core_web_sm","zh_core_web_sm"]'

# Incorrect (will not parse)
export CLASSIFIER_TOOL_ALLOWED_MODELS="en_core_web_sm,zh_core_web_sm"
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export CLASSIFIER_TOOL_MAX_WORKERS=16
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=3600
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- Integer fields must contain valid integers
- Boolean fields must contain valid boolean representations
- List fields must contain valid JSON arrays
- String fields accept any string value

### Custom Validation

The tool includes custom validators for:

- **max_text_length**: Applied to all text inputs
- **allowed_models**: Checked when loading models
- **rate_limit_requests**: Must be positive

### Security Validation

Text inputs are validated for:
- Maximum length constraints
- Potentially malicious SQL injection patterns
- Other security threats

## Performance Tuning

### Memory Optimization

For memory-constrained environments:
```bash
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=3
export CLASSIFIER_TOOL_MAX_WORKERS=4
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_sm"
```

### Speed Optimization

For high-throughput environments:
```bash
export CLASSIFIER_TOOL_MAX_WORKERS=32
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=20
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=7200
```

### Accuracy Optimization

For maximum accuracy (at the cost of speed/memory):
```bash
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_lg"
export CLASSIFIER_TOOL_SPACY_MODEL_ZH="zh_core_web_lg"
export CLASSIFIER_TOOL_ALLOWED_MODELS='["en_core_web_lg","zh_core_web_lg"]'
```

## Model Installation

Before using specific models, ensure they are installed:

```bash
# Install spaCy models
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
python -m spacy download en_core_web_lg
python -m spacy download zh_core_web_sm
python -m spacy download zh_core_web_md
python -m spacy download zh_core_web_lg
```

## Troubleshooting

### Issue: Model not found

**Error:** `OSError: [E050] Can't find model 'en_core_web_md'`

**Solution:**
```bash
# Download the required model
python -m spacy download en_core_web_md

# Or set to an installed model
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_sm"
```

### Issue: Rate limit exceeded

**Error:** `Rate limit exceeded. Please try again later.`

**Solution:**
```bash
# Increase rate limits
export CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=500
export CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=60

# Or disable for testing
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=false
```

### Issue: Out of memory

**Cause:** Too many cached pipelines or workers

**Solution:**
```bash
# Reduce cache and workers
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=3
export CLASSIFIER_TOOL_MAX_WORKERS=4

# Use smaller models
export CLASSIFIER_TOOL_SPACY_MODEL_EN="en_core_web_sm"
```

### Issue: Boolean environment variable not working

**Cause:** Incorrect boolean format

**Solution:**
```bash
# Use recognized boolean values
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=true  # or false, 1, 0, yes, no

# NOT: "True", "FALSE" (with quotes can cause issues)
```

### Issue: List parsing error

**Cause:** Invalid JSON format for list values

**Solution:**
```bash
# Use proper JSON array syntax
export CLASSIFIER_TOOL_ALLOWED_MODELS='["en_core_web_sm","zh_core_web_sm"]'

# Make sure to use double quotes inside the array
# Single quotes for the shell, double quotes for JSON
```

## Best Practices

1. **Resource Management:**
   - Set `max_workers` to 2x CPU count for I/O-bound tasks
   - Limit `pipeline_cache_size` based on available memory
   - Use appropriate `pipeline_cache_ttl` for your workload

2. **Security:**
   - Keep `rate_limit_enabled=true` in production
   - Restrict `allowed_models` to only necessary models
   - Set conservative `max_text_length` limits

3. **Performance:**
   - Use smaller models (`_sm`) for faster processing
   - Use larger models (`_lg`) when accuracy is critical
   - Tune cache settings based on usage patterns

4. **Language Support:**
   - The tool auto-detects language if not specified
   - Pre-load models for languages you frequently use
   - Consider separate instances for different languages

## Operations Supported

The Classifier Tool supports the following operations:

- **classify**: Sentiment classification
- **tokenize**: Text tokenization
- **pos_tag**: Part-of-speech tagging
- **ner**: Named entity recognition
- **lemmatize**: Token lemmatization
- **dependency_parse**: Dependency parsing
- **keyword_extract**: Keyword/phrase extraction
- **summarize**: Text summarization
- **batch_process**: Batch processing of multiple texts

## Related Documentation

- Tool implementation details in the source code
- NLP best practices in `TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md`
- SpaCy documentation: https://spacy.io/usage

## Support

For issues or questions about Classifier Tool configuration:
- Check the tool source code for implementation details
- Review spaCy documentation for model-specific information
- Consult the main documentation for architecture overview

