# LLM Model Configuration Management

This document describes the centralized configuration management system for LLM client models.

## Overview

The LLM configuration system provides a centralized, type-safe way to manage all LLM provider models, their costs, capabilities, and default parameters using YAML configuration files.

## Features

- **Centralized Configuration**: All model settings in one YAML file
- **Type Safety**: Pydantic-based validation ensures configuration integrity
- **Hot Reloading**: Support for reloading configuration without restarting
- **Flexible Model Management**: Easy to add/modify models without code changes
- **Cost Tracking**: Automatic cost estimation based on configured pricing
- **Model Capabilities**: Track features like vision, streaming, function calling

## Architecture

### Configuration Files

#### Main Configuration
- **Path**: `aiecs/config/llm_models.yaml`
- **Format**: YAML
- **Environment Variable**: `LLM_MODELS_CONFIG` (optional override)

### Configuration Schema

```yaml
providers:
  <provider_name>:
    provider_name: string
    default_model: string
    model_mappings:  # Optional: for model aliases
      <alias>: <actual_model_name>
    models:
      - name: string
        display_name: string  # Optional
        description: string   # Optional
        costs:
          input: float   # USD per 1K tokens
          output: float  # USD per 1K tokens
        capabilities:
          streaming: boolean
          vision: boolean
          function_calling: boolean
          max_tokens: integer
          context_window: integer
        default_params:
          temperature: float (0.0-2.0)
          max_tokens: integer
          top_p: float (0.0-1.0)
          top_k: integer
```

## Usage

### Loading Configuration

Configuration is automatically loaded on first use:

```python
from aiecs.llm.config_loader import get_llm_config_loader

# Get the loader instance
loader = get_llm_config_loader()

# Get full configuration
config = loader.get_config()

# Get specific provider configuration
provider_config = loader.get_provider_config("OpenAI")

# Get specific model configuration
model_config = loader.get_model_config("OpenAI", "gpt-4-turbo")

# Get default model for a provider
default_model = loader.get_default_model("Vertex")
```

### Hot Reloading Configuration

```python
from aiecs.llm.config_loader import reload_llm_config
from aiecs.llm.client_factory import LLMClientFactory

# Reload configuration from file
config = reload_llm_config()

# Or reload via client factory
LLMClientFactory.reload_config()
```

### Using Configured Models

The LLM clients automatically use the configuration:

```python
from aiecs.llm.client_factory import LLMClientFactory

# Get a client - it will use configured defaults
client = LLMClientFactory.get_client("OpenAI")

# Generate text - uses default model from config
response = await client.generate_text(
    messages=[{"role": "user", "content": "Hello"}]
)

# Or specify a model explicitly
response = await client.generate_text(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4o"
)
```

### Validating Configuration

```bash
# Run the validation script
poetry run python -m aiecs.llm.validate_config
```

This will:
- Load and validate the configuration file
- Check for errors and warnings
- Display a summary of all configured providers and models

## Configuration Management

### Adding a New Model

1. Open `aiecs/config/llm_models.yaml`
2. Find the appropriate provider section
3. Add the model to the `models` list:

```yaml
providers:
  openai:
    models:
      - name: "gpt-5"  # New model
        display_name: "GPT-5"
        description: "Next generation model"
        costs:
          input: 0.001
          output: 0.003
        capabilities:
          streaming: true
          vision: true
          function_calling: true
          max_tokens: 16384
          context_window: 256000
        default_params:
          temperature: 0.7
          max_tokens: 8192
          top_p: 1.0
          top_k: 0
```

4. Validate the configuration:
```bash
poetry run python -m aiecs.llm.validate_config
```

5. Reload configuration (optional, for hot-reloading):
```python
from aiecs.llm.client_factory import LLMClientFactory
LLMClientFactory.reload_config()
```

### Adding Model Aliases

For providers with model name variations (like xAI/Grok):

```yaml
providers:
  xai:
    model_mappings:
      "Grok 4": "grok-4"
      "Grok 4 Normal": "grok-4"
    models:
      - name: "grok-4"
        # ... configuration
```

### Updating Model Costs

When pricing changes, simply update the YAML file:

```yaml
costs:
  input: 0.002  # Updated price
  output: 0.006  # Updated price
```

No code changes required!

## Configuration Validation

The system validates:

1. **Required Fields**: All required fields must be present
2. **Cost Values**: Must be non-negative
3. **Model Names**: Must be unique within a provider
4. **Default Model**: Must exist in the models list
5. **Model Mappings**: Aliases must point to valid models
6. **Parameters**: Must be within valid ranges (e.g., temperature 0.0-2.0)

Warnings are issued for:
- Zero costs (may be intentional for free tiers)
- Default max_tokens exceeding capability max_tokens

## Environment Variables

### LLM_MODELS_CONFIG
Override the default configuration file path:

```bash
export LLM_MODELS_CONFIG=/path/to/custom/llm_models.yaml
```

### In .env file
```env
LLM_MODELS_CONFIG=/path/to/custom/llm_models.yaml
```

## API Reference

### LLMConfigLoader

**Methods:**
- `get_config()`: Get full configuration
- `reload_config()`: Reload from file
- `get_provider_config(provider_name)`: Get provider configuration
- `get_model_config(provider_name, model_name)`: Get model configuration
- `get_default_model(provider_name)`: Get default model name
- `is_loaded()`: Check if configuration is loaded
- `get_config_path()`: Get path to current config file

### Configuration Models

**LLMModelsConfig**
- Root configuration containing all providers

**ProviderConfig**
- Configuration for a single provider
- Contains models list, default model, and mappings

**ModelConfig**
- Complete configuration for a single model
- Contains costs, capabilities, and default parameters

**ModelCostConfig**
- Token cost information (input/output)

**ModelCapabilities**
- Model features and limits

**ModelDefaultParams**
- Default inference parameters

## Best Practices

1. **Validation**: Always run validation after modifying configuration
2. **Version Control**: Keep `llm_models.yaml` in version control
3. **Cost Updates**: Regularly update pricing information
4. **Documentation**: Add descriptions to new models
5. **Testing**: Test new models before deploying to production
6. **Hot Reload**: Use hot reload in development, restart in production

## Troubleshooting

### Configuration Not Found

**Error**: `FileNotFoundError: LLM models configuration file not found`

**Solutions**:
1. Ensure `aiecs/config/llm_models.yaml` exists
2. Set `LLM_MODELS_CONFIG` environment variable
3. Check file permissions

### Validation Errors

**Error**: `ConfigValidationError: ...`

**Solutions**:
1. Run validation script to see detailed errors
2. Check YAML syntax (indentation, quotes)
3. Verify all required fields are present
4. Ensure costs are non-negative numbers

### Model Not Found

**Error**: Model configuration not found for specific model

**Solutions**:
1. Check model name spelling
2. Verify model exists in YAML configuration
3. Check if model alias is correctly mapped
4. Reload configuration if recently added

## Migration Guide

If you have existing hardcoded model configurations, they will continue to work as fallbacks. However, we recommend migrating to the new configuration system:

1. All model costs are now in the YAML file
2. Default models are configured per provider
3. Model aliases are centrally managed
4. Custom parameters can be set in configuration

The old `token_costs` dictionaries in client classes are deprecated but still functional for backward compatibility.

## Examples

### Complete Provider Configuration

```yaml
providers:
  openai:
    provider_name: "OpenAI"
    default_model: "gpt-4-turbo"
    models:
      - name: "gpt-4-turbo"
        display_name: "GPT-4 Turbo"
        description: "Fast and capable GPT-4 variant"
        costs:
          input: 0.01
          output: 0.03
        capabilities:
          streaming: true
          vision: true
          function_calling: true
          max_tokens: 4096
          context_window: 128000
        default_params:
          temperature: 0.7
          max_tokens: 4096
          top_p: 1.0
          top_k: 0
```

### Programmatic Access

```python
from aiecs.llm.config_loader import get_llm_config_loader

loader = get_llm_config_loader()
config = loader.get_config()

# Iterate through all providers
for provider_name, provider_config in config.providers.items():
    print(f"Provider: {provider_name}")
    print(f"  Default: {provider_config.default_model}")
    
    # Iterate through models
    for model in provider_config.models:
        print(f"  Model: {model.name}")
        print(f"    Cost: ${model.costs.input} in / ${model.costs.output} out")
        print(f"    Max Tokens: {model.capabilities.max_tokens}")
```

## Support

For issues or questions:
1. Check this documentation
2. Run the validation script
3. Review error logs
4. Check YAML syntax

