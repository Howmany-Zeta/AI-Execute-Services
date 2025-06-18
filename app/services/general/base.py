import yaml
import os
from typing import Dict, Any, Optional
from app.services.base_service import BaseAIService

class GeneralServiceBase(BaseAIService):
    """
    General服务的基础类，提供配置加载和通用功能
    """

    def __init__(self):
        self.service_dir = os.path.dirname(__file__)
        super().__init__()

    def load_prompt(self) -> str:
        """从prompts.yaml加载系统提示词"""
        try:
            prompts_path = os.path.join(self.service_dir, 'prompts.yaml')
            with open(prompts_path, 'r', encoding='utf-8') as f:
                prompts = yaml.safe_load(f)

            # 获取当前服务的提示词
            service_name = getattr(self, 'service_name', 'summarizer')
            return prompts.get(service_name, prompts.get('summarizer', ''))
        except Exception as e:
            # 如果加载失败，返回默认提示词
            return self._get_default_prompt()

    def load_tasks(self) -> Dict[str, Any]:
        """从tasks.yaml加载任务配置"""
        try:
            tasks_path = os.path.join(self.service_dir, 'tasks.yaml')
            with open(tasks_path, 'r', encoding='utf-8') as f:
                tasks = yaml.safe_load(f)

            service_name = getattr(self, 'service_name', 'summarizer')
            return tasks.get(service_name, {})
        except Exception as e:
            return {}

    def get_capabilities(self) -> Dict[str, str]:
        """获取服务能力列表"""
        tasks_config = self.load_tasks()
        return tasks_config.get('capabilities', {})

    def get_service_description(self) -> str:
        """获取服务描述"""
        tasks_config = self.load_tasks()
        return tasks_config.get('description', '')

    def _get_default_prompt(self) -> str:
        """默认系统提示词"""
        return """You are a helpful AI assistant that provides clear, accurate, and concise responses to user queries.

Your capabilities include:
- Summarizing text and documents
- Explaining concepts and providing definitions
- Comparing different options with pros and cons
- Making recommendations based on user needs
- Translating text between languages
- Helping with code and programming questions
- Providing recipes and cooking instructions
- Creating step-by-step tutorials
- Writing balanced reviews
- Generating organized lists

Always respond in a professional, helpful manner. Be concise but thorough, and ask for clarification if the user's request is unclear."""
