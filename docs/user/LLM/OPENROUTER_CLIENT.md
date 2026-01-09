# OpenRouter Client

OpenRouter 客户端支持通过 OpenRouter API 访问多个 LLM 提供商（OpenAI、Anthropic、Google 等）。

## 概述

OpenRouter 是一个统一的 API，可以访问多个 LLM 提供商。本客户端使用 OpenAI SDK（OpenRouter 兼容 OpenAI API 格式），支持：

- ✅ 文本生成
- ✅ 流式输出
- ✅ Function Calling
- ✅ Vision（图片输入）
- ✅ 多个模型提供商

## 配置

### 环境变量

```bash
# 必需：OpenRouter API Key
export OPENROUTER_API_KEY="sk-or-v1-..."

# 可选：用于 OpenRouter 排行榜的额外头部信息
export OPENROUTER_HTTP_REFERER="https://myapp.com"
export OPENROUTER_X_TITLE="My App"
```

### 配置文件

在 `aiecs/config/llm_models.yaml` 中已预配置了多个 OpenRouter 模型：

- `openai/gpt-4o`
- `openai/gpt-4-turbo`
- `anthropic/claude-3.5-sonnet`
- `google/gemini-pro-1.5`

## 使用方法

### 基本用法

```python
from aiecs.llm.clients.openrouter_client import OpenRouterClient
from aiecs.llm.clients.base_client import LLMMessage

client = OpenRouterClient()

messages = [
    LLMMessage(
        role="user",
        content="What is the meaning of life?"
    )
]

response = await client.generate_text(
    messages=messages,
    model="openai/gpt-4o"
)

print(response.content)
await client.close()
```

### 使用 Factory

```python
from aiecs.llm.client_factory import LLMClientFactory, AIProvider

client = LLMClientFactory.get_client(AIProvider.OPENROUTER)

response = await client.generate_text(
    messages=messages,
    model="openai/gpt-4o"
)
```

### 流式输出

```python
async for chunk in client.stream_text(
    messages=messages,
    model="openai/gpt-4o"
):
    print(chunk, end="", flush=True)
```

### 使用额外头部信息

OpenRouter 支持可选的额外头部信息用于排行榜：

```python
response = await client.generate_text(
    messages=messages,
    model="openai/gpt-4o",
    http_referer="https://myapp.com",  # 可选
    x_title="My App"  # 可选
)
```

也可以通过环境变量设置：

```bash
export OPENROUTER_HTTP_REFERER="https://myapp.com"
export OPENROUTER_X_TITLE="My App"
```

### Vision 支持

```python
messages = [
    LLMMessage(
        role="user",
        content="What's in this image?",
        images=["https://example.com/image.jpg"]
    )
]

response = await client.generate_text(
    messages=messages,
    model="openai/gpt-4o"  # Vision-capable model
)
```

### Function Calling

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = await client.generate_text(
    messages=messages,
    model="openai/gpt-4o",
    tools=tools
)

if response.tool_calls:
    print(f"Tool calls: {response.tool_calls}")
```

## 支持的模型

OpenRouter 支持多个提供商的模型。常用模型包括：

### OpenAI
- `openai/gpt-4o`
- `openai/gpt-4-turbo`
- `openai/gpt-3.5-turbo`

### Anthropic
- `anthropic/claude-3.5-sonnet`
- `anthropic/claude-3-opus`

### Google
- `google/gemini-pro-1.5`
- `google/gemini-pro`

### 其他
- `meta-llama/llama-3.1-405b-instruct`
- `mistralai/mixtral-8x7b-instruct`

查看 [OpenRouter Models](https://openrouter.ai/models) 获取完整列表。

## 模型映射

可以在 `llm_models.yaml` 中配置模型映射：

```yaml
openrouter:
  provider_name: "OpenRouter"
  default_model: "openai/gpt-4o"
  model_mappings:
    "GPT-4o": "openai/gpt-4o"
    "Claude 3.5": "anthropic/claude-3.5-sonnet"
```

## 错误处理

```python
from aiecs.llm.clients.base_client import ProviderNotAvailableError, RateLimitError

try:
    response = await client.generate_text(messages=messages, model="openai/gpt-4o")
except ProviderNotAvailableError as e:
    print(f"Configuration error: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
except Exception as e:
    print(f"Other error: {e}")
```

## 特性

### 1. OpenAI 兼容

OpenRouter API 完全兼容 OpenAI API 格式，因此：
- 支持所有 OpenAI SDK 功能
- 支持 Function Calling
- 支持 Vision
- 支持 Streaming

### 2. 多提供商支持

通过一个 API Key 访问多个提供商：
- OpenAI
- Anthropic
- Google
- Meta
- Mistral
- 等等

### 3. 统一接口

使用与其他 LLM 客户端相同的接口：
- `generate_text()`
- `stream_text()`
- `close()`

### 4. 配置管理

- 支持环境变量配置
- 支持 YAML 配置文件
- 支持模型映射

## 示例代码

完整示例请参考 `examples/openrouter_example.py`：

```python
# 基本使用
asyncio.run(example_basic())

# 带额外头部信息
asyncio.run(example_with_extra_headers())

# 流式输出
asyncio.run(example_streaming())

# Vision
asyncio.run(example_vision())

# Function Calling
asyncio.run(example_function_calling())
```

## 注意事项

1. **API Key**: 需要有效的 OpenRouter API Key
2. **模型名称**: 使用完整的模型名称（如 `openai/gpt-4o`）
3. **成本**: 不同模型的定价不同，查看 OpenRouter 定价页面
4. **速率限制**: 遵循 OpenRouter 的速率限制策略
5. **额外头部**: `HTTP-Referer` 和 `X-Title` 是可选的，用于排行榜

## 与其他客户端的区别

| 特性 | OpenRouter | OpenAI | xAI |
|------|-----------|--------|-----|
| 多提供商 | ✅ | ❌ | ❌ |
| 统一 API | ✅ | ❌ | ❌ |
| 额外头部 | ✅ | ❌ | ❌ |
| 模型选择 | 多个 | OpenAI 模型 | Grok 模型 |

## 故障排除

### API Key 未配置

```
ProviderNotAvailableError: OpenRouter API key not configured
```

**解决方案**: 设置 `OPENROUTER_API_KEY` 环境变量

### 模型不存在

```
Error: Model not found
```

**解决方案**: 检查模型名称是否正确（需要包含提供商前缀，如 `openai/`）

### 速率限制

```
RateLimitError: OpenRouter rate limit exceeded
```

**解决方案**: 等待后重试，或升级 OpenRouter 计划
