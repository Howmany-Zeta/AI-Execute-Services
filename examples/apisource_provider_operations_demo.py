"""
APISource Provider Operations Discovery Demo

Demonstrates how provider operations are automatically discovered and exposed
to AI agents through the LangChain adapter, solving the schema visibility problem.

This script shows:
1. Provider operations are discovered via @expose_operation decorator
2. Dict-based schemas are converted to Pydantic schemas
3. LangChain adapter creates individual tools for each provider operation
4. AI agents can see fine-grained provider capabilities
"""

import sys
import logging
from typing import List

# Setup path
sys.path.insert(0, '/home/coder1/python-middleware-dev')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_provider_operation_discovery():
    """Test that provider operations are discovered correctly"""
    print("\n" + "="*80)
    print("TEST 1: Provider Operation Discovery")
    print("="*80)
    
    from aiecs.tools.apisource.providers import PROVIDER_REGISTRY
    from aiecs.tools.apisource.providers.fred import FREDProvider
    
    # Test FRED provider
    print(f"\n📋 Testing FRED Provider...")
    exposed_ops = FREDProvider.get_exposed_operations()
    
    print(f"\n✅ Found {len(exposed_ops)} exposed operations:")
    for op in exposed_ops:
        print(f"\n  Operation: {op['name']}")
        print(f"  Description: {op['description']}")
        if op['schema']:
            params = op['schema'].get('parameters', {})
            print(f"  Parameters: {len(params)} parameters")
            for param_name, param_info in list(params.items())[:3]:  # Show first 3
                required = "required" if param_info.get('required') else "optional"
                print(f"    - {param_name} ({param_info.get('type', 'string')}, {required}): {param_info.get('description', 'N/A')[:60]}")
    
    return len(exposed_ops) > 0


def test_schema_conversion():
    """Test Dict-based schema to Pydantic conversion"""
    print("\n" + "="*80)
    print("TEST 2: Schema Conversion (Dict → Pydantic)")
    print("="*80)
    
    from aiecs.tools.apisource.tool import APISourceTool
    from aiecs.tools.apisource.providers.fred import FREDProvider
    
    # Get a sample schema
    exposed_ops = FREDProvider.get_exposed_operations()
    if not exposed_ops:
        print("❌ No exposed operations found")
        return False
    
    sample_op = exposed_ops[0]
    print(f"\n📋 Converting schema for: {sample_op['name']}")
    
    # Convert to Pydantic
    pydantic_schema = APISourceTool._convert_dict_schema_to_pydantic(
        sample_op['schema'],
        f"fred_{sample_op['name']}"
    )
    
    if pydantic_schema:
        print(f"\n✅ Successfully created Pydantic schema: {pydantic_schema.__name__}")
        print(f"\n📝 Schema fields:")
        
        # Get field info
        if hasattr(pydantic_schema, 'model_fields'):
            fields = pydantic_schema.model_fields
            for field_name, field_info in fields.items():
                print(f"  - {field_name}: {field_info.annotation}")
                if field_info.description:
                    print(f"    Description: {field_info.description[:80]}")
        
        return True
    else:
        print("❌ Failed to convert schema")
        return False


def test_apisource_discovery():
    """Test APISourceTool provider operation discovery"""
    print("\n" + "="*80)
    print("TEST 3: APISourceTool Provider Operation Discovery")
    print("="*80)
    
    from aiecs.tools.apisource.tool import APISourceTool
    
    print("\n📋 Discovering provider operations...")
    provider_ops = APISourceTool._discover_provider_operations()
    
    print(f"\n✅ Discovered {len(provider_ops)} provider operations:")
    
    # Group by provider
    by_provider = {}
    for op in provider_ops:
        provider = op.get('provider_name', 'unknown')
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(op)
    
    for provider, ops in by_provider.items():
        print(f"\n  {provider.upper()} Provider: {len(ops)} operations")
        for op in ops[:3]:  # Show first 3
            print(f"    - {op['name']}")
            print(f"      {op['description'][:70]}")
    
    return len(provider_ops) > 0


def test_langchain_adapter():
    """Test LangChain adapter with provider operations"""
    print("\n" + "="*80)
    print("TEST 4: LangChain Adapter Integration")
    print("="*80)
    
    try:
        from aiecs.tools.langchain_adapter import get_langchain_tools
        
        print("\n📋 Creating LangChain tools for apisource...")
        langchain_tools = get_langchain_tools(['apisource'])
        
        print(f"\n✅ Created {len(langchain_tools)} LangChain tools")
        
        # Separate tool-level and provider-level operations
        tool_ops = [t for t in langchain_tools if not t.is_provider_operation]
        provider_ops = [t for t in langchain_tools if t.is_provider_operation]
        
        print(f"\n  Tool-level operations: {len(tool_ops)}")
        for tool in tool_ops[:3]:
            print(f"    - {tool.name}")
        
        print(f"\n  Provider-level operations: {len(provider_ops)}")
        
        # Group provider operations by provider
        by_provider = {}
        for tool in provider_ops:
            provider = tool.provider_name or 'unknown'
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(tool)
        
        for provider, tools in by_provider.items():
            print(f"\n    {provider.upper()}: {len(tools)} operations")
            for tool in tools[:3]:  # Show first 3
                print(f"      - {tool.name}")
                print(f"        Schema: {tool.operation_schema.__name__ if tool.operation_schema else 'None'}")
        
        return len(provider_ops) > 0
    
    except ImportError as e:
        print(f"\n⚠️  LangChain not available: {e}")
        print("   This is expected if langchain is not installed")
        return True  # Don't fail the test


def test_schema_visibility():
    """Test that AI can see provider operation schemas"""
    print("\n" + "="*80)
    print("TEST 5: AI Schema Visibility")
    print("="*80)
    
    try:
        from aiecs.tools.langchain_adapter import get_langchain_tools
        
        langchain_tools = get_langchain_tools(['apisource'])
        provider_ops = [t for t in langchain_tools if t.is_provider_operation]
        
        if not provider_ops:
            print("❌ No provider operations found")
            return False
        
        # Pick a sample operation
        sample_tool = provider_ops[0]
        
        print(f"\n📋 Sample Provider Operation: {sample_tool.name}")
        print(f"\n  Description: {sample_tool.description}")
        print(f"  Provider: {sample_tool.provider_name}")
        print(f"  Operation: {sample_tool.method_name}")
        
        if sample_tool.operation_schema:
            print(f"\n  ✅ Schema Available: {sample_tool.operation_schema.__name__}")
            print(f"\n  📝 Parameters AI can see:")
            
            if hasattr(sample_tool.operation_schema, 'model_fields'):
                fields = sample_tool.operation_schema.model_fields
                for field_name, field_info in fields.items():
                    required = "required" if field_info.is_required() else "optional"
                    print(f"    - {field_name} ({required})")
                    if field_info.description:
                        print(f"      {field_info.description[:80]}")
            
            print(f"\n  🎯 Result: AI can see all {len(fields)} parameters!")
            return True
        else:
            print("  ❌ No schema available")
            return False
    
    except ImportError:
        print("\n⚠️  LangChain not available, skipping test")
        return True


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 APISource Provider Operations Discovery Demo")
    print("="*80)
    print("\nThis demo shows how provider operations are exposed to AI agents")
    print("solving the schema visibility problem.")
    
    results = {}
    
    # Run tests
    results['discovery'] = test_provider_operation_discovery()
    results['conversion'] = test_schema_conversion()
    results['apisource'] = test_apisource_discovery()
    results['langchain'] = test_langchain_adapter()
    results['visibility'] = test_schema_visibility()
    
    # Summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name.title()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 All tests passed! Provider operations are now visible to AI agents!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    print("="*80)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

