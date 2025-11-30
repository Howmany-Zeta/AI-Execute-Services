# DOMAIN_COMMUNITY

## Overview

The DOMAIN_COMMUNITY module provides a comprehensive framework for agent community collaboration, governance, and resource sharing within the AIECS (AI Execution and Collaboration System). This module enables multiple AI agents to work together in structured communities with sophisticated governance models, decision-making processes, and collaborative workflows.

## Key Features

### 🤝 **Agent Community Management**
- Create and manage multi-agent communities
- Role-based access control and permissions
- Member lifecycle management with hooks
- Community capacity and resource limits

### 🏛️ **Governance & Decision Making**
- Multiple governance models (Democratic, Hierarchical, Consensus-based)
- Sophisticated voting and consensus algorithms
- Conflict resolution strategies
- Decision tracking and audit trails

### 💬 **Communication & Context Sharing**
- Real-time agent-to-agent communication
- Shared context management with conflict resolution
- Event-driven messaging system
- Message routing and filtering

### 🔧 **Resource Management**
- Shared resource allocation and management
- Resource type system (Data, Models, Tools, Knowledge)
- Access control and usage tracking
- Resource lifecycle management

### 🔄 **Collaborative Workflows**
- Multi-agent workflow orchestration
- Session-based collaboration
- Workflow state management
- Progress tracking and coordination

### 🔌 **Agent Integration**
- Flexible agent adapter system
- Support for various LLM providers
- Custom agent capability registration
- Standardized agent interfaces

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN_COMMUNITY                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Community       │  │ Decision        │  │ Resource     │ │
│  │ Manager         │  │ Engine          │  │ Manager      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Communication   │  │ Shared Context  │  │ Collaborative│ │
│  │ Hub             │  │ Manager         │  │ Workflow     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Agent Adapter   │  │ Community       │  │ Community    │ │
│  │ System          │  │ Integration     │  │ Builder      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. **CommunityManager**
Central orchestrator for community operations, member management, and lifecycle events.

### 2. **DecisionEngine**
Handles collective decision-making processes with various consensus algorithms and governance models.

### 3. **ResourceManager**
Manages shared resources within communities, including allocation, access control, and lifecycle.

### 4. **CommunicationHub**
Facilitates real-time communication between agents with message routing and event handling.

### 5. **SharedContextManager**
Manages shared context and knowledge across community members with conflict resolution.

### 6. **CollaborativeWorkflowEngine**
Orchestrates multi-agent workflows and collaboration sessions.

### 7. **AgentAdapter System**
Provides flexible integration with various agent types and LLM providers.

### 8. **CommunityBuilder**
Fluent API for creating and configuring agent communities.

## Quick Start

```python
from aiecs.domain import CommunityBuilder, GovernanceType, CommunityRole

# Create a new community
community = (CommunityBuilder()
    .with_name("AI Research Team")
    .with_governance(GovernanceType.DEMOCRATIC)
    .with_capacity(10)
    .build())

# Add members
await community.add_member("agent1", CommunityRole.ADMIN)
await community.add_member("agent2", CommunityRole.MEMBER)

# Start collaboration
session = await community.start_collaboration_session("research_project")
```

## Documentation Structure

- **[API_REFERENCE.md](./API_REFERENCE.md)** - Complete API documentation
- **[USAGE_GUIDE.md](./USAGE_GUIDE.md)** - Practical usage examples and tutorials
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System design and component relationships
- **[EXAMPLES.md](./EXAMPLES.md)** - Code examples and use cases
- **[ANALYTICS.md](./ANALYTICS.md)** - Community analytics and monitoring

## Version

Current Version: **1.0.0**

## Requirements

- Python 3.8+
- asyncio support
- Type hints support

## Installation

The DOMAIN_COMMUNITY module is part of the AIECS framework and is automatically available when importing from `aiecs.domain`.

```python
from aiecs.domain import CommunityManager, DecisionEngine, CommunicationHub
```

## Contributing

This module follows the AIECS architecture patterns and design principles. When contributing:

1. Follow the existing code structure and patterns
2. Add comprehensive type hints
3. Include proper error handling with custom exceptions
4. Write unit tests for new functionality
5. Update documentation for any API changes

## Important Notes

### Enum Value Differences

The actual implementation uses slightly different enum values than what might be expected:

**CommunityRole:**
- Actual values: `LEADER`, `COORDINATOR`, `SPECIALIST`, `CONTRIBUTOR`, `OBSERVER`
- (Not: `ADMIN`, `MODERATOR`, `MEMBER`)

**GovernanceType:**
- Actual values: `DEMOCRATIC`, `CONSENSUS`, `HIERARCHICAL`, `HYBRID`
- (Not: `AUTOCRATIC`)

**DecisionStatus:**
- Actual values: `PROPOSED`, `VOTING`, `APPROVED`, `REJECTED`, `IMPLEMENTED`
- (Not: `PENDING`, `EXPIRED`)

**ResourceType:**
- Actual values: `KNOWLEDGE`, `TOOL`, `EXPERIENCE`, `DATA`, `CAPABILITY`
- (Not: `MODEL`, `CONFIG`)

### Analytics Feature

The **CommunityAnalytics** class is now available in the public API. See [ANALYTICS.md](./ANALYTICS.md) for comprehensive documentation on community analytics and monitoring capabilities.

## License

Part of the AIECS framework - see main project license.
