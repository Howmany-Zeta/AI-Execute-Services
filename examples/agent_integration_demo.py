"""
演示 Langchain ReAct Agent 如何实际使用 Chart Tool
"""

from aiecs.tools.langchain_adapter import get_langchain_tools

def show_actual_integration():
    """展示实际的集成代码"""
    
    print("=== 实际集成代码 ===")
    
    integration_code = '''
# 1. 获取转换后的工具（这一步自动生成工具描述）
from aiecs.tools.langchain_adapter import get_langchain_tools

tools = get_langchain_tools(['chart'])  # 获取chart工具的所有子功能

# 2. 创建ReAct Agent（Langchain自动注入工具信息到prompt）
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

llm = ChatOpenAI(model="gpt-3.5-turbo")

# 标准ReAct prompt - 注意 {tools} 和 {tool_names} 占位符
prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer  
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")

# 创建agent（Langchain自动将工具信息注入prompt）
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 3. 使用Agent
result = agent_executor.invoke({"input": "分析文件 /data/sales.csv 并创建趋势图"})
'''
    
    print(integration_code)

def show_automatic_prompt_injection():
    """展示自动prompt注入机制"""
    
    print("\n=== Langchain 自动 Prompt 注入机制 ===")
    
    # 模拟工具转换后的信息
    print("1️⃣ 工具转换后，每个工具对象包含:")
    print("""
    chart_read_data:
      ├── name: "chart_read_data"  
      ├── description: "Read and analyze data files in multiple formats..."
      └── args_schema: ReadDataSchema (包含所有参数定义)
    
    chart_visualize:
      ├── name: "chart_visualize"
      ├── description: "Create data visualizations including histograms..." 
      └── args_schema: VisualizationSchema
    
    chart_export_data:
      ├── name: "chart_export_data"
      ├── description: "Export data to various formats..."
      └── args_schema: ExportDataSchema
    """)
    
    print("\n2️⃣ Langchain 自动将这些信息注入 {tools} 占位符:")
    print("""
    {tools} 被替换为:
    chart_read_data: Read and analyze data files in multiple formats (CSV, Excel, JSON, Parquet, etc.). Returns data structure summary, preview, and optional export functionality. Required: file_path. Optional: nrows, sheet_name, export_format, export_path.
    chart_visualize: Create data visualizations including histograms, scatter plots, bar charts, line charts, heatmaps, and pair plots. Supports customizable styling, colors, and high-resolution output. Required: file_path, plot_type. Optional: x, y, hue, variables, title, figsize, output_path, dpi, export_format, export_path.
    chart_export_data: Export data to various formats (JSON, CSV, HTML, Excel, Markdown) with optional variable selection and path customization. Required: file_path, format. Optional: variables, export_path, export_format.
    """)
    
    print("\n3️⃣ {tool_names} 被替换为:")
    print("    [chart_read_data, chart_visualize, chart_export_data]")

def show_comparison():
    """对比不同的方法"""
    
    print("\n=== 方法对比 ===")
    
    print("❌ 错误方法 - 手动维护:")
    print("""
    # 在 prompt.yaml 中手动列举
    prompt: |
      你可以使用以下工具:
      - chart_read_data: 读取数据文件...
      - chart_visualize: 创建图表...
      
    问题: 
    ❌ 需要手动同步工具变更
    ❌ 容易出现信息不一致
    ❌ 维护成本高
    """)
    
    print("✅ 正确方法 - 自动化:")
    print("""
    # 代码中自动获取工具
    tools = get_langchain_tools(['chart'])
    agent = create_react_agent(llm, tools, standard_react_prompt)
    
    优势:
    ✅ 工具信息自动同步
    ✅ 描述自动生成并注入
    ✅ 参数schema自动验证
    ✅ 零维护成本
    """)

def main():
    show_actual_integration()
    show_automatic_prompt_injection()
    show_comparison()
    
    print("\n" + "="*80)
    print("💡 关键结论")
    print("="*80)
    print("""
1. 📚 文档作用: 
   - 供开发者学习和参考
   - 不直接用于Agent

2. 🤖 Agent工作原理:
   - 通过工具对象的 name、description、args_schema 获取信息
   - Langchain自动将这些信息注入到 {tools} 和 {tool_names} 占位符
   - Agent根据注入的信息决定何时使用哪个工具

3. 🔧 集成方式:
   - 只需要: tools = get_langchain_tools(['chart'])
   - 然后传递给 create_react_agent(llm, tools, prompt)
   - 其他都是自动化的！

4. ✨ 优势:
   - 工具变更自动反映到Agent
   - 无需手动维护prompt配置
   - 完整保持BaseTool所有特性
""")

if __name__ == "__main__":
    main()
