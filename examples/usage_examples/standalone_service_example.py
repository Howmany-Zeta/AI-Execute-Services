#!/usr/bin/env python3
# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
独立服务模式示例
展示如何启动完整的 AIECS 服务并通过 HTTP API 调用
"""

import asyncio
import httpx
import json
from typing import Dict, Any

async def test_aiecs_service():
    """测试 AIECS 独立服务的各个端点"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("🔍 测试 AIECS 独立服务...")
        
        # 1. 健康检查
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ 服务健康检查通过")
                print(f"   {response.json()}")
            else:
                print("❌ 服务不可用")
                return
        except Exception as e:
            print(f"❌ 无法连接到服务: {e}")
            print("请确保先启动服务: aiecs")
            return
        
        # 2. 获取可用工具
        try:
            response = await client.get(f"{base_url}/api/tools")
            tools_data = response.json()
            print(f"✅ 发现 {tools_data['count']} 个可用工具")
            for tool in tools_data['tools'][:3]:  # 显示前3个
                print(f"   - {tool['name']}: {tool['description']}")
        except Exception as e:
            print(f"❌ 获取工具列表失败: {e}")
        
        # 3. 获取 AI 提供商
        try:
            response = await client.get(f"{base_url}/api/providers")
            providers = response.json()
            print(f"✅ 支持 {providers['count']} 个 AI 提供商")
            for provider in providers['providers']:
                status = "🟢" if provider['enabled'] else "🔴"
                print(f"   {status} {provider['name']}")
        except Exception as e:
            print(f"❌ 获取提供商列表失败: {e}")
        
        # 4. 执行简单任务
        try:
            task_data = {
                "type": "task",
                "mode": "execute",
                "service": "default", 
                "userId": "demo_user",
                "context": {
                    "metadata": {
                        "aiPreference": {
                            "provider": "OpenAI",
                            "model": "gpt-3.5-turbo"
                        }
                    },
                    "data": {
                        "task": "简单文本分析",
                        "content": "今天是个好天气，适合出去走走。"
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}/api/execute",
                json=task_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result["taskId"]
                print(f"✅ 任务提交成功，ID: {task_id}")
                
                # 查询任务状态
                await asyncio.sleep(2)  # 等待任务执行
                status_response = await client.get(f"{base_url}/api/task/{task_id}")
                status_data = status_response.json()
                print(f"📊 任务状态: {status_data.get('status', 'unknown')}")
            else:
                print(f"❌ 任务提交失败: {response.text}")
        
        except Exception as e:
            print(f"❌ 任务执行失败: {e}")

def main():
    """主函数"""
    print("="*60)
    print("AIECS 独立服务模式测试")
    print("="*60)
    print()
    print("请确保已启动以下服务：")
    print("1. AIECS 主服务: aiecs")
    print("2. Redis: redis-server") 
    print("3. PostgreSQL: sudo systemctl start postgresql")
    print("4. Celery Worker: celery -A aiecs.tasks.worker.celery_app worker")
    print()
    
    asyncio.run(test_aiecs_service())

if __name__ == "__main__":
    main()
