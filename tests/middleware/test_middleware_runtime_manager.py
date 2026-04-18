import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_runtime_manager import MiddlewareRuntimeManager


@pytest.fixture
def mock_profile():
    """Standard mock profile for testing."""
    return {
        "fader.1": {
            "target": "group1.dimmer",
            "type": "absolute"
        },
        "mouse.x": {
            "target": "group1.pan",
            "type": "absolute_to_delta",
            "sensitivity": 0.01
        }
    }


@pytest.fixture
def mock_broker_client():
    """Mocked broker client for unit tests."""
    mock = MagicMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
def middleware_core(mock_profile):
    """MappingMiddleware instance with mock profile."""
    return MappingMiddleware(profile=mock_profile)


@pytest.mark.asyncio
async def test_runtime_manager_created_with_defaults():
    """MiddlewareRuntimeManager can be instantiated with defaults."""
    runtime = MiddlewareRuntimeManager()
    assert runtime is not None
    assert runtime.middleware is not None


@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_core(middleware_core):
    """MiddlewareRuntimeManager accepts injected MappingMiddleware."""
    runtime = MiddlewareRuntimeManager(middleware=middleware_core)
    assert runtime.middleware is middleware_core


@pytest.mark.asyncio
async def test_runtime_manager_created_with_injected_broker(mock_broker_client):
    """MiddlewareRuntimeManager accepts injected broker client."""
    runtime = MiddlewareRuntimeManager(broker_client=mock_broker_client)
    assert runtime.broker_client is mock_broker_client


@pytest.mark.asyncio
async def test_runtime_manager_start_subscribes_to_broker(mock_broker_client):
    """Starting runtime manager subscribes to input subject on broker."""
    runtime = MiddlewareRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    mock_broker_client.subscribe.assert_awaited_once()
    call_args = mock_broker_client.subscribe.await_args
    assert call_args[0][0] == "input.>"  # subject


@pytest.mark.asyncio
async def test_runtime_manager_stop_is_safe_without_start(mock_broker_client):
    """Stopping runtime manager without starting is safe."""
    runtime = MiddlewareRuntimeManager(broker_client=mock_broker_client)
    
    # Should not raise
    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_manager_is_running_initially_false():
    """MiddlewareRuntimeManager.is_running() is False initially."""
    runtime = MiddlewareRuntimeManager()
    assert runtime.is_running() is False


@pytest.mark.asyncio
async def test_runtime_manager_is_running_true_after_start(mock_broker_client):
    """MiddlewareRuntimeManager.is_running() is True after start()."""
    runtime = MiddlewareRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    
    assert runtime.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_is_running_false_after_stop(mock_broker_client):
    """MiddlewareRuntimeManager.is_running() is False after stop()."""
    runtime = MiddlewareRuntimeManager(broker_client=mock_broker_client)
    
    await runtime.start()
    await runtime.stop()
    
    assert runtime.is_running() is False