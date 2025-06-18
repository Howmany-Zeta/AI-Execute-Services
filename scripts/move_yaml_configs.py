#!/usr/bin/env python3
"""
KAG YAML配置文件集中管理脚本
将 kag_core 中的所有 YAML 文件移动到 kag_configs 目录集中管理
并更新相关的文件引用路径
"""

import os
import re
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

class YAMLConfigMover:
    """YAML配置文件移动器"""

    def __init__(self, source_dir: str, target_dir: str):
        """
        初始化移动器

        Args:
            source_dir (str): 源目录路径
            target_dir (str): 目标目录路径
        """
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.moved_files = []
        self.updated_references = []

    def find_yaml_files(self) -> List[Path]:
        """
        查找所有YAML文件

        Returns:
            List[Path]: YAML文件路径列表
        """
        yaml_files = []
        for pattern in ['*.yaml', '*.yml']:
            yaml_files.extend(self.source_dir.rglob(pattern))
        return yaml_files

    def create_target_structure(self, yaml_files: List[Path]) -> Dict[Path, Path]:
        """
        创建目标目录结构并计算文件映射

        Args:
            yaml_files (List[Path]): YAML文件列表

        Returns:
            Dict[Path, Path]: 源文件到目标文件的映射
        """
        file_mapping = {}

        for yaml_file in yaml_files:
            # 计算相对路径
            rel_path = yaml_file.relative_to(self.source_dir)

            # 创建目标路径，保持目录结构
            target_file = self.target_dir / rel_path

            # 确保目标目录存在
            target_file.parent.mkdir(parents=True, exist_ok=True)

            file_mapping[yaml_file] = target_file

        return file_mapping

    def move_yaml_files(self, file_mapping: Dict[Path, Path]) -> None:
        """
        移动YAML文件

        Args:
            file_mapping (Dict[Path, Path]): 文件映射
        """
        print("开始移动YAML文件...")

        for source_file, target_file in file_mapping.items():
            try:
                # 移动文件
                shutil.move(str(source_file), str(target_file))
                self.moved_files.append((source_file, target_file))
                try:
                    target_rel = target_file.relative_to(Path.cwd())
                except ValueError:
                    target_rel = target_file
                print(f"✓ 移动: {source_file.relative_to(self.source_dir)} -> {target_rel}")

            except Exception as e:
                print(f"✗ 移动失败: {source_file} -> {target_file}, 错误: {e}")

    def find_yaml_references(self) -> List[Tuple[Path, List[str]]]:
        """
        查找对YAML文件的引用

        Returns:
            List[Tuple[Path, List[str]]]: 包含引用的文件和引用行
        """
        references = []

        # 搜索Python文件中的YAML引用
        for py_file in self.source_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                # 查找可能的YAML文件引用
                yaml_refs = []
                for i, line in enumerate(lines, 1):
                    # 匹配各种可能的YAML文件引用模式
                    patterns = [
                        r'["\']([^"\']*\.ya?ml)["\']',  # 字符串中的yaml文件
                        r'config_file\s*=\s*["\']([^"\']*\.ya?ml)["\']',  # 配置文件赋值
                        r'load.*["\']([^"\']*\.ya?ml)["\']',  # load函数调用
                        r'open\s*\(["\']([^"\']*\.ya?ml)["\']',  # open函数调用
                        r'pipelineconf/([^"\']*\.ya?ml)',  # pipelineconf目录引用
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, line)
                        if matches:
                            for match in matches:
                                yaml_refs.append(f"第{i}行: {line.strip()}")

                if yaml_refs:
                    references.append((py_file, yaml_refs))

            except Exception as e:
                print(f"警告: 读取文件 {py_file} 时出错: {e}")

        return references

    def update_yaml_references(self, file_mapping: Dict[Path, Path]) -> None:
        """
        更新YAML文件引用路径

        Args:
            file_mapping (Dict[Path, Path]): 文件映射
        """
        print("\n开始更新YAML文件引用...")

        # 创建路径映射表
        path_mappings = {}
        for source_file, target_file in file_mapping.items():
            # 从源目录的相对路径
            source_rel = source_file.relative_to(self.source_dir)
            # 到目标目录的相对路径（从项目根目录开始）
            try:
                target_rel = target_file.relative_to(Path.cwd())
            except ValueError:
                target_rel = target_file

            # 创建多种可能的路径映射
            path_mappings[str(source_rel)] = str(target_rel)
            path_mappings[f"pipelineconf/{source_rel.name}"] = str(target_rel)
            path_mappings[source_rel.name] = str(target_rel)

        # 搜索并更新引用
        updated_files = 0
        for py_file in Path("python-middleware").rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # 应用路径替换
                for old_path, new_path in path_mappings.items():
                    # 替换字符串中的路径
                    patterns = [
                        (rf'(["\']){re.escape(old_path)}(["\'])', rf'\1{new_path}\2'),
                        (rf'(["\'])([^"\']*/){{0,1}}{re.escape(old_path)}(["\'])', rf'\1{new_path}\3'),
                    ]

                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content)

                # 如果内容有变化，写回文件
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                    updated_files += 1
                    self.updated_references.append(py_file)
                    print(f"✓ 更新引用: {py_file.relative_to(Path.cwd())}")

            except Exception as e:
                print(f"✗ 更新引用失败: {py_file}, 错误: {e}")

        if updated_files == 0:
            print("没有找到需要更新的文件引用")

    def cleanup_empty_directories(self) -> None:
        """清理空目录"""
        print("\n清理空目录...")

        def remove_empty_dirs(path: Path):
            """递归删除空目录"""
            if not path.exists() or not path.is_dir():
                return

            # 先处理子目录
            for child in path.iterdir():
                if child.is_dir():
                    remove_empty_dirs(child)

            # 如果目录为空，删除它
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    print(f"✓ 删除空目录: {path.relative_to(self.source_dir)}")
            except OSError:
                pass  # 目录不为空或无法删除

        # 从移动的文件的父目录开始清理
        dirs_to_check = set()
        for source_file, _ in self.moved_files:
            dirs_to_check.add(source_file.parent)

        for dir_path in dirs_to_check:
            remove_empty_dirs(dir_path)

    def generate_summary(self) -> None:
        """生成移动总结"""
        print(f"\n=== YAML配置文件移动完成 ===")
        print(f"移动文件数: {len(self.moved_files)}")
        print(f"更新引用文件数: {len(self.updated_references)}")

        if self.moved_files:
            print(f"\n移动的文件:")
            for source_file, target_file in self.moved_files:
                try:
                    target_rel = target_file.relative_to(Path.cwd())
                except ValueError:
                    target_rel = target_file
                print(f"  {source_file.relative_to(self.source_dir)} -> {target_rel}")

        if self.updated_references:
            print(f"\n更新引用的文件:")
            for ref_file in self.updated_references:
                try:
                    ref_rel = ref_file.relative_to(Path.cwd())
                except ValueError:
                    ref_rel = ref_file
                print(f"  {ref_rel}")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="移动KAG YAML配置文件到集中管理目录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 移动kag_core中的YAML文件到kag_configs目录
  python move_yaml_configs.py --source app/services/domain/kag_core --target app/services/domain/kag_configs

  # 试运行模式
  python move_yaml_configs.py --source app/services/domain/kag_core --target app/services/domain/kag_configs --dry-run
        """
    )

    parser.add_argument('--source', '-s',
                       default='app/services/domain/kag_core',
                       help='源目录路径 (默认: app/services/domain/kag_core)')
    parser.add_argument('--target', '-t',
                       default='app/services/domain/kag_configs',
                       help='目标目录路径 (默认: app/services/domain/kag_configs)')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='试运行模式，不实际移动文件')

    args = parser.parse_args()

    # 创建移动器
    mover = YAMLConfigMover(args.source, args.target)

    # 查找YAML文件
    yaml_files = mover.find_yaml_files()

    if not yaml_files:
        print(f"在 {args.source} 中没有找到YAML文件")
        return

    print(f"找到 {len(yaml_files)} 个YAML文件:")
    for yaml_file in yaml_files:
        print(f"  {yaml_file.relative_to(mover.source_dir)}")

    if args.dry_run:
        print(f"\n[试运行模式] 将要移动到: {args.target}")

        # 显示将要创建的目录结构
        file_mapping = mover.create_target_structure(yaml_files)
        print(f"\n将要创建的文件映射:")
        for source_file, target_file in file_mapping.items():
            try:
                target_rel = target_file.relative_to(Path.cwd())
            except ValueError:
                target_rel = target_file
            print(f"  {source_file.relative_to(mover.source_dir)} -> {target_rel}")

        # 查找引用
        references = mover.find_yaml_references()
        if references:
            print(f"\n找到的YAML文件引用:")
            for ref_file, ref_lines in references:
                print(f"  {ref_file.relative_to(mover.source_dir)}:")
                for ref_line in ref_lines[:3]:  # 只显示前3个引用
                    print(f"    {ref_line}")
                if len(ref_lines) > 3:
                    print(f"    ... 还有 {len(ref_lines) - 3} 个引用")

        print(f"\n试运行完成! 移除 --dry-run 参数以实际执行移动。")
        return

    # 确认操作
    response = input(f"\n确定要将YAML文件移动到 {args.target} 吗? (y/N): ")
    if response.lower() != 'y':
        print("操作已取消")
        return

    # 创建目标目录结构
    file_mapping = mover.create_target_structure(yaml_files)

    # 移动文件
    mover.move_yaml_files(file_mapping)

    # 更新引用
    mover.update_yaml_references(file_mapping)

    # 清理空目录
    mover.cleanup_empty_directories()

    # 生成总结
    mover.generate_summary()

    print(f"\nYAML配置文件移动完成!")

if __name__ == "__main__":
    main()
