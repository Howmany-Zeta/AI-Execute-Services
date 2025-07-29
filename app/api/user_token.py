from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from pydantic import BaseModel

from ..utils.token_usage_repository import token_usage_repo
from ..infrastructure.persistence.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/api/token", tags=["token"])

class TokenUsageResponse(BaseModel):
    """Token使用量响应模型"""
    user_id: str
    cycle_start_date: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    usage_limit: Optional[int] = None
    remaining_tokens: Optional[int] = None
    exceeded: bool = False
    timestamp: str

class TokenLimitRequest(BaseModel):
    """设置Token限制请求模型"""
    user_id: str
    limit: int
    cycle_start_date: Optional[str] = None

@router.get("/usage/{user_id}")
async def get_user_token_usage(
    user_id: str,
    cycle_start_date: Optional[str] = Query(None, description="周期开始日期 (YYYY-MM-DD)，不提供则使用当前月份")
) -> TokenUsageResponse:
    """
    获取指定用户的token使用量

    Args:
        user_id: 用户ID
        cycle_start_date: 周期开始日期，格式为 YYYY-MM-DD

    Returns:
        TokenUsageResponse: 包含用户token使用统计的响应
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")

        # 获取用户使用统计
        stats = await token_usage_repo.get_usage_stats(user_id, cycle_start_date)

        # 检查使用限制
        limit_check = await token_usage_repo.check_usage_limit(user_id, cycle_start_date)

        # 确定实际使用的周期开始日期
        actual_cycle_date = cycle_start_date or datetime.now().strftime("%Y-%m-%d")

        response = TokenUsageResponse(
            user_id=user_id,
            cycle_start_date=actual_cycle_date,
            total_tokens=stats.get("total_tokens", 0),
            prompt_tokens=stats.get("prompt_tokens", 0),
            completion_tokens=stats.get("completion_tokens", 0),
            usage_limit=limit_check.get("limit") if limit_check.get("limit", 0) > 0 else None,
            remaining_tokens=limit_check.get("remaining") if limit_check.get("limit", 0) > 0 else None,
            exceeded=limit_check.get("exceeded", False),
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Retrieved token usage for user {user_id}: {stats.get('total_tokens', 0)} tokens")
        return response

    except Exception as e:
        logger.error(f"Failed to get token usage for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户token使用量失败: {str(e)}")

@router.get("/usage/{user_id}/total")
async def get_user_total_tokens(
    user_id: str,
    cycle_start_date: Optional[str] = Query(None, description="周期开始日期 (YYYY-MM-DD)，不提供则使用当前月份")
) -> Dict[str, Any]:
    """
    获取指定用户的总token使用量（简化版本，专门供express-gateway查询）

    Args:
        user_id: 用户ID
        cycle_start_date: 周期开始日期，格式为 YYYY-MM-DD

    Returns:
        Dict: 包含总token数量的简化响应
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")

        # 获取用户使用统计
        stats = await token_usage_repo.get_usage_stats(user_id, cycle_start_date)
        total_tokens = stats.get("total_tokens", 0)

        # 检查使用限制
        limit_check = await token_usage_repo.check_usage_limit(user_id, cycle_start_date)

        response = {
            "user_id": user_id,
            "total_tokens": total_tokens,
            "exceeded": limit_check.get("exceeded", False),
            "limit": limit_check.get("limit", 0),
            "remaining": limit_check.get("remaining", 0) if limit_check.get("limit", 0) > 0 else None,
            "cycle_start_date": cycle_start_date or datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Retrieved total tokens for user {user_id}: {total_tokens}")
        return response

    except Exception as e:
        logger.error(f"Failed to get total tokens for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"获取用户总token数量失败: {str(e)}")

@router.post("/limit")
async def set_user_token_limit(request: TokenLimitRequest) -> Dict[str, Any]:
    """
    设置用户的token使用限制

    Args:
        request: 包含用户ID、限制值和周期开始日期的请求

    Returns:
        Dict: 设置结果
    """
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")

        if request.limit <= 0:
            raise HTTPException(status_code=400, detail="限制值必须大于0")

        await token_usage_repo.set_usage_limit(
            request.user_id,
            request.limit,
            request.cycle_start_date
        )

        response = {
            "user_id": request.user_id,
            "limit": request.limit,
            "cycle_start_date": request.cycle_start_date or datetime.now().strftime("%Y-%m-%d"),
            "status": "success",
            "message": f"成功设置用户 {request.user_id} 的token限制为 {request.limit}",
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Set token limit for user {request.user_id}: {request.limit}")
        return response

    except HTTPException:
        # Re-raise HTTPException to preserve status code
        raise
    except Exception as e:
        logger.error(f"Failed to set token limit for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"设置用户token限制失败: {str(e)}")

@router.delete("/usage/{user_id}")
async def reset_user_token_usage(
    user_id: str,
    cycle_start_date: Optional[str] = Query(None, description="周期开始日期 (YYYY-MM-DD)，不提供则使用当前月份")
) -> Dict[str, Any]:
    """
    重置用户的token使用量

    Args:
        user_id: 用户ID
        cycle_start_date: 周期开始日期，格式为 YYYY-MM-DD

    Returns:
        Dict: 重置结果
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="用户ID不能为空")

        await token_usage_repo.reset_usage(user_id, cycle_start_date)

        response = {
            "user_id": user_id,
            "cycle_start_date": cycle_start_date or datetime.now().strftime("%Y-%m-%d"),
            "status": "success",
            "message": f"成功重置用户 {user_id} 的token使用量",
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Reset token usage for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to reset token usage for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"重置用户token使用量失败: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    健康检查端点

    Returns:
        Dict: 服务状态
    """
    try:
        # 测试Redis连接
        redis_client = await get_redis_client()
        await redis_client.get_client()

        return {
            "status": "healthy",
            "service": "token-management",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}")

# 为了向后兼容，提供一些便利函数
async def get_user_total_token_count(user_id: str, cycle_start_date: Optional[str] = None) -> int:
    """
    便利函数：获取用户总token数量

    Args:
        user_id: 用户ID
        cycle_start_date: 周期开始日期

    Returns:
        int: 总token数量
    """
    try:
        stats = await token_usage_repo.get_usage_stats(user_id, cycle_start_date)
        return stats.get("total_tokens", 0)
    except Exception as e:
        logger.error(f"Failed to get total token count for user {user_id}: {e}")
        return 0

async def check_user_token_limit(user_id: str, cycle_start_date: Optional[str] = None) -> bool:
    """
    便利函数：检查用户是否超过token限制

    Args:
        user_id: 用户ID
        cycle_start_date: 周期开始日期

    Returns:
        bool: True表示超过限制，False表示未超过
    """
    try:
        limit_check = await token_usage_repo.check_usage_limit(user_id, cycle_start_date)
        return limit_check.get("exceeded", False)
    except Exception as e:
        logger.error(f"Failed to check token limit for user {user_id}: {e}")
        return False
