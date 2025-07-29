"""
Agent Models

Data models for agent-related entities in the multi-task service.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class AgentType(Enum):
    """Agent type enumeration."""
    SYSTEM = "system"
    DOMAIN = "domain"
    CUSTOM = "custom"


class AgentRole(Enum):
    """Agent role enumeration."""
    # System agents
    INTENT_PARSER = "intent_parser"
    TASK_DECOMPOSER = "task_decomposer"
    PLANNER = "planner"
    SUPERVISOR = "supervisor"
    DIRECTOR = "director"

    # Answer agents
    GENERAL_RESEARCHER = "general_researcher"
    RESEARCHER_DISCUSSIONFACILITATOR = "researcher_discussionfacilitator"
    RESEARCHER_KNOWLEDGEPROVIDER = "researcher_knowledgeprovider"
    RESEARCHER_IDEAGENERATOR = "researcher_ideagenerator"
    WRITER_CONCLUSIONSPECIALIST = "writer_conclusionspecialist"

    # Collect agents
    FIELDWORK_WEBSCRAPER = "fieldwork_webscraper"
    FIELDWORK_APISEARCHER = "fieldwork_apisearcher"
    FIELDWORK_INTERNALDATACOLLECTOR = "fieldwork_internaldatacollector"
    FIELDWORK_EXTERNALDATACOLLECTOR = "fieldwork_externaldatacollector"

    # Process agents
    GENERAL_FIELDWORK = "general_fieldwork"
    FIELDWORK_DATAOPERATOR = "fieldwork_dataoperator"
    FIELDWORK_DATAENGINEER = "fieldwork_dataengineer"
    FIELDWORK_STATISTICIAN = "fieldwork_statistician"
    FIELDWORK_DATASCIENTIST = "fieldwork_datascientist"
    FIELDWORK_DOCUMENTCONVERTER = "fieldwork_documentconverter"
    FIELDWORK_DOCUMENTCLEANER = "fieldwork_documentcleaner"
    FIELDWORK_DOCUMENTSEGMENTER = "fieldwork_documentsegmenter"
    FIELDWORK_TEXTPROCESSOR = "fieldwork_textprocessor"
    FIELDWORK_DATAEXTRACTOR = "fieldwork_dataextractor"
    FIELDWORK_IMAGEEXTRACTOR = "fieldwork_imageextractor"
    FIELDWORK_IMAGEPROCESSOR = "fieldwork_imageprocessor"

    # Analyze agents
    GENERAL_ANALYST = "general_analyst"
    ANALYST_DATAOUTCOMESPECIALIST = "analyst_dataoutcomespecialist"
    ANALYST_CONTEXTSPECIALIST = "analyst_contextspecialist"
    ANALYST_IMAGEANALYST = "analyst_imageanalyst"
    ANALYST_CLASSIFICATIONSPECIALIST = "analyst_classificationspecialist"
    ANALYST_CODESPECIALIST = "analyst_codespecialist"
    ANALYST_PREDICTIVESPECIALIST = "analyst_predictivespecialist"
    ANALYST_REFININGSPECIALIST = "analyst_refiningspecialist"

    # Generate agents
    GENERAL_WRITER = "general_writer"
    WRITER_FORMATSPECIALIST = "writer_formatspecialist"
    WRITER_TABLESPECIALIST = "writer_tablespecialist"
    WRITER_CONTENTSPECIALIST = "writer_contentspecialist"
    WRITER_SUMMARIZATIONSPECIALIST = "writer_summarizationspecialist"
    WRITER_VISUALIZATIONSPECIALIST = "writer_visualizationspecialist"
    WRITER_IMAGESPECIALIST = "writer_imagespecialist"
    WRITER_REPORTSPECIALIST = "writer_reportspecialist"
    WRITER_CODESPECIALIST = "writer_codespecialist"

    # Specialized agents
    META_ARCHITECT = "meta_architect"

    # Legacy/backward compatibility
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    FIELDWORK = "fieldwork"
    WRITER = "writer"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentCapability(BaseModel):
    """
    Model representing an agent capability.
    """
    name: str = Field(..., description="Name of the capability")
    description: str = Field(..., description="Description of the capability")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Capability parameters")
    enabled: bool = Field(default=True, description="Whether the capability is enabled")


class AgentConfig(BaseModel):
    """
    Configuration model for agent creation and updates.
    """
    # Basic information
    name: str = Field(..., description="Name of the agent")
    role: AgentRole = Field(..., description="Role of the agent")
    agent_type: AgentType = Field(default=AgentType.CUSTOM, description="Type of the agent")

    # Agent behavior
    goal: str = Field(..., description="Primary goal of the agent")
    backstory: str = Field(..., description="Background story and context for the agent")

    # Configuration
    verbose: bool = Field(default=True, description="Whether agent should be verbose")
    allow_delegation: bool = Field(default=False, description="Whether agent can delegate tasks")
    max_iter: int = Field(default=10, description="Maximum iterations for agent execution")
    max_execution_time: Optional[int] = Field(None, description="Maximum execution time in seconds")

    # Tools and capabilities
    tools: List[str] = Field(default_factory=list, description="List of tool names available to the agent")
    tools_instruction: Optional[str] = Field(None, description="Instructions for tool usage")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="Agent capabilities")

    # Domain specialization
    domain_specialization: Optional[str] = Field(None, description="Domain of specialization")
    domain_knowledge: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific knowledge")

    # LLM configuration
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM configuration for the agent")
    temperature: float = Field(default=0.7, description="LLM temperature setting")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for LLM responses")

    # Memory and context
    memory_enabled: bool = Field(default=True, description="Whether agent has memory capabilities")
    context_window: int = Field(default=4000, description="Context window size")

    # Quality control
    quality_threshold: float = Field(default=0.8, description="Quality threshold for agent outputs")
    validation_enabled: bool = Field(default=True, description="Whether to validate agent outputs")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        # Remove use_enum_values to keep enums as enum objects instead of strings
        pass


class AgentModel(BaseModel):
    """
    Core agent model representing an agent in the system.
    """
    # Identification
    agent_id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Name of the agent")
    role: AgentRole = Field(..., description="Role of the agent")
    agent_type: AgentType = Field(..., description="Type of the agent")

    # Status and state
    status: AgentStatus = Field(default=AgentStatus.ACTIVE, description="Current agent status")
    is_available: bool = Field(default=True, description="Whether agent is available for tasks")
    current_task_id: Optional[str] = Field(None, description="ID of currently executing task")

    # Configuration (embedded from AgentConfig)
    goal: str = Field(..., description="Primary goal of the agent")
    backstory: str = Field(..., description="Background story and context for the agent")
    verbose: bool = Field(default=True, description="Whether agent should be verbose")
    allow_delegation: bool = Field(default=False, description="Whether agent can delegate tasks")
    max_iter: int = Field(default=10, description="Maximum iterations for agent execution")
    max_execution_time: Optional[int] = Field(None, description="Maximum execution time in seconds")

    # Tools and capabilities
    tools: List[str] = Field(default_factory=list, description="List of tool names available to the agent")
    tools_instruction: Optional[str] = Field(None, description="Instructions for tool usage")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="Agent capabilities")

    # Domain specialization
    domain_specialization: Optional[str] = Field(None, description="Domain of specialization")
    domain_knowledge: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific knowledge")

    # LLM configuration
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM configuration for the agent")
    temperature: float = Field(default=0.7, description="LLM temperature setting")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for LLM responses")

    # Memory and context
    memory_enabled: bool = Field(default=True, description="Whether agent has memory capabilities")
    context_window: int = Field(default=4000, description="Context window size")
    memory_data: Dict[str, Any] = Field(default_factory=dict, description="Agent memory data")

    # Quality control
    quality_threshold: float = Field(default=0.8, description="Quality threshold for agent outputs")
    validation_enabled: bool = Field(default=True, description="Whether to validate agent outputs")

    # Metrics and performance
    total_tasks_executed: int = Field(default=0, description="Total number of tasks executed")
    successful_tasks: int = Field(default=0, description="Number of successfully completed tasks")
    failed_tasks: int = Field(default=0, description="Number of failed tasks")
    average_execution_time: Optional[float] = Field(None, description="Average task execution time in seconds")
    average_quality_score: Optional[float] = Field(None, description="Average quality score")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Agent creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")

    # Relationships
    created_by: str = Field(..., description="ID of the user who created the agent")
    team_id: Optional[str] = Field(None, description="ID of the team this agent belongs to")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    version: str = Field(default="1.0.0", description="Agent version")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentExecution(BaseModel):
    """
    Model representing an agent execution instance.
    """
    execution_id: str = Field(..., description="Unique identifier for the execution")
    agent_id: str = Field(..., description="ID of the agent performing the execution")
    task_id: str = Field(..., description="ID of the task being executed")

    # Execution details
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Execution start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")
    execution_time_seconds: Optional[float] = Field(None, description="Execution time in seconds")

    # Input and output
    input_data: Dict[str, Any] = Field(..., description="Input data for the execution")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data from the execution")

    # Quality metrics
    quality_score: Optional[float] = Field(None, description="Quality score of the execution")
    validation_passed: Optional[bool] = Field(None, description="Whether execution passed validation")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    error_code: Optional[str] = Field(None, description="Error code if execution failed")

    # Resource usage
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentTeam(BaseModel):
    """
    Model representing a team of agents working together.
    """
    team_id: str = Field(..., description="Unique identifier for the team")
    name: str = Field(..., description="Name of the team")
    description: Optional[str] = Field(None, description="Description of the team")

    # Team composition
    agents: List[str] = Field(..., description="List of agent IDs in the team")
    leader_agent_id: Optional[str] = Field(None, description="ID of the team leader agent")

    # Team configuration
    collaboration_mode: str = Field(default="sequential", description="How agents collaborate")
    communication_enabled: bool = Field(default=True, description="Whether agents can communicate")
    shared_memory: bool = Field(default=False, description="Whether agents share memory")

    # Status
    status: str = Field(default="active", description="Team status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Team creation timestamp")
    created_by: str = Field(..., description="ID of the user who created the team")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
