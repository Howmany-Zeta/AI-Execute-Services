#!/usr/bin/env python3
"""
工具类型注解检查器

用于工具开发和维护，检查工具方法的类型注解完整性。
帮助开发者确保工具方法有完整的类型注解，为自动 Schema 生成提供基础。

使用方法:
    # 检查所有工具
    aiecs tools check-annotations

    # 检查特定工具
    aiecs tools check-annotations pandas

    # 检查多个工具
    aiecs tools check-annotations pandas chart image
"""

from aiecs.tools import discover_tools, TOOL_CLASSES
import sys
import inspect
from typing import get_type_hints, Optional, List, Dict

# 确保可以导入 aiecs
import os

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
)


def check_method_type_annotations(method, method_name):
    """
    检查方法的类型注解完整性

    Returns:
        dict: {
            'has_annotations': bool,
            'complete': bool,
            'params_with_types': list,
            'params_without_types': list,
            'has_return_type': bool,
            'suggestions': list  # 改进建议
        }
    """
    try:
        sig = inspect.signature(method)
        type_hints = get_type_hints(method)
    except Exception:
        return {
            "has_annotations": False,
            "complete": False,
            "params_with_types": [],
            "params_without_types": [],
            "has_return_type": False,
            "error": True,
            "suggestions": ["无法获取类型信息，请检查方法定义"],
        }

    params_with_types = []
    params_without_types = []
    suggestions = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        if param_name in type_hints:
            params_with_types.append(param_name)
        else:
            params_without_types.append(param_name)
            suggestions.append(f"为参数 '{param_name}' 添加类型注解")

    has_return_type = "return" in type_hints
    if not has_return_type:
        suggestions.append("添加返回类型注解")

    has_any_annotations = len(params_with_types) > 0 or has_return_type
    is_complete = len(params_without_types) == 0 and has_return_type

    return {
        "has_annotations": has_any_annotations,
        "complete": is_complete,
        "params_with_types": params_with_types,
        "params_without_types": params_without_types,
        "has_return_type": has_return_type,
        "error": False,
        "suggestions": suggestions,
    }


def analyze_tool(tool_name, tool_class):
    """分析单个工具的类型注解情况"""
    methods_info = []

    for method_name in dir(tool_class):
        # 跳过私有方法和特殊方法
        if method_name.startswith("_"):
            continue

        # 跳过基类方法
        if method_name in ["run", "run_async", "run_batch"]:
            continue

        method = getattr(tool_class, method_name)

        # 跳过非方法属性
        if not callable(method):
            continue

        # 跳过类（如 Config, Schema 等）
        if isinstance(method, type):
            continue

        # 检查类型注解
        annotation_info = check_method_type_annotations(method, method_name)
        annotation_info["method_name"] = method_name

        methods_info.append(annotation_info)

    return methods_info


def print_tool_report(tool_name: str, methods_info: List[Dict], verbose: bool = False):
    """打印单个工具的报告"""

    total = len(methods_info)
    complete = sum(1 for m in methods_info if m["complete"])
    sum(1 for m in methods_info if m["has_annotations"] and not m["complete"])
    sum(1 for m in methods_info if not m["has_annotations"])

    # 计算覆盖率
    coverage = (complete / total * 100) if total > 0 else 0

    # 状态图标
    if coverage == 100:
        status = "✅"
    elif coverage >= 80:
        status = "⚠️"
    else:
        status = "❌"

    print(f"\n{status} {tool_name}: {complete}/{total} 方法有完整类型注解 ({coverage:.1f}%)")

    if verbose or coverage < 100:
        # 显示不完整的方法
        incomplete = [m for m in methods_info if not m["complete"]]
        if incomplete:
            print("\n  需要改进的方法:")
            for method_info in incomplete:
                method_name = method_info["method_name"]
                suggestions = method_info.get("suggestions", [])

                if method_info["error"]:
                    print(f"    ✗ {method_name}: 无法获取类型信息")
                elif not method_info["has_annotations"]:
                    print(f"    ✗ {method_name}: 无类型注解")
                else:
                    print(f"    ⚠ {method_name}: 部分类型注解")

                # 显示改进建议
                if suggestions and verbose:
                    for suggestion in suggestions:
                        print(f"        → {suggestion}")


def check_annotations(tool_names: Optional[List[str]] = None, verbose: bool = False):
    """
    检查工具的类型注解

    Args:
        tool_names: 要检查的工具名称列表，None 表示检查所有工具
        verbose: 是否显示详细信息
    """
    print("=" * 100)
    print("工具类型注解检查器")
    print("=" * 100)

    discover_tools()

    # 确定要检查的工具
    if tool_names:
        tools_to_check = {}
        for name in tool_names:
            if name in TOOL_CLASSES:
                tools_to_check[name] = TOOL_CLASSES[name]
            else:
                print(f"\n❌ 工具 '{name}' 不存在")

        if not tools_to_check:
            print("\n没有找到要检查的工具")
            return
    else:
        tools_to_check = TOOL_CLASSES

    # 检查每个工具
    all_stats = []
    for tool_name in sorted(tools_to_check.keys()):
        tool_class = tools_to_check[tool_name]
        methods_info = analyze_tool(tool_name, tool_class)

        if methods_info:
            print_tool_report(tool_name, methods_info, verbose)

            total = len(methods_info)
            complete = sum(1 for m in methods_info if m["complete"])
            all_stats.append((tool_name, total, complete))

    # 总体统计
    if len(all_stats) > 1:
        total_methods = sum(s[1] for s in all_stats)
        total_complete = sum(s[2] for s in all_stats)
        overall_coverage = (total_complete / total_methods * 100) if total_methods > 0 else 0

        print("\n" + "=" * 100)
        print(f"总体统计: {total_complete}/{total_methods} 方法有完整类型注解 ({overall_coverage:.1f}%)")
        print("=" * 100)

    print("\n💡 提示:")
    print("  - 完整类型注解包括：所有参数的类型 + 返回类型")
    print("  - 使用 --verbose 查看详细的改进建议")
    print("  - 完整的类型注解是自动 Schema 生成的基础")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="检查工具方法的类型注解完整性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查所有工具
  aiecs tools check-annotations

  # 检查特定工具
  aiecs tools check-annotations pandas

  # 检查多个工具并显示详细信息
  aiecs tools check-annotations pandas chart --verbose
        """,
    )

    parser.add_argument("tools", nargs="*", help="要检查的工具名称（不指定则检查所有工具）")

    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细的改进建议")

    args = parser.parse_args()

    tool_names = args.tools if args.tools else None
    check_annotations(tool_names, args.verbose)


if __name__ == "__main__":
    main()
