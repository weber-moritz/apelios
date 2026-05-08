import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from apelios.input.input_publisher import InputPublisher

@pytest.fixture
def mock_broker():
    mock = MagicMock()
    mock.publish = AsyncMock()
    return mock

def test_publsiher_takes_broker_client_instance(mock_broker):
    """Publisher takes the broker client as a valid broker"""
    publisher = InputPublisher(broker_client=mock_broker, input_publish_prefix="input")
    
    assert publisher.broker_client is mock_broker
    

@pytest.mark.asyncio
async def test_publisher_sends_correct_subject_and_payload(mock_broker):
    """Publisher takes the broker client as a valid broker"""
    publisher = InputPublisher(broker_client=mock_broker, input_publish_prefix="input")
    
    await publisher.send(device="device1", axis="axis1", value=0.1)
    
    expected_subject = "input.device1"
    expected_payload = json.dumps({"axis":"axis1", "value":0.1}).encode("utf-8")
    
    mock_broker.publish.assert_awaited_once_with(expected_subject, expected_payload)

