# Example Implementations: Common Patterns

This document provides complete, working examples for common integration patterns with enhanced agent flexibility features.

## Table of Contents

1. [Stateful Tools](#stateful-tools)
2. [Custom LLM Clients](#custom-llm-clients)
3. [Config Managers](#config-managers)
4. [Checkpointers](#checkpointers)
5. [Complete Integration Examples](#complete-integration-examples)

## Stateful Tools

### Example 1: Database Query Tool

Tool that maintains a database connection.

```python
from typing import Dict, Any, Optional
from aiecs.tools import BaseTool
import asyncpg

class DatabaseQueryTool(BaseTool):
    """
    Tool for executing database queries with a persistent connection.
    
    This tool maintains a database connection pool and can execute
    queries across multiple agent invocations.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        name: str = "database_query",
        description: str = "Execute SQL queries against the database"
    ):
        super().__init__(name=name, description=description)
        self.database_url = database_url
        self.pool_size = pool_size
        self._pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=1,
            max_size=self.pool_size
        )
    
    async def run_async(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        fetch_one: bool = False,
        fetch_all: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a database query.
        
        Args:
            query: SQL query string
            parameters: Query parameters (for parameterized queries)
            fetch_one: Return single row
            fetch_all: Return all rows (default)
        
        Returns:
            Dictionary with query results
        """
        if not self._pool:
            await self.initialize()
        
        async with self._pool.acquire() as connection:
            if parameters:
                rows = await connection.fetch(query, *parameters.values())
            else:
                rows = await connection.fetch(query)
            
            if fetch_one:
                return dict(rows[0]) if rows else {}
            
            return {
                "rows": [dict(row) for row in rows],
                "count": len(rows)
            }
    
    async def close(self):
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()

# Usage with agent
async def main():
    # Create tool instance with database connection
    db_tool = DatabaseQueryTool(
        database_url="postgresql://user:pass@localhost/db",
        pool_size=5
    )
    
    # Create agent with stateful tool
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="db_agent",
        name="Database Agent",
        llm_client=OpenAIClient(),
        tools={"database_query": db_tool},  # Stateful tool instance
        config=AgentConfiguration(
            goal="Answer questions using database queries"
        )
    )
    
    await agent.initialize()
    
    # Agent can use the tool with persistent connection
    result = await agent.execute_task(
        {
            "description": "How many users are in the database?"
        },
        {}
    )
    
    await agent.shutdown()
    await db_tool.close()
```

### Example 2: Context Engine Tool

Tool that uses ContextEngine for reading context.

```python
from typing import Dict, Any, Optional
from aiecs.tools import BaseTool
from aiecs.domain.context import ContextEngine

class ReadContextTool(BaseTool):
    """
    Tool for reading context from ContextEngine.
    
    This tool requires a ContextEngine instance to function,
    demonstrating dependency injection pattern.
    """
    
    def __init__(
        self,
        context_engine: ContextEngine,
        name: str = "read_context",
        description: str = "Read context from ContextEngine"
    ):
        super().__init__(name=name, description=description)
        self.context_engine = context_engine
    
    async def run_async(
        self,
        session_id: str,
        context_key: Optional[str] = None,
        limit: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Read context from ContextEngine.
        
        Args:
            session_id: Session ID to read context for
            context_key: Optional context key to filter by
            limit: Maximum number of context items to return
        
        Returns:
            Dictionary with context data
        """
        if context_key:
            context = await self.context_engine.get_context(
                session_id=session_id,
                key=context_key
            )
            return {"context": context}
        else:
            # Get all context for session
            contexts = await self.context_engine.list_contexts(
                session_id=session_id,
                limit=limit
            )
            return {"contexts": contexts}

# Usage with agent
async def main():
    # Initialize ContextEngine
    context_engine = ContextEngine()
    await context_engine.initialize()
    
    # Create tool with ContextEngine dependency
    read_context_tool = ReadContextTool(context_engine=context_engine)
    
    # Create agent with tool instance
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="context_agent",
        name="Context Agent",
        llm_client=OpenAIClient(),
        tools={"read_context": read_context_tool},  # Tool with dependency
        config=AgentConfiguration(
            goal="Read and use context from ContextEngine"
        ),
        context_engine=context_engine  # Also use ContextEngine for memory
    )
    
    await agent.initialize()
    
    # Agent can read context
    result = await agent.execute_task(
        {
            "description": "What context do we have for session user-123?"
        },
        {"session_id": "user-123"}
    )
    
    await agent.shutdown()
```

### Example 3: Service Integration Tool

Tool that calls external services with authentication.

```python
from typing import Dict, Any, Optional
from aiecs.tools import BaseTool
import aiohttp

class ServiceCallTool(BaseTool):
    """
    Tool for calling external services with authentication.
    
    This tool maintains an HTTP session with authentication headers,
    demonstrating stateful service integration.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        name: str = "service_call",
        description: str = "Call external service APIs"
    ):
        super().__init__(name=name, description=description)
        self.base_url = base_url
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize HTTP session with authentication"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._session = aiohttp.ClientSession(headers=headers)
    
    async def run_async(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call service endpoint.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request body data
            params: Query parameters
        
        Returns:
            Dictionary with response data
        """
        if not self._session:
            await self.initialize()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with self._session.request(
            method=method,
            url=url,
            json=data,
            params=params
        ) as response:
            response_data = await response.json()
            return {
                "status": response.status,
                "data": response_data
            }
    
    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()

# Usage with agent
async def main():
    # Create tool with service credentials
    service_tool = ServiceCallTool(
        base_url="https://api.example.com",
        api_key="your-api-key-here"
    )
    
    # Create agent with service tool
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="service_agent",
        name="Service Agent",
        llm_client=OpenAIClient(),
        tools={"service_call": service_tool},  # Service tool instance
        config=AgentConfiguration(
            goal="Call external services to get data"
        )
    )
    
    await agent.initialize()
    
    # Agent can call services with authentication
    result = await agent.execute_task(
        {
            "description": "Get user data from API endpoint /users/123"
        },
        {}
    )
    
    await agent.shutdown()
    await service_tool.close()
```

## Custom LLM Clients

### Example 1: Retry Wrapper

LLM client wrapper that adds retry logic.

```python
from typing import List, Dict, Optional, AsyncIterator
from aiecs.llm.protocols import LLMClientProtocol
from aiecs.llm.models import LLMResponse
import asyncio
import logging

logger = logging.getLogger(__name__)

class RetryLLMClient:
    """
    Wrapper that adds retry logic to any LLM client.
    
    This wrapper implements LLMClientProtocol and can wrap any
    LLM client implementation, adding automatic retry on failures.
    """
    
    def __init__(
        self,
        base_client: LLMClientProtocol,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retryable_errors: Optional[List[type]] = None
    ):
        self.base_client = base_client
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.retryable_errors = retryable_errors or [Exception]
        self.provider_name = base_client.provider_name
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text with retry logic"""
        delay = self.initial_delay
        
        for attempt in range(self.max_retries):
            try:
                return await self.base_client.generate_text(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"LLM call failed after {self.max_retries} attempts: {e}")
                    raise
                
                if any(isinstance(e, error_type) for error_type in self.retryable_errors):
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    # Non-retryable error
                    raise
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text with retry logic"""
        delay = self.initial_delay
        
        for attempt in range(self.max_retries):
            try:
                async for token in self.base_client.stream_text(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    **kwargs
                ):
                    yield token
                return  # Success
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"LLM stream failed after {self.max_retries} attempts: {e}")
                    raise
                
                if any(isinstance(e, error_type) for error_type in self.retryable_errors):
                    logger.warning(
                        f"LLM stream failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    raise
    
    async def close(self):
        """Close base client"""
        await self.base_client.close()

# Usage with agent
async def main():
    from aiecs.llm import OpenAIClient
    
    # Create base client
    base_client = OpenAIClient()
    
    # Wrap with retry logic
    retry_client = RetryLLMClient(
        base_client=base_client,
        max_retries=5,
        initial_delay=1.0,
        backoff_factor=2.0
    )
    
    # Use wrapped client with agent
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    
    agent = HybridAgent(
        agent_id="retry_agent",
        name="Retry Agent",
        llm_client=retry_client,  # Wrapped client works!
        tools=["search"],
        config=AgentConfiguration()
    )
    
    await agent.initialize()
    
    # Agent automatically retries on LLM failures
    result = await agent.execute_task(
        {"description": "Answer question"},
        {}
    )
    
    await agent.shutdown()
```

### Example 2: Caching Wrapper

LLM client wrapper that caches responses.

```python
from typing import List, Dict, Optional, AsyncIterator
from aiecs.llm.protocols import LLMClientProtocol
from aiecs.llm.models import LLMResponse
import hashlib
import json
import time
from collections import OrderedDict

class CachingLLMClient:
    """
    Wrapper that caches LLM responses to reduce API calls.
    
    This wrapper caches responses based on messages and parameters,
    with configurable TTL and cache size limits.
    """
    
    def __init__(
        self,
        base_client: LLMClientProtocol,
        ttl_seconds: int = 3600,
        max_cache_size: int = 1000
    ):
        self.base_client = base_client
        self.ttl_seconds = ttl_seconds
        self.max_cache_size = max_cache_size
        self.cache: OrderedDict[str, tuple[LLMResponse, float]] = OrderedDict()
        self.provider_name = base_client.provider_name
    
    def _cache_key(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs
    ) -> str:
        """Generate cache key from parameters"""
        key_data = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text with caching"""
        cache_key = self._cache_key(messages, model, temperature, max_tokens, **kwargs)
        
        # Check cache
        if cache_key in self.cache:
            response, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end (LRU)
                self.cache.move_to_end(cache_key)
                return response
            else:
                # Expired
                del self.cache[cache_key]
        
        # Call base client
        response = await self.base_client.generate_text(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Store in cache
        self.cache[cache_key] = (response, time.time())
        
        # Evict if cache too large
        if len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)  # Remove oldest
        
        return response
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text (not cached)"""
        # Streaming can't be cached easily, so just delegate
        async for token in self.base_client.stream_text(
            messages=messages,
            model=model,
            temperature=temperature,
            **kwargs
        ):
            yield token
    
    async def close(self):
        """Close base client"""
        await self.base_client.close()

# Usage with agent
async def main():
    from aiecs.llm import OpenAIClient
    
    # Create base client
    base_client = OpenAIClient()
    
    # Wrap with caching
    caching_client = CachingLLMClient(
        base_client=base_client,
        ttl_seconds=3600,  # Cache for 1 hour
        max_cache_size=500
    )
    
    # Use cached client with agent
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    
    agent = HybridAgent(
        agent_id="caching_agent",
        name="Caching Agent",
        llm_client=caching_client,  # Cached client
        tools=["search"],
        config=AgentConfiguration()
    )
    
    await agent.initialize()
    
    # First call - hits API
    result1 = await agent.execute_task(
        {"description": "What is Python?"},
        {}
    )
    
    # Second call with same question - uses cache!
    result2 = await agent.execute_task(
        {"description": "What is Python?"},
        {}
    )
    
    await agent.shutdown()
```

### Example 3: Custom LLM Provider

Complete custom LLM client implementation.

```python
from typing import List, Dict, Optional, AsyncIterator
from aiecs.llm.protocols import LLMClientProtocol
from aiecs.llm.models import LLMResponse, LLMUsage
import aiohttp
import json

class CustomLLMClient:
    """
    Custom LLM client for a hypothetical LLM provider.
    
    This demonstrates how to implement LLMClientProtocol without
    inheriting from BaseLLMClient.
    """
    
    provider_name = "custom_provider"
    
    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        default_model: str = "custom-model-v1"
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.default_model = default_model
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text from custom LLM provider"""
        session = await self._get_session()
        
        payload = {
            "messages": messages,
            "model": model or self.default_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        async with session.post(
            f"{self.api_endpoint}/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            data = await response.json()
            
            return LLMResponse(
                text=data["text"],
                model=data.get("model", self.default_model),
                usage=LLMUsage(
                    prompt_tokens=data.get("usage", {}).get("prompt_tokens", 0),
                    completion_tokens=data.get("usage", {}).get("completion_tokens", 0),
                    total_tokens=data.get("usage", {}).get("total_tokens", 0)
                )
            )
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream text from custom LLM provider"""
        session = await self._get_session()
        
        payload = {
            "messages": messages,
            "model": model or self.default_model,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        
        async with session.post(
            f"{self.api_endpoint}/stream",
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.content:
                if line:
                    data = json.loads(line)
                    if "text" in data:
                        yield data["text"]
    
    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None

# Usage with agent
async def main():
    # Create custom LLM client
    custom_client = CustomLLMClient(
        api_endpoint="https://api.custom-llm.com",
        api_key="your-api-key",
        default_model="custom-model-v1"
    )
    
    # Use directly with agent - no adapter needed!
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    
    agent = HybridAgent(
        agent_id="custom_agent",
        name="Custom LLM Agent",
        llm_client=custom_client,  # Custom client works directly!
        tools=["search"],
        config=AgentConfiguration()
    )
    
    await agent.initialize()
    
    result = await agent.execute_task(
        {"description": "Answer question"},
        {}
    )
    
    await agent.shutdown()
    await custom_client.close()
```

## Config Managers

### Example 1: Database Config Manager

Config manager that loads from database.

```python
from typing import Any, Optional
from aiecs.domain.agent.integration import ConfigManagerProtocol
import asyncpg
import json

class DatabaseConfigManager:
    """
    Config manager that loads configuration from a database.
    
    This allows dynamic configuration updates without restarting agents.
    """
    
    def __init__(self, database_url: str, table_name: str = "agent_configs"):
        self.database_url = database_url
        self.table_name = table_name
        self._pool: Optional[asyncpg.Pool] = None
        self._cache: Dict[str, Any] = {}
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.database_url)
        return self._pool
    
    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from database"""
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT value FROM {self.table_name} WHERE key = $1",
                key
            )
            
            if row:
                value = json.loads(row["value"])
                self._cache[key] = value
                return value
        
        return default
    
    async def set_config(self, key: str, value: Any) -> None:
        """Set configuration value in database"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (key, value)
                VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = $2
                """,
                key,
                json.dumps(value)
            )
        
        # Update cache
        self._cache[key] = value
    
    async def reload_config(self) -> None:
        """Reload all configuration from database"""
        self._cache.clear()
        # Cache will be repopulated on next get_config call

# Usage with agent
async def main():
    # Create config manager
    config_manager = DatabaseConfigManager(
        database_url="postgresql://user:pass@localhost/db"
    )
    
    # Create agent with config manager
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="db_config_agent",
        name="DB Config Agent",
        llm_client=OpenAIClient(),
        tools=["search"],
        config=AgentConfiguration(),  # Base config
        config_manager=config_manager  # Dynamic config manager
    )
    
    await agent.initialize()
    
    # Update config at runtime
    await config_manager.set_config("goal", "New goal from database")
    await config_manager.reload_config()
    
    # Agent can access updated config
    goal = await agent.get_config_manager().get_config("goal")
    print(f"Current goal: {goal}")
    
    await agent.shutdown()
```

### Example 2: Redis Config Manager

Config manager that uses Redis for distributed configuration.

```python
from typing import Any, Optional
from aiecs.domain.agent.integration import ConfigManagerProtocol
import redis.asyncio as redis
import json

class RedisConfigManager:
    """
    Config manager that uses Redis for distributed configuration.
    
    This allows multiple agents to share configuration across instances.
    """
    
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "agent:config:"
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url)
        return self._redis
    
    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from Redis"""
        r = await self._get_redis()
        value = await r.get(f"{self.key_prefix}{key}")
        
        if value:
            return json.loads(value)
        return default
    
    async def set_config(self, key: str, value: Any) -> None:
        """Set configuration value in Redis"""
        r = await self._get_redis()
        await r.set(
            f"{self.key_prefix}{key}",
            json.dumps(value)
        )
    
    async def reload_config(self) -> None:
        """Reload config (no-op for Redis, always fresh)"""
        pass
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()

# Usage with agent
async def main():
    # Create Redis config manager
    config_manager = RedisConfigManager(
        redis_url="redis://localhost:6379"
    )
    
    # Create agent with Redis config
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="redis_config_agent",
        name="Redis Config Agent",
        llm_client=OpenAIClient(),
        tools=["search"],
        config=AgentConfiguration(),
        config_manager=config_manager
    )
    
    await agent.initialize()
    
    # Set config in Redis
    await config_manager.set_config("temperature", 0.9)
    
    # Other agents can read same config
    temperature = await config_manager.get_config("temperature")
    
    await agent.shutdown()
    await config_manager.close()
```

## Checkpointers

### Example 1: File-Based Checkpointer

Simple file-based checkpointer for single-instance deployments.

```python
from typing import Dict, Any, Optional
from aiecs.domain.agent.integration import CheckpointerProtocol
import json
import os
from pathlib import Path
import uuid

class FileCheckpointer:
    """
    File-based checkpointer for saving agent state.
    
    This is suitable for single-instance deployments where
    state persistence to disk is sufficient.
    """
    
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _checkpoint_path(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Path:
        """Get checkpoint file path"""
        if checkpoint_id:
            filename = f"{agent_id}_{session_id}_{checkpoint_id}.json"
        else:
            # Latest checkpoint
            pattern = f"{agent_id}_{session_id}_*.json"
            checkpoints = list(self.checkpoint_dir.glob(pattern))
            if checkpoints:
                # Return most recent
                return max(checkpoints, key=lambda p: p.stat().st_mtime)
            filename = f"{agent_id}_{session_id}_latest.json"
        
        return self.checkpoint_dir / filename
    
    async def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint to file"""
        checkpoint_id = str(uuid.uuid4())
        path = self._checkpoint_path(agent_id, session_id, checkpoint_id)
        
        with open(path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)
        
        return checkpoint_id
    
    async def load_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from file"""
        path = self._checkpoint_path(agent_id, session_id, checkpoint_id)
        
        if not path.exists():
            return None
        
        with open(path, "r") as f:
            return json.load(f)
    
    async def list_checkpoints(
        self,
        agent_id: str,
        session_id: str
    ) -> list[str]:
        """List all checkpoint IDs for agent and session"""
        pattern = f"{agent_id}_{session_id}_*.json"
        checkpoints = list(self.checkpoint_dir.glob(pattern))
        
        # Extract checkpoint IDs
        checkpoint_ids = []
        for checkpoint in checkpoints:
            parts = checkpoint.stem.split("_")
            if len(parts) >= 3:
                checkpoint_ids.append("_".join(parts[2:]))
        
        return checkpoint_ids

# Usage with agent
async def main():
    # Create file checkpointer
    checkpointer = FileCheckpointer(checkpoint_dir="./agent_checkpoints")
    
    # Create agent with checkpointing
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="checkpoint_agent",
        name="Checkpoint Agent",
        llm_client=OpenAIClient(),
        tools=["search"],
        config=AgentConfiguration(),
        checkpointer=checkpointer
    )
    
    await agent.initialize()
    
    # Save checkpoint
    checkpoint_id = await agent.save_checkpoint("session-123")
    print(f"Saved checkpoint: {checkpoint_id}")
    
    # Load checkpoint
    state = await agent.load_checkpoint("session-123", checkpoint_id)
    print(f"Loaded checkpoint: {state}")
    
    # List checkpoints
    checkpoints = await agent.list_checkpoints("session-123")
    print(f"Available checkpoints: {checkpoints}")
    
    await agent.shutdown()
```

### Example 2: Redis Checkpointer

Redis-based checkpointer for distributed systems.

```python
from typing import Dict, Any, Optional
from aiecs.domain.agent.integration import CheckpointerProtocol
import redis.asyncio as redis
import json
import uuid
from datetime import timedelta

class RedisCheckpointer:
    """
    Redis-based checkpointer for distributed agent deployments.
    
    This allows multiple agent instances to share checkpoints
    and supports TTL-based expiration.
    """
    
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "checkpoint:",
        default_ttl: int = 3600  # 1 hour
    ):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = await redis.from_url(self.redis_url)
        return self._redis
    
    def _checkpoint_key(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """Get Redis key for checkpoint"""
        if checkpoint_id:
            return f"{self.key_prefix}{agent_id}:{session_id}:{checkpoint_id}"
        return f"{self.key_prefix}{agent_id}:{session_id}:latest"
    
    async def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint to Redis"""
        checkpoint_id = str(uuid.uuid4())
        r = await self._get_redis()
        
        key = self._checkpoint_key(agent_id, session_id, checkpoint_id)
        latest_key = self._checkpoint_key(agent_id, session_id)
        
        # Save checkpoint
        await r.setex(
            key,
            self.default_ttl,
            json.dumps(checkpoint_data)
        )
        
        # Update latest checkpoint reference
        await r.setex(
            latest_key,
            self.default_ttl,
            checkpoint_id
        )
        
        return checkpoint_id
    
    async def load_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from Redis"""
        r = await self._get_redis()
        
        if checkpoint_id is None:
            # Load latest checkpoint ID
            latest_key = self._checkpoint_key(agent_id, session_id)
            checkpoint_id = await r.get(latest_key)
            if checkpoint_id:
                checkpoint_id = checkpoint_id.decode()
            else:
                return None
        
        # Load checkpoint data
        key = self._checkpoint_key(agent_id, session_id, checkpoint_id)
        data = await r.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def list_checkpoints(
        self,
        agent_id: str,
        session_id: str
    ) -> list[str]:
        """List all checkpoint IDs for agent and session"""
        r = await self._get_redis()
        pattern = f"{self.key_prefix}{agent_id}:{session_id}:*"
        
        keys = []
        async for key in r.scan_iter(match=pattern):
            key_str = key.decode()
            # Extract checkpoint ID (skip "latest")
            parts = key_str.split(":")
            if len(parts) >= 4 and parts[-1] != "latest":
                keys.append(parts[-1])
        
        return keys
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()

# Usage with agent
async def main():
    # Create Redis checkpointer
    checkpointer = RedisCheckpointer(
        redis_url="redis://localhost:6379",
        default_ttl=7200  # 2 hours
    )
    
    # Create agent with Redis checkpointing
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    from aiecs.llm import OpenAIClient
    
    agent = HybridAgent(
        agent_id="redis_checkpoint_agent",
        name="Redis Checkpoint Agent",
        llm_client=OpenAIClient(),
        tools=["search"],
        config=AgentConfiguration(),
        checkpointer=checkpointer
    )
    
    await agent.initialize()
    
    # Save checkpoint (shared across instances)
    checkpoint_id = await agent.save_checkpoint("session-123")
    
    # Load checkpoint from any instance
    state = await agent.load_checkpoint("session-123", checkpoint_id)
    
    await agent.shutdown()
    await checkpointer.close()
```

## Complete Integration Examples

### Example: MasterController Integration

Complete example integrating agents with MasterController.

```python
from aiecs.domain.execution.master_controller import MasterController
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.domain.context import ContextEngine
from aiecs.tools import ReadContextTool

async def create_master_controller_agent():
    """Create agent integrated with MasterController"""
    
    # Initialize MasterController
    master_controller = MasterController(...)
    await master_controller.initialize()
    
    # Create tools with MasterController dependencies
    read_context_tool = ReadContextTool(
        context_engine=master_controller.context_engine
    )
    
    # Create agent with MasterController's LLM manager
    agent = HybridAgent(
        agent_id="master_controller_agent",
        name="Master Controller Agent",
        llm_client=master_controller.llm_manager,  # Direct integration!
        tools={
            "read_context": read_context_tool  # Stateful tool
        },
        config=AgentConfiguration(
            goal="Assist with MasterController tasks"
        ),
        context_engine=master_controller.context_engine  # Persistent memory
    )
    
    await agent.initialize()
    return agent

# Usage
async def main():
    agent = await create_master_controller_agent()
    
    result = await agent.execute_task(
        {"description": "Read context and answer question"},
        {"session_id": "user-123"}
    )
    
    await agent.shutdown()
```

### Example: Production Agent Setup

Complete production-ready agent setup with all features.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration, CacheConfig
from aiecs.domain.agent.models import ResourceLimits, RecoveryStrategy
from aiecs.domain.context import ContextEngine, CompressionConfig
from aiecs.llm import OpenAIClient
from aiecs.tools import BaseTool
import redis.asyncio as redis

async def create_production_agent():
    """Create production-ready agent with all features"""
    
    # 1. LLM client with retry and caching
    base_client = OpenAIClient()
    retry_client = RetryLLMClient(base_client, max_retries=5)
    caching_client = CachingLLMClient(retry_client, ttl_seconds=3600)
    
    # 2. ContextEngine with compression
    compression_config = CompressionConfig(
        strategy="summarize",
        auto_compress_enabled=True,
        auto_compress_threshold=50
    )
    context_engine = ContextEngine(compression_config=compression_config)
    await context_engine.initialize()
    
    # 3. Stateful tools
    db_tool = DatabaseQueryTool(database_url="...")
    service_tool = ServiceCallTool(base_url="...", api_key="...")
    
    # 4. Config manager (Redis)
    config_manager = RedisConfigManager(redis_url="redis://localhost:6379")
    
    # 5. Checkpointer (Redis)
    checkpointer = RedisCheckpointer(redis_url="redis://localhost:6379")
    
    # 6. Cache config for tools
    cache_config = CacheConfig(
        enabled=True,
        default_ttl=300,
        tool_specific_ttl={"search": 600}
    )
    
    # 7. Resource limits
    resource_limits = ResourceLimits(
        max_requests_per_minute=60,
        max_tokens_per_request=4000
    )
    
    # 8. Create agent with all features
    agent = HybridAgent(
        agent_id="production_agent",
        name="Production Agent",
        llm_client=caching_client,  # Cached and retried
        tools={
            "database_query": db_tool,
            "service_call": service_tool
        },
        config=AgentConfiguration(
            goal="Handle production tasks"
        ),
        context_engine=context_engine,  # Persistent memory
        config_manager=config_manager,  # Dynamic config
        checkpointer=checkpointer,  # State persistence
        cache_config=cache_config,  # Tool caching
        resource_limits=resource_limits,  # Rate limiting
        recovery_strategies=[
            RecoveryStrategy.RETRY,
            RecoveryStrategy.FALLBACK_TOOL
        ],
        enable_parallel_execution=True,  # Parallel tools
        enable_streaming=True  # Streaming responses
    )
    
    await agent.initialize()
    return agent

# Usage
async def main():
    agent = await create_production_agent()
    
    # Agent has all production features enabled
    result = await agent.execute_task(
        {"description": "Complex production task"},
        {"session_id": "user-123"}
    )
    
    # Monitor health
    health = agent.get_health_status()
    print(f"Health: {health.status}, Score: {health.health_score}")
    
    # Get metrics
    metrics = agent.get_metrics()
    print(f"Success rate: {metrics.success_rate}")
    
    await agent.shutdown()
```

## Summary

These examples demonstrate:

1. **Stateful Tools**: Tools with dependencies (database, ContextEngine, services)
2. **Custom LLM Clients**: Retry wrappers, caching wrappers, custom providers
3. **Config Managers**: Database and Redis-based dynamic configuration
4. **Checkpointers**: File-based and Redis-based state persistence
5. **Complete Integration**: Production-ready setups with all features

All examples are production-ready and can be adapted to your specific use cases.

