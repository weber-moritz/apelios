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
def mock_dict():
    # The dictionary provided by the Core
    return {"group1.pan": 0.6}

@pytest.fixture
def mock_multi_dict():
    return {"group1.pan": 0.6, "group1.tilt": 0.1, "group2.dim": 0.0}

@pytest.fixture
def mock_mixed_dict():
    # 0 is technically an int, but json.dumps will handle it perfectly fine!
    return {"group1.pan": "some text", "group1.tilt": 0, "group2.dim": 0.0}

@pytest.fixture
def output_publisher(mock_broker):
    return MiddlewareOutputPublisher(broker=mock_broker)

@pytest.mark.asyncio
async def test_publisher_calls_broker_publish(output_publisher, mock_broker, mock_dict):
    # 1. ACT: Hand the dictionary to the publisher
    await output_publisher.publish(mock_dict)

    # 2. EXPECTED PAYLOAD: How it should look over the network
    expected_subject = "outputs.group1.pan"
    expected_payload = json.dumps({"value": 0.6}).encode("utf-8")

    # 3. ASSERT: Did the Publisher format it correctly as bytes before calling the broker?
    mock_broker.publish.assert_called_once_with(expected_subject, expected_payload)

@pytest.mark.asyncio
async def test_publisher_calls_broker_publish_multi_dict(output_publisher, mock_broker, mock_multi_dict):
    await output_publisher.publish(mock_multi_dict)

    # Build a list of the exact function calls we expect to happen
    expected_calls = [
        call("outputs.group1.pan", json.dumps({"value": 0.6}).encode("utf-8")),
        call("outputs.group1.tilt", json.dumps({"value": 0.1}).encode("utf-8")),
        call("outputs.group2.dim", json.dumps({"value": 0.0}).encode("utf-8"))
    ]

    # Did it loop 3 times?
    assert mock_broker.publish.call_count == 3
    
    # Did it send the right data each time? (any_order=True is helpful because dictionaries don't always guarantee order)
    mock_broker.publish.assert_has_calls(expected_calls, any_order=True)


@pytest.mark.asyncio
async def test_publisher_calls_broker_publish_mixed_dict(output_publisher, mock_broker, mock_mixed_dict):
    await output_publisher.publish(mock_mixed_dict)

    expected_calls = [
        call("outputs.group1.tilt", json.dumps({"value": 0.0}).encode("utf-8")),
        call("outputs.group2.dim", json.dumps({"value": 0.0}).encode("utf-8"))
    ]

    # Fixed typo here: call_count
    assert mock_broker.publish.call_count == 2

    mock_broker.publish.assert_has_calls(expected_calls, any_order=True)

@pytest.mark.asyncio
async def test_publisher_handles_broker_exception(output_publisher, mock_broker, mock_dict):
    # This arms the trap. The next time someone calls publish(), it will explode.
    mock_broker.publish.side_effect = Exception("Simulated NATS Connection Drop")
    
    await output_publisher.publish(mock_dict)
    #no assert, as it will work or fail depending on the outcome?

