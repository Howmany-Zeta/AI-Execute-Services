#!/usr/bin/env python3
# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
FastAPI 集成模式示例
展示如何将 AIECS 功能集成到现有的 FastAPI 应用中
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import logging

# AIECS 导入
from aiecs import AIECS, TaskContext, get_fastapi_app, validate_required_settings
from aiecs.tools import get_tool

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== 方式1: 子应用挂载 ==========

def create_app_with_mount():
    """创建带 AIECS 子应用挂载的 FastAPI 应用"""
    
    # 主应用
    app = FastAPI(
        title="集成 AIECS 的应用",
        description="演示如何挂载 AIECS 作为子应用",
        version="1.0.0"
    )
    
    # 挂载 AIECS 应用
    try:
        aiecs_app = get_fastapi_app()
        app.mount("/ai", aiecs_app)
        logger.info("✅ AIECS 子应用挂载成功")
    except Exception as e:
        logger.error(f"❌ AIECS 挂载失败: {e}")
    
    # 主应用路由
    @app.get("/")
    async def root():
        return {
            "message": "主应用首页",
            "ai_service": "/ai",
            "endpoints": {
                "health": "/ai/health",
                "tools": "/ai/api/tools",
                "execute": "/ai/api/execute"
            }
        }
    
    @app.get("/status")
    async def app_status():
        return {
            "main_app": "运行中",
            "ai_service": "已挂载到 /ai",
            "version": "1.0.0"
        }
    
    return app

# ========== 方式2: 组件级集成 ==========

# 请求模型
class AnalyzeRequest(BaseModel):
    text: str
    user_id: str = "anonymous"
    provider: str = "OpenAI" 
    model: str = "gpt-3.5-turbo"

class ScrapeRequest(BaseModel):
    url: str
    extract: List[str] = ["title", "content"]

class ToolRequest(BaseModel):
    tool_name: str
    operation: str
    params: Dict[str, Any]

def create_app_with_integration():
    """创建组件级集成的 FastAPI 应用"""
    
    app = FastAPI(
        title="AIECS 组件集成应用",
        description="将 AIECS 功能直接集成到应用逻辑中",
        version="1.0.0"
    )
    
    # 全局 AIECS 客户端
    aiecs_client: Optional[AIECS] = None
    
    @app.on_event("startup")
    async def startup():
        nonlocal aiecs_client
        
        logger.info("🚀 启动应用...")
        
        # 检查配置
        try:
            validate_required_settings("basic")
            logger.info("✅ 基础配置检查通过")
        except ValueError as e:
            logger.warning(f"⚠️ 配置不完整: {e}")
            logger.warning("AI 功能将受限")
        
        # 初始化 AIECS 客户端
        try:
            aiecs_client = AIECS()
            await aiecs_client.initialize()
            logger.info("✅ AIECS 客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ AIECS 初始化失败: {e}")
            logger.info("应用将以受限模式运行")
    
    @app.on_event("shutdown")
    async def shutdown():
        nonlocal aiecs_client
        if aiecs_client:
            await aiecs_client.close()
            logger.info("✅ AIECS 客户端已关闭")
    
    # 依赖注入
    async def get_aiecs_client():
        if not aiecs_client:
            raise HTTPException(
                status_code=503, 
                detail="AI 服务不可用，请检查配置"
            )
        return aiecs_client
    
    # 业务路由
    @app.get("/")
    async def root():
        return {
            "app": "AIECS 集成应用",
            "features": [
                "文本分析 /api/analyze",
                "网页抓取 /api/scrape", 
                "工具执行 /api/tool/execute",
                "工具列表 /api/tools"
            ]
        }
    
    @app.post("/api/analyze")
    async def analyze_text(
        request: AnalyzeRequest,
        client: AIECS = Depends(get_aiecs_client)
    ):
        """文本分析 API"""
        try:
            context = TaskContext({
                "user_id": request.user_id,
                "metadata": {
                    "aiPreference": {
                        "provider": request.provider,
                        "model": request.model
                    }
                },
                "data": {
                    "task": "分析文本情感、关键词和主题",
                    "content": request.text
                }
            })
            
            result = await client.execute(context)
            return {
                "analysis": result,
                "text": request.text,
                "provider": request.provider
            }
            
        except Exception as e:
            logger.error(f"文本分析失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scrape")
    async def scrape_website(
        request: ScrapeRequest,
        client: AIECS = Depends(get_aiecs_client)
    ):
        """网页抓取 API"""
        try:
            result = await client.execute_tool(
                "scraper_tool",
                "scrape_url",
                {
                    "url": request.url,
                    "extract": request.extract
                }
            )
            
            return {
                "scraped_data": result,
                "url": request.url,
                "extracted_fields": request.extract
            }
            
        except Exception as e:
            logger.error(f"网页抓取失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/tool/execute")
    async def execute_tool(
        request: ToolRequest,
        client: AIECS = Depends(get_aiecs_client)
    ):
        """通用工具执行 API"""
        try:
            result = await client.execute_tool(
                request.tool_name,
                request.operation,
                request.params
            )
            
            return {
                "result": result,
                "tool": request.tool_name,
                "operation": request.operation
            }
            
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tools")
    async def get_tools(client: AIECS = Depends(get_aiecs_client)):
        """获取可用工具列表"""
        try:
            tools = await client.get_available_tools()
            return {
                "tools": tools,
                "count": len(tools),
                "categories": list(set(tool.get("category", "general") for tool in tools))
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/health")
    async def health_check():
        """应用健康检查"""
        ai_status = "可用" if aiecs_client and aiecs_client._initialized else "不可用"
        
        return {
            "app": "健康",
            "ai_service": ai_status,
            "version": "1.0.0"
        }
    
    return app

# ========== 方式3: 选择性功能集成 ==========

def create_app_selective():
    """创建选择性功能集成的应用（轻量级）"""
    
    app = FastAPI(
        title="AIECS 轻量级集成",
        description="只使用 AIECS 的工具系统，不启动完整服务",
        version="1.0.0"
    )
    
    @app.on_event("startup")
    async def startup():
        # 只初始化工具系统
        from aiecs.tools import discover_tools
        try:
            discover_tools("aiecs.tools")
            logger.info("✅ 工具系统初始化完成")
        except Exception as e:
            logger.error(f"❌ 工具系统初始化失败: {e}")
    
    @app.get("/")
    async def root():
        return {
            "app": "AIECS 轻量级集成",
            "mode": "工具系统专用",
            "features": ["工具列表", "直接工具调用"]
        }
    
    @app.get("/tools")
    async def list_tools():
        """列出可用工具（不需要完整初始化）"""
        try:
            from aiecs.tools import list_tools
            tools = list_tools()
            return {"tools": tools, "count": len(tools)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tools/{tool_name}/execute")
    async def execute_tool_direct(tool_name: str, params: Dict[str, Any]):
        """直接执行工具（轻量级模式）"""
        try:
            from aiecs.tools import get_tool
            tool = get_tool(tool_name)
            
            if not tool:
                raise HTTPException(status_code=404, detail=f"工具 {tool_name} 未找到")
            
            result = await tool.execute(params)
            return {
                "tool": tool_name,
                "result": result,
                "mode": "direct"
            }
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

# ========== 演示脚本 ==========

async def demo_all_integrations():
    """演示所有集成方式"""
    print("="*60)
    print("AIECS FastAPI 集成模式演示")
    print("="*60)
    
    # 演示配置检查
    print("\n📊 配置状态检查:")
    try:
        from aiecs import get_settings
        settings = get_settings()
        
        configs = {
            "OpenAI": settings.openai_api_key,
            "Vertex": settings.vertex_project_id,
            "xAI": settings.xai_api_key,
            "Redis": settings.celery_broker_url,
            "Database": f"{settings.db_host}:{settings.db_port}"
        }
        
        for name, value in configs.items():
            status = "🟢" if value else "🔴"
            print(f"   {status} {name}: {'已配置' if value else '未配置'}")
            
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
    
    print(f"\n📱 可用的集成方式:")
    print(f"1️⃣ 子应用挂载: create_app_with_mount()")
    print(f"2️⃣ 组件级集成: create_app_with_integration()")  
    print(f"3️⃣ 选择性集成: create_app_selective()")
    
    print(f"\n🚀 启动命令:")
    print(f"   uvicorn fastapi_integration_example:app_mount --reload")
    print(f"   uvicorn fastapi_integration_example:app_integration --reload")
    print(f"   uvicorn fastapi_integration_example:app_selective --reload")

if __name__ == "__main__":
    # 创建应用实例（用于 uvicorn 启动）
    app_mount = create_app_with_mount()
    app_integration = create_app_with_integration()  
    app_selective = create_app_selective()
    
    # 演示
    asyncio.run(demo_all_integrations())
