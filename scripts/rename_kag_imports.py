#!/usr/bin/env python3
"""
KAG导入路径重命名脚本
将所有 'from kag.' 替换为 'from app.services.domain.kag_core.'
保持 knext 相关导入不变
"""

import os
import re
import sys
from pathlib import Path

def rename_kag_imports(directory_path):
    """
    重命名指定目录下所有Python文件中的KAG导入路径

    Args:
        directory_path (str): 要处理的目录路径
    """
    directory = Path(directory_path)
    if not directory.exists():
        print(f"错误: 目录 {directory_path} 不存在")
        return False

    # 统计信息
    total_files = 0
    modified_files = 0
    total_replacements = 0

    # 遍历所有Python文件
    for py_file in directory.rglob("*.py"):
        total_files += 1
        file_modified = False
        file_replacements = 0

        try:
            # 读取文件内容
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 替换 'from kag.' 为 'from app.services.domain.kag_core.'
            # 使用正则表达式确保精确匹配
            pattern = r'\bfrom kag\.'
            replacement = 'from app.services.domain.kag_core.'

            new_content, count = re.subn(pattern, replacement, content)

            if count > 0:
                file_modified = True
                file_replacements = count
                total_replacements += count

                # 写回文件
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f"✓ {py_file.relative_to(directory)}: {count} 处替换")

        except Exception as e:
            print(f"✗ 处理文件 {py_file} 时出错: {e}")
            continue

        if file_modified:
            modified_files += 1

    # 输出统计信息
    print(f"\n=== 重命名完成 ===")
    print(f"总文件数: {total_files}")
    print(f"修改文件数: {modified_files}")
    print(f"总替换次数: {total_replacements}")

    return True

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python rename_kag_imports.py <目录路径>")
        print("示例: python rename_kag_imports.py python-middleware/app/services/domain/kag_core")
        sys.exit(1)

    directory_path = sys.argv[1]

    print(f"开始重命名 {directory_path} 目录下的KAG导入路径...")
    print("将 'from kag.' 替换为 'from app.services.domain.kag_core.'")
    print("=" * 60)

    success = rename_kag_imports(directory_path)

    if success:
        print("\n重命名操作成功完成!")
    else:
        print("\n重命名操作失败!")
        sys.exit(1)

if __name__ == "__main__":
    main()
