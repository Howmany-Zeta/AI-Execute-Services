#!/usr/bin/env python3
"""
Comprehensive analysis of all registered tools in aiecs.tools module
Analyzes schema development status for each tool
"""

import sys
import os
import inspect
from typing import Dict, List, Any, Type, Optional
from collections import defaultdict
from pydantic import BaseModel

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import tool-related modules
try:
    from aiecs.tools import discover_tools, TOOL_CLASSES, TOOL_REGISTRY
    from aiecs.tools.schema_generator import generate_schema_from_method
    from aiecs.scripts.tools_develop.validate_tool_schemas import (
        find_manual_schema,
        analyze_tool_schemas,
        SchemaQualityMetrics
    )
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    print("Trying minimal imports...")
    # Try minimal import
    sys.path.insert(0, os.path.join(project_root, 'aiecs'))
    from tools import discover_tools, TOOL_CLASSES, TOOL_REGISTRY
    from tools.schema_generator import generate_schema_from_method


class ToolSchemaAnalysis:
    """Comprehensive tool schema analysis"""
    
    def __init__(self):
        self.tools_analysis = {}
        self.summary_stats = {
            'total_tools': 0,
            'tools_with_schemas': 0,
            'total_methods': 0,
            'methods_with_manual_schemas': 0,
            'methods_with_auto_schemas': 0,
            'methods_without_schemas': 0,
            'tools_by_category': defaultdict(int),
            'schema_coverage': 0.0,
            'quality_scores': []
        }
    
    def _find_tool_class_by_name(self, tool_name: str):
        """Try to find and import tool class by name"""
        import re
        import importlib
        
        # Map of tool names to their likely module paths
        tool_module_map = {
            'pandas': 'aiecs.tools.task_tools.pandas_tool',
            'chart': 'aiecs.tools.task_tools.chart_tool',
            'classfire': 'aiecs.tools.task_tools.classfire_tool',
            'image': 'aiecs.tools.task_tools.image_tool',
            'office': 'aiecs.tools.task_tools.office_tool',
            'report': 'aiecs.tools.task_tools.report_tool',
            'research': 'aiecs.tools.task_tools.research_tool',
            'scraper': 'aiecs.tools.task_tools.scraper_tool',
            'stats': 'aiecs.tools.task_tools.stats_tool',
            'search': 'aiecs.tools.search_tool.core',
            'apisource': 'aiecs.tools.apisource.tool',
        }
        
        # Try direct mapping first
        if tool_name in tool_module_map:
            try:
                module = importlib.import_module(tool_module_map[tool_name])
                # Look for class ending with 'Tool'
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name.endswith('Tool') and 
                        hasattr(attr, '__module__')):
                        return attr
            except Exception:
                pass
        
        # Try scanning tool directories
        tools_dir = os.path.join(project_root, 'aiecs', 'tools')
        tool_dirs = ['task_tools', 'docs', 'statistics', 'search_tool', 'apisource', 'knowledge_graph']
        
        for dir_name in tool_dirs:
            dir_path = os.path.join(tools_dir, dir_name)
            if not os.path.exists(dir_path):
                continue
            
            # Check __init__.py first
            init_file = os.path.join(dir_path, '__init__.py')
            if os.path.exists(init_file):
                try:
                    with open(init_file, 'r') as f:
                        content = f.read()
                        # Look for register_tool decorator with this tool name
                        pattern = rf'register_tool\([\'"]{re.escape(tool_name)}[\'"]\)'
                        if re.search(pattern, content):
                            # Try to import the module
                            module_path = f'aiecs.tools.{dir_name}'
                            module = importlib.import_module(module_path)
                            # Look for Tool class
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and 
                                    attr_name.endswith('Tool') and 
                                    hasattr(attr, '__module__')):
                                    return attr
                except Exception:
                    pass
            
            # Check individual Python files
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
                                module = importlib.import_module(module_path)
                                # Look for Tool class
                                for attr_name in dir(module):
                                    attr = getattr(module, attr_name)
                                    if (isinstance(attr, type) and 
                                        attr_name.endswith('Tool') and 
                                        hasattr(attr, '__module__')):
                                        return attr
                    except Exception:
                        pass
        
        return None
    
    def analyze_all_tools(self):
        """Analyze all registered tools"""
        print("=" * 100)
        print("AIECS Tools Schema Development Status Analysis")
        print("=" * 100)
        print("\nDiscovering tools...")
        
        # Discover all tools
        try:
            discover_tools()
        except Exception as e:
            print(f"Warning during tool discovery: {e}")
        
        # Get all tool names
        all_tool_names = list(set(list(TOOL_REGISTRY.keys()) + list(TOOL_CLASSES.keys())))
        self.summary_stats['total_tools'] = len(all_tool_names)
        
        print(f"Found {len(all_tool_names)} registered tools\n")
        
        # Analyze each tool
        for tool_name in sorted(all_tool_names):
            try:
                self.analyze_tool(tool_name)
            except Exception as e:
                print(f"Error analyzing tool {tool_name}: {e}")
                self.tools_analysis[tool_name] = {
                    'error': str(e),
                    'status': 'error'
                }
    
    def analyze_tool(self, tool_name: str):
        """Analyze a single tool"""
        tool_class = None
        
        # Get tool class
        if tool_name in TOOL_CLASSES:
            tool_class = TOOL_CLASSES[tool_name]
        elif tool_name in TOOL_REGISTRY:
            tool_instance = TOOL_REGISTRY[tool_name]
            # Check if placeholder
            if hasattr(tool_instance, 'is_placeholder') and tool_instance.is_placeholder:
                # Try to import the actual tool module
                # First, try to discover which module contains this tool
                tool_class = self._find_tool_class_by_name(tool_name)
            else:
                tool_class = tool_instance.__class__
        
        if tool_class is None:
            self.tools_analysis[tool_name] = {
                'status': 'not_found',
                'error': 'Tool class not found'
            }
            return
        
        # Analyze tool schemas
        try:
            result = analyze_tool_schemas(tool_name, tool_class)
            metrics = result['metrics']
            methods = result['methods']
            
            # Calculate statistics
            manual_count = sum(1 for m in methods if m.get('schema_type') == 'manual')
            auto_count = sum(1 for m in methods if m.get('schema_type') == 'auto')
            no_schema_count = sum(1 for m in methods if not m.get('schema'))
            
            scores = metrics.get_scores()
            
            # Get category
            category = 'unknown'
            if tool_name in TOOL_REGISTRY:
                tool_instance = TOOL_REGISTRY[tool_name]
                category = getattr(tool_instance, 'category', 'unknown')
            elif hasattr(tool_class, 'category'):
                category = tool_class.category
            
            self.tools_analysis[tool_name] = {
                'status': 'analyzed',
                'category': category,
                'class_name': tool_class.__name__,
                'module': tool_class.__module__,
                'total_methods': metrics.total_methods,
                'manual_schemas': manual_count,
                'auto_schemas': auto_count,
                'no_schemas': no_schema_count,
                'schema_coverage': (manual_count + auto_count) / metrics.total_methods * 100 if metrics.total_methods > 0 else 0,
                'quality_scores': scores,
                'methods': methods
            }
            
            # Update summary stats
            self.summary_stats['total_methods'] += metrics.total_methods
            self.summary_stats['methods_with_manual_schemas'] += manual_count
            self.summary_stats['methods_with_auto_schemas'] += auto_count
            self.summary_stats['methods_without_schemas'] += no_schema_count
            self.summary_stats['tools_by_category'][category] += 1
            
            if metrics.total_methods > 0 and (manual_count + auto_count) > 0:
                self.summary_stats['tools_with_schemas'] += 1
                self.summary_stats['quality_scores'].append(scores['overall_score'])
                
        except Exception as e:
            self.tools_analysis[tool_name] = {
                'status': 'analysis_error',
                'error': str(e)
            }
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "=" * 100)
        print("SUMMARY STATISTICS")
        print("=" * 100)
        
        total_tools = self.summary_stats['total_tools']
        total_methods = self.summary_stats['total_methods']
        manual_schemas = self.summary_stats['methods_with_manual_schemas']
        auto_schemas = self.summary_stats['methods_with_auto_schemas']
        no_schemas = self.summary_stats['methods_without_schemas']
        
        print(f"\nTotal Tools: {total_tools}")
        print(f"Tools with Schemas: {self.summary_stats['tools_with_schemas']} ({self.summary_stats['tools_with_schemas']/total_tools*100:.1f}%)" if total_tools > 0 else "N/A")
        
        print(f"\nTotal Methods: {total_methods}")
        print(f"  - With Manual Schemas: {manual_schemas} ({manual_schemas/total_methods*100:.1f}%)" if total_methods > 0 else "N/A")
        print(f"  - With Auto Schemas: {auto_schemas} ({auto_schemas/total_methods*100:.1f}%)" if total_methods > 0 else "N/A")
        print(f"  - Without Schemas: {no_schemas} ({no_schemas/total_methods*100:.1f}%)" if total_methods > 0 else "N/A")
        
        overall_coverage = (manual_schemas + auto_schemas) / total_methods * 100 if total_methods > 0 else 0
        print(f"\nOverall Schema Coverage: {overall_coverage:.1f}%")
        
        if self.summary_stats['quality_scores']:
            avg_quality = sum(self.summary_stats['quality_scores']) / len(self.summary_stats['quality_scores'])
            print(f"Average Schema Quality Score: {avg_quality:.1f}%")
        
        print(f"\nTools by Category:")
        for category, count in sorted(self.summary_stats['tools_by_category'].items()):
            print(f"  - {category}: {count}")
    
    def print_detailed_report(self, verbose=False):
        """Print detailed report for each tool"""
        print("\n" + "=" * 100)
        print("DETAILED TOOL ANALYSIS")
        print("=" * 100)
        
        # Group by category
        tools_by_category = defaultdict(list)
        for tool_name, analysis in self.tools_analysis.items():
            if analysis.get('status') == 'analyzed':
                category = analysis.get('category', 'unknown')
                tools_by_category[category].append((tool_name, analysis))
        
        # Print by category
        for category in sorted(tools_by_category.keys()):
            tools = tools_by_category[category]
            print(f"\n{'=' * 100}")
            print(f"Category: {category.upper()} ({len(tools)} tools)")
            print(f"{'=' * 100}")
            
            for tool_name, analysis in sorted(tools):
                self.print_tool_details(tool_name, analysis, verbose)
    
    def print_tool_details(self, tool_name: str, analysis: Dict, verbose: bool = False):
        """Print details for a single tool"""
        status_icon = "✅" if analysis.get('schema_coverage', 0) >= 80 else "⚠️" if analysis.get('schema_coverage', 0) >= 50 else "❌"
        
        print(f"\n{status_icon} {tool_name}")
        print(f"   Class: {analysis.get('class_name', 'N/A')}")
        print(f"   Module: {analysis.get('module', 'N/A')}")
        print(f"   Total Methods: {analysis.get('total_methods', 0)}")
        print(f"   Schema Coverage: {analysis.get('schema_coverage', 0):.1f}%")
        print(f"     - Manual Schemas: {analysis.get('manual_schemas', 0)}")
        print(f"     - Auto Schemas: {analysis.get('auto_schemas', 0)}")
        print(f"     - No Schemas: {analysis.get('no_schemas', 0)}")
        
        quality_scores = analysis.get('quality_scores', {})
        if quality_scores:
            overall = quality_scores.get('overall_score', 0)
            grade = "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D"
            print(f"   Quality Score: {overall:.1f}% ({grade})")
            print(f"     - Generation Rate: {quality_scores.get('generation_rate', 0):.1f}%")
            print(f"     - Description Quality: {quality_scores.get('description_quality', 0):.1f}%")
        
        if verbose and analysis.get('methods'):
            print(f"\n   Methods:")
            for method in analysis['methods'][:10]:  # Show first 10
                schema_type = method.get('schema_type', 'none')
                icon = "🔧" if schema_type == "manual" else "🤖" if schema_type == "auto" else "❌"
                print(f"     {icon} {method['name']} [{schema_type}]")
                if method.get('issues'):
                    for issue in method['issues'][:2]:  # Show first 2 issues
                        print(f"       {issue}")
            if len(analysis['methods']) > 10:
                print(f"     ... and {len(analysis['methods']) - 10} more methods")
    
    def print_schema_status_matrix(self):
        """Print a matrix showing schema development status"""
        print("\n" + "=" * 100)
        print("SCHEMA DEVELOPMENT STATUS MATRIX")
        print("=" * 100)
        
        # Categorize tools by schema status
        excellent = []  # >= 90% coverage, quality >= 80
        good = []       # >= 70% coverage
        fair = []       # >= 50% coverage
        poor = []       # < 50% coverage
        no_schemas = []
        errors = []
        
        for tool_name, analysis in self.tools_analysis.items():
            if analysis.get('status') != 'analyzed':
                if analysis.get('status') == 'error' or analysis.get('status') == 'analysis_error':
                    errors.append(tool_name)
                continue
            
            coverage = analysis.get('schema_coverage', 0)
            quality = analysis.get('quality_scores', {}).get('overall_score', 0)
            
            if coverage >= 90 and quality >= 80:
                excellent.append((tool_name, analysis))
            elif coverage >= 70:
                good.append((tool_name, analysis))
            elif coverage >= 50:
                fair.append((tool_name, analysis))
            elif coverage > 0:
                poor.append((tool_name, analysis))
            else:
                no_schemas.append((tool_name, analysis))
        
        print(f"\n✅ Excellent (≥90% coverage, ≥80% quality): {len(excellent)}")
        for tool_name, _ in excellent[:5]:
            print(f"   - {tool_name}")
        if len(excellent) > 5:
            print(f"   ... and {len(excellent) - 5} more")
        
        print(f"\n⚠️  Good (≥70% coverage): {len(good)}")
        for tool_name, _ in good[:5]:
            print(f"   - {tool_name}")
        if len(good) > 5:
            print(f"   ... and {len(good) - 5} more")
        
        print(f"\n⚠️  Fair (≥50% coverage): {len(fair)}")
        for tool_name, _ in fair[:5]:
            print(f"   - {tool_name}")
        if len(fair) > 5:
            print(f"   ... and {len(fair) - 5} more")
        
        print(f"\n❌ Poor (<50% coverage): {len(poor)}")
        for tool_name, _ in poor[:5]:
            print(f"   - {tool_name}")
        if len(poor) > 5:
            print(f"   ... and {len(poor) - 5} more")
        
        print(f"\n❌ No Schemas: {len(no_schemas)}")
        for tool_name, _ in no_schemas[:5]:
            print(f"   - {tool_name}")
        if len(no_schemas) > 5:
            print(f"   ... and {len(no_schemas) - 5} more")
        
        if errors:
            print(f"\n⚠️  Errors: {len(errors)}")
            for tool_name in errors[:5]:
                print(f"   - {tool_name}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze schema development status for all registered tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose details')
    parser.add_argument('-s', '--summary-only', action='store_true', help='Show only summary statistics')
    parser.add_argument('-m', '--matrix', action='store_true', help='Show schema status matrix')
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = ToolSchemaAnalysis()
    analyzer.analyze_all_tools()
    
    # Print reports
    if args.summary_only:
        analyzer.print_summary()
    else:
        analyzer.print_summary()
        analyzer.print_detailed_report(verbose=args.verbose)
    
    if args.matrix or not args.summary_only:
        analyzer.print_schema_status_matrix()
    
    print("\n" + "=" * 100)
    print("Analysis Complete")
    print("=" * 100)


if __name__ == "__main__":
    main()

