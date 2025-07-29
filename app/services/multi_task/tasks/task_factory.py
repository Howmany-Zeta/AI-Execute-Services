"""
Task Factory Module

This module is responsible for creating task objects from configuration data.
It isolates the dependency on LangChain and provides a clean interface
for task creation.

Following the Single Responsibility Principle (SRP), this module only handles
task object creation and configuration mapping.
"""

import os
import yaml
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor
from pydantic import ValidationError

from .task_models import (
    TasksConfig,
    TaskConfig,
    SystemTaskConfig,
    SubTaskConfig,
    TaskCategory,
    TaskType,
    SystemTasksDict,
    SubTasksDict,
    LangChainTaskWrapper
)

from ..core.exceptions import (
    TaskValidationError,
    TaskNotFoundException,
    TaskDependencyError
)
from ..core.models.agent_models import AgentRole

import logging

logger = logging.getLogger(__name__)


class TaskFactory:
    """
    Factory class for creating task objects from configuration.

    This factory encapsulates the logic for converting task configurations
    into executable task objects using LangChain components, following the Factory pattern.

    Responsibilities:
    - Load and validate task configurations
    - Create LangChain-based Task objects from configurations
    - Map agents to tasks
    - Handle tool configurations
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the task factory.

        Args:
            config_path: Optional path to the tasks configuration file.
                        If not provided, uses the default tasks.yaml location.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._tasks_config: Optional[TasksConfig] = None
        self._agents_registry: Dict[str, Any] = {}

    def _get_default_config_path(self) -> str:
        """Get the default path to the tasks.yaml configuration file."""
        current_dir = Path(__file__).parent
        # Go up to the multi_task directory
        multi_task_dir = current_dir.parent
        return str(multi_task_dir / "tasks.yaml")

    def load_configuration(self) -> TasksConfig:
        """
        Load and validate the tasks configuration from YAML file.

        Returns:
            TasksConfig: Validated configuration object

        Raises:
            TaskValidationError: If configuration is invalid
            FileNotFoundError: If configuration file is not found
        """
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Tasks configuration file not found: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as file:
                raw_config = yaml.safe_load(file)

            # Validate configuration using Pydantic models
            self._tasks_config = TasksConfig(**raw_config)

            logger.info(f"Successfully loaded tasks configuration from {self.config_path}")
            logger.info(f"Loaded {len(self._tasks_config.system_tasks)} system tasks")
            logger.info(f"Loaded {len(self._tasks_config.sub_tasks)} sub-tasks")

            return self._tasks_config

        except ValidationError as e:
            error_msg = f"Invalid tasks configuration: {e}"
            logger.error(error_msg)
            raise TaskValidationError(error_msg) from e
        except yaml.YAMLError as e:
            error_msg = f"Failed to parse YAML configuration: {e}"
            logger.error(error_msg)
            raise TaskValidationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error loading configuration: {e}"
            logger.error(error_msg)
            raise TaskValidationError(error_msg) from e

    def register_agents(self, agents: Dict[str, Any]) -> None:
        """
        Register agents that can be assigned to tasks.

        Args:
            agents: Dictionary mapping agent names to Agent objects
        """
        self._agents_registry.update(agents)
        logger.info(f"Registered {len(agents)} agents: {list(agents.keys())}")

    def get_agent(self, agent_name) -> Any:
        """
        Get an agent by name from the registry.

        Args:
            agent_name: Name of the agent to retrieve (can be string or AgentRole enum)

        Returns:
            Agent: The requested agent object

        Raises:
            TaskNotFoundException: If agent is not found
        """
        # Convert AgentRole enum to string if needed
        if hasattr(agent_name, 'value'):  # Check if it's an enum
            agent_name_str = agent_name.value
        else:
            agent_name_str = str(agent_name)

        if agent_name_str not in self._agents_registry:
            available_agents = list(self._agents_registry.keys())
            raise TaskNotFoundException(
                f"Agent '{agent_name_str}' not found. Available agents: {available_agents}"
            )

        return self._agents_registry[agent_name_str]

    def _create_task_from_config(
        self,
        task_name: str,
        task_config: TaskConfig,
        task_category: Optional[TaskCategory] = None
    ) -> LangChainTaskWrapper:
        """
        Create a LangChain-based Task object from a task configuration.

        Args:
            task_name: Name of the task
            task_config: Task configuration object
            task_category: Optional task category for context

        Returns:
            LangChainTaskWrapper: LangChain-based task wrapper

        Raises:
            TaskNotFoundException: If required agent is not found
            TaskDependencyError: If task dependencies cannot be resolved
        """
        try:
            # Get the agent for this task
            agent = self.get_agent(task_config.agent)

            # Extract tools if configured
            tools = []
            if task_config.tools:
                tools = self._extract_tools_from_config(task_config.tools)

            # Create a context for the agent
            context = {"task_name": task_name, "task_category": task_category}

            # Create LangChain AgentExecutor from our custom agent
            agent_executor = agent.create_langchain_agent(context=context, tools=tools)

            # Create prompt template for the task
            prompt_template = PromptTemplate(
                input_variables=["task_description", "expected_output", "input_data"],
                template="""Task: {task_description}

Expected Output: {expected_output}

Input Data: {input_data}

Please complete this task according to the specifications above."""
            )

            # Create LLM chain for task execution
            llm_chain = LLMChain(
                llm=agent_executor.agent.llm if hasattr(agent_executor.agent, 'llm') else None,
                prompt=prompt_template,
                verbose=True
            )

            # Create the task wrapper
            task_wrapper = LangChainTaskWrapper(
                task_name=task_name,
                task_category=task_category.value if task_category else None,
                task_config=task_config,
                llm_chain=llm_chain,
                prompt_template=prompt_template,
                metadata={
                    "agent_executor": agent_executor,
                    "tools": tools,
                    "agent_name": task_config.agent
                }
            )

            logger.debug(f"Created task '{task_name}' with agent '{task_config.agent}'")
            return task_wrapper

        except Exception as e:
            error_msg = f"Failed to create task '{task_name}': {e}"
            logger.error(error_msg)
            raise TaskDependencyError(error_msg) from e

    def _extract_tools_from_config(self, tools_config: Dict[str, Any]) -> List[BaseTool]:
        """
        Extract and prepare tools from task configuration.

        Args:
            tools_config: Tools configuration dictionary

        Returns:
            List of LangChain BaseTool objects ready for use

        Note:
            This method currently returns an empty list as tool integration
            depends on the specific tool management system being used.
            It should be extended to integrate with the actual tool layer.
        """
        if not isinstance(tools_config, dict):
            logger.warning(f"tools_config is not a dict! It's {type(tools_config)}: {tools_config}")
            return []

        # TODO: Integrate with the tool layer when it's implemented
        # For now, return empty list to avoid breaking task creation
        logger.debug(f"Tools configuration found but not yet integrated: {list(tools_config.keys())}")
        return []

    def create_system_tasks(self, agents: Dict[str, Any]) -> Dict[str, LangChainTaskWrapper]:
        """
        Create all system tasks from configuration.

        Args:
            agents: Dictionary of available agents

        Returns:
            Dictionary mapping task names to LangChainTaskWrapper objects

        Raises:
            TaskValidationError: If configuration is not loaded
            TaskNotFoundException: If required agents are not found
        """
        if not self._tasks_config:
            raise TaskValidationError("Configuration not loaded. Call load_configuration() first.")

        self.register_agents(agents)

        system_tasks = {}

        for task_name, task_config in self._tasks_config.system_tasks.items():
            try:
                task = self._create_task_from_config(task_name, task_config)
                system_tasks[task_name] = task
                logger.debug(f"Created system task: {task_name}")

            except Exception as e:
                error_msg = f"Failed to create system task '{task_name}': {e}"
                logger.error(error_msg)
                raise TaskDependencyError(error_msg) from e

        logger.info(f"Successfully created {len(system_tasks)} system tasks")
        return system_tasks

    def create_sub_tasks(self, agents: Dict[str, Any]) -> Dict[str, LangChainTaskWrapper]:
        """
        Create all sub-tasks from configuration.

        Args:
            agents: Dictionary of available agents

        Returns:
            Dictionary mapping task names to LangChainTaskWrapper objects

        Raises:
            TaskValidationError: If configuration is not loaded
            TaskNotFoundException: If required agents are not found
        """
        if not self._tasks_config:
            raise TaskValidationError("Configuration not loaded. Call load_configuration() first.")

        self.register_agents(agents)

        sub_tasks = {}

        for task_name, task_config in self._tasks_config.sub_tasks.items():
            try:
                # Determine task category from task name
                category = None
                if '_' in task_name:
                    category_str = task_name.split('_')[0]
                    if category_str in TaskCategory.__members__.values():
                        category = TaskCategory(category_str)

                task = self._create_task_from_config(task_name, task_config, category)
                sub_tasks[task_name] = task
                logger.debug(f"Created sub-task: {task_name} (category: {category})")

            except Exception as e:
                error_msg = f"Failed to create sub-task '{task_name}': {e}"
                logger.error(error_msg)
                raise TaskDependencyError(error_msg) from e

        logger.info(f"Successfully created {len(sub_tasks)} sub-tasks")
        return sub_tasks

    def create_all_tasks(self, agents: Dict[str, Any]) -> Tuple[Dict[str, LangChainTaskWrapper], Dict[str, LangChainTaskWrapper]]:
        """
        Create all tasks (both system and sub-tasks) from configuration.

        Args:
            agents: Dictionary of available agents

        Returns:
            Tuple of (system_tasks, sub_tasks) dictionaries

        Raises:
            TaskValidationError: If configuration is not loaded or invalid
            TaskNotFoundException: If required agents are not found
            TaskDependencyError: If task creation fails
        """
        if not self._tasks_config:
            self.load_configuration()

        try:
            system_tasks = self.create_system_tasks(agents)
            sub_tasks = self.create_sub_tasks(agents)

            logger.info(
                f"Successfully created all tasks: "
                f"{len(system_tasks)} system tasks, {len(sub_tasks)} sub-tasks"
            )

            return system_tasks, sub_tasks

        except Exception as e:
            error_msg = f"Failed to create all tasks: {e}"
            logger.error(error_msg)
            raise TaskDependencyError(error_msg) from e

    def get_tasks_by_category(self, category: TaskCategory) -> List[str]:
        """
        Get all sub-task names for a specific category.

        Args:
            category: Task category to filter by

        Returns:
            List of task names in the specified category
        """
        if not self._tasks_config:
            return []

        category_tasks = []
        category_prefix = category.value + "_"

        for task_name in self._tasks_config.sub_tasks.keys():
            if task_name.startswith(category_prefix):
                category_tasks.append(task_name)

        return category_tasks

    def get_subtasks_by_category(self) -> Dict[str, List[str]]:
        """
        Get all subtasks organized by category.

        This method traverses all loaded sub-tasks and categorizes them based on
        their name prefixes (e.g., 'answer_', 'collect_', 'process_', etc.).

        Returns:
            Dictionary mapping category names to lists of subtask names

        Example:
            {
                "answer": ["answer_discuss", "answer_conclusion", "answer_questions"],
                "collect": ["collect_scrape", "collect_search", "collect_internalResources"],
                "process": ["process_dataCleaning", "process_dataNormalization"],
                ...
            }
        """
        if not self._tasks_config:
            logger.warning("Configuration not loaded. Returning empty subtasks mapping.")
            return {}

        subtasks_by_category = {}

        # Iterate through all sub-tasks and categorize them by prefix
        for task_name in self._tasks_config.sub_tasks.keys():
            if '_' in task_name:
                # Extract category from task name prefix
                category_prefix = task_name.split('_')[0]

                # Initialize category list if not exists
                if category_prefix not in subtasks_by_category:
                    subtasks_by_category[category_prefix] = []

                # Add task to category
                subtasks_by_category[category_prefix].append(task_name)

        logger.debug(f"Categorized subtasks: {subtasks_by_category}")
        return subtasks_by_category

    def validate_task_dependencies(self) -> bool:
        """
        Validate that all task dependencies can be resolved.

        Returns:
            True if all dependencies are valid, False otherwise
        """
        if not self._tasks_config:
            logger.warning("Configuration not loaded. Cannot validate dependencies.")
            return False

        # Basic validation - ensure all referenced agents exist in some form
        all_tasks = {**self._tasks_config.system_tasks, **self._tasks_config.sub_tasks}

        for task_name, task_config in all_tasks.items():
            agent_name = task_config.agent
            # This is a basic check - in a full implementation, you'd validate
            # against the actual agent registry or configuration
            if not agent_name:
                logger.error(f"Task '{task_name}' has no agent assigned")
                return False

        logger.info("Task dependency validation passed")
        return True

    def create_tasks_for_agent(self, agent) -> List[LangChainTaskWrapper]:
        """
        Create all tasks that can be executed by a specific agent.

        Args:
            agent: The agent to create tasks for

        Returns:
            List of LangChainTaskWrapper objects that the agent can execute

        Raises:
            TaskValidationError: If configuration is not loaded
        """
        if not self._tasks_config:
            raise TaskValidationError("Configuration not loaded. Call load_configuration() first.")

        # Get agent name/role for matching
        agent_name = None
        if hasattr(agent, 'config') and hasattr(agent.config, 'role'):
            role = agent.config.role
            agent_name = role.value if hasattr(role, 'value') else str(role)
        elif hasattr(agent, 'role'):
            role = agent.role
            agent_name = role.value if hasattr(role, 'value') else str(role)
        else:
            logger.warning(f"Could not determine agent name for: {agent}")
            return []

        matching_tasks = []
        all_tasks = {**self._tasks_config.system_tasks, **self._tasks_config.sub_tasks}

        for task_name, task_config in all_tasks.items():
            if task_config.agent == agent_name:
                try:
                    # Determine category for sub-tasks
                    category = None
                    if task_name in self._tasks_config.sub_tasks and '_' in task_name:
                        category_str = task_name.split('_')[0]
                        if category_str in TaskCategory.__members__.values():
                            category = TaskCategory(category_str)

                    # Register the agent temporarily
                    temp_agents = {agent_name: agent}
                    self.register_agents(temp_agents)

                    # Create the task
                    task = self._create_task_from_config(task_name, task_config, category)
                    matching_tasks.append(task)

                except Exception as e:
                    logger.error(f"Failed to create task '{task_name}' for agent '{agent_name}': {e}")

        logger.info(f"Created {len(matching_tasks)} tasks for agent '{agent_name}'")
        return matching_tasks


def create_all_tasks(tasks_config: TasksConfig, agents: Dict[str, Any]) -> Tuple[Dict[str, LangChainTaskWrapper], Dict[str, LangChainTaskWrapper]]:
    """
    Convenience function to create all tasks from a configuration object.

    Args:
        tasks_config: TasksConfig object with task definitions
        agents: Dictionary of available agents

    Returns:
        Tuple of (system_tasks, sub_tasks) dictionaries

    Raises:
        TaskDependencyError: If task creation fails
    """
    try:
        factory = TaskFactory()
        factory._tasks_config = tasks_config
        return factory.create_all_tasks(agents)

    except Exception as e:
        error_msg = f"Failed to create tasks from configuration: {e}"
        logger.error(error_msg)
        raise TaskDependencyError(error_msg) from e
