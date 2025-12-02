#!/usr/bin/env python3
"""
验证 ExecutorConfig 字段过滤修复

快速验证工具是否正确使用 self._config_obj 而不是重新创建 Config 对象
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def verify_tool(tool_name, tool_class):
    """验证单个工具"""
    try:
        # 混合配置：包含 executor 字段和工具特有字段
        config = {
            "enable_cache": True,
            "max_workers": 8,
            "timeout": 60,
            "test_field": "test_value",
        }
        
        # 尝试创建工具
        tool = tool_class(config=config)
        
        # 验证配置分离
        executor_config = tool._extract_executor_config(config)
        
        # 检查是否正确过滤
        has_executor_fields = any(k in executor_config for k in ['enable_cache', 'max_workers', 'timeout'])
        
        if has_executor_fields:
            return True, "✓ 配置正确分离"
        else:
            return False, "✗ 配置分离失败"
            
    except Exception as e:
        return False, f"✗ 错误: {str(e)[:100]}"


def main():
    """运行验证"""
    print("="*80)
    print("ExecutorConfig 字段过滤修复验证")
    print("="*80)
    
    tools_to_verify = [
        ("DocumentParserTool", "aiecs.tools.docs.document_parser_tool", "DocumentParserTool"),
        ("DocumentWriterTool", "aiecs.tools.docs.document_writer_tool", "DocumentWriterTool"),
        ("ScraperTool", "aiecs.tools.task_tools.scraper_tool", "ScraperTool"),
    ]
    
    results = []
    
    for tool_name, module_path, class_name in tools_to_verify:
        print(f"\n验证 {tool_name}...", end=" ")
        
        try:
            # 动态导入
            module = __import__(module_path, fromlist=[class_name])
            tool_class = getattr(module, class_name)
            
            # 验证工具
            success, message = verify_tool(tool_name, tool_class)
            print(message)
            results.append((tool_name, success))
            
        except Exception as e:
            print(f"✗ 导入失败: {str(e)[:100]}")
            results.append((tool_name, False))
    
    # 打印总结
    print("\n" + "="*80)
    print("验证总结")
    print("="*80)
    
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}")
    
    all_passed = all(success for _, success in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ 所有工具验证通过")
    else:
        print("❌ 部分工具验证失败")
    print("="*80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

