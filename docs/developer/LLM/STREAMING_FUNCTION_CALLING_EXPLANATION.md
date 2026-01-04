# Streaming Function Calling 说明

## 什么是 Streaming Function Calling？

Streaming Function Calling 是指在流式传输（streaming）模式下，LLM 调用工具（tools）的功能。

### 两种模式对比

#### 1. 非流式模式（Non-Streaming）

```python
# 一次性返回完整响应
response = await llm_client.generate_text(
    messages=messages,
    tools=tools
)

# tool_calls 在响应中直接可用
if response.tool_calls:
    # 立即处理 tool calls
    for tool_call in response.tool_calls:
        execute_tool(tool_call)
```

**特点**:
- ✅ 响应完整，包含所有信息
- ✅ tool_calls 立即可用
- ❌ 需要等待完整响应

#### 2. 流式模式（Streaming）

```python
# 逐块返回响应
async for token in llm_client.stream_text(
    messages=messages,
    tools=tools
):
    # 实时接收 token
    print(token, end="")
    
# ⚠️ 问题：tool_calls 在哪里？
```

**特点**:
- ✅ 实时接收 tokens，用户体验好
- ✅ 可以显示"打字机效果"
- ⚠️ tool_calls 需要特殊处理

## 为什么 tool_calls 在流的最后出现？

### OpenAI API 的行为

在 OpenAI 的 streaming API 中：

1. **文本 tokens** 先出现：
   ```
   chunk 1: delta.content = "Hello"
   chunk 2: delta.content = " world"
   chunk 3: delta.content = "!"
   ```

2. **tool_calls** 在最后出现：
   ```
   chunk 4: delta.tool_calls = [{
       "id": "call_123",
       "function": {"name": "search", "arguments": ""}
   }]
   chunk 5: delta.tool_calls = [{
       "id": "call_123",
       "function": {"arguments": "{\"query\": \"Python\"}"}
   }]
   ```

**原因**:
- LLM 先生成文本内容
- 然后决定是否需要调用工具
- tool_calls 信息分多个 chunk 传输（累积）

## 当前实现的状态

### ✅ 支持 streaming tokens

```python
# 当前实现可以流式传输文本
async for token in stream_text(messages, tools=tools):
    yield token  # ✅ 正常工作
```

### ⚠️ Tool calls 需要在流完成后处理

**当前限制**:

```python
# 当前实现
async for token in stream_text(messages, tools=tools):
    yield token  # ✅ 可以获取 tokens
    # ❌ 但无法获取 tool_calls（它们在流的最后）

# 流结束后，tool_calls 丢失了
# 需要额外的机制来获取 tool_calls
```

**问题**:
- `stream_text()` 只返回 tokens（字符串）
- tool_calls 信息在流的最后，但当前实现没有累积它们
- 调用者无法知道是否有 tool_calls

### ⏳ 未来：实时累积 tool_calls

**计划改进**:

```python
# 未来实现
async for chunk in stream_text(messages, tools=tools):
    if chunk.type == "token":
        yield chunk.content  # 文本 token
    elif chunk.type == "tool_call":
        # 实时累积 tool_calls
        accumulate_tool_call(chunk.tool_call)
        
# 流结束后，返回累积的 tool_calls
final_tool_calls = get_accumulated_tool_calls()
```

**改进方向**:
1. **实时累积**: 在流式传输过程中累积 tool_calls
2. **返回完整信息**: 流结束后返回累积的 tool_calls
3. **事件驱动**: 可以 yield 不同类型的事件（token、tool_call 等）

## 实际影响

### 当前使用场景

**场景 1: 纯文本生成** ✅
```python
# 不需要 tool calls，只显示文本
async for token in stream_text(messages):
    print(token, end="")
# ✅ 完美工作
```

**场景 2: 需要 tool calls** ⚠️
```python
# 需要 tool calls，但流式传输
async for token in stream_text(messages, tools=tools):
    print(token, end="")
    
# ⚠️ 问题：无法知道是否有 tool_calls
# 解决方案：使用非流式模式
response = await generate_text(messages, tools=tools)
if response.tool_calls:
    # 处理 tool calls
```

### HybridAgent 的处理

在 `HybridAgent` 的 streaming 模式中：

```python
# 当前实现（简化版）
async for token in stream_text(...):
    yield token
    
# ⚠️ tool_calls 丢失了
# 需要 fallback 到非流式模式来获取 tool_calls
```

**当前策略**:
- Streaming 模式主要用于显示文本
- 如果需要 tool calls，使用非流式模式
- 未来会改进 streaming 模式以支持 tool_calls

## 技术细节

### OpenAI Streaming API 格式

```json
// chunk 1-3: 文本内容
{"choices": [{"delta": {"content": "Hello"}}]}
{"choices": [{"delta": {"content": " world"}}]}
{"choices": [{"delta": {"content": "!"}}]}

// chunk 4-5: tool_calls（累积）
{"choices": [{"delta": {"tool_calls": [{"id": "call_123", "function": {"name": "search"}}]}}]}
{"choices": [{"delta": {"tool_calls": [{"id": "call_123", "function": {"arguments": "{\"query\": \"Python\"}"}}]}}]}
```

### 累积 tool_calls 的挑战

1. **多个 tool_calls**: 可能有多个 tool_calls 同时进行
2. **分块传输**: 每个 tool_call 的信息分多个 chunk
3. **ID 匹配**: 需要根据 ID 匹配和累积
4. **JSON 解析**: arguments 可能是分块的 JSON

## 总结

| 方面 | 当前状态 | 说明 |
|------|---------|------|
| **Streaming tokens** | ✅ 支持 | 可以实时接收文本 tokens |
| **Tool calls 处理** | ⚠️ 受限 | 需要在流完成后处理，当前实现未累积 |
| **用户体验** | ✅ 良好 | 文本流式传输体验好 |
| **Tool calls 支持** | ⚠️ 不完整 | 流式模式下无法获取 tool_calls |
| **未来改进** | ⏳ 计划中 | 实时累积 tool_calls，支持事件驱动 |

**建议**:
- 如果只需要文本显示，使用 streaming 模式 ✅
- 如果需要 tool calls，使用非流式模式 ✅
- 等待未来改进以支持 streaming + tool calls ⏳

