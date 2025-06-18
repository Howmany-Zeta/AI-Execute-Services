"""
General服务的工具配置和管理模块
提供工具注册、加载和管理功能
"""

import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class GeneralTool(ABC):
    """通用工具的抽象基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具功能"""
        pass

    def get_info(self) -> Dict[str, str]:
        """获取工具信息"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }

class TextFormatterTool(GeneralTool):
    """文本格式化工具"""

    def __init__(self):
        super().__init__(
            name="text_formatter",
            description="Format text into different structures (lists, tables, markdown)"
        )

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行文本格式化"""
        text = input_data.get('text', '')
        format_type = input_data.get('format', 'markdown')

        try:
            if format_type == 'list':
                formatted = self._format_as_list(text)
            elif format_type == 'table':
                formatted = self._format_as_table(text)
            elif format_type == 'markdown':
                formatted = self._format_as_markdown(text)
            else:
                formatted = text

            return {"result": formatted, "format": format_type}
        except Exception as e:
            logger.error(f"Error in text formatting: {e}")
            return {"error": str(e)}

    def _format_as_list(self, text: str) -> str:
        """格式化为列表"""
        lines = text.strip().split('\n')
        return '\n'.join(f"• {line.strip()}" for line in lines if line.strip())

    def _format_as_table(self, text: str) -> str:
        """格式化为表格（简单实现）"""
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return text

        # 简单的表格格式化
        header = "| Item | Description |"
        separator = "|------|-------------|"
        rows = [f"| {i+1} | {line.strip()} |" for i, line in enumerate(lines)]

        return '\n'.join([header, separator] + rows)

    def _format_as_markdown(self, text: str) -> str:
        """格式化为Markdown"""
        # 简单的Markdown格式化
        lines = text.strip().split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # 如果行看起来像标题
                if len(line) < 50 and not line.endswith('.'):
                    formatted_lines.append(f"## {line}")
                else:
                    formatted_lines.append(line)
                formatted_lines.append("")  # 添加空行

        return '\n'.join(formatted_lines).strip()

class LanguageDetectorTool(GeneralTool):
    """语言检测工具"""

    def __init__(self):
        super().__init__(
            name="language_detector",
            description="Detect the language of input text"
        )

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """检测文本语言"""
        text = input_data.get('text', '')

        try:
            # 简单的语言检测逻辑（实际应用中可以使用更复杂的库）
            detected_lang = self._detect_language(text)
            confidence = self._calculate_confidence(text, detected_lang)

            return {
                "language": detected_lang,
                "confidence": confidence,
                "text_length": len(text)
            }
        except Exception as e:
            logger.error(f"Error in language detection: {e}")
            return {"error": str(e)}

    def _detect_language(self, text: str) -> str:
        """简单的语言检测"""
        # 中文字符检测
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > len(text) * 0.3:
            return "zh"

        # 日文字符检测
        japanese_chars = sum(1 for char in text if '\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff')
        if japanese_chars > len(text) * 0.2:
            return "ja"

        # 韩文字符检测
        korean_chars = sum(1 for char in text if '\uac00' <= char <= '\ud7af')
        if korean_chars > len(text) * 0.2:
            return "ko"

        # 默认为英文
        return "en"

    def _calculate_confidence(self, text: str, detected_lang: str) -> float:
        """计算检测置信度"""
        if len(text) < 10:
            return 0.5
        elif len(text) < 50:
            return 0.7
        else:
            return 0.9

class TaskRouterTool(GeneralTool):
    """任务路由工具"""

    def __init__(self):
        super().__init__(
            name="task_router",
            description="Route user queries to appropriate task types"
        )

        # 任务关键词映射
        self.task_keywords = {
            'summarize': ['summary', 'summarize', 'brief', 'overview', 'tldr', '总结', '概述'],
            'explain': ['explain', 'what is', 'how does', 'definition', '解释', '什么是', '如何'],
            'compare': ['compare', 'vs', 'versus', 'difference', 'pros and cons', '比较', '对比'],
            'translate': ['translate', 'translation', 'convert to', '翻译', '转换'],
            'code': ['code', 'programming', 'function', 'script', '代码', '编程', '函数'],
            'recipe': ['recipe', 'cooking', 'ingredients', 'cook', '食谱', '烹饪', '做法'],
            'tutorial': ['tutorial', 'how to', 'step by step', 'guide', '教程', '如何', '步骤'],
            'list': ['list', 'enumerate', 'items', '列表', '枚举', '清单']
        }

    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """路由任务类型"""
        text = input_data.get('text', '').lower()

        try:
            detected_task = self._detect_task_type(text)
            confidence = self._calculate_task_confidence(text, detected_task)

            return {
                "task_type": detected_task,
                "confidence": confidence,
                "suggested_parameters": self._get_suggested_parameters(detected_task)
            }
        except Exception as e:
            logger.error(f"Error in task routing: {e}")
            return {"error": str(e)}

    def _detect_task_type(self, text: str) -> str:
        """检测任务类型"""
        scores = {}

        for task_type, keywords in self.task_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[task_type] = score

        if scores:
            return max(scores, key=scores.get)
        else:
            return 'general_query'

    def _calculate_task_confidence(self, text: str, task_type: str) -> float:
        """计算任务类型检测的置信度"""
        if task_type == 'general_query':
            return 0.5

        keywords = self.task_keywords.get(task_type, [])
        matches = sum(1 for keyword in keywords if keyword in text)

        return min(0.9, 0.3 + (matches * 0.2))

    def _get_suggested_parameters(self, task_type: str) -> Dict[str, Any]:
        """获取任务类型的建议参数"""
        suggestions = {
            'summarize': {'length': 'medium', 'style': 'paragraph'},
            'explain': {'complexity': 'intermediate', 'format': 'with_examples'},
            'compare': {'format': 'pros_cons', 'depth': 'detailed'},
            'translate': {'style': 'formal', 'preserve_formatting': 'yes'},
            'code': {'style': 'commented', 'complexity': 'intermediate'},
            'recipe': {'difficulty': 'medium', 'dietary': 'none'},
            'tutorial': {'format': 'numbered_steps', 'depth': 'comprehensive'},
            'list': {'organization': 'priority', 'detail_level': 'descriptive'}
        }

        return suggestions.get(task_type, {})

class GeneralToolManager:
    """通用工具管理器"""

    def __init__(self):
        self.tools: Dict[str, GeneralTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""
        default_tools = [
            TextFormatterTool(),
            LanguageDetectorTool(),
            TaskRouterTool()
        ]

        for tool in default_tools:
            self.register_tool(tool)

    def register_tool(self, tool: GeneralTool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[GeneralTool]:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有工具"""
        return [tool.get_info() for tool in self.tools.values()]

    async def execute_tool(self, tool_name: str, input_data: Dict[str, Any],
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            return await tool.execute(input_data, context)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}

# 全局工具管理器实例
tool_manager = GeneralToolManager()

def get_tool_manager() -> GeneralToolManager:
    """获取工具管理器实例"""
    return tool_manager
