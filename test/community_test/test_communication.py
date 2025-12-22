"""
Tests for Communication Hub

Tests for messaging, pub/sub, and output streaming.
"""

import pytest
import logging
import asyncio

from aiecs.domain.community.communication_hub import MessageType, EventType

logger = logging.getLogger(__name__)


class TestMessaging:
    """Tests for agent messaging."""
    
    @pytest.mark.asyncio
    async def test_send_and_receive_message(self, communication_hub):
        """Test sending and receiving messages."""
        logger.info("Testing send and receive message")
        
        await communication_hub.register_agent("agent_1")
        await communication_hub.register_agent("agent_2")
        
        # Send message
        message_id = await communication_hub.send_message(
            sender_id="agent_1",
            recipient_ids=["agent_2"],
            message_type=MessageType.REQUEST,
            content="Hello from agent_1"
        )
        
        assert message_id is not None
        
        # Receive messages
        messages = await communication_hub.receive_messages("agent_2")
        
        assert len(messages) == 1
        assert messages[0].sender_id == "agent_1"
        assert messages[0].content == "Hello from agent_1"
        assert messages[0].message_type == MessageType.REQUEST
        
        logger.debug(f"Message {message_id} delivered successfully")
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, communication_hub):
        """Test broadcasting messages."""
        logger.info("Testing broadcast message")
        
        # Register multiple agents
        agents = ["agent_1", "agent_2", "agent_3", "agent_4"]
        for agent_id in agents:
            await communication_hub.register_agent(agent_id)
        
        # Broadcast
        message_id = await communication_hub.broadcast_message(
            sender_id="agent_1",
            content="Broadcast message to all"
        )
        
        assert message_id is not None
        
        # Check all others received
        for agent_id in ["agent_2", "agent_3", "agent_4"]:
            messages = await communication_hub.receive_messages(agent_id)
            assert len(messages) == 1
            assert messages[0].content == "Broadcast message to all"
        
        # Sender shouldn't receive own broadcast
        messages = await communication_hub.receive_messages("agent_1")
        assert len(messages) == 0
        
        logger.debug(f"Broadcast to {len(agents)-1} agents")
    
    @pytest.mark.asyncio
    async def test_multicast_message(self, communication_hub):
        """Test multicast messaging."""
        logger.info("Testing multicast message")
        
        agents = ["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"]
        for agent_id in agents:
            await communication_hub.register_agent(agent_id)
        
        # Send to specific subset
        message_id = await communication_hub.send_message(
            sender_id="agent_1",
            recipient_ids=["agent_2", "agent_4"],
            message_type=MessageType.NOTIFICATION,
            content="Multicast to 2 and 4"
        )
        
        # Check recipients received
        for agent_id in ["agent_2", "agent_4"]:
            messages = await communication_hub.receive_messages(agent_id)
            assert len(messages) == 1
        
        # Check non-recipients didn't receive
        for agent_id in ["agent_3", "agent_5"]:
            messages = await communication_hub.receive_messages(agent_id)
            assert len(messages) == 0
        
        logger.debug("Multicast delivered to correct recipients")
    
    @pytest.mark.asyncio
    async def test_message_queue_overflow(self, communication_hub):
        """Test message queue with many messages."""
        logger.info("Testing message queue limits")
        
        await communication_hub.register_agent("receiver")
        
        # Send many messages
        for i in range(150):  # More than max queue size (100)
            await communication_hub.send_message(
                sender_id="sender",
                recipient_ids=["receiver"],
                message_type=MessageType.NOTIFICATION,
                content=f"Message {i}"
            )
        
        # Should have at most max_queue_size messages
        unread_count = communication_hub.get_unread_count("receiver")
        assert unread_count <= communication_hub.max_queue_size
        
        logger.debug(f"Queue size maintained at: {unread_count}")


class TestPubSub:
    """Tests for pub/sub system."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish_event(self, communication_hub):
        """Test subscribing to and publishing events."""
        logger.info("Testing event subscription and publishing")
        
        received_events = []
        
        async def event_handler(event):
            received_events.append(event)
        
        # Subscribe
        success = await communication_hub.subscribe_to_event(
            subscriber_id="subscriber_1",
            event_type=EventType.MEMBER_JOINED,
            handler=event_handler
        )
        assert success is True
        
        # Publish event
        event_id = await communication_hub.publish_event(
            event_type=EventType.MEMBER_JOINED,
            source_id="community_1",
            data={"member_id": "new_member"},
            community_id="community_1"
        )
        
        assert event_id is not None
        
        # Wait a bit for async handler
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].event_type == EventType.MEMBER_JOINED
        assert received_events[0].data["member_id"] == "new_member"
        
        logger.debug(f"Event {event_id} received by subscriber")
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, communication_hub):
        """Test multiple subscribers to same event."""
        logger.info("Testing multiple subscribers")
        
        received_counts = {"sub1": 0, "sub2": 0, "sub3": 0}
        
        async def make_handler(sub_id):
            async def handler(event):
                received_counts[sub_id] += 1
            return handler
        
        # Subscribe multiple
        for sub_id in ["sub1", "sub2", "sub3"]:
            await communication_hub.subscribe_to_event(
                subscriber_id=sub_id,
                event_type=EventType.DECISION_APPROVED,
                handler=await make_handler(sub_id)
            )
        
        # Publish
        await communication_hub.publish_event(
            event_type=EventType.DECISION_APPROVED,
            source_id="decision_1",
            data={"decision": "approved"}
        )
        
        await asyncio.sleep(0.1)
        
        # All should have received
        assert received_counts["sub1"] == 1
        assert received_counts["sub2"] == 1
        assert received_counts["sub3"] == 1
        
        logger.debug(f"Event delivered to {len(received_counts)} subscribers")
    
    @pytest.mark.asyncio
    async def test_topic_subscription(self, communication_hub):
        """Test custom topic subscriptions."""
        logger.info("Testing topic subscriptions")
        
        received_messages = []
        
        async def topic_handler(event):
            received_messages.append(event.data)
        
        # Subscribe to custom topic
        success = await communication_hub.subscribe_to_topic(
            subscriber_id="topic_subscriber",
            topic="ai_research",
            handler=topic_handler
        )
        assert success is True
        
        # Publish to topic
        event_id = await communication_hub.publish_to_topic(
            topic="ai_research",
            source_id="researcher_1",
            data={"finding": "new discovery"}
        )
        
        await asyncio.sleep(0.1)
        
        assert len(received_messages) == 1
        assert received_messages[0]["finding"] == "new discovery"
        
        logger.debug(f"Topic message received")
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, communication_hub):
        """Test unsubscribing from events."""
        logger.info("Testing unsubscribe")
        
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        # Subscribe
        await communication_hub.subscribe_to_event(
            subscriber_id="temp_subscriber",
            event_type=EventType.RESOURCE_CREATED,
            handler=handler
        )
        
        # Publish (should receive)
        await communication_hub.publish_event(
            event_type=EventType.RESOURCE_CREATED,
            source_id="source_1",
            data={"resource": "test"}
        )
        
        await asyncio.sleep(0.1)
        assert len(received_events) == 1
        
        # Unsubscribe
        success = await communication_hub.unsubscribe_from_event(
            subscriber_id="temp_subscriber",
            event_type=EventType.RESOURCE_CREATED
        )
        assert success is True
        
        # Publish again (should not receive)
        await communication_hub.publish_event(
            event_type=EventType.RESOURCE_CREATED,
            source_id="source_2",
            data={"resource": "test2"}
        )
        
        await asyncio.sleep(0.1)
        assert len(received_events) == 1  # Still 1, not 2
        
        logger.debug("Unsubscribe successful")


class TestOutputStreaming:
    """Tests for output streaming."""
    
    @pytest.mark.asyncio
    async def test_subscribe_to_output_stream(self, communication_hub):
        """Test subscribing to agent output streams."""
        logger.info("Testing output stream subscription")
        
        received_outputs = []
        
        async def output_callback(stream_data):
            received_outputs.append(stream_data)
        
        # Subscribe to agent's output
        success = await communication_hub.subscribe_to_output(
            publisher_id="producer_agent",
            subscriber_callback=output_callback
        )
        assert success is True
        
        # Stream output
        count = await communication_hub.stream_output(
            publisher_id="producer_agent",
            output_data={"result": "partial result"},
            stream_type="progress"
        )
        
        assert count == 1
        
        await asyncio.sleep(0.1)
        
        assert len(received_outputs) == 1
        assert received_outputs[0]["data"]["result"] == "partial result"
        assert received_outputs[0]["stream_type"] == "progress"
        
        logger.debug("Output stream received")
    
    @pytest.mark.asyncio
    async def test_multiple_output_subscribers(self, communication_hub):
        """Test multiple subscribers to same output stream."""
        logger.info("Testing multiple output subscribers")
        
        received_by = {"sub1": [], "sub2": [], "sub3": []}
        
        async def make_callback(sub_id):
            async def callback(data):
                received_by[sub_id].append(data)
            return callback
        
        # Multiple subscribers
        for sub_id in ["sub1", "sub2", "sub3"]:
            await communication_hub.subscribe_to_output(
                publisher_id="stream_agent",
                subscriber_callback=await make_callback(sub_id)
            )
        
        # Stream output
        count = await communication_hub.stream_output(
            publisher_id="stream_agent",
            output_data={"value": 42}
        )
        
        assert count == 3
        
        await asyncio.sleep(0.1)
        
        for sub_id in ["sub1", "sub2", "sub3"]:
            assert len(received_by[sub_id]) == 1
            assert received_by[sub_id][0]["data"]["value"] == 42
        
        logger.debug(f"Stream delivered to {count} subscribers")


class TestStatistics:
    """Tests for communication statistics."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, communication_hub):
        """Test getting hub statistics."""
        logger.info("Testing communication statistics")
        
        # Register agents
        for i in range(5):
            await communication_hub.register_agent(f"agent_{i}")
        
        # Send some messages
        for i in range(3):
            await communication_hub.send_message(
                sender_id="agent_0",
                recipient_ids=["agent_1"],
                message_type=MessageType.NOTIFICATION,
                content=f"Message {i}"
            )
        
        stats = communication_hub.get_statistics()
        
        assert stats["active_agents"] == 5
        assert stats["total_messages"] >= 3
        assert "pending_messages" in stats
        
        logger.debug(f"Statistics: {stats}")
    
    @pytest.mark.asyncio
    async def test_get_agent_status(self, communication_hub):
        """Test getting individual agent status."""
        logger.info("Testing agent status")
        
        await communication_hub.register_agent("status_agent")
        
        # Subscribe to event
        await communication_hub.subscribe_to_event(
            subscriber_id="status_agent",
            event_type=EventType.MEMBER_JOINED
        )
        
        # Send message
        await communication_hub.send_message(
            sender_id="other_agent",
            recipient_ids=["status_agent"],
            message_type=MessageType.NOTIFICATION,
            content="Test"
        )
        
        status = communication_hub.get_agent_status("status_agent")
        
        assert status["is_active"] is True
        assert status["unread_messages"] == 1
        assert EventType.MEMBER_JOINED.value in status["event_subscriptions"]
        
        logger.debug(f"Agent status: {status}")


