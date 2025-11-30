# AI Document Orchestrator Configuration Guide

## Overview

The AI Document Orchestrator is a powerful tool that coordinates document parsing with AI analysis, manages AI provider interactions, and handles complex document processing workflows. It provides intelligent content analysis and extraction capabilities, integrating with DocumentParserTool for document parsing and various AI providers for content analysis. The tool supports multiple processing modes (summarize, extract_info, analyze, translate, classify, answer_questions, custom), multiple AI providers (OpenAI, Vertex AI, XAI, Local), and both synchronous and asynchronous processing. The tool can be configured via environment variables using the `AI_DOC_ORCHESTRATOR_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The AI Document Orchestrator reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=4000
AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=5
AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
AI_DOC_ORCHESTRATOR_MAX_TOKENS=2000
AI_DOC_ORCHESTRATOR_TIMEOUT=60
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator

# The tool will automatically use the environment variables
orchestrator = AIDocumentOrchestrator()
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

from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
orchestrator = AIDocumentOrchestrator()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance and reliability
AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=8000
AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=10
AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
AI_DOC_ORCHESTRATOR_MAX_TOKENS=4000
AI_DOC_ORCHESTRATOR_TIMEOUT=120
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000
AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2
AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.3
AI_DOC_ORCHESTRATOR_MAX_TOKENS=1000
AI_DOC_ORCHESTRATOR_TIMEOUT=30
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
   # AI Document Orchestrator Configuration
   
   # Default AI provider to use
   AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
   
   # Maximum chunk size for AI processing
   AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=4000
   
   # Maximum concurrent AI requests
   AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=5
   
   # Default temperature for AI model
   AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
   
   # Maximum tokens for AI response
   AI_DOC_ORCHESTRATOR_MAX_TOKENS=2000
   
   # Timeout in seconds for AI operations
   AI_DOC_ORCHESTRATOR_TIMEOUT=60
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `openai`, `vertex_ai`
   - Integers: Plain numbers: `4000`, `5`, `2000`, `60`
   - Floats: Decimal numbers: `0.1`, `0.3`

## Configuration Options

### 1. Default AI Provider

**Environment Variable:** `AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER`

**Type:** String

**Default:** `"openai"`

**Description:** Default AI provider to use for document processing operations. This provider is used when no specific provider is specified in the processing request.

**Supported Providers:**
- `openai` - OpenAI API (default)
- `vertex_ai` - Google Vertex AI
- `xai` - XAI (xAI)
- `local` - Local AI model

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=vertex_ai
```

**Provider Note:** Ensure the selected provider is properly configured with API keys and credentials.

### 2. Max Chunk Size

**Environment Variable:** `AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE`

**Type:** Integer

**Default:** `4000`

**Description:** Maximum chunk size for AI processing. Documents larger than this size will be chunked before being sent to AI providers.

**Common Values:**
- `2000` - Small chunks (faster processing, more API calls)
- `4000` - Default chunks (balanced)
- `8000` - Large chunks (fewer API calls, more memory)
- `16000` - Very large chunks (maximum efficiency)

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=8000
```

**Chunking Note:** Larger chunks reduce API calls but may hit token limits. Smaller chunks provide better granularity but increase costs.

### 3. Max Concurrent Requests

**Environment Variable:** `AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS`

**Type:** Integer

**Default:** `5`

**Description:** Maximum number of concurrent AI requests that can be processed simultaneously. This controls the parallelism of batch processing operations.

**Common Values:**
- `2` - Conservative (low resource usage)
- `5` - Default (balanced)
- `10` - Aggressive (high throughput)
- `20` - Maximum (requires high resources)

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=10
```

**Concurrency Note:** Higher values increase throughput but may hit API rate limits or resource constraints.

### 4. Default Temperature

**Environment Variable:** `AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE`

**Type:** Float

**Default:** `0.1`

**Description:** Default temperature setting for AI models. Controls the randomness and creativity of AI responses.

**Temperature Ranges:**
- `0.0` - Deterministic (most focused)
- `0.1` - Low creativity (default, good for factual tasks)
- `0.3` - Moderate creativity
- `0.7` - High creativity
- `1.0` - Maximum creativity

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.3
```

**Temperature Note:** Lower values are better for factual extraction, higher values for creative tasks.

### 5. Max Tokens

**Environment Variable:** `AI_DOC_ORCHESTRATOR_MAX_TOKENS`

**Type:** Integer

**Default:** `2000`

**Description:** Maximum number of tokens for AI response generation. This limits the length of AI-generated content.

**Common Values:**
- `1000` - Short responses
- `2000` - Default responses
- `4000` - Long responses
- `8000` - Very long responses

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=4000
```

**Token Note:** Higher values allow longer responses but increase costs and processing time.

### 6. Timeout

**Environment Variable:** `AI_DOC_ORCHESTRATOR_TIMEOUT`

**Type:** Integer

**Default:** `60`

**Description:** Timeout in seconds for AI operations. Operations that exceed this timeout will be cancelled.

**Common Values:**
- `30` - Fast timeout (quick operations)
- `60` - Default timeout (balanced)
- `120` - Long timeout (complex operations)
- `300` - Very long timeout (batch operations)

**Example:**
```bash
export AI_DOC_ORCHESTRATOR_TIMEOUT=120
```

**Timeout Note:** Increase for complex documents or slow AI providers.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic AI processing parameters
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=4000
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=5
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=2000
export AI_DOC_ORCHESTRATOR_TIMEOUT=60

# Run your application
python app.py
```

### Example 2: High-Performance Configuration

```bash
# Optimized for high throughput
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=8000
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=10
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=4000
export AI_DOC_ORCHESTRATOR_TIMEOUT=120
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.3
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=1000
export AI_DOC_ORCHESTRATOR_TIMEOUT=30
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator

# Initialize with custom configuration
orchestrator = AIDocumentOrchestrator(config={
    'default_ai_provider': 'openai',
    'max_chunk_size': 4000,
    'max_concurrent_requests': 5,
    'default_temperature': 0.1,
    'max_tokens': 2000,
    'timeout': 60
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=4000
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
```

```python
# Override for specific instance
orchestrator = AIDocumentOrchestrator(config={
    'max_chunk_size': 8000,  # This overrides the environment variable
    'default_temperature': 0.3  # This overrides the environment variable
})
```

## Configuration Priority

When the AI Document Orchestrator is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `AI_DOC_ORCHESTRATOR_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=vertex_ai
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=4000
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=5
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=2000
export AI_DOC_ORCHESTRATOR_TIMEOUT=60
```

### Float Values

Floats should be provided as decimal strings:

```bash
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
export AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.3
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `default_ai_provider` must be a valid provider string
- `max_chunk_size` must be a positive integer
- `max_concurrent_requests` must be a positive integer
- `default_temperature` must be a float between 0.0 and 2.0
- `max_tokens` must be a positive integer
- `timeout` must be a positive integer

### Runtime Validation

When processing documents, the tool validates:

1. **AI Provider availability** - Selected provider must be configured
2. **Chunk size limits** - Content must fit within chunk size
3. **Concurrency limits** - Request count must not exceed limits
4. **Token limits** - Responses must not exceed token limits
5. **Timeout limits** - Operations must complete within timeout

## Processing Modes

The AI Document Orchestrator supports various processing modes:

### Basic Modes
- **Summarize** - Create concise document summaries
- **Extract Info** - Extract specific information from documents
- **Analyze** - Provide thorough document analysis
- **Translate** - Translate document content
- **Classify** - Classify documents into categories
- **Answer Questions** - Answer questions based on document content

### Advanced Modes
- **Custom** - Use custom processing templates and prompts

## AI Providers

### Supported Providers
- **OpenAI** - OpenAI API integration
- **Vertex AI** - Google Cloud Vertex AI
- **XAI** - xAI integration
- **Local** - Local AI model integration

### Provider Configuration

Each provider requires specific configuration:

**OpenAI:**
```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_ORG_ID=your-org-id  # Optional
```

**Vertex AI:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
export GOOGLE_CLOUD_PROJECT=your-project-id
```

**XAI:**
```bash
export XAI_API_KEY=your-api-key
```

**Local:**
```bash
export LOCAL_MODEL_PATH=path/to/model
export LOCAL_MODEL_TYPE=llama2  # or other model type
```

## Operations Supported

The AI Document Orchestrator supports comprehensive document processing operations:

### Basic Processing
- `process_document` - Process a single document with AI
- `analyze_document` - Perform AI-first document analysis
- `batch_process_documents` - Process multiple documents in batch

### Async Processing
- `process_document_async` - Async version of document processing
- `_batch_process_async` - Async batch processing with concurrency control

### Custom Processing
- `create_custom_processor` - Create custom processing functions
- `get_processing_stats` - Get processing statistics

### Document Integration
- Integration with DocumentParserTool for document parsing
- Support for various document formats (PDF, DOCX, TXT, HTML, etc.)
- Intelligent content chunking and preparation

### AI Integration
- Integration with AIECS client for AI operations
- Support for multiple AI providers
- Intelligent prompt templating and formatting
- Response validation and post-processing

## Troubleshooting

### Issue: AI Provider not available

**Error:** `AIProviderError` when calling AI providers

**Solutions:**
```bash
# Check provider configuration
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai

# Verify API keys
export OPENAI_API_KEY=your-valid-api-key

# Test with local provider
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
```

### Issue: Document parsing fails

**Error:** `ProcessingError` during document parsing

**Solutions:**
1. Check DocumentParserTool availability
2. Verify document format support
3. Check file accessibility and permissions
4. Validate document content

### Issue: Timeout errors

**Error:** Operations timeout before completion

**Solutions:**
```bash
# Increase timeout
export AI_DOC_ORCHESTRATOR_TIMEOUT=120

# Reduce chunk size
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000

# Reduce concurrent requests
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2
```

### Issue: Memory issues

**Error:** Out of memory during processing

**Solutions:**
```bash
# Reduce chunk size
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000

# Reduce concurrent requests
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2

# Reduce max tokens
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=1000
```

### Issue: Concurrency limits

**Error:** Too many concurrent requests

**Solutions:**
```bash
# Reduce concurrent requests
export AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2

# Check API rate limits
# Adjust based on provider limits
```

### Issue: Token limit exceeded

**Error:** Response exceeds token limits

**Solutions:**
```bash
# Reduce max tokens
export AI_DOC_ORCHESTRATOR_MAX_TOKENS=1000

# Reduce chunk size
export AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000

# Use more specific prompts
```

### Issue: Invalid AI provider

**Error:** Unsupported AI provider

**Solutions:**
```bash
# Use supported provider
export AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai

# Check provider availability
# Verify provider configuration
```

## Best Practices

### Performance Optimization

1. **Chunk Size Management** - Balance chunk size for optimal processing
2. **Concurrency Control** - Set appropriate concurrent request limits
3. **Provider Selection** - Choose providers based on task requirements
4. **Timeout Configuration** - Set reasonable timeouts for operations
5. **Token Management** - Optimize token usage for cost efficiency

### Error Handling

1. **Graceful Degradation** - Handle AI provider failures gracefully
2. **Retry Logic** - Implement retry for transient failures
3. **Fallback Strategies** - Provide fallback processing methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **API Key Management** - Secure storage of API keys
2. **Content Validation** - Validate document content before processing
3. **Access Control** - Control access to AI providers
4. **Data Privacy** - Ensure data privacy in AI processing
5. **Audit Logging** - Log processing activities for compliance

### Resource Management

1. **Memory Usage** - Monitor memory consumption during processing
2. **API Rate Limits** - Respect provider rate limits
3. **Cost Management** - Monitor and control AI processing costs
4. **Processing Time** - Set reasonable timeouts
5. **Cleanup** - Clean up resources after processing

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=2000
AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=2
AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.3
AI_DOC_ORCHESTRATOR_MAX_TOKENS=1000
AI_DOC_ORCHESTRATOR_TIMEOUT=30
```

**Production:**
```bash
AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DOC_ORCHESTRATOR_MAX_CHUNK_SIZE=8000
AI_DOC_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=10
AI_DOC_ORCHESTRATOR_DEFAULT_TEMPERATURE=0.1
AI_DOC_ORCHESTRATOR_MAX_TOKENS=4000
AI_DOC_ORCHESTRATOR_TIMEOUT=120
```

### Error Handling

Always wrap AI processing operations in try-except blocks:

```python
from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator, AIDocumentOrchestratorError, AIProviderError, ProcessingError

orchestrator = AIDocumentOrchestrator()

try:
    result = orchestrator.process_document(
        source="document.pdf",
        processing_mode="summarize",
        ai_provider="openai"
    )
except AIProviderError as e:
    print(f"AI provider error: {e}")
except ProcessingError as e:
    print(f"Processing error: {e}")
except AIDocumentOrchestratorError as e:
    print(f"Orchestrator error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv

# Install AI provider dependencies
pip install openai google-cloud-aiplatform

# Install document processing dependencies
pip install python-docx openpyxl python-pptx
```

### Optional Dependencies

```bash
# For advanced AI providers
pip install anthropic cohere

# For local AI models
pip install transformers torch

# For enhanced document processing
pip install PyPDF2 pdfplumber

# For async processing
pip install aiohttp asyncio
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import openai
    import asyncio
    print("Core dependencies available")
except ImportError as e:
    print(f"Missing dependency: {e}")

# Test AI provider availability
try:
    import openai
    print("OpenAI available")
except ImportError:
    print("OpenAI not available")

try:
    from google.cloud import aiplatform
    print("Vertex AI available")
except ImportError:
    print("Vertex AI not available")

# Test document processing availability
try:
    from aiecs.tools.docs.document_parser_tool import DocumentParserTool
    print("DocumentParserTool available")
except ImportError:
    print("DocumentParserTool not available")
```

## Related Documentation

- Tool implementation details in the source code
- DocumentParserTool documentation for document parsing
- AIECS client documentation for AI operations
- Main aiecs documentation for architecture overview

## Support

For issues or questions about AI Document Orchestrator configuration:
- Check the tool source code for implementation details
- Review AI provider documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple documents first to isolate configuration vs. processing issues
- Monitor API rate limits and costs
- Verify AI provider configuration and credentials
- Ensure proper chunk size and timeout limits
- Check concurrency and token limits
- Validate processing mode and provider compatibility
