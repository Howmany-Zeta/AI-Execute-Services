#!/usr/bin/env python3
"""
Document Writing Example - Modern AI-Powered Document Writer

This example demonstrates how to use the modern document writing component
to write various document types with production-grade features.

Features demonstrated:
1. Multiple write modes (create, overwrite, append, backup)
2. Various document formats (TXT, JSON, CSV, HTML, Markdown)
3. AI-powered content generation and enhancement
4. Batch writing operations
5. Production-grade features (backup, versioning, validation)
6. Cloud storage support
7. Transaction-like operations
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_document_writer():
    """Initialize the document writer tool"""
    try:
        from aiecs.tools.docs.document_writer_tool import DocumentWriterTool
        
        # Production-grade configuration
        config = {
            "enable_backup": True,
            "enable_versioning": True,
            "enable_content_validation": True,
            "atomic_write": True,
            "max_file_size": 10 * 1024 * 1024,  # 10MB for demo
            "temp_dir": tempfile.mkdtemp(prefix="doc_writer_"),
            "backup_dir": tempfile.mkdtemp(prefix="doc_backups_")
        }
        
        return DocumentWriterTool(config)
    except ImportError:
        logger.error("DocumentWriterTool not available. Please ensure it's properly installed.")
        return None

def setup_ai_writer_orchestrator():
    """Initialize the AI document writer orchestrator"""
    try:
        from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator
        return AIDocumentWriterOrchestrator()
    except ImportError:
        logger.error("AIDocumentWriterOrchestrator not available. Please ensure it's properly installed.")
        return None

def example_1_basic_writing_modes():
    """Example 1: Basic document writing modes"""
    print("\n=== Example 1: Basic Document Writing Modes ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    temp_dir = writer.settings.temp_dir
    
    # 1. CREATE mode - create new file
    print("\n1. CREATE Mode:")
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "new_document.txt"),
            content="这是一个新创建的文档。\n包含多行内容。",
            format="txt",
            mode="create"
        )
        print(f"✓ Created: {result['write_result']['path']}")
        print(f"  Size: {result['write_result']['size']} bytes")
    except Exception as e:
        print(f"✗ Create failed: {e}")
    
    # 2. APPEND mode - append to existing file
    print("\n2. APPEND Mode:")
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "new_document.txt"),
            content="\n这是追加的内容。",
            format="txt",
            mode="append"
        )
        print(f"✓ Appended to: {result['write_result']['path']}")
        print(f"  New size: {result['write_result']['size']} bytes")
    except Exception as e:
        print(f"✗ Append failed: {e}")
    
    # 3. OVERWRITE mode - overwrite existing file  
    print("\n3. OVERWRITE Mode:")
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "new_document.txt"),
            content="这是完全新的内容，覆盖了原有内容。",
            format="txt",
            mode="overwrite"
        )
        print(f"✓ Overwritten: {result['write_result']['path']}")
        print(f"  Final size: {result['write_result']['size']} bytes")
    except Exception as e:
        print(f"✗ Overwrite failed: {e}")
    
    # 4. BACKUP_WRITE mode - backup then write
    print("\n4. BACKUP_WRITE Mode:")
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "new_document.txt"),
            content="这是带备份的写入操作。",
            format="txt",
            mode="backup_write",
            backup_comment="安全更新测试"
        )
        print(f"✓ Written with backup: {result['write_result']['path']}")
        if result.get('backup_info'):
            print(f"  Backup: {result['backup_info']['backup_path']}")
            print(f"  Comment: {result['backup_info']['comment']}")
    except Exception as e:
        print(f"✗ Backup write failed: {e}")

def example_2_multiple_formats():
    """Example 2: Multiple document formats"""
    print("\n=== Example 2: Multiple Document Formats ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    temp_dir = writer.settings.temp_dir
    
    # JSON format
    print("\n1. JSON Format:")
    json_data = {
        "name": "Document Writer Tool",
        "version": "1.0",
        "features": ["atomic_write", "backup", "validation"],
        "config": {
            "max_file_size": "10MB",
            "encoding": "utf-8"
        }
    }
    
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "config.json"),
            content=json_data,
            format="json",
            mode="create",
            validation_level="strict"
        )
        print(f"✓ JSON written: {result['write_result']['path']}")
        print(f"  Validation: {result['content_metadata']['validation_level']}")
    except Exception as e:
        print(f"✗ JSON write failed: {e}")
    
    # CSV format
    print("\n2. CSV Format:")
    csv_data = [
        ["Name", "Age", "City", "Department"],
        ["张三", "30", "北京", "技术部"],
        ["李四", "25", "上海", "产品部"],
        ["王五", "35", "深圳", "市场部"]
    ]
    
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "employees.csv"),
            content=csv_data,
            format="csv",
            mode="create"
        )
        print(f"✓ CSV written: {result['write_result']['path']}")
    except Exception as e:
        print(f"✗ CSV write failed: {e}")
    
    # HTML format
    print("\n3. HTML Format:")
    html_data = {
        "title": "Document Writer Tool Demo",
        "heading": "功能演示",
        "content": "这是一个HTML文档写入演示。支持多种格式的文档写入操作。"
    }
    
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "demo.html"),
            content=html_data,
            format="html",
            mode="create"
        )
        print(f"✓ HTML written: {result['write_result']['path']}")
    except Exception as e:
        print(f"✗ HTML write failed: {e}")
    
    # Markdown format
    print("\n4. Markdown Format:")
    markdown_data = {
        "title": "Document Writer Tool",
        "description": "现代化文档写入组件",
        "features": [
            "原子操作",
            "自动备份", 
            "内容验证",
            "多格式支持"
        ]
    }
    
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "readme.md"),
            content=markdown_data,
            format="markdown",
            mode="create"
        )
        print(f"✓ Markdown written: {result['write_result']['path']}")
    except Exception as e:
        print(f"✗ Markdown write failed: {e}")

def example_3_ai_content_generation():
    """Example 3: AI-powered content generation"""
    print("\n=== Example 3: AI-Powered Content Generation ===")
    
    orchestrator = setup_ai_writer_orchestrator()
    if not orchestrator:
        return
    
    temp_dir = tempfile.mkdtemp(prefix="ai_writer_")
    
    # AI content generation
    print("\n1. AI Content Generation:")
    try:
        result = orchestrator.ai_write_document(
            target_path=os.path.join(temp_dir, "ai_report.md"),
            content_requirements="创建一份关于人工智能在文档处理中应用的技术报告，包含背景、技术方案、优势和发展趋势",
            generation_mode="generate",
            document_format="markdown",
            write_strategy="immediate",
            generation_params={
                "audience": "技术团队",
                "length": "详细",
                "style": "专业"
            }
        )
        print(f"✓ AI generated document: {result['write_result']['path']}")
        print(f"  Generation mode: {result['generation_mode']}")
        print(f"  AI provider: {result['ai_provider']}")
        
        # Show preview of generated content
        ai_content = result['ai_result']['generated_content']
        preview = ai_content[:300] + "..." if len(ai_content) > 300 else ai_content
        print(f"  Content preview: {preview}")
        
    except Exception as e:
        print(f"✗ AI generation failed: {e}")
    
    # Content enhancement
    print("\n2. Content Enhancement:")
    
    # First create a basic document
    basic_content = """
    人工智能文档处理系统

    这个系统可以处理文档。它有一些功能。
    系统很好用。可以提高效率。
    """
    
    basic_file = os.path.join(temp_dir, "basic_document.txt")
    writer = setup_document_writer()
    if writer:
        writer.write_document(
            target_path=basic_file,
            content=basic_content,
            format="txt",
            mode="create"
        )
    
    try:
        result = orchestrator.enhance_document(
            source_path=basic_file,
            enhancement_goals="提高文档专业性，增加技术细节，改善结构和表达",
            target_path=os.path.join(temp_dir, "enhanced_document.txt"),
            preserve_format=True
        )
        
        print(f"✓ Document enhanced: {result['target_path']}")
        
        # Show enhancement result
        enhanced_content = result['ai_result']['enhanced_content']
        preview = enhanced_content[:300] + "..." if len(enhanced_content) > 300 else enhanced_content
        print(f"  Enhanced preview: {preview}")
        
    except Exception as e:
        print(f"✗ Content enhancement failed: {e}")

def example_4_batch_operations():
    """Example 4: Batch writing operations"""
    print("\n=== Example 4: Batch Writing Operations ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    temp_dir = writer.settings.temp_dir
    
    # Prepare batch write operations
    write_operations = [
        {
            "target_path": os.path.join(temp_dir, "batch_file_1.txt"),
            "content": "批量操作文件1的内容",
            "format": "txt",
            "mode": "create"
        },
        {
            "target_path": os.path.join(temp_dir, "batch_file_2.json"),
            "content": {"batch_id": 2, "content": "JSON批量文件"},
            "format": "json", 
            "mode": "create"
        },
        {
            "target_path": os.path.join(temp_dir, "batch_file_3.csv"),
            "content": [["ID", "Name"], ["1", "File1"], ["2", "File2"]],
            "format": "csv",
            "mode": "create"
        }
    ]
    
    print(f"\n批量写入 {len(write_operations)} 个文件:")
    
    try:
        result = writer.batch_write_documents(
            write_operations=write_operations,
            transaction_mode=True,
            rollback_on_error=True
        )
        
        print(f"✓ Batch operation completed:")
        print(f"  Total: {result['total_operations']}")
        print(f"  Successful: {result['successful_operations']}")
        print(f"  Failed: {result['failed_operations']}")
        print(f"  Duration: {result['batch_metadata']['duration']:.2f}s")
        
        # Show individual results
        for i, op_result in enumerate(result['operations']):
            if op_result['status'] == 'success':
                write_result = op_result['result']['write_result']
                print(f"  File {i+1}: ✓ {write_result['path']} ({write_result['size']} bytes)")
            else:
                print(f"  File {i+1}: ✗ Failed")
        
    except Exception as e:
        print(f"✗ Batch operation failed: {e}")

def example_5_ai_batch_writing():
    """Example 5: AI-powered batch writing"""
    print("\n=== Example 5: AI-Powered Batch Writing ===")
    
    orchestrator = setup_ai_writer_orchestrator()
    if not orchestrator:
        return
    
    temp_dir = tempfile.mkdtemp(prefix="ai_batch_")
    
    # AI batch write requests
    write_requests = [
        {
            "target_path": os.path.join(temp_dir, "tech_article.md"),
            "content_requirements": "写一篇关于云计算技术的技术文章",
            "generation_mode": "generate",
            "document_format": "markdown",
            "generation_params": {"style": "技术博客", "length": "中等"}
        },
        {
            "target_path": os.path.join(temp_dir, "product_intro.html"),
            "content_requirements": "创建一个产品介绍页面，介绍AI文档处理工具",
            "generation_mode": "generate", 
            "document_format": "html",
            "generation_params": {"style": "营销页面", "audience": "开发者"}
        },
        {
            "target_path": os.path.join(temp_dir, "api_doc.txt"),
            "content_requirements": "编写API文档，说明文档写入接口的使用方法",
            "generation_mode": "generate",
            "document_format": "txt",
            "generation_params": {"style": "技术文档", "detail_level": "详细"}
        }
    ]
    
    print(f"\nAI批量生成 {len(write_requests)} 个文档:")
    
    try:
        result = orchestrator.batch_ai_write(
            write_requests=write_requests,
            coordination_strategy="parallel",
            max_concurrent=2
        )
        
        print(f"✓ AI batch operation completed:")
        print(f"  Total requests: {result['total_requests']}")
        print(f"  Successful: {result['successful_requests']}")
        print(f"  Failed: {result['failed_requests']}")
        print(f"  Duration: {result['batch_metadata']['duration']:.2f}s")
        
        # Show results
        for i, req_result in enumerate(result['results']):
            if req_result['status'] == 'success':
                target = req_result['result']['target_path']
                print(f"  Document {i+1}: ✓ {os.path.basename(target)}")
            else:
                print(f"  Document {i+1}: ✗ {req_result.get('error', 'Failed')}")
        
    except Exception as e:
        print(f"✗ AI batch operation failed: {e}")

def example_6_template_usage():
    """Example 6: Template-based document generation"""
    print("\n=== Example 6: Template-Based Document Generation ===")
    
    orchestrator = setup_ai_writer_orchestrator()
    if not orchestrator:
        return
    
    temp_dir = tempfile.mkdtemp(prefix="template_")
    
    # Create a document template
    print("\n1. Creating Document Template:")
    try:
        template_info = orchestrator.create_content_template(
            template_name="meeting_report",
            template_content="""
# 会议纪要 - {meeting_title}

**时间**: {meeting_date}  
**地点**: {meeting_location}  
**主持人**: {meeting_host}  
**参会人员**: {attendees}

## 会议议题
{agenda}

## 讨论要点
{discussion_points}

## 决议事项
{decisions}

## 后续行动
{action_items}

## 下次会议
时间: {next_meeting}
            """,
            template_variables=[
                "meeting_title", "meeting_date", "meeting_location", 
                "meeting_host", "attendees", "agenda", "discussion_points",
                "decisions", "action_items", "next_meeting"
            ],
            metadata={"category": "meeting", "version": "1.0"}
        )
        
        print(f"✓ Template created: {template_info['name']}")
        print(f"  Variables: {len(template_info['variables'])}")
        
    except Exception as e:
        print(f"✗ Template creation failed: {e}")
        return
    
    # Use template to generate document
    print("\n2. Using Template:")
    try:
        result = orchestrator.use_content_template(
            template_name="meeting_report",
            template_data={
                "meeting_title": "产品开发进度讨论会",
                "meeting_date": "2024年1月15日 14:00-16:00",
                "meeting_location": "会议室A",
                "meeting_host": "张产品经理",
                "attendees": "开发团队、测试团队、设计团队",
                "agenda": "1. 当前开发进度回顾\n2. 遇到的技术难题讨论\n3. 下阶段计划制定",
                "discussion_points": "- 文档写入功能基本完成\n- 需要优化性能表现\n- UI界面需要调整",
                "decisions": "1. 延长测试周期一周\n2. 增加性能测试用例\n3. UI调整在下个版本",
                "action_items": "- 开发团队：性能优化 (本周)\n- 测试团队：编写测试用例 (本周)\n- 产品团队：UI需求整理 (下周)",
                "next_meeting": "2024年1月22日 14:00"
            },
            target_path=os.path.join(temp_dir, "meeting_report_20240115.md"),
            ai_enhancement=True
        )
        
        print(f"✓ Document generated from template: {result['target_path']}")
        print(f"  AI enhancement: {result['ai_enhancement']}")
        
        # Show content preview
        content = result['filled_content']
        preview = content[:400] + "..." if len(content) > 400 else content
        print(f"  Content preview:\n{preview}")
        
    except Exception as e:
        print(f"✗ Template usage failed: {e}")

def example_7_production_features():
    """Example 7: Production-grade features"""
    print("\n=== Example 7: Production-Grade Features ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    temp_dir = writer.settings.temp_dir
    
    # Content validation
    print("\n1. Content Validation:")
    
    # Valid JSON
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "valid_config.json"),
            content='{"setting": "value", "number": 42}',
            format="json",
            mode="create",
            validation_level="strict"
        )
        print("✓ Valid JSON content validation passed")
    except Exception as e:
        print(f"✗ Valid JSON validation failed: {e}")
    
    # Invalid JSON (should fail with strict validation)
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "invalid_config.json"),
            content='{"setting": "value", "number": }',  # Invalid JSON
            format="json",
            mode="create",
            validation_level="strict"
        )
        print("✗ Invalid JSON validation should have failed")
    except Exception as e:
        print("✓ Invalid JSON correctly rejected by validation")
    
    # Security scanning
    print("\n2. Security Scanning:")
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "user_content.html"),
            content="<script>alert('xss')</script><p>Normal content</p>",
            format="html",
            mode="create",
            validation_level="enterprise"  # Enables security scanning
        )
        print("✗ Malicious content should have been blocked")
    except Exception as e:
        print("✓ Security scan correctly blocked malicious content")
    
    # Versioning and backup
    print("\n3. Versioning and Backup:")
    config_file = os.path.join(temp_dir, "app_config.json")
    
    # Initial version
    config_v1 = {"version": "1.0", "feature_x": "enabled"}
    result1 = writer.write_document(
        target_path=config_file,
        content=config_v1,
        format="json",
        mode="create"
    )
    print(f"✓ Version 1 created: {result1['version_info']['version'] if result1.get('version_info') else 'N/A'}")
    
    # Update with backup
    config_v2 = {"version": "2.0", "feature_x": "enhanced", "feature_y": "new"}
    result2 = writer.write_document(
        target_path=config_file,
        content=config_v2,
        format="json",
        mode="backup_write",
        backup_comment="Added feature_y"
    )
    print(f"✓ Version 2 with backup: {result2['backup_info']['backup_path'] if result2.get('backup_info') else 'N/A'}")
    
    # Atomic write demonstration
    print("\n4. Atomic Write:")
    large_content = "Large content: " + "x" * 1000  # Simulate large content
    
    try:
        result = writer.write_document(
            target_path=os.path.join(temp_dir, "large_file.txt"),
            content=large_content,
            format="txt",
            mode="create"
        )
        print(f"✓ Atomic write completed: {result['write_result']['atomic_write']}")
    except Exception as e:
        print(f"✗ Atomic write failed: {e}")

async def example_8_async_operations():
    """Example 8: Asynchronous operations"""
    print("\n=== Example 8: Asynchronous Operations ===")
    
    writer = setup_document_writer()
    orchestrator = setup_ai_writer_orchestrator()
    
    if not writer or not orchestrator:
        return
    
    temp_dir = tempfile.mkdtemp(prefix="async_")
    
    print("\nAsync document writing:")
    
    # Async write operations
    async def write_document_async(index):
        try:
            result = await orchestrator.ai_write_document_async(
                target_path=os.path.join(temp_dir, f"async_doc_{index}.txt"),
                content_requirements=f"生成第{index}个异步文档的内容",
                generation_mode="generate",
                document_format="txt"
            )
            return f"✓ Async document {index} completed"
        except Exception as e:
            return f"✗ Async document {index} failed: {e}"
    
    # Run multiple async operations
    tasks = [write_document_async(i) for i in range(1, 4)]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        print(f"  {result}")

def example_9_error_handling():
    """Example 9: Error handling and recovery"""
    print("\n=== Example 9: Error Handling and Recovery ===")
    
    writer = setup_document_writer()
    if not writer:
        return
    
    from aiecs.tools.docs.document_writer_tool import (
        DocumentWriterError,
        WritePermissionError,
        ContentValidationError
    )
    
    temp_dir = writer.settings.temp_dir
    
    # Test different error scenarios
    print("\n1. File Already Exists Error:")
    existing_file = os.path.join(temp_dir, "existing.txt")
    
    # Create file first
    writer.write_document(
        target_path=existing_file,
        content="Original content",
        format="txt",
        mode="create"
    )
    
    # Try to create again (should fail)
    try:
        writer.write_document(
            target_path=existing_file,
            content="New content",
            format="txt",
            mode="create"  # Should fail because file exists
        )
        print("✗ Should have failed due to existing file")
    except DocumentWriterError as e:
        print(f"✓ Correctly caught file exists error: {type(e).__name__}")
    
    print("\n2. Content Validation Error:")
    try:
        writer.write_document(
            target_path=os.path.join(temp_dir, "invalid.json"),
            content="not valid json content {",
            format="json",
            mode="create",
            validation_level="strict"
        )
        print("✗ Should have failed due to invalid JSON")
    except ContentValidationError as e:
        print(f"✓ Correctly caught validation error: {type(e).__name__}")
    
    print("\n3. Recovery with Backup:")
    important_file = os.path.join(temp_dir, "important.txt")
    
    # Create important file
    writer.write_document(
        target_path=important_file,
        content="Important original content",
        format="txt",
        mode="create"
    )
    
    # Try risky update with backup
    try:
        result = writer.write_document(
            target_path=important_file,
            content="Risky update content",
            format="txt",
            mode="backup_write"
        )
        print(f"✓ Risky update succeeded with backup: {result['backup_info']['backup_path']}")
    except Exception as e:
        print(f"✗ Update failed but backup available: {e}")

def main():
    """Main function to run all document writing examples"""
    print("Modern AI-Powered Document Writing Examples")
    print("=" * 60)
    
    try:
        # Run synchronous examples
        example_1_basic_writing_modes()
        example_2_multiple_formats()
        example_3_ai_content_generation()
        example_4_batch_operations()
        example_5_ai_batch_writing()
        example_6_template_usage()
        example_7_production_features()
        example_9_error_handling()
        
        # Run async example
        print("\nRunning async example...")
        asyncio.run(example_8_async_operations())
        
        print("\n" + "=" * 60)
        print("All document writing examples completed successfully!")
        
        # Implementation notes
        print("\n📝 Key Features Demonstrated:")
        print("✅ Multiple write modes (create, overwrite, append, backup)")
        print("✅ Various document formats (TXT, JSON, CSV, HTML, Markdown)")
        print("✅ AI-powered content generation and enhancement")
        print("✅ Batch and async operations")
        print("✅ Production features (validation, backup, versioning)")
        print("✅ Error handling and recovery")
        print("✅ Template-based document generation")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nError running examples: {e}")
        logger.exception("Exception in main:")

if __name__ == "__main__":
    main()
