#!/usr/bin/env python3
"""
Check all registered tools in aiecs.tools module and analyze schema development status
This script avoids full package initialization to work around dependency issues
"""

import sys
import os
import re
import importlib
import inspect
from typing import Dict, List, Any, Type, Optional
from collections import defaultdict
from pydantic import BaseModel

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import only what we need, avoiding full package init
sys.path.insert(0, os.path.join(project_root, 'aiecs'))

# Import tool registry directly
from tools import TOOL_REGISTRY, TOOL_CLASSES
from tools.base_tool import BaseTool
from tools.schema_generator import generate_schema_from_method


def find_manual_schema(tool_class: Type, method_name: str) -> Optional[Type[BaseModel]]:
    """Find manually defined schema for a method"""
    schemas = {}
    
    # Check class-level schemas
    for attr_name in dir(tool_class):
        attr = getattr(tool_class, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
            schema_base_name = attr.__name__.replace("Schema", "")
            normalized_name = schema_base_name.replace("_", "").lower()
            schemas[normalized_name] = attr
    
    # Check module-level schemas
    tool_module = inspect.getmodule(tool_class)
    if tool_module:
        for attr_name in dir(tool_module):
            if attr_name.startswith("_"):
                continue
            attr = getattr(tool_module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
                schema_base_name = attr.__name__.replace("Schema", "")
                normalized_name = schema_base_name.replace("_", "").lower()
                if normalized_name not in schemas:
                    schemas[normalized_name] = attr
    
    # Normalize method name
    normalized_method_name = method_name.replace("_", "").lower()
    return schemas.get(normalized_method_name)


def analyze_tool_methods(tool_class: Type) -> Dict[str, Any]:
    """Analyze all methods of a tool class"""
    methods_info = []
    
    for method_name in dir(tool_class):
        # Skip private methods and special methods
        if method_name.startswith("_"):
            continue
        
        # Skip base class methods
        if method_name in ["run", "run_async", "run_batch"]:
            continue
        
        method = getattr(tool_class, method_name)
        
        # Skip non-method attributes
        if not callable(method) or isinstance(method, type):
            continue
        
        # Try to find manual schema
        manual_schema = find_manual_schema(tool_class, method_name)
        
        schema = None
        schema_type = None
        
        if manual_schema:
            schema = manual_schema
            schema_type = "manual"
        else:
            # Try to auto-generate schema
            try:
                schema = generate_schema_from_method(method, method_name)
                schema_type = "auto" if schema else None
            except Exception:
                schema_type = None
        
        methods_info.append({
            'name': method_name,
            'schema': schema,
            'schema_type': schema_type,
            'has_schema': schema is not None
        })
    
    return methods_info


def get_tool_class_from_registry(tool_name: str) -> Optional[Type]:
    """Get tool class from registry, importing if necessary"""
    # Check if already in TOOL_CLASSES
    if tool_name in TOOL_CLASSES:
        return TOOL_CLASSES[tool_name]
    
    # Check if in TOOL_REGISTRY
    if tool_name in TOOL_REGISTRY:
        tool_instance = TOOL_REGISTRY[tool_name]
        # Check if placeholder
        if hasattr(tool_instance, 'is_placeholder') and tool_instance.is_placeholder:
            # Need to import the actual module
            return import_tool_class(tool_name)
        else:
            return tool_instance.__class__
    
    return None


def import_tool_class(tool_name: str) -> Optional[Type]:
    """Import tool class by scanning tool directories"""
    tools_dir = os.path.join(project_root, 'aiecs', 'tools')
    tool_dirs = ['task_tools', 'docs', 'statistics', 'search_tool', 'apisource', 'knowledge_graph']
    
    for dir_name in tool_dirs:
        dir_path = os.path.join(tools_dir, dir_name)
        if not os.path.exists(dir_path):
            continue
        
        # Check __init__.py
        init_file = os.path.join(dir_path, '__init__.py')
        if os.path.exists(init_file):
            try:
                with open(init_file, 'r') as f:
                    content = f.read()
                    pattern = rf'register_tool\([\'"]{re.escape(tool_name)}[\'"]\)'
                    if re.search(pattern, content):
                        module_path = f'aiecs.tools.{dir_name}'
                        try:
                            module = importlib.import_module(module_path)
                            # Find Tool class
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and 
                                    attr_name.endswith('Tool') and 
                                    issubclass(attr, BaseTool)):
                                    return attr
                        except Exception:
                            pass
            except Exception:
                pass
        
        # Check individual files
        for filename in os.listdir(dir_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                file_path = os.path.join(dir_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        pattern = rf'register_tool\([\'"]{re.escape(tool_name)}[\'"]\)'
                        if re.search(pattern, content):
                            module_name = filename[:-3]
                            module_path = f'aiecs.tools.{dir_name}.{module_name}'
                            try:
                                module = importlib.import_module(module_path)
                                # Find Tool class
                                for attr_name in dir(module):
                                    attr = getattr(module, attr_name)
                                    if (isinstance(attr, type) and 
                                        attr_name.endswith('Tool') and 
                                        issubclass(attr, BaseTool)):
                                        return attr
                            except Exception:
                                pass
                except Exception:
                    pass
    
    return None


def main():
    """Main analysis function"""
    print("=" * 100)
    print("AIECS Tools Schema Development Status Analysis")
    print("=" * 100)
    
    # Get all registered tools
    all_tool_names = list(set(list(TOOL_REGISTRY.keys()) + list(TOOL_CLASSES.keys())))
    print(f"\nFound {len(all_tool_names)} registered tools\n")
    
    # Analyze each tool
    results = {}
    summary = {
        'total_tools': len(all_tool_names),
        'tools_analyzed': 0,
        'tools_with_errors': 0,
        'total_methods': 0,
        'methods_with_manual_schemas': 0,
        'methods_with_auto_schemas': 0,
        'methods_without_schemas': 0,
        'tools_by_category': defaultdict(int)
    }
    
    for tool_name in sorted(all_tool_names):
        print(f"Analyzing {tool_name}...", end=' ')
        try:
            tool_class = get_tool_class_from_registry(tool_name)
            
            if tool_class is None:
                print("❌ Class not found")
                results[tool_name] = {'status': 'not_found'}
                summary['tools_with_errors'] += 1
                continue
            
            # Get category
            category = 'unknown'
            if tool_name in TOOL_REGISTRY:
                tool_instance = TOOL_REGISTRY[tool_name]
                if hasattr(tool_instance, 'category'):
                    category = tool_instance.category
            elif hasattr(tool_class, 'category'):
                category = tool_class.category
            
            # Analyze methods
            methods_info = analyze_tool_methods(tool_class)
            
            manual_count = sum(1 for m in methods_info if m['schema_type'] == 'manual')
            auto_count = sum(1 for m in methods_info if m['schema_type'] == 'auto')
            no_schema_count = sum(1 for m in methods_info if not m['has_schema'])
            total_methods = len(methods_info)
            
            coverage = ((manual_count + auto_count) / total_methods * 100) if total_methods > 0 else 0
            
            results[tool_name] = {
                'status': 'success',
                'category': category,
                'class_name': tool_class.__name__,
                'module': tool_class.__module__,
                'total_methods': total_methods,
                'manual_schemas': manual_count,
                'auto_schemas': auto_count,
                'no_schemas': no_schema_count,
                'coverage': coverage,
                'methods': methods_info
            }
            
            # Update summary
            summary['tools_analyzed'] += 1
            summary['total_methods'] += total_methods
            summary['methods_with_manual_schemas'] += manual_count
            summary['methods_with_auto_schemas'] += auto_count
            summary['methods_without_schemas'] += no_schema_count
            summary['tools_by_category'][category] += 1
            
            status_icon = "✅" if coverage >= 80 else "⚠️" if coverage >= 50 else "❌"
            print(f"{status_icon} {coverage:.1f}% coverage ({manual_count} manual, {auto_count} auto, {no_schema_count} none)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results[tool_name] = {'status': 'error', 'error': str(e)}
            summary['tools_with_errors'] += 1
    
    # Print summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"\nTotal Tools: {summary['total_tools']}")
    print(f"Successfully Analyzed: {summary['tools_analyzed']}")
    print(f"Errors: {summary['tools_with_errors']}")
    print(f"\nTotal Methods: {summary['total_methods']}")
    print(f"  - With Manual Schemas: {summary['methods_with_manual_schemas']} ({summary['methods_with_manual_schemas']/summary['total_methods']*100:.1f}%)" if summary['total_methods'] > 0 else "N/A")
    print(f"  - With Auto Schemas: {summary['methods_with_auto_schemas']} ({summary['methods_with_auto_schemas']/summary['total_methods']*100:.1f}%)" if summary['total_methods'] > 0 else "N/A")
    print(f"  - Without Schemas: {summary['methods_without_schemas']} ({summary['methods_without_schemas']/summary['total_methods']*100:.1f}%)" if summary['total_methods'] > 0 else "N/A")
    
    overall_coverage = ((summary['methods_with_manual_schemas'] + summary['methods_with_auto_schemas']) / summary['total_methods'] * 100) if summary['total_methods'] > 0 else 0
    print(f"\nOverall Schema Coverage: {overall_coverage:.1f}%")
    
    print(f"\nTools by Category:")
    for category, count in sorted(summary['tools_by_category'].items()):
        print(f"  - {category}: {count}")
    
    # Print detailed breakdown by category
    print("\n" + "=" * 100)
    print("DETAILED BREAKDOWN BY CATEGORY")
    print("=" * 100)
    
    tools_by_category = defaultdict(list)
    for tool_name, result in results.items():
        if result.get('status') == 'success':
            category = result.get('category', 'unknown')
            tools_by_category[category].append((tool_name, result))
    
    for category in sorted(tools_by_category.keys()):
        tools = tools_by_category[category]
        print(f"\n{category.upper()} ({len(tools)} tools):")
        print("-" * 100)
        for tool_name, result in sorted(tools):
            coverage = result['coverage']
            icon = "✅" if coverage >= 80 else "⚠️" if coverage >= 50 else "❌"
            print(f"{icon} {tool_name:30s} | Methods: {result['total_methods']:3d} | "
                  f"Manual: {result['manual_schemas']:2d} | Auto: {result['auto_schemas']:2d} | "
                  f"None: {result['no_schemas']:2d} | Coverage: {coverage:5.1f}%")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()

