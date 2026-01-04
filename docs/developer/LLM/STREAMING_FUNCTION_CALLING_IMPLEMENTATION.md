# Streaming Function Calling 完整实现

## 概述

已实现完整的 streaming function calling 支持，可以实时累积 tool_calls，并在流式传输过程中处理工具调用。

## 实现内容

### 1. StreamChunk 数据结构

**新文件**: `aiecs/llm/clients/openai_compatible_mixin.py`

创建了 `StreamChunk` 数据类来表示流式响应中的不同类型数据：

```python
@dataclass
class StreamChunk:
    type: str  # "token", "tool_call", or "tool_calls"
    content: Optional[str] = None  # Text token content
    tool_call: Optional[Dict[str, Any]] = None  # Tool call information (partial)
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Complete tool calls (at end)
```

### 2. 实时累积 Tool Calls

**修改**: `OpenAICompatibleFunctionCallingMixin._stream_text_with_function_calling()`

**改进**:
- ✅ 实时累积 tool_calls（在流式传输过程中）
- ✅ 支持 `return_chunks` 参数控制返回格式
- ✅ 当 `return_chunks=True` 时，返回 `StreamChunk` 对象
- ✅ 当 `return_chunks=False` 时，只返回字符串 tokens（向后兼容）

**实现逻辑**:
```python
# 累积器字典，按 call_id 组织
tool_calls_accumulator: Dict[str, Dict[str, Any]] = {}

# 在流式传输过程中累积
for tool_call_delta in delta.tool_calls:
    call_id = tool_call_delta.id
    # 初始化或更新累积器
    if call_id not in tool_calls_accumulator:
        tool_calls_accumulator[call_id] = {...}
    # 累积 function name 和 arguments
    tool_calls_accumulator[call_id]["function"]["name"] = ...
    tool_calls_accumulator[call_id]["function"]["arguments"] += ...
    
    # 实时 yield tool_call 更新
    if return_chunks:
        yield StreamChunk(type="tool_call", tool_call=...)

# 流结束时 yield 完整的 tool_calls
if tool_calls_accumulator and return_chunks:
    yield StreamChunk(type="tool_calls", tool_calls=...)
```

### 3. 更新 LLM Clients

**修改**: `OpenAIClient` 和 `XAIClient`

**更新**:
- ✅ 添加 `return_chunks` 参数支持
- ✅ 返回类型更新为 `AsyncGenerator[Any, None]`
- ✅ 导出 `StreamChunk` 类

### 4. HybridAgent Streaming 模式更新

**修改**: `HybridAgent._react_loop_streaming()`

**改进**:
- ✅ 自动检测并使用 `return_chunks=True`
- ✅ 实时处理 tool_calls
- ✅ 自动执行工具并 yield 结果
- ✅ 支持多种事件类型：`token`, `tool_call_update`, `tool_calls`, `tool_result`, `tool_error`

**事件类型**:
```python
# Token 事件
{"type": "token", "content": "...", "timestamp": "..."}

# Tool call 更新事件（实时）
{"type": "tool_call_update", "tool_call": {...}, "timestamp": "..."}

# 完整 tool_calls 事件（流结束时）
{"type": "tool_calls", "tool_calls": [...], "timestamp": "..."}

# Tool 执行结果事件
{"type": "tool_result", "tool_name": "...", "result": "...", "timestamp": "..."}

# Tool 错误事件
{"type": "tool_error", "tool_name": "...", "error": "...", "timestamp": "..."}
```

## 使用示例

### 基础用法（向后兼容）

```python
# 只获取 tokens（默认行为）
async for token in client.stream_text(messages, tools=tools):
    print(token, end="")
```

### 完整用法（包含 tool_calls）

```python
from aiecs.llm.clients import StreamChunk

# 获取完整信息（包括 tool_calls）
async for chunk in client.stream_text(
    messages, 
    tools=tools, 
    return_chunks=True
):
    if isinstance(chunk, StreamChunk):
        if chunk.type == "token":
            # 处理文本 token
            print(chunk.content, end="")
        elif chunk.type == "tool_call":
            # 实时处理 tool_call 更新
            print(f"Tool call update: {chunk.tool_call}")
        elif chunk.type == "tool_calls":
            # 处理完整的 tool_calls
            for tool_call in chunk.tool_calls:
                execute_tool(tool_call)
```

### HybridAgent Streaming

```python
# HybridAgent 自动处理 streaming tool_calls
async for event in agent.execute_task_streaming(task, context):
    if event["type"] == "token":
        print(event["content"], end="")
    elif event["type"] == "tool_call":
        print(f"Calling tool: {event['tool_name']}")
    elif event["type"] == "tool_result":
        print(f"Tool result: {event['result']}")
```

## 技术细节

### Tool Calls 累积机制

1. **初始化**: 为每个 `call_id` 创建累积器条目
2. **累积**: 逐步添加 `function.name` 和 `function.arguments`
3. **实时更新**: 每次更新时 yield `tool_call` 事件
4. **完成**: 流结束时 yield 完整的 `tool_calls` 列表

### 向后兼容性

- ✅ **默认行为**: `return_chunks=False`，只返回字符串 tokens
- ✅ **类型检查**: 调用者可以检查返回值类型
- ✅ **渐进增强**: 需要 tool_calls 时设置 `return_chunks=True`

### 性能考虑

- ✅ **实时处理**: tool_calls 在流式传输过程中实时累积
- ✅ **内存效率**: 只累积必要的 tool_call 信息
- ✅ **事件驱动**: 支持实时响应 tool_call 更新

## 支持的 Providers

| Provider | Streaming Function Calling | 说明 |
|---------|---------------------------|------|
| **OpenAI** | ✅ 完全支持 | 实时累积 tool_calls |
| **xAI** | ✅ 完全支持 | OpenAI 兼容格式 |
| **Google Vertex AI** | ✅ 完全支持 | Google 格式，自动转换 |
| **Google AI** | ⏳ 待实现 | 需要适配 Google 格式 |

## 测试建议

### 单元测试

1. **StreamChunk 创建和序列化**
2. **Tool calls 累积逻辑**
3. **多种 chunk 类型处理**

### 集成测试

1. **OpenAI streaming with tools**
2. **xAI streaming with tools**
3. **HybridAgent streaming mode**

### 端到端测试

1. **完整任务执行流程**
2. **多个 tool calls**
3. **错误处理**

## 相关文档

- [Streaming Function Calling 说明](./STREAMING_FUNCTION_CALLING_EXPLANATION.md)
- [LLM Providers Function Calling 支持](./LLM_PROVIDERS_FUNCTION_CALLING_SUPPORT.md)
- [HybridAgent Function Calling 实现](./HYBRIDAGENT_FUNCTION_CALLING_IMPLEMENTATION.md)

