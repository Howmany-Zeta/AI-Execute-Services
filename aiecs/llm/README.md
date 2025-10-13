# LLM Package - 模块化 AI 提供商架构

## 📦 包结构

```
aiecs/llm/
├── __init__.py              # 主入口，导出所有公共 API
├── client_factory.py        # 客户端工厂和管理器
├── clients/                 # LLM 客户端实现
│   ├── __init__.py
│   ├── base_client.py       # 基础客户端抽象类
│   ├── openai_client.py     # OpenAI 客户端
│   ├── vertex_client.py     # Vertex AI 客户端
│   ├── googleai_client.py   # Google AI 客户端
│   └── xai_client.py        # xAI (Grok) 客户端
├── config/                  # 配置管理
│   ├── __init__.py
│   ├── model_config.py      # Pydantic 配置模型
│   ├── config_loader.py     # 配置加载器
│   └── config_validator.py  # 配置验证器
├── callbacks/               # 回调处理
│   ├── __init__.py
│   └── custom_callbacks.py  # 自定义回调处理器
└── utils/                   # 工具和脚本
    ├── __init__.py
    └── validate_config.py   # 配置验证脚本
```

## 🔌 公共 API（对外接口）

### ✅ 推荐的导入方式（向后兼容）

所有公共 API 都可以从 `aiecs.llm` 直接导入：

```python
# 基础类和类型
from aiecs.llm import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMClientError,
    ProviderNotAvailableError,
    RateLimitError,
    AIProvider
)

# 客户端实现
from aiecs.llm import (
    OpenAIClient,
    VertexAIClient,
    GoogleAIClient,
    XAIClient
)

# 工厂和管理器
from aiecs.llm import (
    LLMClientFactory,
    LLMClientManager,
    get_llm_manager
)

# 便捷函数
from aiecs.llm import generate_text, stream_text

# 配置管理（新增）
from aiecs.llm import (
    ModelCostConfig,
    ModelCapabilities,
    ModelConfig,
    ProviderConfig,
    LLMModelsConfig,
    get_llm_config_loader,
    reload_llm_config
)

# 回调处理
from aiecs.llm import CustomAsyncCallbackHandler
```

### ⚠️ 内部模块路径变化

如果代码直接从子模块导入（不推荐），需要更新路径：

**旧路径（已废弃）：**
```python
from aiecs.llm.base_client import BaseLLMClient          # ❌
from aiecs.llm.vertex_client import VertexAIClient       # ❌
from aiecs.llm.custom_callbacks import CustomAsyncCallbackHandler  # ❌
```

**新路径：**
```python
from aiecs.llm.clients.base_client import BaseLLMClient
from aiecs.llm.clients.vertex_client import VertexAIClient
from aiecs.llm.callbacks.custom_callbacks import CustomAsyncCallbackHandler
```

**最佳实践（推荐）：**
```python
from aiecs.llm import BaseLLMClient, VertexAIClient, CustomAsyncCallbackHandler
```

## 📝 迁移指南

### 不需要更改的代码

以下代码**无需任何修改**，完全向后兼容：

```python
# ✅ 这些导入方式保持不变
from aiecs.llm import VertexAIClient, OpenAIClient
from aiecs.llm import LLMClientFactory, AIProvider
from aiecs.llm import LLMMessage, LLMResponse
from aiecs.llm import get_llm_manager

# ✅ 使用方式也完全不变
client = LLMClientFactory.get_client("OpenAI")
manager = await get_llm_manager()
```

### 需要更改的代码（极少情况）

只有直接导入子模块的代码需要更新：

```python
# ❌ 旧代码
from aiecs.llm.base_client import BaseLLMClient

# ✅ 方案 1：使用新的内部路径
from aiecs.llm.clients.base_client import BaseLLMClient

# ✅ 方案 2：从主模块导入（推荐）
from aiecs.llm import BaseLLMClient
```

## 🎯 最佳实践

1. **始终从主模块导入**
   ```python
   from aiecs.llm import VertexAIClient  # ✅ 推荐
   ```

2. **避免导入内部模块**
   ```python
   from aiecs.llm.clients.vertex_client import VertexAIClient  # ⚠️ 不推荐
   ```

3. **使用工厂模式**
   ```python
   from aiecs.llm import LLMClientFactory
   client = LLMClientFactory.get_client("Vertex")  # ✅ 推荐
   ```

## 🆕 新增功能

### 配置管理

现在可以通过 YAML 配置文件管理所有模型：

```python
from aiecs.llm import get_llm_config_loader, reload_llm_config

# 获取配置加载器
loader = get_llm_config_loader()

# 获取模型配置
model_config = loader.get_model_config("OpenAI", "gpt-4-turbo")
print(f"成本: 输入 ${model_config.costs.input}, 输出 ${model_config.costs.output}")

# 热重载配置（无需重启应用）
reload_llm_config()
```

### 配置验证

```bash
# 验证配置文件
poetry run python -m aiecs.llm.utils.validate_config
```

## 📚 示例

查看完整示例：
- `examples/llm_config_example.py` - 配置管理示例
- `docs/LLM/LLM_CONFIGURATION.md` - 配置文档

## 🔄 向后兼容性

本次重构**100% 向后兼容**：
- ✅ 所有公共 API 保持不变
- ✅ 现有代码无需修改
- ✅ 导入路径保持一致
- ✅ 功能行为完全相同

唯一的变化是内部文件组织结构，但这对使用者透明。

## 📖 更多文档

- [配置管理文档](../../docs/LLM/LLM_CONFIGURATION.md)
- [客户端文档](../../docs/LLM/LLM_AI_CLIENTS.md)
- [回调文档](../../docs/LLM/LLM_CUSTOM_CALLBACKS.md)

