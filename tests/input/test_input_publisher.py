import json
import pytest
from apelios.input.input_publisher import InputPublisher

def test_publisher_takes_broker_client_instance(mock_broker_client):
    """Publisher takes the broker client as a valid broker"""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    assert publisher.broker_client is mock_broker_client
    

@pytest.mark.asyncio
async def test_publisher_publishes_correct_subject_and_payload(mock_broker_client):
    """Publisher publishes correct subject and payload with all required fields."""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    await publisher.publish(device="device1", axis="axis1", value=0.1)
    
    # Verify subject is correct
    call_args = mock_broker_client.publish.await_args
    actual_subject = call_args[0][0]
    assert actual_subject == "input.device1.axis1"
    
    # Verify payload structure
    actual_payload = json.loads(call_args[0][1])
    assert actual_payload["source"] == "input.device1.axis1"
    assert actual_payload["value"] == 0.1
    assert actual_payload["type"] == "absolute_uni"  # default type
    assert "timestamp" in actual_payload


@pytest.mark.asyncio
async def test_publisher_includes_type_in_payload(mock_broker_client):
    """Publisher includes type, timestamp, and source in payload."""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    await publisher.publish(device="device1", axis="axis1", value=0.5, type="absolute_uni")
    
    expected_subject = "input.device1.axis1"
    
    # Get the actual call arguments
    call_args = mock_broker_client.publish.await_args
    actual_subject = call_args[0][0]
    actual_payload = json.loads(call_args[0][1])
    
    assert actual_subject == expected_subject
    assert actual_payload["value"] == 0.5
    assert actual_payload["type"] == "absolute_uni"
    assert "timestamp" in actual_payload
    assert actual_payload["source"] == "input.device1.axis1"


@pytest.mark.asyncio
async def test_publisher_uses_correct_topic_format(mock_broker_client):
    """Publisher uses topic format input.<device>.<axis>."""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    await publisher.publish(device="steamdeck", axis="right_stick.x", value=0.75, type="absolute_bi")
    
    # Get the actual call arguments
    call_args = mock_broker_client.publish.await_args
    actual_subject = call_args[0][0]
    actual_payload = json.loads(call_args[0][1])
    
    assert actual_subject == "input.steamdeck.right_stick.x"
    assert actual_payload["source"] == "input.steamdeck.right_stick.x"


@pytest.mark.asyncio
async def test_publisher_includes_source_in_payload(mock_broker_client):
    """Publisher includes source field in payload."""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    await publisher.publish(device="fader", axis="1", value=0.8, type="absolute_uni", source="input.fader.1")
    
    call_args = mock_broker_client.publish.await_args
    actual_payload = json.loads(call_args[0][1])
    
    assert actual_payload["source"] == "input.fader.1"

