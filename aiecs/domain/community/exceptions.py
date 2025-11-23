"""
Community Exceptions

Defines community-specific exception classes with clear error messages
and recovery suggestions.
"""

from typing import Optional


class CommunityException(Exception):
    """Base exception for community-related errors."""

    def __init__(self, message: str, recovery_suggestion: Optional[str] = None):
        """
        Initialize community exception.

        Args:
            message: Error message
            recovery_suggestion: Optional suggestion for recovery
        """
        self.message = message
        self.recovery_suggestion = recovery_suggestion
        super().__init__(self.message)

    def __str__(self):
        """String representation with recovery suggestion."""
        if self.recovery_suggestion:
            return f"{self.message}\nSuggestion: {self.recovery_suggestion}"
        return self.message


class CommunityNotFoundError(CommunityException):
    """Raised when a community is not found."""

    def __init__(self, community_id: str):
        super().__init__(
            f"Community not found: {community_id}",
            "Verify the community ID is correct and the community exists.",
        )
        self.community_id = community_id


class MemberNotFoundError(CommunityException):
    """Raised when a member is not found."""

    def __init__(self, member_id: str):
        super().__init__(
            f"Member not found: {member_id}",
            "Verify the member ID is correct and the member exists in the community.",
        )
        self.member_id = member_id


class ResourceNotFoundError(CommunityException):
    """Raised when a resource is not found."""

    def __init__(self, resource_id: str):
        super().__init__(
            f"Resource not found: {resource_id}",
            "Verify the resource ID is correct and the resource exists.",
        )
        self.resource_id = resource_id


class DecisionNotFoundError(CommunityException):
    """Raised when a decision is not found."""

    def __init__(self, decision_id: str):
        super().__init__(
            f"Decision not found: {decision_id}",
            "Verify the decision ID is correct and the decision exists.",
        )
        self.decision_id = decision_id


class AccessDeniedError(CommunityException):
    """Raised when access to a community resource is denied."""

    def __init__(self, agent_id: str, resource_type: str, resource_id: str):
        super().__init__(
            f"Access denied for agent {agent_id} to {resource_type} {resource_id}",
            "Request access from the resource owner or community administrator.",
        )
        self.agent_id = agent_id
        self.resource_type = resource_type
        self.resource_id = resource_id


class MembershipError(CommunityException):
    """Raised when there's an issue with community membership."""

    def __init__(self, message: str, agent_id: Optional[str] = None):
        super().__init__(message, "Check membership status and community requirements.")
        self.agent_id = agent_id


class VotingError(CommunityException):
    """Raised when there's an issue with voting."""

    def __init__(self, message: str, decision_id: Optional[str] = None):
        super().__init__(
            message,
            "Verify voting is open and you are eligible to vote on this decision.",
        )
        self.decision_id = decision_id


class GovernanceError(CommunityException):
    """Raised when there's an issue with community governance."""

    def __init__(self, message: str, community_id: Optional[str] = None):
        super().__init__(message, "Review community governance rules and requirements.")
        self.community_id = community_id


class CollaborationError(CommunityException):
    """Raised when there's an issue with collaboration."""

    def __init__(self, message: str, session_id: Optional[str] = None):
        super().__init__(message, "Check session status and participant availability.")
        self.session_id = session_id


class CommunityInitializationError(CommunityException):
    """Raised when community initialization fails."""

    def __init__(self, component: str, reason: str):
        super().__init__(
            f"Failed to initialize {component}: {reason}",
            "Check configuration and dependencies are properly set up.",
        )
        self.component = component
        self.reason = reason


class CommunityValidationError(CommunityException):
    """Raised when community validation fails."""

    def __init__(self, field_or_message: str, reason: Optional[str] = None):
        # Initialize attributes first
        self.field: Optional[str]
        self.reason: Optional[str]

        if reason:
            # Two-argument form: field and reason
            message = f"Validation error for {field_or_message}: {reason}"
            self.field = field_or_message
            self.reason = reason
        else:
            # One-argument form: just message
            message = field_or_message
            self.field = None
            self.reason = None

        super().__init__(message, "Review the field value and ensure it meets requirements.")


class QuorumNotMetError(CommunityException):
    """Raised when quorum is not met for a decision."""

    def __init__(self, required: int, actual: int, decision_id: Optional[str] = None):
        super().__init__(
            f"Quorum not met: {actual} votes cast, {required} required",
            "Encourage more members to participate in voting.",
        )
        self.required = required
        self.actual = actual
        self.decision_id = decision_id


class ConflictResolutionError(CommunityException):
    """Raised when conflict resolution fails."""

    def __init__(self, decision_id: str, strategy: str):
        super().__init__(
            f"Conflict resolution failed for decision {decision_id} using {strategy}",
            "Try a different conflict resolution strategy or escalate the decision.",
        )
        self.decision_id = decision_id
        self.strategy = strategy


class CommunityCapacityError(CommunityException):
    """Raised when community reaches capacity."""

    def __init__(self, community_id: str, current: int, maximum: int):
        super().__init__(
            f"Community {community_id} is at capacity: {current}/{maximum} members",
            "Create a new community or increase the member limit.",
        )
        self.community_id = community_id
        self.current = current
        self.maximum = maximum


class AgentAdapterError(CommunityException):
    """Raised when there's an issue with agent adapter."""

    def __init__(self, agent_id: str, reason: str):
        super().__init__(
            f"Agent adapter error for {agent_id}: {reason}",
            "Check agent adapter configuration and connectivity.",
        )
        self.agent_id = agent_id
        self.reason = reason


class CommunicationError(CommunityException):
    """Raised when there's an issue with agent communication."""

    def __init__(self, sender_id: str, recipient_id: str, reason: str):
        super().__init__(
            f"Communication error from {sender_id} to {recipient_id}: {reason}",
            "Verify both agents are registered and active in the communication hub.",
        )
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.reason = reason


class ContextError(CommunityException):
    """Raised when there's an issue with shared context."""

    def __init__(self, context_id: str, reason: str):
        super().__init__(
            f"Context error for {context_id}: {reason}",
            "Check context access permissions and version compatibility.",
        )
        self.context_id = context_id
        self.reason = reason
