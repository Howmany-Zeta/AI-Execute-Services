import redis.asyncio as redis
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis客户端单例，供不同缓存策略共享使用"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def initialize(self):
        """初始化Redis客户端"""
        try:
            # 从环境变量获取Redis配置
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD')

            # 创建连接池
            self._connection_pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )

            # 创建Redis客户端
            self._client = redis.Redis(connection_pool=self._connection_pool)

            # 测试连接
            await self._client.ping()
            logger.info(f"Redis client initialized successfully: {redis_host}:{redis_port}/{redis_db}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise

    async def get_client(self) -> redis.Redis:
        """获取Redis客户端实例"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        logger.info("Redis client closed")

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Hash字段原子性增加"""
        client = await self.get_client()
        return await client.hincrby(name, key, amount)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取Hash字段值"""
        client = await self.get_client()
        return await client.hget(name, key)

    async def hgetall(self, name: str) -> dict:
        """获取Hash所有字段"""
        client = await self.get_client()
        return await client.hgetall(name)

    async def hset(self, name: str, mapping: dict) -> int:
        """设置Hash字段"""
        client = await self.get_client()
        return await client.hset(name, mapping=mapping)

    async def expire(self, name: str, time: int) -> bool:
        """设置过期时间"""
        client = await self.get_client()
        return await client.expire(name, time)

    async def exists(self, name: str) -> bool:
        """检查key是否存在"""
        client = await self.get_client()
        return bool(await client.exists(name))

    async def ping(self) -> bool:
        """测试Redis连接"""
        try:
            client = await self.get_client()
            result = await client.ping()
            return result
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def info(self, section: str = None) -> dict:
        """Get Redis server information"""
        try:
            client = await self.get_client()
            return await client.info(section)
        except Exception as e:
            logger.error(f"Redis info failed: {e}")
            return {}

    async def delete(self, *keys) -> int:
        """Delete one or more keys"""
        try:
            client = await self.get_client()
            return await client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return 0

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """Set a key-value pair with optional expiration"""
        try:
            client = await self.get_client()
            return await client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            client = await self.get_client()
            return await client.get(key)
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

# ✅ 关键改动：
# 1. 不再立即创建实例。
# 2. 定义一个全局变量，初始值为None。这个变量将被lifespan填充。
redis_client: Optional[RedisClient] = None

# 3. 提供一个初始化函数供lifespan调用
async def initialize_redis_client():
    """在应用启动时创建并初始化全局Redis客户端实例。"""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
        await redis_client.initialize()

# 4. 提供一个关闭函数供lifespan调用
async def close_redis_client():
    """在应用关闭时关闭全局Redis客户端实例。"""
    if redis_client:
        await redis_client.close()

# 为了向后兼容，保留get_redis_client函数
async def get_redis_client() -> RedisClient:
    """获取全局Redis客户端实例"""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call initialize_redis_client() first.")
    return redis_client
