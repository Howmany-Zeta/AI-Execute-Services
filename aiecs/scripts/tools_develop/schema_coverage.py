#!/usr/bin/env python3
"""
Schema Coverage Reporter

Reports schema coverage across all tools with detailed metrics.
Supports multiple output formats: text, JSON, and HTML.

Usage:
    # Report coverage for all tools (text format)
    aiecs tools schema-coverage

    # Report coverage in JSON format
    aiecs tools schema-coverage --format json

    # Report coverage in HTML format
    aiecs tools schema-coverage --format html --output coverage.html

    # Report coverage for specific tools
    aiecs tools schema-coverage pandas stats

    # Set minimum coverage threshold
    aiecs tools schema-coverage --min-coverage 90
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

from aiecs.tools import discover_tools, TOOL_CLASSES, get_tool
from aiecs.scripts.tools_develop.validate_tool_schemas import (
    analyze_tool_schemas,
    SchemaQualityMetrics,
)

# Ensure we can import aiecs
import os
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
)


def generate_coverage_report(
    tool_names: Optional[List[str]] = None,
    format: str = "text",
    output: Optional[str] = None,
    min_coverage: float = 0.0,
) -> Dict[str, Any]:
    """
    Generate schema coverage report for tools.
    
    Args:
        tool_names: List of tool names to report on, None for all tools
        format: Output format ('text', 'json', 'html')
        output: Output file path (None for stdout)
        min_coverage: Minimum coverage threshold (0-100)
    
    Returns:
        Dictionary with coverage data
    """
    discover_tools()
    
    # Determine tools to check
    if tool_names:
        tools_to_check = {}
        for name in tool_names:
            if name in TOOL_CLASSES:
                tools_to_check[name] = TOOL_CLASSES[name]
            else:
                print(f"Warning: Tool '{name}' not found", file=sys.stderr)
        if not tools_to_check:
            print("No tools found to check", file=sys.stderr)
            return {}
    else:
        tools_to_check = TOOL_CLASSES
    
    # Analyze all tools
    all_results = {}
    for tool_name in sorted(tools_to_check.keys()):
        tool_class = tools_to_check[tool_name]
        result = analyze_tool_schemas(tool_name, tool_class)
        all_results[tool_name] = result
    
    # Calculate overall statistics
    total_methods = sum(r["metrics"].total_methods for r in all_results.values())
    total_generated = sum(r["metrics"].schemas_generated for r in all_results.values())
    total_fields = sum(r["metrics"].total_fields for r in all_results.values())
    total_meaningful = sum(r["metrics"].fields_with_meaningful_descriptions for r in all_results.values())
    total_with_types = sum(r["metrics"].fields_with_types for r in all_results.values())
    
    # Count manual vs auto schemas
    total_manual = 0
    total_auto = 0
    for result in all_results.values():
        methods = result["methods"]
        total_manual += len([m for m in methods if m.get("schema_type") == "manual"])
        total_auto += len([m for m in methods if m.get("schema_type") == "auto"])
    
    overall_generation = (total_generated / total_methods * 100) if total_methods > 0 else 0
    overall_description = (total_meaningful / total_fields * 100) if total_fields > 0 else 0
    overall_type_coverage = (total_with_types / total_fields * 100) if total_fields > 0 else 0
    overall_score = (overall_generation + overall_description + overall_type_coverage) / 3
    
    # Build report data
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tools": len(all_results),
            "total_methods": total_methods,
            "total_schemas": total_generated,
            "manual_schemas": total_manual,
            "auto_generated_schemas": total_auto,
            "missing_schemas": total_methods - total_generated,
            "coverage_percentage": overall_generation,
            "description_quality": overall_description,
            "type_coverage": overall_type_coverage,
            "overall_score": overall_score,
        },
        "tools": {},
    }
    
    # Add tool details
    for tool_name, result in all_results.items():
        metrics = result["metrics"]
        methods = result["methods"]
        scores = metrics.get_scores()
        
        manual_count = len([m for m in methods if m.get("schema_type") == "manual"])
        auto_count = len([m for m in methods if m.get("schema_type") == "auto"])
        
        report_data["tools"][tool_name] = {
            "total_methods": metrics.total_methods,
            "schemas_generated": metrics.schemas_generated,
            "manual_schemas": manual_count,
            "auto_generated_schemas": auto_count,
            "missing_schemas": metrics.total_methods - metrics.schemas_generated,
            "coverage_percentage": scores["generation_rate"],
            "description_quality": scores["description_quality"],
            "type_coverage": scores["type_coverage"],
            "overall_score": scores["overall_score"],
            "methods": [
                {
                    "name": m["name"],
                    "has_schema": m["schema"] is not None,
                    "schema_type": m.get("schema_type", "none"),
                    "issues": m.get("issues", []),
                }
                for m in methods
            ],
        }
    
    # Filter by minimum coverage if specified
    if min_coverage > 0:
        filtered_tools = {
            name: data
            for name, data in report_data["tools"].items()
            if data["coverage_percentage"] >= min_coverage
        }
        report_data["tools"] = filtered_tools
        report_data["summary"]["tools_meeting_threshold"] = len(filtered_tools)
    
    # Generate output based on format
    if format == "json":
        output_text = json.dumps(report_data, indent=2, ensure_ascii=False)
    elif format == "html":
        output_text = generate_html_report(report_data)
    else:  # text format
        output_text = generate_text_report(report_data, min_coverage)
    
    # Write output
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Report written to {output}", file=sys.stderr)
    else:
        print(output_text)
    
    return report_data


def generate_text_report(report_data: Dict[str, Any], min_coverage: float) -> str:
    """Generate text format report."""
    summary = report_data["summary"]
    tools = report_data["tools"]
    
    lines = []
    lines.append("=" * 100)
    lines.append("Schema Coverage Report")
    lines.append("=" * 100)
    lines.append(f"Generated: {report_data['timestamp']}")
    lines.append("")
    
    # Summary section
    lines.append("SUMMARY")
    lines.append("-" * 100)
    lines.append(f"Total Tools: {summary['total_tools']}")
    lines.append(f"Total Methods: {summary['total_methods']}")
    lines.append(f"Schemas Generated: {summary['total_schemas']} ({summary['coverage_percentage']:.1f}%)")
    lines.append(f"  - Manual: {summary['manual_schemas']}")
    lines.append(f"  - Auto-generated: {summary['auto_generated_schemas']}")
    lines.append(f"Missing Schemas: {summary['missing_schemas']}")
    lines.append(f"Description Quality: {summary['description_quality']:.1f}%")
    lines.append(f"Type Coverage: {summary['type_coverage']:.1f}%")
    lines.append(f"Overall Score: {summary['overall_score']:.1f}%")
    lines.append("")
    
    # Tools section
    lines.append("TOOLS DETAILS")
    lines.append("-" * 100)
    
    # Sort tools by coverage
    sorted_tools = sorted(
        tools.items(),
        key=lambda x: x[1]["coverage_percentage"],
        reverse=True
    )
    
    for tool_name, tool_data in sorted_tools:
        coverage = tool_data["coverage_percentage"]
        status = "✅" if coverage >= 90 else "⚠️" if coverage >= 70 else "❌"
        
        lines.append(f"\n{status} {tool_name}")
        lines.append(f"  Methods: {tool_data['total_methods']}")
        lines.append(f"  Coverage: {coverage:.1f}% ({tool_data['schemas_generated']}/{tool_data['total_methods']})")
        lines.append(f"    - Manual: {tool_data['manual_schemas']}")
        lines.append(f"    - Auto: {tool_data['auto_generated_schemas']}")
        lines.append(f"    - Missing: {tool_data['missing_schemas']}")
        lines.append(f"  Description Quality: {tool_data['description_quality']:.1f}%")
        lines.append(f"  Type Coverage: {tool_data['type_coverage']:.1f}%")
        lines.append(f"  Overall Score: {tool_data['overall_score']:.1f}%")
        
        # List methods without schemas
        missing_methods = [
            m["name"] for m in tool_data["methods"]
            if not m["has_schema"]
        ]
        if missing_methods:
            lines.append(f"  Missing Schemas: {', '.join(missing_methods)}")
    
    lines.append("")
    lines.append("=" * 100)
    
    return "\n".join(lines)


def generate_html_report(report_data: Dict[str, Any]) -> str:
    """Generate HTML format report."""
    summary = report_data["summary"]
    tools = report_data["tools"]
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Schema Coverage Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .summary {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .summary-item {
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }
        .summary-item h3 {
            margin: 0 0 5px 0;
            color: #666;
            font-size: 0.9em;
        }
        .summary-item .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status-good {
            color: #4CAF50;
            font-weight: bold;
        }
        .status-warning {
            color: #FF9800;
            font-weight: bold;
        }
        .status-bad {
            color: #F44336;
            font-weight: bold;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
        }
        .progress-fill.warning {
            background-color: #FF9800;
        }
        .progress-fill.bad {
            background-color: #F44336;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Schema Coverage Report</h1>
        <p>Generated: {timestamp}</p>
        
        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <h3>Total Tools</h3>
                    <div class="value">{total_tools}</div>
                </div>
                <div class="summary-item">
                    <h3>Total Methods</h3>
                    <div class="value">{total_methods}</div>
                </div>
                <div class="summary-item">
                    <h3>Coverage</h3>
                    <div class="value">{coverage:.1f}%</div>
                </div>
                <div class="summary-item">
                    <h3>Overall Score</h3>
                    <div class="value">{overall_score:.1f}%</div>
                </div>
            </div>
        </div>
        
        <h2>Tools Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Tool</th>
                    <th>Methods</th>
                    <th>Coverage</th>
                    <th>Manual</th>
                    <th>Auto</th>
                    <th>Missing</th>
                    <th>Description Quality</th>
                    <th>Type Coverage</th>
                    <th>Overall Score</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Sort tools by coverage
    sorted_tools = sorted(
        tools.items(),
        key=lambda x: x[1]["coverage_percentage"],
        reverse=True
    )
    
    for tool_name, tool_data in sorted_tools:
        coverage = tool_data["coverage_percentage"]
        status_class = "status-good" if coverage >= 90 else "status-warning" if coverage >= 70 else "status-bad"
        progress_class = "" if coverage >= 90 else "warning" if coverage >= 70 else "bad"
        
        html += f"""
                <tr>
                    <td><strong>{tool_name}</strong></td>
                    <td>{tool_data['total_methods']}</td>
                    <td>
                        <span class="{status_class}">{coverage:.1f}%</span>
                        <div class="progress-bar">
                            <div class="progress-fill {progress_class}" style="width: {coverage}%"></div>
                        </div>
                    </td>
                    <td>{tool_data['manual_schemas']}</td>
                    <td>{tool_data['auto_generated_schemas']}</td>
                    <td>{tool_data['missing_schemas']}</td>
                    <td>{tool_data['description_quality']:.1f}%</td>
                    <td>{tool_data['type_coverage']:.1f}%</td>
                    <td>{tool_data['overall_score']:.1f}%</td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    
    return html.format(
        timestamp=report_data["timestamp"],
        total_tools=summary["total_tools"],
        total_methods=summary["total_methods"],
        coverage=summary["coverage_percentage"],
        overall_score=summary["overall_score"],
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Report schema coverage across all tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Report coverage for all tools (text format)
  aiecs tools schema-coverage

  # Report coverage in JSON format
  aiecs tools schema-coverage --format json

  # Report coverage in HTML format
  aiecs tools schema-coverage --format html --output coverage.html

  # Report coverage for specific tools
  aiecs tools schema-coverage pandas stats

  # Set minimum coverage threshold
  aiecs tools schema-coverage --min-coverage 90
        """,
    )
    
    parser.add_argument(
        "tools",
        nargs="*",
        help="Tool names to report on (default: all tools)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "-m", "--min-coverage",
        type=float,
        default=0.0,
        help="Minimum coverage threshold (0-100, default: 0)"
    )
    
    args = parser.parse_args()
    
    tool_names = args.tools if args.tools else None
    generate_coverage_report(
        tool_names=tool_names,
        format=args.format,
        output=args.output,
        min_coverage=args.min_coverage,
    )


if __name__ == "__main__":
    main()

