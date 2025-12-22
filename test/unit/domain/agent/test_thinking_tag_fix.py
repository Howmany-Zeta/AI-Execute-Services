#!/usr/bin/env python3
"""
测试 thinking 标签修复逻辑
模拟 Vertex AI 返回不完整的 <thinking> 标签的情况
"""

import re

def test_incomplete_thinking_tag_fix():
    """
    测试不完整的 <thinking> 标签修复逻辑
    """
    
    # 模拟 Vertex AI 返回的 multi-part response
    # Part 1: 包含 <thinking> 开始标签但没有结束标签
    part1 = """<thinking>
1. **Deconstruct the Goal:** The goal is to generate an executable workflow plan...
2. **Analyze Input JSON:** The input contains detailed subtask information...
3. **Identify Dependencies:** Building a comprehensive dependency map...
4. **Final Review:** The plan looks good."""

    # Part 2: 包含实际的 JSON 输出
    part2 = """```json
{
  "plan_status": "SUCCESS",
  "plan_dsl": [
    {
      "task_name": "example_task",
      "agent": "example_agent"
    }
  ]
}
```"""

    text_parts = [part1, part2]
    
    print("🔍 测试不完整 <thinking> 标签修复")
    print("=" * 80)
    print(f"\n输入:")
    print(f"  Part 1 长度: {len(part1)} 字符")
    print(f"  Part 1 包含 <thinking>: {'<thinking>' in part1}")
    print(f"  Part 1 包含 </thinking>: {'</thinking>' in part1}")
    print(f"  Part 2 长度: {len(part2)} 字符")
    
    # 应用修复逻辑
    first_part = text_parts[0]
    has_thinking_tags = '<thinking>' in first_part
    
    if has_thinking_tags:
        thinking_contents = []
        actual_outputs = []
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part:
                if '</thinking>' in part:
                    # Complete thinking tags in this part
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                    if thinking_match:
                        thinking_contents.append(thinking_match.group(1).strip())
                        
                    # Extract content after </thinking>
                    after_thinking = part[thinking_match.end():].strip()
                    if after_thinking:
                        actual_outputs.append(after_thinking)
                else:
                    # Incomplete thinking tag (only opening tag)
                    # Extract content after <thinking>
                    thinking_start = part.find('<thinking>')
                    thinking_content = part[thinking_start + len('<thinking>'):].strip()
                    if thinking_content:
                        thinking_contents.append(thinking_content)
                    print(f"  ✅ Part {i+1}: Incomplete <thinking> tag detected, extracted {len(thinking_content)} chars")
            else:
                # This part doesn't have thinking tags, treat as actual output
                actual_outputs.append(part)
        
        # Combine thinking content and actual outputs
        if thinking_contents:
            combined_thinking = '\n\n'.join(thinking_contents)
            content = f"<thinking>\n{combined_thinking}\n</thinking>"
            if actual_outputs:
                content += "\n" + "\n".join(actual_outputs)
        else:
            content = "\n".join(text_parts)
        
        print(f"\n修复结果:")
        print(f"  Thinking 内容数量: {len(thinking_contents)}")
        print(f"  实际输出数量: {len(actual_outputs)}")
        print(f"  合并后总长度: {len(content)} 字符")
        
        # 验证修复后的内容
        has_opening = '<thinking>' in content
        has_closing = '</thinking>' in content
        opening_count = content.count('<thinking>')
        closing_count = content.count('</thinking>')
        
        print(f"\n验证:")
        print(f"  包含 <thinking>: {has_opening}")
        print(f"  包含 </thinking>: {has_closing}")
        print(f"  <thinking> 数量: {opening_count}")
        print(f"  </thinking> 数量: {closing_count}")
        print(f"  标签平衡: {'✅' if opening_count == closing_count else '❌'}")
        
        # 显示修复后的内容预览
        print(f"\n修复后内容预览:")
        print("-" * 80)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 80)
        
        return content, opening_count == closing_count
    
    return None, False

def test_complete_thinking_tag():
    """
    测试完整的 <thinking> 标签（不需要修复）
    """
    
    # 模拟包含完整标签的响应
    part1 = """<thinking>
This is complete thinking content.
</thinking>"""

    part2 = """```json
{"status": "success"}
```"""

    text_parts = [part1, part2]
    
    print("\n\n🔍 测试完整 <thinking> 标签")
    print("=" * 80)
    print(f"\n输入:")
    print(f"  Part 1 包含 <thinking>: {'<thinking>' in part1}")
    print(f"  Part 1 包含 </thinking>: {'</thinking>' in part1}")
    
    # 应用修复逻辑
    first_part = text_parts[0]
    has_thinking_tags = '<thinking>' in first_part
    
    if has_thinking_tags:
        thinking_contents = []
        actual_outputs = []
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part:
                if '</thinking>' in part:
                    # Complete thinking tags in this part
                    thinking_match = re.search(r'<thinking>(.*?)</thinking>', part, re.DOTALL)
                    if thinking_match:
                        thinking_contents.append(thinking_match.group(1).strip())
                        
                    # Extract content after </thinking>
                    after_thinking = part[thinking_match.end():].strip()
                    if after_thinking:
                        actual_outputs.append(after_thinking)
                    print(f"  ✅ Part {i+1}: Complete <thinking> tags found")
                else:
                    # Incomplete thinking tag (only opening tag)
                    thinking_start = part.find('<thinking>')
                    thinking_content = part[thinking_start + len('<thinking>'):].strip()
                    if thinking_content:
                        thinking_contents.append(thinking_content)
                    print(f"  ⚠️ Part {i+1}: Incomplete <thinking> tag detected")
            else:
                # This part doesn't have thinking tags, treat as actual output
                actual_outputs.append(part)
        
        # Combine thinking content and actual outputs
        if thinking_contents:
            combined_thinking = '\n\n'.join(thinking_contents)
            content = f"<thinking>\n{combined_thinking}\n</thinking>"
            if actual_outputs:
                content += "\n" + "\n".join(actual_outputs)
        else:
            content = "\n".join(text_parts)
        
        print(f"\n处理结果:")
        print(f"  Thinking 内容数量: {len(thinking_contents)}")
        print(f"  实际输出数量: {len(actual_outputs)}")
        
        # 验证
        opening_count = content.count('<thinking>')
        closing_count = content.count('</thinking>')
        print(f"  标签平衡: {'✅' if opening_count == closing_count else '❌'}")
        
        return content, opening_count == closing_count
    
    return None, False

def main():
    """
    主测试函数
    """
    print("🧪 Thinking 标签修复逻辑测试")
    print("=" * 80)
    
    # 测试 1: 不完整的标签
    content1, balanced1 = test_incomplete_thinking_tag_fix()
    
    # 测试 2: 完整的标签
    content2, balanced2 = test_complete_thinking_tag()
    
    # 总结
    print("\n\n📊 测试总结")
    print("=" * 80)
    print(f"测试 1 (不完整标签): {'✅ 通过' if balanced1 else '❌ 失败'}")
    print(f"测试 2 (完整标签): {'✅ 通过' if balanced2 else '❌ 失败'}")
    
    if balanced1 and balanced2:
        print("\n🎉 所有测试通过！修复逻辑工作正常。")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试。")

if __name__ == "__main__":
    main()

