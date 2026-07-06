import json
import pytest
from unittest.mock import MagicMock, AsyncMock, call
from apelios.router.router_output_publisher import RouterOutputPublisher

@pytest.fixture
def mock_broker():
    mock = MagicMock()
    mock.publish = AsyncMock()
    return mock

@pytest.fixture
def output_publisher(mock_broker):
    return RouterOutputPublisher(broker=mock_broker)

@pytest.mark.asyncio
async def test_publisher_forwards_type_unchanged(output_publisher, mock_broker):
    """Test that type field is forwarded unchanged through the publisher."""
    outputs = {
        "group1.pan": {
            "value": 0.5,
            "type": "delta",
            "timestamp": 123.0
        }
    }
    
    await output_publisher.publish(outputs)
    
    # Verify publish was called
    assert mock_broker.publish.call_count == 1
    
    # Verify the payload has type field unchanged
    call_args = mock_broker.publish.call_args
    subject = call_args[0][0]
    payload_bytes = call_args[0][1]
    payload = json.loads(payload_bytes.decode("utf-8"))
    
    assert subject == "target.group1.pan"
    assert payload["value"] == 0.5
    assert payload["type"] == "delta"
    assert payload["timestamp"] == 123.0

@pytest.mark.asyncio
async def test_publisher_forwards_all_types(output_publisher, mock_broker):
    """Test that all type values (absolute_uni, absolute_bi, delta, rate) are forwarded."""
    outputs = {
        "group1.dimmer": {"value": 0.5, "type": "absolute_uni", "timestamp": 100.0},
        "group1.pan": {"value": 0.3, "type": "absolute_bi", "timestamp": 101.0},
        "group1.x": {"value": 0.1, "type": "delta", "timestamp": 102.0},
        "group1.rate": {"value": 0.8, "type": "rate", "timestamp": 103.0},
    }
    
    await output_publisher.publish(outputs)
    
    assert mock_broker.publish.call_count == 4
    
    # Verify each type was preserved
    calls = mock_broker.publish.call_args_list
    for c in calls:
        payload = json.loads(c[0][1].decode("utf-8"))
        assert "type" in payload
        assert payload["type"] in ["absolute_uni", "absolute_bi", "delta", "rate"]

@pytest.mark.asyncio
async def test_publisher_publishes_to_target_topics(output_publisher, mock_broker):
    """Test that outputs are published to target.* subjects."""
    outputs = {
        "group1.pan": {"value": 0.5, "type": "delta", "timestamp": 123.0},
        "group2.tilt": {"value": 0.7, "type": "absolute_uni", "timestamp": 124.0}
    }
    
    await output_publisher.publish(outputs)
    
    calls = mock_broker.publish.call_args_list
    subjects = [c[0][0] for c in calls]
    
    assert "target.group1.pan" in subjects
    assert "target.group2.tilt" in subjects

@pytest.mark.asyncio
async def test_publisher_forwards_exact_payload(output_publisher, mock_broker):
    """Test that the exact payload dict is forwarded without modification."""
    original_payload = {"value": 0.6, "type": "delta", "timestamp": 123.0}
    outputs = {"group1.pan": original_payload}
    
    await output_publisher.publish(outputs)
    
    call_args = mock_broker.publish.call_args
    payload_bytes = call_args[0][1]
    payload = json.loads(payload_bytes.decode("utf-8"))
    
    assert payload == original_payload

@pytest.mark.asyncio
async def test_publisher_handles_empty_outputs(output_publisher, mock_broker):
    """Test that empty outputs dict doesn't publish anything."""
    await output_publisher.publish({})
    assert mock_broker.publish.call_count == 0

