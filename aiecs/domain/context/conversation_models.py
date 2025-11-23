"""
Conversation Models for ContextEngine

This module defines the data models used for agent communication and conversation isolation
within the ContextEngine. These models are specific to the context management domain.
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ConversationParticipant:
    """Represents a participant in a conversation."""

    participant_id: str
    participant_type: str  # 'user', 'master_controller', 'agent'
    # For agents: 'writer', 'researcher', etc.
    participant_role: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate participant data after initialization."""
        if not self.participant_id:
            raise ValueError("participant_id cannot be empty")
        if not self.participant_type:
            raise ValueError("participant_type cannot be empty")

        # Validate participant types
        valid_types = {"user", "master_controller", "agent"}
        if self.participant_type not in valid_types:
            raise ValueError(f"participant_type must be one of {valid_types}")

        # For agents, role should be specified
        if self.participant_type == "agent" and not self.participant_role:
            raise ValueError("participant_role is required for agent participants")


@dataclass
class ConversationSession:
    """Represents an isolated conversation session between participants."""

    session_id: str
    participants: List[ConversationParticipant]
    session_type: str  # 'user_to_mc', 'mc_to_agent', 'agent_to_agent', 'user_to_agent'
    created_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate session data after initialization."""
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.participants:
            raise ValueError("participants list cannot be empty")

        # Validate session types
        valid_session_types = {
            "user_to_mc",
            "mc_to_agent",
            "agent_to_agent",
            "user_to_agent",
        }
        if self.session_type not in valid_session_types:
            raise ValueError(f"session_type must be one of {valid_session_types}")

        # Validate participant count and types based on session type
        self._validate_participants_for_session_type()

    def _validate_participants_for_session_type(self):
        """Validate that participants match the session type."""
        participant_types = [p.participant_type for p in self.participants]

        if self.session_type == "user_to_mc":
            expected_types = {"user", "master_controller"}
            if not expected_types.issubset(set(participant_types)):
                raise ValueError("user_to_mc session requires user and master_controller participants")

        elif self.session_type == "mc_to_agent":
            expected_types = {"master_controller", "agent"}
            if not expected_types.issubset(set(participant_types)):
                raise ValueError("mc_to_agent session requires master_controller and agent participants")

        elif self.session_type == "agent_to_agent":
            agent_count = sum(1 for p in self.participants if p.participant_type == "agent")
            if agent_count < 2:
                raise ValueError("agent_to_agent session requires at least 2 agent participants")

        elif self.session_type == "user_to_agent":
            expected_types = {"user", "agent"}
            if not expected_types.issubset(set(participant_types)):
                raise ValueError("user_to_agent session requires user and agent participants")

    def generate_session_key(self) -> str:
        """Generate a unique session key for conversation isolation."""
        if self.session_type == "user_to_mc":
            return self.session_id
        elif self.session_type == "mc_to_agent":
            agent_role = next(
                (p.participant_role for p in self.participants if p.participant_type == "agent"),
                "unknown",
            )
            return f"{self.session_id}_mc_to_{agent_role}"
        elif self.session_type == "agent_to_agent":
            agent_roles = [p.participant_role for p in self.participants if p.participant_type == "agent"]
            if len(agent_roles) >= 2:
                return f"{self.session_id}_{agent_roles[0]}_to_{agent_roles[1]}"
            return f"{self.session_id}_agent_to_agent"
        elif self.session_type == "user_to_agent":
            agent_role = next(
                (p.participant_role for p in self.participants if p.participant_type == "agent"),
                "unknown",
            )
            return f"{self.session_id}_user_to_{agent_role}"
        else:
            return self.session_id

    def get_participant_by_type_and_role(self, participant_type: str, participant_role: Optional[str] = None) -> Optional[ConversationParticipant]:
        """Get a participant by type and optionally by role."""
        for participant in self.participants:
            if participant.participant_type == participant_type:
                if participant_role is None or participant.participant_role == participant_role:
                    return participant
        return None

    def update_activity(self):
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "participants": [
                {
                    "participant_id": p.participant_id,
                    "participant_type": p.participant_type,
                    "participant_role": p.participant_role,
                    "metadata": p.metadata,
                }
                for p in self.participants
            ],
            "session_type": self.session_type,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Create from dictionary."""
        participants = [
            ConversationParticipant(
                participant_id=p["participant_id"],
                participant_type=p["participant_type"],
                participant_role=p.get("participant_role"),
                metadata=p.get("metadata", {}),
            )
            for p in data["participants"]
        ]

        return cls(
            session_id=data["session_id"],
            participants=participants,
            session_type=data["session_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentCommunicationMessage:
    """Message for agent-to-agent or controller-to-agent communication."""

    message_id: str
    session_key: str
    sender_id: str
    sender_type: str  # 'master_controller', 'agent', 'user'
    sender_role: Optional[str]  # For agents
    recipient_id: str
    recipient_type: str  # 'agent', 'master_controller', 'user'
    recipient_role: Optional[str]  # For agents
    content: str
    # 'task_assignment', 'result_report', 'collaboration_request', 'feedback', 'communication'
    message_type: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message data after initialization."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.session_key:
            raise ValueError("session_key cannot be empty")
        if not self.sender_id:
            raise ValueError("sender_id cannot be empty")
        if not self.recipient_id:
            raise ValueError("recipient_id cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")

        # Validate message types
        valid_message_types = {
            "task_assignment",
            "result_report",
            "collaboration_request",
            "feedback",
            "communication",
            "status_update",
            "error_report",
            "task_completion",
            "progress_update",
            "clarification_request",
        }
        if self.message_type not in valid_message_types:
            raise ValueError(f"message_type must be one of {valid_message_types}")

    def to_conversation_message_dict(self) -> Dict[str, Any]:
        """Convert to format compatible with ContextEngine conversation messages."""
        role = f"{self.sender_type}_{self.sender_role}" if self.sender_role else self.sender_type
        return {
            "role": role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": {
                **self.metadata,
                "message_id": self.message_id,
                "sender_id": self.sender_id,
                "sender_type": self.sender_type,
                "sender_role": self.sender_role,
                "recipient_id": self.recipient_id,
                "recipient_type": self.recipient_type,
                "recipient_role": self.recipient_role,
                "message_type": self.message_type,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "message_id": self.message_id,
            "session_key": self.session_key,
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "sender_role": self.sender_role,
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "recipient_role": self.recipient_role,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCommunicationMessage":
        """Create from dictionary."""
        return cls(
            message_id=data["message_id"],
            session_key=data["session_key"],
            sender_id=data["sender_id"],
            sender_type=data["sender_type"],
            sender_role=data.get("sender_role"),
            recipient_id=data["recipient_id"],
            recipient_type=data["recipient_type"],
            recipient_role=data.get("recipient_role"),
            content=data["content"],
            message_type=data["message_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


# Conversation isolation utility functions


def create_session_key(
    session_id: str,
    session_type: str,
    participants: List[ConversationParticipant],
) -> str:
    """
    Utility function to create session keys for conversation isolation.

    Args:
        session_id: Base session ID
        session_type: Type of conversation
        participants: List of conversation participants

    Returns:
        Generated session key
    """
    if session_type == "user_to_mc":
        return session_id
    elif session_type == "mc_to_agent":
        agent_role = next(
            (p.participant_role for p in participants if p.participant_type == "agent"),
            "unknown",
        )
        return f"{session_id}_mc_to_{agent_role}"
    elif session_type == "agent_to_agent":
        agent_roles = [p.participant_role for p in participants if p.participant_type == "agent"]
        if len(agent_roles) >= 2:
            return f"{session_id}_{agent_roles[0]}_to_{agent_roles[1]}"
        return f"{session_id}_agent_to_agent"
    elif session_type == "user_to_agent":
        agent_role = next(
            (p.participant_role for p in participants if p.participant_type == "agent"),
            "unknown",
        )
        return f"{session_id}_user_to_{agent_role}"
    else:
        return session_id


def validate_conversation_isolation_pattern(session_key: str, expected_pattern: str) -> bool:
    """
    Validate that a session key follows the expected conversation isolation pattern.

    Args:
        session_key: The session key to validate
        expected_pattern: Expected pattern ('user_to_mc', 'mc_to_agent', etc.)

    Returns:
        True if the pattern matches, False otherwise
    """
    if expected_pattern == "user_to_mc":
        # Should be just the base session_id
        return "_" not in session_key or not any(x in session_key for x in ["_mc_to_", "_to_", "_user_to_"])
    elif expected_pattern == "mc_to_agent":
        return "_mc_to_" in session_key
    elif expected_pattern == "agent_to_agent":
        return "_to_" in session_key and "_mc_to_" not in session_key and "_user_to_" not in session_key
    elif expected_pattern == "user_to_agent":
        return "_user_to_" in session_key
    else:
        return False
