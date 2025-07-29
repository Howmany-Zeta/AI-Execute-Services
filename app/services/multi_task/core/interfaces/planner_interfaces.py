"""
Planner Layer Interfaces

Defines the contracts for planner layer implementations following the
Interface Segregation Principle (ISP) and Dependency Inversion Principle (DIP).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from ..models.planner_models import PlannerConfig, WorkflowPlan, PlanningContext
from ..models.architect_models import BlueprintConstructionRequest, BlueprintConstructionResult, FrameworkRecommendation, StrategicPlan


class IIntentParser(ABC):
    """
    Interface for intent parsing implementations.

    Responsible for analyzing user input and identifying intent categories.
    Follows SRP by focusing solely on intent parsing functionality.
    """

    @abstractmethod
    async def parse_intent(self, input_data: Dict[str, Any], context: PlanningContext) -> List[str]:
        """
        Parse user input to identify intent categories.

        Args:
            input_data: Raw input data from the user
            context: Planning context with additional metadata

        Returns:
            List of identified intent categories

        Raises:
            IntentParsingError: If intent parsing fails
        """
        pass

    @abstractmethod
    async def validate_intent(self, categories: List[str]) -> Dict[str, Any]:
        """
        Validate identified intent categories.

        Args:
            categories: List of intent categories to validate

        Returns:
            Validation result with confidence scores and feedback

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    def get_supported_categories(self) -> List[str]:
        """
        Get list of supported intent categories.

        Returns:
            List of supported category names
        """
        pass


class ITaskDecomposer(ABC):
    """
    Interface for task decomposition implementations.

    Responsible for breaking down intent categories into executable sub-tasks.
    Follows SRP by focusing solely on task decomposition functionality.
    """

    @abstractmethod
    async def decompose_tasks(self, categories: List[str], context: PlanningContext) -> Dict[str, List[str]]:
        """
        Break down intent categories into executable sub-tasks.

        Args:
            categories: List of intent categories to decompose
            context: Planning context with additional metadata

        Returns:
            Mapping of categories to their corresponding sub-tasks

        Raises:
            DecompositionError: If task decomposition fails
        """
        pass

    @abstractmethod
    async def validate_decomposition(self, breakdown: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate task decomposition result.

        Args:
            breakdown: Task breakdown to validate

        Returns:
            Validation result with feasibility analysis

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    def get_available_subtasks(self, category: str) -> List[str]:
        """
        Get available sub-tasks for a specific category.

        Args:
            category: Category name

        Returns:
            List of available sub-tasks for the category
        """
        pass


class ISequencePlanner(ABC):
    """
    Interface for sequence planning implementations.

    Responsible for creating optimized execution sequences from sub-task breakdowns.
    Follows SRP by focusing solely on sequence planning functionality.
    """

    @abstractmethod
    async def plan_sequence(self, subtask_breakdown: Dict[str, List[str]], context: PlanningContext) -> List[Dict[str, Any]]:
        """
        Plan execution sequence for sub-tasks.

        Args:
            subtask_breakdown: Mapping of categories to sub-tasks
            context: Planning context with tools and constraints

        Returns:
            Ordered list of execution steps in DSL format

        Raises:
            PlanningError: If sequence planning fails
        """
        pass

    @abstractmethod
    async def optimize_sequence(self, sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize execution sequence for efficiency.

        Args:
            sequence: Original execution sequence

        Returns:
            Optimized execution sequence

        Raises:
            PlanningError: If optimization fails
        """
        pass

    @abstractmethod
    async def validate_sequence(self, sequence: List[Dict[str, Any]], context: PlanningContext) -> Dict[str, Any]:
        """
        Validate execution sequence for correctness and feasibility.

        Args:
            sequence: Execution sequence to validate
            context: Planning context for validation

        Returns:
            Validation result with analysis and recommendations

        Raises:
            ValidationError: If validation fails
        """
        pass


class IPlannerService(ABC):
    """
    Main interface for the planner service.

    Orchestrates the complete planning workflow by coordinating
    intent parsing, task decomposition, and sequence planning.
    Follows SRP by focusing on high-level workflow orchestration.
    """

    @abstractmethod
    async def initialize(self, config: PlannerConfig) -> None:
        """
        Initialize the planner service.

        Args:
            config: Planner configuration

        Raises:
            ConfigurationError: If configuration is invalid
            ResourceError: If required resources are unavailable
        """
        pass

    @abstractmethod
    async def create_plan(self, input_data: Dict[str, Any], context: Optional[PlanningContext] = None) -> WorkflowPlan:
        """
        Create a complete workflow plan from user input.

        This is the main orchestration method that coordinates:
        1. Intent parsing
        2. Task decomposition
        3. Sequence planning

        Args:
            input_data: User input data
            context: Optional planning context

        Returns:
            Complete workflow plan ready for execution

        Raises:
            PlannerException: If any step of planning fails
        """
        pass

    @abstractmethod
    async def validate_plan(self, plan: WorkflowPlan) -> Dict[str, Any]:
        """
        Validate a complete workflow plan.

        Args:
            plan: Workflow plan to validate

        Returns:
            Comprehensive validation result

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def get_plan_metrics(self, plan: WorkflowPlan) -> Dict[str, Any]:
        """
        Get metrics and analysis for a workflow plan.

        Args:
            plan: Workflow plan to analyze

        Returns:
            Plan metrics including complexity, estimated duration, etc.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources used by the planner service.
        """
        pass


class IPlanValidator(ABC):
    """
    Interface for plan validation implementations.

    Responsible for validating workflow plans for correctness,
    feasibility, and optimization opportunities.
    """

    @abstractmethod
    async def validate_plan_structure(self, plan: WorkflowPlan) -> Dict[str, Any]:
        """
        Validate the structural integrity of a plan.

        Args:
            plan: Plan to validate

        Returns:
            Structural validation result
        """
        pass

    @abstractmethod
    async def validate_plan_feasibility(self, plan: WorkflowPlan, context: PlanningContext) -> Dict[str, Any]:
        """
        Validate the feasibility of a plan given available resources.

        Args:
            plan: Plan to validate
            context: Planning context with resource information

        Returns:
            Feasibility validation result
        """
        pass


class IBlueprintConstructor(ABC):
    """
    Interface for blueprint construction implementations.

    Responsible for analyzing complex problems and constructing strategic blueprints
    using analytical frameworks and decomposition strategies.
    Follows SRP by focusing solely on blueprint construction functionality.
    """

    @abstractmethod
    async def construct_blueprint(
        self,
        request: BlueprintConstructionRequest,
        context: PlanningContext
    ) -> BlueprintConstructionResult:
        """
        Construct strategic blueprint for complex problems.

        Args:
            request: Blueprint construction request with problem details
            context: Planning context with additional metadata

        Returns:
            Blueprint construction result with strategic plan

        Raises:
            BlueprintConstructionError: If blueprint construction fails
        """
        pass

    @abstractmethod
    async def validate_blueprint(self, strategic_plan: StrategicPlan) -> Dict[str, Any]:
        """
        Validate constructed strategic blueprint.

        Args:
            strategic_plan: Strategic plan to validate

        Returns:
            Validation result with confidence scores and feedback

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def get_framework_recommendations(
        self,
        problem_description: str,
        domain: str,
        complexity: str
    ) -> List[FrameworkRecommendation]:
        """
        Get framework recommendations for a problem.

        Args:
            problem_description: Description of the problem
            domain: Problem domain
            complexity: Problem complexity level

        Returns:
            List of framework recommendations
        """
        pass

    @abstractmethod
    def get_supported_domains(self) -> List[str]:
        """
        Get list of supported problem domains.

        Returns:
            List of supported domain names
        """
        pass

    @abstractmethod
    def get_supported_complexities(self) -> List[str]:
        """
        Get list of supported complexity levels.

        Returns:
            List of supported complexity levels
        """
        pass

    @abstractmethod
    async def suggest_optimizations(self, plan: WorkflowPlan) -> List[Dict[str, Any]]:
        """
        Suggest optimizations for a workflow plan.

        Args:
            plan: Plan to optimize

        Returns:
            List of optimization suggestions
        """
        pass
