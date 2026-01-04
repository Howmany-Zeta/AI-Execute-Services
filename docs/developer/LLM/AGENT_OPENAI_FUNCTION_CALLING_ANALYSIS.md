# Agent OpenAI Function Calling 格式支持分析

## 问题确认

### 当前实现状态

1. **HybridAgent 使用 ReAct 模式（文本推理）**
   - 位置：`aiecs/domain/agent/hybrid_agent.py`
   - 方式：通过文本 prompt 描述工具，让 LLM 通过文本推理选择工具
   - 问题：工具的描述和参数信息没有被自动传递给 LLM

2. **ToolSchemaGenerator 存在但未被使用**
   - 位置：`aiecs/domain/agent/tools/schema_generator.py`
   - 功能：可以生成 OpenAI Function Calling 格式的 schema
   - 问题：HybridAgent 没有使用它

3. **LLMClient 不支持 functions/tools 参数**
   - 位置：`aiecs/llm/clients/openai_client.py`
   - 问题：`generate_text()` 和 `stream_text()` 方法没有处理 `functions` 或 `tools` 参数

4. **BaseTool 有完整的 schema 定义**
   - 位置：`aiecs/tools/base_tool.py`
   - 功能：使用 Pydantic models 定义工具参数
   - 问题：这些 schema 没有被转换为 OpenAI Function Calling 格式

## 需要修改的地方

### 1. ToolSchemaGenerator 增强
- 使用 BaseTool 的 Pydantic schema（包括 description 和 Field 信息）
- 生成完整的 OpenAI Function Calling 格式

### 2. HybridAgent 修改
- 在调用 LLM 时传递 `functions` 或 `tools` 参数
- 处理 LLM 返回的 `function_call` 响应
- 保持向后兼容（支持 ReAct 模式作为 fallback）

### 3. LLMClient 增强
- 支持 `functions` 参数（OpenAI API）
- 支持 `tools` 参数（OpenAI API v1.0+）
- 处理 function_call 响应

### 4. 其他 Agent 类型
- LLMAgent：如果添加工具支持，也需要更新
- ToolAgent：检查是否需要更新

## 工作量评估

### 高优先级（必须）
1. **ToolSchemaGenerator 增强** - 2-3 小时
   - 从 BaseTool 的 Pydantic schema 提取信息
   - 生成完整的 OpenAI Function Calling schema
   - 包括 description、parameters、required fields

2. **OpenAIClient 支持 functions/tools** - 2-3 小时
   - 修改 `generate_text()` 支持 `functions` 参数
   - 修改 `stream_text()` 支持 `tools` 参数（streaming function calls）
   - 处理 `function_call` 响应

3. **HybridAgent 集成** - 3-4 小时
   - 生成工具 schema
   - 在 LLM 调用时传递 functions
   - 处理 function_call 响应
   - 保持向后兼容

### 中优先级（建议）
4. **其他 LLM Clients** - 2-3 小时
   - Google Vertex AI client
   - xAI client
   - 其他支持的 providers

5. **测试和文档** - 2-3 小时
   - 单元测试
   - 集成测试
   - 更新文档

### 总计工作量
- **核心功能**：7-10 小时
- **完整支持**：11-16 小时

## 实现方案

### 方案 1：完全迁移到 Function Calling（推荐）
- 优点：更好的工具调用准确性，自动参数验证
- 缺点：需要支持 Function Calling 的 LLM（OpenAI, Anthropic 等）

### 方案 2：混合模式（推荐）
- 优先使用 Function Calling（如果 LLM 支持）
- Fallback 到 ReAct 模式（如果不支持）
- 优点：向后兼容，支持更多 LLM
- 缺点：需要维护两套逻辑

### 方案 3：配置选项
- 添加配置选项选择使用 Function Calling 还是 ReAct
- 优点：用户可以选择
- 缺点：增加复杂度

## 建议

采用**方案 2（混合模式）**：
1. 检测 LLM 是否支持 Function Calling
2. 如果支持，使用 Function Calling
3. 如果不支持，fallback 到 ReAct 模式
4. 保持现有 API 不变

