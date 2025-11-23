"""
Communication Hub

Provides agent-to-agent messaging, event bus, and pub/sub system
for community communication and collaboration.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from enum import Enum
from collections import defaultdict, deque
import uuid

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in the community."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    SHARE = "share"
    BROADCAST = "broadcast"


class EventType(str, Enum):
    """Types of community events."""

    COMMUNITY_CREATED = "community_created"
    COMMUNITY_UPDATED = "community_updated"
    MEMBER_JOINED = "member_joined"
    MEMBER_EXITED = "member_exited"
    MEMBER_UPDATED = "member_updated"
    DECISION_PROPOSED = "decision_proposed"
    DECISION_VOTED = "decision_voted"
    DECISION_APPROVED = "decision_approved"
    DECISION_REJECTED = "decision_rejected"
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_SHARED = "resource_shared"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    CUSTOM = "custom"


class Message:
    """Represents a message between agents."""

    def __init__(
        self,
        sender_id: str,
        recipient_ids: List[str],
        message_type: MessageType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a message.

        Args:
            sender_id: ID of the sending agent
            recipient_ids: List of recipient agent IDs (empty for broadcast)
            message_type: Type of message
            content: Message content
            metadata: Optional metadata
        """
        self.message_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.recipient_ids = recipient_ids
        self.message_type = message_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.delivered_to: Set[str] = set()
        self.read_by: Set[str] = set()


class Event:
    """Represents a community event."""

    def __init__(
        self,
        event_type: EventType,
        source_id: str,
        data: Dict[str, Any],
        community_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an event.

        Args:
            event_type: Type of event
            source_id: ID of the source (community, member, etc.)
            data: Event data
            community_id: Optional community ID
            metadata: Optional metadata
        """
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.source_id = source_id
        self.data = data
        self.community_id = community_id
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class CommunicationHub:
    """
    Central hub for agent communication and event distribution.
    Provides messaging, pub/sub, and event broadcasting capabilities.
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the communication hub.

        Args:
            max_queue_size: Maximum size for message queues
        """
        self.max_queue_size = max_queue_size

        # Message queues per agent
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))

        # Event subscriptions: event_type -> set of subscriber_ids
        self.event_subscriptions: Dict[EventType, Set[str]] = defaultdict(set)

        # Topic subscriptions: topic -> set of subscriber_ids
        self.topic_subscriptions: Dict[str, Set[str]] = defaultdict(set)

        # Event handlers: subscriber_id -> handler_function
        self.event_handlers: Dict[str, Callable] = {}

        # Message history (limited)
        self.message_history: deque = deque(maxlen=max_queue_size * 2)
        self.event_history: deque = deque(maxlen=max_queue_size * 2)

        # Output streams: agent_id -> list of subscriber_callback
        self.output_streams: Dict[str, List[Callable]] = defaultdict(list)

        # Active connections
        self.active_agents: Set[str] = set()

        logger.info("Communication hub initialized")

    # ========== Agent Messaging ==========

    async def send_message(
        self,
        sender_id: str,
        recipient_ids: List[str],
        message_type: MessageType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send a message to one or more recipients (unicast/multicast).

        Args:
            sender_id: ID of the sending agent
            recipient_ids: List of recipient agent IDs
            message_type: Type of message
            content: Message content
            metadata: Optional metadata

        Returns:
            Message ID
        """
        message = Message(sender_id, recipient_ids, message_type, content, metadata)

        # Deliver to each recipient's queue
        for recipient_id in recipient_ids:
            if recipient_id in self.active_agents or len(self.message_queues[recipient_id]) < self.max_queue_size:
                self.message_queues[recipient_id].append(message)
                message.delivered_to.add(recipient_id)

        # Store in history
        self.message_history.append(message)

        logger.debug(f"Message {message.message_id} from {sender_id} to {len(recipient_ids)} recipients")
        return message.message_id

    async def broadcast_message(
        self,
        sender_id: str,
        content: Any,
        community_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Broadcast a message to all active agents or community members.

        Args:
            sender_id: ID of the sending agent
            content: Message content
            community_id: Optional community to limit broadcast
            metadata: Optional metadata

        Returns:
            Message ID
        """
        # Get recipients (all active agents or community members)
        recipients = list(self.active_agents)

        message = Message(sender_id, recipients, MessageType.BROADCAST, content, metadata)

        # Deliver to all recipients
        for recipient_id in recipients:
            if recipient_id != sender_id:  # Don't send to self
                self.message_queues[recipient_id].append(message)
                message.delivered_to.add(recipient_id)

        # Store in history
        self.message_history.append(message)

        logger.info(f"Broadcast message {message.message_id} from {sender_id} to {len(recipients)} agents")
        return message.message_id

    async def receive_messages(
        self,
        agent_id: str,
        mark_as_read: bool = True,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        Receive messages for an agent.

        Args:
            agent_id: ID of the agent receiving messages
            mark_as_read: Whether to mark messages as read
            limit: Optional limit on number of messages to retrieve

        Returns:
            List of messages
        """
        queue = self.message_queues[agent_id]

        if not queue:
            return []

        # Get messages
        count = min(limit, len(queue)) if limit else len(queue)
        messages = []

        for _ in range(count):
            if queue:
                message = queue.popleft()
                if mark_as_read:
                    message.read_by.add(agent_id)
                messages.append(message)

        logger.debug(f"Agent {agent_id} received {len(messages)} messages")
        return messages

    async def peek_messages(self, agent_id: str, limit: Optional[int] = None) -> List[Message]:
        """
        Peek at messages without removing them from queue.

        Args:
            agent_id: ID of the agent
            limit: Optional limit on number of messages

        Returns:
            List of messages
        """
        queue = self.message_queues[agent_id]
        count = min(limit, len(queue)) if limit else len(queue)
        return list(queue)[:count] if count > 0 else []

    def get_unread_count(self, agent_id: str) -> int:
        """
        Get count of unread messages for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Number of unread messages
        """
        return len(self.message_queues[agent_id])

    # ========== Event Bus & Pub/Sub ==========

    async def subscribe_to_event(
        self,
        subscriber_id: str,
        event_type: EventType,
        handler: Optional[Callable] = None,
    ) -> bool:
        """
        Subscribe to a specific event type.

        Args:
            subscriber_id: ID of the subscriber
            event_type: Type of event to subscribe to
            handler: Optional handler function for the event

        Returns:
            True if subscription was successful
        """
        self.event_subscriptions[event_type].add(subscriber_id)

        if handler:
            self.event_handlers[f"{subscriber_id}:{event_type.value}"] = handler

        logger.debug(f"Agent {subscriber_id} subscribed to {event_type.value}")
        return True

    async def unsubscribe_from_event(self, subscriber_id: str, event_type: EventType) -> bool:
        """
        Unsubscribe from an event type.

        Args:
            subscriber_id: ID of the subscriber
            event_type: Type of event to unsubscribe from

        Returns:
            True if unsubscription was successful
        """
        if event_type in self.event_subscriptions:
            self.event_subscriptions[event_type].discard(subscriber_id)

        handler_key = f"{subscriber_id}:{event_type.value}"
        if handler_key in self.event_handlers:
            del self.event_handlers[handler_key]

        logger.debug(f"Agent {subscriber_id} unsubscribed from {event_type.value}")
        return True

    async def subscribe_to_topic(
        self,
        subscriber_id: str,
        topic: str,
        handler: Optional[Callable] = None,
    ) -> bool:
        """
        Subscribe to a custom topic.

        Args:
            subscriber_id: ID of the subscriber
            topic: Topic name
            handler: Optional handler function

        Returns:
            True if subscription was successful
        """
        self.topic_subscriptions[topic].add(subscriber_id)

        if handler:
            self.event_handlers[f"{subscriber_id}:topic:{topic}"] = handler

        logger.debug(f"Agent {subscriber_id} subscribed to topic '{topic}'")
        return True

    async def unsubscribe_from_topic(self, subscriber_id: str, topic: str) -> bool:
        """
        Unsubscribe from a topic.

        Args:
            subscriber_id: ID of the subscriber
            topic: Topic name

        Returns:
            True if unsubscription was successful
        """
        if topic in self.topic_subscriptions:
            self.topic_subscriptions[topic].discard(subscriber_id)

        handler_key = f"{subscriber_id}:topic:{topic}"
        if handler_key in self.event_handlers:
            del self.event_handlers[handler_key]

        logger.debug(f"Agent {subscriber_id} unsubscribed from topic '{topic}'")
        return True

    async def publish_event(
        self,
        event_type: EventType,
        source_id: str,
        data: Dict[str, Any],
        community_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event
            source_id: ID of the event source
            data: Event data
            community_id: Optional community ID
            metadata: Optional metadata

        Returns:
            Event ID
        """
        event = Event(event_type, source_id, data, community_id, metadata)

        # Store in history
        self.event_history.append(event)

        # Get subscribers
        subscribers = self.event_subscriptions.get(event_type, set())

        # Execute handlers
        for subscriber_id in subscribers:
            handler_key = f"{subscriber_id}:{event_type.value}"
            handler = self.event_handlers.get(handler_key)

            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error executing event handler for {subscriber_id}: {e}")

        logger.debug(f"Published event {event_type.value} to {len(subscribers)} subscribers")
        return event.event_id

    async def publish_to_topic(
        self,
        topic: str,
        source_id: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Publish data to a topic.

        Args:
            topic: Topic name
            source_id: ID of the publisher
            data: Data to publish
            metadata: Optional metadata

        Returns:
            Event ID
        """
        event = Event(EventType.CUSTOM, source_id, data, None, metadata)
        event.metadata["topic"] = topic

        # Store in history
        self.event_history.append(event)

        # Get subscribers
        subscribers = self.topic_subscriptions.get(topic, set())

        # Execute handlers
        for subscriber_id in subscribers:
            handler_key = f"{subscriber_id}:topic:{topic}"
            handler = self.event_handlers.get(handler_key)

            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error executing topic handler for {subscriber_id}: {e}")

        logger.debug(f"Published to topic '{topic}' for {len(subscribers)} subscribers")
        return event.event_id

    # ========== Output Streaming ==========

    async def subscribe_to_output(
        self,
        publisher_id: str,
        subscriber_callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Subscribe to an agent's output stream.

        Args:
            publisher_id: ID of the agent publishing output
            subscriber_callback: Callback function for output data

        Returns:
            True if subscription was successful
        """
        self.output_streams[publisher_id].append(subscriber_callback)
        logger.debug(f"Subscribed to output stream of {publisher_id}")
        return True

    async def unsubscribe_from_output(
        self,
        publisher_id: str,
        subscriber_callback: Callable[[Dict[str, Any]], None],
    ) -> bool:
        """
        Unsubscribe from an agent's output stream.

        Args:
            publisher_id: ID of the agent
            subscriber_callback: Callback function to remove

        Returns:
            True if unsubscription was successful
        """
        if publisher_id in self.output_streams:
            if subscriber_callback in self.output_streams[publisher_id]:
                self.output_streams[publisher_id].remove(subscriber_callback)
                logger.debug(f"Unsubscribed from output stream of {publisher_id}")
                return True
        return False

    async def stream_output(
        self,
        publisher_id: str,
        output_data: Dict[str, Any],
        stream_type: str = "result",
    ) -> int:
        """
        Stream output to all subscribers with backpressure handling.

        Args:
            publisher_id: ID of the publishing agent
            output_data: Output data to stream
            stream_type: Type of output (result, progress, partial, etc.)

        Returns:
            Number of subscribers notified
        """
        if publisher_id not in self.output_streams:
            return 0

        stream_data = {
            "publisher_id": publisher_id,
            "stream_type": stream_type,
            "data": output_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        subscribers = self.output_streams[publisher_id]
        notified_count = 0

        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(stream_data)
                else:
                    callback(stream_data)
                notified_count += 1
            except Exception as e:
                logger.error(f"Error streaming output to subscriber: {e}")

        return notified_count

    # ========== Connection Management ==========

    async def register_agent(self, agent_id: str) -> bool:
        """
        Register an agent as active in the hub.

        Args:
            agent_id: ID of the agent

        Returns:
            True if registration was successful
        """
        self.active_agents.add(agent_id)
        logger.info(f"Registered agent {agent_id} in communication hub")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the hub.

        Args:
            agent_id: ID of the agent

        Returns:
            True if unregistration was successful
        """
        self.active_agents.discard(agent_id)

        # Clean up subscriptions
        for event_type in self.event_subscriptions:
            self.event_subscriptions[event_type].discard(agent_id)

        for topic in self.topic_subscriptions:
            self.topic_subscriptions[topic].discard(agent_id)

        # Clean up output streams
        if agent_id in self.output_streams:
            del self.output_streams[agent_id]

        logger.info(f"Unregistered agent {agent_id} from communication hub")
        return True

    # ========== Statistics & Monitoring ==========

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get communication hub statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "active_agents": len(self.active_agents),
            "total_messages": len(self.message_history),
            "total_events": len(self.event_history),
            "pending_messages": sum(len(q) for q in self.message_queues.values()),
            "event_subscriptions": sum(len(s) for s in self.event_subscriptions.values()),
            "topic_subscriptions": sum(len(s) for s in self.topic_subscriptions.values()),
            "output_streams": len(self.output_streams),
        }

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status for a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent status dictionary
        """
        return {
            "agent_id": agent_id,
            "is_active": agent_id in self.active_agents,
            "unread_messages": len(self.message_queues[agent_id]),
            "event_subscriptions": [et.value for et, subs in self.event_subscriptions.items() if agent_id in subs],
            "topic_subscriptions": [topic for topic, subs in self.topic_subscriptions.items() if agent_id in subs],
            "output_subscribers": len(self.output_streams.get(agent_id, [])),
        }
