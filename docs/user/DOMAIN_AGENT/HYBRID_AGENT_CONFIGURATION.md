# HybridAgent Configuration Guide

本文档说明如何配置 HybridAgent 的参数，特别是 `max_tokens` 和 `max_iterations`。

## 配置参数

### max_tokens

**用途**: 控制每次 LLM 调用生成的最大 token 数量

**配置方式**: 只能通过 `AgentConfiguration` 配置

**默认值**: 4096

**示例**:
```python
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.hybrid_agent import HybridAgent

# 通过 config 设置 max_tokens
config = AgentConfiguration(max_tokens=8192)

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search"],
    config=config
)
```

### max_iterations

**用途**: 控制 ReAct 循环的最大迭代次数

**配置方式**: 
1. 通过 `AgentConfiguration` 配置（推荐）
2. 通过构造函数参数（会覆盖 config 值）

**默认值**: 10

**优先级**: 构造函数参数 > config.max_iterations

**示例**:

```python
# 方式 1: 通过 config（推荐）
config = AgentConfiguration(max_iterations=5)

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search"],
    config=config
    # 使用 config.max_iterations = 5
)

# 方式 2: 通过构造函数参数（覆盖 config）
config = AgentConfiguration(max_iterations=5)

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    max_iterations=3  # 覆盖 config，使用 3
)
```

## 完整配置示例

```python
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.llm.clients.openai_client import OpenAIClient

# 创建配置
config = AgentConfiguration(
    max_tokens=8192,        # LLM 最大 token 数
    max_iterations=5,       # ReAct 最大迭代次数
    temperature=0.7,
    llm_model="gpt-4o"
)

# 创建 agent
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator"],
    config=config
)

await agent.initialize()
```

## 配置对比

| 参数 | 配置方式 | 默认值 | 优先级 |
|------|---------|--------|--------|
| `max_tokens` | 仅 config | 4096 | config.max_tokens |
| `max_iterations` | config 或构造函数 | 10 | 构造函数 > config.max_iterations |

## 使用建议

1. **推荐方式**: 使用 `AgentConfiguration` 统一配置所有参数
   ```python
   config = AgentConfiguration(
       max_tokens=8192,
       max_iterations=5
   )
   ```

2. **特殊情况**: 如果需要在运行时动态调整 `max_iterations`，可以使用构造函数参数
   ```python
   # 根据任务复杂度动态调整
   iterations = 10 if is_complex_task else 5
   agent = HybridAgent(..., max_iterations=iterations)
   ```

3. **一致性**: `max_tokens` 和 `max_iterations` 都可以通过 config 配置，保持配置的一致性

## 实现细节

- `max_tokens` 在每次 LLM 调用时使用：`self._config.max_tokens`
- `max_iterations` 在 ReAct 循环中使用：`self._max_iterations`
- 如果构造函数未提供 `max_iterations`（None），则使用 `config.max_iterations`
- 如果构造函数明确提供了 `max_iterations`，则优先使用构造函数值

## 相关文件

- `aiecs/domain/agent/models.py`: `AgentConfiguration` 定义
- `aiecs/domain/agent/hybrid_agent.py`: `HybridAgent` 实现
- `test/unit/domain/agent/test_hybrid_agent_max_tokens_config.py`: 配置测试
