"""
ContextEngine: Advanced Context and Session Management Engine

This engine extends TaskContext capabilities to provide comprehensive
session management, conversation tracking, and persistent storage for BaseAIService.

Key Features:
1. Multi-session management (extends TaskContext from single task to multiple sessions)
2. Redis backend storage for persistence and scalability
3. Conversation history management with optimization
4. Performance metrics and analytics
5. Resource and lifecycle management
6. Integration with BaseServiceCheckpointer
"""

from aiecs.core.interface.storage_interface import (
    IStorageBackend,
    ICheckpointerBackend,
)
from aiecs.domain.task.task_context import TaskContext, ContextUpdate
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, is_dataclass


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Import TaskContext for base functionality

# Import core storage interfaces

# Redis client import - use existing infrastructure
try:
    import redis.asyncio as redis
    from aiecs.infrastructure.persistence.redis_client import get_redis_client

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    get_redis_client = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Session-level performance metrics."""

    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    request_count: int = 0
    error_count: int = 0
    total_processing_time: float = 0.0
    status: str = "active"  # active, completed, failed, expired

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetrics":
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)


@dataclass
class ConversationMessage:
    """Structured conversation message."""

    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class CompressionConfig:
    """
    Configuration for conversation compression.

    Provides flexible control over compression behavior with multiple strategies
    to manage conversation history size and reduce token usage.

    **Compression Strategies:**
    - truncate: Fast truncation, keeps most recent N messages (no LLM required)
    - summarize: LLM-based summarization of older messages
    - semantic: Embedding-based deduplication of similar messages
    - hybrid: Combination of multiple strategies applied sequentially

    **Key Features:**
    - Automatic compression triggers based on message count
    - Custom prompt templates for summarization
    - Configurable similarity thresholds for semantic deduplication
    - Performance timeouts to prevent long-running operations

    Attributes:
        strategy: Compression strategy to use. One of: "truncate", "summarize", "semantic", "hybrid"
        max_messages: Maximum messages to keep (for truncation strategy)
        keep_recent: Always keep N most recent messages (applies to all strategies)
        summary_prompt_template: Custom prompt template for summarization (uses {messages} placeholder)
        summary_max_tokens: Maximum tokens for summary output
        include_summary_in_history: Whether to add summary as system message in history
        similarity_threshold: Similarity threshold for semantic deduplication (0.0-1.0)
        embedding_model: Embedding model name for semantic deduplication
        hybrid_strategies: List of strategies to combine for hybrid mode (default: ["truncate", "summarize"])
        auto_compress_enabled: Enable automatic compression when threshold exceeded
        auto_compress_threshold: Message count threshold to trigger auto-compression
        auto_compress_target: Target message count after auto-compression
        compression_timeout: Maximum time for compression operation in seconds

    Examples:
        # Example 1: Basic truncation configuration
        config = CompressionConfig(
            strategy="truncate",
            max_messages=50,
            keep_recent=10
        )

        # Example 2: LLM-based summarization
        config = CompressionConfig(
            strategy="summarize",
            keep_recent=10,
            summary_max_tokens=500,
            include_summary_in_history=True
        )

        # Example 3: Semantic deduplication
        config = CompressionConfig(
            strategy="semantic",
            keep_recent=10,
            similarity_threshold=0.95,
            embedding_model="text-embedding-ada-002"
        )

        # Example 4: Hybrid strategy (truncate then summarize)
        config = CompressionConfig(
            strategy="hybrid",
            hybrid_strategies=["truncate", "summarize"],
            keep_recent=10,
            summary_max_tokens=500
        )

        # Example 5: Auto-compression enabled
        config = CompressionConfig(
            auto_compress_enabled=True,
            auto_compress_threshold=100,
            auto_compress_target=50,
            strategy="summarize",
            keep_recent=10
        )

        # Example 6: Custom summarization prompt
        config = CompressionConfig(
            strategy="summarize",
            summary_prompt_template=(
                "Summarize the following conversation focusing on "
                "key decisions and action items:\n\n{messages}"
            ),
            summary_max_tokens=300
        )
    """

    # Strategy selection
    strategy: str = "truncate"  # truncate, summarize, semantic, hybrid

    # Truncation settings
    max_messages: int = 50  # Maximum messages to keep
    keep_recent: int = 10  # Always keep N most recent messages

    # Summarization settings (LLM-based)
    summary_prompt_template: Optional[str] = None  # Custom prompt template
    summary_max_tokens: int = 500  # Max tokens for summary
    include_summary_in_history: bool = True  # Add summary as system message

    # Semantic deduplication settings (embedding-based)
    similarity_threshold: float = 0.95  # Messages above this similarity are duplicates
    embedding_model: str = "text-embedding-ada-002"  # Embedding model to use

    # Hybrid strategy settings
    hybrid_strategies: Optional[List[str]] = None  # Strategies to combine (default: ["truncate", "summarize"])

    # Auto-compression triggers
    auto_compress_enabled: bool = False  # Enable automatic compression
    auto_compress_threshold: int = 100  # Trigger when message count exceeds this
    auto_compress_target: int = 50  # Target message count after compression

    # Performance settings
    compression_timeout: float = 30.0  # Max time for compression operation (seconds)

    def __post_init__(self):
        """Validate and set defaults."""
        if self.hybrid_strategies is None:
            self.hybrid_strategies = ["truncate", "summarize"]

        # Validate strategy
        valid_strategies = ["truncate", "summarize", "semantic", "hybrid"]
        if self.strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{self.strategy}'. " f"Must be one of: {', '.join(valid_strategies)}")


class ContextEngine(IStorageBackend, ICheckpointerBackend):
    """
    Advanced Context and Session Management Engine.

    Implements core storage interfaces to provide comprehensive session management
    with Redis backend storage for BaseAIService and BaseServiceCheckpointer.

    This implementation follows the middleware's core interface pattern,
    enabling dependency inversion and clean architecture.

    **Key Features:**
    - Multi-session management with Redis backend
    - Conversation history management with compression
    - Performance metrics and analytics
    - Resource and lifecycle management
    - Integration with BaseServiceCheckpointer

    **Compression Strategies:**
    - truncate: Fast truncation (no LLM required)
    - summarize: LLM-based summarization
    - semantic: Embedding-based deduplication
    - hybrid: Combination of multiple strategies

    Examples:
        # Example 1: Basic ContextEngine initialization
        engine = ContextEngine()
        await engine.initialize()

        # Create session
        session = await engine.create_session(
            session_id="session-123",
            user_id="user-456"
        )

        # Add conversation messages
        await engine.add_conversation_message(
            session_id="session-123",
            role="user",
            content="Hello, I need help"
        )

        # Example 2: ContextEngine with compression (truncation strategy)
        from aiecs.domain.context.context_engine import CompressionConfig

        compression_config = CompressionConfig(
            strategy="truncate",
            max_messages=50,
            keep_recent=10  # Always keep 10 most recent messages
        )

        engine = ContextEngine(compression_config=compression_config)
        await engine.initialize()

        # Add many messages
        for i in range(100):
            await engine.add_conversation_message(
                session_id="session-123",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )

        # Compress conversation (truncates to 10 most recent)
        result = await engine.compress_conversation("session-123")
        print(f"Compressed from {result['original_count']} to {result['compressed_count']} messages")

        # Example 3: ContextEngine with LLM-based summarization
        from aiecs.llm import OpenAIClient

        llm_client = OpenAIClient()

        compression_config = CompressionConfig(
            strategy="summarize",
            keep_recent=10,  # Keep 10 most recent messages
            summary_max_tokens=500,
            include_summary_in_history=True
        )

        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=llm_client  # Required for summarization
        )
        await engine.initialize()

        # Add conversation
        for i in range(50):
            await engine.add_conversation_message(
                session_id="session-123",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}: Important information about topic {i % 5}"
            )

        # Compress using summarization
        result = await engine.compress_conversation("session-123", strategy="summarize")
        print(f"Compressed: {result['original_count']} -> {result['compressed_count']} messages")
        print(f"Compression ratio: {result['compression_ratio']:.1%}")

        # Example 4: ContextEngine with semantic deduplication
        compression_config = CompressionConfig(
            strategy="semantic",
            keep_recent=10,
            similarity_threshold=0.95,  # Remove messages >95% similar
            embedding_model="text-embedding-ada-002"
        )

        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=llm_client  # Required for embeddings
        )
        await engine.initialize()

        # Add conversation with similar messages
        messages = [
            "What's the weather?",
            "What's the weather today?",
            "Tell me about the weather",
            "What's the temperature?"
        ]
        for msg in messages:
            await engine.add_conversation_message(
                session_id="session-123",
                role="user",
                content=msg
            )

        # Compress using semantic deduplication
        result = await engine.compress_conversation("session-123", strategy="semantic")
        print(f"Removed {result['original_count'] - result['compressed_count']} similar messages")

        # Example 5: ContextEngine with hybrid compression
        compression_config = CompressionConfig(
            strategy="hybrid",
            hybrid_strategies=["truncate", "summarize"],  # Apply truncate then summarize
            keep_recent=10,
            summary_max_tokens=500
        )

        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=llm_client
        )
        await engine.initialize()

        # Compress using hybrid strategy
        result = await engine.compress_conversation("session-123", strategy="hybrid")

        # Example 6: Auto-compression on message limit
        compression_config = CompressionConfig(
            auto_compress_enabled=True,
            auto_compress_threshold=100,  # Trigger at 100 messages
            auto_compress_target=50,  # Compress to 50 messages
            strategy="summarize",
            keep_recent=10
        )

        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=llm_client
        )
        await engine.initialize()

        # Add messages - auto-compression triggers at 100
        for i in range(105):
            await engine.add_conversation_message(
                session_id="session-123",
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )

            # Check if auto-compression was triggered
            result = await engine.auto_compress_on_limit("session-123")
            if result:
                print(f"Auto-compressed: {result['original_count']} -> {result['compressed_count']}")

        # Example 7: Custom compression prompt template
        compression_config = CompressionConfig(
            strategy="summarize",
            summary_prompt_template=(
                "Summarize the following conversation focusing on key decisions, "
                "action items, and important facts. Keep it concise:\n\n{messages}"
            ),
            summary_max_tokens=300
        )

        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=llm_client
        )
        await engine.initialize()

        # Compress with custom prompt
        result = await engine.compress_conversation("session-123")

        # Example 8: Get compressed context in different formats
        engine = ContextEngine(compression_config=compression_config, llm_client=llm_client)
        await engine.initialize()

        # Get as formatted string
        context_string = await engine.get_compressed_context(
            session_id="session-123",
            format="string",
            compress_first=True  # Compress before returning
        )
        print(context_string)

        # Get as messages list
        messages = await engine.get_compressed_context(
            session_id="session-123",
            format="messages",
            compress_first=False  # Use existing compressed version
        )

        # Get as dictionary
        context_dict = await engine.get_compressed_context(
            session_id="session-123",
            format="dict"
        )

        # Example 9: Runtime compression config override
        engine = ContextEngine(
            compression_config=CompressionConfig(strategy="truncate"),
            llm_client=llm_client
        )
        await engine.initialize()

        # Override compression config for specific operation
        custom_config = CompressionConfig(
            strategy="summarize",
            summary_max_tokens=1000
        )

        result = await engine.compress_conversation(
            session_id="session-123",
            config_override=custom_config
        )

        # Example 10: Compression with custom LLM client
        class CustomLLMClient:
            provider_name = "custom"

            async def generate_text(self, messages, **kwargs):
                # Custom summarization logic
                return LLMResponse(content="Custom summary...")

            async def get_embeddings(self, texts, model):
                # Custom embedding logic
                return [[0.1] * 1536 for _ in texts]

        custom_llm = CustomLLMClient()

        compression_config = CompressionConfig(strategy="semantic")
        engine = ContextEngine(
            compression_config=compression_config,
            llm_client=custom_llm  # Custom LLM client for compression
        )
        await engine.initialize()

        # Compress using custom LLM client
        result = await engine.compress_conversation("session-123", strategy="semantic")
    """

    def __init__(
        self,
        use_existing_redis: bool = True,
        compression_config: Optional[CompressionConfig] = None,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize ContextEngine.

        Args:
            use_existing_redis: Whether to use the existing Redis client from infrastructure
                              (已弃用: 现在总是创建独立的 RedisClient 实例以避免事件循环冲突)
            compression_config: Optional compression configuration for conversation compression
            llm_client: Optional LLM client for summarization and embeddings (must implement LLMClientProtocol)
        """
        self.use_existing_redis = use_existing_redis
        self.redis_client: Optional[redis.Redis] = None
        self._redis_client_wrapper: Optional[Any] = None  # RedisClient 包装器实例

        # Fallback to memory storage if Redis not available
        self._memory_sessions: Dict[str, SessionMetrics] = {}
        self._memory_conversations: Dict[str, List[ConversationMessage]] = {}
        self._memory_contexts: Dict[str, TaskContext] = {}
        self._memory_checkpoints: Dict[str, Dict[str, Any]] = {}

        # Configuration
        self.session_ttl = 3600 * 24  # 24 hours default TTL
        self.conversation_limit = 1000  # Max messages per conversation
        self.checkpoint_ttl = 3600 * 24 * 7  # 7 days for checkpoints

        # Compression configuration (Phase 6)
        self.compression_config = compression_config or CompressionConfig()
        self.llm_client = llm_client

        # Metrics
        self._global_metrics = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_messages": 0,
            "total_checkpoints": 0,
        }

        logger.info(f"ContextEngine initialized with compression strategy: {self.compression_config.strategy}")

    async def initialize(self) -> bool:
        """Initialize Redis connection and validate setup."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using memory storage")
            return True

        try:
            # ✅ 修复方案：在当前事件循环中创建新的 RedisClient 实例
            #
            # 问题根源：
            # - 全局 RedisClient 单例在应用启动的事件循环A中创建
            # - ContextEngine 可能在不同的事件循环B中被初始化（例如在请求处理中）
            # - redis.asyncio 的连接池绑定到创建时的事件循环
            # - 跨事件循环使用会导致 "Task got Future attached to a different loop" 错误
            #
            # 解决方案：
            # - 为每个 ContextEngine 实例创建独立的 RedisClient
            # - 使用 RedisClient 包装器保持架构一致性
            # - 在当前事件循环中初始化，确保事件循环匹配

            from aiecs.infrastructure.persistence.redis_client import (
                RedisClient,
            )

            # 创建专属的 RedisClient 实例（在当前事件循环中）
            self._redis_client_wrapper = RedisClient()
            await self._redis_client_wrapper.initialize()

            # 获取底层 redis.Redis 客户端用于现有代码
            self.redis_client = await self._redis_client_wrapper.get_client()

            # Test connection
            await self.redis_client.ping()
            logger.info("ContextEngine connected to Redis successfully using RedisClient wrapper in current event loop")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to memory storage")
            self.redis_client = None
            self._redis_client_wrapper = None
            return False

    async def close(self):
        """Close Redis connection."""
        if hasattr(self, "_redis_client_wrapper") and self._redis_client_wrapper:
            # 使用 RedisClient 包装器的 close 方法
            await self._redis_client_wrapper.close()
            self._redis_client_wrapper = None
            self.redis_client = None
        elif self.redis_client:
            # 兼容性处理：直接关闭 redis 客户端
            await self.redis_client.close()
            self.redis_client = None

    # ==================== Session Management ====================

    async def create_session(self, session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new session."""
        now = datetime.utcnow()
        session = SessionMetrics(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
        )

        # Store session
        await self._store_session(session)

        # Create associated TaskContext
        task_context = TaskContext(
            {
                "user_id": user_id,
                "chat_id": session_id,
                "metadata": metadata or {},
            }
        )
        await self._store_task_context(session_id, task_context)

        # Update metrics
        self._global_metrics["total_sessions"] += 1
        self._global_metrics["active_sessions"] += 1

        logger.info(f"Created session {session_id} for user {user_id}")
        return session.to_dict()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        if self.redis_client:
            try:
                data = await self.redis_client.hget("sessions", session_id)  # type: ignore[misc]
                if data:
                    session = SessionMetrics.from_dict(json.loads(data))
                    return session.to_dict()
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")

        # Fallback to memory
        memory_session: Optional[SessionMetrics] = self._memory_sessions.get(session_id)
        return memory_session.to_dict() if memory_session else None

    async def update_session(
        self,
        session_id: str,
        updates: Optional[Dict[str, Any]] = None,
        increment_requests: bool = False,
        add_processing_time: float = 0.0,
        mark_error: bool = False,
    ) -> bool:
        """Update session with activity and metrics."""
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        # Convert dict to SessionMetrics if needed
        session: SessionMetrics
        if isinstance(session_data, dict):
            session = SessionMetrics.from_dict(session_data)
        else:
            session = session_data

        # Update activity
        session.last_activity = datetime.utcnow()

        # Update metrics
        if increment_requests:
            session.request_count += 1
        if add_processing_time > 0:
            session.total_processing_time += add_processing_time
        if mark_error:
            session.error_count += 1

        # Apply custom updates
        if updates:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)

        # Store updated session
        await self._store_session(session)
        return True

    async def end_session(self, session_id: str, status: str = "completed") -> bool:
        """End a session and update metrics."""
        session_data = await self.get_session(session_id)
        if not session_data:
            return False

        # Convert dict to SessionMetrics if needed
        session = SessionMetrics.from_dict(session_data) if isinstance(session_data, dict) else session_data
        session.status = status
        session.last_activity = datetime.utcnow()

        # Store final state
        await self._store_session(session)

        # Update global metrics
        self._global_metrics["active_sessions"] = max(0, self._global_metrics["active_sessions"] - 1)

        logger.info(f"Ended session {session_id} with status: {status}")
        return True

    async def _store_session(self, session: SessionMetrics):
        """Store session to Redis or memory."""
        if self.redis_client:
            try:
                await self.redis_client.hset(  # type: ignore[misc]
                    "sessions",
                    session.session_id,
                    json.dumps(session.to_dict(), cls=DateTimeEncoder),
                )
                await self.redis_client.expire("sessions", self.session_ttl)  # type: ignore[misc]
                return
            except Exception as e:
                logger.error(f"Failed to store session to Redis: {e}")

        # Fallback to memory
        self._memory_sessions[session.session_id] = session

    # ==================== Conversation Management ====================

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add message to conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

        # Store message
        await self._store_conversation_message(session_id, message)

        # Update session activity
        await self.update_session(session_id)

        # Update global metrics
        self._global_metrics["total_messages"] += 1

        return True

    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        if self.redis_client:
            try:
                messages_data = await self.redis_client.lrange(f"conversation:{session_id}", -limit, -1)  # type: ignore[misc]
                # Since lpush adds to the beginning, we need to reverse to get
                # chronological order
                messages = [ConversationMessage.from_dict(json.loads(msg)) for msg in reversed(messages_data)]
                return [msg.to_dict() for msg in messages]
            except Exception as e:
                logger.error(f"Failed to get conversation from Redis: {e}")

        # Fallback to memory
        messages = self._memory_conversations.get(session_id, [])
        message_list = messages[-limit:] if limit > 0 else messages
        return [msg.to_dict() for msg in message_list]

    async def _store_conversation_message(self, session_id: str, message: ConversationMessage):
        """Store conversation message to Redis or memory."""
        if self.redis_client:
            try:
                # Add to list
                await self.redis_client.lpush(  # type: ignore[misc]
                    f"conversation:{session_id}",
                    json.dumps(message.to_dict(), cls=DateTimeEncoder),
                )
                # Trim to limit
                await self.redis_client.ltrim(f"conversation:{session_id}", -self.conversation_limit, -1)  # type: ignore[misc]
                # Set TTL
                await self.redis_client.expire(f"conversation:{session_id}", self.session_ttl)
                return
            except Exception as e:
                logger.error(f"Failed to store message to Redis: {e}")

        # Fallback to memory
        if session_id not in self._memory_conversations:
            self._memory_conversations[session_id] = []

        self._memory_conversations[session_id].append(message)

        # Trim to limit
        if len(self._memory_conversations[session_id]) > self.conversation_limit:
            self._memory_conversations[session_id] = self._memory_conversations[session_id][-self.conversation_limit :]

    # ==================== TaskContext Integration ====================

    async def get_task_context(self, session_id: str) -> Optional[TaskContext]:
        """Get TaskContext for a session."""
        if self.redis_client:
            try:
                data = await self.redis_client.hget("task_contexts", session_id)  # type: ignore[misc]
                if data:
                    context_data = json.loads(data)
                    # Reconstruct TaskContext from stored data
                    return self._reconstruct_task_context(context_data)
            except Exception as e:
                logger.error(f"Failed to get TaskContext from Redis: {e}")

        # Fallback to memory
        return self._memory_contexts.get(session_id)

    def _sanitize_dataclasses(self, obj: Any) -> Any:
        """
        Recursively convert dataclasses to dictionaries for JSON serialization.

        This method handles:
        - Dataclass instances -> dict (via asdict)
        - Nested dataclasses in dictionaries
        - Nested dataclasses in lists
        - Other types -> pass through

        Args:
            obj: Object to sanitize

        Returns:
            Sanitized object (JSON-serializable)
        """
        # Handle dataclass instances
        if is_dataclass(obj) and not isinstance(obj, type):
            logger.debug(f"Converting dataclass {type(obj).__name__} to dict for serialization")
            # Convert dataclass to dict and recursively sanitize
            return self._sanitize_dataclasses(asdict(obj))

        # Handle dictionaries
        if isinstance(obj, dict):
            return {key: self._sanitize_dataclasses(value) for key, value in obj.items()}

        # Handle lists and tuples
        if isinstance(obj, (list, tuple)):
            sanitized_list = [self._sanitize_dataclasses(item) for item in obj]
            return sanitized_list if isinstance(obj, list) else tuple(sanitized_list)

        # Handle sets
        if isinstance(obj, set):
            return [self._sanitize_dataclasses(item) for item in obj]

        # All other types pass through
        return obj

    async def _store_task_context(self, session_id: str, context: TaskContext):
        """
        Store TaskContext to Redis or memory.

        Automatically converts dataclasses to dictionaries to ensure
        JSON serialization compatibility.
        """
        if self.redis_client:
            try:
                # Get context dict and sanitize dataclasses
                context_dict = context.to_dict()
                sanitized_dict = self._sanitize_dataclasses(context_dict)

                await self.redis_client.hset(  # type: ignore[misc]
                    "task_contexts",
                    session_id,
                    json.dumps(sanitized_dict, cls=DateTimeEncoder),
                )
                await self.redis_client.expire("task_contexts", self.session_ttl)  # type: ignore[misc]
                return
            except Exception as e:
                logger.error(f"Failed to store TaskContext to Redis: {e}")

        # Fallback to memory
        self._memory_contexts[session_id] = context

    def _reconstruct_task_context(self, data: Dict[str, Any]) -> TaskContext:
        """Reconstruct TaskContext from stored data."""
        # Create new TaskContext with stored data
        context = TaskContext(data)

        # Restore context history
        if "context_history" in data:
            context.context_history = [
                ContextUpdate(
                    timestamp=entry["timestamp"],
                    update_type=entry["update_type"],
                    data=entry["data"],
                    metadata=entry["metadata"],
                )
                for entry in data["context_history"]
            ]

        return context

    # ==================== Checkpoint Management (for BaseServiceCheckpointer)

    async def store_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store checkpoint data for LangGraph workflows.

        Automatically converts dataclasses to dictionaries to ensure
        JSON serialization compatibility.
        """
        # Sanitize checkpoint data to handle dataclasses
        sanitized_data = self._sanitize_dataclasses(checkpoint_data)
        sanitized_metadata = self._sanitize_dataclasses(metadata or {})

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "thread_id": thread_id,
            "data": sanitized_data,
            "metadata": sanitized_metadata,
            "created_at": datetime.utcnow().isoformat(),
        }

        if self.redis_client:
            try:
                # Store checkpoint
                await self.redis_client.hset(  # type: ignore[misc]
                    f"checkpoints:{thread_id}",
                    checkpoint_id,
                    json.dumps(checkpoint, cls=DateTimeEncoder),
                )
                # Set TTL
                await self.redis_client.expire(f"checkpoints:{thread_id}", self.checkpoint_ttl)  # type: ignore[misc]

                # Update global metrics
                self._global_metrics["total_checkpoints"] += 1
                return True

            except Exception as e:
                logger.error(f"Failed to store checkpoint to Redis: {e}")

        # Fallback to memory
        key = f"{thread_id}:{checkpoint_id}"
        self._memory_checkpoints[key] = checkpoint
        return True

    async def get_checkpoint(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get checkpoint data. If checkpoint_id is None, get the latest."""
        if self.redis_client:
            try:
                if checkpoint_id:
                    # Get specific checkpoint
                    data = await self.redis_client.hget(f"checkpoints:{thread_id}", checkpoint_id)  # type: ignore[misc]
                    if data:
                        return json.loads(data)
                else:
                    # Get latest checkpoint
                    checkpoints = await self.redis_client.hgetall(f"checkpoints:{thread_id}")  # type: ignore[misc]
                    if checkpoints:
                        # Sort by creation time and get latest
                        latest = max(
                            checkpoints.values(),
                            key=lambda x: json.loads(x)["created_at"],
                        )
                        return json.loads(latest)
            except Exception as e:
                logger.error(f"Failed to get checkpoint from Redis: {e}")

        # Fallback to memory
        if checkpoint_id:
            key = f"{thread_id}:{checkpoint_id}"
            return self._memory_checkpoints.get(key)
        else:
            # Get latest from memory
            thread_checkpoints = {k: v for k, v in self._memory_checkpoints.items() if k.startswith(f"{thread_id}:")}
            if thread_checkpoints:
                latest_key = max(
                    thread_checkpoints.keys(),
                    key=lambda k: thread_checkpoints[k]["created_at"],
                )
                return thread_checkpoints[latest_key]

        return None

    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List checkpoints for a thread, ordered by creation time (newest first)."""
        if self.redis_client:
            try:
                checkpoints_data = await self.redis_client.hgetall(f"checkpoints:{thread_id}")  # type: ignore[misc]
                checkpoints = [json.loads(data) for data in checkpoints_data.values()]
                # Sort by creation time (newest first)
                checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
                return checkpoints[:limit]
            except Exception as e:
                logger.error(f"Failed to list checkpoints from Redis: {e}")

        # Fallback to memory
        thread_checkpoints = [v for k, v in self._memory_checkpoints.items() if k.startswith(f"{thread_id}:")]
        thread_checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
        return thread_checkpoints[:limit]

    # ==================== Cleanup and Maintenance ====================

    async def cleanup_expired_sessions(self, max_idle_hours: int = 24) -> int:
        """Clean up expired sessions and associated data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_idle_hours)
        cleaned_count = 0

        if self.redis_client:
            try:
                # Get all sessions
                sessions_data = await self.redis_client.hgetall("sessions")  # type: ignore[misc]
                expired_sessions = []

                for session_id, data in sessions_data.items():
                    session = SessionMetrics.from_dict(json.loads(data))
                    if session.last_activity < cutoff_time:
                        expired_sessions.append(session_id)

                # Clean up expired sessions
                for session_id in expired_sessions:
                    await self._cleanup_session_data(session_id)
                    cleaned_count += 1

            except Exception as e:
                logger.error(f"Failed to cleanup expired sessions from Redis: {e}")
        else:
            # Memory cleanup
            expired_sessions = [session_id for session_id, session in self._memory_sessions.items() if session.last_activity < cutoff_time]

            for session_id in expired_sessions:
                await self._cleanup_session_data(session_id)
                cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired sessions")

        return cleaned_count

    async def _cleanup_session_data(self, session_id: str):
        """Clean up all data associated with a session."""
        if self.redis_client:
            try:
                # Remove session
                await self.redis_client.hdel("sessions", session_id)  # type: ignore[misc]
                # Remove conversation
                await self.redis_client.delete(f"conversation:{session_id}")  # type: ignore[misc]
                # Remove task context
                await self.redis_client.hdel("task_contexts", session_id)  # type: ignore[misc]
                # Remove checkpoints
                await self.redis_client.delete(f"checkpoints:{session_id}")  # type: ignore[misc]
            except Exception as e:
                logger.error(f"Failed to cleanup session data from Redis: {e}")
        else:
            # Memory cleanup
            self._memory_sessions.pop(session_id, None)
            self._memory_conversations.pop(session_id, None)
            self._memory_contexts.pop(session_id, None)

            # Remove checkpoints
            checkpoint_keys = [k for k in self._memory_checkpoints.keys() if k.startswith(f"{session_id}:")]
            for key in checkpoint_keys:
                self._memory_checkpoints.pop(key, None)

    # ==================== Metrics and Health ====================

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        active_sessions_count = 0

        if self.redis_client:
            try:
                sessions_data = await self.redis_client.hgetall("sessions")  # type: ignore[misc]
                active_sessions_count = len([s for s in sessions_data.values() if json.loads(s)["status"] == "active"])
            except Exception as e:
                logger.error(f"Failed to get metrics from Redis: {e}")
        else:
            active_sessions_count = len([s for s in self._memory_sessions.values() if s.status == "active"])

        return {
            **self._global_metrics,
            "active_sessions": active_sessions_count,
            "storage_backend": "redis" if self.redis_client else "memory",
            "redis_connected": self.redis_client is not None,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health: Dict[str, Any] = {
            "status": "healthy",
            "storage_backend": "redis" if self.redis_client else "memory",
            "redis_connected": False,
            "issues": [],
        }
        issues: List[str] = health["issues"]  # Type narrowing

        # Check Redis connection
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis_connected"] = True
            except Exception as e:
                issues.append(f"Redis connection failed: {e}")
                health["status"] = "degraded"

        # Check memory usage (basic check)
        if not self.redis_client:
            total_memory_items = len(self._memory_sessions) + len(self._memory_conversations) + len(self._memory_contexts) + len(self._memory_checkpoints)
            if total_memory_items > 10000:  # Arbitrary threshold
                issues.append(f"High memory usage: {total_memory_items} items")
                health["status"] = "warning"
        
        health["issues"] = issues  # Update health dict

        return health

    # ==================== ICheckpointerBackend Implementation ===============

    async def put_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a checkpoint for LangGraph workflows (ICheckpointerBackend interface)."""
        return await self.store_checkpoint(thread_id, checkpoint_id, checkpoint_data, metadata)

    async def put_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple],
    ) -> bool:
        """Store intermediate writes for a checkpoint (ICheckpointerBackend interface)."""
        writes_key = f"writes:{thread_id}:{checkpoint_id}:{task_id}"
        writes_payload = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "writes": writes_data,
            "created_at": datetime.utcnow().isoformat(),
        }

        if self.redis_client:
            try:
                await self.redis_client.hset(  # type: ignore[misc]
                    f"checkpoint_writes:{thread_id}",
                    f"{checkpoint_id}:{task_id}",
                    json.dumps(writes_payload, cls=DateTimeEncoder),
                )
                await self.redis_client.expire(f"checkpoint_writes:{thread_id}", self.checkpoint_ttl)
                return True
            except Exception as e:
                logger.error(f"Failed to store writes to Redis: {e}")

        # Fallback to memory
        self._memory_checkpoints[writes_key] = writes_payload
        return True

    async def get_writes(self, thread_id: str, checkpoint_id: str) -> List[tuple]:
        """Get intermediate writes for a checkpoint (ICheckpointerBackend interface)."""
        if self.redis_client:
            try:
                writes_data = await self.redis_client.hgetall(f"checkpoint_writes:{thread_id}")  # type: ignore[misc]
                writes = []
                for key, data in writes_data.items():
                    if key.startswith(f"{checkpoint_id}:"):
                        payload = json.loads(data)
                        writes.extend(payload.get("writes", []))
                return writes
            except Exception as e:
                logger.error(f"Failed to get writes from Redis: {e}")

        # Fallback to memory
        writes = []
        writes_prefix = f"writes:{thread_id}:{checkpoint_id}:"
        for key, payload in self._memory_checkpoints.items():
            if key.startswith(writes_prefix):
                writes.extend(payload.get("writes", []))
        return writes

    # ==================== ITaskContextStorage Implementation ================

    async def store_task_context(self, session_id: str, context: Any) -> bool:
        """Store TaskContext for a session (ITaskContextStorage interface)."""
        return await self._store_task_context(session_id, context)

    # ==================== Agent Communication and Conversation Isolation ====

    async def create_conversation_session(
        self,
        session_id: str,
        participants: List[Dict[str, Any]],
        session_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create an isolated conversation session between participants.

        Args:
            session_id: Base session ID
            participants: List of participant dictionaries with id, type, role
            session_type: Type of conversation ('user_to_mc', 'mc_to_agent', 'agent_to_agent', 'user_to_agent')
            metadata: Additional session metadata

        Returns:
            Generated session key for conversation isolation
        """
        from .conversation_models import (
            ConversationSession,
            ConversationParticipant,
        )

        # Create participant objects
        participant_objects = [
            ConversationParticipant(
                participant_id=p.get("id") or "",
                participant_type=p.get("type") or "",
                participant_role=p.get("role"),
                metadata=p.get("metadata", {}),
            )
            for p in participants
        ]

        # Create conversation session
        conversation_session = ConversationSession(
            session_id=session_id,
            participants=participant_objects,
            session_type=session_type,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            metadata=metadata or {},
        )

        # Generate unique session key
        session_key = conversation_session.generate_session_key()

        # Store conversation session metadata
        await self._store_conversation_session(session_key, conversation_session)

        logger.info(f"Created conversation session: {session_key} (type: {session_type})")
        return session_key

    async def add_agent_communication_message(
        self,
        session_key: str,
        sender_id: str,
        sender_type: str,
        sender_role: Optional[str],
        recipient_id: str,
        recipient_type: str,
        recipient_role: Optional[str],
        content: str,
        message_type: str = "communication",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a message to an agent communication session.

        Args:
            session_key: Isolated session key
            sender_id: ID of the sender
            sender_type: Type of sender ('master_controller', 'agent', 'user')
            sender_role: Role of sender (for agents)
            recipient_id: ID of the recipient
            recipient_type: Type of recipient
            recipient_role: Role of recipient (for agents)
            content: Message content
            message_type: Type of message
            metadata: Additional message metadata

        Returns:
            Success status
        """
        from .conversation_models import AgentCommunicationMessage

        # Create agent communication message
        message = AgentCommunicationMessage(
            message_id=str(uuid.uuid4()),
            session_key=session_key,
            sender_id=sender_id,
            sender_type=sender_type,
            sender_role=sender_role,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            recipient_role=recipient_role,
            content=content,
            message_type=message_type,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
        )

        # Convert to conversation message format and store
        conv_message_dict = message.to_conversation_message_dict()

        # Store using existing conversation message infrastructure
        await self.add_conversation_message(
            session_id=session_key,
            role=conv_message_dict["role"],
            content=conv_message_dict["content"],
            metadata=conv_message_dict["metadata"],
        )

        # Update session activity
        await self._update_conversation_session_activity(session_key)

        logger.debug(f"Added agent communication message to session {session_key}")
        return True

    async def get_agent_conversation_history(
        self,
        session_key: str,
        limit: int = 50,
        message_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for an agent communication session.

        Args:
            session_key: Isolated session key
            limit: Maximum number of messages to retrieve
            message_types: Filter by message types

        Returns:
            List of conversation messages
        """
        # Get conversation history using existing infrastructure
        messages = await self.get_conversation_history(session_key, limit)

        # Filter by message types if specified
        if message_types:
            filtered_messages = []
            for msg in messages:
                if hasattr(msg, "to_dict"):
                    msg_dict = msg.to_dict()
                else:
                    msg_dict = msg  # type: ignore[assignment]

                msg_metadata = msg_dict.get("metadata", {})
                msg_type = msg_metadata.get("message_type", "communication")

                if msg_type in message_types:
                    filtered_messages.append(msg_dict)

            return filtered_messages

        # Convert messages to dict format
        return [msg.to_dict() if hasattr(msg, "to_dict") else msg for msg in messages]

    async def _store_conversation_session(self, session_key: str, conversation_session) -> None:
        """Store conversation session metadata."""
        session_data = {
            "session_id": conversation_session.session_id,
            "participants": [
                {
                    "participant_id": p.participant_id,
                    "participant_type": p.participant_type,
                    "participant_role": p.participant_role,
                    "metadata": p.metadata,
                }
                for p in conversation_session.participants
            ],
            "session_type": conversation_session.session_type,
            "created_at": conversation_session.created_at.isoformat(),
            "last_activity": conversation_session.last_activity.isoformat(),
            "metadata": conversation_session.metadata,
        }

        if self.redis_client:
            try:
                await self.redis_client.hset(  # type: ignore[misc]
                    "conversation_sessions",
                    session_key,
                    json.dumps(session_data, cls=DateTimeEncoder),
                )
                await self.redis_client.expire("conversation_sessions", self.session_ttl)  # type: ignore[misc]
                return
            except Exception as e:
                logger.error(f"Failed to store conversation session to Redis: {e}")

        # Fallback to memory (extend memory storage)
        if not hasattr(self, "_memory_conversation_sessions"):
            self._memory_conversation_sessions = {}
        self._memory_conversation_sessions[session_key] = session_data

    async def _update_conversation_session_activity(self, session_key: str) -> None:
        """Update last activity timestamp for a conversation session."""
        if self.redis_client:
            try:
                session_data = await self.redis_client.hget("conversation_sessions", session_key)  # type: ignore[misc]
                if session_data:
                    session_dict = json.loads(session_data)
                    session_dict["last_activity"] = datetime.utcnow().isoformat()
                    await self.redis_client.hset(  # type: ignore[misc]
                        "conversation_sessions",
                        session_key,
                        json.dumps(session_dict, cls=DateTimeEncoder),
                    )
                return
            except Exception as e:
                logger.error(f"Failed to update conversation session activity in Redis: {e}")

        # Fallback to memory
        if hasattr(self, "_memory_conversation_sessions") and session_key in self._memory_conversation_sessions:
            self._memory_conversation_sessions[session_key]["last_activity"] = datetime.utcnow().isoformat()

    # ==================== Compression Methods (Phase 6) ====================

    async def compress_conversation(
        self,
        session_id: str,
        strategy: Optional[str] = None,
        config_override: Optional[CompressionConfig] = None,
    ) -> Dict[str, Any]:
        """
        Compress conversation history using specified strategy.

        Args:
            session_id: Session ID to compress
            strategy: Compression strategy (overrides config if provided)
            config_override: Override compression config for this operation

        Returns:
            Dictionary with compression results:
            {
                "success": bool,
                "strategy": str,
                "original_count": int,
                "compressed_count": int,
                "compression_ratio": float,
                "tokens_saved": int (if applicable),
                "time_taken": float
            }

        Example:
            result = await engine.compress_conversation(
                session_id="session-123",
                strategy="summarize"
            )
            print(f"Compressed from {result['original_count']} to {result['compressed_count']} messages")
        """
        import time

        start_time = time.time()

        # Use config override or default
        config = config_override or self.compression_config
        selected_strategy = strategy or config.strategy

        logger.info(f"Compressing conversation {session_id} using strategy: {selected_strategy}")

        try:
            # Get current conversation
            messages_dict = await self.get_conversation_history(session_id)
            # Convert dict list to ConversationMessage list
            messages = [ConversationMessage.from_dict(msg) for msg in messages_dict]
            original_count = len(messages)

            if original_count == 0:
                return {
                    "success": False,
                    "error": "No messages to compress",
                    "original_count": 0,
                    "compressed_count": 0,
                }

            # Select compression strategy
            if selected_strategy == "truncate":
                compressed_messages = await self._compress_with_truncation(messages, config)
            elif selected_strategy == "summarize":
                compressed_messages = await self._compress_with_summarization(messages, config)
            elif selected_strategy == "semantic":
                compressed_messages = await self._compress_with_semantic_dedup(messages, config)
            elif selected_strategy == "hybrid":
                compressed_messages = await self._compress_with_hybrid(messages, config)
            else:
                raise ValueError(f"Unknown compression strategy: {selected_strategy}")

            compressed_count = len(compressed_messages)
            compression_ratio = 1.0 - (compressed_count / original_count) if original_count > 0 else 0.0

            # Replace conversation history
            await self._replace_conversation_history(session_id, compressed_messages)

            time_taken = time.time() - start_time

            result = {
                "success": True,
                "strategy": selected_strategy,
                "original_count": original_count,
                "compressed_count": compressed_count,
                "compression_ratio": compression_ratio,
                "time_taken": time_taken,
            }

            logger.info(f"Compression complete: {original_count} -> {compressed_count} messages " f"({compression_ratio:.1%} reduction) in {time_taken:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Compression failed for session {session_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "strategy": selected_strategy,
                "time_taken": time.time() - start_time,
            }

    async def _compress_with_truncation(self, messages: List[ConversationMessage], config: CompressionConfig) -> List[ConversationMessage]:
        """
        Compress by truncating old messages (fast, no LLM required).

        Keeps the most recent N messages based on config.keep_recent.

        Args:
            messages: List of conversation messages
            config: Compression configuration

        Returns:
            Truncated list of messages
        """
        if len(messages) <= config.keep_recent:
            return messages

        # Keep most recent messages
        truncated = messages[-config.keep_recent :]

        logger.debug(f"Truncation: kept {len(truncated)} most recent messages " f"(removed {len(messages) - len(truncated)})")

        return truncated

    async def _compress_with_summarization(self, messages: List[ConversationMessage], config: CompressionConfig) -> List[ConversationMessage]:
        """
        Compress using LLM-based summarization.

        Creates a summary of older messages and keeps recent messages intact.

        Args:
            messages: List of conversation messages
            config: Compression configuration

        Returns:
            List with summary message + recent messages

        Raises:
            ValueError: If no LLM client configured
        """
        if not self.llm_client:
            raise ValueError("LLM client required for summarization compression. " "Provide llm_client parameter to ContextEngine.")

        if len(messages) <= config.keep_recent:
            return messages

        # Split into messages to summarize and messages to keep
        messages_to_summarize = messages[: -config.keep_recent]
        messages_to_keep = messages[-config.keep_recent :]

        # Build summary prompt
        summary_prompt = self._build_summary_prompt(messages_to_summarize, config)

        # Generate summary using LLM
        from aiecs.llm.clients.base_client import LLMMessage

        llm_messages = [LLMMessage(role="user", content=summary_prompt)]

        response = await self.llm_client.generate_text(messages=llm_messages, max_tokens=config.summary_max_tokens)

        summary_text = response.content

        # Create summary message
        summary_message = ConversationMessage(
            role="system",
            content=f"[Summary of {len(messages_to_summarize)} previous messages]\n\n{summary_text}",
            timestamp=datetime.utcnow(),
            metadata={"type": "summary", "summarized_count": len(messages_to_summarize)},
        )

        # Combine summary + recent messages
        if config.include_summary_in_history:
            compressed = [summary_message] + messages_to_keep
        else:
            compressed = messages_to_keep

        logger.debug(f"Summarization: {len(messages_to_summarize)} messages -> 1 summary, " f"kept {len(messages_to_keep)} recent messages")

        return compressed

    def _build_summary_prompt(self, messages: List[ConversationMessage], config: CompressionConfig) -> str:
        """
        Build prompt for summarization.

        Args:
            messages: Messages to summarize
            config: Compression configuration

        Returns:
            Prompt string for LLM
        """
        # Use custom template if provided
        if config.summary_prompt_template:
            # Format template with messages
            messages_text = "\n\n".join([f"{msg.role}: {msg.content}" for msg in messages])
            return config.summary_prompt_template.format(messages=messages_text)

        # Default template
        messages_text = "\n\n".join([f"{msg.role}: {msg.content}" for msg in messages])

        prompt = f"""Please provide a concise summary of the following conversation.
Focus on key points, decisions, and important information.
Keep the summary under {config.summary_max_tokens} tokens.

Conversation:
{messages_text}

Summary:"""

        return prompt

    async def _compress_with_semantic_dedup(self, messages: List[ConversationMessage], config: CompressionConfig) -> List[ConversationMessage]:
        """
        Compress using semantic deduplication (embedding-based).

        Removes messages that are semantically similar to keep diverse content.

        Args:
            messages: List of conversation messages
            config: Compression configuration

        Returns:
            List of semantically diverse messages

        Raises:
            ValueError: If no LLM client configured
        """
        if not self.llm_client:
            raise ValueError("LLM client required for semantic deduplication. " "Provide llm_client parameter to ContextEngine.")

        if len(messages) <= config.keep_recent:
            return messages

        # Get embeddings for all messages
        texts = [msg.content for msg in messages]

        try:
            embeddings = await self.llm_client.get_embeddings(texts=texts, model=config.embedding_model)
        except NotImplementedError:
            logger.warning("LLM client does not support embeddings. Falling back to truncation.")
            return await self._compress_with_truncation(messages, config)

        # Find diverse messages using embeddings
        diverse_indices = self._find_diverse_messages(embeddings, config.similarity_threshold, config.keep_recent)

        # Keep messages at diverse indices
        compressed = [messages[i] for i in sorted(diverse_indices)]

        logger.debug(f"Semantic dedup: kept {len(compressed)} diverse messages " f"(removed {len(messages) - len(compressed)} similar messages)")

        return compressed

    def _find_diverse_messages(self, embeddings: List[List[float]], similarity_threshold: float, target_count: int) -> List[int]:
        """
        Find diverse messages using embeddings.

        Uses greedy selection to find messages that are semantically diverse.

        Args:
            embeddings: List of embedding vectors
            similarity_threshold: Similarity threshold for deduplication
            target_count: Target number of messages to keep

        Returns:
            List of indices of diverse messages
        """
        import numpy as np

        if len(embeddings) <= target_count:
            return list(range(len(embeddings)))

        # Convert to numpy array
        emb_array = np.array(embeddings)

        # Normalize embeddings for cosine similarity
        norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
        emb_normalized = emb_array / (norms + 1e-8)

        # Greedy selection: always keep most recent messages
        selected_indices = list(range(len(embeddings) - target_count, len(embeddings)))

        # For older messages, select diverse ones
        remaining_indices = list(range(len(embeddings) - target_count))

        while remaining_indices and len(selected_indices) < target_count:
            # Find message most different from selected ones
            max_min_distance = -1
            best_idx = None

            for idx in remaining_indices:
                # Calculate similarity to all selected messages
                similarities = np.dot(emb_normalized[idx], emb_normalized[selected_indices].T)
                min_similarity = np.min(similarities) if len(similarities) > 0 else 0

                # We want maximum minimum distance (most diverse)
                if min_similarity > max_min_distance:
                    max_min_distance = min_similarity
                    best_idx = idx

            if best_idx is not None and max_min_distance < similarity_threshold:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break

        return selected_indices

    async def _replace_conversation_history(self, session_id: str, messages: List[ConversationMessage]) -> None:
        """
        Replace conversation history with compressed messages.

        Args:
            session_id: Session ID
            messages: New list of messages
        """
        if self.redis_client:
            try:
                # Clear existing messages
                await self.redis_client.delete(f"conversation:{session_id}")

                # Store new messages
                for msg in messages:
                    await self.redis_client.rpush(  # type: ignore[misc]
                        f"conversation:{session_id}",
                        json.dumps(msg.to_dict(), cls=DateTimeEncoder),
                    )

                # Set TTL
                await self.redis_client.expire(f"conversation:{session_id}", self.session_ttl)

                logger.debug(f"Replaced conversation history for {session_id} with {len(messages)} messages")
                return
            except Exception as e:
                logger.error(f"Failed to replace conversation history in Redis: {e}")

        # Fallback to memory
        self._memory_conversations[session_id] = messages
        logger.debug(f"Replaced conversation history (memory) for {session_id} with {len(messages)} messages")

    async def _compress_with_hybrid(self, messages: List[ConversationMessage], config: CompressionConfig) -> List[ConversationMessage]:
        """
        Compress using hybrid strategy (combination of multiple strategies).

        Applies multiple compression strategies in sequence based on config.hybrid_strategies.

        Args:
            messages: List of conversation messages
            config: Compression configuration

        Returns:
            Compressed list of messages

        Example:
            # Default hybrid: truncate then summarize
            config = CompressionConfig(
                strategy="hybrid",
                hybrid_strategies=["truncate", "summarize"]
            )
        """
        compressed = messages

        # Type narrowing: ensure hybrid_strategies is a list
        if config.hybrid_strategies is None:
            config.hybrid_strategies = ["truncate", "summarize"]
        
        for strategy in config.hybrid_strategies:
            if strategy == "truncate":
                compressed = await self._compress_with_truncation(compressed, config)
            elif strategy == "summarize":
                compressed = await self._compress_with_summarization(compressed, config)
            elif strategy == "semantic":
                compressed = await self._compress_with_semantic_dedup(compressed, config)
            else:
                logger.warning(f"Unknown hybrid strategy: {strategy}, skipping")

        logger.debug(f"Hybrid compression: {len(messages)} -> {len(compressed)} messages " f"using strategies: {', '.join(config.hybrid_strategies)}")

        return compressed

    async def auto_compress_on_limit(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Automatically compress conversation if it exceeds threshold.

        Checks if conversation exceeds auto_compress_threshold and compresses
        to auto_compress_target if needed.

        Args:
            session_id: Session ID to check

        Returns:
            Compression result dict if compression was triggered, None otherwise

        Example:
            # Configure auto-compression
            config = CompressionConfig(
                auto_compress_enabled=True,
                auto_compress_threshold=100,
                auto_compress_target=50
            )
            engine = ContextEngine(compression_config=config)

            # Check and auto-compress if needed
            result = await engine.auto_compress_on_limit(session_id)
            if result:
                print(f"Auto-compressed: {result['original_count']} -> {result['compressed_count']}")
        """
        if not self.compression_config.auto_compress_enabled:
            return None

        # Get current message count
        messages = await self.get_conversation_history(session_id)
        message_count = len(messages)

        # Check if threshold exceeded
        if message_count <= self.compression_config.auto_compress_threshold:
            return None

        logger.info(f"Auto-compression triggered for {session_id}: " f"{message_count} messages exceeds threshold of " f"{self.compression_config.auto_compress_threshold}")

        # Compress conversation
        result = await self.compress_conversation(session_id)

        if result.get("success"):
            logger.info(f"Auto-compression complete for {session_id}: " f"{result['original_count']} -> {result['compressed_count']} messages")

        return result

    async def get_compressed_context(
        self,
        session_id: str,
        format: str = "messages",
        compress_first: bool = False,
    ) -> Any:
        """
        Get conversation context in compressed format.

        Args:
            session_id: Session ID
            format: Output format - "messages", "string", or "dict"
            compress_first: Whether to compress before returning

        Returns:
            Conversation in requested format:
            - "messages": List[ConversationMessage]
            - "string": Formatted string
            - "dict": List[Dict[str, Any]]

        Example:
            # Get as formatted string
            context = await engine.get_compressed_context(
                session_id="session-123",
                format="string"
            )
            print(context)

            # Get as messages, compress first
            messages = await engine.get_compressed_context(
                session_id="session-456",
                format="messages",
                compress_first=True
            )
        """
        # Compress first if requested
        if compress_first:
            await self.compress_conversation(session_id)

        # Get conversation history
        messages = await self.get_conversation_history(session_id)

        # Return in requested format
        if format == "messages":
            return messages

        elif format == "string":
            # Format as string
            lines = []
            for msg in messages:
                # messages is List[Dict[str, Any]] from get_conversation_history
                timestamp = msg.get("timestamp", "").strftime("%Y-%m-%d %H:%M:%S") if isinstance(msg.get("timestamp"), datetime) else str(msg.get("timestamp", ""))
                role = msg.get("role", "")
                content = msg.get("content", "")
                lines.append(f"[{timestamp}] {role}: {content}")
            return "\n\n".join(lines)

        elif format == "dict":
            # Return as list of dicts (already dicts from get_conversation_history)
            return [self._sanitize_for_json(msg) for msg in messages]

        else:
            raise ValueError(f"Invalid format '{format}'. Must be 'messages', 'string', or 'dict'")

    def _sanitize_for_json(self, obj: Any) -> Any:
        """
        Sanitize object for JSON serialization.

        Handles common non-serializable types like datetime, dataclasses, etc.

        Args:
            obj: Object to sanitize

        Returns:
            JSON-serializable version of object

        Note:
            This is similar to _sanitize_dataclasses but more general purpose.
        """
        # Use existing sanitization logic
        return self._sanitize_dataclasses(obj)
