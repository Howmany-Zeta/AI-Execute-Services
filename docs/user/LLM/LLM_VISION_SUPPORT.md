# LLM Vision Support

本文档说明如何在 LLM 模块中使用图片上传功能。

## 概述

LLM 模块现在支持多模态输入，可以将图片与文本一起发送给支持视觉功能的模型。支持的图片格式包括：

- **图片 URL** (`http://` 或 `https://`)
- **Base64 数据 URI** (`data:image/...;base64,...`)
- **本地文件路径**

## 支持的模型

以下模型支持视觉功能（在 `llm_models.yaml` 中标记为 `vision: true`）：

### OpenAI
- `gpt-4-turbo`
- `gpt-4o`
- `gpt-4o-mini`

### Google Vertex AI / Google AI
- `gemini-2.5-pro`
- `gemini-2.5-flash`

### xAI (Grok)
- `grok-2-vision`

## 使用方法

### 基本用法

```python
from aiecs.llm.clients.openai_client import OpenAIClient
from aiecs.llm.clients.base_client import LLMMessage

client = OpenAIClient()

# 使用图片 URL
messages = [
    LLMMessage(
        role="user",
        content="What's in this image?",
        images=["https://example.com/image.jpg"]
    )
]

response = await client.generate_text(
    messages=messages,
    model="gpt-4o"
)
print(response.content)
```

### 使用本地文件

```python
messages = [
    LLMMessage(
        role="user",
        content="Describe this image",
        images=["/path/to/local/image.png"]
    )
]
```

### 使用 Base64 数据

```python
messages = [
    LLMMessage(
        role="user",
        content="Analyze this image",
        images=["data:image/png;base64,iVBORw0KGgoAAAANS..."]
    )
]
```

### 多张图片

```python
messages = [
    LLMMessage(
        role="user",
        content="Compare these two images",
        images=[
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    )
]
```

### 使用字典格式（OpenAI 专用）

对于 OpenAI 客户端，可以使用字典格式指定更多选项：

```python
messages = [
    LLMMessage(
        role="user",
        content="Analyze this image in detail",
        images=[
            {
                "url": "https://example.com/image.jpg",
                "detail": "high"  # "low", "high", 或 "auto"
            }
        ]
    )
]
```

## 各提供商实现细节

### OpenAI / xAI

- 使用 `content` 数组格式
- 支持 `image_url` 类型，包含 `url` 和可选的 `detail` 参数
- URL 可以是 HTTP/HTTPS URL 或 base64 数据 URI

### Google Vertex AI / Google AI

- 使用 `Part` 结构
- 支持 `Part.from_uri()` 用于 URL
- 支持 `Part.from_bytes()` 用于 base64 或本地文件
- 自动下载 URL 图片并转换为字节

## 示例代码

完整示例请参考 `examples/llm_vision_example.py`：

```python
# OpenAI 示例
from aiecs.llm.clients.openai_client import OpenAIClient

client = OpenAIClient()
messages = [
    LLMMessage(
        role="user",
        content="What's in this image?",
        images=["https://example.com/image.jpg"]
    )
]
response = await client.generate_text(messages=messages, model="gpt-4o")
```

```python
# Google AI 示例
from aiecs.llm.clients.googleai_client import GoogleAIClient

client = GoogleAIClient()
messages = [
    LLMMessage(
        role="user",
        content="Describe this image",
        images=["/path/to/image.jpg"]
    )
]
response = await client.generate_text(messages=messages, model="gemini-2.5-pro")
```

```python
# Vertex AI 示例
from aiecs.llm.clients.vertex_client import VertexAIClient

client = VertexAIClient()
messages = [
    LLMMessage(
        role="user",
        content="Analyze this image",
        images=["https://example.com/image.png"]
    )
]
response = await client.generate_text(messages=messages, model="gemini-2.5-pro")
```

## 注意事项

1. **模型兼容性**：确保使用的模型支持视觉功能（检查 `vision: true` 配置）

2. **图片格式**：支持的格式包括 PNG、JPEG、WEBP、GIF（非动画）

3. **文件大小**：对于本地文件，确保文件大小在合理范围内

4. **URL 可访问性**：使用 URL 时，确保图片可以通过网络访问

5. **Base64 编码**：Base64 数据 URI 格式应为 `data:image/<type>;base64,<data>`

## 错误处理

如果遇到错误，请检查：

- 模型是否支持视觉功能
- 图片格式是否支持
- URL 是否可访问
- 文件路径是否存在
- Base64 数据格式是否正确

## 技术实现

- **图片处理工具**：`aiecs.llm.utils.image_utils`
  - `ImageContent`：图片内容封装类
  - `parse_image_source()`：解析图片源（URL、文件路径、base64）

- **消息格式**：`LLMMessage` 新增 `images` 字段
  - 类型：`List[Union[str, Dict[str, Any]]]`
  - 支持字符串（URL、文件路径、base64）或字典格式

- **客户端适配**：
  - OpenAI/xAI：通过 `OpenAICompatibleFunctionCallingMixin` 自动支持
  - Google Vertex AI：使用 `Part.from_uri()` 和 `Part.from_bytes()`
  - Google AI：使用 `types.Part.from_bytes()`
