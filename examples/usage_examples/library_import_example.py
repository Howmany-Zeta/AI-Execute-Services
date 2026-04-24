#!/usr/bin/env python3
# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
库导入模式示例
展示如何在 Python 代码中直接使用 AIECS 作为库
"""

import asyncio
import logging
from aiecs import AIECS, TaskContext, validate_required_settings, get_settings, create_simple_client

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_basic_usage():
    """基础使用示例"""
    print("\n1️⃣ 基础使用示例")
    print("-" * 40)
    
    # 使用 session context manager（推荐）- 简化模式
    try:
        async with AIECS(mode="simple").session() as client:
            print("✅ AIECS 客户端初始化成功")
            
            # 获取可用工具
            tools = await client.get_available_tools()
            print(f"✅ 发现 {len(tools)} 个可用工具")
            
            # 创建任务上下文
            context = TaskContext({
                "user_id": "demo_user",
                "chat_id": "demo_chat",
                "metadata": {
                    "aiPreference": {
                        "provider": "OpenAI",
                        "model": "gpt-3.5-turbo"
                    }
                },
                "data": {
                    "task": "分析这段文本的情感倾向",
                    "content": "今天天气很好，心情愉悦，工作效率很高！"
                }
            })
            
            print("✅ 任务上下文创建完成")
            
            # 注意：实际执行需要完整的环境配置
            print("📋 任务已准备就绪（需要配置环境变量才能执行）")
            
    except Exception as e:
        print(f"❌ 基础使用失败: {e}")

async def example_tool_direct_usage():
    """直接工具使用示例"""
    print("\n2️⃣ 直接工具使用示例") 
    print("-" * 40)
    
    try:
        async with AIECS(mode="simple").session() as client:
            # 获取特定工具
            scraper_tool = await client.get_tool("scraper_tool")
            if scraper_tool:
                print("✅ 获取网页抓取工具成功")
                print(f"   工具描述: {scraper_tool.description}")
                
                # 执行工具（示例参数）
                tool_params = {
                    "url": "https://httpbin.org/json",
                    "extract": ["content"]
                }
                print(f"🔧 工具参数: {tool_params}")
                print("📋 工具已准备执行（需要网络连接）")
            
            # 尝试获取其他工具
            office_tool = await client.get_tool("office_tool")
            if office_tool:
                print("✅ 获取文档处理工具成功")
                
    except Exception as e:
        print(f"❌ 工具使用失败: {e}")

async def example_manual_lifecycle():
    """手动生命周期管理示例"""
    print("\n3️⃣ 手动生命周期管理示例")
    print("-" * 40)
    
    client = None
    try:
        # 创建客户端（简化模式）
        client = AIECS(mode="simple")
        print("✅ AIECS 客户端创建")
        
        # 手动初始化
        await client.initialize()
        print("✅ AIECS 客户端初始化完成")
        
        # 执行操作
        tools = await client.get_available_tools()
        print(f"✅ 获取到 {len(tools)} 个工具")
        
        # 检查状态
        print(f"✅ 初始化状态: {client._initialized}")
        print(f"✅ 工具发现状态: {client._tools_discovered}")
        
    except Exception as e:
        print(f"❌ 手动管理失败: {e}")
        
    finally:
        # 手动清理
        if client:
            await client.close()
            print("✅ AIECS 客户端已关闭")

async def example_configuration_check():
    """配置检查示例"""
    print("\n4️⃣ 配置检查示例")
    print("-" * 40)
    
    try:
        # 获取配置
        settings = get_settings()
        print("✅ 获取配置成功")
        
        # 检查不同级别的配置
        check_levels = ["basic", "llm", "database", "storage"]
        
        for level in check_levels:
            try:
                validate_required_settings(level)
                print(f"✅ {level.upper()} 配置检查通过")
            except ValueError as e:
                print(f"⚠️  {level.upper()} 配置缺失: {str(e).split(':')[1].strip()}")
        
        # 显示当前配置状态
        print("\n📊 当前配置状态:")
        config_status = {
            "OpenAI": bool(settings.openai_api_key),
            "Vertex AI": bool(settings.vertex_project_id and settings.google_application_credentials),
            "xAI": bool(settings.xai_api_key),
            "Redis": bool(settings.celery_broker_url),
            "Database": bool(settings.db_password),
            "Storage": bool(settings.google_cloud_project_id)
        }
        
        for service, configured in config_status.items():
            status = "🟢" if configured else "🔴"
            print(f"   {status} {service}")
    
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")

async def example_custom_config():
    """自定义配置示例"""
    print("\n5️⃣ 自定义配置示例")
    print("-" * 40)
    
    try:
        # 自定义配置
        custom_config = {
            "rate_limit_requests_per_second": 2,  # 降低请求频率
            "max_retries": 5,                     # 增加重试次数
            "timeout": 120                        # 增加超时时间
        }
        
        async with AIECS(config=custom_config, mode="simple").session() as client:
            print("✅ 使用自定义配置创建客户端")
            print(f"   配置参数: {custom_config}")
            
            # 检查配置是否生效
            if hasattr(client, 'config'):
                print(f"✅ 自定义配置已应用: {client.config}")
    
    except Exception as e:
        print(f"❌ 自定义配置失败: {e}")

async def example_convenience_functions():
    """便利函数示例"""
    print("\n6️⃣ 便利函数示例")
    print("-" * 40)
    
    try:
        # 使用便利函数创建简化客户端
        client = await create_simple_client()
        print("✅ 使用 create_simple_client() 创建客户端成功")
        
        # 获取工具列表
        tools = await client.get_available_tools()
        print(f"✅ 获取到 {len(tools)} 个工具")
        
        # 显示前几个工具
        for i, tool in enumerate(tools[:3]):
            print(f"   {i+1}. {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        # 清理
        await client.close()
        print("✅ 客户端已清理")
        
    except Exception as e:
        print(f"❌ 便利函数失败: {e}")

def main():
    """主函数"""
    print("="*60)
    print("AIECS 库导入模式示例")
    print("="*60)
    print()
    print("这个示例展示了如何在 Python 代码中直接使用 AIECS。")
    print("无需启动独立服务，可以直接集成到现有应用中。")
    print()
    
    try:
        # 运行所有示例
        asyncio.run(example_basic_usage())
        asyncio.run(example_tool_direct_usage()) 
        asyncio.run(example_manual_lifecycle())
        asyncio.run(example_configuration_check())
        asyncio.run(example_custom_config())
        asyncio.run(example_convenience_functions())
        
        print("\n" + "="*60)
        print("🎉 库导入模式示例完成！")
        print()
        print("💡 下一步：")
        print("1. 配置环境变量（见 .env 示例）")
        print("2. 启动 Redis: redis-server")
        print("3. 启动 PostgreSQL: sudo systemctl start postgresql")
        print("4. 运行你的应用代码")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断执行")
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")

if __name__ == "__main__":
    main()
