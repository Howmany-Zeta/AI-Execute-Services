#!/usr/bin/env python3
"""
测试最小化修复方案：只修复标签，保持原始顺序
"""

def test_minimal_fix():
    """测试最小化修复逻辑"""
    
    print("🧪 最小化修复方案测试")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "测试 1: 不完整标签修复",
            "input": [
                "<thinking>\n推理过程...",
                "```json\n{\"result\": \"success\"}\n```"
            ],
            "expected_fixes": 1,
            "expected_order": [
                "<thinking>\n推理过程...\n</thinking>",
                "```json\n{\"result\": \"success\"}\n```"
            ]
        },
        {
            "name": "测试 2: 保持上下文关系",
            "input": [
                "第一步分析结果",
                "<thinking>\n对第一步的思考",
                "第二步分析结果",
                "<thinking>\n对第二步的思考",
                "最终结论"
            ],
            "expected_fixes": 2,
            "expected_order": [
                "第一步分析结果",
                "<thinking>\n对第一步的思考\n</thinking>",
                "第二步分析结果",
                "<thinking>\n对第二步的思考\n</thinking>",
                "最终结论"
            ]
        },
        {
            "name": "测试 3: 完整标签不修改",
            "input": [
                "<thinking>\n完整的思考\n</thinking>",
                "输出内容"
            ],
            "expected_fixes": 0,
            "expected_order": [
                "<thinking>\n完整的思考\n</thinking>",
                "输出内容"
            ]
        },
        {
            "name": "测试 4: 无标签不修改",
            "input": [
                "# Markdown 标题",
                "## 内容",
                "结论"
            ],
            "expected_fixes": 0,
            "expected_order": [
                "# Markdown 标题",
                "## 内容",
                "结论"
            ]
        },
        {
            "name": "测试 5: 混合场景",
            "input": [
                "问题描述",
                "<thinking>\n步骤1思考",
                "步骤1结果",
                "<thinking>\n步骤2思考\n</thinking>",  # 完整标签
                "步骤2结果",
                "<thinking>\n步骤3思考",  # 不完整
                "最终答案"
            ],
            "expected_fixes": 2,  # 只修复 part 2 和 part 6
            "expected_order": [
                "问题描述",
                "<thinking>\n步骤1思考\n</thinking>",
                "步骤1结果",
                "<thinking>\n步骤2思考\n</thinking>",
                "步骤2结果",
                "<thinking>\n步骤3思考\n</thinking>",
                "最终答案"
            ]
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print("-" * 60)
        
        text_parts = test_case['input']
        expected_fixes = test_case['expected_fixes']
        expected_order = test_case['expected_order']
        
        # 应用最小化修复逻辑
        processed_parts = []
        fixed_count = 0
        
        for i, part in enumerate(text_parts):
            if '<thinking>' in part and '</thinking>' not in part:
                # 不完整标签：补全结束标签
                part = part + '\n</thinking>'
                fixed_count += 1
                print(f"  Part {i+1}: Incomplete <thinking> tag fixed")
            
            processed_parts.append(part)
        
        # 按原始顺序合并
        content = "\n".join(processed_parts)
        
        # 验证
        fixes_correct = fixed_count == expected_fixes
        order_correct = processed_parts == expected_order
        
        print(f"\n  修复数量: {fixed_count} (期望: {expected_fixes}) {'✅' if fixes_correct else '❌'}")
        print(f"  顺序保持: {'✅' if order_correct else '❌'}")
        
        if not order_correct:
            print(f"\n  期望顺序:")
            for i, part in enumerate(expected_order, 1):
                print(f"    {i}. {part[:50]}...")
            print(f"\n  实际顺序:")
            for i, part in enumerate(processed_parts, 1):
                print(f"    {i}. {part[:50]}...")
        
        # 验证标签平衡
        opening_count = content.count('<thinking>')
        closing_count = content.count('</thinking>')
        tags_balanced = opening_count == closing_count
        
        print(f"  标签平衡: {opening_count} 开始, {closing_count} 结束 {'✅' if tags_balanced else '❌'}")
        
        test_passed = fixes_correct and order_correct and tags_balanced
        results.append((test_case['name'], test_passed))
        
        print(f"\n  结果: {'✅ 通过' if test_passed else '❌ 失败'}")
    
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
        print("\n🎉 所有测试通过！最小化修复方案工作正常。")
        print("\n关键特性:")
        print("  ✅ 只修复不完整的 <thinking> 标签")
        print("  ✅ 保持 Vertex AI 返回的原始顺序")
        print("  ✅ 保持 thinking 和 output 的上下文关系")
        print("  ✅ 不做任何内容重组")
        print("  ✅ 让下游代码自由处理语义")
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试。")

if __name__ == "__main__":
    test_minimal_fix()

