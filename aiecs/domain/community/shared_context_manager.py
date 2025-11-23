"""
Shared Context Manager

Manages shared memory and context for agents in a community,
with support for versioning, conflict resolution, and real-time streaming.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from enum import Enum
from collections import defaultdict
import uuid
import copy

logger = logging.getLogger(__name__)


class ContextScope(str, Enum):
    """Scope levels for shared context."""

    COMMUNITY = "community"
    SESSION = "session"
    TASK = "task"
    AGENT = "agent"


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving context conflicts."""

    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    TIMESTAMP_BASED = "timestamp_based"


class ContextVersion:
    """Represents a version of context data."""

    def __init__(
        self,
        context_id: str,
        data: Dict[str, Any],
        version_number: int,
        author_id: str,
        parent_version: Optional[int] = None,
    ):
        """
        Initialize a context version.

        Args:
            context_id: ID of the context
            data: Context data
            version_number: Version number
            author_id: ID of the author who created this version
            parent_version: Optional parent version number
        """
        self.context_id = context_id
        self.data = copy.deepcopy(data)
        self.version_number = version_number
        self.author_id = author_id
        self.parent_version = parent_version
        self.timestamp = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}


class SharedContext:
    """Represents a shared context in the community."""

    def __init__(
        self,
        context_id: str,
        scope: ContextScope,
        owner_id: str,
        initial_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a shared context.

        Args:
            context_id: Unique context identifier
            scope: Scope level of the context
            owner_id: ID of the context owner
            initial_data: Optional initial data
        """
        self.context_id = context_id
        self.scope = scope
        self.owner_id = owner_id
        self.current_version = 0
        self.versions: List[ContextVersion] = []
        self.data = initial_data or {}
        self.access_control: Set[str] = {owner_id}  # IDs with access
        self.subscribers: Set[str] = set()  # IDs subscribed to updates
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}

        # Create initial version
        if initial_data:
            self._create_version(initial_data, owner_id)

    def _create_version(self, data: Dict[str, Any], author_id: str) -> ContextVersion:
        """Create a new version of the context."""
        version = ContextVersion(
            self.context_id,
            data,
            self.current_version + 1,
            author_id,
            self.current_version if self.current_version > 0 else None,
        )
        self.versions.append(version)
        self.current_version = version.version_number
        self.data = copy.deepcopy(data)
        self.updated_at = datetime.utcnow()
        return version


class SharedContextManager:
    """
    Manager for shared contexts in agent communities.
    Provides versioning, conflict resolution, and streaming capabilities.
    """

    def __init__(
        self,
        default_conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    ):
        """
        Initialize the shared context manager.

        Args:
            default_conflict_strategy: Default strategy for conflict resolution
        """
        self.contexts: Dict[str, SharedContext] = {}
        self.default_conflict_strategy = default_conflict_strategy

        # Scope-based indexes
        self.community_contexts: Dict[str, Set[str]] = defaultdict(set)
        self.session_contexts: Dict[str, Set[str]] = defaultdict(set)
        self.task_contexts: Dict[str, Set[str]] = defaultdict(set)
        self.agent_contexts: Dict[str, Set[str]] = defaultdict(set)

        # Update callbacks for streaming
        self.update_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        logger.info("Shared context manager initialized")

    async def create_context(
        self,
        scope: ContextScope,
        owner_id: str,
        scope_id: str,
        initial_data: Optional[Dict[str, Any]] = None,
        access_control: Optional[Set[str]] = None,
    ) -> str:
        """
        Create a new shared context.

        Args:
            scope: Scope level of the context
            owner_id: ID of the context owner
            scope_id: ID of the scope (community_id, session_id, task_id, or agent_id)
            initial_data: Optional initial data
            access_control: Optional set of agent IDs with access

        Returns:
            Context ID
        """
        context_id = str(uuid.uuid4())
        context = SharedContext(context_id, scope, owner_id, initial_data)

        if access_control:
            context.access_control = access_control

        self.contexts[context_id] = context

        # Add to scope index
        if scope == ContextScope.COMMUNITY:
            self.community_contexts[scope_id].add(context_id)
        elif scope == ContextScope.SESSION:
            self.session_contexts[scope_id].add(context_id)
        elif scope == ContextScope.TASK:
            self.task_contexts[scope_id].add(context_id)
        elif scope == ContextScope.AGENT:
            self.agent_contexts[scope_id].add(context_id)

        logger.info(f"Created {scope.value} context {context_id}")
        return context_id

    async def get_context(self, context_id: str, requester_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get context data.

        Args:
            context_id: ID of the context
            requester_id: ID of the requester
            version: Optional specific version to retrieve

        Returns:
            Context data or None if not found/unauthorized
        """
        context = self.contexts.get(context_id)
        if not context:
            return None

        # Check access control
        if requester_id not in context.access_control:
            logger.warning(f"Access denied for {requester_id} to context {context_id}")
            return None

        # Return specific version or current
        if version is not None:
            for v in context.versions:
                if v.version_number == version:
                    return copy.deepcopy(v.data)
            return None

        return copy.deepcopy(context.data)

    async def update_context(
        self,
        context_id: str,
        updater_id: str,
        updates: Dict[str, Any],
        conflict_strategy: Optional[ConflictResolutionStrategy] = None,
        create_version: bool = True,
    ) -> bool:
        """
        Update context data with conflict resolution.

        Args:
            context_id: ID of the context
            updater_id: ID of the updater
            updates: Data updates
            conflict_strategy: Optional conflict resolution strategy
            create_version: Whether to create a new version

        Returns:
            True if update was successful
        """
        context = self.contexts.get(context_id)
        if not context:
            logger.error(f"Context {context_id} not found")
            return False

        # Check access control
        if updater_id not in context.access_control:
            logger.warning(f"Access denied for {updater_id} to update context {context_id}")
            return False

        # Apply updates with conflict resolution
        strategy = conflict_strategy or self.default_conflict_strategy
        merged_data = await self._resolve_conflicts(context.data, updates, strategy, context, updater_id)

        # Create new version if requested
        if create_version:
            context._create_version(merged_data, updater_id)
        else:
            context.data = merged_data
            context.updated_at = datetime.utcnow()

        # Notify subscribers via streaming
        await self._notify_subscribers(context_id, merged_data, updater_id)

        logger.debug(f"Updated context {context_id} by {updater_id}")
        return True

    async def _resolve_conflicts(
        self,
        current_data: Dict[str, Any],
        updates: Dict[str, Any],
        strategy: ConflictResolutionStrategy,
        context: SharedContext,
        updater_id: str,
    ) -> Dict[str, Any]:
        """Resolve conflicts between current data and updates."""
        if strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Simply apply updates over current data
            merged = copy.deepcopy(current_data)
            merged.update(updates)
            return merged

        elif strategy == ConflictResolutionStrategy.FIRST_WRITE_WINS:
            # Only add new keys, don't override existing
            merged = copy.deepcopy(current_data)
            for key, value in updates.items():
                if key not in merged:
                    merged[key] = value
            return merged

        elif strategy == ConflictResolutionStrategy.MERGE:
            # Intelligent merge based on data types
            merged = copy.deepcopy(current_data)
            for key, new_value in updates.items():
                if key in merged:
                    current_value = merged[key]
                    # Merge lists
                    if isinstance(current_value, list) and isinstance(new_value, list):
                        merged[key] = current_value + [item for item in new_value if item not in current_value]
                    # Merge dicts
                    elif isinstance(current_value, dict) and isinstance(new_value, dict):
                        merged[key] = {**current_value, **new_value}
                    # Otherwise, last write wins
                    else:
                        merged[key] = new_value
                else:
                    merged[key] = new_value
            return merged

        elif strategy == ConflictResolutionStrategy.TIMESTAMP_BASED:
            # Use timestamps to determine which update wins
            merged = copy.deepcopy(current_data)
            current_time = datetime.utcnow()
            for key, value in updates.items():
                if key not in merged or context.updated_at < current_time:
                    merged[key] = value
            return merged

        else:  # MANUAL
            # Return updates as-is and log conflict for manual resolution
            logger.warning(f"Manual conflict resolution required for context {context.context_id}")
            return copy.deepcopy(updates)

    async def subscribe_to_context(
        self,
        context_id: str,
        subscriber_id: str,
        callback: Optional[Callable] = None,
    ) -> bool:
        """
        Subscribe to context updates (streaming).

        Args:
            context_id: ID of the context
            subscriber_id: ID of the subscriber
            callback: Optional callback for updates

        Returns:
            True if subscription was successful
        """
        context = self.contexts.get(context_id)
        if not context:
            return False

        # Check access control
        if subscriber_id not in context.access_control:
            logger.warning(f"Access denied for {subscriber_id} to subscribe to context {context_id}")
            return False

        context.subscribers.add(subscriber_id)

        if callback:
            self.update_callbacks[context_id].append(callback)

        logger.debug(f"Agent {subscriber_id} subscribed to context {context_id}")
        return True

    async def unsubscribe_from_context(
        self,
        context_id: str,
        subscriber_id: str,
        callback: Optional[Callable] = None,
    ) -> bool:
        """
        Unsubscribe from context updates.

        Args:
            context_id: ID of the context
            subscriber_id: ID of the subscriber
            callback: Optional callback to remove

        Returns:
            True if unsubscription was successful
        """
        context = self.contexts.get(context_id)
        if not context:
            return False

        context.subscribers.discard(subscriber_id)

        if callback and context_id in self.update_callbacks:
            if callback in self.update_callbacks[context_id]:
                self.update_callbacks[context_id].remove(callback)

        logger.debug(f"Agent {subscriber_id} unsubscribed from context {context_id}")
        return True

    async def _notify_subscribers(self, context_id: str, updated_data: Dict[str, Any], updater_id: str) -> None:
        """Notify subscribers of context updates."""
        context = self.contexts.get(context_id)
        if not context:
            return

        update_notification = {
            "context_id": context_id,
            "updater_id": updater_id,
            "data": copy.deepcopy(updated_data),
            "version": context.current_version,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Execute callbacks
        if context_id in self.update_callbacks:
            for callback in self.update_callbacks[context_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(update_notification)
                    else:
                        callback(update_notification)
                except Exception as e:
                    logger.error(f"Error executing context update callback: {e}")

    async def grant_access(self, context_id: str, granter_id: str, grantee_id: str) -> bool:
        """
        Grant access to a context.

        Args:
            context_id: ID of the context
            granter_id: ID of the agent granting access (must be owner)
            grantee_id: ID of the agent being granted access

        Returns:
            True if access was granted
        """
        context = self.contexts.get(context_id)
        if not context:
            return False

        # Only owner can grant access
        if granter_id != context.owner_id:
            logger.warning(f"Only owner can grant access to context {context_id}")
            return False

        context.access_control.add(grantee_id)
        logger.info(f"Granted access to {grantee_id} for context {context_id}")
        return True

    async def revoke_access(self, context_id: str, revoker_id: str, revokee_id: str) -> bool:
        """
        Revoke access to a context.

        Args:
            context_id: ID of the context
            revoker_id: ID of the agent revoking access (must be owner)
            revokee_id: ID of the agent losing access

        Returns:
            True if access was revoked
        """
        context = self.contexts.get(context_id)
        if not context:
            return False

        # Only owner can revoke access
        if revoker_id != context.owner_id:
            logger.warning(f"Only owner can revoke access to context {context_id}")
            return False

        # Can't revoke owner's access
        if revokee_id == context.owner_id:
            logger.warning("Cannot revoke owner's access to context")
            return False

        context.access_control.discard(revokee_id)
        context.subscribers.discard(revokee_id)
        logger.info(f"Revoked access from {revokee_id} for context {context_id}")
        return True

    async def get_version_history(self, context_id: str, requester_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get version history for a context.

        Args:
            context_id: ID of the context
            requester_id: ID of the requester

        Returns:
            List of version information or None if unauthorized
        """
        context = self.contexts.get(context_id)
        if not context:
            return None

        # Check access control
        if requester_id not in context.access_control:
            return None

        history = []
        for version in context.versions:
            history.append(
                {
                    "version_number": version.version_number,
                    "author_id": version.author_id,
                    "timestamp": version.timestamp.isoformat(),
                    "parent_version": version.parent_version,
                    "metadata": version.metadata,
                }
            )

        return history

    async def rollback_to_version(self, context_id: str, requester_id: str, target_version: int) -> bool:
        """
        Rollback context to a previous version.

        Args:
            context_id: ID of the context
            requester_id: ID of the requester (must be owner)
            target_version: Version number to rollback to

        Returns:
            True if rollback was successful
        """
        context = self.contexts.get(context_id)
        if not context:
            return False

        # Only owner can rollback
        if requester_id != context.owner_id:
            logger.warning(f"Only owner can rollback context {context_id}")
            return False

        # Find target version
        target = None
        for version in context.versions:
            if version.version_number == target_version:
                target = version
                break

        if not target:
            logger.error(f"Version {target_version} not found for context {context_id}")
            return False

        # Create new version based on target (rollback is a new version)
        context._create_version(target.data, requester_id)
        context.metadata["rollback"] = {
            "from_version": context.current_version - 1,
            "to_version": target_version,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Notify subscribers
        await self._notify_subscribers(context_id, context.data, requester_id)

        logger.info(f"Rolled back context {context_id} to version {target_version}")
        return True

    def get_contexts_by_scope(self, scope: ContextScope, scope_id: str) -> List[str]:
        """
        Get all contexts for a specific scope.

        Args:
            scope: Scope level
            scope_id: ID of the scope

        Returns:
            List of context IDs
        """
        if scope == ContextScope.COMMUNITY:
            return list(self.community_contexts.get(scope_id, set()))
        elif scope == ContextScope.SESSION:
            return list(self.session_contexts.get(scope_id, set()))
        elif scope == ContextScope.TASK:
            return list(self.task_contexts.get(scope_id, set()))
        elif scope == ContextScope.AGENT:
            return list(self.agent_contexts.get(scope_id, set()))
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get context manager statistics.

        Returns:
            Statistics dictionary
        """
        total_versions = sum(len(ctx.versions) for ctx in self.contexts.values())
        total_subscribers = sum(len(ctx.subscribers) for ctx in self.contexts.values())

        return {
            "total_contexts": len(self.contexts),
            "total_versions": total_versions,
            "total_subscribers": total_subscribers,
            "community_contexts": sum(len(s) for s in self.community_contexts.values()),
            "session_contexts": sum(len(s) for s in self.session_contexts.values()),
            "task_contexts": sum(len(s) for s in self.task_contexts.values()),
            "agent_contexts": sum(len(s) for s in self.agent_contexts.values()),
        }
