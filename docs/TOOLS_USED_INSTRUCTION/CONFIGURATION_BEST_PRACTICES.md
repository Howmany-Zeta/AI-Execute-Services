# 工具配置最佳实践

## 使用 BaseSettings 而非 BaseModel

### 问题背景

AIECS 工具使用 Pydantic 进行配置管理。在配置类中，必须使用 `BaseSettings` 而不是 `BaseModel`：

**❌ 错误（不会自动读取环境变量）：**
```python
from pydantic import BaseModel, Field, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(env_prefix="DOC_PARSER_")
    
    gcs_project_id: Optional[str] = Field(default=None)
```

**✅ 正确（自动读取环境变量）：**
```python
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    model_config = ConfigDict(env_prefix="DOC_PARSER_")
    
    gcs_project_id: Optional[str] = Field(default=None)
```

### 关键区别

| 特性 | BaseModel | BaseSettings |
|------|-----------|--------------|
| 来源包 | `pydantic` | `pydantic_settings` |
| 环境变量读取 | ❌ 不支持 | ✅ 自动支持 |
| 用途 | 数据验证 | 配置管理 |
| `.env` 文件支持 | ❌ 无 | ✅ 有 |

### 为什么重要

使用 `get_tool()` 时，如果配置类使用 `BaseModel`：
- 环境变量 `DOC_PARSER_GCS_PROJECT_ID` **不会被读取**
- 会使用默认值 `None`
- 导致 "GCS project ID not provided" 错误

使用 `BaseSettings` 时：
- 自动从环境变量读取
- 支持 `.env` 文件
- 配置优先级正确：代码配置 > 环境变量 > 默认值

## 配置优先级

当使用 `BaseSettings` 时，配置值按以下优先级解析（从高到低）：

1. **显式传入的参数**（最高优先级）
   ```python
   tool = DocumentParserTool(config={'gcs_project_id': 'my-project'})
   ```

2. **环境变量**
   ```bash
   export DOC_PARSER_GCS_PROJECT_ID=my-project
   ```

3. **`.env` 文件**
   ```bash
   # .env
   DOC_PARSER_GCS_PROJECT_ID=my-project
   ```

4. **默认值**（最低优先级）
   ```python
   gcs_project_id: Optional[str] = Field(default=None)
   ```

## 使用示例

### 方式 1：使用环境变量（推荐）

```python
from dotenv import load_dotenv
load_dotenv()  # 必须在导入工具之前调用

from aiecs.tools import get_tool

# 自动从环境变量读取 DOC_PARSER_GCS_PROJECT_ID
tool = get_tool("document_parser")
print(tool.config.gcs_project_id)  # 输出: your-project-id
```

### 方式 2：显式传入配置

```python
from aiecs.tools.docs.document_parser_tool import DocumentParserTool

tool = DocumentParserTool(config={
    'gcs_project_id': 'my-project',
    'gcs_bucket_name': 'my-bucket'
})
```

### 方式 3：混合使用

```python
# .env 文件
DOC_PARSER_GCS_BUCKET_NAME=default-bucket

# 代码
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools.docs.document_parser_tool import DocumentParserTool

# gcs_bucket_name 从环境变量读取
# gcs_project_id 从代码传入（优先级更高）
tool = DocumentParserTool(config={
    'gcs_project_id': 'override-project'
})
```

## 依赖项

确保安装 `pydantic-settings`：

```bash
pip install pydantic pydantic-settings python-dotenv
```

## 验证配置

```python
from dotenv import load_dotenv
load_dotenv()

from aiecs.tools import get_tool

tool = get_tool("document_parser")

# 检查配置是否正确加载
print(f"GCS Project ID: {tool.config.gcs_project_id}")
print(f"GCS Bucket: {tool.config.gcs_bucket_name}")
print(f"Enable Cloud Storage: {tool.config.enable_cloud_storage}")
```

## 常见问题

### Q: 为什么使用 get_tool() 后环境变量不生效？

**A:** 确认配置类继承自 `BaseSettings` 而不是 `BaseModel`。

### Q: .env 文件中的变量没有被读取？

**A:** 确保在导入工具**之前**调用 `load_dotenv()`：

```python
# ✅ 正确顺序
from dotenv import load_dotenv
load_dotenv()
from aiecs.tools import get_tool

# ❌ 错误顺序
from aiecs.tools import get_tool
from dotenv import load_dotenv
load_dotenv()  # 太晚了！
```

### Q: 如何检查工具是否使用了 BaseSettings？

**A:** 检查工具源码中的 Config 类定义：

```python
# 在工具文件中查找
class Config(BaseSettings):  # ✅ 正确
    ...

class Config(BaseModel):  # ❌ 错误
    ...
```

## 已修复的工具

以下工具已更新为使用 `BaseSettings`：

- ✅ DocumentParserTool
- ✅ DocumentWriterTool  
- ✅ AIDocumentWriterOrchestrator

## 相关文档

- [Document Parser Tool Configuration](DOCUMENT_PARSER_TOOL_CONFIGURATION.md)
- [Document Writer Tool Configuration](DOCUMENT_WRITER_TOOL_CONFIGURATION.md)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

**最后更新**: 2025-11-05  
**维护者**: AIECS Tools Team

