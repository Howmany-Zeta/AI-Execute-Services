# API Reference

## Table of Contents

- [Core Managers](#core-managers)
- [Communication & Context](#communication--context)
- [Agent Adapters](#agent-adapters)
- [Builder](#builder)
- [Models](#models)
- [Enums](#enums)
- [Exceptions](#exceptions)

## Core Managers

### CommunityManager

Central orchestrator for community operations, member management, and lifecycle events.

```python
class CommunityManager:
    def __init__(self, integration: CommunityIntegration)
```

#### Methods

##### `async add_member(community_id: str, agent_id: str, role: CommunityRole, metadata: Optional[Dict[str, Any]] = None) -> CommunityMember`

Add a new member to a community.

**Parameters:**
- `community_id` (str): ID of the community
- `agent_id` (str): ID of the agent to add
- `role` (CommunityRole): Role of the member
- `metadata` (Optional[Dict[str, Any]]): Additional member metadata

**Returns:** `CommunityMember` - The created member object

**Raises:**
- `CommunityNotFoundError`: If community doesn't exist
- `MembershipError`: If agent is already a member
- `CommunityCapacityError`: If community is at capacity

##### `async remove_member(community_id: str, agent_id: str, reason: Optional[str] = None) -> bool`

Remove a member from a community.

**Parameters:**
- `community_id` (str): ID of the community
- `agent_id` (str): ID of the agent to remove
- `reason` (Optional[str]): Reason for removal

**Returns:** `bool` - True if successful

##### `async update_member_role(community_id: str, agent_id: str, new_role: CommunityRole) -> CommunityMember`

Update a member's role in a community.

**Parameters:**
- `community_id` (str): ID of the community
- `agent_id` (str): ID of the agent
- `new_role` (CommunityRole): New role for the member

**Returns:** `CommunityMember` - Updated member object

##### `async get_community(community_id: str) -> AgentCommunity`

Get a community by ID.

**Parameters:**
- `community_id` (str): ID of the community

**Returns:** `AgentCommunity` - The community object

**Raises:**
- `CommunityNotFoundError`: If community doesn't exist

##### `async list_communities(filters: Optional[Dict[str, Any]] = None) -> List[AgentCommunity]`

List communities with optional filtering.

**Parameters:**
- `filters` (Optional[Dict[str, Any]]): Filter criteria

**Returns:** `List[AgentCommunity]` - List of matching communities

### DecisionEngine

Handles collective decision-making processes with various consensus algorithms.

```python
class DecisionEngine:
    def __init__(self, community_manager=None)
```

#### Methods

##### `async evaluate_decision(decision_id: str, community_id: str, algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY) -> Tuple[bool, Dict[str, Any]]`

Evaluate a community decision using the specified consensus algorithm.

**Parameters:**
- `decision_id` (str): ID of the decision to evaluate
- `community_id` (str): ID of the community
- `algorithm` (ConsensusAlgorithm): Consensus algorithm to use

**Returns:** `Tuple[bool, Dict[str, Any]]` - (decision_passed, evaluation_details)

##### `async propose_decision(community_id: str, proposer_id: str, title: str, description: str, options: List[str], algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY) -> CommunityDecision`

Propose a new decision to a community.

**Parameters:**
- `community_id` (str): ID of the community
- `proposer_id` (str): ID of the proposing agent
- `title` (str): Decision title
- `description` (str): Decision description
- `options` (List[str]): Available options for voting
- `algorithm` (ConsensusAlgorithm): Consensus algorithm to use

**Returns:** `CommunityDecision` - The created decision object

##### `async cast_vote(decision_id: str, voter_id: str, choice: str, weight: float = 1.0) -> bool`

Cast a vote on a decision.

**Parameters:**
- `decision_id` (str): ID of the decision
- `voter_id` (str): ID of the voting agent
- `choice` (str): The chosen option
- `weight` (float): Vote weight (default: 1.0)

**Returns:** `bool` - True if vote was cast successfully

### ResourceManager

Manages shared resources within communities.

```python
class ResourceManager:
    def __init__(self, community_manager=None)
```

#### Methods

##### `async create_resource(community_id: str, creator_id: str, name: str, resource_type: ResourceType, data: Any, metadata: Optional[Dict[str, Any]] = None) -> CommunityResource`

Create a new shared resource.

**Parameters:**
- `community_id` (str): ID of the community
- `creator_id` (str): ID of the creating agent
- `name` (str): Resource name
- `resource_type` (ResourceType): Type of resource
- `data` (Any): Resource data
- `metadata` (Optional[Dict[str, Any]]): Additional metadata

**Returns:** `CommunityResource` - The created resource object

##### `async share_resource(resource_id: str, from_agent_id: str, to_agent_ids: List[str], permissions: Optional[Dict[str, Any]] = None) -> bool`

Share a resource with specific agents.

**Parameters:**
- `resource_id` (str): ID of the resource
- `from_agent_id` (str): ID of the sharing agent
- `to_agent_ids` (List[str]): IDs of agents to share with
- `permissions` (Optional[Dict[str, Any]]): Access permissions

**Returns:** `bool` - True if successful

##### `async get_resource(resource_id: str, requester_id: str) -> CommunityResource`

Get a resource by ID.

**Parameters:**
- `resource_id` (str): ID of the resource
- `requester_id` (str): ID of the requesting agent

**Returns:** `CommunityResource` - The resource object

**Raises:**
- `ResourceNotFoundError`: If resource doesn't exist
- `AccessDeniedError`: If access is denied

### CollaborativeWorkflowEngine

Orchestrates multi-agent workflows and collaboration sessions.

```python
class CollaborativeWorkflowEngine:
    def __init__(self, community_manager=None)
```

### CommunityAnalytics

Provides comprehensive analytics and monitoring for community health and effectiveness.

```python
class CommunityAnalytics:
    def __init__(self, community_manager=None)
```

#### Key Methods

##### `get_decision_analytics(community_id: str, time_range_days: int = 30) -> Dict[str, Any]`

Get comprehensive decision analytics for a community.

**Parameters:**
- `community_id` (str): ID of the community
- `time_range_days` (int): Time range for analytics in days (default: 30)

**Returns:** Dictionary containing decision metrics, approval rates, and participation data

##### `get_participation_metrics(community_id: str, time_range_days: int = 30) -> Dict[str, Any]`

Get member participation metrics for a community.

**Parameters:**
- `community_id` (str): ID of the community
- `time_range_days` (int): Time range for metrics in days (default: 30)

**Returns:** Dictionary containing active members, participation rates, and engagement scores

##### `get_community_health_metrics(community_id: str) -> Dict[str, Any]`

Get overall community health metrics.

**Parameters:**
- `community_id` (str): ID of the community

**Returns:** Dictionary containing health score, vitality indicators, and recommendations

**For complete analytics documentation, see [ANALYTICS.md](./ANALYTICS.md)**

#### CollaborativeWorkflowEngine Methods

##### `async start_collaboration_session(community_id: str, session_name: str, participants: List[str], workflow_config: Optional[Dict[str, Any]] = None) -> CollaborationSession`

Start a new collaboration session.

**Parameters:**
- `community_id` (str): ID of the community
- `session_name` (str): Name of the session
- `participants` (List[str]): List of participant agent IDs
- `workflow_config` (Optional[Dict[str, Any]]): Workflow configuration

**Returns:** `CollaborationSession` - The created session object

##### `async execute_workflow_step(session_id: str, step_name: str, executor_id: str, input_data: Any) -> Any`

Execute a workflow step.

**Parameters:**
- `session_id` (str): ID of the collaboration session
- `step_name` (str): Name of the workflow step
- `executor_id` (str): ID of the executing agent
- `input_data` (Any): Input data for the step

**Returns:** `Any` - Step execution result

## Communication & Context

### CommunicationHub

Facilitates real-time communication between agents.

```python
class CommunicationHub:
    def __init__(self, community_manager=None)
```

#### Methods

##### `async send_message(message: Message) -> bool`

Send a message to specified recipients.

**Parameters:**
- `message` (Message): The message to send

**Returns:** `bool` - True if sent successfully

##### `async broadcast_message(sender_id: str, community_id: str, content: Any, message_type: MessageType = MessageType.BROADCAST) -> bool`

Broadcast a message to all community members.

**Parameters:**
- `sender_id` (str): ID of the sending agent
- `community_id` (str): ID of the community
- `content` (Any): Message content
- `message_type` (MessageType): Type of message

**Returns:** `bool` - True if broadcast successfully

##### `async subscribe_to_events(agent_id: str, event_types: List[EventType], callback: Callable[[Event], None]) -> str`

Subscribe to specific event types.

**Parameters:**
- `agent_id` (str): ID of the subscribing agent
- `event_types` (List[EventType]): Types of events to subscribe to
- `callback` (Callable[[Event], None]): Callback function for events

**Returns:** `str` - Subscription ID

### SharedContextManager

Manages shared context and knowledge across community members.

```python
class SharedContextManager:
    def __init__(self, community_manager=None)
```

#### Methods

##### `async create_shared_context(community_id: str, creator_id: str, name: str, scope: ContextScope, initial_data: Any) -> SharedContext`

Create a new shared context.

**Parameters:**
- `community_id` (str): ID of the community
- `creator_id` (str): ID of the creating agent
- `name` (str): Context name
- `scope` (ContextScope): Context scope
- `initial_data` (Any): Initial context data

**Returns:** `SharedContext` - The created context object

##### `async update_shared_context(context_id: str, updater_id: str, data: Any, conflict_strategy: ContextConflictStrategy = ContextConflictStrategy.LAST_WRITER_WINS) -> SharedContext`

Update a shared context.

**Parameters:**
- `context_id` (str): ID of the context
- `updater_id` (str): ID of the updating agent
- `data` (Any): New context data
- `conflict_strategy` (ContextConflictStrategy): Strategy for resolving conflicts

**Returns:** `SharedContext` - Updated context object

## Agent Adapters

### AgentAdapter

Base class for agent adapters.

```python
class AgentAdapter(ABC):
    @abstractmethod
    async def process_message(self, message: Message) -> Any
    @abstractmethod
    async def get_capabilities(self) -> List[AgentCapability]
```

### StandardLLMAdapter

Standard adapter for LLM-based agents.

```python
class StandardLLMAdapter(AgentAdapter):
    def __init__(self, agent_id: str, llm_provider: str, model_name: str, api_key: str)
```

### AgentAdapterRegistry

Registry for managing agent adapters.

```python
class AgentAdapterRegistry:
    def register_adapter(self, agent_id: str, adapter: AgentAdapter) -> None
    def get_adapter(self, agent_id: str) -> Optional[AgentAdapter]
    def list_adapters(self) -> Dict[str, AgentAdapter]
```

## Builder

### CommunityBuilder

Fluent interface for creating communities.

```python
class CommunityBuilder:
    def with_name(self, name: str) -> 'CommunityBuilder'
    def with_description(self, description: str) -> 'CommunityBuilder'
    def with_governance(self, governance_type: GovernanceType) -> 'CommunityBuilder'
    def with_capacity(self, capacity: int) -> 'CommunityBuilder'
    def with_template(self, template: str, config: Optional[Dict[str, Any]] = None) -> 'CommunityBuilder'
    def build(self) -> AgentCommunity
```

#### Usage Example

```python
community = (CommunityBuilder(integration)
    .with_name("AI Research Team")
    .with_description("Collaborative AI research community")
    .with_governance(GovernanceType.DEMOCRATIC)
    .with_capacity(10)
    .build())
```

## Models

### AgentCommunity

Represents an agent community.

```python
@dataclass
class AgentCommunity:
    community_id: str
    name: str
    description: Optional[str]
    governance_type: GovernanceType
    created_at: datetime
    created_by: str
    capacity: int
    metadata: Dict[str, Any]
```

### CommunityMember

Represents a community member.

```python
@dataclass
class CommunityMember:
    member_id: str
    agent_id: str
    community_id: str
    role: CommunityRole
    joined_at: datetime
    metadata: Dict[str, Any]
```

### CommunityDecision

Represents a community decision.

```python
@dataclass
class CommunityDecision:
    decision_id: str
    community_id: str
    proposer_id: str
    title: str
    description: str
    options: List[str]
    status: DecisionStatus
    algorithm: ConsensusAlgorithm
    created_at: datetime
    expires_at: Optional[datetime]
    votes: Dict[str, Dict[str, Any]]
    result: Optional[Dict[str, Any]]
```

### CommunityResource

Represents a shared community resource.

```python
@dataclass
class CommunityResource:
    resource_id: str
    community_id: str
    creator_id: str
    name: str
    resource_type: ResourceType
    data: Any
    created_at: datetime
    metadata: Dict[str, Any]
    access_control: Dict[str, Any]
```

### CollaborationSession

Represents a collaboration session.

```python
@dataclass
class CollaborationSession:
    session_id: str
    community_id: str
    name: str
    participants: List[str]
    workflow_config: Dict[str, Any]
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
```

## Enums

### CommunityRole

```python
class CommunityRole(str, Enum):
    LEADER = "leader"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    CONTRIBUTOR = "contributor"
    OBSERVER = "observer"
```

### GovernanceType

```python
class GovernanceType(str, Enum):
    DEMOCRATIC = "democratic"  # Voting-based decisions
    CONSENSUS = "consensus"    # Consensus-based decisions
    HIERARCHICAL = "hierarchical"  # Leader-based decisions
    HYBRID = "hybrid"          # Mixed governance
```

### DecisionStatus

```python
class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
```

### ResourceType

```python
class ResourceType(str, Enum):
    KNOWLEDGE = "knowledge"
    TOOL = "tool"
    EXPERIENCE = "experience"
    DATA = "data"
    CAPABILITY = "capability"
```

### ConsensusAlgorithm

```python
class ConsensusAlgorithm(str, Enum):
    SIMPLE_MAJORITY = "simple_majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED_VOTING = "weighted_voting"
    DELEGATED_PROOF = "delegated_proof"
```

### MessageType

```python
class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    SHARE = "share"
    BROADCAST = "broadcast"
```

### EventType

```python
class EventType(str, Enum):
    COMMUNITY_CREATED = "community_created"
    MEMBER_JOINED = "member_joined"
    DECISION_PROPOSED = "decision_proposed"
    RESOURCE_SHARED = "resource_shared"
    SESSION_STARTED = "session_started"
    # ... and more
```

## Exceptions

### CommunityException

Base exception for all community-related errors.

```python
class CommunityException(Exception):
    def __init__(self, message: str, error_code: Optional[str] = None)
```

### Specific Exceptions

- `CommunityNotFoundError`: Community doesn't exist
- `MemberNotFoundError`: Member doesn't exist
- `ResourceNotFoundError`: Resource doesn't exist
- `DecisionNotFoundError`: Decision doesn't exist
- `AccessDeniedError`: Access denied
- `MembershipError`: Membership-related error
- `VotingError`: Voting-related error
- `GovernanceError`: Governance-related error
- `CollaborationError`: Collaboration-related error
- `CommunityInitializationError`: Community initialization failed
- `CommunityValidationError`: Community validation failed
- `QuorumNotMetError`: Quorum not met for decision
- `ConflictResolutionError`: Conflict resolution failed
- `CommunityCapacityError`: Community at capacity
- `AgentAdapterError`: Agent adapter error
- `CommunicationError`: Communication error
- `ContextError`: Context-related error

## Type Hints

All classes and methods include comprehensive type hints for better IDE support and code clarity.

## Async/Await Support

All operations are asynchronous and use Python's `async`/`await` syntax for non-blocking execution.
