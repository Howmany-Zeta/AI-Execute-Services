import json
import uuid
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class OpenAIStreamFormatter:
    """
    OpenAI兼容的流式响应格式化器
    确保所有服务输出统一的流式格式，兼容Vercel AI SDK
    """

    def __init__(self, model_name: str = "ai-service"):
        self.stream_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        self.created = int(time.time())
        self.model_name = model_name

    def format_delta_chunk(self, content: str, finish_reason: Optional[str] = None) -> str:
        """格式化流式增量块，符合OpenAI格式"""
        chunk = {
            "id": self.stream_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model_name,
            "choices": [{
                "index": 0,
                "delta": {
                    "content": content
                } if content else {},
                "finish_reason": finish_reason
            }]
        }
        return json.dumps(chunk, ensure_ascii=False)

    def format_done_message(self) -> str:
        """格式化完成消息"""
        return "[DONE]"

    def format_error_chunk(self, error_message: str, error_code: str = "service_error") -> str:
        """格式化错误块"""
        chunk = {
            "id": self.stream_id,
            "object": "error",
            "created": self.created,
            "error": {
                "message": error_message,
                "type": error_code,
                "code": error_code
            }
        }
        return json.dumps(chunk, ensure_ascii=False)

class BaseAIService(ABC):
    """
    所有 AI 服务的抽象基类，要求实现 run 和 stream 方法
    提供统一的OpenAI兼容流式格式化功能
    """

    def __init__(self):
        self.prompt = self.load_prompt()
        self.tools = self.load_tools()

    @abstractmethod
    def run(self, input_data, context):
        """处理用户请求，返回完整结果"""
        pass

    @abstractmethod
    async def stream(self, input_data, context):
        """流式输出响应"""
        pass

    def load_prompt(self):
        """可选：从文件或 registry 中加载 system prompt"""
        return "[DEFAULT_PROMPT]"

    def load_tools(self):
        """可选：从工具注册表中加载默认工具"""
        return []

    def create_stream_formatter(self, model_name: str = None) -> OpenAIStreamFormatter:
        """
        创建OpenAI兼容的流式格式化器

        Args:
            model_name: 模型名称，如果未提供则使用服务名称

        Returns:
            OpenAIStreamFormatter实例
        """
        if model_name is None:
            model_name = getattr(self, 'service_name', 'ai-service')
        return OpenAIStreamFormatter(model_name)

    def format_stream_chunk(self, formatter: OpenAIStreamFormatter, content: str,
                          finish_reason: Optional[str] = None) -> str:
        """
        格式化单个流式块

        Args:
            formatter: 流式格式化器实例
            content: 内容文本
            finish_reason: 完成原因（可选）

        Returns:
            格式化后的JSON字符串
        """
        return formatter.format_delta_chunk(content, finish_reason)

    def format_stream_error(self, formatter: OpenAIStreamFormatter,
                          error_message: str, error_code: str = "service_error") -> str:
        """
        格式化流式错误消息

        Args:
            formatter: 流式格式化器实例
            error_message: 错误消息
            error_code: 错误代码

        Returns:
            格式化后的错误JSON字符串
        """
        return formatter.format_error_chunk(error_message, error_code)

    def format_stream_done(self, formatter: OpenAIStreamFormatter) -> str:
        """
        格式化流式完成消息

        Args:
            formatter: 流式格式化器实例

        Returns:
            完成消息字符串
        """
        return formatter.format_done_message()
