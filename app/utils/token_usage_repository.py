from datetime import datetime
from typing import Optional, Dict, Any
import logging
from ..infrastructure.persistence.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class TokenUsageRepository:
    """封装所有与用户Token使用量相关的Redis操作"""

    def _get_key_for_current_period(self, user_id: str, cycle_start_date: Optional[str] = None) -> str:
        """
        生成当前计费周期的Redis Key

        Args:
            user_id: 用户ID
            cycle_start_date: 周期开始日期，格式为 YYYY-MM-DD，如果不提供则使用当前月份

        Returns:
            Redis key字符串
        """
        if cycle_start_date:
            # 使用提供的周期开始日期
            period = cycle_start_date
        else:
            # 使用当前月份作为默认周期
            period = datetime.now().strftime("%Y-%m-%d")

        return f"token_usage:{user_id}:{period}"

    async def increment_prompt_tokens(self, user_id: str, prompt_tokens: int, cycle_start_date: Optional[str] = None):
        """
        为指定用户增加prompt token使用量

        Args:
            user_id: 用户ID
            prompt_tokens: 输入token数量
            cycle_start_date: 周期开始日期
        """
        if not user_id or prompt_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # 使用 HINCRBY 进行原子性累加
            client = await get_redis_client()
            await client.hincrby(redis_key, "prompt_tokens", prompt_tokens)
            logger.info(f"[Repository] User '{user_id}' prompt tokens incremented by {prompt_tokens} in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment prompt tokens for user {user_id}: {e}")
            raise

    async def increment_completion_tokens(self, user_id: str, completion_tokens: int, cycle_start_date: Optional[str] = None):
        """
        为指定用户增加completion token使用量

        Args:
            user_id: 用户ID
            completion_tokens: 输出token数量
            cycle_start_date: 周期开始日期
        """
        if not user_id or completion_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # 使用 HINCRBY 进行原子性累加
            client = await get_redis_client()
            await client.hincrby(redis_key, "completion_tokens", completion_tokens)
            logger.info(f"[Repository] User '{user_id}' completion tokens incremented by {completion_tokens} in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment completion tokens for user {user_id}: {e}")
            raise

    async def increment_total_usage(self, user_id: str, total_tokens: int, cycle_start_date: Optional[str] = None):
        """
        为指定用户增加总token使用量

        Args:
            user_id: 用户ID
            total_tokens: 总token数量
            cycle_start_date: 周期开始日期
        """
        if not user_id or total_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # 使用 HINCRBY 进行原子性累加
            client = await get_redis_client()
            await client.hincrby(redis_key, "total_tokens", total_tokens)
            logger.info(f"[Repository] User '{user_id}' total usage incremented by {total_tokens} tokens in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment total tokens for user {user_id}: {e}")
            raise

    async def increment_detailed_usage(
        self,
        user_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cycle_start_date: Optional[str] = None
    ):
        """
        为指定用户同时增加prompt和completion token使用量

        Args:
            user_id: 用户ID
            prompt_tokens: 输入token数量
            completion_tokens: 输出token数量
            cycle_start_date: 周期开始日期
        """
        if not user_id or (prompt_tokens <= 0 and completion_tokens <= 0):
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # 批量更新多个字段
            updates = {}
            if prompt_tokens > 0:
                updates["prompt_tokens"] = prompt_tokens
            if completion_tokens > 0:
                updates["completion_tokens"] = completion_tokens

            # 计算总token数
            total_tokens = prompt_tokens + completion_tokens
            if total_tokens > 0:
                updates["total_tokens"] = total_tokens

            # 使用pipeline进行批量操作
            redis_client_instance = await get_redis_client()
            client = await redis_client_instance.get_client()
            pipe = client.pipeline()

            for field, value in updates.items():
                pipe.hincrby(redis_key, field, value)

            await pipe.execute()

            logger.info(f"[Repository] User '{user_id}' detailed usage updated: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens} in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment detailed usage for user {user_id}: {e}")
            raise

    async def get_usage_stats(self, user_id: str, cycle_start_date: Optional[str] = None) -> Dict[str, int]:
        """
        获取指定用户的token使用统计

        Args:
            user_id: 用户ID
            cycle_start_date: 周期开始日期

        Returns:
            包含token使用统计的字典
        """
        if not user_id:
            return {}

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            client = await get_redis_client()
            stats = await client.hgetall(redis_key)

            # 转换为整数类型
            result = {}
            for key, value in stats.items():
                try:
                    result[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    result[key] = 0

            # 确保必要字段存在
            result.setdefault("prompt_tokens", 0)
            result.setdefault("completion_tokens", 0)
            result.setdefault("total_tokens", 0)

            logger.debug(f"[Repository] Retrieved usage stats for user '{user_id}': {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to get usage stats for user {user_id}: {e}")
            return {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }

    async def reset_usage(self, user_id: str, cycle_start_date: Optional[str] = None):
        """
        重置指定用户的token使用量

        Args:
            user_id: 用户ID
            cycle_start_date: 周期开始日期
        """
        if not user_id:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            redis_client_instance = await get_redis_client()
            client = await redis_client_instance.get_client()
            await client.delete(redis_key)
            logger.info(f"[Repository] Reset usage for user '{user_id}' in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to reset usage for user {user_id}: {e}")
            raise

    async def set_usage_limit(self, user_id: str, limit: int, cycle_start_date: Optional[str] = None):
        """
        设置用户的token使用限制

        Args:
            user_id: 用户ID
            limit: token使用限制
            cycle_start_date: 周期开始日期
        """
        if not user_id or limit <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            client = await get_redis_client()
            await client.hset(redis_key, {"usage_limit": str(limit)})
            logger.info(f"[Repository] Set usage limit {limit} for user '{user_id}' in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to set usage limit for user {user_id}: {e}")
            raise

    async def check_usage_limit(self, user_id: str, cycle_start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        检查用户是否超过使用限制

        Args:
            user_id: 用户ID
            cycle_start_date: 周期开始日期

        Returns:
            包含限制检查结果的字典
        """
        if not user_id:
            return {"exceeded": False, "current_usage": 0, "limit": 0, "remaining": 0}

        try:
            stats = await self.get_usage_stats(user_id, cycle_start_date)
            current_usage = stats.get("total_tokens", 0)

            redis_key = self._get_key_for_current_period(user_id, cycle_start_date)
            client = await get_redis_client()
            limit_str = await client.hget(redis_key, "usage_limit")
            limit = int(limit_str) if limit_str else 0

            exceeded = limit > 0 and current_usage >= limit
            remaining = max(0, limit - current_usage) if limit > 0 else float('inf')

            result = {
                "exceeded": exceeded,
                "current_usage": current_usage,
                "limit": limit,
                "remaining": remaining
            }

            logger.debug(f"[Repository] Usage limit check for user '{user_id}': {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to check usage limit for user {user_id}: {e}")
            return {"exceeded": False, "current_usage": 0, "limit": 0, "remaining": 0}


# 创建一个单例供应用全局使用
token_usage_repo = TokenUsageRepository()
