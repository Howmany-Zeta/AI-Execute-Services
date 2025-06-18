import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from app.core.registry import register_ai_service
from app.services.general.base import GeneralServiceBase
from app.llm import get_llm_manager, LLMMessage, AIProvider, LLMResponse
from app.core.task_context import TaskContext

logger = logging.getLogger(__name__)

@register_ai_service("general", "summarizer")
class SummarizerService(GeneralServiceBase):
    """
    优化的通用AI服务，使用配置驱动的架构，支持多种任务类型。
    集成了YAML配置文件，简化了代码结构，提高了可维护性。
    """

    def __init__(self):
        self.service_name = "summarizer"
        super().__init__()
        self.tasks_config = self.load_tasks()
        self.capabilities = self.get_capabilities()

        # 从配置加载默认参数
        self.metadata = self.tasks_config.get('metadata', {})
        self.default_temperature = self.metadata.get('default_temperature', 0.7)
        self.max_tokens = self.metadata.get('max_context_length', 2000)

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户查询的主要方法

        Args:
            input_data: 包含用户输入的字典，通常包含 'text' 键
            context: 请求上下文，可能包含提供商/模型偏好

        Returns:
            包含AI响应的字典
        """
        try:
            # 验证输入
            user_text = input_data.get('text', '').strip()
            if not user_text:
                return self._create_error_response("请提供一些文本供我帮助您处理。")

            # 准备消息
            messages = self._prepare_messages(user_text, input_data, context)

            # 获取新的LLM管理器并生成响应
            llm_manager = await get_llm_manager()

            # 调整参数基于任务类型
            temperature, max_tokens = self._adjust_parameters_for_task(input_data)

            # 使用新的上下文感知生成方法
            response = await llm_manager.generate_text(
                messages=messages,
                context=context,  # 让管理器自动从context中提取AI偏好
                temperature=temperature,
                max_tokens=max_tokens
            )

            logger.info(f"Generated response using {response.provider}/{response.model}, "
                       f"tokens: {response.tokens_used}, cost: ${response.cost_estimate:.4f}")

            return self._create_success_response(response)

        except Exception as e:
            logger.error(f"Error in SummarizerService.run: {str(e)}")
            return self._create_error_response(
                "抱歉，处理您的请求时遇到了错误。请稍后再试。",
                str(e)
            )

    async def stream(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        OpenAI兼容的流式响应方法

        Args:
            input_data: 包含用户输入的字典
            context: 请求上下文

        Yields:
            OpenAI格式的流式响应块JSON字符串
        """
        # 创建OpenAI兼容的流式格式化器
        formatter = self.create_stream_formatter(f"general-{self.service_name}")

        try:
            # 验证输入
            user_text = input_data.get('text', '').strip()
            if not user_text:
                yield self.format_stream_error(formatter, "Please provide text for processing", "invalid_request")
                yield self.format_stream_done(formatter)
                return

            # 准备消息
            messages = self._prepare_messages(user_text, input_data, context)

            # 获取新的LLM管理器
            llm_manager = await get_llm_manager()

            # 调整参数
            temperature, max_tokens = self._adjust_parameters_for_task(input_data)

            # 使用新的上下文感知流式方法
            async for chunk in llm_manager.stream_text(
                messages=messages,
                context=context,  # 让管理器自动从context中提取AI偏好
                temperature=temperature,
                max_tokens=max_tokens
            ):
                yield self.format_stream_chunk(formatter, chunk)
                await asyncio.sleep(0.01)  # 防止客户端过载

            # 发送完成消息
            yield self.format_stream_chunk(formatter, "", finish_reason="stop")
            yield self.format_stream_done(formatter)
            logger.info(f"Completed streaming response using context-aware provider selection")

        except Exception as e:
            logger.error(f"Error in SummarizerService.stream: {str(e)}")
            error_message = "An error occurred while processing your request. Please try again later."
            yield self.format_stream_error(formatter, error_message, "service_error")
            yield self.format_stream_done(formatter)

    def _prepare_messages(self, user_text: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> list:
        """准备发送给LLM的消息"""
        # 获取系统提示词
        system_prompt = self.load_prompt()

        # 根据任务类型调整提示词
        task_type = input_data.get('task_type', 'general_query')
        if task_type in self.capabilities:
            capability_info = self.capabilities[task_type]
            enhanced_prompt = f"{system_prompt}\n\n当前任务类型: {task_type}\n任务描述: {capability_info.get('description', '')}"
        else:
            enhanced_prompt = system_prompt

        return [
            LLMMessage(role="system", content=enhanced_prompt),
            LLMMessage(role="user", content=user_text)
        ]

    # 注意：_get_provider_and_model, _get_provider_from_context, _get_model_from_context
    # 方法已被移除，因为新的LLMClientManager会自动从context中提取AI偏好

    def _adjust_parameters_for_task(self, input_data: Dict[str, Any]) -> tuple[float, int]:
        """根据任务类型调整参数"""
        task_type = input_data.get('task_type', 'general_query')

        # 任务特定的参数调整
        task_params = {
            'code': {'temperature': 0.3, 'max_tokens': 3000},
            'translate': {'temperature': 0.2, 'max_tokens': 2000},
            'summarize': {'temperature': 0.4, 'max_tokens': 1500},
            'explain': {'temperature': 0.5, 'max_tokens': 2500},
            'compare': {'temperature': 0.6, 'max_tokens': 2000},
        }

        params = task_params.get(task_type, {})
        temperature = params.get('temperature', self.default_temperature)
        max_tokens = params.get('max_tokens', self.max_tokens)

        return temperature, max_tokens

    def _create_success_response(self, response: LLMResponse) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "result": response.content,
            "metadata": {
                "provider": response.provider,
                "model": response.model,
                "tokens_used": response.tokens_used,
                "cost_estimate": response.cost_estimate,
                "response_time": getattr(response, 'response_time', None),
                "service_version": self.tasks_config.get('version', '1.0'),
                "llm_architecture": "modular_client_v2"  # 标识使用新架构
            }
        }

    def _create_error_response(self, message: str, error: Optional[str] = None) -> Dict[str, Any]:
        """创建错误响应"""
        response = {"result": message}
        if error:
            response["error"] = error
        return response


    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "name": "SummarizerService",
            "version": self.tasks_config.get('version', '1.0'),
            "description": self.get_service_description(),
            "capabilities": list(self.capabilities.keys()),
            "supported_languages": self.metadata.get('supported_languages', []),
            "response_formats": self.metadata.get('response_formats', [])
        }
