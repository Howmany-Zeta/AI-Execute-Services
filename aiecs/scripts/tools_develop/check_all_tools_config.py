#!/usr/bin/env python3
"""
检查所有注册工具的配置设置是否正确

验证所有工具是否正确使用 self._config_obj 而不是重新创建 Config 对象
并提取打印所有工具的配置信息，方便开发者配置
"""

import sys
import os
import re
import inspect
import json
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def find_all_tool_files() -> List[str]:
    """查找所有工具文件"""
    tool_files = []
    # 从脚本位置向上找到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../../..'))
    tools_dir = os.path.join(project_root, 'aiecs', 'tools')

    for root, dirs, files in os.walk(tools_dir):
        for file in files:
            # 包含 _tool.py, tool.py, 以及 orchestrator.py 文件
            if (file.endswith('_tool.py') or file == 'tool.py' or
                file.endswith('orchestrator.py')):
                if file != 'base_tool.py':
                    tool_files.append(os.path.join(root, file))

    return sorted(tool_files)


def extract_config_fields(file_path: str, content: str) -> Dict[str, Any]:
    """
    从工具文件中提取 Config 类的字段信息
    
    Returns:
        包含配置字段信息的字典
    """
    config_fields = {}
    
    # 提取 Config 类定义
    config_class_match = re.search(
        r'class Config\(BaseSettings\):(.*?)(?=\n    class |\n    def |\nclass |\Z)',
        content,
        re.DOTALL
    )
    
    if not config_class_match:
        return config_fields
    
    config_body = config_class_match.group(1)
    
    # 提取字段定义 - 匹配各种模式
    # 模式1: field_name: Type = default_value
    # 模式2: field_name: Type = Field(default=..., description="...")
    # 模式3: field_name: Type
    field_pattern = r'^\s{8}(\w+)\s*:\s*([^=\n]+)(?:\s*=\s*(.+))?$'
    
    lines = config_body.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 跳过注释和空行
        if line.strip().startswith('#') or not line.strip():
            i += 1
            continue
        
        # 跳过 model_config 和其他特殊配置
        if 'model_config' in line or 'Config:' in line:
            i += 1
            continue
        
        match = re.match(field_pattern, line)
        if match:
            field_name = match.group(1)
            field_type = match.group(2).strip()
            field_default = match.group(3).strip() if match.group(3) else None
            
            # 提取描述信息
            description = ""
            if field_default and 'Field(' in field_default:
                # 尝试提取 Field 中的 description
                desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', field_default)
                if desc_match:
                    description = desc_match.group(1)
                
                # 提取实际默认值
                default_match = re.search(r'default\s*=\s*([^,\)]+)', field_default)
                if default_match:
                    field_default = default_match.group(1).strip()
                elif 'default_factory' in field_default:
                    field_default = "factory function"
                else:
                    # Field() 没有指定 default，表示必需字段
                    field_default = None
            
            # 检查上一行是否有注释
            if i > 0:
                prev_line = lines[i-1].strip()
                if prev_line.startswith('#'):
                    if not description:
                        description = prev_line[1:].strip()
            
            # 判断是否必需（没有默认值且类型不是 Optional）
            is_required = (field_default is None and 
                          'Optional' not in field_type and 
                          '|' not in field_type or 'None' not in field_type)
            
            config_fields[field_name] = {
                'type': field_type,
                'default': field_default,
                'required': is_required,
                'description': description
            }
        
        i += 1
    
    return config_fields


def check_tool_init_pattern(file_path: str) -> Tuple[str, str, List[str], Dict[str, Any]]:
    """
    检查工具的 __init__ 方法是否正确使用配置，并提取配置信息
    
    Returns:
        (tool_name, status, issues, config_fields)
        status: 'CORRECT', 'INCORRECT', 'NO_CONFIG', 'NO_INIT', 'ERROR'
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取工具名称
        tool_name_match = re.search(r'class (\w+Tool)\(BaseTool\)', content)
        if not tool_name_match:
            tool_name_match = re.search(r'class (\w+)\(BaseTool\)', content)
        
        tool_name = tool_name_match.group(1) if tool_name_match else os.path.basename(file_path)
        
        # 检查是否有 Config 类
        has_config_class = bool(re.search(r'class Config\(BaseSettings\)', content))
        
        # 提取配置字段
        config_fields = extract_config_fields(file_path, content) if has_config_class else {}
        
        if not has_config_class:
            return tool_name, 'NO_CONFIG', [], config_fields
        
        # 检查是否有 __init__ 方法
        init_match = re.search(r'def __init__\(self[^)]*\):(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
        
        if not init_match:
            return tool_name, 'NO_INIT', [], config_fields
        
        init_body = init_match.group(1)
        
        issues = []
        
        # 检查是否调用了 super().__init__
        if 'super().__init__' not in init_body:
            issues.append("未调用 super().__init__()")
        
        # 检查错误模式：重新创建 Config 对象
        incorrect_patterns = [
            r'self\.config\s*=\s*self\.Config\(\*\*',  # self.config = self.Config(**...)
            r'self\.config\s*=\s*self\.Config\(\s*\)',  # self.config = self.Config()
            r'self\.config\s*=\s*Config\(\*\*',         # self.config = Config(**...)
        ]
        
        for pattern in incorrect_patterns:
            if re.search(pattern, init_body):
                # 检查是否在正确的模式之前（即不是 self._config_obj 的回退）
                if 'self._config_obj if self._config_obj else' not in init_body:
                    issues.append(f"发现错误模式: 直接创建 Config 对象")
                    break
        
        # 检查正确模式：使用 self._config_obj
        correct_pattern = r'self\.config\s*=\s*self\._config_obj\s+if\s+self\._config_obj\s+else\s+self\.Config\(\)'
        
        if re.search(correct_pattern, init_body):
            if not issues:
                return tool_name, 'CORRECT', [], config_fields
            else:
                return tool_name, 'MIXED', issues, config_fields
        else:
            if not issues:
                issues.append("未找到正确的配置模式 (self._config_obj)")
            return tool_name, 'INCORRECT', issues, config_fields
        
    except Exception as e:
        return os.path.basename(file_path), 'ERROR', [str(e)], {}


def print_config_details(tool_name: str, config_fields: Dict[str, Any], indent: str = "    "):
    """打印配置字段详情"""
    if not config_fields:
        print(f"{indent}(无配置字段)")
        return
    
    print(f"{indent}配置字段 ({len(config_fields)} 个):")
    for field_name, field_info in sorted(config_fields.items()):
        required_marker = "🔴 必需" if field_info['required'] else "🟢 可选"
        print(f"{indent}  • {field_name}: {field_info['type']}")
        print(f"{indent}    {required_marker}")
        
        if field_info['default'] is not None:
            default_str = str(field_info['default'])
            if len(default_str) > 50:
                default_str = default_str[:47] + "..."
            print(f"{indent}    默认值: {default_str}")
        
        if field_info['description']:
            desc = field_info['description']
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"{indent}    说明: {desc}")


def generate_config_template(all_configs: Dict[str, Dict[str, Any]], output_file: str = None):
    """生成配置模板文件"""
    
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'tools_config_template.json')
    
    template = {}
    
    for tool_name, config_fields in sorted(all_configs.items()):
        if not config_fields:
            continue
        
        tool_config = {}
        for field_name, field_info in sorted(config_fields.items()):
            # 为每个字段生成示例值
            if field_info['default'] is not None:
                value = field_info['default']
            elif field_info['required']:
                # 必需字段，根据类型提供示例
                field_type = field_info['type'].lower()
                if 'str' in field_type:
                    value = f"your_{field_name}_here"
                elif 'int' in field_type:
                    value = 0
                elif 'float' in field_type:
                    value = 0.0
                elif 'bool' in field_type:
                    value = False
                elif 'list' in field_type:
                    value = []
                elif 'dict' in field_type:
                    value = {}
                else:
                    value = None
            else:
                continue  # 可选字段且没有默认值，跳过
            
            tool_config[field_name] = {
                "value": value,
                "type": field_info['type'],
                "required": field_info['required'],
                "description": field_info['description']
            }
        
        if tool_config:
            template[tool_name] = tool_config
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    return output_file


def generate_markdown_doc(all_configs: Dict[str, Dict[str, Any]], output_file: str = None):
    """生成 Markdown 格式的配置文档"""
    
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'TOOLS_CONFIG_GUIDE.md')
    
    lines = []
    lines.append("# AIECS 工具配置指南")
    lines.append("")
    lines.append("本文档列出了所有工具的配置参数，方便开发者快速配置和使用。")
    lines.append("")
    lines.append(f"生成时间: {Path(__file__).name}")
    lines.append("")
    
    # 目录
    lines.append("## 目录")
    lines.append("")
    for i, tool_name in enumerate(sorted(all_configs.keys()), 1):
        lines.append(f"{i}. [{tool_name}](#{tool_name.lower()})")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 各工具详情
    for tool_name, config_fields in sorted(all_configs.items()):
        if not config_fields:
            continue
        
        lines.append(f"## {tool_name}")
        lines.append("")
        
        # 统计信息
        required_count = sum(1 for f in config_fields.values() if f['required'])
        optional_count = len(config_fields) - required_count
        lines.append(f"**配置字段数**: {len(config_fields)} (必需: {required_count}, 可选: {optional_count})")
        lines.append("")
        
        # 配置表格
        lines.append("| 字段名 | 类型 | 必需 | 默认值 | 说明 |")
        lines.append("|--------|------|------|--------|------|")
        
        for field_name, field_info in sorted(config_fields.items()):
            field_type = field_info['type'].replace('|', '\\|')
            required_marker = "✅" if field_info['required'] else "❌"
            default_val = field_info['default'] if field_info['default'] is not None else "-"
            if isinstance(default_val, str) and len(str(default_val)) > 30:
                default_val = str(default_val)[:27] + "..."
            description = field_info['description'] if field_info['description'] else "-"
            
            lines.append(f"| `{field_name}` | {field_type} | {required_marker} | `{default_val}` | {description} |")
        
        lines.append("")
        
        # 配置示例
        lines.append("### 配置示例")
        lines.append("")
        lines.append("```python")
        lines.append(f"{tool_name.lower()}_config = {{")
        
        for field_name, field_info in sorted(config_fields.items()):
            if field_info['default'] is not None:
                value = field_info['default']
            else:
                field_type = field_info['type'].lower()
                if 'str' in field_type:
                    value = f'"your_{field_name}"'
                elif 'int' in field_type:
                    value = 0
                elif 'float' in field_type:
                    value = 0.0
                elif 'bool' in field_type:
                    value = 'False'
                elif 'list' in field_type:
                    value = '[]'
                elif 'dict' in field_type:
                    value = '{}'
                else:
                    value = 'None'
            
            comment = f"  # {field_info['description']}" if field_info['description'] else ""
            lines.append(f"    '{field_name}': {value},{comment}")
        
        lines.append("}")
        lines.append("```")
        lines.append("")
        
        # 环境变量映射
        lines.append("### 环境变量映射")
        lines.append("")
        lines.append("```bash")
        for field_name in sorted(config_fields.keys()):
            env_var = f"{tool_name.upper().replace('TOOL', '_TOOL').replace('ORCHESTRATOR', '_ORCHESTRATOR')}_{field_name.upper()}"
            lines.append(f"export {env_var}=<value>")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_file


def main():
    """检查所有工具并展示配置信息"""
    import argparse
    
    parser = argparse.ArgumentParser(description='检查所有工具的配置并展示配置信息')
    parser.add_argument('--show-config', action='store_true', 
                       help='显示每个工具的详细配置信息')
    parser.add_argument('--generate-template', action='store_true',
                       help='生成 JSON 格式配置模板文件')
    parser.add_argument('--generate-markdown', action='store_true',
                       help='生成 Markdown 格式配置文档')
    parser.add_argument('--output', type=str,
                       help='配置模板输出文件路径')
    parser.add_argument('--markdown-output', type=str,
                       help='Markdown 文档输出文件路径')
    
    args = parser.parse_args()
    
    print("="*80)
    print("检查所有注册工具的配置设置")
    print("="*80)
    
    tool_files = find_all_tool_files()
    print(f"\n找到 {len(tool_files)} 个工具文件\n")
    
    results = {
        'CORRECT': [],
        'INCORRECT': [],
        'NO_CONFIG': [],
        'NO_INIT': [],
        'MIXED': [],
        'ERROR': []
    }
    
    all_configs = {}
    
    for file_path in tool_files:
        rel_path = os.path.relpath(file_path, os.path.join(os.path.dirname(__file__), '..'))
        tool_name, status, issues, config_fields = check_tool_init_pattern(file_path)
        
        results[status].append((tool_name, rel_path, issues, config_fields))
        
        if config_fields:
            all_configs[tool_name] = config_fields
    
    # 打印结果
    print("\n" + "="*80)
    print("配置检查结果")
    print("="*80)
    
    # 正确的工具
    if results['CORRECT']:
        print(f"\n✅ 正确配置 ({len(results['CORRECT'])} 个):")
        for tool_name, rel_path, _, config_fields in results['CORRECT']:
            print(f"  ✓ {tool_name}")
            print(f"    文件: {rel_path}")
            if args.show_config and config_fields:
                print_config_details(tool_name, config_fields)
    
    # 错误的工具
    if results['INCORRECT']:
        print(f"\n❌ 错误配置 ({len(results['INCORRECT'])} 个):")
        for tool_name, rel_path, issues, config_fields in results['INCORRECT']:
            print(f"  ✗ {tool_name}")
            print(f"    文件: {rel_path}")
            for issue in issues:
                print(f"    问题: {issue}")
            if args.show_config and config_fields:
                print_config_details(tool_name, config_fields)
    
    # 混合模式
    if results['MIXED']:
        print(f"\n⚠️  混合模式 ({len(results['MIXED'])} 个):")
        for tool_name, rel_path, issues, config_fields in results['MIXED']:
            print(f"  ⚠ {tool_name}")
            print(f"    文件: {rel_path}")
            for issue in issues:
                print(f"    问题: {issue}")
            if args.show_config and config_fields:
                print_config_details(tool_name, config_fields)
    
    # 无配置类
    if results['NO_CONFIG']:
        print(f"\n📝 无 Config 类 ({len(results['NO_CONFIG'])} 个):")
        for tool_name, rel_path, _, _ in results['NO_CONFIG']:
            print(f"  - {tool_name}")
    
    # 无 __init__ 方法
    if results['NO_INIT']:
        print(f"\n📝 无 __init__ 方法 ({len(results['NO_INIT'])} 个):")
        for tool_name, rel_path, _, config_fields in results['NO_INIT']:
            print(f"  - {tool_name}")
            if args.show_config and config_fields:
                print_config_details(tool_name, config_fields)
    
    # 错误
    if results['ERROR']:
        print(f"\n⚠️  检查错误 ({len(results['ERROR'])} 个):")
        for tool_name, rel_path, issues, _ in results['ERROR']:
            print(f"  ! {tool_name}")
            print(f"    文件: {rel_path}")
            for issue in issues:
                print(f"    错误: {issue}")
    
    # 配置信息总结
    if all_configs and not args.show_config:
        print("\n" + "="*80)
        print("配置信息概览")
        print("="*80)
        print(f"\n共有 {len(all_configs)} 个工具包含配置类")
        
        total_fields = sum(len(fields) for fields in all_configs.values())
        print(f"总配置字段数: {total_fields}")
        
        print("\n提示: 使用 --show-config 参数查看所有工具的详细配置信息")
        print("提示: 使用 --generate-template 生成配置模板文件")
    
    # 生成配置模板
    if args.generate_template:
        print("\n" + "="*80)
        print("生成 JSON 配置模板")
        print("="*80)
        template_file = generate_config_template(all_configs, args.output)
        print(f"\n✅ JSON 配置模板已生成: {template_file}")
        print(f"   包含 {len(all_configs)} 个工具的配置信息")
    
    # 生成 Markdown 文档
    if args.generate_markdown:
        print("\n" + "="*80)
        print("生成 Markdown 配置文档")
        print("="*80)
        markdown_file = generate_markdown_doc(all_configs, args.markdown_output)
        print(f"\n✅ Markdown 配置文档已生成: {markdown_file}")
        print(f"   包含 {len(all_configs)} 个工具的详细配置说明")
    
    # 总结
    print("\n" + "="*80)
    print("检查总结")
    print("="*80)
    total = len(tool_files)
    correct = len(results['CORRECT'])
    incorrect = len(results['INCORRECT']) + len(results['MIXED'])
    no_config = len(results['NO_CONFIG']) + len(results['NO_INIT'])
    
    print(f"总工具数: {total}")
    print(f"✅ 正确配置: {correct}")
    print(f"❌ 需要修复: {incorrect}")
    print(f"📝 无需配置: {no_config}")
    
    if incorrect > 0:
        print(f"\n⚠️  发现 {incorrect} 个工具需要修复配置！")
        return 1
    else:
        print(f"\n✅ 所有工具配置正确！")
        return 0


if __name__ == "__main__":
    sys.exit(main())

