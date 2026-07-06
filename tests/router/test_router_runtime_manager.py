import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.router.router_core import MappingRouter
from apelios.router.router_runtime_manager import RouterRuntimeManager


@pytest.fixture
def mock_profile():
    """Standard mock profile for testing (with intent field)."""
    return {
        "fader.1": {
            "target": "group1.dimmer",
            "intent": "absolute"
        },
        "mouse.x": {
            "target": "group1.pan",
            "intent": "delta",
            "sensitivity": 0.01
        }
    }


@pytest.fixture
def mock_broker_client():
    """Mocked broker client for unit tests."""
    mock_broker = MagicMock()
    mock_broker.connect = AsyncMock()
    mock_broker.disconnect = AsyncMock()
    mock_broker.subscribe = AsyncMock()
    mock_broker.publish = AsyncMock()
    return mock_broker


@pytest.fixture
def router_core(mock_profile):
    """MappingRouter instance with mock profile."""
    return MappingRouter(profile=mock_profile)


@pytest.mark.asyncio
async def test_runtime_manager_created_with_defaults():
    """RouterRuntimeManager can be instantiated with defaults."""
    runtime = RouterRuntimeManager()
    assert runtime is not None
    assert runtime.router is not None


@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_core(router_core):
    """RouterRuntimeManager accepts injected MappingRouter."""
    runtime = RouterRuntimeManager(router=router_core)
    assert runtime.router is router_core


@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_broker_client(mock_broker_client):
    """RouterRuntimeManager accepts injected broker client."""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    assert runtime.broker_client is mock_broker_client


@pytest.mark.asyncio
async def test_runtime_manager_start_subscribes_to_broker(mock_broker_client):
    """Starting runtime manager subscribes to input subject on broker."""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    mock_broker_client.subscribe.assert_awaited_once()
    call_args = mock_broker_client.subscribe.await_args
    assert call_args[0][0] == "input.>"  # subject


@pytest.mark.asyncio
async def test_runtime_manager_stop_is_safe_without_start(mock_broker_client):
    """Stopping runtime manager without starting is safe."""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    
    # Should not raise
    await runtime.stop()

@pytest.mark.asyncio
async def test_runtime_manager_start_is_safe_when_already_running(mock_broker_client):
    """Starting runtime manager if alrady running"""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    await runtime.start()
    await runtime.start()

    mock_broker_client.connect.assert_awaited_once()
    mock_broker_client.subscribe.assert_awaited_once()
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_initially_false():
    """RouterRuntimeManager.is_running() is False initially."""
    runtime = RouterRuntimeManager()
    assert runtime.is_running() is False


@pytest.mark.asyncio
async def test_runtime_manager_is_running_true_after_start(mock_broker_client):
    """RouterRuntimeManager.is_running() is True after start()."""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_false_after_stop(mock_broker_client):
    """RouterRuntimeManager.is_running() is False after stop()."""
    runtime = RouterRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    await runtime.stop()
    
    assert runtime.is_running() is False


def test_runtime_manager_default_profile_includes_steamdeck_axes():
    """The default router profile should include the Steam Deck controller axes."""
    runtime = RouterRuntimeManager()

    profile = runtime.router.profile

    assert "steamdeck.right_stick.x" in profile
    assert "steamdeck.right_stick.y" in profile
    assert "steamdeck.imu.pitch" in profile
    assert "steamdeck.imu.yaw" in profile
    assert "steamdeck.imu.roll" in profile


@pytest.mark.asyncio
async def test_runtime_manager_tick_publishes_outputs(mock_broker_client):
    """Test that tick() processes inputs and publishes outputs immediately."""
    from apelios.router.router_input_subscriber import RouterInputSubscriber
    
    # Create router with simple profile - maps source string to target
    profile = {
        "test.device.axis": "group1.pan"
    }
    core = MappingRouter(profile=profile)
    
    runtime = RouterRuntimeManager(
        router=core,
        broker_client=mock_broker_client
    )
    
    await runtime.start()
    
    # Simulate an input message arriving
    mock_msg = MagicMock()
    mock_msg.data = json.dumps({
        "source": "test.device.axis",
        "value": 0.5,
        "type": "delta",
        "timestamp": 123.0
    }).encode("utf-8")
    
    # Get the subscriber callback
    sub_callback = mock_broker_client.subscribe.call_args.args[1]
    await sub_callback(mock_msg)
    
    # Tick should process and publish
    await runtime.tick(dt=0.016)
    
    # Verify output was published
    assert mock_broker_client.publish.call_count >= 1
    
    # Check that type was forwarded
    calls = mock_broker_client.publish.call_args_list
    for call in calls:
        subject = call[0][0]
        payload_bytes = call[0][1]
        payload = json.loads(payload_bytes.decode("utf-8"))
        if subject == "target.group1.pan":
            assert payload["value"] == 0.5
            assert payload["type"] == "delta"
            assert payload["timestamp"] == 123.0
            break


@pytest.mark.asyncio
async def test_runtime_manager_stateless(mock_broker_client):
    """Test that runtime manager doesn't maintain state between ticks."""
    profile = {
        "test.axis": "group1.param"
    }
    core = MappingRouter(profile=profile)
    runtime = RouterRuntimeManager(
        router=core,
        broker_client=mock_broker_client
    )
    
    await runtime.start()
    
    # Process first input
    mock_msg1 = MagicMock()
    mock_msg1.data = json.dumps({
        "source": "test.axis",
        "value": 0.5,
        "type": "absolute_uni",
        "timestamp": 100.0
    }).encode("utf-8")
    
    sub_callback = mock_broker_client.subscribe.call_args.args[1]
    await sub_callback(mock_msg1)
    await runtime.tick(dt=0.016)
    
    # Reset mock
    mock_broker_client.publish.reset_mock()
    
    # Process second input - should not depend on first
    mock_msg2 = MagicMock()
    mock_msg2.data = json.dumps({
        "source": "test.axis",
        "value": 0.8,
        "type": "absolute_uni",
        "timestamp": 200.0
    }).encode("utf-8")
    
    await sub_callback(mock_msg2)
    await runtime.tick(dt=0.016)
    
    # Verify second value was published, not first
    assert mock_broker_client.publish.call_count >= 1
    calls = mock_broker_client.publish.call_args_list
    for call in calls:
        payload = json.loads(call[0][1].decode("utf-8"))
        assert payload["value"] == 0.8
        assert payload["timestamp"] == 200.0