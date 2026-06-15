import json
import pytest
from unittest.mock import MagicMock, AsyncMock, call

from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager


@pytest.fixture
def mock_profile():
    """A profile with one absolute fader and one delta mouse (passthrough in MVP)."""
    return {
        "fader.1": "group1.dimmer",
        "mouse.x": "group1.pan",
    }


@pytest.fixture
def mock_broker():
    """A perfectly abstracted fake network."""
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_full_middleware_signal_flow(mock_profile, mock_broker):
    """
    BLACK BOX TEST: 
    Proves data travels from network -> subscriber -> core -> publisher -> network.
    Middleware now acts as a pure passthrough router (no math).
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
    # 2. ACT & ASSERT: Tick 1 (Absolute passthrough)
    # ==========================================

    # Simulate network packet arriving
    msg_1 = MagicMock()
    msg_1.data = json.dumps({"source": "fader.1", "value": 0.8, "type": "absolute_uni", "timestamp": 1234567890.0}).encode("utf-8")
    
    # FIX: Await the callback because it is now an async function
    await captured_subscriber_callback(msg_1)

    # Simulate the 60Hz loop ticking once
    await manager.tick(dt=0.016)

    # Verify the Publisher sent enriched payload to target.*
    calls = mock_broker.publish.call_args_list
    assert any(
        c[0][0] == "target.group1.dimmer" for c in calls
    ), "Expected publish to target.group1.dimmer"


    # ==========================================
    # 3. ACT & ASSERT: Tick 2 (Delta passthrough - no math)
    # ==========================================
    
    # Reset the mock's call memory
    mock_broker.publish.reset_mock()
    
    # Send a delta value (middleware will just pass it through unchanged)
    msg_2 = MagicMock()
    msg_2.data = json.dumps({"source": "mouse.x", "value": 0.5, "type": "delta", "timestamp": 1234567890.0}).encode("utf-8")
    await captured_subscriber_callback(msg_2)
    
    # Process the frame
    await manager.tick()
    
    # Verify the Publisher sent the passthrough value to target.* (NO DELTA MATH APPLIED)
    calls = mock_broker.publish.call_args_list
    assert any(
        c[0][0] == "target.group1.pan" for c in calls
    ), "Expected publish to target.group1.pan"