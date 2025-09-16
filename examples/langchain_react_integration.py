"""
Langchain ReAct Agent 集成示例

展示如何使用 BaseTool 适配器创建完整的 ReAct Agent
支持所有 BaseTool 的功能特性，包括缓存、安全、异步等
"""

import asyncio
import logging
from typing import List, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_dependencies():
    """检查必要的依赖包"""
    try:
        import langchain
        from langchain.agents import create_react_agent, AgentExecutor
        from langchain.prompts import PromptTemplate
        from langchain_openai import ChatOpenAI
        return True
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Please install: pip install langchain langchain-openai")
        return False

if check_dependencies():
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI
    
    # 导入我们的适配器
    from aiecs.tools.langchain_adapter import (
        get_langchain_tools, 
        create_react_agent_tools,
        check_langchain_compatibility
    )

    class BasetoolReactAgent:
        """
        集成了 BaseTool 的 ReAct Agent
        
        特性：
        - 自动发现并转换所有 BaseTool 及其子功能
        - 保持原有的缓存、安全、性能监控等特性
        - 支持同步和异步执行
        - 灵活的工具选择和配置
        """
        
        def __init__(
            self, 
            llm_model: str = "gpt-3.5-turbo",
            tool_names: Optional[List[str]] = None,
            openai_api_key: Optional[str] = None
        ):
            """
            初始化 ReAct Agent
            
            Args:
                llm_model: 使用的LLM模型
                tool_names: 指定要使用的工具名称列表，None表示使用所有工具
                openai_api_key: OpenAI API密钥
            """
            self.llm_model = llm_model
            self.tool_names = tool_names
            self.openai_api_key = openai_api_key
            
            # 检查兼容性
            self.compatibility_report = check_langchain_compatibility()
            logger.info(f"BaseTool兼容性报告: {self.compatibility_report}")
            
            # 初始化组件
            self._setup_llm()
            self._setup_tools()
            self._setup_agent()
        
        def _setup_llm(self):
            """设置LLM"""
            self.llm = ChatOpenAI(
                model=self.llm_model,
                temperature=0,
                api_key=self.openai_api_key
            )
        
        def _setup_tools(self):
            """设置工具集合"""
            # 获取转换后的Langchain工具
            self.tools = get_langchain_tools(self.tool_names)
            
            logger.info(f"已加载 {len(self.tools)} 个工具:")
            for tool in self.tools:
                logger.info(f"  - {tool.name}: {tool.description}")
        
        def _setup_agent(self):
            """设置ReAct Agent"""
            # ReAct prompt模板
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
            
            # 创建ReAct agent
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # 创建Agent执行器
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10
            )
        
        def run(self, query: str) -> str:
            """
            同步执行查询
            
            Args:
                query: 用户查询
                
            Returns:
                Agent的响应结果
            """
            try:
                result = self.agent_executor.invoke({"input": query})
                return result["output"]
            except Exception as e:
                logger.error(f"执行查询失败: {e}")
                return f"执行失败: {str(e)}"
        
        async def arun(self, query: str) -> str:
            """
            异步执行查询
            
            Args:
                query: 用户查询
                
            Returns:
                Agent的响应结果
            """
            try:
                result = await self.agent_executor.ainvoke({"input": query})
                return result["output"]
            except Exception as e:
                logger.error(f"异步执行查询失败: {e}")
                return f"执行失败: {str(e)}"
        
        def get_available_tools(self) -> List[str]:
            """获取可用工具列表"""
            return [tool.name for tool in self.tools]
        
        def get_tool_descriptions(self) -> dict:
            """获取工具描述信息"""
            return {tool.name: tool.description for tool in self.tools}

    # 使用示例
    async def demo_usage():
        """演示如何使用BasetoolReactAgent"""
        
        print("=== BaseTool ReAct Agent 集成演示 ===\n")
        
        # 1. 检查兼容性
        print("1. 检查兼容性...")
        compatibility = check_langchain_compatibility()
        print(f"可用工具数: {compatibility['total_base_tools']}")
        print(f"总操作数: {compatibility['total_operations']}")
        
        # 2. 创建Agent（选择特定工具）
        print("\n2. 创建ReAct Agent...")
        try:
            # 可以指定特定工具，如只使用chart工具
            agent = BasetoolReactAgent(
                tool_names=['chart'],  # 只使用chart工具
                llm_model="gpt-3.5-turbo"
            )
            
            print(f"Agent创建成功，可用工具: {agent.get_available_tools()}")
            
            # 3. 演示同步执行
            print("\n3. 同步执行示例...")
            query1 = "请帮我读取 /tmp/sample.csv 文件的数据"
            response1 = agent.run(query1)
            print(f"查询: {query1}")
            print(f"响应: {response1}")
            
            # 4. 演示异步执行
            print("\n4. 异步执行示例...")
            query2 = "创建一个柱状图显示销售数据"
            response2 = await agent.arun(query2)
            print(f"查询: {query2}")
            print(f"响应: {response2}")
            
        except Exception as e:
            print(f"演示过程中出现错误: {e}")
            print("这可能是因为缺少OpenAI API密钥或其他配置")

    # 批量工具转换示例
    def demo_tool_conversion():
        """演示工具转换过程"""
        print("\n=== 工具转换演示 ===")
        
        # 获取所有转换后的工具
        all_tools = create_react_agent_tools()
        
        print(f"总共转换了 {len(all_tools)} 个工具:")
        
        # 按原始工具分组展示
        tool_groups = {}
        for tool in all_tools:
            base_name = tool.base_tool_name
            if base_name not in tool_groups:
                tool_groups[base_name] = []
            tool_groups[base_name].append(tool)
        
        for base_name, tools in tool_groups.items():
            print(f"\n{base_name} 工具 ({len(tools)} 个操作):")
            for tool in tools:
                print(f"  - {tool.name}")
                print(f"    描述: {tool.description}")
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    schema_fields = list(tool.args_schema.__fields__.keys())
                    print(f"    参数: {schema_fields}")

    if __name__ == "__main__":
        print("BaseTool Langchain 集成示例")
        
        # 演示工具转换
        demo_tool_conversion()
        
        # 演示Agent使用（需要配置OpenAI API Key）
        # asyncio.run(demo_usage())
        
        print("\n如需运行完整演示，请配置 OpenAI API Key 并取消注释最后一行")

else:
    print("请安装必要的依赖包:")
    print("pip install langchain langchain-openai")
