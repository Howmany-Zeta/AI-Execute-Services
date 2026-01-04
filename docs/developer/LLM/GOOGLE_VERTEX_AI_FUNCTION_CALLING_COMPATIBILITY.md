# Google Vertex AI Function Calling 兼容性分析

## 当前设计状态

### 架构设计
- ✅ **OpenAICompatibleFunctionCallingMixin**: 为 OpenAI 兼容的 providers 提供统一实现
- ✅ **GoogleFunctionCallingMixin**: 为 Google providers 提供统一实现
- ✅ **BaseLLMClient**: 抽象基类，定义接口
- ✅ **VertexAIClient**: 已实现 Function Calling 支持（包括 Streaming）

### HybridAgent 检测逻辑
```python
supported_providers = ["openai", "xai", "anthropic", "vertex"]
# Google Vertex AI uses FunctionDeclaration format, handled via GoogleFunctionCallingMixin
```

## Google Vertex AI Function Calling 格式

### API 格式差异

**OpenAI 格式**:
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "...",
            "parameters": {...}
        }
    }
]
```

**Google Vertex AI 格式**:
```python
from vertexai.generative_models import FunctionDeclaration, Schema

tools = [
    FunctionDeclaration(
        name="tool_name",
        description="...",
        parameters=Schema(
            type=Type.OBJECT,
            properties={...}
        )
    )
]
```

### 关键差异

1. **类型系统**:
   - OpenAI: JSON Schema (dict)
   - Vertex AI: `FunctionDeclaration` 和 `Schema` 对象

2. **参数格式**:
   - OpenAI: 嵌套字典结构
   - Vertex AI: 强类型对象 (`Type.OBJECT`, `Type.STRING`, 等)

3. **响应格式**:
   - OpenAI: `tool_calls` 数组
   - Vertex AI: `function_calls` 或 `functionCall` (取决于 API 版本)

## 兼容性评估

### ✅ 设计兼容性

**当前设计完全兼容**，原因：

1. **Mixin 模式**: 
   - 每个 Provider 可以选择使用不同的 Mixin
   - Vertex AI 可以使用独立的 `GoogleFunctionCallingMixin`
   - 不影响现有的 OpenAI 兼容实现

2. **接口统一**:
   - `BaseLLMClient.generate_text()` 接受 `tools` 和 `functions` 参数
   - 各 Provider 可以内部转换格式
   - 对外接口保持一致

3. **HybridAgent 自动检测**:
   - 通过方法签名检测是否支持 Function Calling
   - 如果 Vertex AI 实现了 `tools` 参数，会自动启用

### ⚠️ 需要实现的内容

1. **格式转换函数**:
   ```python
   def convert_openai_to_vertex_format(openai_tools: List[Dict]) -> List[FunctionDeclaration]:
       """Convert OpenAI tools format to Vertex AI FunctionDeclaration format"""
       pass
   ```

2. **响应解析**:
   ```python
   def extract_vertex_function_calls(response) -> List[Dict]:
       """Extract function calls from Vertex AI response"""
       pass
   ```

3. **GoogleFunctionCallingMixin** (可选):
   - 如果多个 Google providers 使用相同格式，可以创建 Mixin
   - 或者直接在 VertexAIClient 中实现

## 实现方案

### 方案 1: 创建 GoogleFunctionCallingMixin (推荐)

**优点**:
- 代码复用（如果 Google AI 也使用相同格式）
- 与现有架构一致
- 易于维护

**实现**:
```python
class GoogleFunctionCallingMixin:
    """Mixin for Google Vertex AI Function Calling format"""
    
    def _convert_openai_to_vertex_format(self, tools: List[Dict]) -> List[FunctionDeclaration]:
        """Convert OpenAI format to Vertex AI format"""
        from vertexai.generative_models import FunctionDeclaration, Schema, Type
        
        vertex_tools = []
        for tool in tools:
            func = tool.get("function", {})
            vertex_tools.append(
                FunctionDeclaration(
                    name=func["name"],
                    description=func.get("description", ""),
                    parameters=self._convert_schema(func.get("parameters", {}))
                )
            )
        return vertex_tools
    
    def _convert_schema(self, schema: Dict) -> Schema:
        """Convert JSON Schema to Vertex AI Schema"""
        # Implementation
        pass
```

### 方案 2: 直接在 VertexAIClient 中实现

**优点**:
- 简单直接
- 不需要额外的 Mixin

**缺点**:
- 如果 Google AI 也使用相同格式，会有代码重复

### 方案 3: 适配 OpenAI 格式 (如果 API 支持)

**如果 Google Vertex AI SDK 支持 OpenAI 格式**:
- 可以直接使用 `OpenAICompatibleFunctionCallingMixin`
- 需要验证 API 是否支持

## 推荐实现步骤

### 1. 验证 API 兼容性
```python
# 测试 Vertex AI 是否支持 OpenAI 格式
# 如果支持，可以直接使用 OpenAICompatibleFunctionCallingMixin
```

### 2. 实现格式转换
```python
# 如果不支持，实现格式转换函数
def convert_openai_to_vertex_format(...):
    pass
```

### 3. 更新 VertexAIClient
```python
class VertexAIClient(BaseLLMClient, GoogleFunctionCallingMixin):
    async def generate_text(self, messages, tools=None, functions=None, ...):
        if tools or functions:
            # Convert to Vertex AI format
            vertex_tools = self._convert_openai_to_vertex_format(tools or functions)
            # Use in API call
        ...
```

### 4. 更新 HybridAgent 检测
```python
supported_providers = ["openai", "xai", "anthropic", "vertexai"]
```

## 兼容性结论

### ✅ 架构兼容性: **完全兼容**

当前设计完全支持 Google Vertex AI 的 Function Calling：

1. **Mixin 模式**: 允许每个 Provider 有独立的实现
2. **接口统一**: `tools` 和 `functions` 参数统一
3. **自动检测**: HybridAgent 可以自动检测支持情况

### ✅ 实现状态: **已完成**

已完成：
1. ✅ 格式转换函数 (`GoogleFunctionCallingMixin._convert_openai_to_google_format`)
2. ✅ VertexAIClient 的 Function Calling 支持
3. ✅ 响应解析 (`_extract_function_calls_from_google_response`)
4. ⏳ 测试验证（待完成）

### ✅ 实现完成

1. ✅ 创建 `GoogleFunctionCallingMixin` 类
2. ✅ 实现格式转换函数 (`_convert_openai_to_google_format`)
3. ✅ 实现 JSON Schema 到 Google Schema 转换
4. ✅ 实现响应解析 (`_extract_function_calls_from_google_response`)
5. ✅ 更新 `VertexAIClient` 使用 Mixin
6. ✅ 更新 `HybridAgent` 检测逻辑（添加 "vertex" 支持）
7. ✅ **实现 Streaming Function Calling 支持**
   - ✅ 实时累积 tool_calls
   - ✅ 支持 `return_chunks` 参数
   - ✅ 返回 `StreamChunk` 对象（与 OpenAI 兼容）
   - ✅ 处理 safety blocks
8. ⏳ 添加测试（待完成）

### 📋 下一步

1. ⏳ 添加单元测试和集成测试
2. ⏳ 验证实际 API 调用
3. ⏳ 处理 edge cases（如嵌套 schema、数组类型等）
4. ✅ Streaming Function Calling 支持（已完成）

## 相关文档

- [Function Calling 架构设计](./ARCHITECTURE_FUNCTION_CALLING.md)
- [LLM Providers Function Calling 支持](./LLM_PROVIDERS_FUNCTION_CALLING_SUPPORT.md)
- [HybridAgent Function Calling 实现](./HYBRIDAGENT_FUNCTION_CALLING_IMPLEMENTATION.md)

