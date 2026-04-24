#!/usr/bin/env python3
# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Advanced Document Editing Example

This example demonstrates the comprehensive editing capabilities
of the enhanced DocumentWriterTool, including:

1. Text formatting (bold, italic, underline, strikethrough, highlight)
2. Text operations (insert, delete, replace, copy, cut, paste)
3. Line operations (insert, delete, move)
4. Advanced find/replace with regex support
5. Position-based and selection-based editing
"""

import tempfile
import os
from pathlib import Path

def setup_document_writer():
    """Initialize the enhanced document writer tool"""
    try:
        from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
        
        config = {
            "temp_dir": tempfile.mkdtemp(prefix="advanced_edit_"),
            "backup_dir": tempfile.mkdtemp(prefix="edit_backups_"),
            "enable_backup": True,
            "atomic_write": True
        }
        
        return DocumentWriterTool(config)
    except ImportError:
        print("DocumentWriterTool not available")
        return None

def create_sample_document(writer, file_path):
    """Create a sample document for editing demonstrations"""
    sample_content = """# 文档编辑示例

这是一个用于演示高级编辑功能的示例文档。

## 基本内容
这里有一些普通文本内容。
这行文本将用于格式化演示。
还有一些需要修改的内容。

## 功能特点
- 支持多种文本格式
- 提供丰富的编辑操作
- 实现精确的位置控制

## 结论
通过这些功能，可以实现强大的文档编辑能力。
"""
    
    result = writer.write_document(
        target_path=file_path,
        content=sample_content,
        format="markdown",
        mode="create"
    )
    print(f"✓ Created sample document: {file_path}")
    return result

def example_1_text_formatting():
    """Example 1: Text formatting operations"""
    print("\n=== Example 1: Text Formatting Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    # Create sample document
    doc_path = os.path.join(writer.settings.temp_dir, "formatting_demo.md")
    create_sample_document(writer, doc_path)
    
    print("\n1. Bold Formatting:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="bold",
            selection={
                "start_offset": 50,  # Position of text to format
                "end_offset": 65     # End position
            },
            format_options={"format_type": "markdown"}
        )
        print(f"✓ Applied bold formatting: {result['operation']}")
    except Exception as e:
        print(f"✗ Bold formatting failed: {e}")
    
    print("\n2. Italic Formatting:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="italic",
            selection={
                "start_line": 5,     # Line-based selection
                "end_line": 5,
                "start_column": 5,
                "end_column": 15
            },
            format_options={"format_type": "markdown"}
        )
        print(f"✓ Applied italic formatting: {result['operation']}")
    except Exception as e:
        print(f"✗ Italic formatting failed: {e}")
    
    print("\n3. Highlight Formatting:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="highlight",
            selection={
                "start_offset": 100,
                "end_offset": 120
            },
            format_options={
                "format_type": "html",
                "color": "yellow"
            }
        )
        print(f"✓ Applied highlight formatting: {result['operation']}")
    except Exception as e:
        print(f"✗ Highlight formatting failed: {e}")
    
    print("\n4. Text Formatting by Content:")
    try:
        result = writer.format_text(
            target_path=doc_path,
            text_to_format="功能特点",
            format_type="bold",
            format_options={"format_type": "markdown"}
        )
        print(f"✓ Formatted specific text: {result['text_formatted']}")
    except Exception as e:
        print(f"✗ Text formatting failed: {e}")

def example_2_text_operations():
    """Example 2: Text insert, delete, replace operations"""
    print("\n=== Example 2: Text Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    doc_path = os.path.join(writer.settings.temp_dir, "text_ops_demo.txt")
    
    # Create initial content
    initial_content = "这是第一行。\n这是第二行。\n这是第三行。"
    writer.write_document(
        target_path=doc_path,
        content=initial_content,
        format="txt",
        mode="create"
    )
    print(f"✓ Created initial document")
    
    print("\n1. Insert Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="insert_text",
            content="[插入的内容] ",
            position={
                "line": 1,      # Insert at line 1
                "column": 0     # At the beginning
            }
        )
        print(f"✓ Inserted text at line 1, column 0")
    except Exception as e:
        print(f"✗ Insert text failed: {e}")
    
    print("\n2. Delete Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="delete_text",
            selection={
                "start_line": 2,
                "end_line": 2,
                "start_column": 2,
                "end_column": 4
            }
        )
        print(f"✓ Deleted text from line 2, columns 2-4")
    except Exception as e:
        print(f"✗ Delete text failed: {e}")
    
    print("\n3. Replace Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="replace_text",
            content="[替换后的内容]",
            selection={
                "start_offset": 10,
                "end_offset": 15
            }
        )
        print(f"✓ Replaced text at offset 10-15")
    except Exception as e:
        print(f"✗ Replace text failed: {e}")

def example_3_copy_cut_paste():
    """Example 3: Copy, cut, and paste operations"""
    print("\n=== Example 3: Copy, Cut, and Paste Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    doc_path = os.path.join(writer.settings.temp_dir, "clipboard_demo.txt")
    
    # Create content for clipboard operations
    content = "原始内容第一段。\n这段文字将被复制。\n这是第三段内容。"
    writer.write_document(
        target_path=doc_path,
        content=content,
        format="txt",
        mode="create"
    )
    
    print("\n1. Copy Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="copy_text",
            selection={
                "start_line": 1,    # Copy the second line
                "end_line": 1,
                "start_column": 0,
                "end_column": -1    # To end of line
            }
        )
        print(f"✓ Copied text: '{result['copied_text'][:30]}...'")
        print(f"  Copied {result['copied_length']} characters")
    except Exception as e:
        print(f"✗ Copy failed: {e}")
    
    print("\n2. Cut Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="cut_text",
            selection={
                "start_offset": 8,
                "end_offset": 15
            }
        )
        print(f"✓ Cut text operation completed")
    except Exception as e:
        print(f"✗ Cut failed: {e}")
    
    print("\n3. Paste Text:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="paste_text",
            position={
                "line": 2,      # Paste at line 2
                "column": 5     # Column 5
            }
        )
        print(f"✓ Pasted text at line 2, column 5")
    except Exception as e:
        print(f"✗ Paste failed: {e}")

def example_4_line_operations():
    """Example 4: Line-based operations"""
    print("\n=== Example 4: Line Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    doc_path = os.path.join(writer.settings.temp_dir, "line_ops_demo.txt")
    
    # Create multi-line content
    lines_content = """Line 1: 第一行内容
Line 2: 第二行内容  
Line 3: 第三行内容
Line 4: 第四行内容
Line 5: 第五行内容"""
    
    writer.write_document(
        target_path=doc_path,
        content=lines_content,
        format="txt",
        mode="create"
    )
    
    print("\n1. Insert Line:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="insert_line",
            content="新插入的行: 这是在第2行位置插入的内容",
            position={"line": 2}  # Insert at line 2
        )
        print(f"✓ Inserted new line at position 2")
    except Exception as e:
        print(f"✗ Insert line failed: {e}")
    
    print("\n2. Delete Line:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="delete_line",
            position={"line": 4}  # Delete line 4
        )
        print(f"✓ Deleted line 4")
    except Exception as e:
        print(f"✗ Delete line failed: {e}")
    
    print("\n3. Move Line:")
    try:
        result = writer.edit_document(
            target_path=doc_path,
            operation="move_line",
            position={"line": 1},        # Move from line 1
            format_options={"to_line": 3}  # To line 3
        )
        print(f"✓ Moved line 1 to position 3")
    except Exception as e:
        print(f"✗ Move line failed: {e}")

def example_5_find_replace():
    """Example 5: Advanced find and replace operations"""
    print("\n=== Example 5: Find and Replace Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    doc_path = os.path.join(writer.settings.temp_dir, "find_replace_demo.txt")
    
    # Create content with repeated patterns
    content = """这是一个示例文档。
示例文档包含多个示例。
EXAMPLE文档用于演示功能。
example功能非常强大。
最后一个示例结束。"""
    
    writer.write_document(
        target_path=doc_path,
        content=content,
        format="txt", 
        mode="create"
    )
    
    print("\n1. Simple Find and Replace:")
    try:
        result = writer.find_replace(
            target_path=doc_path,
            find_text="示例",
            replace_text="样例",
            replace_all=True,
            case_sensitive=True
        )
        print(f"✓ Replaced {result['replacements_made']} occurrences of '示例' with '样例'")
    except Exception as e:
        print(f"✗ Simple find/replace failed: {e}")
    
    print("\n2. Case-Insensitive Replace:")
    try:
        result = writer.find_replace(
            target_path=doc_path,
            find_text="example",
            replace_text="范例",
            replace_all=True,
            case_sensitive=False  # Case insensitive
        )
        print(f"✓ Case-insensitive replace: {result['replacements_made']} replacements")
    except Exception as e:
        print(f"✗ Case-insensitive replace failed: {e}")
    
    print("\n3. Regex Find and Replace:")
    try:
        result = writer.find_replace(
            target_path=doc_path,
            find_text=r"文档.*?功能",    # Regex pattern
            replace_text="文档[正则替换]功能",
            replace_all=True,
            regex_mode=True
        )
        print(f"✓ Regex replace: {result['replacements_made']} replacements")
    except Exception as e:
        print(f"✗ Regex replace failed: {e}")
    
    print("\n4. Single Occurrence Replace:")
    try:
        result = writer.find_replace(
            target_path=doc_path,
            find_text="强大",
            replace_text="卓越",
            replace_all=False  # Only first occurrence
        )
        print(f"✓ Single replace: {result['replacements_made']} replacement")
    except Exception as e:
        print(f"✗ Single replace failed: {e}")

def example_6_position_based_editing():
    """Example 6: Precise position-based editing"""
    print("\n=== Example 6: Position-Based Editing ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    doc_path = os.path.join(writer.settings.temp_dir, "position_demo.txt")
    
    # Create structured content
    structured_content = """标题: 文档编辑演示
作者: AI助手
日期: 2024-01-01

正文内容:
这是第一段内容。
这是第二段内容。
这是第三段内容。

结论:
编辑功能测试完成。"""
    
    writer.write_document(
        target_path=doc_path,
        content=structured_content,
        format="txt",
        mode="create"
    )
    
    print("\n1. Offset-Based Editing:")
    try:
        # Insert at specific character offset
        result = writer.edit_document(
            target_path=doc_path,
            operation="insert_text",
            content="[修改版] ",
            position={"offset": 3}  # After "标题:"
        )
        print(f"✓ Inserted text at offset 3")
    except Exception as e:
        print(f"✗ Offset-based insert failed: {e}")
    
    print("\n2. Line/Column-Based Editing:")
    try:
        # Edit at specific line and column
        result = writer.edit_document(
            target_path=doc_path,
            operation="replace_text",
            content="AI文档处理系统",
            selection={
                "start_line": 1,    # Line 1 (0-indexed)
                "end_line": 1,
                "start_column": 3,  # After "作者: "
                "end_column": 6     # Replace "AI助手"
            }
        )
        print(f"✓ Replaced text at line 1, columns 3-6")
    except Exception as e:
        print(f"✗ Line/column-based replace failed: {e}")
    
    print("\n3. Multi-Line Selection:")
    try:
        # Select and format multiple lines
        result = writer.edit_document(
            target_path=doc_path,
            operation="bold",
            selection={
                "start_line": 4,    # From line 4
                "end_line": 6,      # To line 6
                "start_column": 0,
                "end_column": -1    # Entire lines
            },
            format_options={"format_type": "markdown"}
        )
        print(f"✓ Applied bold formatting to lines 4-6")
    except Exception as e:
        print(f"✗ Multi-line formatting failed: {e}")

def example_7_format_specific_operations():
    """Example 7: Format-specific editing operations"""
    print("\n=== Example 7: Format-Specific Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    # HTML document editing
    html_path = os.path.join(writer.settings.temp_dir, "html_demo.html")
    html_content = """<!DOCTYPE html>
<html>
<head><title>测试页面</title></head>
<body>
<h1>主标题</h1>
<p>这是一段普通文本。</p>
<p>这段文本需要格式化。</p>
</body>
</html>"""
    
    writer.write_document(
        target_path=html_path,
        content=html_content,
        format="html",
        mode="create"
    )
    
    print("\n1. HTML Bold Formatting:")
    try:
        result = writer.edit_document(
            target_path=html_path,
            operation="bold",
            selection={
                "start_offset": 120,
                "end_offset": 135
            },
            format_options={"format_type": "html"}
        )
        print(f"✓ Applied HTML bold formatting")
    except Exception as e:
        print(f"✗ HTML bold formatting failed: {e}")
    
    # Markdown document editing
    md_path = os.path.join(writer.settings.temp_dir, "markdown_demo.md")
    md_content = """# Markdown编辑演示

这是**粗体**文本和*斜体*文本的示例。

## 列表示例
- 项目1
- 项目2
- 项目3

普通段落文本。"""
    
    writer.write_document(
        target_path=md_path,
        content=md_content,
        format="markdown",
        mode="create"
    )
    
    print("\n2. Markdown Strikethrough:")
    try:
        result = writer.edit_document(
            target_path=md_path,
            operation="strikethrough",
            selection={
                "start_offset": 100,
                "end_offset": 105
            },
            format_options={"format_type": "markdown"}
        )
        print(f"✓ Applied Markdown strikethrough")
    except Exception as e:
        print(f"✗ Markdown strikethrough failed: {e}")

def show_final_results(writer):
    """Show the results of all editing operations"""
    print("\n=== Final Results ===")
    
    temp_dir = writer.settings.temp_dir
    backup_dir = writer.settings.backup_dir
    
    # List created files
    print(f"\n📁 Created files in: {temp_dir}")
    try:
        for file in os.listdir(temp_dir):
            if file.endswith(('.txt', '.md', '.html')):
                file_path = os.path.join(temp_dir, file)
                size = os.path.getsize(file_path)
                print(f"  📄 {file} ({size} bytes)")
    except:
        pass
    
    # List backup files
    print(f"\n💾 Backup files in: {backup_dir}")
    try:
        backup_count = len([f for f in os.listdir(backup_dir) if f.endswith('_backup_')])
        print(f"  📦 {backup_count} backup files created")
    except:
        print("  📦 Backup directory not accessible")
    
    print(f"\n📊 Operation Summary:")
    print(f"  ✅ Text Formatting: Bold, Italic, Underline, Strikethrough, Highlight")
    print(f"  ✅ Text Operations: Insert, Delete, Replace")
    print(f"  ✅ Clipboard: Copy, Cut, Paste")
    print(f"  ✅ Line Operations: Insert, Delete, Move")
    print(f"  ✅ Find/Replace: Simple, Case-insensitive, Regex")
    print(f"  ✅ Position Control: Offset-based, Line/Column-based")
    print(f"  ✅ Format Support: HTML, Markdown, Plain Text")

def main():
    """Main function to run all advanced editing examples"""
    print("Advanced Document Editing Capabilities Demo")
    print("=" * 70)
    
    try:
        # Run all editing examples
        example_1_text_formatting()
        example_2_text_operations()
        example_3_copy_cut_paste()
        example_4_line_operations()
        example_5_find_replace()
        example_6_position_based_editing()
        example_7_format_specific_operations()
        
        # Show results
        writer = setup_document_writer()
        if writer:
            show_final_results(writer)
        
        print("\n" + "=" * 70)
        print("🎉 All advanced editing examples completed successfully!")
        
        print("\n📋 Supported Operations Summary:")
        print("✅ 9 基础写入模式 (CREATE, OVERWRITE, APPEND, etc.)")
        print("✅ 15 高级编辑操作 (BOLD, ITALIC, INSERT_TEXT, etc.)")
        print("✅ 11 文档格式支持 (TXT, JSON, HTML, Markdown, etc.)")
        print("✅ 精确位置控制 (offset, line/column)")
        print("✅ 选择范围操作 (single/multi-line selections)")
        print("✅ 格式特定处理 (HTML tags, Markdown syntax)")
        print("✅ 剪贴板功能 (copy, cut, paste)")
        print("✅ 查找替换 (simple, regex, case-insensitive)")
        print("✅ 自动备份和版本控制")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError in demo: {e}")

if __name__ == "__main__":
    main()
