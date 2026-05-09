import json
import pytest
from apelios.input.input_publisher import InputPublisher

def test_publisher_takes_broker_client_instance(mock_broker_client):
    """Publisher takes the broker client as a valid broker"""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    assert publisher.broker_client is mock_broker_client
    

@pytest.mark.asyncio
async def test_publisher_publishes_correct_subject_and_payload(mock_broker_client):
    """Publisher takes the broker client as a valid broker"""
    publisher = InputPublisher(broker_client=mock_broker_client, input_publish_prefix="input")
    
    await publisher.publish(device="device1", axis="axis1", value=0.1)
    
    expected_subject = "input.device1"
    expected_payload = json.dumps({"source":"device1.axis1", "value":0.1}).encode("utf-8")
    
    mock_broker_client.publish.assert_awaited_once_with(expected_subject, expected_payload)

