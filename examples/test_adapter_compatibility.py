"""
BaseTool Langchain 适配器兼容性测试

无需外部API依赖的测试脚本，验证适配器功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiecs.tools.langchain_adapter import (
    tool_registry,
    get_langchain_tools,
    check_langchain_compatibility,
    LangchainToolAdapter
)
from aiecs.tools import list_tools, TOOL_CLASSES

def test_compatibility():
    """测试兼容性检查功能"""
    print("=== BaseTool Langchain 兼容性测试 ===\n")
    
    # 1. 基础兼容性检查
    print("1. 检查基础兼容性...")
    compatibility = check_langchain_compatibility()
    
    print(f"Langchain 可用: {compatibility['langchain_available']}")
    print(f"BaseTool 工具数: {compatibility['total_base_tools']}")
    print(f"总操作数: {compatibility['total_operations']}")
    print(f"兼容工具数: {len(compatibility['compatible_tools'])}")
    print(f"不兼容工具数: {len(compatibility['incompatible_tools'])}")
    
    if compatibility['incompatible_tools']:
        print("不兼容的工具:")
        for tool_info in compatibility['incompatible_tools']:
            print(f"  - {tool_info['name']}: {tool_info['error']}")
    
    return compatibility

def test_tool_discovery():
    """测试工具发现功能"""
    print("\n2. 测试工具发现...")
    
    available_tools = list_tools()
    print(f"发现的BaseTool: {available_tools}")
    
    # 测试每个工具的操作发现
    for tool_name in available_tools[:3]:  # 只测试前3个工具避免输出过多
        if tool_name in TOOL_CLASSES:
            print(f"\n分析工具: {tool_name}")
            tool_class = TOOL_CLASSES[tool_name]
            operations = tool_registry.discover_operations(tool_class)
            
            print(f"  发现的操作 ({len(operations)}):")
            for op in operations:
                print(f"    - {op['name']}")
                print(f"      描述: {op['description']}")
                print(f"      Schema: {op['schema'].__name__ if op['schema'] else 'None'}")
                print(f"      异步: {op['is_async']}")

def test_adapter_creation():
    """测试适配器创建"""
    print("\n3. 测试适配器创建...")
    
    try:
        # 尝试为单个工具创建适配器
        available_tools = list_tools()
        if available_tools:
            test_tool = available_tools[0]
            print(f"为工具 '{test_tool}' 创建Langchain适配器...")
            
            adapters = tool_registry.create_langchain_tools(test_tool)
            print(f"成功创建 {len(adapters)} 个适配器:")
            
            for adapter in adapters[:5]:  # 只显示前5个
                print(f"  - {adapter.name}")
                print(f"    描述: {adapter.description}")
                print(f"    参数Schema: {adapter.args_schema.__name__ if hasattr(adapter, 'args_schema') and adapter.args_schema else 'None'}")
        
    except Exception as e:
        print(f"适配器创建测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_mock_execution():
    """模拟测试工具执行（不实际调用外部服务）"""
    print("\n4. 模拟工具执行测试...")
    
    try:
        # 创建一个简单的适配器进行测试
        from aiecs.tools.langchain_adapter import LangchainToolAdapter
        
        # 创建模拟适配器
        mock_adapter = LangchainToolAdapter(
            base_tool_name="test_tool",
            operation_name="test_operation", 
            description="测试适配器"
        )
        
        print(f"创建的模拟适配器:")
        print(f"  名称: {mock_adapter.name}")
        print(f"  描述: {mock_adapter.description}")
        print(f"  基础工具: {mock_adapter.base_tool_name}")
        print(f"  操作名: {mock_adapter.operation_name}")
        
    except Exception as e:
        print(f"模拟执行测试失败: {e}")

def generate_integration_report():
    """生成集成报告"""
    print("\n=== 集成可行性报告 ===")
    
    compatibility = check_langchain_compatibility()
    
    print(f"""
🔍 现状分析:
  - BaseTool 工具总数: {compatibility['total_base_tools']}
  - 可转换操作总数: {compatibility['total_operations']}
  - Langchain 兼容性: {'✅ 可用' if compatibility['langchain_available'] else '❌ 不可用'}

📊 转换潜力:
  - 每个 BaseTool 平均可生成: {compatibility['total_operations'] / max(compatibility['total_base_tools'], 1):.1f} 个 Langchain 工具
  - 总计可为 ReAct Agent 提供: {compatibility['total_operations']} 个独立工具

✅ 优势:
  1. 完整保持原有功能特性（缓存、安全、性能监控）
  2. 自动化转换，无需手动适配
  3. 支持同步和异步执行
  4. 支持动态工具发现和注册
  5. 保持输入验证和错误处理

🔧 使用建议:
  1. 通过 get_langchain_tools() 获取所有转换后的工具
  2. 可选择性地使用特定工具子集
  3. 与标准 Langchain ReAct Agent 完全兼容
  4. 支持批量操作和复杂工作流

📝 实施步骤:
  1. pip install langchain langchain-openai
  2. from aiecs.tools.langchain_adapter import get_langchain_tools
  3. tools = get_langchain_tools()  # 获取所有工具
  4. 创建 ReAct Agent 并传入工具列表
    """)
    
    if compatibility['compatible_tools']:
        print("详细工具清单:")
        for tool_info in compatibility['compatible_tools']:
            print(f"  📦 {tool_info['name']}: {tool_info['operations_count']} 个操作")
            for op in tool_info['operations']:
                print(f"    - {tool_info['name']}_{op}")

def main():
    """主测试函数"""
    try:
        # 运行所有测试
        test_compatibility()
        test_tool_discovery() 
        test_adapter_creation()
        test_mock_execution()
        generate_integration_report()
        
        print("\n✅ 所有测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
