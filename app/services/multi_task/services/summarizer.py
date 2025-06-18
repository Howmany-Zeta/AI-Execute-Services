import yaml
import json
import os
from typing import Dict, List, Any, Optional, AsyncGenerator
from enum import Enum
from datetime import datetime
import asyncio
from asyncio import TimeoutError as AsyncioTimeoutError

from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field

from app.core.registry import register_ai_service
from app.services.base_service import BaseAIService
from app.core.service_executor import (
    get_executor,
    TaskStatus,
    ErrorCode,
    TaskStepResult,
    UserConfirmation
)
import logging
from app.tools import get_tool, list_tools
from app.services.multi_task.tools import MultiTaskTools

# Import the DOMAINS list from base.py
from ..base import DOMAINS, BaseTaskService

logger = logging.getLogger(__name__)

# Task Category Enum
class TaskCategory(Enum):
    ANSWER = "answer"
    COLLECT = "collect"
    PROCESS = "process"
    ANALYZE = "analyze"
    GENERATE = "generate"

# YAML Configuration Models for Validation
class RoleConfig(BaseModel):
    goal: str
    backstory: str
    tools: Optional[List[str]] = None
    tools_instruction: Optional[str] = None
    domain_specialization: Optional[str] = None

class TaskConfig(BaseModel):
    description: str
    agent: str
    expected_output: str
    task_type: str = Field(default="fast", pattern="^(fast|heavy)$")
    tools: Optional[Dict[str, Dict[str, List[Dict]]]] = None
    conditions: Optional[List[Dict]] = None

class PromptsConfig(BaseModel):
    system_prompt: str
    roles: Dict[str, RoleConfig]

class TasksConfig(BaseModel):
    system_tasks: Dict[str, TaskConfig]
    sub_tasks: Dict[str, TaskConfig]

def load_yaml_config(file_name: str) -> Dict:
    """Load a YAML configuration file.

    Args:
        file_name (str): Name of the YAML file.

    Returns:
        Dict: The loaded configuration as a dictionary.
    """
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the multi_task directory
    parent_dir = os.path.dirname(current_dir)
    # Construct the full path
    file_path = os.path.join(parent_dir, file_name)

    with open(file_path, 'r', encoding="utf-8") as file:
        return yaml.safe_load(file)

@register_ai_service("multi_task", "summarizer")
class MultiTaskSummarizerRefactored(BaseTaskService):
    """
    重构后的多任务汇总器服务，使用新的模块化执行框架

    主要改进：
    1. 继承自 BaseTaskService，实现抽象方法
    2. 使用重构后的 ServiceExecutor 和其组件
    3. 完整的 DSL 执行支持
    4. 改进的工具集成
    5. 更好的错误处理和状态管理
    """

    def __init__(self):
        """初始化重构后的汇总器服务"""
        super().__init__()

        # 获取重构后的执行器
        self._executor = get_executor()

        # 初始化工具管理器
        self.tools_manager = MultiTaskTools()

        # 验证并加载 YAML 配置
        self._validate_yaml_configs()
        self.prompts_config = load_yaml_config('prompts.yaml')
        self.tasks_config = load_yaml_config('tasks.yaml')

        # 存储域列表
        self.domain_list = DOMAINS

        # 初始化代理和任务
        self.agents = self._create_agents()
        self.system_tasks = self._create_tasks(self.agents, 'system_tasks')
        self.sub_tasks = self._create_tasks(self.agents, 'sub_tasks')

        logger.info("MultiTaskSummarizerRefactored initialized with modular architecture")

    def _validate_yaml_configs(self):
        """验证 YAML 配置

        Raises:
            ValueError: 如果 prompts.yaml 或 tasks.yaml 配置无效
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to the multi_task directory
        parent_dir = os.path.dirname(current_dir)

        try:
            prompts_path = os.path.join(parent_dir, 'prompts.yaml')
            with open(prompts_path, 'r', encoding="utf-8") as file:
                prompts_data = yaml.safe_load(file)
            PromptsConfig(**prompts_data)
        except Exception as e:
            raise ValueError(f"Invalid prompts.yaml configuration: {e}")

        try:
            tasks_path = os.path.join(parent_dir, 'tasks.yaml')
            with open(tasks_path, 'r', encoding="utf-8") as file:
                tasks_data = yaml.safe_load(file)
            TasksConfig(**tasks_data)
        except Exception as e:
            raise ValueError(f"Invalid tasks.yaml configuration: {e}")

    def _create_agents(self) -> Dict[str, Agent]:
        """基于 prompts.yaml 创建代理

        Returns:
            Dict[str, Agent]: 角色名称到代理实例的映射字典
        """
        agents = {}
        available_tools = self.tools_manager.get_available_tools()

        for role_name, role_config in self.prompts_config['roles'].items():
            agent_tools = []
            if 'tools' in role_config:
                for tool_name in role_config.get('tools', []):
                    if tool_name in available_tools:
                        try:
                            tool = get_tool(tool_name)
                            agent_tools.append(tool)
                        except ValueError as e:
                            logger.warning(f"Unable to load tool {tool_name}: {e}")

            backstory = role_config['backstory']
            if 'tools_instruction' in role_config and role_config['tools_instruction']:
                backstory = f"{backstory}\n\n{role_config['tools_instruction']}"

            additional_context = {}
            if 'domain_specialization' in role_config:
                additional_context['domain_list'] = self.domain_list

            agents[role_name] = Agent(
                role=role_name,
                goal=role_config['goal'],
                backstory=backstory,
                verbose=True,
                allow_delegation=False,
                tools=agent_tools,
                context=additional_context
            )
        return agents

    def _create_tasks(self, agents: Dict[str, Agent], task_section: str) -> Dict[str, Task]:
        """基于 tasks.yaml 创建任务

        Args:
            agents (Dict[str, Agent]): 按角色名称映射的代理字典
            task_section (str): tasks.yaml 的任务部分（'system_tasks' 或 'sub_tasks'）

        Returns:
            Dict[str, Task]: 任务名称到任务实例的映射字典
        """
        tasks = {}
        for task_name, task_config in self.tasks_config[task_section].items():
            agent_role = task_config['agent']
            tasks[task_name] = Task(
                description=task_config['description'],
                agent=agents[agent_role],
                expected_output=task_config['expected_output'],
                task_type=task_config.get('task_type', 'fast')
            )
        return tasks

    # 实现 BaseTaskService 的抽象方法

    async def _parse_intent(self, input_data: Dict) -> List[TaskCategory]:
        """解析用户意图以确定任务类别"""
        user_text = input_data.get("text", "")
        intent_task = Task(
            description=f"Analyze the following user input and determine which task categories are required: {user_text}\nCategories: answer, collect, process, analyze, generate",
            agent=self.agents['intent_parser'],
            expected_output="A list of task categories (e.g., ['collect', 'process', 'generate'])"
        )
        crew = Crew(
            agents=[self.agents['intent_parser']],
            tasks=[intent_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            raise AsyncioTimeoutError(result.get("error_message", "Intent parsing timed out"))

        categories = json.loads(result) if isinstance(result, str) else result
        return [TaskCategory(category) for category in categories]

    async def _breakdown_subtasks(self, categories: List[TaskCategory]) -> Dict[str, List[str]]:
        """将意图类别分解为可执行的子任务"""
        breakdown_task = Task(
            description=f"Break down the following intent categories into executable sub-tasks: {[cat.value for cat in categories]}. Available sub-tasks: {list(self.sub_tasks.keys())}",
            agent=self.agents['task_decomposer'],
            expected_output="A JSON mapping of intent categories to sub-tasks, e.g., {'collect': ['collect_scrape', 'collect_search'], 'analyze': ['analyze_dataoutcome']}"
        )
        crew = Crew(
            agents=[self.agents['task_decomposer']],
            tasks=[breakdown_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            raise AsyncioTimeoutError(result.get("error_message", "Sub-task breakdown timed out"))

        breakdown = json.loads(result) if isinstance(result, str) else result
        return breakdown

    async def _examine_outcome(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """检查收集和处理任务的结果"""
        examination_task = Task(
            description=f"Examine the outcome of task {task_name} in category {category}. Result: {json.dumps(task_result)}",
            agent=self.agents['supervisor'],
            expected_output="A JSON object with examination results, e.g., {'task': 'collect_scrape', 'credibility': 0.9, 'confidence': 0.85, 'passed': true}"
        )
        crew = Crew(
            agents=[self.agents['supervisor']],
            tasks=[examination_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            raise AsyncioTimeoutError(result.get("error_message", "Examination timed out"))

        return json.loads(result) if isinstance(result, str) else result

    async def _accept_outcome(self, task_name: str, category: str, task_result: Dict) -> Dict:
        """接受分析和生成任务的结果"""
        acceptance_task = Task(
            description=f"Review the outcome of task {task_name} in category {category}. Result: {json.dumps(task_result)}",
            agent=self.agents['director'],
            expected_output="A JSON object with acceptance results, e.g., {'task': 'analyze_dataoutcome', 'passed': true, 'criteria': {'meets_request': true, 'accurate': true, 'no_synthetic_data': true}}"
        )
        crew = Crew(
            agents=[self.agents['director']],
            tasks=[acceptance_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            raise AsyncioTimeoutError(result.get("error_message", "Acceptance timed out"))

        return json.loads(result) if isinstance(result, str) else result

    async def _plan_task_sequence(self, subtask_breakdown: Dict[str, List[str]]) -> List[Dict]:
        """基于子任务分解规划任务序列"""
        available_tools = self.tools_manager.get_available_tools()

        task_tools = {}
        for task_name, task_config in self.tasks_config['sub_tasks'].items():
            task_tools[task_name] = task_config.get('tools', {})

        tools_instruction = ""
        if 'planner' in self.prompts_config['roles'] and 'tools_instruction' in self.prompts_config['roles']['planner']:
            tools_instruction = self.prompts_config['roles']['planner'].get('tools_instruction', '')

        plan_task = Task(
            description=f"Create a task sequence for the following sub-task breakdown: {json.dumps(subtask_breakdown)}. "
                        f"Available sub-tasks: {list(self.sub_tasks.keys())}. "
                        f"Available tools: {available_tools}. "
                        f"Tools available for each sub-task: {task_tools}. "
                        f"{tools_instruction}\n"
                        f"Use a DSL to express the workflow, supporting: "
                        f"- Conditional branching: {{'if': 'condition', 'then': [steps]}} "
                        f"- Parallel blocks: {{'parallel': [task_names]}} "
                        f"- Single tasks: {{'task': 'task_name', 'tools': ['tool1.operation']}} "
                        f"Optimize using conditions and parallelism, ensuring examination and acceptance are involved for collect/process and analyze/generate tasks respectively.",
            agent=self.agents['planner'],
            expected_output="A JSON list of DSL steps"
        )
        crew = Crew(
            agents=[self.agents['planner']],
            tasks=[plan_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            raise AsyncioTimeoutError(result.get("error_message", "Task planning timed out"))

        sequence = json.loads(result) if isinstance(result, str) else result
        return sequence

    async def _execute_dsl_step(self, step: Dict, intent_categories: List[str], input_data: Dict, context: Dict) -> TaskStepResult:
        """执行 DSL 步骤 - 使用重构后的 DSL 处理器"""
        return await self._executor.execute_dsl_step(
            step,
            intent_categories,
            input_data,
            context,
            self._execute_single_task,
            self._execute_batch_task
        )

    def _category_enum(self, category: str) -> TaskCategory:
        """将类别字符串转换为对应的枚举值"""
        try:
            return TaskCategory(category)
        except ValueError:
            raise ValueError(f"Invalid task category: {category}")

    # 辅助执行方法

    async def _execute_single_task(self, task_name: str, input_data: Dict, context: Dict) -> Dict:
        """执行单个任务 - 适配新的执行框架"""
        try:
            # 确定任务类别
            category = self._determine_task_category(task_name)

            # 获取任务配置
            task_section = 'system_tasks' if task_name in self.system_tasks else 'sub_tasks'
            task_config = self.tasks_config[task_section][task_name]

            # 使用重构后的操作执行器执行任务
            if task_name in self.sub_tasks:
                # 子任务：使用工具执行
                task_tools = task_config.get('tools', {})
                operations = self._convert_tools_to_operations(task_tools, input_data, context)

                if operations:
                    # 执行操作序列
                    results = await self._executor.execute_operations_sequence(
                        operations,
                        input_data.get('user_id', 'anonymous'),
                        input_data.get('task_id', 'none'),
                        stop_on_failure=False
                    )

                    # 合并结果
                    combined_result = self._combine_operation_results(results)

                    return {
                        "step": f"{category}/{task_name}",
                        "result": combined_result,
                        "completed": all(r.completed for r in results),
                        "message": f"Completed {category} task: {task_name}",
                        "status": TaskStatus.COMPLETED if all(r.completed for r in results) else TaskStatus.FAILED,
                        "error_code": None,
                        "error_message": None
                    }
                else:
                    # 无工具的任务：使用 CrewAI 执行
                    return await self._execute_crew_task(task_name, category, input_data, context)
            else:
                # 系统任务：使用 CrewAI 执行
                return await self._execute_crew_task(task_name, category, input_data, context)

        except Exception as e:
            logger.error(f"Error executing single task {task_name}: {e}")
            return {
                "step": f"error/{task_name}",
                "result": None,
                "completed": False,
                "message": f"Failed to execute task {task_name}",
                "status": TaskStatus.FAILED,
                "error_code": ErrorCode.EXECUTION_ERROR,
                "error_message": str(e)
            }

    async def _execute_batch_task(self, batch_tasks: List[Dict], input_data: Dict, context: Dict) -> List[TaskStepResult]:
        """执行批量任务 - 使用重构后的并行执行"""
        try:
            # 转换为操作格式
            operations = []
            for task_info in batch_tasks:
                task_name = task_info.get('task', task_info.get('task_name'))
                category = task_info.get('category', self._determine_task_category(task_name))

                # 为每个任务创建操作
                task_input = {**input_data, 'current_task': task_info}
                operations.append({
                    'operation': f'task.{task_name}',
                    'params': {
                        'input_data': task_input,
                        'context': context,
                        'category': category
                    }
                })

            # 使用重构后的并行执行
            results = await self._executor.execute_parallel_operations(operations)
            return results

        except Exception as e:
            logger.error(f"Error executing batch tasks: {e}")
            # 返回失败结果
            return [TaskStepResult(
                step=f"batch_error",
                result=None,
                completed=False,
                message=f"Batch execution failed",
                status=TaskStatus.FAILED,
                error_code=ErrorCode.EXECUTION_ERROR,
                error_message=str(e)
            )]

    async def _execute_crew_task(self, task_name: str, category: str, input_data: Dict, context: Dict) -> Dict:
        """使用 CrewAI 执行任务"""
        task_section = 'system_tasks' if task_name in self.system_tasks else 'sub_tasks'
        task_dict = self.system_tasks if task_section == 'system_tasks' else self.sub_tasks
        task = task_dict.get(task_name)

        if not task:
            raise ValueError(f"Task {task_name} not found")

        # 创建 Crew 并执行
        crew_task = Task(
            description=task.description.format(input=input_data, context=context),
            agent=task.agent,
            expected_output=task.expected_output
        )
        crew = Crew(
            agents=[task.agent],
            tasks=[crew_task],
            verbose=2,
            process=Process.sequential
        )

        result = await self._executor.execute_with_timeout(
            crew.kickoff,
            timeout=self._executor.config.call_timeout_seconds
        )

        if isinstance(result, dict) and result.get("status") == TaskStatus.TIMED_OUT.value:
            return result

        return {
            "step": f"{category}/{task_name}",
            "result": result,
            "completed": True,
            "message": f"Completed {category} task: {task_name}",
            "status": TaskStatus.COMPLETED,
            "error_code": None,
            "error_message": None
        }

    def _determine_task_category(self, task_name: str) -> str:
        """根据任务名称确定类别"""
        if task_name.startswith('answer_'):
            return 'answer'
        elif task_name.startswith('collect_'):
            return 'collect'
        elif task_name.startswith('process_'):
            return 'process'
        elif task_name.startswith('analyze_'):
            return 'analyze'
        elif task_name.startswith('generate_'):
            return 'generate'
        else:
            return 'system'

    def _convert_tools_to_operations(self, task_tools: Dict, input_data: Dict, context: Dict) -> List[Dict]:
        """将任务工具转换为操作格式"""
        operations = []

        for tool_name, tool_config in task_tools.items():
            if isinstance(tool_config, dict) and 'operations' in tool_config:
                for operation_name, operation_config in tool_config['operations'].items():
                    # 检查条件
                    if self._check_operation_conditions(operation_config, input_data, context):
                        operations.append({
                            'operation': f'{tool_name}.{operation_name}',
                            'params': self._extract_operation_params(operation_config, input_data, context)
                        })

        return operations

    def _check_operation_conditions(self, operation_config: Dict, input_data: Dict, context: Dict) -> bool:
        """检查操作执行条件"""
        if not isinstance(operation_config, dict) or 'conditions' not in operation_config:
            return True

        conditions = operation_config['conditions']
        if not isinstance(conditions, list):
            return True

        for condition in conditions:
            if isinstance(condition, dict) and 'if' in condition:
                condition_expr = condition['if']
                # 使用 DSL 处理器评估条件
                try:
                    result = self._executor.evaluate_condition(condition_expr, [], context, input_data)
                    if not result:
                        return False
                except Exception as e:
                    logger.warning(f"Failed to evaluate condition {condition_expr}: {e}")
                    return False

        return True

    def _extract_operation_params(self, operation_config: Dict, input_data: Dict, context: Dict) -> Dict:
        """提取操作参数"""
        params = {}

        # 从输入数据和上下文中提取相关参数
        if 'params' in operation_config:
            params.update(operation_config['params'])

        # 添加标准参数
        params.update({
            'user_id': input_data.get('user_id', 'anonymous'),
            'task_id': input_data.get('task_id', 'none'),
            'input_data': input_data,
            'context': context
        })

        return params

    def _combine_operation_results(self, results: List[TaskStepResult]) -> Any:
        """合并操作结果"""
        if not results:
            return None

        if len(results) == 1:
            return results[0].result

        # 合并多个结果
        combined = {
            'operations': [r.dict() for r in results],
            'success_count': sum(1 for r in results if r.completed),
            'total_count': len(results),
            'combined_result': [r.result for r in results if r.result is not None]
        }

        return combined

    # 重写 BaseAIService 的方法

    async def initialize(self):
        """初始化服务"""
        await self._executor.initialize()
        logger.info("MultiTaskSummarizerRefactored initialized successfully")

    async def stream(self, input_data: Dict, context: Dict) -> AsyncGenerator[Dict, None]:
        """流式执行任务 - 使用继承的工作流"""
        async for result in self.execute_workflow(input_data, context):
            yield result

    def run(self, input_data: Dict, context: Dict) -> Dict:
        """同步运行方法（未实现）"""
        raise NotImplementedError("Use the async `stream` method for task execution.")
