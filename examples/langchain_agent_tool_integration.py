"""
Langchain ReAct Agent 工具集成实际示例

展示Agent如何通过工具元数据（而非外部文档）来了解和使用工具
"""

import os
import json
from typing import List

def demonstrate_tool_metadata():
    """演示工具元数据如何传递给Agent"""
    
    print("=== Langchain ReAct Agent 工具使用机制 ===\n")
    
    # 模拟导入（如果langchain可用）
    try:
        from aiecs.tools.langchain_adapter import get_langchain_tools, tool_registry
        
        # 1. 获取chart工具的Langchain适配器
        print("1. 获取chart工具的Langchain适配器...")
        chart_tools = tool_registry.create_langchain_tools('chart')
        
        print(f"Chart工具被转换为 {len(chart_tools)} 个独立的Langchain工具:\n")
        
        for tool in chart_tools:
            print(f"🔧 工具名称: {tool.name}")
            print(f"📝 描述: {tool.description}")
            
            # 显示参数schema（这是Agent了解参数的方式）
            if hasattr(tool, 'args_schema') and tool.args_schema:
                schema = tool.args_schema
                print(f"📋 参数Schema: {schema.__name__}")
                
                # 显示具体参数
                if hasattr(schema, '__fields__'):
                    fields = schema.__fields__
                    print("   必需参数:")
                    required_fields = [name for name, field in fields.items() if field.is_required()]
                    for field_name in required_fields:
                        field_info = fields[field_name]
                        print(f"     - {field_name}: {field_info.annotation}")
                    
                    print("   可选参数:")
                    optional_fields = [name for name, field in fields.items() if not field.is_required()]
                    for field_name in optional_fields:
                        field_info = fields[field_name]
                        default = getattr(field_info, 'default', None)
                        print(f"     - {field_name}: {field_info.annotation} (default: {default})")
            
            print("─" * 50)
        
        # 2. 演示Agent如何看到工具信息
        print("\n2. Agent在prompt中看到的工具信息:")
        print("```")
        for tool in chart_tools[:2]:  # 只显示前两个避免输出过长
            print(f"{tool.name}: {tool.description}")
        print("```")
        
        # 3. 演示Prompt构建
        demonstrate_prompt_construction(chart_tools)
        
    except Exception as e:
        print(f"演示失败: {e}")
        print("请确保已正确安装langchain和相关依赖")

def demonstrate_prompt_construction(tools: List):
    """演示ReAct Agent的Prompt构建过程"""
    
    print("\n3. ReAct Agent Prompt 构建过程:")
    print("─" * 60)
    
    # 模拟Langchain ReAct Agent如何构建prompt
    tool_descriptions = []
    tool_names = []
    
    for tool in tools[:3]:  # 限制数量避免输出过长
        tool_descriptions.append(f"{tool.name}: {tool.description}")
        tool_names.append(tool.name)
    
    # 这就是Agent实际看到的prompt内容
    react_prompt = f"""
Answer the following questions as best you can. You have access to the following tools:

{chr(10).join(tool_descriptions)}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{', '.join(tool_names)}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {{input}}
Thought: {{agent_scratchpad}}
"""
    
    print("实际的ReAct Prompt模板:")
    print("```")
    print(react_prompt)
    print("```")
    
    print("\n📋 关键点:")
    print("- Agent通过工具的 name 和 description 了解功能")
    print("- Agent通过 args_schema 了解需要什么参数") 
    print("- 工具描述会自动注入到prompt的 {tools} 部分")
    print("- 工具名称列表会注入到 {tool_names} 部分")

def demonstrate_actual_usage():
    """演示实际的Agent使用流程"""
    
    print("\n4. 实际Agent调用示例:")
    print("─" * 60)
    
    # 模拟用户查询
    user_query = "分析文件 /data/sales.csv 并创建销售趋势图"
    
    print(f"👤 用户查询: {user_query}")
    print("\n🤖 Agent 思考过程:")
    
    print("""
Thought: 用户想要分析CSV文件并创建趋势图，我需要先读取数据了解结构，然后创建可视化。

Action: chart_read_data
Action Input: {"file_path": "/data/sales.csv"}

Observation: {
    "variables": ["date", "product", "sales", "region"],
    "observations": 1000,
    "dtypes": {"date": "object", "product": "object", "sales": "int64", "region": "object"},
    "preview": [...]
}

Thought: 数据已读取，包含日期、产品、销售额等字段。现在创建销售趋势图。

Action: chart_visualize
Action Input: {
    "file_path": "/data/sales.csv",
    "plot_type": "line", 
    "x": "date",
    "y": "sales",
    "title": "销售趋势图"
}

Observation: {
    "plot_type": "line",
    "output_path": "/tmp/chart_exports/sales_trend.png",
    "title": "销售趋势图"
}

Thought: 趋势图已创建完成。

Final Answer: 我已为你分析了销售数据文件，包含1000条记录，并创建了销售趋势图。图表保存在 /tmp/chart_exports/sales_trend.png，显示了销售额随时间的变化趋势。
""")

def explain_documentation_role():
    """解释文档的实际作用"""
    
    print("\n5. 文档的实际作用:")
    print("─" * 60)
    
    print("📚 创建的文档 (chart_tool_langchain_guide.md) 的作用:")
    print("  ✅ 供开发者参考 - 了解如何配置和使用工具")
    print("  ✅ 集成指南 - 展示最佳实践和使用模式")
    print("  ✅ 故障排除 - 提供常见问题的解决方案")
    print("  ✅ API参考 - 详细的参数说明和示例")
    
    print("\n🤖 Agent获取工具信息的实际方式:")
    print("  ➡️ tool.name - 工具名称")
    print("  ➡️ tool.description - 功能描述（自动注入prompt）")
    print("  ➡️ tool.args_schema - 参数结构（指导Action Input格式）")
    print("  ➡️ tool._run() - 实际执行逻辑")
    
    print("\n🔄 信息流转过程:")
    print("  1️⃣ BaseTool.method → LangchainToolAdapter")
    print("  2️⃣ 适配器提取name、description、args_schema")
    print("  3️⃣ Langchain将这些信息注入ReAct prompt")
    print("  4️⃣ Agent基于prompt中的信息决定使用哪个工具")
    print("  5️⃣ Agent根据args_schema构造Action Input")

def show_prompt_injection_example():
    """展示实际的prompt注入示例"""
    
    print("\n6. Agent Prompt 自动注入示例:")
    print("─" * 60)
    
    # 模拟工具描述如何注入prompt
    mock_tool_descriptions = [
        "chart_read_data: Read and analyze data files in multiple formats (CSV, Excel, JSON, Parquet, etc.). Returns data structure summary, preview, and optional export functionality. Required: file_path. Optional: nrows, sheet_name, export_format, export_path.",
        "chart_visualize: Create data visualizations including histograms, scatter plots, bar charts, line charts, heatmaps, and pair plots. Supports customizable styling, colors, and high-resolution output. Required: file_path, plot_type. Optional: x, y, hue, variables, title, figsize, output_path, dpi, export_format, export_path.",
        "chart_export_data: Export data to various formats (JSON, CSV, HTML, Excel, Markdown) with optional variable selection and path customization. Required: file_path, format. Optional: variables, export_path, export_format."
    ]
    
    print("实际注入到Agent prompt的工具信息:")
    print("```")
    for desc in mock_tool_descriptions:
        print(desc)
    print("```")
    
    print("\n💡 关键理解:")
    print("- Agent通过这些描述了解每个工具的能力")
    print("- 'Required' 和 'Optional' 参数信息指导Agent构造输入")
    print("- Agent根据用户查询匹配最合适的工具")
    print("- 无需在prompt.yaml中手动列举工具内容")

def main():
    """主演示函数"""
    
    # 运行所有演示
    demonstrate_tool_metadata()
    demonstrate_actual_usage()
    explain_documentation_role()
    show_prompt_injection_example()
    
    print("\n" + "=" * 80)
    print("总结: Langchain ReAct Agent 工具使用机制")
    print("=" * 80)
    
    print("""
🎯 核心机制:
  - Agent通过工具对象的元数据(name, description, args_schema)了解工具功能
  - 这些信息由适配器自动提供，无需手动配置
  - 文档仅供开发者参考，不直接用于Agent

📝 集成步骤:
  1. 使用适配器: from aiecs.tools.langchain_adapter import get_langchain_tools
  2. 获取工具: tools = get_langchain_tools(['chart'])
  3. 创建Agent: agent = create_react_agent(llm, tools, prompt)
  4. Agent自动获取工具信息并注入prompt

✨ 优势:
  - 自动化工具发现和描述生成
  - 保持所有BaseTool原有功能特性
  - 无需手动维护prompt中的工具列表
  - 支持动态工具添加和更新
""")

if __name__ == "__main__":
    main()
