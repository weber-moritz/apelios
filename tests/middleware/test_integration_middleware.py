import json
import pytest
from unittest.mock import MagicMock, AsyncMock, call

from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager


@pytest.fixture
def mock_profile():
    """A profile with one absolute fader and one delta mouse to test state memory."""
    return {
        "fader.1": {
            "target": "group1.dimmer", 
            "type": "absolute"
        },
        "mouse.x": {
            "target": "group1.pan", 
            "type": "absolute_to_delta", 
            "sensitivity": 1.0  # 1.0 sensitivity makes the math easy to assert (1:1 delta)
        }
    }


@pytest.fixture
def mock_broker():
    """A perfectly abstracted fake network."""
    mock = MagicMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_full_middleware_signal_flow(mock_profile, mock_broker):
    """
    BLACK BOX TEST: 
    Proves data travels from network -> subscriber -> core -> publisher -> network,
    and proves that the system remembers state between frames.
    """
    
    # ==========================================
    # 1. ARRANGE: Build the Hexagon
    # ==========================================
    real_core = MappingMiddleware(profile=mock_profile)
    
    manager = MiddlewareRuntimeManager(
        middleware=real_core,
        broker_client=mock_broker
    )
    
    # Start the manager to bind the subscriber to the broker
    await manager.start()
    
    # Pytest Trick: Steal the callback function the Manager gave to the mock broker.
    # call_args.args[0] is the subject string ("input.>")
    # call_args.args[1] is the actual subscriber __call__ function
    captured_subscriber_callback = mock_broker.subscribe.call_args.args[1]


    # ==========================================
    # 2. ACT & ASSERT: Tick 1 (Absolute Value)
    # ==========================================
    
    # Simulate network packet arriving
    msg_1 = MagicMock()
    msg_1.data = json.dumps({"source": "fader.1", "value": 0.8}).encode("utf-8")
    captured_subscriber_callback(msg_1)
    
    # Simulate the 60Hz loop ticking once
    await manager.tick()
    
    # Verify the Publisher sent the absolute value to the network
    expected_payload_1 = json.dumps({"value": 0.8}).encode("utf-8")
    mock_broker.publish.assert_any_call("outputs.group1.dimmer", expected_payload_1)


    # ==========================================
    # 3. ACT & ASSERT: Tick 2 & 3 (Delta Math)
    # ==========================================
    
    # Feed an initial mouse position to baseline the Core's memory
    msg_2 = MagicMock()
    msg_2.data = json.dumps({"source": "mouse.x", "value": 100.0}).encode("utf-8")
    captured_subscriber_callback(msg_2)
    await manager.tick()
    
    # Reset the mock's call memory so we only look at the next tick
    mock_broker.publish.reset_mock()
    
    # Move the mouse by +10 units
    msg_3 = MagicMock()
    msg_3.data = json.dumps({"source": "mouse.x", "value": 110.0}).encode("utf-8")
    captured_subscriber_callback(msg_3)
    
    # Process the frame that calculates the difference
    await manager.tick()
    
    # Verify the Publisher successfully sent the calculated delta (10.0)
    expected_payload_delta = json.dumps({"value": 10.0}).encode("utf-8")
    mock_broker.publish.assert_any_call("outputs.group1.pan", expected_payload_delta)