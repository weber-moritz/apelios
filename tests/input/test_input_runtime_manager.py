import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.input.adapters import FakeAdapter
from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.input.input_publisher import InputPublisher


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.name = "test_adapter"
    adapter.axis = "joystick1"
    adapter.start = AsyncMock()
    adapter.stop = AsyncMock()
    return adapter


@pytest.mark.asyncio
async def test_register_and_start_adapter_uses_shared_publisher(mock_broker_client):
    """Registering and starting adapters should attach the runtime's publisher."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    adapter = FakeAdapter(device="fake_device")
    runtime.register_adapter(adapter)

    await runtime.start_registered_adapters()

    assert adapter in runtime._running_adapters
    assert hasattr(adapter, "_publisher")
    assert isinstance(adapter._publisher, InputPublisher)
    assert adapter._publisher.broker_client is mock_broker_client


@pytest.mark.asyncio
async def test_runtime_tick_publishes_adapter_snapshot_to_broker(mock_broker_client):
    """An end-to-end tick should call adapter.poll and publish via broker."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    adapter = FakeAdapter(device="fake_device")
    runtime.register_adapter(adapter)

    await runtime.start_registered_adapters()

    await runtime.tick(dt=0.016)

    assert mock_broker_client.publish.await_count == 2

    seen = []
    for call in mock_broker_client.publish.await_args_list:
        subject, msg = call.args
        seen.append((subject, json.loads(msg.decode("utf-8"))))

    # Check payloads include type and timestamp
    for subject, payload in seen:
        assert "source" in payload
        assert "value" in payload
        assert "type" in payload
        assert "timestamp" in payload
    
    # Check specific values with Phase 7 topic and source format
    left_stick_call = next((s, p) for s, p in seen if p["source"] == "input.fake_device.left_stick.x")
    assert left_stick_call[0] == "input.fake_device.left_stick.x"
    assert left_stick_call[1]["value"] == 0.5
    assert left_stick_call[1]["type"] == "absolute_bi"
    
    fader_call = next((s, p) for s, p in seen if p["source"] == "input.fake_device.fader_1")
    assert fader_call[0] == "input.fake_device.fader_1"
    assert fader_call[1]["value"] == 0.75
    assert fader_call[1]["type"] == "absolute_uni"


@pytest.mark.asyncio
async def test_runtime_manager_created_with_defaults():
    """InputRuntimeManager can be instantiated with defaults."""
    runtime = InputRuntimeManager()
    assert runtime is not None
    assert runtime.input_publish_prefix == "input"


@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_broker_client(mock_broker_client):
    """InputRuntimeManager accepts injected broker client."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    assert runtime.broker_client is mock_broker_client


@pytest.mark.asyncio
async def test_runtime_manager_start_connects_to_broker(mock_broker_client):
    """Starting runtime manager connects to broker."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    await runtime.start()

    mock_broker_client.connect.assert_awaited_once()
    mock_broker_client.subscribe.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_manager_stop_is_safe_without_start(mock_broker_client):
    """Stopping runtime manager without starting is safe."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    await runtime.stop()

    mock_broker_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_manager_start_is_safe_when_already_running(mock_broker_client):
    """Starting runtime manager if already running is idempotent."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    await runtime.start()
    await runtime.start()

    mock_broker_client.connect.assert_awaited_once()
    mock_broker_client.subscribe.assert_not_awaited()
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_initially_false():
    """InputRuntimeManager.is_running() is False initially."""
    runtime = InputRuntimeManager()
    assert runtime.is_running() is False


@pytest.mark.asyncio
async def test_runtime_manager_is_running_true_after_start(mock_broker_client):
    """InputRuntimeManager.is_running() is True after start()."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    await runtime.start()

    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_false_after_stop(mock_broker_client):
    """InputRuntimeManager.is_running() is False after stop()."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    await runtime.start()
    await runtime.stop()

    assert runtime.is_running() is False


def test_runtime_manager_register_adapter_added_to_list(mock_broker_client, mock_adapter):
    """Registering a valid adapter stores it in the runtime registry."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    runtime.register_adapter(mock_adapter)

    assert mock_adapter in runtime.registered_adapters


def test_runtime_manager_register_adapter_rejects_invalid(mock_broker_client):
    """Registering an invalid adapter raises a validation error."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    with pytest.raises((TypeError, ValueError)):
        runtime.register_adapter("")


def test_runtime_manager_register_empty_on_start(mock_broker_client):
    """Register list is empty on runtime manager start"""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    assert len(runtime.registered_adapters) == 0


@pytest.mark.asyncio
async def test_runtime_manager_start_adapter(mock_broker_client, mock_adapter):
    """Starting a registered adapter activates it and calls its lifecycle start."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    await runtime.start()

    runtime.register_adapter(mock_adapter)
    await runtime.start_adapter(mock_adapter)

    assert runtime.adapter_is_running(mock_adapter)
    mock_adapter.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_manager_start_registered_adapters_is_safe_when_empty(mock_broker_client):
    """Starting registered adapters is safe when the registry is empty."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    await runtime.start()

    await runtime.start_registered_adapters()


@pytest.mark.asyncio
async def test_runtime_manager_start_registered_adapters_skips_bad_adapters(mock_broker_client):
    """Adapter startup failures are skipped and later adapters still start."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    failing_adapter = MagicMock()
    failing_adapter.start = AsyncMock(side_effect=RuntimeError("adapter failed"))
    failing_adapter.stop = AsyncMock()

    following_adapter = MagicMock()
    following_adapter.start = AsyncMock()
    following_adapter.stop = AsyncMock()

    runtime.register_adapter(failing_adapter)
    runtime.register_adapter(following_adapter)

    await runtime.start()

    await runtime.start_registered_adapters()

    failing_adapter.start.assert_awaited_once()
    following_adapter.start.assert_awaited_once()
    assert failing_adapter in runtime.failed_adapters
    assert runtime.adapter_is_running(following_adapter) is True


@pytest.mark.asyncio
async def test_runtime_manager_stop_registered_adapters_continues_on_error(mock_broker_client):
    """Adapter stop failures do not block stopping the remaining adapters."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    failing_adapter = MagicMock()
    failing_adapter.start = AsyncMock()
    failing_adapter.stop = AsyncMock(side_effect=RuntimeError("stop failed"))

    healthy_adapter = MagicMock()
    healthy_adapter.start = AsyncMock()
    healthy_adapter.stop = AsyncMock()

    runtime.register_adapter(failing_adapter)
    runtime.register_adapter(healthy_adapter)

    await runtime.start()
    await runtime.start_registered_adapters()
    await runtime.stop_registered_adapters()

    failing_adapter.stop.assert_awaited_once()
    healthy_adapter.stop.assert_awaited_once()


def test_runtime_manager_creates_input_publisher_with_broker(mock_broker_client):
    """Runtime manager creates an InputPublisher bound to its broker client."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)

    assert isinstance(runtime.input_publisher, InputPublisher)
    assert runtime.input_publisher.broker_client is mock_broker_client


@pytest.mark.asyncio
async def test_runtime_manager_passes_publisher_to_adapter_on_start(mock_broker_client, mock_adapter):
    """Starting a registered adapter injects the runtime InputPublisher."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    await runtime.start()

    runtime.register_adapter(mock_adapter)
    await runtime.start_adapter(mock_adapter)

    mock_adapter.start.assert_awaited_once_with(input_publisher=runtime.input_publisher)
