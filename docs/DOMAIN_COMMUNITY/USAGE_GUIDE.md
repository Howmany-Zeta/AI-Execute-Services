# Usage Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Community Operations](#basic-community-operations)
- [Decision Making](#decision-making)
- [Resource Sharing](#resource-sharing)
- [Communication](#communication)
- [Collaborative Workflows](#collaborative-workflows)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

```python
from aiecs.domain import (
    CommunityBuilder, CommunityManager, DecisionEngine,
    CommunicationHub, ResourceManager, CollaborativeWorkflowEngine,
    GovernanceType, CommunityRole, ConsensusAlgorithm
)
```

### Basic Setup

```python
import asyncio
from aiecs.domain import CommunityIntegration

# Initialize the community integration
integration = CommunityIntegration()

# Create a community manager
community_manager = CommunityManager(integration)

# Initialize other components
decision_engine = DecisionEngine(community_manager)
communication_hub = CommunicationHub(community_manager)
resource_manager = ResourceManager(community_manager)
workflow_engine = CollaborativeWorkflowEngine(community_manager)
```

## Basic Community Operations

### Creating a Community

#### Using CommunityBuilder (Recommended)

```python
async def create_research_community():
    # Create a research community with democratic governance
    community = (CommunityBuilder(integration)
        .with_name("AI Research Team")
        .with_description("Collaborative AI research and development")
        .with_governance(GovernanceType.DEMOCRATIC)
        .with_capacity(15)
        .with_template("research_team", {
            "default_roles": ["researcher", "reviewer", "coordinator"],
            "auto_approve_members": False
        })
        .build())
    
    return community
```

#### Direct Creation

```python
async def create_community_directly():
    community = await community_manager.create_community(
        name="Development Team",
        description="Software development collaboration",
        governance_type=GovernanceType.HIERARCHICAL,
        creator_agent_id="admin_agent",
        capacity=10
    )
    return community
```

### Managing Members

```python
async def manage_community_members():
    community_id = "research_team_001"
    
    # Add members with different roles
    await community_manager.add_member(
        community_id, "agent_001", CommunityRole.ADMIN
    )
    await community_manager.add_member(
        community_id, "agent_002", CommunityRole.MEMBER
    )
    await community_manager.add_member(
        community_id, "agent_003", CommunityRole.OBSERVER
    )
    
    # Update member role
    await community_manager.update_member_role(
        community_id, "agent_002", CommunityRole.MODERATOR
    )
    
    # Remove a member
    await community_manager.remove_member(
        community_id, "agent_003", "No longer needed"
    )
```

### Member Lifecycle Hooks

```python
class CustomMemberHooks:
    async def on_member_join(self, community_id: str, member_id: str, member):
        print(f"Welcome {member_id} to community {community_id}!")
        # Send welcome message, initialize resources, etc.
    
    async def on_member_exit(self, community_id: str, member_id: str, member, reason=None):
        print(f"Member {member_id} left community {community_id}. Reason: {reason}")
        # Clean up resources, notify other members, etc.
    
    async def on_member_update(self, community_id: str, member_id: str, old_member, new_member):
        print(f"Member {member_id} updated in community {community_id}")
        # Handle role changes, permission updates, etc.

# Register hooks
hooks = CustomMemberHooks()
community_manager.register_lifecycle_hooks(hooks)
```

## Decision Making

### Proposing Decisions

```python
async def propose_feature_decision():
    community_id = "research_team_001"
    
    # Propose a new feature
    decision = await decision_engine.propose_decision(
        community_id=community_id,
        proposer_id="agent_001",
        title="Implement New ML Model",
        description="Should we implement a new transformer-based model for our research?",
        options=["Yes", "No", "Defer to next sprint"],
        algorithm=ConsensusAlgorithm.SUPERMAJORITY
    )
    
    print(f"Decision proposed: {decision.decision_id}")
    return decision
```

### Voting on Decisions

```python
async def vote_on_decisions():
    decision_id = "decision_001"
    
    # Cast votes
    await decision_engine.cast_vote(decision_id, "agent_001", "Yes", weight=1.0)
    await decision_engine.cast_vote(decision_id, "agent_002", "Yes", weight=1.0)
    await decision_engine.cast_vote(decision_id, "agent_003", "No", weight=1.0)
    
    # Evaluate the decision
    passed, details = await decision_engine.evaluate_decision(
        decision_id, "research_team_001", ConsensusAlgorithm.SUPERMAJORITY
    )
    
    print(f"Decision passed: {passed}")
    print(f"Vote details: {details}")
```

### Advanced Decision Making

```python
async def weighted_voting_example():
    # Create a decision with weighted voting
    decision = await decision_engine.propose_decision(
        community_id="research_team_001",
        proposer_id="agent_001",
        title="Budget Allocation",
        description="How should we allocate our research budget?",
        options=["More compute", "More data", "More personnel"],
        algorithm=ConsensusAlgorithm.WEIGHTED_VOTING
    )
    
    # Cast weighted votes (based on expertise/role)
    await decision_engine.cast_vote(decision.decision_id, "agent_001", "More compute", weight=2.0)  # Senior researcher
    await decision_engine.cast_vote(decision.decision_id, "agent_002", "More data", weight=1.5)     # Data specialist
    await decision_engine.cast_vote(decision.decision_id, "agent_003", "More personnel", weight=1.0) # Junior researcher
```

## Resource Sharing

### Creating and Sharing Resources

```python
async def share_research_data():
    community_id = "research_team_001"
    
    # Create a dataset resource
    dataset_resource = await resource_manager.create_resource(
        community_id=community_id,
        creator_id="agent_001",
        name="Research Dataset v2.1",
        resource_type=ResourceType.DATA,
        data={
            "dataset_path": "/data/research_v2.1.parquet",
            "size": "2.3GB",
            "samples": 50000,
            "features": 128
        },
        metadata={
            "description": "Updated research dataset with new features",
            "version": "2.1",
            "license": "MIT"
        }
    )
    
    # Share with specific members
    await resource_manager.share_resource(
        resource_id=dataset_resource.resource_id,
        from_agent_id="agent_001",
        to_agent_ids=["agent_002", "agent_003"],
        permissions={"read": True, "write": False}
    )
    
    return dataset_resource
```

### Model Sharing

```python
async def share_trained_model():
    # Create a model resource
    model_resource = await resource_manager.create_resource(
        community_id="research_team_001",
        creator_id="agent_002",
        name="BERT Fine-tuned Model",
        resource_type=ResourceType.MODEL,
        data={
            "model_path": "/models/bert_finetuned.pkl",
            "architecture": "BERT-base",
            "accuracy": 0.94,
            "training_data": "research_dataset_v2.1"
        },
        metadata={
            "framework": "transformers",
            "python_version": "3.9",
            "dependencies": ["torch", "transformers"]
        }
    )
    
    # Share with all community members
    community = await community_manager.get_community("research_team_001")
    all_members = [member.agent_id for member in community.members]
    
    await resource_manager.share_resource(
        resource_id=model_resource.resource_id,
        from_agent_id="agent_002",
        to_agent_ids=all_members,
        permissions={"read": True, "inference": True}
    )
```

## Communication

### Basic Messaging

```python
async def send_messages():
    # Send a direct message
    message = Message(
        sender_id="agent_001",
        recipient_ids=["agent_002"],
        message_type=MessageType.REQUEST,
        content="Can you review my latest research proposal?",
        metadata={"priority": "high", "deadline": "2024-01-15"}
    )
    
    await communication_hub.send_message(message)
    
    # Broadcast to community
    await communication_hub.broadcast_message(
        sender_id="agent_001",
        community_id="research_team_001",
        content="Weekly team meeting scheduled for tomorrow at 2 PM",
        message_type=MessageType.NOTIFICATION
    )
```

### Event Subscriptions

```python
async def setup_event_handlers():
    async def on_decision_proposed(event: Event):
        print(f"New decision proposed: {event.data['title']}")
        # Notify relevant agents, update UI, etc.
    
    async def on_resource_shared(event: Event):
        print(f"Resource shared: {event.data['resource_name']}")
        # Update resource lists, notify interested parties, etc.
    
    # Subscribe to events
    await communication_hub.subscribe_to_events(
        agent_id="agent_001",
        event_types=[EventType.DECISION_PROPOSED, EventType.RESOURCE_SHARED],
        callback=on_decision_proposed
    )
```

## Collaborative Workflows

### Creating Collaboration Sessions

```python
async def start_research_session():
    # Start a collaborative research session
    session = await workflow_engine.start_collaboration_session(
        community_id="research_team_001",
        session_name="Model Evaluation Session",
        participants=["agent_001", "agent_002", "agent_003"],
        workflow_config={
            "workflow_type": "evaluation",
            "steps": [
                "data_preparation",
                "model_training",
                "evaluation",
                "reporting"
            ],
            "timeout_minutes": 120
        }
    )
    
    return session
```

### Executing Workflow Steps

```python
async def execute_workflow():
    session_id = "session_001"
    
    # Execute workflow steps
    data_result = await workflow_engine.execute_workflow_step(
        session_id=session_id,
        step_name="data_preparation",
        executor_id="agent_001",
        input_data={"dataset": "research_dataset_v2.1"}
    )
    
    model_result = await workflow_engine.execute_workflow_step(
        session_id=session_id,
        step_name="model_training",
        executor_id="agent_002",
        input_data={"prepared_data": data_result}
    )
    
    evaluation_result = await workflow_engine.execute_workflow_step(
        session_id=session_id,
        step_name="evaluation",
        executor_id="agent_003",
        input_data={"trained_model": model_result}
    )
    
    return evaluation_result
```

## Advanced Features

### Custom Agent Adapters

```python
class CustomResearchAgent(AgentAdapter):
    def __init__(self, agent_id: str, specialization: str):
        self.agent_id = agent_id
        self.specialization = specialization
    
    async def process_message(self, message: Message) -> Any:
        # Custom message processing logic
        if message.message_type == MessageType.REQUEST:
            return await self.handle_research_request(message.content)
        return None
    
    async def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="data_analysis",
                description="Statistical data analysis",
                parameters={"methods": ["regression", "classification"]}
            ),
            AgentCapability(
                name="model_training",
                description="Machine learning model training",
                parameters={"frameworks": ["scikit-learn", "pytorch"]}
            )
        ]
    
    async def handle_research_request(self, content: Any) -> Any:
        # Implement research-specific logic
        pass

# Register the custom adapter
adapter = CustomResearchAgent("research_agent_001", "ML")
registry = AgentAdapterRegistry()
registry.register_adapter("research_agent_001", adapter)
```

### Shared Context Management

```python
async def manage_shared_context():
    # Create shared research context
    context = await shared_context_manager.create_shared_context(
        community_id="research_team_001",
        creator_id="agent_001",
        name="Research Progress",
        scope=ContextScope.COMMUNITY,
        initial_data={
            "current_phase": "data_collection",
            "completed_tasks": ["literature_review", "data_gathering"],
            "next_milestones": ["model_design", "experimentation"]
        }
    )
    
    # Update context with conflict resolution
    updated_context = await shared_context_manager.update_shared_context(
        context_id=context.context_id,
        updater_id="agent_002",
        data={
            "current_phase": "model_design",
            "completed_tasks": ["literature_review", "data_gathering", "data_preprocessing"],
            "next_milestones": ["experimentation", "evaluation"]
        },
        conflict_strategy=ContextConflictStrategy.MERGE
    )
```

## Best Practices

### 1. Community Design

```python
# Good: Clear governance and roles
community = (CommunityBuilder(integration)
    .with_name("Clear Purpose Community")
    .with_governance(GovernanceType.DEMOCRATIC)
    .with_capacity(10)
    .build())

# Bad: Unclear purpose and governance
community = (CommunityBuilder(integration)
    .with_name("General Community")
    .with_governance(GovernanceType.AUTOCRATIC)  # Too restrictive for collaboration
    .with_capacity(100)  # Too large for effective collaboration
    .build())
```

### 2. Error Handling

```python
async def safe_community_operation():
    try:
        await community_manager.add_member("community_001", "agent_001", CommunityRole.MEMBER)
    except CommunityNotFoundError:
        print("Community not found")
    except MembershipError as e:
        print(f"Membership error: {e}")
    except CommunityCapacityError:
        print("Community is at capacity")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

### 3. Resource Management

```python
async def efficient_resource_sharing():
    # Good: Share with specific permissions
    await resource_manager.share_resource(
        resource_id="resource_001",
        from_agent_id="creator",
        to_agent_ids=["agent_001", "agent_002"],
        permissions={"read": True, "write": False, "share": False}
    )
    
    # Bad: Overly permissive sharing
    await resource_manager.share_resource(
        resource_id="resource_001",
        from_agent_id="creator",
        to_agent_ids=["agent_001", "agent_002"],
        permissions={"read": True, "write": True, "share": True, "delete": True}  # Too permissive
    )
```

### 4. Decision Making

```python
async def effective_decision_making():
    # Good: Clear options and appropriate algorithm
    decision = await decision_engine.propose_decision(
        community_id="community_001",
        proposer_id="agent_001",
        title="Choose Research Direction",
        description="Which research direction should we pursue next?",
        options=["NLP", "Computer Vision", "Reinforcement Learning"],
        algorithm=ConsensusAlgorithm.SUPERMAJORITY  # Requires strong consensus
    )
    
    # Bad: Vague options and inappropriate algorithm
    decision = await decision_engine.propose_decision(
        community_id="community_001",
        proposer_id="agent_001",
        title="What should we do?",
        description="Something needs to be decided",
        options=["Yes", "No", "Maybe"],  # Too vague
        algorithm=ConsensusAlgorithm.UNANIMOUS  # Too strict for most decisions
    )
```

## Troubleshooting

### Common Issues

#### 1. Community Not Found

```python
# Problem: CommunityNotFoundError
try:
    community = await community_manager.get_community("nonexistent_community")
except CommunityNotFoundError:
    # Solution: Check if community exists first
    communities = await community_manager.list_communities()
    community_ids = [c.community_id for c in communities]
    if "nonexistent_community" not in community_ids:
        print("Community does not exist")
```

#### 2. Permission Denied

```python
# Problem: AccessDeniedError
try:
    resource = await resource_manager.get_resource("resource_001", "unauthorized_agent")
except AccessDeniedError:
    # Solution: Check permissions or share resource
    await resource_manager.share_resource(
        resource_id="resource_001",
        from_agent_id="owner",
        to_agent_ids=["unauthorized_agent"],
        permissions={"read": True}
    )
```

#### 3. Decision Evaluation Fails

```python
# Problem: QuorumNotMetError
try:
    passed, details = await decision_engine.evaluate_decision("decision_001", "community_001")
except QuorumNotMetError:
    # Solution: Wait for more votes or adjust quorum requirements
    decision = await decision_engine.get_decision("decision_001")
    print(f"Need {decision.required_votes} votes, have {len(decision.votes)}")
```

### Debugging Tips

1. **Enable Logging**: Set up proper logging to track community operations
2. **Check Permissions**: Verify agent permissions before operations
3. **Validate Input**: Ensure all required parameters are provided
4. **Monitor Events**: Subscribe to relevant events for debugging
5. **Use Timeouts**: Set appropriate timeouts for long-running operations

### Performance Optimization

1. **Batch Operations**: Group related operations together
2. **Async/Await**: Use proper async patterns
3. **Resource Cleanup**: Clean up unused resources and sessions
4. **Connection Pooling**: Reuse connections where possible
5. **Caching**: Cache frequently accessed data
