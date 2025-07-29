#!/usr/bin/env python3
"""
Test script for the new configuration management implementation.

This script tests the LLM binding and agent list configurations,
their validators, schemas, and integration with ConfigManager.
"""

import sys
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.services.multi_task.config.config_manager import ConfigManager
    from app.services.multi_task.config.validators.config_validator import ConfigValidator
    from app.services.multi_task.config.validators.llm_binding_validator import LLMBindingValidator
    from app.services.multi_task.config.validators.agent_list_validator import AgentListValidator
    from app.services.multi_task.config.schemas.llm_binding_schema import LLMBindingSchema
    from app.services.multi_task.config.schemas.agent_list_schema import AgentListSchema
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running this from the project root directory")
    sys.exit(1)


def test_config_loading():
    """Test that all configuration files can be loaded."""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)

    try:
        config_manager = ConfigManager()
        print("✓ ConfigManager initialized successfully")

        # Test loading individual configs
        prompts_config = config_manager.get_prompts_config()
        print(f"✓ Prompts config loaded: {len(prompts_config.get('roles', {}))} roles")

        llm_binding_config = config_manager.get_llm_binding_config()
        print(f"✓ LLM binding config loaded: {len(llm_binding_config.get('llm_bindings', {}))} bindings")

        agent_list_config = config_manager.get_agent_list_config()
        categories = agent_list_config.get('agent_categories', {})
        total_agents = sum(len(cat.get('agents', [])) for cat in categories.values())
        print(f"✓ Agent list config loaded: {len(categories)} categories, {total_agents} agents")

        return True, config_manager

    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False, None


def test_llm_binding_functionality(config_manager: ConfigManager):
    """Test LLM binding functionality."""
    print("\n" + "=" * 60)
    print("Testing LLM Binding Functionality")
    print("=" * 60)

    try:
        # Test get_llm_binding method
        test_agents = ['intent_parser', 'researcher_discussionfacilitator', 'analyst_dataoutcomespecialist']

        for agent in test_agents:
            binding = config_manager.get_llm_binding(agent)
            if binding:
                provider = binding.get('llm_provider', 'context-aware')
                model = binding.get('llm_model', 'context-aware')
                print(f"✓ {agent}: {provider} / {model}")
            else:
                print(f"✗ No binding found for {agent}")

        # Test agent categorization
        print("\nAgent Categories:")
        categories = config_manager.list_agents_by_category()
        for category, agents in categories.items():
            print(f"  {category}: {len(agents)} agents")

        # Test specific agent category lookup
        test_agent = 'intent_parser'
        category = config_manager.get_agent_category(test_agent)
        print(f"✓ {test_agent} is in category: {category}")

        return True

    except Exception as e:
        print(f"✗ LLM binding functionality test failed: {e}")
        return False


def test_validation():
    """Test configuration validation."""
    print("\n" + "=" * 60)
    print("Testing Configuration Validation")
    print("=" * 60)

    try:
        # Test individual validators
        llm_validator = LLMBindingValidator()
        agent_validator = AgentListValidator()
        config_validator = ConfigValidator()

        # Load configuration files directly for validation
        config_dir = Path("app/services/multi_task")

        # Test LLM binding validation
        with open(config_dir / "llm_binding.yaml", 'r') as f:
            llm_binding_data = yaml.safe_load(f)

        llm_result = llm_validator.validate(llm_binding_data)
        print(f"LLM Binding Validation: {'✓ PASS' if llm_result.is_valid else '✗ FAIL'}")
        if not llm_result.is_valid:
            for error_key, errors in llm_result.errors.items():
                print(f"  Error ({error_key}): {errors}")
        if llm_result.warnings:
            print(f"  Warnings: {len(llm_result.warnings)}")

        # Test agent list validation
        with open(config_dir / "agent_list.yaml", 'r') as f:
            agent_list_data = yaml.safe_load(f)

        agent_result = agent_validator.validate(agent_list_data)
        print(f"Agent List Validation: {'✓ PASS' if agent_result.is_valid else '✗ FAIL'}")
        if not agent_result.is_valid:
            for error_key, errors in agent_result.errors.items():
                print(f"  Error ({error_key}): {errors}")
        if agent_result.warnings:
            print(f"  Warnings: {len(agent_result.warnings)}")

        return llm_result.is_valid and agent_result.is_valid

    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False


def test_cross_validation():
    """Test cross-configuration validation."""
    print("\n" + "=" * 60)
    print("Testing Cross-Configuration Validation")
    print("=" * 60)

    try:
        config_validator = ConfigValidator()
        config_dir = Path("app/services/multi_task")

        # Load all configurations
        configs = {}

        # Load YAML files
        for filename in ['prompts.yaml', 'llm_binding.yaml', 'agent_list.yaml']:
            with open(config_dir / filename, 'r') as f:
                configs[filename] = yaml.safe_load(f)

        # Load JSON file (skip if doesn't exist)
        domains_file = config_dir / "domains.json"
        if domains_file.exists():
            with open(domains_file, 'r') as f:
                configs['domains.json'] = json.load(f)
        else:
            print("⚠️  domains.json not found, skipping domains validation")

        # Validate all configurations
        results = config_validator.validate_all_configs(configs)

        print("Cross-validation results:")
        overall_valid = True
        for config_name, result in results.items():
            status = "✓ PASS" if result.is_valid else "✗ FAIL"
            print(f"  {config_name}: {status}")

            if not result.is_valid:
                overall_valid = False
                for error_key, errors in result.errors.items():
                    print(f"    Error ({error_key}): {errors}")

            if result.warnings:
                print(f"    Warnings: {len(result.warnings)}")
                for warning in result.warnings[:3]:  # Show first 3 warnings
                    print(f"      - {warning}")
                if len(result.warnings) > 3:
                    print(f"      ... and {len(result.warnings) - 3} more")

        return overall_valid

    except Exception as e:
        print(f"✗ Cross-validation test failed: {e}")
        return False


def test_consistency_checks():
    """Test consistency between configurations."""
    print("\n" + "=" * 60)
    print("Testing Consistency Checks")
    print("=" * 60)

    try:
        config_dir = Path("app/services/multi_task")

        # Load configurations
        with open(config_dir / "prompts.yaml", 'r') as f:
            prompts_data = yaml.safe_load(f)
        with open(config_dir / "llm_binding.yaml", 'r') as f:
            llm_binding_data = yaml.safe_load(f)
        with open(config_dir / "agent_list.yaml", 'r') as f:
            agent_list_data = yaml.safe_load(f)

        # Get agent lists
        prompt_agents = set(prompts_data.get('roles', {}).keys())
        llm_binding_agents = set(llm_binding_data.get('llm_bindings', {}).keys())

        # Get agents from agent list
        agent_list_agents = set()
        for category_config in agent_list_data.get('agent_categories', {}).values():
            agent_list_agents.update(category_config.get('agents', []))

        print(f"Agents in prompts.yaml: {len(prompt_agents)}")
        print(f"Agents in llm_binding.yaml: {len(llm_binding_agents)}")
        print(f"Agents in agent_list.yaml: {len(agent_list_agents)}")

        # Check consistency
        all_consistent = True

        # Check prompts vs LLM bindings
        missing_bindings = prompt_agents - llm_binding_agents
        extra_bindings = llm_binding_agents - prompt_agents

        if missing_bindings:
            print(f"✗ Agents missing LLM bindings: {sorted(missing_bindings)}")
            all_consistent = False
        else:
            print("✓ All prompt agents have LLM bindings")

        if extra_bindings:
            print(f"⚠ Extra LLM bindings: {sorted(extra_bindings)}")

        # Check prompts vs agent list
        missing_in_list = prompt_agents - agent_list_agents
        extra_in_list = agent_list_agents - prompt_agents

        if missing_in_list:
            print(f"✗ Agents missing from agent list: {sorted(missing_in_list)}")
            all_consistent = False
        else:
            print("✓ All prompt agents are in agent list")

        if extra_in_list:
            print(f"⚠ Extra agents in list: {sorted(extra_in_list)}")

        # Check LLM bindings vs agent list
        if llm_binding_agents == agent_list_agents:
            print("✓ LLM bindings and agent list are consistent")
        else:
            print("⚠ LLM bindings and agent list have differences")
            all_consistent = False

        return all_consistent

    except Exception as e:
        print(f"✗ Consistency check failed: {e}")
        return False


def test_schema_validation():
    """Test Pydantic schema validation."""
    print("\n" + "=" * 60)
    print("Testing Schema Validation")
    print("=" * 60)

    try:
        config_dir = Path("app/services/multi_task")

        # Test LLM binding schema
        with open(config_dir / "llm_binding.yaml", 'r') as f:
            llm_binding_data = yaml.safe_load(f)

        try:
            llm_schema = LLMBindingSchema(**llm_binding_data)
            print("✓ LLM binding schema validation passed")
        except Exception as e:
            print(f"✗ LLM binding schema validation failed: {e}")
            return False

        # Test agent list schema
        with open(config_dir / "agent_list.yaml", 'r') as f:
            agent_list_data = yaml.safe_load(f)

        try:
            agent_schema = AgentListSchema(**agent_list_data)
            print("✓ Agent list schema validation passed")
        except Exception as e:
            print(f"✗ Agent list schema validation failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"✗ Schema validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Configuration Implementation Test Suite")
    print("=" * 60)

    tests = [
        ("Configuration Loading", test_config_loading),
        ("Schema Validation", test_schema_validation),
        ("Validation", test_validation),
        ("Cross-Validation", test_cross_validation),
        ("Consistency Checks", test_consistency_checks),
    ]

    results = []
    config_manager = None

    for test_name, test_func in tests:
        if test_name == "Configuration Loading":
            success, config_manager = test_func()
        elif test_name == "LLM Binding Functionality" and config_manager:
            success = test_func(config_manager)
        else:
            success = test_func()

        results.append((test_name, success))

    # Test LLM binding functionality if config manager is available
    if config_manager:
        success = test_llm_binding_functionality(config_manager)
        results.append(("LLM Binding Functionality", success))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Implementation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
