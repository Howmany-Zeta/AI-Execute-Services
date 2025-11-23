from datetime import datetime
from typing import Optional, Dict, Any
import logging
from aiecs.infrastructure.persistence.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class TokenUsageRepository:
    """Encapsulates all Redis operations related to user token usage"""

    def _get_key_for_current_period(self, user_id: str, cycle_start_date: Optional[str] = None) -> str:
        """
        Generate Redis key for current billing period

        Args:
            user_id: User ID
            cycle_start_date: Cycle start date in YYYY-MM-DD format, defaults to current month if not provided

        Returns:
            Redis key string
        """
        if cycle_start_date:
            # Use provided cycle start date
            period = cycle_start_date
        else:
            # Use current month as default period
            period = datetime.now().strftime("%Y-%m-%d")

        return f"token_usage:{user_id}:{period}"

    async def increment_prompt_tokens(
        self,
        user_id: str,
        prompt_tokens: int,
        cycle_start_date: Optional[str] = None,
    ):
        """
        Increment prompt token usage for specified user

        Args:
            user_id: User ID
            prompt_tokens: Number of input tokens
            cycle_start_date: Cycle start date
        """
        if not user_id or prompt_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # Use HINCRBY for atomic increment
            client = await get_redis_client()
            await client.hincrby(redis_key, "prompt_tokens", prompt_tokens)
            logger.info(f"[Repository] User '{user_id}' prompt tokens incremented by {prompt_tokens} in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment prompt tokens for user {user_id}: {e}")
            raise

    async def increment_completion_tokens(
        self,
        user_id: str,
        completion_tokens: int,
        cycle_start_date: Optional[str] = None,
    ):
        """
        Increment completion token usage for specified user

        Args:
            user_id: User ID
            completion_tokens: Number of output tokens
            cycle_start_date: Cycle start date
        """
        if not user_id or completion_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # Use HINCRBY for atomic increment
            client = await get_redis_client()
            await client.hincrby(redis_key, "completion_tokens", completion_tokens)
            logger.info(f"[Repository] User '{user_id}' completion tokens incremented by {completion_tokens} in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to increment completion tokens for user {user_id}: {e}")
            raise

    async def increment_total_usage(
        self,
        user_id: str,
        total_tokens: int,
        cycle_start_date: Optional[str] = None,
    ):
        """
        Increment total token usage for specified user

        Args:
            user_id: User ID
            total_tokens: Total number of tokens
            cycle_start_date: Cycle start date
        """
        if not user_id or total_tokens <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # Use HINCRBY for atomic increment
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
        cycle_start_date: Optional[str] = None,
    ):
        """
        Increment both prompt and completion token usage for specified user

        Args:
            user_id: User ID
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            cycle_start_date: Cycle start date
        """
        if not user_id or (prompt_tokens <= 0 and completion_tokens <= 0):
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            # Batch update multiple fields
            updates = {}
            if prompt_tokens > 0:
                updates["prompt_tokens"] = prompt_tokens
            if completion_tokens > 0:
                updates["completion_tokens"] = completion_tokens

            # Calculate total token count
            total_tokens = prompt_tokens + completion_tokens
            if total_tokens > 0:
                updates["total_tokens"] = total_tokens

            # Use pipeline for batch operations
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
        Get token usage statistics for specified user

        Args:
            user_id: User ID
            cycle_start_date: Cycle start date

        Returns:
            Dictionary containing token usage statistics
        """
        if not user_id:
            return {}

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            client = await get_redis_client()
            stats = await client.hgetall(redis_key)

            # Convert to integer type
            result = {}
            for key, value in stats.items():
                try:
                    result[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    result[key] = 0

            # Ensure required fields exist
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
                "total_tokens": 0,
            }

    async def reset_usage(self, user_id: str, cycle_start_date: Optional[str] = None):
        """
        Reset token usage for specified user

        Args:
            user_id: User ID
            cycle_start_date: Cycle start date
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
        Set token usage limit for user

        Args:
            user_id: User ID
            limit: Token usage limit
            cycle_start_date: Cycle start date
        """
        if not user_id or limit <= 0:
            return

        redis_key = self._get_key_for_current_period(user_id, cycle_start_date)

        try:
            client = await get_redis_client()
            await client.hset(redis_key, key="usage_limit", value=str(limit))
            logger.info(f"[Repository] Set usage limit {limit} for user '{user_id}' in key '{redis_key}'.")
        except Exception as e:
            logger.error(f"Failed to set usage limit for user {user_id}: {e}")
            raise

    async def check_usage_limit(self, user_id: str, cycle_start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if user has exceeded usage limit

        Args:
            user_id: User ID
            cycle_start_date: Cycle start date

        Returns:
            Dictionary containing limit check results
        """
        if not user_id:
            return {
                "exceeded": False,
                "current_usage": 0,
                "limit": 0,
                "remaining": 0,
            }

        try:
            stats = await self.get_usage_stats(user_id, cycle_start_date)
            current_usage = stats.get("total_tokens", 0)

            redis_key = self._get_key_for_current_period(user_id, cycle_start_date)
            client = await get_redis_client()
            limit_str = await client.hget(redis_key, "usage_limit")
            limit = int(limit_str) if limit_str else 0

            exceeded = limit > 0 and current_usage >= limit
            remaining = max(0, limit - current_usage) if limit > 0 else float("inf")

            result = {
                "exceeded": exceeded,
                "current_usage": current_usage,
                "limit": limit,
                "remaining": remaining,
            }

            logger.debug(f"[Repository] Usage limit check for user '{user_id}': {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to check usage limit for user {user_id}: {e}")
            return {
                "exceeded": False,
                "current_usage": 0,
                "limit": 0,
                "remaining": 0,
            }


# Create a singleton for global application use
token_usage_repo = TokenUsageRepository()
