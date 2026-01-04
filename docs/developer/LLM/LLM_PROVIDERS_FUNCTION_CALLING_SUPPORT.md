# LLM Providers Function Calling 支持情况

## 概述

本文档说明各个 LLM Provider 对 OpenAI Function Calling 格式的支持情况。

## 支持状态

| Provider | 支持状态 | 格式 | 说明 |
|---------|---------|------|------|
| **OpenAI** | ✅ 完全支持 | OpenAI 原生格式 | `tools` 和 `functions` 参数 |
| **xAI (Grok)** | ✅ 完全支持 | OpenAI 兼容格式 | 使用 OpenAI SDK，完全兼容 |
| **Google Vertex AI** | ⚠️ 部分支持 | FunctionDeclaration 格式 | 需要格式转换 |
| **Google AI** | ⚠️ 部分支持 | FunctionDeclaration 格式 | 需要格式转换 |
| **Anthropic** | ⚠️ 待实现 | 自定义格式 | 需要单独实现 |

## 实现详情

### ✅ OpenAI

**状态**: 完全支持

**实现**:
- `generate_text()` 支持 `tools` 和 `functions` 参数
- `stream_text()` 支持 `tools` 参数
- 正确处理 `function_call` 和 `tool_calls` 响应

**文件**: `aiecs/llm/clients/openai_client.py`

### ✅ xAI (Grok)

**状态**: 完全支持（OpenAI 兼容）

**实现**:
- xAI API 使用 OpenAI 兼容格式
- 直接使用 OpenAI SDK
- 完全支持 `tools` 和 `functions` 参数
- 正确处理 `tool_calls` 响应

**文件**: `aiecs/llm/clients/xai_client.py`

**注意**: xAI 的 API 与 OpenAI 完全兼容，所以可以直接使用相同的格式。

### ✅ Google Vertex AI

**状态**: 完全支持（包括 Streaming Function Calling）

**当前实现**:
- ✅ 已实现 Function Calling 支持（非流式）
- ✅ 已实现 Streaming Function Calling 支持（流式）
- ✅ Google Vertex AI 使用 `FunctionDeclaration` 格式，自动转换

**架构兼容性**:
- ✅ **完全兼容**: 使用 `GoogleFunctionCallingMixin` 实现
- ✅ **接口统一**: `tools` 和 `functions` 参数统一
- ✅ **自动检测**: HybridAgent 自动检测并启用
- ✅ **Streaming 支持**: 实时累积 tool_calls

**格式转换**:
- ✅ 自动将 OpenAI 格式转换为 Google `FunctionDeclaration` 格式
- ✅ 自动将 Google 响应转换为 OpenAI 兼容格式

**Streaming Function Calling**:
- ✅ 支持 `return_chunks` 参数
- ✅ 实时累积 tool_calls
- ✅ 返回 `StreamChunk` 对象（与 OpenAI 兼容）

**详细分析**: 请参阅 [Google Vertex AI Function Calling 兼容性](./GOOGLE_VERTEX_AI_FUNCTION_CALLING_COMPATIBILITY.md)

### ⚠️ Google AI

**状态**: 部分支持（需要格式转换）

**当前实现**:
- 尚未实现 Function Calling 支持
- Google AI 使用 `FunctionDeclaration` 格式

**未来实现**:
- 与 Vertex AI 类似的格式转换
- 支持 Gemini 模型的 Function Calling

### ⚠️ Anthropic

**状态**: 待实现

**说明**:
- Anthropic 使用自定义的 tool use 格式
- 需要单独实现格式转换

## HybridAgent 自动检测

HybridAgent 会自动检测 LLM 是否支持 Function Calling：

1. **Provider 名称检测**:
   - 检查 provider_name 是否在支持列表中
   - 当前支持: `["openai", "xai", "anthropic"]`

2. **方法签名检测**:
   - 检查 `generate_text()` 方法是否接受 `tools` 或 `functions` 参数
   - 如果接受，则认为支持 Function Calling

3. **Fallback**:
   - 如果不支持，自动使用 ReAct 模式
   - 完全向后兼容

## 使用示例

### OpenAI (完全支持)

```python
from aiecs.llm import OpenAIClient
from aiecs.domain.agent import HybridAgent

llm_client = OpenAIClient()
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config
)
# ✅ 自动使用 Function Calling
```

### xAI (完全支持)

```python
from aiecs.llm import XAIClient
from aiecs.domain.agent import HybridAgent

llm_client = XAIClient()
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config
)
# ✅ 自动使用 Function Calling (OpenAI 兼容)
```

### Google Vertex AI (当前使用 ReAct 模式)

```python
from aiecs.llm import VertexAIClient
from aiecs.domain.agent import HybridAgent

llm_client = VertexAIClient()
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config
)
# ⚠️ 当前使用 ReAct 模式（Function Calling 待实现）
```

## 未来计划

### 短期（已完成）
- ✅ OpenAI Function Calling 支持
- ✅ xAI Function Calling 支持
- ✅ Streaming Function Calling 基础支持

### 中期（计划中）
- ⏳ Google Vertex AI Function Calling 支持
- ⏳ Google AI Function Calling 支持
- ⏳ Streaming Function Calling 完整支持（tool_calls 累积）

### 长期（考虑中）
- ⏳ Anthropic Function Calling 支持
- ⏳ 其他 providers 的支持

## 技术细节

### 格式转换需求

对于 Google providers，需要实现格式转换：

```python
def convert_openai_to_google_format(openai_tools: List[Dict]) -> List[FunctionDeclaration]:
    """Convert OpenAI tools format to Google FunctionDeclaration format."""
    # Implementation needed
    pass
```

### Streaming Function Calling

✅ **完整支持**: 实时累积 tool_calls，支持在流式传输过程中处理工具调用

**当前实现**:
- ✅ 支持 streaming tokens（实时接收文本内容）
- ✅ 实时累积 tool_calls（在流式传输过程中）
- ✅ 支持 StreamChunk 对象（包含 tokens 和 tool_calls 信息）
- ✅ HybridAgent 自动处理 streaming tool_calls

**使用方式**:

```python
# 方式 1: 只获取 tokens（向后兼容）
async for token in client.stream_text(messages, tools=tools):
    print(token, end="")

# 方式 2: 获取完整信息（包括 tool_calls）
async for chunk in client.stream_text(messages, tools=tools, return_chunks=True):
    if isinstance(chunk, StreamChunk):
        if chunk.type == "token":
            print(chunk.content, end="")
        elif chunk.type == "tool_call":
            # 实时处理 tool_call 更新
            process_tool_call(chunk.tool_call)
        elif chunk.type == "tool_calls":
            # 完整的 tool_calls 列表
            process_all_tool_calls(chunk.tool_calls)
```

**详细说明**: 请参阅 [Streaming Function Calling 说明](./STREAMING_FUNCTION_CALLING_EXPLANATION.md)

## 相关文档

- [HybridAgent Function Calling 实现](./HYBRIDAGENT_FUNCTION_CALLING_IMPLEMENTATION.md)
- [Agent OpenAI Function Calling 分析](./AGENT_OPENAI_FUNCTION_CALLING_ANALYSIS.md)

