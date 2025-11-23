#!/usr/bin/env python3
"""
Validation script for LLM models configuration.

This script validates the LLM models configuration file and prints
information about configured providers and models.
"""

import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main validation function"""
    try:
        from aiecs.llm.config import get_llm_config_loader, validate_llm_config

        logger.info("=" * 70)
        logger.info("LLM Models Configuration Validator")
        logger.info("=" * 70)

        # Load configuration
        loader = get_llm_config_loader()
        config = loader.get_config()

        logger.info(f"\nConfiguration loaded from: {loader.get_config_path()}")

        # Validate configuration
        logger.info("\nValidating configuration...")
        is_valid, warnings = validate_llm_config(config)

        if is_valid:
            logger.info("✓ Configuration is valid!")

        # Print summary
        logger.info("\n" + "=" * 70)
        logger.info("Configuration Summary")
        logger.info("=" * 70)

        logger.info(f"\nTotal Providers: {len(config.providers)}")

        for provider_name, provider_config in config.providers.items():
            logger.info(f"\n{provider_name}:")
            logger.info(f"  Default Model: {provider_config.default_model}")
            logger.info(f"  Total Models: {len(provider_config.models)}")

            if provider_config.model_mappings:
                logger.info(f"  Model Aliases: {len(provider_config.model_mappings)}")

            logger.info("  Available Models:")
            for model in provider_config.models:
                cost_str = f"${model.costs.input:.6f} in / ${model.costs.output:.6f} out (per 1K tokens)"
                logger.info(f"    - {model.name}: {cost_str}")
                if model.capabilities.vision:
                    logger.info("        Vision: Yes")
                if model.capabilities.function_calling:
                    logger.info("        Function Calling: Yes")

        logger.info("\n" + "=" * 70)
        logger.info("Validation Complete!")
        logger.info("=" * 70)

        if warnings:
            logger.info(f"\nNote: {len(warnings)} warnings were generated during validation.")
            logger.info("See logs above for details.")

        return 0

    except FileNotFoundError as e:
        logger.error(f"\n✗ Configuration file not found: {e}")
        logger.error("\nPlease ensure the LLM models configuration file exists at:")
        logger.error("  - aiecs/config/llm_models.yaml")
        logger.error("  - Or set LLM_MODELS_CONFIG environment variable")
        return 1

    except Exception as e:
        logger.error(f"\n✗ Validation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
