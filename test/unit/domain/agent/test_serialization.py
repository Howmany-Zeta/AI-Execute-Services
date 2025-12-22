"""
Serialization Tests

Tests sanitization of asyncio.Queue, queue.Queue, ChainMap, datetime objects,
nested dictionaries, nested lists, and sanitization logging.
Covers tasks 2.9.1-2.9.7 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
import queue
import json
import logging
from datetime import datetime
from collections import ChainMap
from dataclasses import dataclass
from typing import Dict, Any
from unittest.mock import Mock, patch

from aiecs.domain.agent.persistence import AgentStateSerializer


# ==================== Test 2.9.1: asyncio.Queue Sanitization ====================


@pytest.mark.asyncio
async def test_sanitize_asyncio_queue():
    """
    Test 2.9.1: Test sanitization of asyncio.Queue objects.

    Verifies that asyncio.Queue objects are converted to placeholders.
    """
    # Create data with asyncio.Queue
    async_queue = asyncio.Queue()
    data = {
        "queue": async_queue,
        "name": "test",
    }

    # Sanitize
    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify queue was replaced with placeholder
    assert sanitized["name"] == "test"
    assert sanitized["queue"] == "<asyncio.Queue: not serializable>"
    assert isinstance(sanitized["queue"], str)


@pytest.mark.asyncio
async def test_sanitize_asyncio_queue_in_nested_dict():
    """
    Test 2.9.1: Test sanitization of asyncio.Queue in nested dictionary.

    Verifies that asyncio.Queue objects are sanitized in nested structures.
    """
    async_queue = asyncio.Queue()
    data = {
        "config": {
            "queue": async_queue,
            "timeout": 30,
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["config"]["timeout"] == 30
    assert sanitized["config"]["queue"] == "<asyncio.Queue: not serializable>"


# ==================== Test 2.9.2: queue.Queue Sanitization ====================


def test_sanitize_queue_queue():
    """
    Test 2.9.2: Test sanitization of queue.Queue objects.

    Verifies that queue.Queue objects are converted to placeholders.
    """
    # Create data with queue.Queue
    sync_queue = queue.Queue()
    data = {
        "queue": sync_queue,
        "name": "test",
    }

    # Sanitize
    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify queue was replaced with placeholder
    assert sanitized["name"] == "test"
    assert sanitized["queue"] == "<queue.Queue: not serializable>"
    assert isinstance(sanitized["queue"], str)


def test_sanitize_queue_queue_in_list():
    """
    Test 2.9.2: Test sanitization of queue.Queue in list.

    Verifies that queue.Queue objects are sanitized in lists.
    """
    sync_queue = queue.Queue()
    data = {
        "queues": [sync_queue, "item2", sync_queue]
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert len(sanitized["queues"]) == 3
    assert sanitized["queues"][0] == "<queue.Queue: not serializable>"
    assert sanitized["queues"][1] == "item2"
    assert sanitized["queues"][2] == "<queue.Queue: not serializable>"


# ==================== Test 2.9.3: ChainMap Sanitization ====================


def test_sanitize_chainmap():
    """
    Test 2.9.3: Test sanitization of ChainMap objects.

    Verifies that ChainMap objects are converted to regular dicts.
    """
    # Create ChainMap
    map1 = {"a": 1, "b": 2}
    map2 = {"b": 3, "c": 4}
    chain_map = ChainMap(map1, map2)

    data = {
        "config": chain_map,
        "name": "test",
    }

    # Sanitize
    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify ChainMap was converted to dict
    assert sanitized["name"] == "test"
    assert isinstance(sanitized["config"], dict)
    assert sanitized["config"]["a"] == 1
    assert sanitized["config"]["b"] == 2  # First map takes precedence
    assert sanitized["config"]["c"] == 4


def test_sanitize_chainmap_with_datetime():
    """
    Test 2.9.3: Test sanitization of ChainMap with datetime values.

    Verifies that ChainMap with datetime values is properly sanitized.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    chain_map = ChainMap({"timestamp": now, "value": 42})

    data = {"config": chain_map}

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert isinstance(sanitized["config"], dict)
    assert sanitized["config"]["timestamp"] == "2024-01-01T12:00:00"
    assert sanitized["config"]["value"] == 42


# ==================== Test 2.9.4: datetime Sanitization ====================


def test_sanitize_datetime():
    """
    Test 2.9.4: Test sanitization of datetime objects.

    Verifies that datetime objects are converted to ISO strings.
    """
    now = datetime(2024, 1, 1, 12, 0, 0, 123456)
    data = {
        "created_at": now,
        "name": "test",
    }

    # Sanitize
    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify datetime was converted to ISO string
    assert sanitized["name"] == "test"
    assert sanitized["created_at"] == "2024-01-01T12:00:00.123456"
    assert isinstance(sanitized["created_at"], str)


def test_sanitize_multiple_datetimes():
    """
    Test 2.9.4: Test sanitization of multiple datetime objects.

    Verifies that all datetime objects in a structure are converted.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    later = datetime(2024, 1, 2, 14, 30, 0)

    data = {
        "created_at": now,
        "updated_at": later,
        "metadata": {
            "timestamp": now,
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["created_at"] == "2024-01-01T12:00:00"
    assert sanitized["updated_at"] == "2024-01-02T14:30:00"
    assert sanitized["metadata"]["timestamp"] == "2024-01-01T12:00:00"


# ==================== Test 2.9.5: Nested Dictionary Sanitization ====================


def test_sanitize_nested_dictionaries():
    """
    Test 2.9.5: Test sanitization of nested dictionaries.

    Verifies that nested dictionaries are properly sanitized.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    async_queue = asyncio.Queue()

    data = {
        "level1": {
            "level2": {
                "level3": {
                    "timestamp": now,
                    "queue": async_queue,
                    "value": 42,
                }
            }
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify all levels are sanitized
    assert sanitized["level1"]["level2"]["level3"]["timestamp"] == "2024-01-01T12:00:00"
    assert sanitized["level1"]["level2"]["level3"]["queue"] == "<asyncio.Queue: not serializable>"
    assert sanitized["level1"]["level2"]["level3"]["value"] == 42


def test_sanitize_complex_nested_structure():
    """
    Test 2.9.5: Test sanitization of complex nested structure.

    Verifies that complex nested structures with mixed types are sanitized.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    chain_map = ChainMap({"a": 1}, {"b": 2})

    data = {
        "config": {
            "settings": {
                "timestamp": now,
                "chain": chain_map,
                "nested": {
                    "queue": queue.Queue(),
                    "value": "test",
                }
            }
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["config"]["settings"]["timestamp"] == "2024-01-01T12:00:00"
    assert isinstance(sanitized["config"]["settings"]["chain"], dict)
    assert sanitized["config"]["settings"]["chain"]["a"] == 1
    assert sanitized["config"]["settings"]["nested"]["queue"] == "<queue.Queue: not serializable>"
    assert sanitized["config"]["settings"]["nested"]["value"] == "test"


# ==================== Test 2.9.6: Nested List Sanitization ====================


def test_sanitize_nested_lists():
    """
    Test 2.9.6: Test sanitization of nested lists.

    Verifies that nested lists are properly sanitized.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)

    data = {
        "items": [
            [now, "item1"],
            ["item2", [now, "item3"]],
            [asyncio.Queue(), "item4"],
        ]
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify nested lists are sanitized
    assert sanitized["items"][0][0] == "2024-01-01T12:00:00"
    assert sanitized["items"][0][1] == "item1"
    assert sanitized["items"][1][0] == "item2"
    assert sanitized["items"][1][1][0] == "2024-01-01T12:00:00"
    assert sanitized["items"][1][1][1] == "item3"
    assert sanitized["items"][2][0] == "<asyncio.Queue: not serializable>"
    assert sanitized["items"][2][1] == "item4"


def test_sanitize_list_with_mixed_types():
    """
    Test 2.9.6: Test sanitization of list with mixed types.

    Verifies that lists with various types are properly sanitized.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    chain_map = ChainMap({"a": 1})

    data = {
        "mixed": [
            42,
            "string",
            now,
            chain_map,
            asyncio.Queue(),
            {"nested": now},
            [1, 2, 3],
        ]
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["mixed"][0] == 42
    assert sanitized["mixed"][1] == "string"
    assert sanitized["mixed"][2] == "2024-01-01T12:00:00"
    assert isinstance(sanitized["mixed"][3], dict)
    assert sanitized["mixed"][3]["a"] == 1
    assert sanitized["mixed"][4] == "<asyncio.Queue: not serializable>"
    assert sanitized["mixed"][5]["nested"] == "2024-01-01T12:00:00"
    assert sanitized["mixed"][6] == [1, 2, 3]


# ==================== Test 2.9.7: Sanitization Logging ====================


def test_sanitization_logging_asyncio_queue(caplog):
    """
    Test 2.9.7: Test sanitization logging for asyncio.Queue.

    Verifies that warnings are logged when asyncio.Queue is sanitized.
    """
    with caplog.at_level(logging.WARNING):
        data = {"queue": asyncio.Queue()}
        AgentStateSerializer._sanitize_checkpoint(data)

    # Verify warning was logged
    assert any("asyncio.Queue detected" in record.message for record in caplog.records)


def test_sanitization_logging_queue_queue(caplog):
    """
    Test 2.9.7: Test sanitization logging for queue.Queue.

    Verifies that warnings are logged when queue.Queue is sanitized.
    """
    with caplog.at_level(logging.WARNING):
        data = {"queue": queue.Queue()}
        AgentStateSerializer._sanitize_checkpoint(data)

    # Verify warning was logged
    assert any("queue.Queue detected" in record.message for record in caplog.records)


def test_sanitization_logging_chainmap(caplog):
    """
    Test 2.9.7: Test sanitization logging for ChainMap.

    Verifies that debug messages are logged when ChainMap is converted.
    """
    with caplog.at_level(logging.DEBUG):
        data = {"config": ChainMap({"a": 1})}
        AgentStateSerializer._sanitize_checkpoint(data)

    # Verify debug message was logged
    assert any("Converting ChainMap" in record.message for record in caplog.records)


def test_sanitization_logging_custom_object(caplog):
    """
    Test 2.9.7: Test sanitization logging for custom objects.

    Verifies that warnings are logged when custom objects are sanitized.
    """
    class CustomObject:
        def __init__(self):
            self.value = 42

    with caplog.at_level(logging.WARNING):
        data = {"obj": CustomObject()}
        AgentStateSerializer._sanitize_checkpoint(data)

    # Verify warning was logged
    assert any("Converting custom object" in record.message for record in caplog.records)


# ==================== Additional Comprehensive Tests ====================


def test_sanitize_dataclass():
    """
    Test sanitization of dataclass objects.

    Verifies that dataclass objects are converted to dicts.
    """
    @dataclass
    class TestData:
        name: str
        value: int
        timestamp: datetime

    now = datetime(2024, 1, 1, 12, 0, 0)
    test_obj = TestData(name="test", value=42, timestamp=now)

    data = {"obj": test_obj}

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert isinstance(sanitized["obj"], dict)
    assert sanitized["obj"]["name"] == "test"
    assert sanitized["obj"]["value"] == 42
    assert sanitized["obj"]["timestamp"] == "2024-01-01T12:00:00"


def test_sanitize_set():
    """
    Test sanitization of set objects.

    Verifies that sets are converted to lists.
    """
    data = {"items": {1, 2, 3, 4, 5}}

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert isinstance(sanitized["items"], list)
    assert len(sanitized["items"]) == 5
    assert set(sanitized["items"]) == {1, 2, 3, 4, 5}


def test_sanitize_bytes():
    """
    Test sanitization of bytes objects.

    Verifies that bytes are converted to base64 strings.
    """
    data = {"data": b"Hello, World!"}

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert isinstance(sanitized["data"], str)
    # Verify it's base64 encoded
    import base64
    decoded = base64.b64decode(sanitized["data"])
    assert decoded == b"Hello, World!"


def test_sanitize_tuple():
    """
    Test sanitization of tuple objects.

    Verifies that tuples are preserved (converted to tuple after sanitization).
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    data = {"items": (1, "test", now)}

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert isinstance(sanitized["items"], tuple)
    assert sanitized["items"][0] == 1
    assert sanitized["items"][1] == "test"
    assert sanitized["items"][2] == "2024-01-01T12:00:00"


def test_sanitize_none_and_primitives():
    """
    Test sanitization of None and primitive types.

    Verifies that None, bool, int, float, str are preserved.
    """
    data = {
        "none": None,
        "bool": True,
        "int": 42,
        "float": 3.14,
        "str": "test",
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["none"] is None
    assert sanitized["bool"] is True
    assert sanitized["int"] == 42
    assert sanitized["float"] == 3.14
    assert sanitized["str"] == "test"


def test_sanitize_empty_structures():
    """
    Test sanitization of empty structures.

    Verifies that empty dicts and lists are preserved.
    """
    data = {
        "empty_dict": {},
        "empty_list": [],
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    assert sanitized["empty_dict"] == {}
    assert sanitized["empty_list"] == []


def test_sanitize_json_serializable():
    """
    Test that sanitized data is JSON serializable.

    Verifies that the output can be serialized to JSON.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    data = {
        "timestamp": now,
        "queue": asyncio.Queue(),
        "chain": ChainMap({"a": 1}),
        "nested": {
            "list": [now, "test"],
            "value": 42,
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Should not raise an exception
    json_str = json.dumps(sanitized)
    assert json_str is not None

    # Verify we can load it back
    loaded = json.loads(json_str)
    assert loaded["timestamp"] == "2024-01-01T12:00:00"
    assert loaded["queue"] == "<asyncio.Queue: not serializable>"
    assert loaded["chain"]["a"] == 1


def test_sanitize_deeply_nested_structure():
    """
    Test sanitization of deeply nested structure.

    Verifies that very deep nesting is handled correctly.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)

    # Create deeply nested structure
    data = {
        "l1": {
            "l2": {
                "l3": {
                    "l4": {
                        "l5": {
                            "timestamp": now,
                            "queue": asyncio.Queue(),
                            "value": "deep",
                        }
                    }
                }
            }
        }
    }

    sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Verify deep nesting is preserved and sanitized
    assert sanitized["l1"]["l2"]["l3"]["l4"]["l5"]["timestamp"] == "2024-01-01T12:00:00"
    assert sanitized["l1"]["l2"]["l3"]["l4"]["l5"]["queue"] == "<asyncio.Queue: not serializable>"
    assert sanitized["l1"]["l2"]["l3"]["l4"]["l5"]["value"] == "deep"


def test_sanitize_error_handling(caplog):
    """
    Test error handling during sanitization.

    Verifies that errors during sanitization are handled gracefully.
    """
    class ProblematicObject:
        def __getattribute__(self, name):
            if name == "__dict__":
                raise RuntimeError("Cannot access __dict__")
            return super().__getattribute__(name)

    with caplog.at_level(logging.WARNING):
        data = {"obj": ProblematicObject()}
        sanitized = AgentStateSerializer._sanitize_checkpoint(data)

    # Should have a placeholder
    assert "<non-serializable:" in sanitized["obj"] or "ProblematicObject" in str(sanitized["obj"])


def test_make_json_serializable_direct():
    """
    Test _make_json_serializable method directly.

    Verifies that the core serialization method works correctly.
    """
    # Test primitives
    assert AgentStateSerializer._make_json_serializable(None) is None
    assert AgentStateSerializer._make_json_serializable(True) is True
    assert AgentStateSerializer._make_json_serializable(42) == 42
    assert AgentStateSerializer._make_json_serializable(3.14) == 3.14
    assert AgentStateSerializer._make_json_serializable("test") == "test"

    # Test datetime
    now = datetime(2024, 1, 1, 12, 0, 0)
    assert AgentStateSerializer._make_json_serializable(now) == "2024-01-01T12:00:00"

    # Test asyncio.Queue
    result = AgentStateSerializer._make_json_serializable(asyncio.Queue())
    assert result == "<asyncio.Queue: not serializable>"

    # Test queue.Queue
    result = AgentStateSerializer._make_json_serializable(queue.Queue())
    assert result == "<queue.Queue: not serializable>"

    # Test ChainMap
    chain = ChainMap({"a": 1})
    result = AgentStateSerializer._make_json_serializable(chain)
    assert isinstance(result, dict)
    assert result["a"] == 1


def test_serialize_agent_method():
    """
    Test AgentStateSerializer.serialize() method.

    Verifies that the high-level serialize method works correctly.
    """
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.models import AgentConfiguration, AgentType

    class MockAgent(BaseAIAgent):
        def __init__(self):
            config = AgentConfiguration()
            super().__init__(
                agent_id="test-agent",
                name="Test Agent",
                agent_type=AgentType.TASK_EXECUTOR,
                config=config,
            )

        async def _initialize(self):
            pass

        async def _shutdown(self):
            pass

        async def execute_task(self, task, context):
            return {"success": True}

        async def process_message(self, message, sender_id=None):
            return {"success": True}

    agent = MockAgent()
    serialized = AgentStateSerializer.serialize(agent)

    # Verify it's a dict
    assert isinstance(serialized, dict)
    assert serialized["agent_id"] == "test-agent"
    assert serialized["name"] == "Test Agent"

    # Verify it's JSON serializable
    json_str = json.dumps(serialized)
    assert json_str is not None

