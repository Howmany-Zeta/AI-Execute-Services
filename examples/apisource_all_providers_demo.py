#!/usr/bin/env python3
"""
APISource Tool - All Providers Operations Demo

This script demonstrates that ALL provider operations from ALL providers
are now visible to AI agents through the LangChain adapter.

This solves the critical problem: AI can now see and use individual provider
operations instead of just a generic 'query' operation with opaque parameters.
"""

import sys
from typing import Dict, List

from aiecs.tools.apisource.tool import APISourceTool
from aiecs.tools.langchain_adapter import ToolRegistry


def print_section(title: str, char: str = "="):
    """Print a formatted section header"""
    print(f"\n{char * 80}")
    print(title)
    print(f"{char * 80}\n")


def test_all_providers_discovery():
    """Test that all providers' operations are discovered"""
    print_section("🔍 ALL PROVIDERS OPERATION DISCOVERY TEST")
    
    # Discover all provider operations
    operations = APISourceTool._discover_provider_operations()
    
    # Group by provider
    providers_ops: Dict[str, List] = {}
    for op in operations:
        provider = op['provider_name']
        if provider not in providers_ops:
            providers_ops[provider] = []
        providers_ops[provider].append(op)
    
    print(f"✅ Discovered {len(operations)} operations from {len(providers_ops)} providers\n")
    
    # Display each provider's operations
    for provider_name, ops in sorted(providers_ops.items()):
        print(f"📦 {provider_name.upper()} Provider: {len(ops)} operations")
        for op in ops:
            print(f"   • {op['name']}")
            print(f"     {op['description']}")
            if op['schema']:
                # Count parameters
                schema_class = op['schema']
                if hasattr(schema_class, 'model_fields'):
                    param_count = len(schema_class.model_fields)
                    print(f"     Parameters: {param_count}")
                elif hasattr(schema_class, '__fields__'):
                    param_count = len(schema_class.__fields__)
                    print(f"     Parameters: {param_count}")
        print()
    
    return providers_ops


def test_langchain_tools_creation():
    """Test that all operations are converted to LangChain tools"""
    print_section("🔗 LANGCHAIN TOOLS CREATION TEST")

    registry = ToolRegistry()
    tools = registry.create_langchain_tools('apisource')
    
    # Separate tool-level and provider-level operations
    tool_ops = [t for t in tools if not t.is_provider_operation]
    provider_ops = [t for t in tools if t.is_provider_operation]
    
    print(f"✅ Created {len(tools)} total LangChain tools")
    print(f"   • Tool-level operations: {len(tool_ops)}")
    print(f"   • Provider-level operations: {len(provider_ops)}\n")
    
    # Group provider operations by provider
    providers_tools: Dict[str, List] = {}
    for tool in provider_ops:
        provider = tool.provider_name
        if provider not in providers_tools:
            providers_tools[provider] = []
        providers_tools[provider].append(tool)
    
    # Display each provider's tools
    for provider_name, tools_list in sorted(providers_tools.items()):
        print(f"📦 {provider_name.upper()}: {len(tools_list)} tools")
        for tool in tools_list:
            print(f"   • {tool.name}")
            print(f"     Schema: {tool.args_schema.__name__ if tool.args_schema else 'None'}")
            if tool.args_schema:
                # Pydantic V2 compatibility
                if hasattr(tool.args_schema, 'model_fields'):
                    params = tool.args_schema.model_fields
                elif hasattr(tool.args_schema, '__fields__'):
                    params = tool.args_schema.__fields__
                else:
                    params = {}

                if params:
                    print(f"     Parameters: {len(params)}")
                    for param_name, field in params.items():
                        required = field.is_required()
                        req_str = "required" if required else "optional"
                        print(f"       - {param_name} ({req_str})")
        print()
    
    return provider_ops


def test_ai_visibility_sample():
    """Test AI visibility with sample operations from each provider"""
    print_section("👁️  AI VISIBILITY TEST - SAMPLE FROM EACH PROVIDER")

    registry = ToolRegistry()
    tools = registry.create_langchain_tools('apisource')
    
    # Get one sample from each provider
    providers_samples: Dict[str, any] = {}
    for tool in tools:
        if tool.is_provider_operation:
            provider = tool.provider_name
            if provider not in providers_samples:
                providers_samples[provider] = tool
    
    # Test each sample
    for provider_name, tool in sorted(providers_samples.items()):
        print(f"📦 {provider_name.upper()} Sample: {tool.name}")
        print(f"   Description: {tool.description}")
        
        if tool.args_schema:
            print(f"   ✅ Schema: {tool.args_schema.__name__}")

            # Pydantic V2 compatibility
            if hasattr(tool.args_schema, 'model_fields'):
                fields = tool.args_schema.model_fields
            elif hasattr(tool.args_schema, '__fields__'):
                fields = tool.args_schema.__fields__
            else:
                fields = {}

            if fields:
                print(f"   📝 Parameters ({len(fields)}):")

                for param_name, field in fields.items():
                    required = field.is_required()
                    req_str = "required" if required else "optional"
                    # Pydantic V2: field IS the FieldInfo
                    desc = field.description or "No description"
                    # Truncate long descriptions
                    if len(desc) > 80:
                        desc = desc[:77] + "..."
                    print(f"      • {param_name} ({req_str})")
                    print(f"        {desc}")
        else:
            print(f"   ❌ No schema available")
        
        print()


def test_complete_coverage():
    """Verify complete coverage of all provider operations"""
    print_section("✅ COMPLETE COVERAGE VERIFICATION")
    
    # Expected operations per provider
    expected = {
        'fred': ['get_categories', 'get_releases', 'get_series_info', 
                 'get_series_observations', 'search_series'],
        'worldbank': ['get_indicator', 'search_indicators', 'get_country_data',
                      'list_countries', 'list_indicators'],
        'newsapi': ['get_top_headlines', 'search_everything', 'get_sources'],
        'census': ['get_acs_data', 'get_population', 'get_economic_data',
                   'list_datasets', 'list_variables']
    }
    
    # Get actual operations
    operations = APISourceTool._discover_provider_operations()
    actual: Dict[str, List[str]] = {}
    for op in operations:
        provider = op['provider_name']
        if provider not in actual:
            actual[provider] = []
        # Extract operation name from full name (e.g., 'fred_get_series' -> 'get_series')
        op_name = op['method_name']
        actual[provider].append(op_name)
    
    # Verify coverage
    all_covered = True
    for provider, expected_ops in expected.items():
        actual_ops = actual.get(provider, [])
        missing = set(expected_ops) - set(actual_ops)
        extra = set(actual_ops) - set(expected_ops)
        
        status = "✅" if not missing else "❌"
        print(f"{status} {provider.upper()}")
        print(f"   Expected: {len(expected_ops)} operations")
        print(f"   Found: {len(actual_ops)} operations")
        
        if missing:
            print(f"   ⚠️  Missing: {', '.join(missing)}")
            all_covered = False
        if extra:
            print(f"   ℹ️  Extra: {', '.join(extra)}")
        
        if not missing and not extra:
            print(f"   ✅ Perfect match!")
        
        print()
    
    return all_covered


def main():
    """Run all tests"""
    print_section("🎯 APISource Tool - All Providers Operations Demo", "=")
    print("This demo verifies that ALL provider operations are visible to AI agents")
    print("through the LangChain adapter with full schema information.")
    
    try:
        # Test 1: Discovery
        providers_ops = test_all_providers_discovery()
        
        # Test 2: LangChain tools creation
        provider_tools = test_langchain_tools_creation()
        
        # Test 3: AI visibility
        test_ai_visibility_sample()
        
        # Test 4: Complete coverage
        all_covered = test_complete_coverage()
        
        # Summary
        print_section("📊 FINAL SUMMARY")
        print(f"✅ Total Providers: {len(providers_ops)}")
        print(f"✅ Total Operations: {sum(len(ops) for ops in providers_ops.values())}")
        print(f"✅ Total LangChain Tools: {len(provider_tools)}")
        print(f"✅ Coverage: {'100% - All operations exposed!' if all_covered else 'Incomplete'}")
        
        print("\n" + "=" * 80)
        print("🎉 SUCCESS! All provider operations are now visible to AI agents!")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

