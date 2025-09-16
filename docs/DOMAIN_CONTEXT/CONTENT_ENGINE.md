# 内容引擎技术文档

## 概述

### 设计动机与问题背景

在构建大型 AI 应用系统时，上下文和会话管理面临以下核心挑战：

**1. 多会话管理复杂性**
- 需要支持多个用户会话的并发管理
- 会话状态需要在多个请求间保持一致性
- 缺乏统一的会话生命周期管理机制

**2. 对话历史管理困难**
- 大量对话消息需要高效存储和检索
- 对话上下文需要在长时间内保持连续性
- 缺乏对话历史的优化和压缩机制

**3. 检查点和状态持久化**
- 复杂工作流需要支持检查点和状态恢复
- 状态数据需要在系统重启后保持可用
- 缺乏统一的检查点管理机制

**4. 性能和扩展性挑战**
- 大量并发会话需要高性能存储支持
- 内存使用需要优化以避免资源耗尽
- 缺乏有效的缓存和清理机制

**内容引擎的解决方案**：
- **统一会话管理**：提供完整的会话生命周期管理
- **多存储后端支持**：支持 Redis 和内存存储的自动切换
- **对话历史优化**：智能的对话历史管理和压缩
- **检查点集成**：与 LangGraph 检查点系统深度集成
- **性能监控**：提供详细的性能指标和健康检查

### 组件定位

`content_engine.py` 是 AIECS 系统的核心领域服务，位于领域层 (Domain Layer)，实现了存储接口和检查点后端接口。作为系统的上下文管理核心，它提供了高级的会话管理、对话跟踪和持久化存储能力。

## 组件类型与定位

### 组件类型
**领域服务组件** - 位于领域层 (Domain Layer)，属于业务逻辑层

### 架构层次
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← 使用内容引擎的组件
│  (BaseAIService, ServiceLayer)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← 内容引擎所在层
│  (ContextEngine, Business Logic)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← 内容引擎依赖的组件
│  (Redis, Storage Interfaces)            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Services               │  ← 外部存储系统
│  (Redis, PostgreSQL, FileSystem)        │
└─────────────────────────────────────────┘
```

## 上游组件（使用方）

### 1. AI 服务层
- **BaseAIService** (如果存在)
- **ServiceLayer** (如果存在)
- **AgentService** (如果存在)

### 2. 应用层服务
- **TaskService** (如果存在)
- **ExecutionService** (如果存在)
- **ConversationService** (如果存在)

### 3. 工作流引擎
- **LangGraph 工作流** (通过检查点接口)
- **BaseServiceCheckpointer** (如果存在)
- **工作流执行器** (如果存在)

## 下游组件（被依赖方）

### 1. 存储接口
- **IStorageBackend** (`core/interface/storage_interface.py`)
- **ICheckpointerBackend** (`core/interface/storage_interface.py`)

### 2. 基础设施层
- **RedisClient** (`infrastructure/persistence/redis_client.py`)
- **Redis 连接池** (通过 Redis 客户端)

### 3. 领域模型
- **TaskContext** (`domain/task/task_context.py`)
- **SessionMetrics** (内部定义)
- **ConversationMessage** (内部定义)

### 4. 对话模型
- **ConversationParticipant** (`domain/context/conversation_models.py`)
- **ConversationSession** (`domain/context/conversation_models.py`)
- **AgentCommunicationMessage** (`domain/context/conversation_models.py`)

## 核心功能

### 1. 会话管理 (Session Management)

#### 会话创建和生命周期
```python
async def create_session(
    self,
    session_id: str,
    user_id: str,
    metadata: Dict[str, Any] = None
) -> SessionMetrics:
    """创建新会话"""
    now = datetime.utcnow()
    session = SessionMetrics(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        last_activity=now,
        status="active"
    )
    await self._store_session(session)
    return session
```

**特性**：
- **唯一会话标识**：支持自定义或自动生成的会话ID
- **用户关联**：每个会话关联到特定用户
- **元数据支持**：支持自定义会话元数据
- **状态跟踪**：实时跟踪会话状态和活动

#### 会话更新和指标跟踪
```python
async def update_session(
    self,
    session_id: str,
    updates: Dict[str, Any] = None,
    increment_requests: bool = False,
    add_processing_time: float = 0.0,
    mark_error: bool = False
) -> bool:
    """更新会话信息和指标"""
    session = await self.get_session(session_id)
    if not session:
        return False
    
    # 更新指标
    if increment_requests:
        session.request_count += 1
    if add_processing_time > 0:
        session.total_processing_time += add_processing_time
    if mark_error:
        session.error_count += 1
    
    session.last_activity = datetime.utcnow()
    await self._store_session(session)
    return True
```

**特性**：
- **请求计数**：自动跟踪会话请求数量
- **处理时间统计**：累计会话处理时间
- **错误统计**：跟踪会话错误次数
- **活动时间更新**：自动更新最后活动时间

### 2. 对话历史管理 (Conversation Management)

#### 对话消息存储
```python
async def add_conversation_message(
    self,
    session_id: str,
    role: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> bool:
    """添加对话消息"""
    message = ConversationMessage(
        role=role,
        content=content,
        timestamp=datetime.utcnow(),
        metadata=metadata or {}
    )
    await self._store_conversation_message(session_id, message)
    return True
```

**特性**：
- **结构化消息**：支持角色、内容、时间戳、元数据
- **时序存储**：保持消息的时间顺序
- **元数据支持**：支持消息级别的自定义元数据
- **自动时间戳**：自动记录消息创建时间

#### 对话历史检索
```python
async def get_conversation_history(
    self,
    session_id: str,
    limit: int = 50
) -> List[ConversationMessage]:
    """获取对话历史"""
    if self.redis_client:
        # Redis 实现
        key = f"conversation:{session_id}"
        messages_data = await self.redis_client.lrange(key, 0, limit - 1)
        return [ConversationMessage.from_dict(json.loads(msg)) for msg in messages_data]
    else:
        # 内存实现
        messages = self._memory_conversations.get(session_id, [])
        return messages[-limit:] if limit > 0 else messages
```

**特性**：
- **分页支持**：支持限制返回消息数量
- **时序检索**：按时间顺序返回消息
- **多存储后端**：支持 Redis 和内存存储
- **数据反序列化**：自动处理数据格式转换

### 3. 任务上下文管理 (Task Context Management)

#### 上下文存储和检索
```python
async def store_task_context(self, session_id: str, context: Any) -> bool:
    """存储任务上下文"""
    if isinstance(context, TaskContext):
        await self._store_task_context(session_id, context)
        return True
    return False

async def get_task_context(self, session_id: str) -> Optional[TaskContext]:
    """获取任务上下文"""
    if self.redis_client:
        # Redis 实现
        key = f"context:{session_id}"
        context_data = await self.redis_client.get(key)
        if context_data:
            return TaskContext.from_dict(json.loads(context_data))
    else:
        # 内存实现
        return self._memory_contexts.get(session_id)
    return None
```

**特性**：
- **类型安全**：支持 TaskContext 类型检查
- **序列化支持**：自动处理上下文的序列化和反序列化
- **持久化存储**：支持上下文的持久化存储
- **快速检索**：提供高效的上下文检索

### 4. 检查点管理 (Checkpoint Management)

#### LangGraph 检查点集成
```python
async def store_checkpoint(
    self,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_data: Dict[str, Any],
    metadata: Dict[str, Any] = None
) -> bool:
    """存储检查点数据"""
    checkpoint_key = f"checkpoint:{thread_id}:{checkpoint_id}"
    checkpoint_info = {
        "checkpoint_id": checkpoint_id,
        "thread_id": thread_id,
        "data": checkpoint_data,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat()
    }
    
    if self.redis_client:
        await self.redis_client.setex(
            checkpoint_key, 
            self.checkpoint_ttl, 
            json.dumps(checkpoint_info)
        )
    else:
        self._memory_checkpoints[checkpoint_key] = checkpoint_info
    
    return True
```

**特性**：
- **LangGraph 兼容**：完全兼容 LangGraph 检查点接口
- **线程隔离**：支持多线程工作流的检查点隔离
- **元数据支持**：支持检查点级别的元数据
- **TTL 支持**：支持检查点的自动过期

### 5. 多存储后端支持 (Multi-Backend Support)

#### 存储后端自动切换
```python
async def initialize(self) -> bool:
    """初始化存储后端"""
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available, using memory storage")
        return True
    
    try:
        if self.use_existing_redis and get_redis_client:
            # 使用现有 Redis 客户端
            redis_client_instance = await get_redis_client()
            self.redis_client = await redis_client_instance.get_client()
            await self.redis_client.ping()
            return True
        else:
            # 直接连接 Redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            return True
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Falling back to memory storage")
        self.redis_client = None
        return False
```

**特性**：
- **自动降级**：Redis 不可用时自动切换到内存存储
- **连接复用**：支持使用现有的 Redis 连接池
- **配置灵活**：支持环境变量配置 Redis 连接
- **错误处理**：完善的错误处理和日志记录

## 数据模型详解

### 1. SessionMetrics - 会话指标模型

```python
@dataclass
class SessionMetrics:
    """会话级性能指标"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    request_count: int = 0
    error_count: int = 0
    total_processing_time: float = 0.0
    status: str = "active"  # active, completed, failed, expired
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetrics':
        """从字典创建实例"""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)
```

**字段说明**：
- **session_id**: 会话唯一标识
- **user_id**: 用户标识
- **created_at**: 会话创建时间
- **last_activity**: 最后活动时间
- **request_count**: 请求计数
- **error_count**: 错误计数
- **total_processing_time**: 总处理时间
- **status**: 会话状态

### 2. ConversationMessage - 对话消息模型

```python
@dataclass
class ConversationMessage:
    """结构化对话消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """从字典创建实例"""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
```

**字段说明**：
- **role**: 消息角色（用户、助手、系统）
- **content**: 消息内容
- **timestamp**: 消息时间戳
- **metadata**: 消息元数据

## 设计模式详解

### 1. 适配器模式 (Adapter Pattern)
```python
class ContextEngine(IStorageBackend, ICheckpointerBackend):
    """适配器模式 - 适配存储接口和检查点接口"""
    
    async def create_session(self, session_id: str, user_id: str, metadata: Dict[str, Any] = None):
        # 实现 IStorageBackend 接口
        pass
    
    async def put_checkpoint(self, thread_id: str, checkpoint_id: str, checkpoint_data: Dict[str, Any]):
        # 实现 ICheckpointerBackend 接口
        pass
```

**优势**：
- **接口统一**：统一不同存储接口的实现
- **向后兼容**：保持与现有接口的兼容性
- **功能整合**：将相关功能整合到统一实现中

### 2. 策略模式 (Strategy Pattern)
```python
async def _store_session(self, session: SessionMetrics):
    """存储策略 - 根据可用后端选择存储方式"""
    if self.redis_client:
        # Redis 存储策略
        key = f"session:{session.session_id}"
        await self.redis_client.setex(key, self.session_ttl, json.dumps(session.to_dict()))
    else:
        # 内存存储策略
        self._memory_sessions[session.session_id] = session
```

**优势**：
- **算法封装**：将存储算法封装在具体实现中
- **动态切换**：可以在运行时切换存储策略
- **易于扩展**：新增存储策略无需修改现有代码

### 3. 模板方法模式 (Template Method Pattern)
```python
async def _store_conversation_message(self, session_id: str, message: ConversationMessage):
    """模板方法 - 定义存储对话消息的通用流程"""
    # 1. 序列化消息
    message_data = message.to_dict()
    
    # 2. 选择存储后端
    if self.redis_client:
        # Redis 存储实现
        key = f"conversation:{session_id}"
        await self.redis_client.lpush(key, json.dumps(message_data))
        await self.redis_client.expire(key, self.session_ttl)
    else:
        # 内存存储实现
        if session_id not in self._memory_conversations:
            self._memory_conversations[session_id] = []
        self._memory_conversations[session_id].append(message)
    
    # 3. 更新指标
    self._global_metrics["total_messages"] += 1
```

**优势**：
- **流程统一**：定义统一的存储流程
- **步骤复用**：公共步骤可以在子类中复用
- **易于维护**：修改流程只需修改模板方法

## 使用示例

### 1. 基本会话管理

```python
from aiecs.domain.context.content_engine import ContextEngine

# 初始化内容引擎
engine = ContextEngine(use_existing_redis=True)
await engine.initialize()

# 创建会话
session = await engine.create_session(
    session_id="user_123_session_001",
    user_id="user_123",
    metadata={"source": "web", "version": "1.0"}
)

# 更新会话指标
await engine.update_session(
    session_id="user_123_session_001",
    increment_requests=True,
    add_processing_time=1.5,
    mark_error=False
)

# 结束会话
await engine.end_session("user_123_session_001", status="completed")
```

### 2. 对话历史管理

```python
# 添加对话消息
await engine.add_conversation_message(
    session_id="user_123_session_001",
    role="user",
    content="Hello, I need help with data analysis",
    metadata={"message_type": "query", "priority": "normal"}
)

await engine.add_conversation_message(
    session_id="user_123_session_001",
    role="assistant",
    content="I'd be happy to help you with data analysis. What specific data do you have?",
    metadata={"message_type": "response", "confidence": 0.95}
)

# 获取对话历史
history = await engine.get_conversation_history(
    session_id="user_123_session_001",
    limit=10
)

for message in history:
    print(f"{message.role}: {message.content}")
```

### 3. 任务上下文管理

```python
from aiecs.domain.task.task_context import TaskContext

# 创建任务上下文
context = TaskContext(
    mode="execute",
    service="data_analysis",
    user_id="user_123",
    metadata={"task_type": "analysis"},
    data={"dataset": "sales_data.csv"}
)

# 存储上下文
await engine.store_task_context("user_123_session_001", context)

# 检索上下文
retrieved_context = await engine.get_task_context("user_123_session_001")
if retrieved_context:
    print(f"Task mode: {retrieved_context.mode}")
    print(f"Service: {retrieved_context.service}")
```

### 4. 检查点管理

```python
# 存储检查点
checkpoint_data = {
    "workflow_state": "data_processing",
    "current_step": "data_cleaning",
    "processed_records": 1000,
    "errors": []
}

await engine.store_checkpoint(
    thread_id="workflow_001",
    checkpoint_id="checkpoint_001",
    checkpoint_data=checkpoint_data,
    metadata={"workflow_version": "1.0", "created_by": "system"}
)

# 获取检查点
checkpoint = await engine.get_checkpoint(
    thread_id="workflow_001",
    checkpoint_id="checkpoint_001"
)

if checkpoint:
    print(f"Workflow state: {checkpoint['data']['workflow_state']}")
    print(f"Current step: {checkpoint['data']['current_step']}")
```

### 5. 高级对话会话管理

```python
# 创建对话会话
conversation_session = await engine.create_conversation_session(
    participants=[
        ConversationParticipant("user_123", "user"),
        ConversationParticipant("agent_001", "agent", "data_analyst")
    ],
    session_type="user_to_agent",
    metadata={"project": "sales_analysis", "priority": "high"}
)

# 添加代理通信消息
await engine.add_agent_communication_message(
    conversation_session_id=conversation_session.session_id,
    sender_id="agent_001",
    sender_type="agent",
    sender_role="data_analyst",
    content="I've analyzed your sales data and found some interesting patterns.",
    message_type="analysis_result",
    metadata={"analysis_id": "analysis_001", "confidence": 0.92}
)

# 获取代理对话历史
agent_history = await engine.get_agent_conversation_history(
    conversation_session_id=conversation_session.session_id,
    limit=20
)
```

## 维护指南

### 1. 日常维护

#### 健康检查
```python
async def check_engine_health(engine: ContextEngine):
    """检查内容引擎健康状态"""
    health_status = await engine.health_check()
    
    print(f"Engine Status: {health_status['status']}")
    print(f"Storage Backend: {health_status['storage_backend']}")
    print(f"Active Sessions: {health_status['active_sessions']}")
    print(f"Total Messages: {health_status['total_messages']}")
    
    if health_status['status'] != 'healthy':
        print(f"Health Issues: {health_status.get('issues', [])}")
    
    return health_status['status'] == 'healthy'
```

#### 性能监控
```python
async def monitor_engine_performance(engine: ContextEngine):
    """监控内容引擎性能"""
    metrics = await engine.get_metrics()
    
    print("=== Content Engine Metrics ===")
    print(f"Total Sessions: {metrics['total_sessions']}")
    print(f"Active Sessions: {metrics['active_sessions']}")
    print(f"Total Messages: {metrics['total_messages']}")
    print(f"Total Checkpoints: {metrics['total_checkpoints']}")
    
    # 检查内存使用
    if 'memory_usage' in metrics:
        print(f"Memory Usage: {metrics['memory_usage']}")
    
    # 检查存储性能
    if 'storage_performance' in metrics:
        perf = metrics['storage_performance']
        print(f"Average Response Time: {perf['avg_response_time']:.3f}s")
        print(f"Cache Hit Rate: {perf['cache_hit_rate']:.2%}")
```

### 2. 故障排查

#### 常见问题诊断

**问题1: Redis 连接失败**
```python
async def diagnose_redis_connection(engine: ContextEngine):
    """诊断 Redis 连接问题"""
    try:
        # 检查 Redis 客户端状态
        if engine.redis_client:
            await engine.redis_client.ping()
            print("✅ Redis connection is healthy")
        else:
            print("⚠️ Redis client is None, using memory storage")
        
        # 检查健康状态
        health = await engine.health_check()
        print(f"Health status: {health['status']}")
        
        if health['status'] != 'healthy':
            print(f"Health issues: {health.get('issues', [])}")
            
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        
        # 检查环境变量
        import os
        redis_url = os.getenv('REDIS_URL')
        print(f"REDIS_URL: {redis_url}")
        
        # 检查网络连接
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            print(f"Network connectivity: {'ok' if result == 0 else 'failed'}")
        except Exception as net_e:
            print(f"Network check failed: {net_e}")
```

**问题2: 会话数据不一致**
```python
async def diagnose_session_consistency(engine: ContextEngine, session_id: str):
    """诊断会话数据一致性问题"""
    try:
        # 获取会话
        session = await engine.get_session(session_id)
        if not session:
            print(f"❌ Session {session_id} not found")
            return
        
        print(f"✅ Session found: {session.session_id}")
        print(f"User ID: {session.user_id}")
        print(f"Status: {session.status}")
        print(f"Request Count: {session.request_count}")
        print(f"Error Count: {session.error_count}")
        
        # 检查对话历史
        history = await engine.get_conversation_history(session_id, limit=5)
        print(f"Recent messages: {len(history)}")
        
        # 检查任务上下文
        context = await engine.get_task_context(session_id)
        if context:
            print(f"Task context: {context.mode} - {context.service}")
        else:
            print("No task context found")
        
        # 检查检查点
        checkpoints = await engine.list_checkpoints(session_id, limit=5)
        print(f"Checkpoints: {len(checkpoints)}")
        
    except Exception as e:
        print(f"❌ Session consistency check failed: {e}")
```

### 3. 性能优化

#### 内存使用优化
```python
async def optimize_memory_usage(engine: ContextEngine):
    """优化内存使用"""
    # 清理过期会话
    cleaned_count = await engine.cleanup_expired_sessions(max_idle_hours=24)
    print(f"Cleaned up {cleaned_count} expired sessions")
    
    # 检查内存使用
    metrics = await engine.get_metrics()
    if 'memory_usage' in metrics:
        memory_usage = metrics['memory_usage']
        print(f"Current memory usage: {memory_usage}")
        
        # 如果内存使用过高，进行清理
        if memory_usage > 0.8:  # 80% 阈值
            print("Memory usage high, performing cleanup...")
            # 执行额外的清理操作
            await engine.cleanup_expired_sessions(max_idle_hours=12)
```

#### 存储性能优化
```python
async def optimize_storage_performance(engine: ContextEngine):
    """优化存储性能"""
    # 检查存储性能指标
    metrics = await engine.get_metrics()
    
    if 'storage_performance' in metrics:
        perf = metrics['storage_performance']
        
        # 检查响应时间
        if perf['avg_response_time'] > 0.1:  # 100ms 阈值
            print("Storage response time is high, checking connection...")
            health = await engine.health_check()
            print(f"Storage health: {health}")
        
        # 检查缓存命中率
        if perf['cache_hit_rate'] < 0.8:  # 80% 阈值
            print("Cache hit rate is low, consider increasing cache size")
```

### 4. 数据迁移

#### 会话数据迁移
```python
async def migrate_session_data(source_engine: ContextEngine, target_engine: ContextEngine):
    """迁移会话数据"""
    print("Starting session data migration...")
    
    # 获取所有会话（需要实现 list_sessions 方法）
    # 这里假设有获取所有会话的方法
    sessions = await source_engine.list_all_sessions()
    
    migrated_count = 0
    for session in sessions:
        try:
            # 迁移会话
            await target_engine.create_session(
                session.session_id,
                session.user_id,
                session.metadata
            )
            
            # 迁移对话历史
            history = await source_engine.get_conversation_history(session.session_id)
            for message in history:
                await target_engine.add_conversation_message(
                    session.session_id,
                    message.role,
                    message.content,
                    message.metadata
                )
            
            # 迁移任务上下文
            context = await source_engine.get_task_context(session.session_id)
            if context:
                await target_engine.store_task_context(session.session_id, context)
            
            migrated_count += 1
            print(f"Migrated session: {session.session_id}")
            
        except Exception as e:
            print(f"Failed to migrate session {session.session_id}: {e}")
    
    print(f"Migration completed: {migrated_count} sessions migrated")
```

## 监控与日志

### 性能监控
```python
import time
from typing import Dict, Any

class ContentEngineMonitor:
    """内容引擎监控器"""
    
    def __init__(self, engine: ContextEngine):
        self.engine = engine
        self.operation_metrics = {
            "session_operations": [],
            "conversation_operations": [],
            "checkpoint_operations": []
        }
    
    async def record_operation(self, operation_type: str, operation: str, 
                             latency: float, success: bool):
        """记录操作指标"""
        metric = {
            "operation_type": operation_type,
            "operation": operation,
            "latency": latency,
            "success": success,
            "timestamp": time.time()
        }
        
        self.operation_metrics[f"{operation_type}_operations"].append(metric)
        
        # 保持最近1000条记录
        if len(self.operation_metrics[f"{operation_type}_operations"]) > 1000:
            self.operation_metrics[f"{operation_type}_operations"] = \
                self.operation_metrics[f"{operation_type}_operations"][-1000:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {}
        
        for operation_type, metrics in self.operation_metrics.items():
            if not metrics:
                continue
            
            latencies = [m["latency"] for m in metrics]
            successes = [m["success"] for m in metrics]
            
            report[operation_type] = {
                "total_operations": len(metrics),
                "success_rate": sum(successes) / len(successes) if successes else 0,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "min_latency": min(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0
            }
        
        return report
```

### 日志记录
```python
import logging
from typing import Dict, Any

class ContentEngineLogger:
    """内容引擎日志记录器"""
    
    def __init__(self, engine: ContextEngine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
    
    async def log_session_operation(self, operation: str, session_id: str, 
                                  success: bool, latency: float, error: str = None):
        """记录会话操作日志"""
        log_data = {
            "operation": operation,
            "session_id": session_id,
            "success": success,
            "latency": latency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            log_data["error"] = error
        
        if success:
            self.logger.info(f"Session operation completed: {log_data}")
        else:
            self.logger.error(f"Session operation failed: {log_data}")
    
    async def log_conversation_operation(self, operation: str, session_id: str,
                                       message_count: int, success: bool):
        """记录对话操作日志"""
        log_data = {
            "operation": operation,
            "session_id": session_id,
            "message_count": message_count,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"Conversation operation completed: {log_data}")
        else:
            self.logger.error(f"Conversation operation failed: {log_data}")
```

## 版本历史

- **v1.0.0**: 初始版本，基础会话管理功能
- **v1.1.0**: 添加对话历史管理
- **v1.2.0**: 添加任务上下文管理
- **v1.3.0**: 添加检查点管理
- **v1.4.0**: 添加多存储后端支持
- **v1.5.0**: 添加高级对话会话管理
- **v1.6.0**: 添加性能监控和日志记录

## 相关文档

- [AIECS 项目总览](../PROJECT_SUMMARY.md)
- [存储接口文档](./STORAGE_INTERFACES.md)
- [执行接口文档](./EXECUTION_INTERFACES.md)
- [配置管理文档](./CONFIG_MANAGEMENT.md)
