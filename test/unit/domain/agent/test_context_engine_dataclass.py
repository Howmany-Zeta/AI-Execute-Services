"""
ContextEngine Dataclass Bug Fix Tests

Tests ContextEngine with dataclass objects in metadata to verify the bug fix
that eliminates the need for monkey patching.
Covers tasks 2.10.1-2.10.6 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

from aiecs.domain.context.context_engine import ContextEngine
from aiecs.domain.task.task_context import TaskContext


# ==================== Test Dataclasses ====================


@dataclass
class SummarizerState:
    """Example dataclass from the proposal - used in summarization."""
    summary: str
    token_count: int
    created_at: datetime


@dataclass
class Config:
    """Simple nested dataclass."""
    name: str
    value: int


@dataclass
class ComplexState:
    """Complex dataclass with nested structures."""
    config: Config
    states: List[str] = field(default_factory=list)
    tags: set = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==================== Fixtures ====================


@pytest.fixture
async def context_engine():
    """Create and initialize a ContextEngine instance for testing."""
    engine = ContextEngine()
    await engine.initialize()
    yield engine
    
    # Cleanup
    if engine._redis_client_wrapper:
        try:
            redis = await engine._redis_client_wrapper.get_client()
            # Delete test keys
            keys_to_delete = [
                "task_contexts",
                "sessions",
                "conversation_sessions",
            ]
            await redis.delete(*keys_to_delete)
        except Exception as e:
            logging.warning(f"Cleanup failed: {e}")
    
    if hasattr(engine, 'close'):
        await engine.close()


# ==================== Test 2.10.1: Dataclass in Metadata ====================


@pytest.mark.asyncio
async def test_context_engine_with_dataclass_in_metadata(context_engine):
    """
    Test 2.10.1: Test ContextEngine with dataclass objects in metadata.

    Verifies that dataclass objects in TaskContext metadata are automatically
    converted to dicts without requiring monkey patching.
    """
    # Create dataclass instance
    state = SummarizerState(
        summary="This is a test summary",
        token_count=100,
        created_at=datetime(2024, 1, 1, 12, 0, 0)
    )

    # Create TaskContext with dataclass in metadata
    context_data = {
        "user_id": "user123",
        "chat_id": "session456",
        "metadata": {
            "state": state,  # Dataclass should be automatically converted
            "other_data": "test"
        }
    }
    context = TaskContext(context_data)

    # Store context - should not raise any errors
    await context_engine.store_task_context("session456", context)

    # Retrieve context
    retrieved = await context_engine.get_task_context("session456")

    # Verify context was stored and retrieved
    assert retrieved is not None
    assert retrieved.user_id == "user123"
    assert retrieved.chat_id == "session456"
    
    # Verify metadata contains the state (as dict, not dataclass)
    assert "state" in retrieved.metadata
    state_dict = retrieved.metadata["state"]
    assert isinstance(state_dict, dict)
    assert state_dict["summary"] == "This is a test summary"
    assert state_dict["token_count"] == 100
    assert "other_data" in retrieved.metadata
    assert retrieved.metadata["other_data"] == "test"


@pytest.mark.asyncio
async def test_context_engine_with_multiple_dataclasses(context_engine):
    """
    Test 2.10.1: Test ContextEngine with multiple dataclass objects.

    Verifies that multiple dataclass objects are all converted properly.
    """
    state1 = SummarizerState(
        summary="Summary 1",
        token_count=50,
        created_at=datetime(2024, 1, 1, 12, 0, 0)
    )
    
    state2 = SummarizerState(
        summary="Summary 2",
        token_count=75,
        created_at=datetime(2024, 1, 2, 14, 0, 0)
    )

    context_data = {
        "user_id": "user789",
        "chat_id": "session789",
        "metadata": {
            "state1": state1,
            "state2": state2,
            "count": 2
        }
    }
    context = TaskContext(context_data)

    # Store and retrieve
    await context_engine.store_task_context("session789", context)
    retrieved = await context_engine.get_task_context("session789")

    # Verify both states were converted
    assert "state1" in retrieved.metadata
    assert "state2" in retrieved.metadata
    assert isinstance(retrieved.metadata["state1"], dict)
    assert isinstance(retrieved.metadata["state2"], dict)
    assert retrieved.metadata["state1"]["summary"] == "Summary 1"
    assert retrieved.metadata["state2"]["summary"] == "Summary 2"


# ==================== Test 2.10.2: Nested Dataclasses ====================


@pytest.mark.asyncio
async def test_context_engine_with_nested_dataclasses(context_engine):
    """
    Test 2.10.2: Test ContextEngine with nested dataclasses.

    Verifies that nested dataclass structures are properly converted.
    """
    # Create nested dataclass
    config = Config(name="test_config", value=42)
    complex_state = ComplexState(
        config=config,
        states=["state1", "state2"],
        tags={"tag1", "tag2"},
        metadata={"key": "value"}
    )

    context_data = {
        "user_id": "user_nested",
        "chat_id": "session_nested",
        "metadata": {
            "complex_state": complex_state
        }
    }
    context = TaskContext(context_data)

    # Store and retrieve
    await context_engine.store_task_context("session_nested", context)
    retrieved = await context_engine.get_task_context("session_nested")

    # Verify nested dataclass was converted
    assert "complex_state" in retrieved.metadata
    state_dict = retrieved.metadata["complex_state"]
    assert isinstance(state_dict, dict)

    # Verify nested config was also converted
    assert "config" in state_dict
    assert isinstance(state_dict["config"], dict)
    assert state_dict["config"]["name"] == "test_config"
    assert state_dict["config"]["value"] == 42

    # Verify other fields
    assert state_dict["states"] == ["state1", "state2"]
    assert isinstance(state_dict["tags"], list)  # Sets converted to lists
    assert set(state_dict["tags"]) == {"tag1", "tag2"}
    assert state_dict["metadata"]["key"] == "value"


@pytest.mark.asyncio
async def test_context_engine_with_dataclass_in_list(context_engine):
    """
    Test 2.10.2: Test ContextEngine with dataclass in list.

    Verifies that dataclasses inside lists are converted.
    """
    states = [
        SummarizerState(
            summary=f"Summary {i}",
            token_count=i * 10,
            created_at=datetime(2024, 1, i+1, 12, 0, 0)
        )
        for i in range(3)
    ]

    context_data = {
        "user_id": "user_list",
        "chat_id": "session_list",
        "metadata": {
            "states": states
        }
    }
    context = TaskContext(context_data)

    # Store and retrieve
    await context_engine.store_task_context("session_list", context)
    retrieved = await context_engine.get_task_context("session_list")

    # Verify list of dataclasses was converted
    assert "states" in retrieved.metadata
    states_list = retrieved.metadata["states"]
    assert isinstance(states_list, list)
    assert len(states_list) == 3

    for i, state_dict in enumerate(states_list):
        assert isinstance(state_dict, dict)
        assert state_dict["summary"] == f"Summary {i}"
        assert state_dict["token_count"] == i * 10


# ==================== Test 2.10.3: SummarizerState Dataclass ====================


@pytest.mark.asyncio
async def test_context_engine_with_summarizer_state(context_engine):
    """
    Test 2.10.3: Test ContextEngine with SummarizerState dataclass.

    Verifies the specific SummarizerState dataclass from the proposal works.
    """
    # Create SummarizerState as described in the proposal
    state = SummarizerState(
        summary="This is a comprehensive summary of the conversation",
        token_count=250,
        created_at=datetime.utcnow()
    )

    context_data = {
        "user_id": "user_summarizer",
        "chat_id": "session_summarizer",
        "metadata": {
            "summarizer_state": state,
            "compression_enabled": True
        }
    }
    context = TaskContext(context_data)

    # Store context - this is the exact use case from the proposal
    await context_engine.store_task_context("session_summarizer", context)

    # Retrieve and verify
    retrieved = await context_engine.get_task_context("session_summarizer")

    assert retrieved is not None
    assert "summarizer_state" in retrieved.metadata
    state_dict = retrieved.metadata["summarizer_state"]

    # Verify all fields
    assert state_dict["summary"] == "This is a comprehensive summary of the conversation"
    assert state_dict["token_count"] == 250
    assert "created_at" in state_dict
    assert retrieved.metadata["compression_enabled"] is True


@pytest.mark.asyncio
async def test_context_engine_summarizer_state_with_datetime(context_engine):
    """
    Test 2.10.3: Test SummarizerState with datetime serialization.

    Verifies that datetime objects in dataclasses are properly handled.
    """
    now = datetime(2024, 1, 15, 10, 30, 45)
    state = SummarizerState(
        summary="Test summary with specific datetime",
        token_count=150,
        created_at=now
    )

    context_data = {
        "user_id": "user_dt",
        "chat_id": "session_dt",
        "metadata": {"state": state}
    }
    context = TaskContext(context_data)

    await context_engine.store_task_context("session_dt", context)
    retrieved = await context_engine.get_task_context("session_dt")

    # Verify datetime was serialized
    state_dict = retrieved.metadata["state"]
    assert "created_at" in state_dict
    # Datetime should be converted to string (ISO format)
    assert isinstance(state_dict["created_at"], (str, datetime))


# ==================== Test 2.10.4: Automatic Conversion ====================


@pytest.mark.asyncio
async def test_automatic_dataclass_conversion(context_engine):
    """
    Test 2.10.4: Verify automatic dataclass conversion to dict.

    Verifies that the conversion happens automatically without manual intervention.
    """
    # Create a complex structure with multiple dataclasses
    config1 = Config(name="config1", value=10)
    config2 = Config(name="config2", value=20)

    state = ComplexState(
        config=config1,
        states=["active", "processing"],
        tags={"important", "urgent"},
        metadata={
            "nested_config": config2,
            "timestamp": datetime.utcnow()
        }
    )

    context_data = {
        "user_id": "user_auto",
        "chat_id": "session_auto",
        "metadata": {
            "state": state,
            "direct_config": config1
        }
    }
    context = TaskContext(context_data)

    # Store - automatic conversion should happen
    await context_engine.store_task_context("session_auto", context)
    retrieved = await context_engine.get_task_context("session_auto")

    # Verify all dataclasses were converted automatically
    assert isinstance(retrieved.metadata["state"], dict)
    assert isinstance(retrieved.metadata["state"]["config"], dict)
    assert isinstance(retrieved.metadata["state"]["metadata"]["nested_config"], dict)
    assert isinstance(retrieved.metadata["direct_config"], dict)

    # Verify values are preserved
    assert retrieved.metadata["state"]["config"]["name"] == "config1"
    assert retrieved.metadata["state"]["metadata"]["nested_config"]["value"] == 20
    assert retrieved.metadata["direct_config"]["value"] == 10


@pytest.mark.asyncio
async def test_dataclass_conversion_preserves_data(context_engine):
    """
    Test 2.10.4: Verify that dataclass conversion preserves all data.

    Ensures no data is lost during automatic conversion.
    """
    original_state = SummarizerState(
        summary="Original summary text",
        token_count=500,
        created_at=datetime(2024, 2, 1, 15, 30, 0)
    )

    context_data = {
        "user_id": "user_preserve",
        "chat_id": "session_preserve",
        "metadata": {"state": original_state}
    }
    context = TaskContext(context_data)

    await context_engine.store_task_context("session_preserve", context)
    retrieved = await context_engine.get_task_context("session_preserve")

    # Verify all original data is preserved
    state_dict = retrieved.metadata["state"]
    assert state_dict["summary"] == "Original summary text"
    assert state_dict["token_count"] == 500
    assert "created_at" in state_dict


# ==================== Test 2.10.5: Logging ====================


@pytest.mark.asyncio
async def test_dataclass_conversion_logging(context_engine, caplog):
    """
    Test 2.10.5: Verify logging for dataclass conversion.

    Verifies that debug messages are logged when dataclasses are converted.
    """
    with caplog.at_level(logging.DEBUG):
        state = SummarizerState(
            summary="Test for logging",
            token_count=100,
            created_at=datetime.utcnow()
        )

        context_data = {
            "user_id": "user_log",
            "chat_id": "session_log",
            "metadata": {"state": state}
        }
        context = TaskContext(context_data)

        await context_engine.store_task_context("session_log", context)

    # Verify debug logging occurred
    # The log message should mention dataclass conversion
    log_messages = [record.message for record in caplog.records]
    dataclass_logs = [msg for msg in log_messages if "dataclass" in msg.lower() or "SummarizerState" in msg]

    # Should have at least one log about dataclass conversion
    assert len(dataclass_logs) > 0, "Should log dataclass conversion"


@pytest.mark.asyncio
async def test_nested_dataclass_logging(context_engine, caplog):
    """
    Test 2.10.5: Verify logging for nested dataclass conversion.

    Verifies that nested dataclasses also generate appropriate logs.
    """
    with caplog.at_level(logging.DEBUG):
        config = Config(name="test", value=42)
        complex_state = ComplexState(
            config=config,
            states=["state1"],
            tags={"tag1"},
            metadata={}
        )

        context_data = {
            "user_id": "user_nested_log",
            "chat_id": "session_nested_log",
            "metadata": {"complex": complex_state}
        }
        context = TaskContext(context_data)

        await context_engine.store_task_context("session_nested_log", context)

    # Should have logs for both ComplexState and Config dataclasses
    log_messages = [record.message for record in caplog.records]
    dataclass_logs = [msg for msg in log_messages if "dataclass" in msg.lower()]

    # Should log conversion of nested dataclasses
    assert len(dataclass_logs) > 0


# ==================== Test 2.10.6: Existing Tests Compatibility ====================


@pytest.mark.asyncio
async def test_non_dataclass_metadata_still_works(context_engine):
    """
    Test 2.10.6: Verify that non-dataclass metadata still works.

    Ensures the dataclass fix doesn't break existing functionality.
    """
    # Regular metadata without dataclasses
    context_data = {
        "user_id": "user_regular",
        "chat_id": "session_regular",
        "metadata": {
            "string_value": "test",
            "int_value": 42,
            "list_value": [1, 2, 3],
            "dict_value": {"key": "value"},
            "datetime_value": datetime.utcnow()
        }
    }
    context = TaskContext(context_data)

    # Should work without any issues
    await context_engine.store_task_context("session_regular", context)
    retrieved = await context_engine.get_task_context("session_regular")

    # Verify all values are preserved
    assert retrieved.metadata["string_value"] == "test"
    assert retrieved.metadata["int_value"] == 42
    assert retrieved.metadata["list_value"] == [1, 2, 3]
    assert retrieved.metadata["dict_value"]["key"] == "value"


@pytest.mark.asyncio
async def test_mixed_dataclass_and_regular_metadata(context_engine):
    """
    Test 2.10.6: Verify mixed dataclass and regular metadata works.

    Ensures dataclasses and regular types can coexist in metadata.
    """
    state = SummarizerState(
        summary="Mixed metadata test",
        token_count=75,
        created_at=datetime.utcnow()
    )

    context_data = {
        "user_id": "user_mixed",
        "chat_id": "session_mixed",
        "metadata": {
            "dataclass_field": state,
            "string_field": "regular string",
            "number_field": 123,
            "list_field": ["a", "b", "c"],
            "dict_field": {"nested": "value"}
        }
    }
    context = TaskContext(context_data)

    await context_engine.store_task_context("session_mixed", context)
    retrieved = await context_engine.get_task_context("session_mixed")

    # Verify dataclass was converted
    assert isinstance(retrieved.metadata["dataclass_field"], dict)
    assert retrieved.metadata["dataclass_field"]["summary"] == "Mixed metadata test"

    # Verify regular fields are unchanged
    assert retrieved.metadata["string_field"] == "regular string"
    assert retrieved.metadata["number_field"] == 123
    assert retrieved.metadata["list_field"] == ["a", "b", "c"]
    assert retrieved.metadata["dict_field"]["nested"] == "value"


@pytest.mark.asyncio
async def test_empty_dataclass(context_engine):
    """
    Test edge case: empty dataclass with default values.
    """
    @dataclass
    class EmptyState:
        value: str = "default"
        count: int = 0

    state = EmptyState()

    context_data = {
        "user_id": "user_empty",
        "chat_id": "session_empty",
        "metadata": {"state": state}
    }
    context = TaskContext(context_data)

    await context_engine.store_task_context("session_empty", context)
    retrieved = await context_engine.get_task_context("session_empty")

    # Verify empty dataclass was converted
    assert isinstance(retrieved.metadata["state"], dict)
    assert retrieved.metadata["state"]["value"] == "default"
    assert retrieved.metadata["state"]["count"] == 0


@pytest.mark.asyncio
async def test_dataclass_with_none_values(context_engine):
    """
    Test edge case: dataclass with None values.
    """
    @dataclass
    class StateWithNone:
        required: str
        optional: str = None

    state = StateWithNone(required="test", optional=None)

    context_data = {
        "user_id": "user_none",
        "chat_id": "session_none",
        "metadata": {"state": state}
    }
    context = TaskContext(context_data)

    await context_engine.store_task_context("session_none", context)
    retrieved = await context_engine.get_task_context("session_none")

    # Verify None values are preserved
    state_dict = retrieved.metadata["state"]
    assert state_dict["required"] == "test"
    assert state_dict["optional"] is None

