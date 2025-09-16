import redis.asyncio as redis
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client singleton for sharing across different caching strategies"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def initialize(self):
        """Initialize Redis client"""
        try:
            # Get Redis configuration from environment variables
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            redis_password = os.getenv('REDIS_PASSWORD')

            # Create connection pool
            self._connection_pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self._client.ping()
            logger.info(f"Redis client initialized successfully: {redis_host}:{redis_port}/{redis_db}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise

    async def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        logger.info("Redis client closed")

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """Atomically increment hash field"""
        client = await self.get_client()
        return await client.hincrby(name, key, amount)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        client = await self.get_client()
        return await client.hget(name, key)

    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        client = await self.get_client()
        return await client.hgetall(name)

    async def hset(self, name: str, mapping: dict) -> int:
        """Set hash fields"""
        client = await self.get_client()
        return await client.hset(name, mapping=mapping)

    async def expire(self, name: str, time: int) -> bool:
        """Set expiration time"""
        client = await self.get_client()
        return await client.expire(name, time)

    async def exists(self, name: str) -> bool:
        """Check if key exists"""
        client = await self.get_client()
        return bool(await client.exists(name))

    async def ping(self) -> bool:
        """Test Redis connection"""
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

# ✅ Key changes:
# 1. No longer create instance immediately.
# 2. Define a global variable with initial value None. This variable will be populated by lifespan.
redis_client: Optional[RedisClient] = None

# 3. Provide an initialization function for lifespan to call
async def initialize_redis_client():
    """Create and initialize global Redis client instance at application startup."""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
        await redis_client.initialize()

# 4. Provide a close function for lifespan to call
async def close_redis_client():
    """Close global Redis client instance at application shutdown."""
    if redis_client:
        await redis_client.close()

# For backward compatibility, keep get_redis_client function
async def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call initialize_redis_client() first.")
    return redis_client
