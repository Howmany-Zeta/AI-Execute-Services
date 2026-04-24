# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
简单演示：Langchain ReAct Agent 自动获取工具信息
证明无需手动配置，工具适配器自动提供所有必要信息
"""

def demo_automatic_tool_discovery():
    """演示自动工具发现机制"""
    
    print("=== 自动工具发现演示 ===\n")
    
    try:
        from aiecs.tools.langchain_adapter import get_langchain_tools
        
        # 🎯 关键：只需要这一行代码！
        tools = get_langchain_tools(['chart'])
        
        print(f"📦 自动发现的工具数量: {len(tools)}")
        print("\n🔧 每个工具自动包含的信息:")
        
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   📝 自动描述: {tool.description}")
            
            # 参数Schema信息（Agent用来构造Action Input）
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    schema_fields = tool.args_schema.__annotations__
                    print(f"   📋 参数Schema: {list(schema_fields.keys())}")
                except:
                    print(f"   📋 参数Schema: {tool.args_schema.__name__}")
        
        print(f"\n✨ 结果: {len(tools)} 个工具已自动准备好，无需任何手动配置！")
        
        return tools
        
    except Exception as e:
        print(f"演示失败: {e}")
        return []

def show_agent_perspective(tools):
    """展示Agent视角看到的信息"""
    
    if not tools:
        print("没有可用工具，跳过Agent视角演示")
        return
    
    print("\n=== Agent 视角：自动注入的Prompt信息 ===\n")
    
    # 模拟Langchain如何构建tools描述
    tool_descriptions = []
    tool_names = []
    
    for tool in tools:
        tool_descriptions.append(f"{tool.name}: {tool.description}")
        tool_names.append(tool.name)
    
    print("🤖 Agent在prompt中看到的工具列表:")
    print("```")
    for desc in tool_descriptions:
        print(desc)
    print("```")
    
    print(f"\n🎯 可用工具名称: [{', '.join(tool_names)}]")
    
    print("\n📋 关键点:")
    print("  ❌ 无需在 prompt.yaml 中列举这些内容")
    print("  ❌ 无需手动维护工具描述")
    print("  ✅ 适配器自动提供所有信息")
    print("  ✅ Langchain自动注入到 {tools} 占位符")

def compare_approaches():
    """对比手动vs自动方式"""
    
    print("\n=== 方法对比 ===\n")
    
    print("❌ 手动方式（不推荐）:")
    print("""
    # prompt.yaml 或 prompt 字符串中手动写入:
    prompt: |
      你有以下工具可用:
      - chart_read_data: 读取CSV、Excel等格式的数据文件，参数包括file_path(必需)、nrows(可选)...
      - chart_visualize: 创建各种图表，参数包括file_path(必需)、plot_type(必需)...
      - chart_export_data: 导出数据到不同格式...
    
    问题:
    🚫 每次添加新工具都要手动更新prompt
    🚫 参数变更需要同步多个地方
    🚫 容易出现描述不准确或过时
    🚫 维护成本高，容易出错
    """)
    
    print("✅ 自动方式（推荐）:")
    print("""
    # 只需要2行代码:
    tools = get_langchain_tools(['chart'])  # 自动转换所有子功能
    agent = create_react_agent(llm, tools, standard_react_prompt)
    
    优势:
    ✅ 工具信息自动提取和更新
    ✅ 参数Schema自动同步
    ✅ 描述自动生成并保持最新
    ✅ 零维护成本
    ✅ 支持动态工具添加
    ✅ 完全保持BaseTool的所有特性（缓存、安全、性能监控等）
    """)

def main():
    # 运行演示
    tools = demo_automatic_tool_discovery()
    show_agent_perspective(tools)
    compare_approaches()
    
    print("\n" + "="*80)
    print("🎯 最终答案")
    print("="*80)
    print("""
问题: 是否需要手动列出工具使用文档给 Langchain Agent？

答案: ❌ 完全不需要！

原因:
1️⃣ 适配器自动提取工具信息（name, description, args_schema）
2️⃣ Langchain框架自动将这些信息注入ReAct prompt
3️⃣ Agent通过prompt中的信息了解工具功能和参数
4️⃣ 整个过程完全自动化，无需人工干预

集成方式:
    tools = get_langchain_tools(['chart'])  # 一行代码搞定！
    agent = create_react_agent(llm, tools, prompt)

创建的文档作用:
    📚 供开发者学习和集成参考
    🔍 不会直接被Agent读取
    📖 帮助理解工具能力和最佳实践
""")

if __name__ == "__main__":
    main()






