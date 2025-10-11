# Research Tool Configuration Guide

## Overview

The Research Tool provides comprehensive causal inference capabilities using Mill's methods, advanced induction, deduction, and text summarization. It leverages spaCy for natural language processing and statistical analysis for correlation studies. The tool can be configured via environment variables using the `RESEARCH_TOOL_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The Research Tool reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
RESEARCH_TOOL_MAX_WORKERS=16
RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
RESEARCH_TOOL_MAX_TEXT_LENGTH=10000
RESEARCH_TOOL_ALLOWED_SPACY_MODELS=["en_core_web_sm","zh_core_web_sm"]
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.task_tools.research_tool import ResearchTool

# The tool will automatically use the environment variables
research_tool = ResearchTool()
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

from aiecs.tools.task_tools.research_tool import ResearchTool
research_tool = ResearchTool()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance
RESEARCH_TOOL_MAX_WORKERS=32
RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
RESEARCH_TOOL_MAX_TEXT_LENGTH=50000
RESEARCH_TOOL_ALLOWED_SPACY_MODELS=["en_core_web_sm"]
```

**Example `.env.development`:**
```bash
# Development settings - more permissive for testing
RESEARCH_TOOL_MAX_WORKERS=4
RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
RESEARCH_TOOL_MAX_TEXT_LENGTH=10000
RESEARCH_TOOL_ALLOWED_SPACY_MODELS=["en_core_web_sm","zh_core_web_sm"]
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
   # Research Tool Configuration
   
   # Maximum number of worker threads
   RESEARCH_TOOL_MAX_WORKERS=16
   
   # Default spaCy model to use
   RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
   
   # Maximum text length for inputs
   RESEARCH_TOOL_MAX_TEXT_LENGTH=10000
   
   # Allowed spaCy models (JSON array)
   RESEARCH_TOOL_ALLOWED_SPACY_MODELS=["en_core_web_sm","zh_core_web_sm"]
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format complex types correctly**:
   - Strings: Plain text: `en_core_web_sm`
   - Integers: Plain numbers: `16`, `10000`
   - Lists: JSON array format: `["en_core_web_sm","zh_core_web_sm"]`

## Configuration Options

### 1. Max Workers

**Environment Variable:** `RESEARCH_TOOL_MAX_WORKERS`

**Type:** Integer

**Default:** `min(32, (os.cpu_count() or 4) * 2)`

**Description:** Maximum number of worker threads for parallel processing. This affects the concurrency of operations that can be parallelized.

**Common Values:**
- `4` - Conservative (development)
- `8` - Balanced (small servers)
- `16` - High performance (production)
- `32` - Maximum (high-end servers)

**Example:**
```bash
export RESEARCH_TOOL_MAX_WORKERS=16
```

**Performance Note:** Higher values use more CPU cores but may increase memory usage. Set based on available system resources.

### 2. SpaCy Model

**Environment Variable:** `RESEARCH_TOOL_SPACY_MODEL`

**Type:** String

**Default:** `"en_core_web_sm"`

**Description:** Default spaCy model to use for natural language processing. This model is used for all text analysis operations including tokenization, POS tagging, NER, and dependency parsing.

**Available Models:**
- `en_core_web_sm` - English small model (default, fastest)
- `en_core_web_md` - English medium model (better accuracy)
- `en_core_web_lg` - English large model (best accuracy)
- `zh_core_web_sm` - Chinese small model
- `zh_core_web_md` - Chinese medium model

**Example:**
```bash
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_md
```

**Installation Note:** Models must be installed separately:
```bash
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

### 3. Max Text Length

**Environment Variable:** `RESEARCH_TOOL_MAX_TEXT_LENGTH`

**Type:** Integer

**Default:** `10_000`

**Description:** Maximum text length in characters for input processing. This prevents memory issues with extremely long texts and ensures reasonable processing times.

**Common Values:**
- `5_000` - Short texts (summaries, abstracts)
- `10_000` - Standard texts (articles, reports)
- `50_000` - Long texts (documents, books)
- `100_000` - Very long texts (research papers)

**Example:**
```bash
export RESEARCH_TOOL_MAX_TEXT_LENGTH=50000
```

**Memory Note:** Longer texts use more memory and processing time. Adjust based on available system resources.

### 4. Allowed SpaCy Models

**Environment Variable:** `RESEARCH_TOOL_ALLOWED_SPACY_MODELS`

**Type:** List[str]

**Default:** `["en_core_web_sm", "zh_core_web_sm"]`

**Description:** List of allowed spaCy models that can be used. This is a security feature that prevents loading of unauthorized or potentially malicious models.

**Format:** JSON array string with double quotes

**Common Configurations:**
- **English only:** `["en_core_web_sm"]`
- **Multilingual:** `["en_core_web_sm", "zh_core_web_sm"]`
- **High accuracy:** `["en_core_web_lg", "zh_core_web_md"]`

**Example:**
```bash
# English only
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm"]'

# Multilingual support
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm"]'
```

**Security Note:** Only include models that are actually needed and have been verified as safe.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set custom processing parameters
export RESEARCH_TOOL_MAX_WORKERS=16
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_md
export RESEARCH_TOOL_MAX_TEXT_LENGTH=50000

# Run your application
python app.py
```

### Example 2: High-Performance Configuration

```bash
# Optimized for large-scale processing
export RESEARCH_TOOL_MAX_WORKERS=32
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_lg
export RESEARCH_TOOL_MAX_TEXT_LENGTH=100000
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_lg"]'
```

### Example 3: Multilingual Configuration

```bash
# Support for multiple languages
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm","de_core_news_sm"]'
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.task_tools.research_tool import ResearchTool

# Initialize with custom configuration
research_tool = ResearchTool(config={
    'max_workers': 16,
    'spacy_model': 'en_core_web_md',
    'max_text_length': 50000,
    'allowed_spacy_models': ['en_core_web_sm', 'en_core_web_md']
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
export RESEARCH_TOOL_MAX_WORKERS=8
```

```python
# Override for specific instance
research_tool = ResearchTool(config={
    'spacy_model': 'en_core_web_lg',  # This overrides the environment variable
    'max_workers': 16                 # This overrides the environment variable
})
```

## Configuration Priority

When the Research Tool is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `RESEARCH_TOOL_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export RESEARCH_TOOL_MAX_WORKERS=16
export RESEARCH_TOOL_MAX_TEXT_LENGTH=50000
```

### List Values

Lists must be provided as JSON arrays with double quotes:

```bash
# Correct
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm"]'

# Incorrect (will not parse)
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS="en_core_web_sm,zh_core_web_sm"
```

**Important:** Use single quotes for the shell, double quotes for JSON:
```bash
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm"]'
#                                      ^                    ^
#                                      Single quotes for shell
#                                         ^      ^
#                                         Double quotes for JSON
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `max_workers` must be a positive integer
- `spacy_model` must be a non-empty string
- `max_text_length` must be a positive integer
- `allowed_spacy_models` must be a list of strings

### Runtime Validation

When processing data, the tool validates:

1. **SpaCy model availability** - Model must be installed and loadable
2. **Model authorization** - Model must be in `allowed_spacy_models` list
3. **Text length limits** - Input text must not exceed `max_text_length`
4. **Data structure** - Input data must be valid for each operation
5. **Statistical requirements** - Sufficient data for correlation analysis

## Operations Supported

The Research Tool supports comprehensive causal inference and text analysis operations:

### Mill's Methods for Causal Inference

#### Method of Agreement
- `mill_agreement` - Identify common factors in positive cases
- Finds attributes present in all cases with positive outcomes
- Useful for identifying necessary conditions

#### Method of Difference
- `mill_difference` - Identify factors present in positive but absent in negative cases
- Compares single positive and negative case
- Useful for identifying sufficient conditions

#### Joint Method
- `mill_joint` - Combine agreement and difference methods
- Identifies causal factors by analyzing both positive and negative cases
- Most robust method for causal inference

#### Method of Residues
- `mill_residues` - Identify residual causes after accounting for known causes
- Removes known causal factors to find remaining causes
- Useful for complex causal analysis

#### Method of Concomitant Variations
- `mill_concomitant` - Analyze correlation between factor and effect variations
- Uses statistical correlation analysis
- Provides quantitative causal evidence

### Advanced Analysis Operations

#### Induction
- `induction` - Generalize patterns from examples using spaCy-based clustering
- Extracts common noun phrases and verbs
- Identifies recurring patterns in text data

#### Deduction
- `deduction` - Validate conclusions using spaCy dependency parsing
- Checks logical consistency between premises and conclusions
- Validates reasoning chains

#### Text Summarization
- `summarize` - Summarize text using spaCy sentence ranking
- Extracts key sentences based on keyword frequency
- Produces concise summaries of long texts

## Troubleshooting

### Issue: SpaCy model not found

**Error:** `OSError: [E050] Can't find model 'en_core_web_sm'`

**Solutions:**
1. Install the model: `python -m spacy download en_core_web_sm`
2. Check model name: `export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm`
3. Verify installation: `python -c "import spacy; spacy.load('en_core_web_sm')"`

### Issue: Model not in allowed list

**Error:** `Invalid spaCy model 'model_name', expected ['allowed_models']`

**Solution:**
```bash
# Add the model to allowed list
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","your_model"]'
```

### Issue: Memory errors with large texts

**Error:** `MemoryError` or system becomes unresponsive

**Solutions:**
```bash
# Reduce text length limit
export RESEARCH_TOOL_MAX_TEXT_LENGTH=5000

# Use smaller spaCy model
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
```

### Issue: Slow processing

**Causes:** Large texts, complex models, insufficient workers

**Solutions:**
```bash
# Increase worker count
export RESEARCH_TOOL_MAX_WORKERS=32

# Use faster model
export RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm

# Reduce text length
export RESEARCH_TOOL_MAX_TEXT_LENGTH=10000
```

### Issue: Correlation analysis fails

**Error:** `Failed to process mill_concomitant`

**Solutions:**
1. Ensure sufficient data points (minimum 2 cases)
2. Check data types (numeric values required)
3. Verify factor and effect column names exist
4. Use appropriate statistical methods

### Issue: List parsing error

**Error:** Configuration parsing fails for `allowed_spacy_models`

**Solution:**
```bash
# Use proper JSON array syntax
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm"]'

# NOT: [en_core_web_sm,zh_core_web_sm] or en_core_web_sm,zh_core_web_sm
```

### Issue: Text too long

**Error:** Text exceeds maximum length limit

**Solutions:**
```bash
# Increase text length limit
export RESEARCH_TOOL_MAX_TEXT_LENGTH=50000

# Or preprocess text to reduce length
```

## Best Practices

### Performance Optimization

1. **Model Selection** - Choose appropriate spaCy model for your needs:
   - `en_core_web_sm` - Fastest, good for basic tasks
   - `en_core_web_md` - Balanced speed and accuracy
   - `en_core_web_lg` - Best accuracy, slower processing

2. **Worker Configuration** - Match worker count to available CPU cores:
   - Development: 4-8 workers
   - Production: 16-32 workers
   - High-end: 32+ workers

3. **Text Length Management** - Set appropriate limits:
   - Short texts: 5,000 characters
   - Standard texts: 10,000 characters
   - Long texts: 50,000+ characters

4. **Memory Management** - Monitor memory usage:
   - Use smaller models for memory-constrained environments
   - Process texts in batches for very long documents
   - Clean up spaCy models when done

### Causal Inference Best Practices

1. **Data Quality** - Ensure high-quality input data:
   - Consistent attribute naming
   - Clear outcome definitions
   - Sufficient sample sizes

2. **Method Selection** - Choose appropriate Mill's method:
   - **Agreement**: When you have multiple positive cases
   - **Difference**: When comparing single positive/negative cases
   - **Joint**: For most robust causal inference
   - **Residues**: When you have known causes to exclude
   - **Concomitant**: For quantitative correlation analysis

3. **Statistical Validation** - Always validate results:
   - Check correlation significance (p-values)
   - Consider multiple causal factors
   - Validate with additional data

### Text Analysis Best Practices

1. **Preprocessing** - Clean and prepare text data:
   - Remove irrelevant content
   - Standardize formatting
   - Handle special characters

2. **Model Selection** - Choose appropriate spaCy model:
   - Match language of your text
   - Consider accuracy vs. speed trade-offs
   - Use domain-specific models when available

3. **Result Interpretation** - Understand tool limitations:
   - Statistical methods provide correlations, not causation
   - Text analysis is probabilistic, not deterministic
   - Results should be validated with domain expertise

### Security

1. **Model Validation** - Only use trusted spaCy models:
   - Download from official spaCy repository
   - Verify model integrity
   - Keep models updated

2. **Input Sanitization** - Validate input data:
   - Check text length limits
   - Validate data structures
   - Handle malformed inputs gracefully

3. **Resource Limits** - Prevent resource exhaustion:
   - Set appropriate worker limits
   - Monitor memory usage
   - Implement timeout mechanisms

### Development vs Production

**Development:**
```bash
RESEARCH_TOOL_MAX_WORKERS=4
RESEARCH_TOOL_SPACY_MODEL=en_core_web_sm
RESEARCH_TOOL_MAX_TEXT_LENGTH=10000
RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","zh_core_web_sm"]'
```

**Production:**
```bash
RESEARCH_TOOL_MAX_WORKERS=32
RESEARCH_TOOL_SPACY_MODEL=en_core_web_md
RESEARCH_TOOL_MAX_TEXT_LENGTH=50000
RESEARCH_TOOL_ALLOWED_SPACY_MODELS='["en_core_web_sm","en_core_web_md"]'
```

### Error Handling

Always wrap research operations in try-except blocks:

```python
from aiecs.tools.task_tools.research_tool import ResearchTool, ResearchToolError, FileOperationError

research_tool = ResearchTool()

try:
    result = research_tool.mill_agreement(cases)
except FileOperationError as e:
    print(f"Research operation failed: {e}")
except ResearchToolError as e:
    print(f"Research tool error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## SpaCy Model Installation

### Installing Models

```bash
# Install English models
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_md
python -m spacy download en_core_web_lg

# Install Chinese models
python -m spacy download zh_core_web_sm
python -m spacy download zh_core_web_md

# Install German models
python -m spacy download de_core_news_sm
python -m spacy download de_core_news_md
```

### Verifying Installation

```python
import spacy

# Test model loading
try:
    nlp = spacy.load("en_core_web_sm")
    print("Model loaded successfully")
except OSError:
    print("Model not found, install with: python -m spacy download en_core_web_sm")
```

### Model Information

```python
import spacy

# Get model information
nlp = spacy.load("en_core_web_sm")
print(f"Model: {nlp.meta['name']}")
print(f"Version: {nlp.meta['version']}")
print(f"Language: {nlp.meta['lang']}")
print(f"Pipeline: {nlp.pipe_names}")
```

## Related Documentation

- Tool implementation details in the source code
- SpaCy documentation: https://spacy.io/
- Mill's Methods: https://en.wikipedia.org/wiki/Mill%27s_methods
- Main aiecs documentation for architecture overview

## Support

For issues or questions about Research Tool configuration:
- Check the tool source code for implementation details
- Review spaCy documentation for NLP functionality
- Consult the main aiecs documentation for architecture overview
- Test with small datasets first to isolate configuration vs. data issues
- Monitor memory and CPU usage during processing
- Validate spaCy model installation and compatibility
