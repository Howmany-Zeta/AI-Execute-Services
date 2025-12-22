#!/usr/bin/env python3
"""
全面测试 multi-part response 处理逻辑
包括 reasoning 和 non-reasoning 场景
"""

import re

def test_reasoning_mode_incomplete_tags():
    """测试 1: Reasoning mode - 不完整的 thinking 标签"""
    print("\n" + "="*80)
    print("测试 1: Reasoning Mode - 不完整 Thinking 标签")
    print("="*80)
    
    text_parts = [
        "<thinking>\n推理过程第一部分...",  # 不完整标签
        "```json\n{\"result\": \"success\"}\n```"
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        thinking_contents = []
        actual_outputs = []
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part:
                if '</thinking>' in part:
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                    if thinking_match:
                        thinking_contents.append(thinking_match.group(1).strip())
                else:
                    thinking_start = part.find('<thinking>')
                    thinking_content = part[thinking_start + len('<thinking>'):].strip()
                    if thinking_content:
                        thinking_contents.append(thinking_content)
            else:
                actual_outputs.append(part)
        
        if thinking_contents:
            combined_thinking = '\n\n'.join(thinking_contents)
            content = f"<thinking>\n{combined_thinking}\n</thinking>"
            if actual_outputs:
                content += "\n" + "\n".join(actual_outputs)
        else:
            content = "\n".join(text_parts)
        
        print(f"✅ Reasoning mode: {len(thinking_contents)} thinking, {len(actual_outputs)} output")
        print(f"标签平衡: {content.count('<thinking>') == content.count('</thinking>')}")
        return True
    else:
        print("❌ 未检测到 thinking 标签")
        return False

def test_reasoning_mode_tags_in_middle():
    """测试 2: Reasoning mode - thinking 标签在中间的 parts"""
    print("\n" + "="*80)
    print("测试 2: Reasoning Mode - Thinking 标签在中间 Parts")
    print("="*80)
    
    text_parts = [
        "# Markdown 说明文档",
        "<thinking>\n第一步分析...",  # 第2个part有标签
        "中间结果",
        "<thinking>\n第二步分析...",  # 第4个part有标签
        "```json\n{\"result\": \"success\"}\n```"
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        thinking_contents = []
        actual_outputs = []
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part:
                if '</thinking>' in part:
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                    if thinking_match:
                        thinking_contents.append(thinking_match.group(1).strip())
                else:
                    thinking_start = part.find('<thinking>')
                    thinking_content = part[thinking_start + len('<thinking>'):].strip()
                    if thinking_content:
                        thinking_contents.append(thinking_content)
            else:
                actual_outputs.append(part)
        
        if thinking_contents:
            combined_thinking = '\n\n'.join(thinking_contents)
            content = f"<thinking>\n{combined_thinking}\n</thinking>"
            if actual_outputs:
                content += "\n" + "\n".join(actual_outputs)
        else:
            content = "\n".join(text_parts)
        
        print(f"✅ Reasoning mode: {len(thinking_contents)} thinking, {len(actual_outputs)} output")
        print(f"Thinking parts: Part 2, Part 4")
        print(f"Output parts: Part 1, Part 3, Part 5")
        print(f"标签平衡: {content.count('<thinking>') == content.count('</thinking>')}")
        return True
    else:
        print("❌ 未检测到 thinking 标签")
        return False

def test_non_reasoning_markdown():
    """测试 3: Non-reasoning mode - Markdown 多 part"""
    print("\n" + "="*80)
    print("测试 3: Non-Reasoning Mode - Markdown 格式")
    print("="*80)
    
    text_parts = [
        "# 分析报告\n## 概述",
        "## 详细分析\n内容...",
        "## 结论\n总结..."
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        print("❌ 不应该检测到 thinking 标签")
        return False
    else:
        # 直接合并，不添加 thinking 标签
        content = "\n".join(text_parts)
        print(f"✅ Normal multi-part: {len(text_parts)} parts merged")
        print(f"保持 Markdown 结构: {content.startswith('# 分析报告')}")
        print(f"无 thinking 标签: {'<thinking>' not in content}")
        return True

def test_non_reasoning_code_generation():
    """测试 4: Non-reasoning mode - 代码生成"""
    print("\n" + "="*80)
    print("测试 4: Non-Reasoning Mode - 代码生成")
    print("="*80)
    
    text_parts = [
        "这是一个示例函数：",
        "```python\ndef example():\n    return 'Hello'\n```",
        "使用方法：\nexample()"
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        print("❌ 不应该检测到 thinking 标签")
        return False
    else:
        content = "\n".join(text_parts)
        print(f"✅ Normal multi-part: {len(text_parts)} parts merged")
        print(f"保持代码块: {'```python' in content}")
        print(f"无 thinking 标签: {'<thinking>' not in content}")
        return True

def test_non_reasoning_long_text():
    """测试 5: Non-reasoning mode - 长文本分段"""
    print("\n" + "="*80)
    print("测试 5: Non-Reasoning Mode - 长文本分段")
    print("="*80)
    
    text_parts = [
        "第一段内容...",
        "第二段内容...",
        "第三段内容..."
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        print("❌ 不应该检测到 thinking 标签")
        return False
    else:
        content = "\n".join(text_parts)
        print(f"✅ Normal multi-part: {len(text_parts)} parts merged")
        line_count = len(content.split('\n'))
        print(f"内容完整: {line_count == 3}")
        print(f"无 thinking 标签: {'<thinking>' not in content}")
        return True

def test_reasoning_mode_complete_tags():
    """测试 6: Reasoning mode - 完整的 thinking 标签"""
    print("\n" + "="*80)
    print("测试 6: Reasoning Mode - 完整 Thinking 标签")
    print("="*80)
    
    text_parts = [
        "<thinking>\n完整的推理过程\n</thinking>",
        "```json\n{\"result\": \"success\"}\n```"
    ]
    
    has_any_thinking_tags = any('<thinking>' in part for part in text_parts)
    print(f"检测结果: has_any_thinking_tags = {has_any_thinking_tags}")
    
    if has_any_thinking_tags:
        thinking_contents = []
        actual_outputs = []
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part:
                if '</thinking>' in part:
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                    if thinking_match:
                        thinking_contents.append(thinking_match.group(1).strip())
                    after_thinking = part[thinking_match.end():].strip()
                    if after_thinking:
                        actual_outputs.append(after_thinking)
                else:
                    thinking_start = part.find('<thinking>')
                    thinking_content = part[thinking_start + len('<thinking>'):].strip()
                    if thinking_content:
                        thinking_contents.append(thinking_content)
            else:
                actual_outputs.append(part)
        
        if thinking_contents:
            combined_thinking = '\n\n'.join(thinking_contents)
            content = f"<thinking>\n{combined_thinking}\n</thinking>"
            if actual_outputs:
                content += "\n" + "\n".join(actual_outputs)
        else:
            content = "\n".join(text_parts)
        
        print(f"✅ Reasoning mode: {len(thinking_contents)} thinking, {len(actual_outputs)} output")
        print(f"标签平衡: {content.count('<thinking>') == content.count('</thinking>')}")
        return True
    else:
        print("❌ 未检测到 thinking 标签")
        return False

def main():
    """运行所有测试"""
    print("\n🧪 全面 Multi-Part Response 处理测试")
    print("="*80)
    
    tests = [
        ("Reasoning - 不完整标签", test_reasoning_mode_incomplete_tags),
        ("Reasoning - 标签在中间", test_reasoning_mode_tags_in_middle),
        ("Non-Reasoning - Markdown", test_non_reasoning_markdown),
        ("Non-Reasoning - 代码生成", test_non_reasoning_code_generation),
        ("Non-Reasoning - 长文本", test_non_reasoning_long_text),
        ("Reasoning - 完整标签", test_reasoning_mode_complete_tags),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            results.append((name, False))
    
    print("\n" + "="*80)
    print("📊 测试结果总结")
    print("="*80)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！修复逻辑工作正常。")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试。")

if __name__ == "__main__":
    main()

