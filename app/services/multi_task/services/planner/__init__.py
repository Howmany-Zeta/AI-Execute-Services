"""
Planner Layer

The planner layer serves as the "brain" of the multi-task architecture, responsible for
high-level decision making and workflow planning. This layer extracts and refactors
the planning logic from the original summarizer service, following SOLID principles.

Key Components:
- WorkflowPlanningService: New LangGraph-based workflow planning service that integrates
  task_decomposer and planner agents, accepts input from mining.py
- PlanValidatorService: Plan validation services for syntax, logic, and feasibility checking

Architecture Principles:
- Single Responsibility Principle (SRP): Each service handles one specific function
- Dependency Inversion Principle (DIP): Services depend on abstractions, not concretions
- Open/Closed Principle (OCP): Open for extension, closed for modification
- Interface Segregation Principle (ISP): Small, focused interfaces

Usage:
    from app.services.multi_task.services.planner import WorkflowPlanningService

    # Initialize with configuration managers
    planning_service = WorkflowPlanningService(config_manager, llm_manager)
    await planning_service.initialize()

    # Create a workflow plan from mining.py input
    result = await planning_service.create_workflow_plan(
        mining_input={
            "intent_categories": ["collect", "analyze", "generate"],
            "intent_confidence": 0.9,
            "intent_reasoning": "User wants data analysis and reporting",
            "strategic_blueprint": {...}
        },
        user_id="user123"
    )
"""

# Import from existing modules
from .workflow_planning import WorkflowPlanningService
from .validation import PlanValidatorService

__all__ = [
    "WorkflowPlanningService",
    "PlanValidatorService"
]

# Version information
__version__ = "1.0.0"
__author__ = "Multi-Task Architecture Team"
__description__ = "Enhanced planner layer with LangGraph integration for multi-task workflow orchestration"

# Service registry for dependency injection
PLANNER_SERVICES = {
    "workflow_planning": WorkflowPlanningService,
    "plan_validator": PlanValidatorService
}

def create_planner_service(service_name: str, *args, **kwargs):
    """
    Factory function to create planner services.

    Args:
        service_name: Name of the service to create
        *args: Positional arguments for service initialization
        **kwargs: Keyword arguments for service initialization

    Returns:
        Instance of the requested planner service

    Raises:
        ValueError: If service_name is not recognized
    """
    if service_name not in PLANNER_SERVICES:
        available_services = ", ".join(PLANNER_SERVICES.keys())
        raise ValueError(f"Unknown planner service: {service_name}. Available services: {available_services}")

    service_class = PLANNER_SERVICES[service_name]
    return service_class(*args, **kwargs)

def get_available_services():
    """
    Get list of available planner services.

    Returns:
        List of available service names
    """
    return list(PLANNER_SERVICES.keys())

# Module organization information
PLANNER_MODULES = {
    "workflow_planning": {
        "description": "LangGraph-based workflow planning service with enhanced capabilities",
        "services": ["WorkflowPlanningService"],
        "features": [
            "Accepts input from mining.py (intent categories and strategic blueprint)",
            "Integrates task_decomposer and planner agents using LangGraph",
            "Enhanced task decomposition with agent mapping",
            "DSL validation using plan_validator",
            "Comprehensive workflow plan generation"
        ]
    },
    "validation": {
        "description": "Plan validation and verification services",
        "services": ["PlanValidatorService"],
        "features": [
            "DSL syntax validation",
            "Logical flow analysis",
            "Dependency validation",
            "Performance assessment"
        ]
    }
}

def get_module_info():
    """
    Get information about planner modules and their services.

    Returns:
        Dictionary containing module organization information
    """
    return PLANNER_MODULES.copy()

def get_service_capabilities():
    """
    Get detailed capabilities of available services.

    Returns:
        Dictionary mapping service names to their capabilities
    """
    capabilities = {}

    for service_name, service_class in PLANNER_SERVICES.items():
        if hasattr(service_class, 'get_service_metrics'):
            capabilities[service_name] = {
                "type": "enhanced_service",
                "supports_metrics": True,
                "async_operations": True
            }
        else:
            capabilities[service_name] = {
                "type": "standard_service",
                "supports_metrics": False,
                "async_operations": True
            }

    return capabilities
