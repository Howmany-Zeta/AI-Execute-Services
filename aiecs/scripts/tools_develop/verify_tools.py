#!/usr/bin/env python3
"""
快速验证脚本：展示 aiecs.tools 注册的所有工具和功能

使用方法:
    poetry run python -m aiecs.scripts.tools_develop.verify_tools

功能:
    1. 列出所有注册的工具（按类别分组）
    2. 交互式选择工具查看详细功能
    3. 实际加载指定工具，展示真实的原子功能
"""

import sys
import os
import inspect
from typing import List, Dict
from collections import defaultdict

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, project_root)


def get_tool_methods(tool_instance) -> List[str]:
    """获取工具实例的所有公共方法（原子功能）"""
    methods = []
    for name, method in inspect.getmembers(tool_instance, predicate=inspect.ismethod):
        # 只获取公共方法，排除私有方法和特殊方法
        if not name.startswith("_"):
            methods.append(name)
    return sorted(methods)


def display_tools_by_category(tools: List[Dict]):
    """按类别分组显示工具"""
    # 按类别分组
    categories = defaultdict(list)
    for tool in tools:
        category = tool.get("category", "unknown")
        categories[category].append(tool)

    # 显示每个类别
    category_names = {
        "task": "任务工具",
        "docs": "文档工具",
        "statistics": "数据统计工具",
        "unknown": "其他工具",
    }

    tool_index = 1
    tool_map = {}  # 用于存储序号到工具名的映射

    for category in ["task", "docs", "statistics", "unknown"]:
        if category not in categories:
            continue

        category_tools = categories[category]
        category_display = category_names.get(category, category.upper())

        print(f"\n{'=' * 80}")
        print(f"📁 {category_display} ({len(category_tools)} 个)")
        print(f"{'=' * 80}")

        for tool in category_tools:
            tool_name = tool["name"]
            tool_map[tool_index] = tool_name

            print(f"\n[{tool_index}] {tool_name}")
            print(f"    描述: {tool.get('description', '无描述')}")
            print(f"    状态: {tool.get('status', '未知')}")

            tool_index += 1

    return tool_map


def auto_discover_tool_modules():
    """自动发现工具模块映射，无需手动维护"""
    import os
    import re

    tool_module_map = {}

    # 扫描 aiecs/tools 目录
    tools_dir = os.path.join(project_root, "aiecs", "tools")

    # 定义工具目录
    tool_dirs = {
        "task_tools": "aiecs.tools.task_tools",
        "docs": "aiecs.tools.docs",
        "statistics": "aiecs.tools.statistics",
        "api_sources": "aiecs.tools.api_sources",  # 旧的 API sources (如果存在)
        "apisource": "aiecs.tools.apisource",  # 新的 APISource Tool
        "search_tool": "aiecs.tools.search_tool",
    }

    for dir_name, package_name in tool_dirs.items():
        dir_path = os.path.join(tools_dir, dir_name)
        if not os.path.exists(dir_path):
            continue

        # Check if this is a package (has __init__.py) or a directory of
        # modules
        init_file = os.path.join(dir_path, "__init__.py")
        files_to_scan = []

        if os.path.isfile(init_file):
            # For packages, scan __init__.py and use package name directly
            files_to_scan.append(("__init__.py", init_file, package_name))

        # 扫描目录中的所有其他 Python 文件
        for filename in os.listdir(dir_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                file_path = os.path.join(dir_path, filename)
                module_name = filename[:-3]  # 去掉 .py 扩展名
                module_path = f"{package_name}.{module_name}"
                files_to_scan.append((filename, file_path, module_path))

        # Process all files
        for filename, file_path, module_path in files_to_scan:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                    # 查找 @register_tool 装饰器 (两种模式)
                    # Pattern 1: @register_tool("name") decorator syntax
                    decorator_pattern = r'@register_tool\([\'"]([^\'"]+)[\'"]\)'
                    decorator_matches = re.findall(decorator_pattern, content)

                    # Pattern 2: register_tool("name")(ClassName) function call
                    # syntax
                    function_pattern = r'register_tool\([\'"]([^\'"]+)[\'"]\)\([A-Za-z_][A-Za-z0-9_]*\)'
                    function_matches = re.findall(function_pattern, content)

                    # Combine all matches
                    all_matches = list(set(decorator_matches + function_matches))

                    for tool_name in all_matches:
                        tool_module_map[tool_name] = {
                            "module_file": (filename[:-3] if filename != "__init__.py" else "__init__"),
                            "package": package_name,
                            "module_path": module_path,
                            "category": dir_name,
                        }
            except Exception:
                pass

    return tool_module_map


def load_and_inspect_tool(tool_name: str):
    """加载并检查指定工具的详细功能"""
    from aiecs.tools import get_tool
    import importlib

    print(f"\n{'=' * 80}")
    print(f"🔍 加载工具: {tool_name}")
    print(f"{'=' * 80}")

    try:
        # 自动发现工具模块
        print("\n⏳ 正在加载...")

        tool_module_map = auto_discover_tool_modules()

        # 如果找到了工具的模块信息，预加载模块
        if tool_name in tool_module_map:
            info = tool_module_map[tool_name]
            module_path = info.get("module_path") or f"{info['package']}.{info['module_file']}"

            try:
                importlib.import_module(module_path)
                print(f"    已触发 {module_path} 模块加载")
            except Exception as e:
                print(f"    警告: 无法预加载模块 ({e})")
        else:
            print("    未找到工具模块映射，尝试直接加载...")

        # 获取工具实例
        tool = get_tool(tool_name)

        # 检查是否为占位符
        is_placeholder = getattr(tool, "is_placeholder", False)

        if is_placeholder:
            print("\n⚠️  工具仍处于占位符状态")
            print(f"    描述: {tool.description}")
            print("    提示: 此工具需要在调用具体方法时才会完全实例化")
            return

        # 显示工具基本信息
        print("\n✅ 工具已成功加载")
        print(f"    类名: {tool.__class__.__name__}")
        print(f"    模块: {tool.__class__.__module__}")

        if hasattr(tool, "description"):
            print(f"    描述: {tool.description}")

        if hasattr(tool, "category"):
            print(f"    类别: {tool.category}")

        # 获取所有方法（原子功能）
        methods = get_tool_methods(tool)

        if not methods:
            print("\n❌ 未发现公共方法")
            return

        print(f"\n📋 原子功能列表 (共 {len(methods)} 个方法):")
        print("-" * 80)

        for i, method_name in enumerate(methods, 1):
            try:
                method = getattr(tool, method_name)

                # 获取方法签名
                sig = inspect.signature(method)
                params = []
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue

                    # 构建参数字符串
                    param_str = param_name
                    if param.annotation != inspect.Parameter.empty:
                        param_str += f": {param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)}"
                    if param.default != inspect.Parameter.empty:
                        param_str += f" = {param.default!r}"
                    params.append(param_str)

                # 获取返回类型
                return_annotation = ""
                if sig.return_annotation != inspect.Signature.empty:
                    return_type = sig.return_annotation
                    return_annotation = f" -> {return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)}"

                # 显示方法签名
                print(f"\n  [{i}] {method_name}({', '.join(params)}){return_annotation}")

                # 获取文档字符串
                if method.__doc__:
                    doc_lines = method.__doc__.strip().split("\n")
                    first_line = doc_lines[0].strip()
                    if first_line:
                        print(f"      {first_line}")

            except Exception as e:
                print(f"\n  [{i}] {method_name}")
                print(f"      (无法获取详细信息: {e})")

        print(f"\n{'-' * 80}")

    except Exception as e:
        print(f"\n❌ 加载工具失败: {e}")
        import traceback

        traceback.print_exc()


def interactive_mode(tool_map: Dict[int, str]):
    """交互式模式"""
    print(f"\n{'=' * 80}")
    print("🎮 交互模式")
    print(f"{'=' * 80}")
    print("\n提示:")
    print("  - 输入工具序号 (1-{}) 查看详细功能".format(len(tool_map)))
    print("  - 输入工具名称查看详细功能")
    print("  - 输入 'list' 重新显示工具列表")
    print("  - 输入 'q' 或 'quit' 退出")

    while True:
        try:
            user_input = input("\n👉 请选择工具 > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["q", "quit", "exit"]:
                print("\n👋 再见!")
                break

            if user_input.lower() == "list":
                from aiecs.tools import list_tools

                tools = list_tools()
                display_tools_by_category(tools)
                continue

            # 尝试作为序号解析
            tool_name = None
            try:
                index = int(user_input)
                if index in tool_map:
                    tool_name = tool_map[index]
                else:
                    print(f"❌ 无效的序号: {index}")
                    continue
            except ValueError:
                # 作为工具名称
                tool_name = user_input

            if tool_name:
                load_and_inspect_tool(tool_name)

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except EOFError:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


def main():
    """主函数：验证和展示所有注册的工具"""
    print("=" * 80)
    print("AIECS Tools 注册工具验证")
    print("=" * 80)

    try:
        from aiecs.tools import list_tools

        # 获取所有注册的工具
        tools = list_tools()

        print(f"\n发现 {len(tools)} 个注册的工具")

        # 按类别显示工具
        tool_map = display_tools_by_category(tools)

        print(f"\n{'=' * 80}")
        print(f"✅ 工具列表显示完成! 共 {len(tools)} 个工具")
        print(f"{'=' * 80}")

        # 进入交互模式
        interactive_mode(tool_map)

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保在正确的项目目录中运行此脚本")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
