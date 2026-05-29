import json
import pytest
from unittest.mock import MagicMock, AsyncMock, call
from apelios.middleware.middleware_output_publisher import MiddlewareOutputPublisher

@pytest.fixture
def mock_broker():
    mock = MagicMock()
    mock.publish = AsyncMock()
    return mock

@pytest.fixture
def output_publisher(mock_broker):
    return MiddlewareOutputPublisher(broker=mock_broker)

@pytest.mark.asyncio
async def test_publisher_publishes_enriched_payloads_to_target(output_publisher, mock_broker):
    """Test that enriched payloads are published to target.* subjects."""
    enriched_outputs = {
        "group1.pan": {
            "target": "group1.pan",
            "value": 0.6,
            "intent": "delta",
            "timestamp": 1234567890.123
        },
        "group1.tilt": {
            "target": "group1.tilt",
            "value": 0.1,
            "intent": "absolute",
            "timestamp": 1234567890.124
        }
    }
    
    await output_publisher.publish_enriched(enriched_outputs)
    
    # Should publish to target.* for each enriched payload
    # That's 2 payloads = 2 publish calls
    assert mock_broker.publish.call_count == 2
    
    # Verify that target.* subjects were called
    calls = mock_broker.publish.call_args_list
    subjects_called = [call[0][0] for call in calls]
    
    assert "target.group1.pan" in subjects_called
    assert "target.group1.tilt" in subjects_called


@pytest.mark.asyncio
async def test_publisher_enriched_payload_structure(output_publisher, mock_broker):
    """Test that enriched payload JSON is correctly serialized."""
    enriched_outputs = {
        "movinghead01.pan": {
            "target": "movinghead01.pan",
            "value": 0.75,
            "intent": "rate",
            "timestamp": 1234567890.123
        }
    }
    
    await output_publisher.publish_enriched(enriched_outputs)
    
    # Get the calls
    calls = mock_broker.publish.call_args_list
    
    # Find the call to target.* (first call should be target.*)
    target_call = next(c for c in calls if c[0][0] == "target.movinghead01.pan")
    
    # Verify the payload is the enriched JSON
    payload_bytes = target_call[0][1]
    payload_json = json.loads(payload_bytes.decode("utf-8"))
    
    assert payload_json["target"] == "movinghead01.pan"
    assert payload_json["value"] == 0.75
    assert payload_json["intent"] == "rate"
    assert "timestamp" in payload_json

