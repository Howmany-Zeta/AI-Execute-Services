#!/usr/bin/env python3
"""
KAG项目导入路径更新脚本
支持灵活的导入路径重命名，为KAG项目更新做准备

用法:
    python update_kag_imports.py --help
    python update_kag_imports.py --source-path kag --target-path app.services.domain.kag_core --directory app/services/domain/kag_core
    python update_kag_imports.py --config config.json
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

class KAGImportUpdater:
    """KAG导入路径更新器"""

    def __init__(self, config: Dict = None):
        """
        初始化更新器

        Args:
            config (Dict): 配置字典，包含替换规则和选项
        """
        self.config = config or {}
        self.stats = {
            'total_files': 0,
            'modified_files': 0,
            'total_replacements': 0,
            'replacements_by_rule': {}
        }

    def add_replacement_rule(self, pattern: str, replacement: str, description: str = ""):
        """
        添加替换规则

        Args:
            pattern (str): 正则表达式模式
            replacement (str): 替换字符串
            description (str): 规则描述
        """
        if 'rules' not in self.config:
            self.config['rules'] = []

        self.config['rules'].append({
            'pattern': pattern,
            'replacement': replacement,
            'description': description
        })

    def load_config_from_file(self, config_file: str):
        """
        从JSON文件加载配置

        Args:
            config_file (str): 配置文件路径
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"错误: 无法加载配置文件 {config_file}: {e}")
            sys.exit(1)

    def save_config_to_file(self, config_file: str):
        """
        保存配置到JSON文件

        Args:
            config_file (str): 配置文件路径
        """
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"配置已保存到: {config_file}")
        except Exception as e:
            print(f"错误: 无法保存配置文件 {config_file}: {e}")

    def update_imports(self, directory_path: str, dry_run: bool = False):
        """
        更新指定目录下的导入路径

        Args:
            directory_path (str): 要处理的目录路径
            dry_run (bool): 是否为试运行模式（不实际修改文件）
        """
        directory = Path(directory_path)
        if not directory.exists():
            print(f"错误: 目录 {directory_path} 不存在")
            return False

        if not self.config.get('rules'):
            print("错误: 没有配置替换规则")
            return False

        # 重置统计信息
        self.stats = {
            'total_files': 0,
            'modified_files': 0,
            'total_replacements': 0,
            'replacements_by_rule': {rule['description'] or rule['pattern']: 0 for rule in self.config['rules']}
        }

        print(f"{'[试运行] ' if dry_run else ''}开始更新 {directory_path} 目录下的导入路径...")
        print("替换规则:")
        for i, rule in enumerate(self.config['rules'], 1):
            print(f"  {i}. {rule.get('description', rule['pattern'])}")
            print(f"     模式: {rule['pattern']}")
            print(f"     替换: {rule['replacement']}")
        print("=" * 80)

        # 遍历所有Python文件
        for py_file in directory.rglob("*.py"):
            self.stats['total_files'] += 1
            file_modified = False
            file_replacements = 0

            try:
                # 读取文件内容
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                new_content = content

                # 应用所有替换规则
                for rule in self.config['rules']:
                    pattern = rule['pattern']
                    replacement = rule['replacement']
                    rule_desc = rule.get('description', pattern)

                    modified_content, count = re.subn(pattern, replacement, new_content)

                    if count > 0:
                        new_content = modified_content
                        file_replacements += count
                        self.stats['replacements_by_rule'][rule_desc] += count
                        file_modified = True

                # 如果文件被修改且不是试运行模式，则写回文件
                if file_modified:
                    if not dry_run:
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)

                    self.stats['modified_files'] += 1
                    self.stats['total_replacements'] += file_replacements

                    status = "✓" if not dry_run else "○"
                    print(f"{status} {py_file.relative_to(directory)}: {file_replacements} 处替换")

            except Exception as e:
                print(f"✗ 处理文件 {py_file} 时出错: {e}")
                continue

        # 输出统计信息
        print(f"\n=== {'试运行' if dry_run else '更新'}完成 ===")
        print(f"总文件数: {self.stats['total_files']}")
        print(f"修改文件数: {self.stats['modified_files']}")
        print(f"总替换次数: {self.stats['total_replacements']}")

        if self.stats['replacements_by_rule']:
            print("\n按规则统计:")
            for rule_desc, count in self.stats['replacements_by_rule'].items():
                if count > 0:
                    print(f"  {rule_desc}: {count} 次")

        return True

def create_default_config():
    """创建默认配置"""
    return {
        "rules": [
            {
                "pattern": r"\bfrom kag\.",
                "replacement": "from app.services.domain.kag_core.",
                "description": "KAG核心模块导入路径重命名"
            }
        ],
        "exclude_patterns": [
            r"knext\.",
            r"__pycache__",
            r"\.pyc$"
        ],
        "description": "KAG项目导入路径更新配置"
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="KAG项目导入路径更新脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认规则更新导入路径
  python update_kag_imports.py --directory app/services/domain/kag_core

  # 自定义源路径和目标路径
  python update_kag_imports.py --source-path kag --target-path app.services.domain.kag_core --directory app/services/domain/kag_core

  # 使用配置文件
  python update_kag_imports.py --config kag_update_config.json

  # 试运行模式（不实际修改文件）
  python update_kag_imports.py --directory app/services/domain/kag_core --dry-run

  # 生成默认配置文件
  python update_kag_imports.py --generate-config kag_update_config.json
        """
    )

    parser.add_argument('--directory', '-d',
                       help='要处理的目录路径')
    parser.add_argument('--source-path', '-s',
                       default='kag',
                       help='源导入路径前缀 (默认: kag)')
    parser.add_argument('--target-path', '-t',
                       default='app.services.domain.kag_core',
                       help='目标导入路径前缀 (默认: app.services.domain.kag_core)')
    parser.add_argument('--config', '-c',
                       help='配置文件路径 (JSON格式)')
    parser.add_argument('--generate-config',
                       help='生成默认配置文件到指定路径')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='试运行模式，不实际修改文件')

    args = parser.parse_args()

    # 生成配置文件
    if args.generate_config:
        config = create_default_config()
        updater = KAGImportUpdater(config)
        updater.save_config_to_file(args.generate_config)
        return

    # 检查必需参数
    if not args.directory and not args.config:
        parser.error("必须指定 --directory 或 --config 参数")

    # 创建更新器
    updater = KAGImportUpdater()

    # 加载配置
    if args.config:
        updater.load_config_from_file(args.config)
    else:
        # 使用命令行参数创建规则
        pattern = rf"\bfrom {re.escape(args.source_path)}\."
        replacement = f"from {args.target_path}."
        description = f"将 'from {args.source_path}.' 替换为 'from {args.target_path}.'"

        updater.add_replacement_rule(pattern, replacement, description)

    # 执行更新
    if args.directory:
        success = updater.update_imports(args.directory, args.dry_run)
        if success:
            if args.dry_run:
                print(f"\n试运行完成! 使用 --dry-run 参数查看将要进行的更改。")
                print("移除 --dry-run 参数以实际执行更新。")
            else:
                print(f"\n导入路径更新成功完成!")
        else:
            print(f"\n导入路径更新失败!")
            sys.exit(1)
    else:
        parser.error("使用配置文件时仍需指定 --directory 参数")

if __name__ == "__main__":
    main()
