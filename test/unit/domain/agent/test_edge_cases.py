#!/usr/bin/env python3
"""
测试边缘情况：复杂的 multi-part 混合场景
包括各种格式交替、thinking 标签穿插等
"""

def apply_minimal_fix(text_parts):
    """应用最小化修复逻辑"""
    processed_parts = []
    fixed_count = 0
    
    for i, part in enumerate(text_parts):
        if '<thinking>' in part and '</thinking>' not in part:
            # 不完整标签：补全结束标签
            part = part + '\n</thinking>'
            fixed_count += 1
        
        processed_parts.append(part)
    
    # 按原始顺序合并
    content = "\n".join(processed_parts)
    
    return content, fixed_count, processed_parts

def verify_result(processed_parts, expected_parts, content):
    """验证结果"""
    # 检查顺序
    order_correct = processed_parts == expected_parts
    
    # 检查标签平衡
    opening_count = content.count('<thinking>')
    closing_count = content.count('</thinking>')
    tags_balanced = opening_count == closing_count
    
    # 检查每个不完整标签都被修复
    all_fixed = all(
        '</thinking>' in part if '<thinking>' in part else True
        for part in processed_parts
    )
    
    return {
        'order_correct': order_correct,
        'tags_balanced': tags_balanced,
        'all_fixed': all_fixed,
        'opening_count': opening_count,
        'closing_count': closing_count
    }

def test_complex_mixed_formats():
    """测试复杂的混合格式场景"""
    
    print("🧪 边缘情况测试：复杂混合格式")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "测试 1: JSON + Markdown + Thinking 交替",
            "description": "不同格式和 thinking 标签穿插",
            "input": [
                '{"status": "start"}',  # Part 1: JSON, 无 thinking
                '# 分析步骤\n<thinking>\n步骤1的思考',  # Part 2: Markdown + 不完整 thinking
                '## 结果\n数据分析完成',  # Part 3: Markdown, 无 thinking
                '{"data": [1,2,3]}\n<thinking>\n步骤2的思考',  # Part 4: JSON + 不完整 thinking
                '# 总结\n最终结论',  # Part 5: Markdown, 无 thinking
            ],
            "expected_fixes": 2,  # Part 2 和 Part 4
        },
        
        {
            "name": "测试 2: 完整和不完整标签混合",
            "description": "有些标签完整，有些不完整",
            "input": [
                '<thinking>\n完整的思考1\n</thinking>',  # 完整
                'JSON: {"key": "value"}',  # 无标签
                '<thinking>\n不完整的思考2',  # 不完整
                '# Markdown\n内容',  # 无标签
                '<thinking>\n完整的思考3\n</thinking>',  # 完整
                '<thinking>\n不完整的思考4',  # 不完整
            ],
            "expected_fixes": 2,  # Part 3 和 Part 6
        },
        
        {
            "name": "测试 3: Markdown 和 JSON 混合内容",
            "description": "单个 part 包含多种格式",
            "input": [
                '# 标题\n```json\n{"data": 1}\n```\n说明文字',  # Markdown + JSON code block
                '<thinking>\n对上述内容的思考',  # 不完整 thinking
                '## 分析\n```python\ncode\n```\n<thinking>\n代码分析',  # Markdown + code + 不完整 thinking
                '最终结论\n```json\n{"result": "done"}\n```',  # Markdown + JSON
            ],
            "expected_fixes": 2,  # Part 2 和 Part 3
        },
        
        {
            "name": "测试 4: 连续多个不完整 thinking",
            "description": "多个连续的不完整 thinking 标签",
            "input": [
                '<thinking>\n思考1',
                '<thinking>\n思考2',
                '<thinking>\n思考3',
                '普通内容',
                '<thinking>\n思考4',
                '<thinking>\n思考5',
            ],
            "expected_fixes": 5,  # 5个不完整标签
        },
        
        {
            "name": "测试 5: 所有格式混合 + 随机 thinking",
            "description": "最复杂的场景",
            "input": [
                '{"start": true}',  # JSON
                '# 步骤1\n<thinking>\n分析JSON',  # Markdown + 不完整 thinking
                '```python\ndef func():\n    pass\n```',  # 代码块
                '<thinking>\n代码审查\n</thinking>',  # 完整 thinking
                '## 结果\n- 项目1\n- 项目2',  # Markdown list
                '{"intermediate": {"data": [1,2,3]}}\n<thinking>\n数据验证',  # JSON + 不完整 thinking
                '# 总结\n```json\n{"final": "result"}\n```',  # Markdown + JSON
                '<thinking>\n最终思考',  # 不完整 thinking
                '完成',  # 普通文本
            ],
            "expected_fixes": 3,  # Part 2, 6, 8
        },
        
        {
            "name": "测试 6: 空内容和特殊字符",
            "description": "包含空字符串、特殊字符等",
            "input": [
                '',  # 空字符串
                '<thinking>\n思考内容 with special chars: <>&"\'',  # 特殊字符
                '{"key": "value with <tag>"}',  # JSON 中的类标签字符
                '<thinking>\n多行\n思考\n内容',  # 多行不完整 thinking
                '# Title with <angle> brackets',  # 标题中的特殊字符
            ],
            "expected_fixes": 2,  # Part 2 和 Part 4
        },
        
        {
            "name": "测试 7: 超长 Part 混合",
            "description": "包含很长的内容",
            "input": [
                '# 长标题\n' + 'A' * 1000 + '\n## 子标题',  # 超长 Markdown
                '<thinking>\n超长思考内容\n' + 'B' * 2000,  # 超长不完整 thinking
                '```json\n' + '{"data": "' + 'C' * 500 + '"}\n```',  # 超长 JSON
                '<thinking>\n简短思考\n</thinking>',  # 完整 thinking
            ],
            "expected_fixes": 1,  # Part 2
        },
        
        {
            "name": "测试 8: 嵌套结构",
            "description": "复杂的嵌套内容",
            "input": [
                '```json\n{\n  "nested": {\n    "deep": {\n      "value": "<not a tag>"\n    }\n  }\n}\n```',
                '<thinking>\n分析嵌套结构\n- Level 1\n  - Level 2\n    - Level 3',
                '# 外层\n## 内层\n### 更深层\n```python\nif True:\n    if True:\n        pass\n```',
                '<thinking>\n嵌套思考\n  缩进内容\n    更深缩进',
            ],
            "expected_fixes": 2,  # Part 2 和 Part 4
        },
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print("-" * 60)
        print(f"描述: {test_case['description']}")
        print(f"\n输入 Parts: {len(test_case['input'])} 个")
        
        for i, part in enumerate(test_case['input'], 1):
            preview = part[:60].replace('\n', '\\n')
            has_thinking = '<thinking>' in part
            is_complete = '</thinking>' in part if has_thinking else None
            status = ""
            if has_thinking:
                status = " [完整thinking]" if is_complete else " [不完整thinking]"
            print(f"  Part {i}: {preview}...{status}")
        
        # 应用修复
        content, fixed_count, processed_parts = apply_minimal_fix(test_case['input'])
        
        # 生成期望结果
        expected_parts = []
        for part in test_case['input']:
            if '<thinking>' in part and '</thinking>' not in part:
                part = part + '\n</thinking>'
            expected_parts.append(part)
        
        # 验证
        verification = verify_result(processed_parts, expected_parts, content)
        
        print(f"\n结果:")
        print(f"  修复数量: {fixed_count} (期望: {test_case['expected_fixes']}) {'✅' if fixed_count == test_case['expected_fixes'] else '❌'}")
        print(f"  顺序保持: {'✅' if verification['order_correct'] else '❌'}")
        print(f"  标签平衡: {verification['opening_count']} 开始, {verification['closing_count']} 结束 {'✅' if verification['tags_balanced'] else '❌'}")
        print(f"  全部修复: {'✅' if verification['all_fixed'] else '❌'}")
        
        # 显示修复后的预览
        if fixed_count > 0:
            print(f"\n修复后内容预览 (前200字符):")
            preview = content[:200].replace('\n', '\\n')
            print(f"  {preview}...")
        
        test_passed = (
            fixed_count == test_case['expected_fixes'] and
            verification['order_correct'] and
            verification['tags_balanced'] and
            verification['all_fixed']
        )
        
        print(f"\n测试结果: {'✅ 通过' if test_passed else '❌ 失败'}")
        results.append((test_case['name'], test_passed))
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\n总计: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("\n🎉 所有边缘情况测试通过！")
        print("\n验证的边缘情况:")
        print("  ✅ JSON + Markdown + Thinking 交替")
        print("  ✅ 完整和不完整标签混合")
        print("  ✅ Markdown 和 JSON 混合内容")
        print("  ✅ 连续多个不完整 thinking")
        print("  ✅ 所有格式随机混合")
        print("  ✅ 空内容和特殊字符")
        print("  ✅ 超长内容")
        print("  ✅ 嵌套结构")
        print("\n关键特性:")
        print("  ✅ 正确识别所有不完整的 <thinking> 标签")
        print("  ✅ 保持原始顺序，不重组")
        print("  ✅ 支持各种格式混合")
        print("  ✅ 处理特殊字符和边界情况")
        print("  ✅ 标签平衡且完整")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试。")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = test_complex_mixed_formats()
    exit(0 if success else 1)

