# AI Data Analysis Orchestrator Configuration Guide

## Overview

The AI Data Analysis Orchestrator is a powerful tool that coordinates multiple foundation tools to provide natural language driven analysis, automated workflow orchestration, multi-tool coordination, and comprehensive analysis execution. It supports various analysis modes (exploratory, diagnostic, predictive, prescriptive, comparative, causal) and coordinates foundation tools including data_loader, data_profiler, data_transformer, data_visualizer, statistical_analyzer, and model_trainer. The tool can be configured via environment variables using the `AI_DATA_ORCHESTRATOR_` prefix or through programmatic configuration when initializing the tool.

## Using .env Files in Your Project

When using aiecs as a dependency in your project, you can store configuration in a `.env` file for convenience. The AI Data Analysis Orchestrator reads from environment variables that are already loaded into the process, so you need to load the `.env` file in your application before importing aiecs tools.

### Setting Up .env Files

**1. Install python-dotenv:**

```bash
pip install python-dotenv
```

**2. Create a `.env` file in your project root:**

```bash
# .env file in your project root
AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=10
AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
```

**3. Load the .env file in your application:**

```python
# main.py or app.py - at the top of your entry point
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be done BEFORE importing aiecs tools
load_dotenv()

# Now import and use aiecs tools
from aiecs.tools.statistics.ai_data_analysis_orchestrator import AIDataAnalysisOrchestrator

# The tool will automatically use the environment variables
orchestrator = AIDataAnalysisOrchestrator()
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

from aiecs.tools.statistics.ai_data_analysis_orchestrator import AIDataAnalysisOrchestrator
orchestrator = AIDataAnalysisOrchestrator()
```

**Example `.env.production`:**
```bash
# Production settings - optimized for performance and reliability
AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20
AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
```

**Example `.env.development`:**
```bash
# Development settings - optimized for testing and debugging
AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=5
AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=false
AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
AI_DATA_ORCHESTRATOR_ENABLE_CACHING=false
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
   # AI Data Analysis Orchestrator Configuration
   
   # Default analysis mode to use
   AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
   
   # Maximum number of analysis iterations
   AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=10
   
   # Whether to enable automatic workflow generation
   AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
   
   # Default AI provider to use
   AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
   
   # Whether to enable result caching
   AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
   ```

3. **Document your variables** - Add comments explaining each setting

4. **Use load_dotenv() early** - Call it at the very top of your entry point, before any aiecs imports

5. **Format values correctly**:
   - Strings: Plain text: `exploratory`, `openai`
   - Integers: Plain numbers: `10`, `20`
   - Booleans: `true` or `false`

## Configuration Options

### 1. Default Mode

**Environment Variable:** `AI_DATA_ORCHESTRATOR_DEFAULT_MODE`

**Type:** String

**Default:** `"exploratory"`

**Description:** Default analysis mode to use for data analysis operations. This mode is used when no specific mode is specified in the analysis request.

**Supported Modes:**
- `exploratory` - Exploratory data analysis (default)
- `diagnostic` - Diagnostic analysis
- `predictive` - Predictive analysis
- `prescriptive` - Prescriptive analysis
- `comparative` - Comparative analysis
- `causal` - Causal analysis

**Example:**
```bash
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=predictive
```

**Mode Note:** Choose the mode that best fits your typical analysis requirements.

### 2. Max Iterations

**Environment Variable:** `AI_DATA_ORCHESTRATOR_MAX_ITERATIONS`

**Type:** Integer

**Default:** `10`

**Description:** Maximum number of analysis iterations that can be performed in a single analysis workflow. This controls the depth and complexity of analysis operations.

**Common Values:**
- `5` - Quick analysis (basic insights)
- `10` - Standard analysis (default, balanced)
- `20` - Deep analysis (comprehensive insights)
- `50` - Maximum analysis (exhaustive exploration)

**Example:**
```bash
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20
```

**Iteration Note:** Higher values provide more comprehensive analysis but may increase processing time and resource usage.

### 3. Enable Auto Workflow

**Environment Variable:** `AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable automatic workflow generation. When enabled, the orchestrator automatically designs analysis workflows based on the data and requirements.

**Values:**
- `true` - Enable auto workflow (default)
- `false` - Disable auto workflow

**Example:**
```bash
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
```

**Workflow Note:** Auto workflow provides intelligent analysis design but may require more computational resources.

### 4. Default AI Provider

**Environment Variable:** `AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER`

**Type:** String

**Default:** `"openai"`

**Description:** Default AI provider to use for analysis operations. This provider is used when no specific provider is specified in the request.

**Supported Providers:**
- `openai` - OpenAI API (default)
- `anthropic` - Anthropic Claude
- `google` - Google AI
- `local` - Local AI model

**Example:**
```bash
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=anthropic
```

**Provider Note:** Ensure the selected provider is properly configured with API keys and credentials.

### 5. Enable Caching

**Environment Variable:** `AI_DATA_ORCHESTRATOR_ENABLE_CACHING`

**Type:** Boolean

**Default:** `True`

**Description:** Whether to enable result caching. When enabled, analysis results are cached to improve performance for similar requests.

**Values:**
- `true` - Enable caching (default)
- `false` - Disable caching

**Example:**
```bash
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
```

**Caching Note:** Caching improves performance but requires additional memory and storage.

## Usage Examples

### Example 1: Basic Environment Configuration

```bash
# Set basic analysis parameters
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=10
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true

# Run your application
python app.py
```

### Example 2: High-Performance Configuration

```bash
# Optimized for comprehensive analysis
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
```

### Example 3: Development Configuration

```bash
# Development-friendly settings
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=5
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=false
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.tools.statistics.ai_data_analysis_orchestrator import AIDataAnalysisOrchestrator

# Initialize with custom configuration
orchestrator = AIDataAnalysisOrchestrator(config={
    'default_mode': 'exploratory',
    'max_iterations': 10,
    'enable_auto_workflow': True,
    'default_ai_provider': 'openai',
    'enable_caching': True
})
```

### Example 5: Mixed Configuration

Environment variables are used as defaults, but can be overridden programmatically:

```bash
# Set environment defaults
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=10
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
```

```python
# Override for specific instance
orchestrator = AIDataAnalysisOrchestrator(config={
    'max_iterations': 20,  # This overrides the environment variable
    'default_mode': 'predictive'  # This overrides the environment variable
})
```

## Configuration Priority

When the AI Data Analysis Orchestrator is initialized, configuration values are resolved in the following order (highest to lowest priority):

1. **Programmatic config** - Values passed to the constructor
2. **Environment variables** - Values set via `AI_DATA_ORCHESTRATOR_*` variables
3. **Default values** - Built-in defaults as specified above

## Data Type Parsing

### String Values

Strings should be provided as plain text without quotes:

```bash
export AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
```

### Integer Values

Integers should be provided as numeric strings:

```bash
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=10
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20
```

### Boolean Values

Booleans should be provided as lowercase strings:

```bash
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=false
```

## Validation

### Automatic Type Validation

Pydantic automatically validates configuration values:

- `default_mode` must be a valid analysis mode string
- `max_iterations` must be a positive integer
- `enable_auto_workflow` must be a boolean
- `default_ai_provider` must be a valid provider string
- `enable_caching` must be a boolean

### Runtime Validation

When performing analysis, the tool validates:

1. **Analysis mode** - Mode must be supported
2. **Iteration limits** - Analysis must not exceed max iterations
3. **AI provider availability** - Provider must be configured
4. **Workflow constraints** - Auto workflow must be properly configured
5. **Caching requirements** - Cache must be accessible if enabled

## Analysis Modes

The AI Data Analysis Orchestrator supports various analysis modes:

### Basic Modes
- **Exploratory** - Initial data exploration and discovery
- **Diagnostic** - Root cause analysis and problem diagnosis
- **Predictive** - Future trend prediction and forecasting
- **Prescriptive** - Actionable recommendations and solutions

### Advanced Modes
- **Comparative** - Compare different datasets or time periods
- **Causal** - Identify cause-and-effect relationships

## AI Providers

### Supported Providers
- **OpenAI** - OpenAI API integration
- **Anthropic** - Anthropic Claude integration
- **Google** - Google AI integration
- **Local** - Local AI model integration

### Provider Configuration

Each provider requires specific configuration:

**OpenAI:**
```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_ORG_ID=your-org-id  # Optional
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY=your-api-key
```

**Google:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
export GOOGLE_CLOUD_PROJECT=your-project-id
```

**Local:**
```bash
export LOCAL_MODEL_PATH=path/to/model
export LOCAL_MODEL_TYPE=llama2  # or other model type
```

## Operations Supported

The AI Data Analysis Orchestrator supports comprehensive data analysis operations:

### Basic Analysis
- `analyze_data` - Perform comprehensive data analysis
- `exploratory_analysis` - Perform exploratory data analysis
- `diagnostic_analysis` - Perform diagnostic analysis
- `predictive_analysis` - Perform predictive analysis
- `prescriptive_analysis` - Perform prescriptive analysis

### Advanced Analysis
- `comparative_analysis` - Compare different datasets
- `causal_analysis` - Identify causal relationships
- `workflow_analysis` - Execute custom analysis workflows
- `iterative_analysis` - Perform iterative analysis with feedback

### Workflow Management
- `design_workflow` - Design analysis workflows
- `execute_workflow` - Execute analysis workflows
- `optimize_workflow` - Optimize workflow performance
- `cache_workflow` - Cache workflow results

### Tool Coordination
- `coordinate_tools` - Coordinate multiple analysis tools
- `integrate_results` - Integrate results from multiple tools
- `validate_analysis` - Validate analysis results
- `generate_report` - Generate comprehensive analysis reports

## Troubleshooting

### Issue: AI Provider not available

**Error:** `OrchestratorError` when calling AI providers

**Solutions:**
```bash
# Check provider configuration
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai

# Verify API keys
export OPENAI_API_KEY=your-valid-api-key

# Test with local provider
export AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
```

### Issue: Analysis workflow fails

**Error:** `WorkflowError` during workflow execution

**Solutions:**
1. Check foundation tool availability
2. Verify data accessibility
3. Check workflow configuration
4. Validate analysis parameters

### Issue: Max iterations exceeded

**Error:** Analysis exceeds maximum iterations

**Solutions:**
```bash
# Increase max iterations
export AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20

# Or optimize analysis workflow
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
```

### Issue: Caching problems

**Error:** Cache operations fail

**Solutions:**
```bash
# Disable caching for testing
export AI_DATA_ORCHESTRATOR_ENABLE_CACHING=false

# Check cache directory permissions
# Verify cache configuration
```

### Issue: Auto workflow issues

**Error:** Auto workflow generation fails

**Solutions:**
```bash
# Disable auto workflow for testing
export AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=false

# Check AI provider configuration
# Verify workflow templates
```

### Issue: Foundation tool errors

**Error:** Foundation tool operations fail

**Solutions:**
1. Check tool availability and dependencies
2. Verify data format compatibility
3. Check tool configuration
4. Validate input data

## Best Practices

### Performance Optimization

1. **Iteration Management** - Set appropriate max iterations
2. **Caching Strategy** - Enable caching for repeated analyses
3. **Workflow Optimization** - Use auto workflow for efficiency
4. **Provider Selection** - Choose providers based on task requirements
5. **Resource Management** - Monitor memory and CPU usage

### Error Handling

1. **Graceful Degradation** - Handle tool failures gracefully
2. **Retry Logic** - Implement retry for transient failures
3. **Fallback Strategies** - Provide fallback analysis methods
4. **Error Logging** - Log errors for debugging and monitoring
5. **User Feedback** - Provide clear error messages

### Security

1. **API Key Management** - Secure storage of API keys
2. **Data Privacy** - Ensure data privacy in analysis
3. **Access Control** - Control access to analysis tools
4. **Audit Logging** - Log analysis activities for compliance
5. **Data Validation** - Validate input data before analysis

### Resource Management

1. **Memory Usage** - Monitor memory consumption during analysis
2. **API Rate Limits** - Respect provider rate limits
3. **Cost Management** - Monitor and control analysis costs
4. **Processing Time** - Set reasonable timeouts
5. **Cleanup** - Clean up temporary files and resources

### Integration

1. **Tool Dependencies** - Ensure required tools are available
2. **API Compatibility** - Maintain API compatibility
3. **Error Propagation** - Properly propagate errors
4. **Logging Integration** - Integrate with logging systems
5. **Monitoring** - Monitor tool performance and usage

### Development vs Production

**Development:**
```bash
AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=5
AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=false
AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=local
AI_DATA_ORCHESTRATOR_ENABLE_CACHING=false
```

**Production:**
```bash
AI_DATA_ORCHESTRATOR_DEFAULT_MODE=exploratory
AI_DATA_ORCHESTRATOR_MAX_ITERATIONS=20
AI_DATA_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=true
AI_DATA_ORCHESTRATOR_DEFAULT_AI_PROVIDER=openai
AI_DATA_ORCHESTRATOR_ENABLE_CACHING=true
```

### Error Handling

Always wrap analysis operations in try-except blocks:

```python
from aiecs.tools.statistics.ai_data_analysis_orchestrator import AIDataAnalysisOrchestrator, OrchestratorError, WorkflowError

orchestrator = AIDataAnalysisOrchestrator()

try:
    result = orchestrator.analyze_data(
        data_source="dataset.csv",
        analysis_mode="exploratory",
        max_iterations=10
    )
except WorkflowError as e:
    print(f"Workflow error: {e}")
except OrchestratorError as e:
    print(f"Orchestrator error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Dependencies

### Core Dependencies

```bash
# Install core dependencies
pip install pydantic python-dotenv pandas

# Install AI provider dependencies
pip install openai anthropic google-cloud-aiplatform

# Install analysis dependencies
pip install numpy scipy scikit-learn matplotlib seaborn
```

### Optional Dependencies

```bash
# For advanced analysis
pip install plotly dash streamlit

# For machine learning
pip install xgboost lightgbm catboost

# For statistical analysis
pip install statsmodels pingouin

# For data processing
pip install dask vaex
```

### Verification

```python
# Test dependency availability
try:
    import pydantic
    import pandas
    import numpy
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
    import anthropic
    print("Anthropic available")
except ImportError:
    print("Anthropic not available")

# Test analysis tool availability
try:
    from aiecs.tools.statistics.data_loader import DataLoader
    from aiecs.tools.statistics.data_profiler import DataProfiler
    print("Foundation tools available")
except ImportError:
    print("Foundation tools not available")
```

## Related Documentation

- Tool implementation details in the source code
- Foundation tools documentation (data_loader, data_profiler, etc.)
- AIECS client documentation for AI operations
- Main aiecs documentation for architecture overview

## Support

For issues or questions about AI Data Analysis Orchestrator configuration:
- Check the tool source code for implementation details
- Review foundation tool documentation for specific features
- Consult the main aiecs documentation for architecture overview
- Test with simple datasets first to isolate configuration vs. analysis issues
- Monitor API rate limits and costs
- Verify AI provider configuration and credentials
- Ensure proper iteration and workflow limits
- Check foundation tool availability and configuration
- Validate analysis mode and provider compatibility
