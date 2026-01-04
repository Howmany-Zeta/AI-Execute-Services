# HybridAgent OpenAI Function Calling 实现

## 概述

已成功更新 HybridAgent 以支持 OpenAI Function Calling 格式，现在工具的 `description` 和 `parameters` 属性会被自动传递给 LLM。

## 修改内容

### 1. ToolSchemaGenerator 增强 ✅

**文件**: `aiecs/domain/agent/tools/schema_generator.py`

**改进**:
- 从 BaseTool 的 Pydantic schema 中提取完整的参数信息
- 使用 Pydantic Field 的 `description` 属性
- 自动识别必需参数
- 支持工具实例直接生成 schema

**新增方法**:
- `_extract_from_pydantic_schema()`: 从 Pydantic schema 提取参数
- `_get_description()`: 从 schema 或方法 docstring 获取描述
- `generate_schemas_for_tool_instances()`: 直接从工具实例生成 schema

### 2. OpenAIClient 支持 Function Calling ✅

**文件**: `aiecs/llm/clients/openai_client.py`

**改进**:
- `generate_text()` 方法支持 `functions` 和 `tools` 参数
- `stream_text()` 方法支持 `tools` 参数
- 处理 `function_call` 和 `tool_calls` 响应
- 支持 `tool_choice` 参数

**响应处理**:
- 提取 `function_call`（旧格式）
- 提取 `tool_calls`（新格式）
- 将 function_call/tool_calls 附加到 LLMResponse

### 3. LLMMessage 增强 ✅

**文件**: `aiecs/llm/clients/base_client.py`

**改进**:
- 添加 `tool_calls` 字段（用于 assistant 消息）
- 添加 `tool_call_id` 字段（用于 tool 消息）
- `content` 字段改为可选（Function Calling 时可能为 None）

### 4. HybridAgent 集成 Function Calling ✅

**文件**: `aiecs/domain/agent/hybrid_agent.py`

**改进**:
- 初始化时生成工具 schema
- 自动检测 LLM 是否支持 Function Calling
- 优先使用 Function Calling（如果支持）
- Fallback 到 ReAct 模式（如果不支持）
- 处理 `tool_calls` 响应
- 正确处理工具执行结果

**新增方法**:
- `_generate_tool_schemas()`: 生成工具 schema
- `_check_function_calling_support()`: 检测 LLM 是否支持 Function Calling

**修改的方法**:
- `_react_loop()`: 支持 Function Calling 模式
- `_build_system_prompt()`: 保持向后兼容（ReAct 模式）

## 工作流程

### Function Calling 模式（优先）

1. **初始化**:
   - 加载工具实例
   - 生成工具 schema（从 Pydantic models）
   - 检测 LLM 是否支持 Function Calling

2. **执行任务**:
   - 构建消息（包含工具 schema）
   - 调用 LLM（传递 `tools` 参数）
   - 处理 `tool_calls` 响应
   - 执行工具
   - 添加工具结果到消息
   - 继续迭代

3. **工具调用格式**:
   ```json
   {
     "id": "call_xxx",
     "type": "function",
     "function": {
       "name": "tool_name_operation",
       "arguments": "{\"param1\": \"value1\"}"
     }
   }
   ```

### ReAct 模式（Fallback）

如果 LLM 不支持 Function Calling，自动 fallback 到 ReAct 模式：
- 使用文本 prompt 描述工具
- LLM 通过文本推理选择工具
- 解析文本响应中的工具调用

## 向后兼容性

✅ **完全向后兼容**:
- 如果 LLM 不支持 Function Calling，自动使用 ReAct 模式
- 现有代码无需修改即可工作
- 工具定义保持不变（使用 BaseTool 和 Pydantic schemas）

## 优势

1. **更准确的工具调用**:
   - LLM 直接看到工具的完整 schema
   - 参数类型和描述自动传递
   - 减少工具调用错误

2. **更好的性能**:
   - 减少 prompt 长度（不需要文本描述所有工具）
   - LLM 可以更高效地选择工具

3. **自动参数验证**:
   - Pydantic schema 确保参数类型正确
   - 必需参数自动识别

## 使用示例

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient
from aiecs.tools import BaseTool

# 定义工具（使用 Pydantic schema）
class SearchTool(BaseTool):
    class SearchSchema(BaseModel):
        query: str = Field(description="Search query string")
        num_results: int = Field(default=5, description="Number of results to return")
    
    def search(self, query: str, num_results: int = 5):
        # Implementation
        pass

# 创建 agent
llm_client = OpenAIClient()
config = AgentConfiguration(llm_model="gpt-4")

agent = HybridAgent(
    agent_id="agent1",
    name="Search Agent",
    llm_client=llm_client,
    tools={"search": SearchTool()},
    config=config
)

# 执行任务 - Function Calling 自动使用
result = await agent.execute_task({
    "description": "搜索 Python 的最新特性"
}, {})
```

## 测试建议

1. **单元测试**:
   - ToolSchemaGenerator 生成正确的 schema
   - OpenAIClient 正确处理 tools 参数
   - HybridAgent 正确检测 Function Calling 支持

2. **集成测试**:
   - 使用真实 OpenAI API 测试 Function Calling
   - 测试 Fallback 到 ReAct 模式
   - 测试工具执行流程

3. **端到端测试**:
   - 完整任务执行流程
   - 多个工具调用
   - 错误处理

## 已知限制

1. **Streaming Function Calling**:
   - Streaming 模式下的 Function Calling 支持需要进一步优化
   - Tool calls 通常在流的最后才出现

2. **其他 LLM Providers**:
   - 目前主要支持 OpenAI
   - 其他 providers（如 Google Vertex AI, xAI）需要单独实现

## 下一步

1. ✅ 完成核心 Function Calling 支持
2. ✅ 优化 Streaming Function Calling（基础支持）
3. ✅ 添加 xAI provider 支持（OpenAI 兼容）
4. ⏳ 添加 Google Vertex AI 和 Google AI 支持（需要格式转换）
5. ⏳ 完善 Streaming Function Calling（tool_calls 实时累积）
6. ⏳ 完善测试覆盖
7. ⏳ 更新文档和示例

## Provider 支持状态

详细支持情况请参阅：[LLM Providers Function Calling 支持](./LLM_PROVIDERS_FUNCTION_CALLING_SUPPORT.md)

### 当前支持
- ✅ **OpenAI**: 完全支持
- ✅ **xAI (Grok)**: 完全支持（OpenAI 兼容）

### 计划支持
- ⏳ **Google Vertex AI**: 需要格式转换
- ⏳ **Google AI**: 需要格式转换
- ⏳ **Anthropic**: 需要单独实现

## 相关文档

- [Agent OpenAI Function Calling 分析](./AGENT_OPENAI_FUNCTION_CALLING_ANALYSIS.md)
- [ToolAgent Function Calling 分析](./TOOLAGENT_FUNCTION_CALLING_ANALYSIS.md)

