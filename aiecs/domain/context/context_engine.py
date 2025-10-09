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

import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import TaskContext for base functionality
from aiecs.domain.task.task_context import TaskContext, ContextUpdate

# Import core storage interfaces
from aiecs.core.interface.storage_interface import IStorageBackend, ICheckpointerBackend

# Redis client import - use existing infrastructure
try:
    import redis.asyncio as redis
    from aiecs.infrastructure.persistence.redis_client import get_redis_client
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    get_redis_client = None
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
            "last_activity": self.last_activity.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetrics':
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
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class ContextEngine(IStorageBackend, ICheckpointerBackend):
    """
    Advanced Context and Session Management Engine.

    Implements core storage interfaces to provide comprehensive session management
    with Redis backend storage for BaseAIService and BaseServiceCheckpointer.

    This implementation follows the middleware's core interface pattern,
    enabling dependency inversion and clean architecture.
    """

    def __init__(self, use_existing_redis: bool = True):
        """
        Initialize ContextEngine.

        Args:
            use_existing_redis: Whether to use the existing Redis client from infrastructure
                              (已弃用: 现在总是创建独立的 RedisClient 实例以避免事件循环冲突)
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

        # Metrics
        self._global_metrics = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_messages": 0,
            "total_checkpoints": 0
        }

        logger.info("ContextEngine initialized")

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
            
            from aiecs.infrastructure.persistence.redis_client import RedisClient
            
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
        if hasattr(self, '_redis_client_wrapper') and self._redis_client_wrapper:
            # 使用 RedisClient 包装器的 close 方法
            await self._redis_client_wrapper.close()
            self._redis_client_wrapper = None
            self.redis_client = None
        elif self.redis_client:
            # 兼容性处理：直接关闭 redis 客户端
            await self.redis_client.close()
            self.redis_client = None

    # ==================== Session Management ====================

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> SessionMetrics:
        """Create a new session."""
        now = datetime.utcnow()
        session = SessionMetrics(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now
        )

        # Store session
        await self._store_session(session)

        # Create associated TaskContext
        task_context = TaskContext({
            "user_id": user_id,
            "chat_id": session_id,
            "metadata": metadata or {}
        })
        await self._store_task_context(session_id, task_context)

        # Update metrics
        self._global_metrics["total_sessions"] += 1
        self._global_metrics["active_sessions"] += 1

        logger.info(f"Created session {session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionMetrics]:
        """Get session by ID."""
        if self.redis_client:
            try:
                data = await self.redis_client.hget("sessions", session_id)
                if data:
                    return SessionMetrics.from_dict(json.loads(data))
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")

        # Fallback to memory
        return self._memory_sessions.get(session_id)

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any] = None,
        increment_requests: bool = False,
        add_processing_time: float = 0.0,
        mark_error: bool = False
    ) -> bool:
        """Update session with activity and metrics."""
        session = await self.get_session(session_id)
        if not session:
            return False

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
        session = await self.get_session(session_id)
        if not session:
            return False

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
                await self.redis_client.hset(
                    "sessions",
                    session.session_id,
                    json.dumps(session.to_dict(), cls=DateTimeEncoder)
                )
                await self.redis_client.expire(f"sessions", self.session_ttl)
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
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add message to conversation history."""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )

        # Store message
        await self._store_conversation_message(session_id, message)

        # Update session activity
        await self.update_session(session_id)

        # Update global metrics
        self._global_metrics["total_messages"] += 1

        return True

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Get conversation history for a session."""
        if self.redis_client:
            try:
                messages_data = await self.redis_client.lrange(
                    f"conversation:{session_id}",
                    -limit,
                    -1
                )
                # Since lpush adds to the beginning, we need to reverse to get chronological order
                messages = [
                    ConversationMessage.from_dict(json.loads(msg))
                    for msg in reversed(messages_data)
                ]
                return messages
            except Exception as e:
                logger.error(f"Failed to get conversation from Redis: {e}")

        # Fallback to memory
        messages = self._memory_conversations.get(session_id, [])
        return messages[-limit:] if limit > 0 else messages

    async def _store_conversation_message(self, session_id: str, message: ConversationMessage):
        """Store conversation message to Redis or memory."""
        if self.redis_client:
            try:
                # Add to list
                await self.redis_client.lpush(
                    f"conversation:{session_id}",
                    json.dumps(message.to_dict(), cls=DateTimeEncoder)
                )
                # Trim to limit
                await self.redis_client.ltrim(
                    f"conversation:{session_id}",
                    -self.conversation_limit,
                    -1
                )
                # Set TTL
                await self.redis_client.expire(
                    f"conversation:{session_id}",
                    self.session_ttl
                )
                return
            except Exception as e:
                logger.error(f"Failed to store message to Redis: {e}")

        # Fallback to memory
        if session_id not in self._memory_conversations:
            self._memory_conversations[session_id] = []

        self._memory_conversations[session_id].append(message)

        # Trim to limit
        if len(self._memory_conversations[session_id]) > self.conversation_limit:
            self._memory_conversations[session_id] = self._memory_conversations[session_id][-self.conversation_limit:]

    # ==================== TaskContext Integration ====================

    async def get_task_context(self, session_id: str) -> Optional[TaskContext]:
        """Get TaskContext for a session."""
        if self.redis_client:
            try:
                data = await self.redis_client.hget("task_contexts", session_id)
                if data:
                    context_data = json.loads(data)
                    # Reconstruct TaskContext from stored data
                    return self._reconstruct_task_context(context_data)
            except Exception as e:
                logger.error(f"Failed to get TaskContext from Redis: {e}")

        # Fallback to memory
        return self._memory_contexts.get(session_id)

    async def _store_task_context(self, session_id: str, context: TaskContext):
        """Store TaskContext to Redis or memory."""
        if self.redis_client:
            try:
                await self.redis_client.hset(
                    "task_contexts",
                    session_id,
                    json.dumps(context.to_dict(), cls=DateTimeEncoder)
                )
                await self.redis_client.expire("task_contexts", self.session_ttl)
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
                    metadata=entry["metadata"]
                )
                for entry in data["context_history"]
            ]

        return context

    # ==================== Checkpoint Management (for BaseServiceCheckpointer) ====================

    async def store_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store checkpoint data for LangGraph workflows."""
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "thread_id": thread_id,
            "data": checkpoint_data,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }

        if self.redis_client:
            try:
                # Store checkpoint
                await self.redis_client.hset(
                    f"checkpoints:{thread_id}",
                    checkpoint_id,
                    json.dumps(checkpoint, cls=DateTimeEncoder)
                )
                # Set TTL
                await self.redis_client.expire(
                    f"checkpoints:{thread_id}",
                    self.checkpoint_ttl
                )

                # Update global metrics
                self._global_metrics["total_checkpoints"] += 1
                return True

            except Exception as e:
                logger.error(f"Failed to store checkpoint to Redis: {e}")

        # Fallback to memory
        key = f"{thread_id}:{checkpoint_id}"
        self._memory_checkpoints[key] = checkpoint
        return True

    async def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get checkpoint data. If checkpoint_id is None, get the latest."""
        if self.redis_client:
            try:
                if checkpoint_id:
                    # Get specific checkpoint
                    data = await self.redis_client.hget(f"checkpoints:{thread_id}", checkpoint_id)
                    if data:
                        return json.loads(data)
                else:
                    # Get latest checkpoint
                    checkpoints = await self.redis_client.hgetall(f"checkpoints:{thread_id}")
                    if checkpoints:
                        # Sort by creation time and get latest
                        latest = max(
                            checkpoints.values(),
                            key=lambda x: json.loads(x)["created_at"]
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
            thread_checkpoints = {
                k: v for k, v in self._memory_checkpoints.items()
                if k.startswith(f"{thread_id}:")
            }
            if thread_checkpoints:
                latest_key = max(
                    thread_checkpoints.keys(),
                    key=lambda k: thread_checkpoints[k]["created_at"]
                )
                return thread_checkpoints[latest_key]

        return None

    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints for a thread, ordered by creation time (newest first)."""
        if self.redis_client:
            try:
                checkpoints_data = await self.redis_client.hgetall(f"checkpoints:{thread_id}")
                checkpoints = [json.loads(data) for data in checkpoints_data.values()]
                # Sort by creation time (newest first)
                checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
                return checkpoints[:limit]
            except Exception as e:
                logger.error(f"Failed to list checkpoints from Redis: {e}")

        # Fallback to memory
        thread_checkpoints = [
            v for k, v in self._memory_checkpoints.items()
            if k.startswith(f"{thread_id}:")
        ]
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
                sessions_data = await self.redis_client.hgetall("sessions")
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
            expired_sessions = [
                session_id for session_id, session in self._memory_sessions.items()
                if session.last_activity < cutoff_time
            ]

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
                await self.redis_client.hdel("sessions", session_id)
                # Remove conversation
                await self.redis_client.delete(f"conversation:{session_id}")
                # Remove task context
                await self.redis_client.hdel("task_contexts", session_id)
                # Remove checkpoints
                await self.redis_client.delete(f"checkpoints:{session_id}")
            except Exception as e:
                logger.error(f"Failed to cleanup session data from Redis: {e}")
        else:
            # Memory cleanup
            self._memory_sessions.pop(session_id, None)
            self._memory_conversations.pop(session_id, None)
            self._memory_contexts.pop(session_id, None)

            # Remove checkpoints
            checkpoint_keys = [
                k for k in self._memory_checkpoints.keys()
                if k.startswith(f"{session_id}:")
            ]
            for key in checkpoint_keys:
                self._memory_checkpoints.pop(key, None)

    # ==================== Metrics and Health ====================

    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        active_sessions_count = 0

        if self.redis_client:
            try:
                sessions_data = await self.redis_client.hgetall("sessions")
                active_sessions_count = len([
                    s for s in sessions_data.values()
                    if json.loads(s)["status"] == "active"
                ])
            except Exception as e:
                logger.error(f"Failed to get metrics from Redis: {e}")
        else:
            active_sessions_count = len([
                s for s in self._memory_sessions.values()
                if s.status == "active"
            ])

        return {
            **self._global_metrics,
            "active_sessions": active_sessions_count,
            "storage_backend": "redis" if self.redis_client else "memory",
            "redis_connected": self.redis_client is not None,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        health = {
            "status": "healthy",
            "storage_backend": "redis" if self.redis_client else "memory",
            "redis_connected": False,
            "issues": []
        }

        # Check Redis connection
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis_connected"] = True
            except Exception as e:
                health["issues"].append(f"Redis connection failed: {e}")
                health["status"] = "degraded"

        # Check memory usage (basic check)
        if not self.redis_client:
            total_memory_items = (
                len(self._memory_sessions) +
                len(self._memory_conversations) +
                len(self._memory_contexts) +
                len(self._memory_checkpoints)
            )
            if total_memory_items > 10000:  # Arbitrary threshold
                health["issues"].append(f"High memory usage: {total_memory_items} items")
                health["status"] = "warning"

        return health

    # ==================== ICheckpointerBackend Implementation ====================

    async def put_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store a checkpoint for LangGraph workflows (ICheckpointerBackend interface)."""
        return await self.store_checkpoint(thread_id, checkpoint_id, checkpoint_data, metadata)

    async def put_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple]
    ) -> bool:
        """Store intermediate writes for a checkpoint (ICheckpointerBackend interface)."""
        writes_key = f"writes:{thread_id}:{checkpoint_id}:{task_id}"
        writes_payload = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "writes": writes_data,
            "created_at": datetime.utcnow().isoformat()
        }

        if self.redis_client:
            try:
                await self.redis_client.hset(
                    f"checkpoint_writes:{thread_id}",
                    f"{checkpoint_id}:{task_id}",
                    json.dumps(writes_payload, cls=DateTimeEncoder)
                )
                await self.redis_client.expire(
                    f"checkpoint_writes:{thread_id}",
                    self.checkpoint_ttl
                )
                return True
            except Exception as e:
                logger.error(f"Failed to store writes to Redis: {e}")

        # Fallback to memory
        self._memory_checkpoints[writes_key] = writes_payload
        return True

    async def get_writes(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> List[tuple]:
        """Get intermediate writes for a checkpoint (ICheckpointerBackend interface)."""
        if self.redis_client:
            try:
                writes_data = await self.redis_client.hgetall(f"checkpoint_writes:{thread_id}")
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

    # ==================== ITaskContextStorage Implementation ====================

    async def store_task_context(self, session_id: str, context: Any) -> bool:
        """Store TaskContext for a session (ITaskContextStorage interface)."""
        return await self._store_task_context(session_id, context)

    # ==================== Agent Communication and Conversation Isolation ====================

    async def create_conversation_session(
        self,
        session_id: str,
        participants: List[Dict[str, Any]],
        session_type: str,
        metadata: Dict[str, Any] = None
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
        from .conversation_models import ConversationSession, ConversationParticipant

        # Create participant objects
        participant_objects = [
            ConversationParticipant(
                participant_id=p.get('id'),
                participant_type=p.get('type'),
                participant_role=p.get('role'),
                metadata=p.get('metadata', {})
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
            metadata=metadata or {}
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
        metadata: Dict[str, Any] = None
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
            metadata=metadata or {}
        )

        # Convert to conversation message format and store
        conv_message_dict = message.to_conversation_message_dict()

        # Store using existing conversation message infrastructure
        await self.add_conversation_message(
            session_id=session_key,
            role=conv_message_dict["role"],
            content=conv_message_dict["content"],
            metadata=conv_message_dict["metadata"]
        )

        # Update session activity
        await self._update_conversation_session_activity(session_key)

        logger.debug(f"Added agent communication message to session {session_key}")
        return True

    async def get_agent_conversation_history(
        self,
        session_key: str,
        limit: int = 50,
        message_types: Optional[List[str]] = None
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
                if hasattr(msg, 'to_dict'):
                    msg_dict = msg.to_dict()
                else:
                    msg_dict = msg

                msg_metadata = msg_dict.get('metadata', {})
                msg_type = msg_metadata.get('message_type', 'communication')

                if msg_type in message_types:
                    filtered_messages.append(msg_dict)

            return filtered_messages

        # Convert messages to dict format
        return [msg.to_dict() if hasattr(msg, 'to_dict') else msg for msg in messages]

    async def _store_conversation_session(self, session_key: str, conversation_session) -> None:
        """Store conversation session metadata."""
        session_data = {
            "session_id": conversation_session.session_id,
            "participants": [
                {
                    "participant_id": p.participant_id,
                    "participant_type": p.participant_type,
                    "participant_role": p.participant_role,
                    "metadata": p.metadata
                }
                for p in conversation_session.participants
            ],
            "session_type": conversation_session.session_type,
            "created_at": conversation_session.created_at.isoformat(),
            "last_activity": conversation_session.last_activity.isoformat(),
            "metadata": conversation_session.metadata
        }

        if self.redis_client:
            try:
                await self.redis_client.hset(
                    "conversation_sessions",
                    session_key,
                    json.dumps(session_data, cls=DateTimeEncoder)
                )
                await self.redis_client.expire("conversation_sessions", self.session_ttl)
                return
            except Exception as e:
                logger.error(f"Failed to store conversation session to Redis: {e}")

        # Fallback to memory (extend memory storage)
        if not hasattr(self, '_memory_conversation_sessions'):
            self._memory_conversation_sessions = {}
        self._memory_conversation_sessions[session_key] = session_data

    async def _update_conversation_session_activity(self, session_key: str) -> None:
        """Update last activity timestamp for a conversation session."""
        if self.redis_client:
            try:
                session_data = await self.redis_client.hget("conversation_sessions", session_key)
                if session_data:
                    session_dict = json.loads(session_data)
                    session_dict["last_activity"] = datetime.utcnow().isoformat()
                    await self.redis_client.hset(
                        "conversation_sessions",
                        session_key,
                        json.dumps(session_dict, cls=DateTimeEncoder)
                    )
                return
            except Exception as e:
                logger.error(f"Failed to update conversation session activity in Redis: {e}")

        # Fallback to memory
        if hasattr(self, '_memory_conversation_sessions') and session_key in self._memory_conversation_sessions:
            self._memory_conversation_sessions[session_key]["last_activity"] = datetime.utcnow().isoformat()
