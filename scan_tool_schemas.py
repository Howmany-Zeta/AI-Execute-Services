#!/usr/bin/env python3
"""
Scan all tool files in aiecs.tools module and analyze schema development status
This script reads files directly without importing the full package
"""

import os
import re
import ast
from typing import Dict, List, Any, Set
from collections import defaultdict

project_root = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.join(project_root, 'aiecs', 'tools')


def find_registered_tools() -> Dict[str, Dict[str, Any]]:
    """Find all registered tools by scanning tool directories"""
    tools = {}
    tool_dirs = ['task_tools', 'docs', 'statistics', 'search_tool', 'apisource', 'knowledge_graph']
    
    for dir_name in tool_dirs:
        dir_path = os.path.join(tools_dir, dir_name)
        if not os.path.exists(dir_path):
            continue
        
        # Check __init__.py
        init_file = os.path.join(dir_path, '__init__.py')
        if os.path.exists(init_file):
            scan_file_for_tools(init_file, dir_name, tools)
        
        # Check individual Python files
        for filename in os.listdir(dir_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                file_path = os.path.join(dir_path, filename)
                scan_file_for_tools(file_path, dir_name, tools)
    
    return tools


def scan_file_for_tools(file_path: str, category: str, tools: Dict):
    """Scan a Python file for registered tools"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find register_tool decorators
        # Pattern 1: @register_tool("name")
        decorator_pattern = r'@register_tool\([\'"]([^\'"]+)[\'"]\)'
        decorator_matches = re.findall(decorator_pattern, content)
        
        # Pattern 2: register_tool("name")(ClassName)
        function_pattern = r'register_tool\([\'"]([^\'"]+)[\'"]\)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)'
        function_matches = re.findall(function_pattern, content)
        
        # Process decorator matches
        for tool_name in decorator_matches:
            if tool_name not in tools:
                tools[tool_name] = {
                    'name': tool_name,
                    'category': category,
                    'file': file_path,
                    'class_name': None,
                    'methods': [],
                    'schemas': []
                }
        
        # Process function matches
        for tool_name, class_name in function_matches:
            if tool_name not in tools:
                tools[tool_name] = {
                    'name': tool_name,
                    'category': category,
                    'file': file_path,
                    'class_name': class_name,
                    'methods': [],
                    'schemas': []
                }
            else:
                tools[tool_name]['class_name'] = class_name
        
        # Try to parse AST to find class definition
        try:
            tree = ast.parse(content)
            registered_tool_names = decorator_matches + [m[0] for m in function_matches]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this class is registered as a tool
                    # Look for decorators on the class
                    class_decorators = []
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Name) and decorator.func.id == 'register_tool':
                                # Extract tool name from decorator
                                if decorator.args and isinstance(decorator.args[0], (ast.Str, ast.Constant)):
                                    tool_name_from_decorator = decorator.args[0].s if isinstance(decorator.args[0], ast.Str) else decorator.args[0].value
                                    class_decorators.append(tool_name_from_decorator)
                    
                    # Also check if class name matches any registered tool
                    for tool_name in registered_tool_names:
                        if tool_name in tools:
                            # Check if this class is the tool class (ends with Tool)
                            if node.name.endswith('Tool') or tool_name in class_decorators:
                                analyze_class_for_schemas(node, content, tools[tool_name])
                                break
        except Exception as e:
            # Fallback: use regex to find methods and schemas
            try:
                for tool_name in decorator_matches + [m[0] for m in function_matches]:
                    if tool_name in tools:
                        # Find class definition
                        class_pattern = rf'class\s+(\w+Tool)\s*\([^)]*BaseTool[^)]*\):'
                        class_match = re.search(class_pattern, content)
                        if class_match:
                            # Find methods (def method_name(...))
                            method_pattern = r'^\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*:'
                            methods = re.findall(method_pattern, content, re.MULTILINE)
                            methods = [m for m in methods if not m.startswith('_') and m not in ['run', 'run_async', 'run_batch']]
                            
                            # Find Schema classes
                            schema_pattern = r'class\s+(\w+Schema)\s*\([^)]*BaseModel[^)]*\):'
                            schemas = re.findall(schema_pattern, content)
                            
                            tools[tool_name]['methods'] = methods
                            tools[tool_name]['schemas'] = schemas
                            
                            # Match schemas to methods
                            schema_map = {}
                            for schema_name in schemas:
                                method_name = schema_name.replace('Schema', '').lower().replace('_', '')
                                schema_map[method_name] = schema_name
                            
                            methods_with_schemas = sum(1 for m in methods if m.lower().replace('_', '') in schema_map)
                            tools[tool_name]['methods_with_schemas'] = methods_with_schemas
                            tools[tool_name]['total_methods'] = len(methods)
                            tools[tool_name]['schema_coverage'] = (methods_with_schemas / len(methods) * 100) if methods else 0
            except Exception:
                pass
            
    except Exception as e:
        pass


def analyze_class_for_schemas(class_node: ast.ClassDef, file_content: str, tool_info: Dict):
    """Analyze a class AST node for methods and schemas"""
    # Find all methods
    methods = []
    schemas = []
    
    # Also search for schemas in module-level (outside class)
    try:
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith('Schema'):
                # Check if it's a BaseModel subclass
                for base in node.bases:
                    if isinstance(base, ast.Name) and 'BaseModel' in base.id:
                        schemas.append(node.name)
                    elif isinstance(base, ast.Attribute) and 'BaseModel' in ast.unparse(base):
                        schemas.append(node.name)
    except Exception:
        pass
    
    # Find methods in the class
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            # Skip private methods and special methods
            if not node.name.startswith('_') and node.name not in ['run', 'run_async', 'run_batch']:
                methods.append(node.name)
        
        elif isinstance(node, ast.ClassDef):
            # Check if it's a Schema class
            if node.name.endswith('Schema'):
                schemas.append(node.name)
    
    tool_info['methods'] = methods
    tool_info['schemas'] = schemas
    
    # Try to match schemas to methods
    schema_map = {}
    for schema_name in schemas:
        # Remove 'Schema' suffix and normalize
        method_name = schema_name.replace('Schema', '').lower().replace('_', '')
        schema_map[method_name] = schema_name
    
    # Count schema coverage
    methods_with_schemas = 0
    for method_name in methods:
        normalized = method_name.lower().replace('_', '')
        if normalized in schema_map:
            methods_with_schemas += 1
    
    tool_info['methods_with_schemas'] = methods_with_schemas
    tool_info['total_methods'] = len(methods)
    tool_info['schema_coverage'] = (methods_with_schemas / len(methods) * 100) if methods else 0


def main():
    """Main analysis function"""
    print("=" * 100)
    print("AIECS Tools Schema Development Status Analysis")
    print("=" * 100)
    print("\nScanning tool files...")
    
    # Find all registered tools
    tools = find_registered_tools()
    
    print(f"Found {len(tools)} registered tools\n")
    
    # Analyze and print results
    summary = {
        'total_tools': len(tools),
        'total_methods': 0,
        'methods_with_schemas': 0,
        'tools_by_category': defaultdict(int)
    }
    
    # Group by category
    tools_by_category = defaultdict(list)
    for tool_name, tool_info in tools.items():
        category = tool_info.get('category', 'unknown')
        tools_by_category[category].append((tool_name, tool_info))
        summary['tools_by_category'][category] += 1
        summary['total_methods'] += tool_info.get('total_methods', 0)
        summary['methods_with_schemas'] += tool_info.get('methods_with_schemas', 0)
    
    # Print summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"\nTotal Tools: {summary['total_tools']}")
    print(f"Total Methods: {summary['total_methods']}")
    print(f"Methods with Schemas: {summary['methods_with_schemas']} ({summary['methods_with_schemas']/summary['total_methods']*100:.1f}%)" if summary['total_methods'] > 0 else "N/A")
    
    overall_coverage = (summary['methods_with_schemas'] / summary['total_methods'] * 100) if summary['total_methods'] > 0 else 0
    print(f"Overall Schema Coverage: {overall_coverage:.1f}%")
    
    print(f"\nTools by Category:")
    for category, count in sorted(summary['tools_by_category'].items()):
        print(f"  - {category}: {count}")
    
    # Print detailed breakdown
    print("\n" + "=" * 100)
    print("DETAILED BREAKDOWN BY CATEGORY")
    print("=" * 100)
    
    for category in sorted(tools_by_category.keys()):
        tools_list = tools_by_category[category]
        print(f"\n{category.upper()} ({len(tools_list)} tools):")
        print("-" * 100)
        
        for tool_name, tool_info in sorted(tools_list):
            total_methods = tool_info.get('total_methods', 0)
            methods_with_schemas = tool_info.get('methods_with_schemas', 0)
            coverage = tool_info.get('schema_coverage', 0)
            schemas_count = len(tool_info.get('schemas', []))
            
            icon = "✅" if coverage >= 80 else "⚠️" if coverage >= 50 else "❌"
            
            print(f"{icon} {tool_name:30s} | Methods: {total_methods:3d} | "
                  f"Schemas: {schemas_count:2d} | Coverage: {coverage:5.1f}%")
            
            # Show schema details if available
            if schemas_count > 0 and total_methods > 0:
                schema_list = tool_info.get('schemas', [])
                if len(schema_list) <= 5:
                    print(f"    Schemas: {', '.join(schema_list)}")
                else:
                    print(f"    Schemas: {', '.join(schema_list[:5])} ... ({len(schema_list)} total)")
    
    # Schema development status matrix
    print("\n" + "=" * 100)
    print("SCHEMA DEVELOPMENT STATUS MATRIX")
    print("=" * 100)
    
    excellent = []
    good = []
    fair = []
    poor = []
    no_schemas = []
    
    for tool_name, tool_info in tools.items():
        coverage = tool_info.get('schema_coverage', 0)
        total_methods = tool_info.get('total_methods', 0)
        
        if total_methods == 0:
            no_schemas.append(tool_name)
        elif coverage >= 90:
            excellent.append(tool_name)
        elif coverage >= 70:
            good.append(tool_name)
        elif coverage >= 50:
            fair.append(tool_name)
        else:
            poor.append(tool_name)
    
    print(f"\n✅ Excellent (≥90% coverage): {len(excellent)}")
    for name in excellent[:10]:
        print(f"   - {name}")
    if len(excellent) > 10:
        print(f"   ... and {len(excellent) - 10} more")
    
    print(f"\n⚠️  Good (≥70% coverage): {len(good)}")
    for name in good[:10]:
        print(f"   - {name}")
    if len(good) > 10:
        print(f"   ... and {len(good) - 10} more")
    
    print(f"\n⚠️  Fair (≥50% coverage): {len(fair)}")
    for name in fair[:10]:
        print(f"   - {name}")
    if len(fair) > 10:
        print(f"   ... and {len(fair) - 10} more")
    
    print(f"\n❌ Poor (<50% coverage): {len(poor)}")
    for name in poor[:10]:
        print(f"   - {name}")
    if len(poor) > 10:
        print(f"   ... and {len(poor) - 10} more")
    
    print(f"\n❌ No Schemas: {len(no_schemas)}")
    for name in no_schemas[:10]:
        print(f"   - {name}")
    if len(no_schemas) > 10:
        print(f"   ... and {len(no_schemas) - 10} more")
    
    print("\n" + "=" * 100)
    print("Analysis Complete")
    print("=" * 100)


if __name__ == "__main__":
    main()

