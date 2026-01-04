# Function Calling 架构设计

## 问题

为什么 Function Calling 和 Streaming Function Calling 不在 `base_client.py` 中统一实现，而是需要在各个 provider 中分别实现？

## 原因分析

### 1. Provider API 格式差异

不同 LLM Provider 的 API 格式存在显著差异：

| Provider | Function Calling 格式 | 说明 |
|---------|---------------------|------|
| **OpenAI** | `tools` / `functions` 参数 | 标准格式 |
| **xAI** | OpenAI 兼容格式 | 使用 OpenAI SDK |
| **Google Vertex AI** | `FunctionDeclaration` | 完全不同的格式 |
| **Google AI** | `FunctionDeclaration` | 完全不同的格式 |
| **Anthropic** | 自定义 tool use 格式 | 需要单独实现 |

### 2. 响应格式差异

不同 Provider 的响应格式也不同：

- **OpenAI/xAI**: `tool_calls` 数组，包含 `id`, `type`, `function`
- **Google**: `function_calls` 或 `functionCall`，格式不同
- **Anthropic**: `tool_use` blocks，格式完全不同

### 3. BaseLLMClient 是抽象基类

`BaseLLMClient` 是一个抽象基类（ABC），不应该包含具体实现：

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def generate_text(...):
        """Generate text using the provider's API"""
```

它只定义接口，不提供实现。

## 解决方案：Mixin 模式

我们采用了 **Mixin 模式** 来解决代码重复问题：

### OpenAICompatibleFunctionCallingMixin

创建了一个 Mixin 类，为 OpenAI 兼容的 providers 提供统一的实现：

```python
class OpenAICompatibleFunctionCallingMixin:
    """Mixin for OpenAI-compatible Function Calling"""
    
    def _convert_messages_to_openai_format(...):
        """Convert messages to OpenAI format"""
    
    def _prepare_function_calling_params(...):
        """Prepare function calling parameters"""
    
    def _extract_function_calls_from_response(...):
        """Extract function calls from response"""
    
    async def _generate_text_with_function_calling(...):
        """Generate text with Function Calling support"""
    
    async def _stream_text_with_function_calling(...):
        """Stream text with Function Calling support"""
```

### 使用方式

**OpenAI Client**:
```python
class OpenAIClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    async def generate_text(self, ...):
        client = self._get_client()
        return await self._generate_text_with_function_calling(
            client=client, ...
        )
```

**xAI Client**:
```python
class XAIClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    async def generate_text(self, ...):
        client = self._get_openai_client()
        return await self._generate_text_with_function_calling(
            client=client, ...
        )
```

## 优势

### 1. 代码复用
- ✅ OpenAI 和 xAI 共享相同的实现
- ✅ 减少代码重复
- ✅ 统一维护

### 2. 灵活性
- ✅ 每个 provider 可以有自己的实现
- ✅ Google providers 可以使用不同的格式
- ✅ 易于扩展新的 providers

### 3. 清晰的职责分离
- ✅ `BaseLLMClient`: 定义接口
- ✅ `OpenAICompatibleFunctionCallingMixin`: 提供 OpenAI 兼容实现
- ✅ 各个 Client: 实现 provider 特定逻辑

## 为什么不直接在 BaseLLMClient 中实现？

### 1. 违反抽象原则
`BaseLLMClient` 是抽象基类，不应该包含具体实现。如果添加具体实现，会：
- 违反单一职责原则
- 使基类变得臃肿
- 难以维护

### 2. 格式差异太大
不同 Provider 的格式差异太大，无法统一：
- Google 使用 `FunctionDeclaration`
- Anthropic 使用 `tool_use` blocks
- OpenAI 使用 `tools` 参数

### 3. 向后兼容
直接在 `BaseLLMClient` 中添加会影响所有现有实现。

## 未来扩展

### Google Providers

对于 Google providers，可以创建类似的 Mixin：

```python
class GoogleFunctionCallingMixin:
    """Mixin for Google Function Calling format"""
    
    def _convert_openai_to_vertex_format(self, tools):
        """Convert OpenAI format to Google FunctionDeclaration"""
        from vertexai.generative_models import FunctionDeclaration, Schema
        
        # Convert OpenAI tools format to Vertex AI FunctionDeclaration format
        pass
    
    def _extract_google_function_calls(self, response):
        """Extract function calls from Google response"""
        pass
```

**兼容性说明**:
- ✅ **架构兼容**: 当前设计完全支持 Google Vertex AI
- ⚠️ **实现状态**: Vertex AI Function Calling 待实现
- 📋 **格式差异**: Google 使用 `FunctionDeclaration`，需要格式转换

详细分析请参阅: [Google Vertex AI Function Calling 兼容性](./GOOGLE_VERTEX_AI_FUNCTION_CALLING_COMPATIBILITY.md)

### 其他 Providers

每个使用不同格式的 provider 都可以有自己的 Mixin 或独立实现。

## 总结

1. **BaseLLMClient**: 抽象基类，定义接口
2. **Mixin 类**: 为兼容的 providers 提供共享实现
3. **具体 Client**: 实现 provider 特定逻辑

这种架构设计：
- ✅ 减少代码重复
- ✅ 保持灵活性
- ✅ 易于维护和扩展
- ✅ 符合 SOLID 原则

