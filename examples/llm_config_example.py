#!/usr/bin/env python3
"""
Example script demonstrating LLM configuration management.

This script shows how to:
1. Load and access LLM configuration
2. Query provider and model information
3. Use configuration in LLM clients
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_load_config():
    """Example 1: Loading and accessing configuration"""
    print("\n" + "="*70)
    print("Example 1: Loading and Accessing Configuration")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    # Get the loader instance (singleton)
    loader = get_llm_config_loader()
    
    # Get full configuration
    config = loader.get_config()
    
    print(f"\nLoaded configuration from: {loader.get_config_path()}")
    print(f"Total providers: {len(config.providers)}")
    print(f"Provider names: {', '.join(config.get_provider_names())}")


def example_2_provider_info():
    """Example 2: Getting provider information"""
    print("\n" + "="*70)
    print("Example 2: Getting Provider Information")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    loader = get_llm_config_loader()
    
    # Get OpenAI provider configuration
    openai_config = loader.get_provider_config("OpenAI")
    
    if openai_config:
        print(f"\nProvider: {openai_config.provider_name}")
        print(f"Default Model: {openai_config.default_model}")
        print(f"Available Models: {', '.join(openai_config.get_model_names())}")


def example_3_model_info():
    """Example 3: Getting model information"""
    print("\n" + "="*70)
    print("Example 3: Getting Model Information")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    loader = get_llm_config_loader()
    
    # Get specific model configuration
    model_config = loader.get_model_config("OpenAI", "gpt-4-turbo")
    
    if model_config:
        print(f"\nModel: {model_config.name}")
        print(f"Display Name: {model_config.display_name}")
        print(f"Description: {model_config.description}")
        print(f"\nCosts (per 1K tokens):")
        print(f"  Input: ${model_config.costs.input}")
        print(f"  Output: ${model_config.costs.output}")
        print(f"\nCapabilities:")
        print(f"  Streaming: {model_config.capabilities.streaming}")
        print(f"  Vision: {model_config.capabilities.vision}")
        print(f"  Function Calling: {model_config.capabilities.function_calling}")
        print(f"  Max Tokens: {model_config.capabilities.max_tokens}")
        print(f"  Context Window: {model_config.capabilities.context_window}")
        print(f"\nDefault Parameters:")
        print(f"  Temperature: {model_config.default_params.temperature}")
        print(f"  Max Tokens: {model_config.default_params.max_tokens}")


def example_4_iterate_providers():
    """Example 4: Iterating through all providers and models"""
    print("\n" + "="*70)
    print("Example 4: Iterating Through All Providers")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    loader = get_llm_config_loader()
    config = loader.get_config()
    
    for provider_name, provider_config in config.providers.items():
        print(f"\n{provider_name}:")
        print(f"  Default: {provider_config.default_model}")
        print(f"  Models ({len(provider_config.models)}):")
        
        for model in provider_config.models[:3]:  # Show first 3 models
            cost_str = f"${model.costs.input:.6f} in / ${model.costs.output:.6f} out"
            print(f"    - {model.name}: {cost_str}")
        
        if len(provider_config.models) > 3:
            print(f"    ... and {len(provider_config.models) - 3} more")


def example_5_model_aliases():
    """Example 5: Working with model aliases"""
    print("\n" + "="*70)
    print("Example 5: Working with Model Aliases")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    loader = get_llm_config_loader()
    
    # xAI has model aliases
    xai_config = loader.get_provider_config("xAI")
    
    if xai_config and xai_config.model_mappings:
        print(f"\nxAI Model Aliases:")
        for alias, actual_name in list(xai_config.model_mappings.items())[:5]:
            print(f"  '{alias}' -> '{actual_name}'")
        
        # Get model config using alias
        model_config = loader.get_model_config("xAI", "Grok 4 Normal")
        if model_config:
            print(f"\nResolved 'Grok 4 Normal' to '{model_config.name}'")


async def example_6_using_with_clients():
    """Example 6: Using configuration with LLM clients"""
    print("\n" + "="*70)
    print("Example 6: Using Configuration with LLM Clients")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader
    
    loader = get_llm_config_loader()
    
    # Show how clients will use the configuration
    print("\nConfiguration usage in clients:")
    
    # Get default models for each provider
    for provider_name in ["Vertex", "OpenAI", "GoogleAI", "xAI"]:
        default_model = loader.get_default_model(provider_name)
        print(f"  {provider_name}: Default model is '{default_model}'")
    
    print("\nNote: Clients automatically use these defaults when no model is specified.")


def example_7_reload_config():
    """Example 7: Reloading configuration"""
    print("\n" + "="*70)
    print("Example 7: Reloading Configuration (Hot Reload)")
    print("="*70)
    
    from aiecs.llm.config import get_llm_config_loader, reload_llm_config
    from aiecs.llm.client_factory import LLMClientFactory
    
    loader = get_llm_config_loader()
    print(f"\nCurrent config path: {loader.get_config_path()}")
    
    # Reload configuration
    print("\nReloading configuration...")
    config = reload_llm_config()
    print(f"✓ Configuration reloaded: {len(config.providers)} providers")
    
    # Or reload via client factory
    print("\nReloading via ClientFactory...")
    LLMClientFactory.reload_config()
    print("✓ Configuration reloaded in factory")
    
    print("\nThis allows updating model costs and settings without restarting!")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("LLM Configuration Management Examples")
    print("="*70)
    
    # Run synchronous examples
    example_1_load_config()
    example_2_provider_info()
    example_3_model_info()
    example_4_iterate_providers()
    example_5_model_aliases()
    
    # Run async example
    asyncio.run(example_6_using_with_clients())
    
    # Reload example
    example_7_reload_config()
    
    print("\n" + "="*70)
    print("Examples Complete!")
    print("="*70)
    print("\nFor more information, see: docs/LLM_CONFIGURATION.md")


if __name__ == "__main__":
    main()

