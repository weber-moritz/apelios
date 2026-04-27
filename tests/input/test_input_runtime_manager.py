# start starts all adapters and marks runtime running.
# start when already started is idempotent (no duplicate starts, no duplicate broker connect).
# stop stops all adapters and marks runtime not running.
# stop when not started is safe and idempotent.
# Injected broker client is used as-is (not replaced internally).
# If no broker is injected, default broker client is created.

# Start failure policy is explicit:
    # either fail-fast and stop partial startup
    # or continue with degraded mode
# Stop failure policy is explicit:
    # one adapter failing stop should not block others.
# Adapter registry behavior:
    # empty adapter list is valid (start/stop still safe).

import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.input.input_runtime_manager import InputRuntimeManager


@pytest.fixture
def mock_broker_client():
    """Mocked broker client for unit tests."""
    mock_broker = MagicMock()
    mock_broker.connect = AsyncMock()
    mock_broker.disconnect = AsyncMock()
    mock_broker.subscribe = AsyncMock()
    mock_broker.publish = AsyncMock()
    return mock_broker

@pytest.mark.asyncio
async def test_runtime_manager_created_with_defaults():
    """ InputRuntimeManager can be instantiated with defaults."""
    runtime = InputRuntimeManager()
    assert runtime is not None
    assert runtime.middleware is not None

@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_broker_client(mock_broker_client):
    """ InputRuntimeManager accepts injected broker client."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    assert runtime.broker_client is mock_broker_client



@pytest.mark.asyncio
async def test_runtime_manager_start_subscribes_to_broker(mock_broker_client):
    """Starting runtime manager subscribes to input subject on broker."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    mock_broker_client.subscribe.assert_awaited_once()
    call_args = mock_broker_client.subscribe.await_args
    assert call_args[0][0] == "input.>"  # subject


@pytest.mark.asyncio
async def test_runtime_manager_stop_is_safe_without_start(mock_broker_client):
    """Stopping runtime manager without starting is safe."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    
    # Should not raise
    await runtime.stop()

@pytest.mark.asyncio
async def test_runtime_manager_start_is_safe_when_already_running(mock_broker_client):
    """Starting runtime manager if alrady running"""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    await runtime.start()
    await runtime.start()

    mock_broker_client.connect.assert_awaited_once()
    mock_broker_client.subscribe.assert_awaited_once()
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_initially_false():
    """ InputRuntimeManager.is_running() is False initially."""
    runtime = InputRuntimeManager()
    assert runtime.is_running() is False


@pytest.mark.asyncio
async def test_runtime_manager_is_running_true_after_start(mock_broker_client):
    """ InputRuntimeManager.is_running() is True after start()."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_false_after_stop(mock_broker_client):
    """ InputRuntimeManager.is_running() is False after stop()."""
    runtime = InputRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    await runtime.stop()
    
    assert runtime.is_running() is False
    

# Start failure policy is explicit:
    # either fail-fast and stop partial startup
    # or continue with degraded mode
# Stop failure policy is explicit:
    # one adapter failing stop should not block others.
# Adapter registry behavior:
    # empty adapter list is valid (start/stop still safe).