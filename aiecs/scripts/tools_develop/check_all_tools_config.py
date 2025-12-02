#!/usr/bin/env python3
"""
检查所有注册工具的配置设置是否正确

验证所有工具是否正确使用 self._config_obj 而不是重新创建 Config 对象
"""

import sys
import os
import re
import inspect
from typing import List, Tuple, Dict

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


def check_tool_init_pattern(file_path: str) -> Tuple[str, str, List[str]]:
    """
    检查工具的 __init__ 方法是否正确使用配置
    
    Returns:
        (tool_name, status, issues)
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
        
        if not has_config_class:
            return tool_name, 'NO_CONFIG', []
        
        # 检查是否有 __init__ 方法
        init_match = re.search(r'def __init__\(self[^)]*\):(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
        
        if not init_match:
            return tool_name, 'NO_INIT', []
        
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
                return tool_name, 'CORRECT', []
            else:
                return tool_name, 'MIXED', issues
        else:
            if not issues:
                issues.append("未找到正确的配置模式 (self._config_obj)")
            return tool_name, 'INCORRECT', issues
        
    except Exception as e:
        return os.path.basename(file_path), 'ERROR', [str(e)]


def main():
    """检查所有工具"""
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
    
    for file_path in tool_files:
        rel_path = os.path.relpath(file_path, os.path.join(os.path.dirname(__file__), '..'))
        tool_name, status, issues = check_tool_init_pattern(file_path)
        
        results[status].append((tool_name, rel_path, issues))
    
    # 打印结果
    print("\n" + "="*80)
    print("检查结果")
    print("="*80)
    
    # 正确的工具
    if results['CORRECT']:
        print(f"\n✅ 正确配置 ({len(results['CORRECT'])} 个):")
        for tool_name, rel_path, _ in results['CORRECT']:
            print(f"  ✓ {tool_name}")
            print(f"    {rel_path}")
    
    # 错误的工具
    if results['INCORRECT']:
        print(f"\n❌ 错误配置 ({len(results['INCORRECT'])} 个):")
        for tool_name, rel_path, issues in results['INCORRECT']:
            print(f"  ✗ {tool_name}")
            print(f"    {rel_path}")
            for issue in issues:
                print(f"    问题: {issue}")
    
    # 混合模式
    if results['MIXED']:
        print(f"\n⚠️  混合模式 ({len(results['MIXED'])} 个):")
        for tool_name, rel_path, issues in results['MIXED']:
            print(f"  ⚠ {tool_name}")
            print(f"    {rel_path}")
            for issue in issues:
                print(f"    问题: {issue}")
    
    # 无配置类
    if results['NO_CONFIG']:
        print(f"\n📝 无 Config 类 ({len(results['NO_CONFIG'])} 个):")
        for tool_name, rel_path, _ in results['NO_CONFIG']:
            print(f"  - {tool_name}")
    
    # 无 __init__ 方法
    if results['NO_INIT']:
        print(f"\n📝 无 __init__ 方法 ({len(results['NO_INIT'])} 个):")
        for tool_name, rel_path, _ in results['NO_INIT']:
            print(f"  - {tool_name}")
    
    # 错误
    if results['ERROR']:
        print(f"\n⚠️  检查错误 ({len(results['ERROR'])} 个):")
        for tool_name, rel_path, issues in results['ERROR']:
            print(f"  ! {tool_name}")
            print(f"    {rel_path}")
            for issue in issues:
                print(f"    错误: {issue}")
    
    # 总结
    print("\n" + "="*80)
    print("总结")
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

