"""
Agent Factory

Factory class for creating different types of agents based on configuration.
Implements the Factory pattern to provide a unified interface for agent creation.
"""

import logging
from typing import Dict, Type, Optional, List, Any
from ..base_agent import BaseAgent
from ..system import (
    IntentParserAgent,
    TaskDecomposerAgent,
    PlannerAgent,
    SupervisorAgent,
    DirectorAgent
)
from ..domain import (
    ResearcherAgent,
    AnalystAgent,
    FieldworkAgent,
    WriterAgent,
    MetaArchitectAgent
)
from ...core.models.agent_models import AgentConfig, AgentRole, AgentType
from ...core.exceptions.task_exceptions import TaskValidationError
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager
from ...tools.langchain_integration_manager import LangChainIntegrationManager

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating agents based on configuration.

    Supports both predefined agent types and custom agent creation
    from configuration files.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        llm_manager: LLMIntegrationManager,
        tool_integration_manager: Optional[LangChainIntegrationManager] = None
    ):
        """
        Initialize the agent factory.

        Args:
            config_manager: Configuration manager for loading agent configs
            llm_manager: LLM integration manager for actual LLM calls
            tool_integration_manager: Optional LangChain tool integration manager
        """
        self.config_manager = config_manager
        self.llm_manager = llm_manager
        self.tool_integration_manager = tool_integration_manager

        # Registry of agent classes by role
        self._agent_classes: Dict[AgentRole, Type[BaseAgent]] = {
            # System agents
            AgentRole.INTENT_PARSER: IntentParserAgent,
            AgentRole.TASK_DECOMPOSER: TaskDecomposerAgent,
            AgentRole.PLANNER: PlannerAgent,
            AgentRole.SUPERVISOR: SupervisorAgent,
            AgentRole.DIRECTOR: DirectorAgent,

            # Domain agents - original mappings
            AgentRole.RESEARCHER: ResearcherAgent,
            AgentRole.ANALYST: AnalystAgent,
            AgentRole.FIELDWORK: FieldworkAgent,
            AgentRole.WRITER: WriterAgent,

            # Domain agents - new general mappings
            AgentRole.GENERAL_RESEARCHER: ResearcherAgent,
            AgentRole.GENERAL_ANALYST: AnalystAgent,
            AgentRole.GENERAL_FIELDWORK: FieldworkAgent,
            AgentRole.GENERAL_WRITER: WriterAgent,

            # Domain agents - specialized mappings (fallback to general types)
            AgentRole.RESEARCHER_DISCUSSIONFACILITATOR: ResearcherAgent,
            AgentRole.RESEARCHER_KNOWLEDGEPROVIDER: ResearcherAgent,
            AgentRole.RESEARCHER_IDEAGENERATOR: ResearcherAgent,
            AgentRole.WRITER_CONCLUSIONSPECIALIST: WriterAgent,
            AgentRole.FIELDWORK_WEBSCRAPER: FieldworkAgent,
            AgentRole.FIELDWORK_APISEARCHER: FieldworkAgent,
            AgentRole.FIELDWORK_INTERNALDATACOLLECTOR: FieldworkAgent,
            AgentRole.FIELDWORK_EXTERNALDATACOLLECTOR: FieldworkAgent,
            AgentRole.FIELDWORK_DATAOPERATOR: FieldworkAgent,
            AgentRole.FIELDWORK_DATAENGINEER: FieldworkAgent,
            AgentRole.FIELDWORK_STATISTICIAN: FieldworkAgent,
            AgentRole.FIELDWORK_DATASCIENTIST: FieldworkAgent,
            AgentRole.FIELDWORK_DOCUMENTCONVERTER: FieldworkAgent,
            AgentRole.FIELDWORK_DOCUMENTCLEANER: FieldworkAgent,
            AgentRole.FIELDWORK_DOCUMENTSEGMENTER: FieldworkAgent,
            AgentRole.FIELDWORK_TEXTPROCESSOR: FieldworkAgent,
            AgentRole.FIELDWORK_DATAEXTRACTOR: FieldworkAgent,
            AgentRole.FIELDWORK_IMAGEEXTRACTOR: FieldworkAgent,
            AgentRole.FIELDWORK_IMAGEPROCESSOR: FieldworkAgent,
            AgentRole.ANALYST_DATAOUTCOMESPECIALIST: AnalystAgent,
            AgentRole.ANALYST_CONTEXTSPECIALIST: AnalystAgent,
            AgentRole.ANALYST_IMAGEANALYST: AnalystAgent,
            AgentRole.ANALYST_CLASSIFICATIONSPECIALIST: AnalystAgent,
            AgentRole.ANALYST_CODESPECIALIST: AnalystAgent,
            AgentRole.ANALYST_PREDICTIVESPECIALIST: AnalystAgent,
            AgentRole.ANALYST_REFININGSPECIALIST: AnalystAgent,
            AgentRole.WRITER_FORMATSPECIALIST: WriterAgent,
            AgentRole.WRITER_TABLESPECIALIST: WriterAgent,
            AgentRole.WRITER_CONTENTSPECIALIST: WriterAgent,
            AgentRole.WRITER_SUMMARIZATIONSPECIALIST: WriterAgent,
            AgentRole.WRITER_VISUALIZATIONSPECIALIST: WriterAgent,
            AgentRole.WRITER_IMAGESPECIALIST: WriterAgent,
            AgentRole.WRITER_REPORTSPECIALIST: WriterAgent,
            AgentRole.WRITER_CODESPECIALIST: WriterAgent,

            # Specialized agents
            AgentRole.META_ARCHITECT: MetaArchitectAgent,
        }

        # Custom agent factory functions
        self._custom_factories: Dict[str, callable] = {}

        logger.info("Agent factory initialized")

    def create_agent(self, config: AgentConfig) -> BaseAgent:
        """
        Create an agent based on the provided configuration.

        Args:
            config: Agent configuration

        Returns:
            Created agent instance

        Raises:
            TaskValidationError: If agent creation fails
        """
        try:
            # Validate configuration
            validation_errors = self._validate_config(config)
            if validation_errors:
                raise TaskValidationError(
                    message="Agent configuration validation failed",
                    validation_errors={"config_errors": validation_errors}
                )

            # Get agent class
            agent_class = self._get_agent_class(config.role, config.agent_type)

            # Create agent instance with tool integration manager
            agent = agent_class(
                config=config,
                config_manager=self.config_manager,
                llm_manager=self.llm_manager,
                tool_integration_manager=self.tool_integration_manager
            )

            logger.info(f"Created agent: {agent.agent_id} ({config.role.value})")
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise TaskValidationError(
                message=f"Agent creation failed: {e}",
                validation_errors={"creation_error": str(e)}
            )

    def create_agent_from_role_config(self, role_name: str, **overrides) -> BaseAgent:
        """
        Create an agent from role configuration in prompts.yaml.

        Args:
            role_name: Name of the role in the configuration
            **overrides: Configuration overrides

        Returns:
            Created agent instance

        Raises:
            TaskValidationError: If role not found or creation fails
        """
        try:
            # Get role configuration
            role_config = self.config_manager.get_role_config(role_name)
            if not role_config:
                raise ValueError(f"Role configuration not found: {role_name}")

            # Convert role name to AgentRole enum
            agent_role = self._map_role_name_to_enum(role_name)

            # Build agent configuration
            config_data = {
                'name': role_name,
                'role': agent_role,
                'agent_type': AgentType.SYSTEM if agent_role != AgentRole.CUSTOM else AgentType.CUSTOM,
                'goal': role_config['goal'],
                'backstory': role_config['backstory'],
                'tools': role_config.get('tools', []),
                'tools_instruction': role_config.get('tools_instruction'),
                'domain_specialization': role_config.get('domain_specialization'),
                **overrides
            }

            config = AgentConfig(**config_data)
            return self.create_agent(config)

        except Exception as e:
            logger.error(f"Failed to create agent from role config {role_name}: {e}")
            raise TaskValidationError(
                message=f"Agent creation from role config failed: {e}",
                validation_errors={"role_config_error": str(e)}
            )

    def create_agents_from_config(self) -> Dict[str, BaseAgent]:
        """
        Create all agents defined in the configuration.

        Returns:
            Dictionary mapping role names to agent instances

        Raises:
            TaskValidationError: If any agent creation fails
        """
        agents = {}

        try:
            # Get all available roles from configuration
            role_names = self.config_manager.list_available_roles()

            for role_name in role_names:
                try:
                    agent = self.create_agent_from_role_config(role_name)
                    agents[role_name] = agent
                    logger.info(f"Created agent from config: {role_name}")
                except Exception as e:
                    logger.error(f"Failed to create agent {role_name}: {e}")
                    # Continue with other agents instead of failing completely
                    continue

            logger.info(f"Created {len(agents)} agents from configuration")
            return agents

        except Exception as e:
            logger.error(f"Failed to create agents from configuration: {e}")
            raise TaskValidationError(
                message=f"Batch agent creation failed: {e}",
                validation_errors={"batch_creation_error": str(e)}
            )

    def register_custom_agent_type(self, agent_type: str, factory_func: callable) -> None:
        """
        Register a custom agent factory function.

        Args:
            agent_type: Name of the custom agent type
            factory_func: Function that creates the agent (takes AgentConfig, returns BaseAgent)

        Raises:
            ValueError: If agent type already registered
        """
        if agent_type in self._custom_factories:
            raise ValueError(f"Agent type already registered: {agent_type}")

        self._custom_factories[agent_type] = factory_func
        logger.info(f"Registered custom agent type: {agent_type}")

    def get_available_agent_types(self) -> List[str]:
        """
        Get list of available agent types.

        Returns:
            List of agent type names
        """
        predefined_types = [role.value for role in AgentRole]
        custom_types = list(self._custom_factories.keys())
        return predefined_types + custom_types

    def _get_agent_class(self, role: AgentRole, agent_type: AgentType) -> Type[BaseAgent]:
        """
        Get the appropriate agent class for the given role and type.

        Args:
            role: Agent role
            agent_type: Agent type

        Returns:
            Agent class

        Raises:
            ValueError: If no suitable agent class found
        """
        # Check for predefined agent classes
        if role in self._agent_classes:
            return self._agent_classes[role]

        # Check for custom agent factories
        role_name = role.value if hasattr(role, 'value') else str(role)
        if role_name in self._custom_factories:
            # Return a wrapper class that uses the custom factory
            class CustomAgentWrapper(BaseAgent):
                def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager: Optional[LangChainIntegrationManager] = None):
                    super().__init__(config, config_manager, llm_manager, tool_integration_manager)
                    self._custom_agent = self._custom_factories[role_name](config)

                async def initialize(self):
                    if hasattr(self._custom_agent, 'initialize'):
                        await self._custom_agent.initialize()

                async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
                    return await self._custom_agent.execute_task(task_data, context)

                def get_capabilities(self) -> List[str]:
                    if hasattr(self._custom_agent, 'get_capabilities'):
                        return self._custom_agent.get_capabilities()
                    return []

            return CustomAgentWrapper

        # Handle CUSTOM role with a generic agent implementation
        if role == AgentRole.CUSTOM:
            # Create a generic agent class for custom roles
            class GenericCustomAgent(BaseAgent):
                def __init__(self, config: AgentConfig, config_manager: ConfigManager, llm_manager: LLMIntegrationManager, tool_integration_manager: Optional[LangChainIntegrationManager] = None):
                    super().__init__(config, config_manager, llm_manager, tool_integration_manager)

                async def initialize(self):
                    """Initialize the generic custom agent."""
                    logger.info(f"Initialized generic custom agent: {self.config.name}")

                async def execute_task(self, task_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
                    """Execute task using LangChain agent with tool integration."""
                    try:
                        # Use tool integration manager if available
                        if self.tool_integration_manager:
                            logger.info(f"Executing task with tool integration for {self.config.name}")
                            return await self.tool_integration_manager.execute_agent_task_with_tools(
                                self.config, task_data, context
                            )
                        else:
                            # Fallback to basic LangChain agent execution
                            langchain_agent = await self.create_langchain_agent(context)

                            # Execute the task using LangChain AgentExecutor
                            result = await langchain_agent.arun(
                                input=task_data.get('description', ''),
                                task_description=task_data.get('description', ''),
                                expected_output=task_data.get('expected_output', ''),
                                input_data=task_data
                            )

                            return {
                                "status": "completed",
                                "result": result,
                                "agent_id": self.agent_id,
                                "task_data": task_data,
                                "context": context
                            }
                    except Exception as e:
                        logger.error(f"Task execution failed for {self.config.name}: {e}")
                        return {
                            "status": "failed",
                            "error": str(e),
                            "agent_id": self.agent_id
                        }

                def get_capabilities(self) -> List[str]:
                    """Get capabilities from configuration."""
                    capabilities = []
                    if self.config.tools:
                        capabilities.extend([f"tool:{tool}" for tool in self.config.tools])
                    if self.config.domain_specialization:
                        capabilities.append(f"domain:{self.config.domain_specialization}")
                    capabilities.append("custom_agent")
                    return capabilities

            return GenericCustomAgent

        raise ValueError(f"No agent class found for role: {role}")

    def _map_role_name_to_enum(self, role_name: str) -> AgentRole:
        """
        Map role name to AgentRole enum with intelligent mapping for specialized roles.

        Args:
            role_name: Role name from configuration

        Returns:
            Corresponding AgentRole enum value
        """
        # Direct mapping for exact matches
        try:
            return AgentRole(role_name.lower())
        except ValueError:
            pass

        # Intelligent mapping for specialized roles
        role_lower = role_name.lower()

        # System agent mappings
        if role_lower in ['intent_parser', 'intentparser']:
            return AgentRole.INTENT_PARSER
        elif role_lower in ['task_decomposer', 'taskdecomposer']:
            return AgentRole.TASK_DECOMPOSER
        elif role_lower in ['planner']:
            return AgentRole.PLANNER
        elif role_lower in ['supervisor']:
            return AgentRole.SUPERVISOR
        elif role_lower in ['director']:
            return AgentRole.DIRECTOR

        # Domain agent mappings based on prefix
        elif role_lower.startswith('researcher'):
            return AgentRole.RESEARCHER
        elif role_lower.startswith('analyst'):
            return AgentRole.ANALYST
        elif role_lower.startswith('fieldwork'):
            return AgentRole.FIELDWORK
        elif role_lower.startswith('writer'):
            return AgentRole.WRITER

        # Specialized agent mappings
        elif role_lower in ['meta_architect', 'metaarchitect']:
            return AgentRole.META_ARCHITECT

        # Fallback to CUSTOM for unrecognized roles
        else:
            return AgentRole.CUSTOM

    def _validate_config(self, config: AgentConfig) -> List[str]:
        """
        Validate agent configuration.

        Args:
            config: Agent configuration to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Basic validation
        if not config.name:
            errors.append("Agent name is required")

        if not config.goal:
            errors.append("Agent goal is required")

        if not config.backstory:
            errors.append("Agent backstory is required")

        # Role validation
        if not isinstance(config.role, AgentRole):
            errors.append("Invalid agent role")

        # Type validation
        if not isinstance(config.agent_type, AgentType):
            errors.append("Invalid agent type")

        # Numeric constraints
        if config.temperature < 0.0 or config.temperature > 2.0:
            errors.append("Temperature must be between 0.0 and 2.0")

        if config.quality_threshold < 0.0 or config.quality_threshold > 1.0:
            errors.append("Quality threshold must be between 0.0 and 1.0")

        if config.max_iter <= 0:
            errors.append("Max iterations must be positive")

        if config.context_window <= 0:
            errors.append("Context window must be positive")

        # Tools validation
        if config.tools:
            # TODO: Validate that tools exist
            pass

        return errors

    def create_agent_team(self, agent_configs: List[AgentConfig]) -> List[BaseAgent]:
        """
        Create a team of agents.

        Args:
            agent_configs: List of agent configurations

        Returns:
            List of created agents

        Raises:
            TaskValidationError: If any agent creation fails
        """
        agents = []

        try:
            for config in agent_configs:
                agent = self.create_agent(config)
                agents.append(agent)

            logger.info(f"Created agent team with {len(agents)} agents")
            return agents

        except Exception as e:
            logger.error(f"Failed to create agent team: {e}")
            raise TaskValidationError(
                message=f"Agent team creation failed: {e}",
                validation_errors={"team_creation_error": str(e)}
            )

    def clone_agent(self, agent: BaseAgent, **config_overrides) -> BaseAgent:
        """
        Clone an existing agent with optional configuration overrides.

        Args:
            agent: Agent to clone
            **config_overrides: Configuration overrides

        Returns:
            Cloned agent instance
        """
        # Create new config based on existing agent
        config_data = agent.config.dict()
        config_data.update(config_overrides)

        # Generate new name if not overridden
        if 'name' not in config_overrides:
            config_data['name'] = f"{agent.config.name}_clone"

        new_config = AgentConfig(**config_data)
        return self.create_agent(new_config)
