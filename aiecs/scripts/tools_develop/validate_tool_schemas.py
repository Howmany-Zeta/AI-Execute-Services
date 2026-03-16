#!/usr/bin/env python3
"""
工具 Schema 质量验证器

用于工具开发和维护，验证自动生成的 Schema 质量。
帮助开发者识别需要改进的文档字符串，提升 Schema 描述质量。

使用方法:
    # 验证所有工具
    aiecs tools validate-schemas

    # 验证特定工具
    aiecs tools validate-schemas pandas

    # 显示详细的改进建议
    aiecs tools validate-schemas pandas --verbose

    # 显示示例 Schema
    aiecs tools validate-schemas pandas --show-examples
"""

from aiecs.tools.schema_generator import generate_schema_from_method
from aiecs.tools import discover_tools, TOOL_CLASSES
import sys
from typing import Dict, List, Any, Type, Optional, Callable
from pydantic import BaseModel

# 确保可以导入 aiecs
import os

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
)


class SchemaQualityMetrics:
    """Schema 质量指标"""

    def __init__(self):
        self.total_methods = 0
        self.schemas_generated = 0
        self.schemas_failed = 0
        self.total_fields = 0
        self.fields_with_meaningful_descriptions = 0
        self.fields_with_types = 0
        self.quality_issues = []

    def add_method(self, has_schema: bool):
        """添加方法统计"""
        self.total_methods += 1
        if has_schema:
            self.schemas_generated += 1
        else:
            self.schemas_failed += 1

    def add_field(self, has_type: bool, has_meaningful_desc: bool):
        """添加字段统计"""
        self.total_fields += 1
        if has_type:
            self.fields_with_types += 1
        if has_meaningful_desc:
            self.fields_with_meaningful_descriptions += 1

    def add_issue(self, issue: str):
        """添加质量问题"""
        self.quality_issues.append(issue)

    def get_scores(self) -> Dict[str, float]:
        """计算质量分数"""
        generation_rate = (self.schemas_generated / self.total_methods * 100) if self.total_methods > 0 else 0
        description_rate = (self.fields_with_meaningful_descriptions / self.total_fields * 100) if self.total_fields > 0 else 0
        type_coverage = (self.fields_with_types / self.total_fields * 100) if self.total_fields > 0 else 0

        return {
            "generation_rate": generation_rate,
            "description_quality": description_rate,
            "type_coverage": type_coverage,
            "overall_score": (generation_rate + description_rate + type_coverage) / 3,
        }


def validate_schema_quality(schema: Type[BaseModel], method: Callable[..., Any], method_name: str) -> List[str]:
    """
    验证单个 Schema 的质量

    Returns:
        质量问题列表（改进建议）
    """
    issues = []

    # 1. 检查 Schema 描述
    if not schema.__doc__ or schema.__doc__.strip() == f"Execute {method_name} operation":
        issues.append("💡 在方法文档字符串的第一行添加有意义的描述")

    # 2. 检查字段
    if not schema.model_fields:
        return issues

    for field_name, field_info in schema.model_fields.items():
        # 检查字段描述
        description = field_info.description
        if not description or description == f"Parameter {field_name}":
            issues.append(f"💡 在文档字符串的 Args 部分为参数 '{field_name}' 添加描述")

    return issues


def find_manual_schema(tool_class: Type, method_name: str) -> Optional[Type[BaseModel]]:
    """
    查找手动定义的 Schema（与 langchain_adapter 逻辑一致）

    Args:
        tool_class: 工具类
        method_name: 方法名

    Returns:
        找到的 Schema 类，如果没有则返回 None
    """
    schemas = {}

    # 1. 检查类级别的 schemas
    for attr_name in dir(tool_class):
        attr = getattr(tool_class, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr.__name__.endswith("Schema"):
            # 标准化：移除 'Schema' 后缀，转小写，移除下划线
            schema_base_name = attr.__name__.replace("Schema", "")
            normalized_name = schema_base_name.replace("_", "").lower()
            schemas[normalized_name] = attr

    # 2. 检查模块级别的 schemas
    import inspect

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

    # 标准化方法名：移除下划线并转小写
    normalized_method_name = method_name.replace("_", "").lower()

    # 查找匹配的 schema
    return schemas.get(normalized_method_name)


def analyze_tool_schemas(tool_name: str, tool_class: Type) -> Dict[str, Any]:
    """分析工具的 Schema 生成情况（支持手动定义和自动生成）"""

    metrics = SchemaQualityMetrics()
    methods_info = []

    for method_name in dir(tool_class):
        # 跳过私有方法和特殊方法
        if method_name.startswith("_"):
            continue

        # 跳过基类方法
        if method_name in ["run", "run_async", "run_batch", "close", "get_schema_coverage"]:
            continue

        method = getattr(tool_class, method_name)

        # 跳过非方法属性
        if not callable(method) or isinstance(method, type):
            continue

        # 首先尝试查找手动定义的 Schema
        manual_schema = find_manual_schema(tool_class, method_name)

        schema: Optional[Type[BaseModel]]
        if manual_schema:
            schema = manual_schema
            schema_type = "manual"
        else:
            # 如果没有手动 Schema，则自动生成
            schema = generate_schema_from_method(method, method_name)
            schema_type = "auto"

        method_info: Dict[str, Any] = {
            "name": method_name,
            "schema": schema,
            "schema_type": schema_type,
            "issues": [],
        }

        if schema:
            metrics.add_method(True)

            # 验证质量
            issues = validate_schema_quality(schema, method, method_name)
            method_info["issues"] = issues

            # 统计字段
            for field_name, field_info in schema.model_fields.items():
                has_type = field_info.annotation is not None
                has_meaningful_desc = bool(field_info.description and field_info.description != f"Parameter {field_name}")
                metrics.add_field(has_type, has_meaningful_desc)

            # 记录问题
            for issue in issues:
                metrics.add_issue(f"{tool_name}.{method_name}: {issue}")
        else:
            metrics.add_method(False)
            method_info["issues"] = ["⚠️  无法生成 Schema（可能是无参数方法）"]

        methods_info.append(method_info)

    return {"metrics": metrics, "methods": methods_info}


def print_tool_report(
    tool_name: str,
    result: Dict,
    verbose: bool = False,
    show_examples: bool = False,
):
    """打印工具报告"""

    metrics = result["metrics"]
    methods = result["methods"]
    scores = metrics.get_scores()

    # 统计手动和自动 schema
    manual_schemas = [m for m in methods if m.get("schema_type") == "manual"]
    auto_schemas = [m for m in methods if m.get("schema_type") == "auto"]

    # 状态图标
    overall = scores["overall_score"]
    if overall >= 90:
        status = "✅"
        grade = "A (优秀)"
    elif overall >= 80:
        status = "⚠️"
        grade = "B (良好)"
    elif overall >= 70:
        status = "⚠️"
        grade = "C (中等)"
    else:
        status = "❌"
        grade = "D (需改进)"

    print(f"\n{status} {tool_name}")
    print(f"  方法数: {metrics.total_methods}")
    print(f"  成功生成 Schema: {metrics.schemas_generated} ({scores['generation_rate']:.1f}%)")
    print(f"    - 手动定义: {len(manual_schemas)} 个")
    print(f"    - 自动生成: {len(auto_schemas)} 个")
    print(f"  描述质量: {scores['description_quality']:.1f}%")
    print(f"  综合评分: {scores['overall_score']:.1f}% ({grade})")

    # 显示需要改进的方法
    methods_with_issues = [m for m in methods if m["issues"] and m["schema"]]

    if methods_with_issues and (verbose or scores["description_quality"] < 80):
        print(f"\n  需要改进的方法 ({len(methods_with_issues)} 个):")

        for method_info in methods_with_issues[: 5 if not verbose else None]:
            print(f"\n    {method_info['name']}:")
            for issue in method_info["issues"]:
                print(f"      {issue}")

        if not verbose and len(methods_with_issues) > 5:
            print(f"\n    ... 还有 {len(methods_with_issues) - 5} 个方法需要改进")
            print("    使用 --verbose 查看全部")

    # 显示示例 Schema
    if show_examples:
        methods_with_schema = [m for m in methods if m["schema"]]
        if methods_with_schema:
            print("\n  示例 Schema:")
            for method_info in methods_with_schema[:2]:
                schema = method_info["schema"]
                schema_type_label = "🔧 手动定义" if method_info.get("schema_type") == "manual" else "🤖 自动生成"
                print(f"\n    {method_info['name']} → {schema.__name__} [{schema_type_label}]")
                print(f"      描述: {schema.__doc__}")
                print("      字段:")
                for field_name, field_info in list(schema.model_fields.items())[:3]:
                    required = "必需" if field_info.is_required() else "可选"
                    print(f"        - {field_name}: {field_info.description} [{required}]")


def validate_schemas(
    tool_names: Optional[List[str]] = None,
    verbose: bool = False,
    show_examples: bool = False,
    export_coverage: Optional[str] = None,
    min_coverage: float = 0.0,
) -> Dict[str, Any]:
    """
    验证工具的 Schema 质量

    Args:
        tool_names: 要验证的工具名称列表，None 表示验证所有工具
        verbose: 是否显示详细信息
        show_examples: 是否显示示例 Schema
        export_coverage: 导出覆盖率报告的文件路径（支持 .json, .html, .txt）
        min_coverage: 最小覆盖率阈值（0-100），低于此值的工具会被标记

    Returns:
        包含所有工具分析结果的字典
    """
    print("=" * 100)
    print("工具 Schema 质量验证器")
    print("=" * 100)

    discover_tools()

    # 确定要验证的工具
    if tool_names:
        tools_to_check = {}
        for name in tool_names:
            if name in TOOL_CLASSES:
                tools_to_check[name] = TOOL_CLASSES[name]
            else:
                print(f"\n❌ 工具 '{name}' 不存在")

        if not tools_to_check:
            print("\n没有找到要验证的工具")
            return {}
    else:
        tools_to_check = TOOL_CLASSES

    # 验证每个工具
    all_results = {}
    for tool_name in sorted(tools_to_check.keys()):
        tool_class = tools_to_check[tool_name]
        result = analyze_tool_schemas(tool_name, tool_class)
        all_results[tool_name] = result

        print_tool_report(tool_name, result, verbose, show_examples)

    # 总体统计
    if len(all_results) > 1:
        total_methods = sum(r["metrics"].total_methods for r in all_results.values())
        total_generated = sum(r["metrics"].schemas_generated for r in all_results.values())
        total_fields = sum(r["metrics"].total_fields for r in all_results.values())
        total_meaningful = sum(r["metrics"].fields_with_meaningful_descriptions for r in all_results.values())
        total_with_types = sum(r["metrics"].fields_with_types for r in all_results.values())

        overall_generation = (total_generated / total_methods * 100) if total_methods > 0 else 0
        overall_description = (total_meaningful / total_fields * 100) if total_fields > 0 else 0
        overall_type_coverage = (total_with_types / total_fields * 100) if total_fields > 0 else 0
        overall_score = (overall_generation + overall_description + overall_type_coverage) / 3

        print("\n" + "=" * 100)
        print("总体统计:")
        print(f"  工具数: {len(all_results)}")
        print(f"  方法数: {total_methods}")
        print(f"  Schema 生成率: {total_generated}/{total_methods} ({overall_generation:.1f}%)")
        print(f"  描述质量: {overall_description:.1f}%")
        print(f"  类型覆盖率: {overall_type_coverage:.1f}%")
        print(f"  综合评分: {overall_score:.1f}%")
        print("=" * 100)

        # Coverage summary by tool
        print("\n覆盖率摘要:")
        tools_by_coverage = []
        for tool_name, result in all_results.items():
            metrics = result["metrics"]
            scores = metrics.get_scores()
            coverage = scores["generation_rate"]
            tools_by_coverage.append((tool_name, coverage, scores))

        # Sort by coverage (lowest first)
        tools_by_coverage.sort(key=lambda x: x[1])

        # Show tools below 90%
        low_coverage_tools = [t for t in tools_by_coverage if t[1] < 90]
        if low_coverage_tools:
            print(f"\n  需要改进的工具 ({len(low_coverage_tools)} 个，覆盖率 < 90%):")
            for tool_name, coverage, scores in low_coverage_tools[:10]:
                print(f"    - {tool_name}: {coverage:.1f}% (生成率: {scores['generation_rate']:.1f}%, " f"描述: {scores['description_quality']:.1f}%, 类型: {scores['type_coverage']:.1f}%)")
            if len(low_coverage_tools) > 10:
                print(f"    ... 还有 {len(low_coverage_tools) - 10} 个工具需要改进")

        # Show tools at 90%+
        high_coverage_tools = [t for t in tools_by_coverage if t[1] >= 90]
        if high_coverage_tools:
            print(f"\n  ✅ 达标工具 ({len(high_coverage_tools)} 个，覆盖率 ≥ 90%):")
            for tool_name, coverage, scores in high_coverage_tools[:5]:
                print(f"    - {tool_name}: {coverage:.1f}%")
            if len(high_coverage_tools) > 5:
                print(f"    ... 还有 {len(high_coverage_tools) - 5} 个工具已达标")

    print("\n💡 改进建议:")
    print("  1. 在方法的文档字符串第一行添加简短描述")
    print("  2. 在 Args 部分为每个参数添加详细描述")
    print("  3. 使用 Google 或 NumPy 风格的文档字符串")
    print("\n示例:")
    print("  def filter(self, records: List[Dict], condition: str) -> List[Dict]:")
    print('      """')
    print("      Filter DataFrame based on a condition.")
    print("      ")
    print("      Args:")
    print("          records: List of records to filter")
    print("          condition: Filter condition (pandas query syntax)")
    print('      """')

    # Export coverage report if requested
    if export_coverage:
        from aiecs.scripts.tools_develop.schema_coverage import generate_coverage_report

        report_format = "json" if export_coverage.endswith(".json") else "html" if export_coverage.endswith(".html") else "text"
        generate_coverage_report(
            tool_names=tool_names,
            format=report_format,
            output=export_coverage,
            min_coverage=min_coverage,
        )

    return all_results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="验证工具 Schema 的生成质量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 验证所有工具
  aiecs tools validate-schemas

  # 验证特定工具
  aiecs tools validate-schemas pandas

  # 显示详细的改进建议
  aiecs tools validate-schemas pandas --verbose

  # 显示示例 Schema
  aiecs tools validate-schemas pandas --show-examples
        """,
    )

    parser.add_argument("tools", nargs="*", help="要验证的工具名称（不指定则验证所有工具）")

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细的改进建议")

    parser.add_argument("-e", "--show-examples", action="store_true", help="显示示例 Schema")

    parser.add_argument("--export-coverage", type=str, help="导出覆盖率报告到文件（支持 .json, .html, .txt 格式）")

    parser.add_argument("--min-coverage", type=float, default=0.0, help="最小覆盖率阈值（0-100），用于导出报告时过滤工具")

    args = parser.parse_args()

    tool_names = args.tools if args.tools else None
    validate_schemas(
        tool_names,
        args.verbose,
        args.show_examples,
        args.export_coverage,
        args.min_coverage,
    )


if __name__ == "__main__":
    main()
