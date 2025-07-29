"""
Services Interfaces

This module contains all the interface definitions used across the multi-task services.
These interfaces have been extracted from individual service files for unified maintenance.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IPlanValidator(ABC):
    """Interface for plan validation services."""

    @abstractmethod
    async def validate_plan_structure(self, plan: Any) -> Dict[str, Any]:
        """
        Validate the structural integrity of a plan.

        Args:
            plan: Plan to validate

        Returns:
            Structural validation result
        """
        pass

    @abstractmethod
    async def validate_plan_feasibility(self, plan: Any, context: Any) -> Dict[str, Any]:
        """
        Validate the feasibility of a plan given available resources.

        Args:
            plan: Plan to validate
            context: Planning context with resource information

        Returns:
            Feasibility validation result
        """
        pass

    @abstractmethod
    async def validate_workflow_plan(self, plan: Dict[str, Any]) -> Any:
        """
        Validate a complete workflow plan.

        Args:
            plan: Workflow plan to validate

        Returns:
            Comprehensive validation result
        """
        pass

    @abstractmethod
    async def validate_dsl_syntax(self, dsl_plan: List[str]) -> Dict[str, Any]:
        """
        Validate DSL syntax for a plan.

        Args:
            dsl_plan: List of DSL steps to validate

        Returns:
            Syntax validation result
        """
        pass

    @abstractmethod
    async def validate_execution_feasibility(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate execution feasibility of a plan.

        Args:
            plan: Plan to validate for execution feasibility

        Returns:
            Feasibility validation result
        """
        pass

    @abstractmethod
    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get the current validation rules configuration.

        Returns:
            Dictionary of validation rules
        """
        pass


class IExamineOutcomeService(ABC):
    """Interface for examine outcome services."""

    @abstractmethod
    async def examine_task_outcome(self, request: Any) -> Any:
        """
        Examine a task outcome using both supervisor agent and quality processor.

        Args:
            request: Examination request with task details

        Returns:
            Comprehensive examination result
        """
        pass

    @abstractmethod
    async def examine_collect_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """
        Convenience method for examining collect task outcomes.

        Args:
            task_name: Name of the collect task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Examination result
        """
        pass

    @abstractmethod
    async def examine_process_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """
        Convenience method for examining process task outcomes.

        Args:
            task_name: Name of the process task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Examination result
        """
        pass


class IAcceptOutcomeService(ABC):
    """Interface for accept outcome services."""

    @abstractmethod
    async def accept_task_outcome(self, request: Any) -> Any:
        """
        Accept a task outcome using both director agent and quality processor.

        Args:
            request: Acceptance request with task details

        Returns:
            Comprehensive acceptance result
        """
        pass

    @abstractmethod
    async def accept_analyze_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """
        Convenience method for accepting analyze task outcomes.

        Args:
            task_name: Name of the analyze task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Acceptance result
        """
        pass

    @abstractmethod
    async def accept_generate_task(self, task_name: str, task_result: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """
        Convenience method for accepting generate task outcomes.

        Args:
            task_name: Name of the generate task
            task_result: Task execution result
            context: Optional execution context

        Returns:
            Acceptance result
        """
        pass


class IInteracterService(ABC):
    """Interface for interacter services."""

    @abstractmethod
    async def validate_user_request(self, user_input: str, context: Dict[str, Any] = None) -> Any:
        """
        Validate if user request contains substantial requirements for multi-task processing.

        Args:
            user_input: Raw user input text
            context: Optional context information

        Returns:
            InteractionResult with validation outcome and guidance
        """
        pass

    @abstractmethod
    async def provide_guidance(self, result: Any, user_input: str) -> str:
        """
        Provide user guidance based on validation result.

        Args:
            result: Validation result
            user_input: Original user input

        Returns:
            Guidance message for the user
        """
        pass

    @abstractmethod
    async def analyze_demand_state(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user demand state according to SMART criteria.

        Args:
            user_text: User input text to analyze
            context: Execution context

        Returns:
            Demand state analysis result
        """
        pass


class IMiningService(ABC):
    """Interface for mining services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service and underlying agents."""
        pass

    @abstractmethod
    async def mine_requirements(self, user_input: str, context: Any) -> Any:
        """
        Main entry point for mining user requirements.

        Args:
            user_input: User input text to analyze
            context: Mining context with metadata

        Returns:
            Mining result with requirements and blueprint
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the mining service.

        Returns:
            Health status information
        """
        pass

    @abstractmethod
    def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get service performance metrics.

        Returns:
            Dictionary containing service metrics
        """
        pass


class ISummarizerService(ABC):
    """Interface for summarizer services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize all service components."""
        pass

    @abstractmethod
    async def stream(self, input_data: Dict, context: Dict) -> Any:
        """
        Main streaming method using LangGraph workflow orchestration.

        Args:
            input_data: Input data for processing
            context: Execution context

        Returns:
            AsyncGenerator for streaming output
        """
        pass

    @abstractmethod
    async def run(self, input_data: Dict, context: Dict) -> Dict:
        """
        Non-streaming execution method.

        Args:
            input_data: Input data for processing
            context: Execution context

        Returns:
            Complete execution result
        """
        pass

    @abstractmethod
    async def update_session_feedback(self, session_id: str, feedback: Dict[str, Any]) -> bool:
        """
        Update session with user feedback.

        Args:
            session_id: Session identifier
            feedback: User feedback data

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get service performance metrics.

        Returns:
            Dictionary containing service metrics
        """
        pass

    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information and capabilities.

        Returns:
            Service information dictionary
        """
        pass


class IWorkflowPlanningService(ABC):
    """Interface for workflow planning services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service and all agents."""
        pass

    @abstractmethod
    async def create_workflow_plan(self, mining_input: Dict[str, Any], user_id: str = "anonymous", task_id: str = None) -> Dict[str, Any]:
        """
        Create a comprehensive workflow plan from mining.py input.

        Args:
            mining_input: Pre-processed input from mining.py
            user_id: User identifier
            task_id: Optional task identifier

        Returns:
            Complete workflow plan with DSL, agent mapping, and validation results
        """
        pass

    @abstractmethod
    def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get service performance metrics.

        Returns:
            Dictionary containing service metrics
        """
        pass
