"""
Community Collaboration Models

Defines the data models for agent community collaboration,
including governance, resource sharing, and collective decision-making.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class CommunityRole(str, Enum):
    """Roles within the agent community."""

    LEADER = "leader"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    CONTRIBUTOR = "contributor"
    OBSERVER = "observer"


class GovernanceType(str, Enum):
    """Types of community governance."""

    DEMOCRATIC = "democratic"  # Voting-based decisions
    CONSENSUS = "consensus"  # Consensus-based decisions
    HIERARCHICAL = "hierarchical"  # Leader-based decisions
    HYBRID = "hybrid"  # Mixed governance


class DecisionStatus(str, Enum):
    """Status of community decisions."""

    PROPOSED = "proposed"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


class ResourceType(str, Enum):
    """Types of community resources."""

    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    EXPERIENCE = "experience"
    DATA = "data"
    CAPABILITY = "capability"


class CommunityMember(BaseModel):
    """Model representing a member of the agent community."""

    member_id: str = Field(..., description="Unique identifier for the member")
    agent_id: str = Field(..., description="Associated agent ID")
    agent_role: str = Field(..., description="Agent's functional role")
    community_role: CommunityRole = Field(..., description="Role within the community")

    # Participation metrics
    contribution_score: float = Field(default=0.0, description="Contribution score to the community")
    reputation: float = Field(default=0.0, description="Reputation within the community")
    participation_level: str = Field(default="active", description="Level of participation")

    # Capabilities and specializations
    specializations: List[str] = Field(default_factory=list, description="Areas of specialization")
    available_resources: List[str] = Field(default_factory=list, description="Resources this member can provide")

    # Status
    is_active: bool = Field(default=True, description="Whether the member is active")
    joined_at: datetime = Field(default_factory=datetime.utcnow, description="When the member joined")
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()


class CommunityResource(BaseModel):
    """Model representing a shared community resource."""

    resource_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique resource identifier",
    )
    name: str = Field(..., description="Name of the resource")
    resource_type: ResourceType = Field(..., description="Type of resource")
    description: Optional[str] = Field(None, description="Description of the resource")

    # Ownership and access
    owner_id: str = Field(..., description="ID of the member who owns/contributed this resource")
    access_level: str = Field(
        default="public",
        description="Access level (public, restricted, private)",
    )
    allowed_members: List[str] = Field(
        default_factory=list,
        description="Members allowed to access (if restricted)",
    )

    # Content
    content: Dict[str, Any] = Field(default_factory=dict, description="Resource content/data")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Usage metrics
    usage_count: int = Field(default=0, description="Number of times this resource has been used")
    rating: float = Field(default=0.0, description="Average rating from community members")

    # Status
    is_available: bool = Field(default=True, description="Whether the resource is available")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()


class CommunityDecision(BaseModel):
    """Model representing a community decision or proposal."""

    decision_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique decision identifier",
    )
    title: str = Field(..., description="Title of the decision/proposal")
    description: str = Field(..., description="Detailed description")

    # Proposal details
    proposer_id: str = Field(..., description="ID of the member who proposed this")
    decision_type: str = Field(..., description="Type of decision (policy, resource, task, etc.)")
    priority: str = Field(default="medium", description="Priority level")

    # Voting and consensus
    status: DecisionStatus = Field(default=DecisionStatus.PROPOSED, description="Current status")
    votes_for: List[str] = Field(default_factory=list, description="Member IDs who voted for")
    votes_against: List[str] = Field(default_factory=list, description="Member IDs who voted against")
    abstentions: List[str] = Field(default_factory=list, description="Member IDs who abstained")

    # Implementation
    implementation_plan: Optional[str] = Field(None, description="Plan for implementing the decision")
    assigned_members: List[str] = Field(default_factory=list, description="Members assigned to implement")
    deadline: Optional[datetime] = Field(None, description="Implementation deadline")

    # Status tracking
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    voting_ends_at: Optional[datetime] = Field(None, description="When voting ends")
    implemented_at: Optional[datetime] = Field(None, description="When decision was implemented")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()


class AgentCommunity(BaseModel):
    """Model representing an agent community."""

    community_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique community identifier",
    )
    name: str = Field(..., description="Name of the community")
    description: Optional[str] = Field(None, description="Description of the community")

    # Governance
    governance_type: GovernanceType = Field(default=GovernanceType.DEMOCRATIC, description="Type of governance")
    governance_rules: Dict[str, Any] = Field(default_factory=dict, description="Governance rules and policies")

    # Membership
    members: List[str] = Field(default_factory=list, description="List of member IDs")
    max_members: Optional[int] = Field(None, description="Maximum number of members")
    membership_criteria: Dict[str, Any] = Field(default_factory=dict, description="Criteria for membership")

    # Leadership
    leaders: List[str] = Field(default_factory=list, description="List of leader member IDs")
    coordinators: List[str] = Field(default_factory=list, description="List of coordinator member IDs")

    # Resources and capabilities
    shared_resources: List[str] = Field(default_factory=list, description="List of shared resource IDs")
    collective_capabilities: List[str] = Field(default_factory=list, description="Collective capabilities")
    knowledge_base: Dict[str, Any] = Field(default_factory=dict, description="Community knowledge base")

    # Activity and metrics
    activity_level: str = Field(default="active", description="Overall activity level")
    collaboration_score: float = Field(default=0.0, description="Overall collaboration effectiveness score")
    decision_count: int = Field(default=0, description="Number of decisions made")
    resource_count: int = Field(default=0, description="Number of shared resources")

    # Status
    is_active: bool = Field(default=True, description="Whether the community is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()


class CollaborationSession(BaseModel):
    """Model representing a collaborative session between community members."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier",
    )
    community_id: str = Field(..., description="Associated community ID")

    # Participants
    participants: List[str] = Field(..., description="List of participating member IDs")
    session_leader: Optional[str] = Field(None, description="Session leader member ID")

    # Session details
    purpose: str = Field(..., description="Purpose of the collaboration session")
    session_type: str = Field(
        ...,
        description="Type of session (brainstorm, decision, problem-solving, etc.)",
    )
    agenda: List[str] = Field(default_factory=list, description="Session agenda items")

    # Outcomes
    decisions_made: List[str] = Field(default_factory=list, description="Decision IDs made during session")
    resources_created: List[str] = Field(default_factory=list, description="Resource IDs created during session")
    action_items: List[Dict[str, Any]] = Field(default_factory=list, description="Action items from the session")

    # Status
    status: str = Field(default="active", description="Session status")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Session start time")
    ended_at: Optional[datetime] = Field(None, description="Session end time")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    model_config = ConfigDict()
