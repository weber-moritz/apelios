"""Tests for OutputRuntimeManager - TDD Red Phase.

These tests define the expected behavior of the OutputRuntimeManager
before any implementation exists. All tests should fail initially.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apelios.output.output_core import OutputCore
from apelios.output.output_runtime_manager import OutputRuntimeManager


@pytest.fixture
def mock_broker_client():
    """Provide a mocked BrokerClient."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.subscribe = AsyncMock()
    return client


@pytest.fixture
def mock_output_core():
    """Provide a mocked OutputCore."""
    core = MagicMock()
    core.process_frame = AsyncMock()
    core.register_adapter = MagicMock()
    core.adapters = []
    return core


@pytest.fixture
def mock_input_subscriber():
    """Provide a mocked OutputInputSubscriber."""
    return MagicMock()


class TestOutputRuntimeManagerInitialization:
    """Tests for OutputRuntimeManager initialization."""

    def test_runtime_manager_initializes_with_defaults(self):
        """OutputRuntimeManager should create default BrokerClient and OutputCore when none provided."""
        manager = OutputRuntimeManager()
        
        assert manager.broker_client is not None
        assert manager.core is not None
        assert manager.input_subscriber is not None
        assert manager._running is False

    def test_runtime_manager_initializes_with_injected_dependencies(self, mock_broker_client, mock_output_core):
        """OutputRuntimeManager should accept and store injected BrokerClient and OutputCore."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=mock_output_core
        )
        
        assert manager.broker_client is mock_broker_client
        assert manager.core is mock_output_core
        assert manager._running is False


class TestOutputRuntimeManagerStart:
    """Tests for OutputRuntimeManager.start() method."""

    @pytest.mark.asyncio
    async def test_start_connects_to_broker_and_subscribes(self, mock_broker_client, mock_input_subscriber):
        """start() should connect to broker and subscribe to output.> topics."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        manager.input_subscriber = mock_input_subscriber
        
        await manager.start()
        
        mock_broker_client.connect.assert_awaited_once()
        mock_broker_client.subscribe.assert_awaited_once()
        
        # Verify subscribed to correct topic
        subscribe_call = mock_broker_client.subscribe.await_args
        assert subscribe_call.args[0] == "output.>"
        assert subscribe_call.args[1] is mock_input_subscriber
        assert manager._running is True

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, mock_broker_client):
        """Multiple calls to start() should not cause errors or duplicate connections."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        
        await manager.start()
        await manager.start()
        
        # Should only connect once
        mock_broker_client.connect.assert_awaited_once()
        mock_broker_client.subscribe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_is_idempotent_when_already_running(self, mock_broker_client):
        """start() should be a no-op when already running."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        manager._running = True
        
        await manager.start()
        
        # Should not connect again
        mock_broker_client.connect.assert_not_awaited()


class TestOutputRuntimeManagerStop:
    """Tests for OutputRuntimeManager.stop() method."""

    @pytest.mark.asyncio
    async def test_stop_disconnects_and_clears_running(self, mock_broker_client):
        """stop() should disconnect from broker and clear running flag."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        manager._running = True
        
        await manager.stop()
        
        mock_broker_client.disconnect.assert_awaited_once()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_stop_is_idempotent_when_not_running(self, mock_broker_client):
        """stop() should be a no-op when not running."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        
        await manager.stop()
        
        mock_broker_client.disconnect.assert_not_awaited()


class TestOutputRuntimeManagerTick:
    """Tests for OutputRuntimeManager.tick() method."""

    @pytest.mark.asyncio
    async def test_tick_calls_core_process_frame(self, mock_output_core):
        """tick() should call core.process_frame()."""
        manager = OutputRuntimeManager(
            broker_client=MagicMock(),
            core=mock_output_core
        )
        
        await manager.tick(dt=0.016)
        
        mock_output_core.process_frame.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tick_passes_dt_to_core(self, mock_output_core):
        """tick() should pass dt parameter to core.process_frame()."""
        manager = OutputRuntimeManager(
            broker_client=MagicMock(),
            core=mock_output_core
        )
        
        await manager.tick(dt=0.016)
        
        mock_output_core.process_frame.assert_awaited_once_with(dt=0.016)

    @pytest.mark.asyncio
    async def test_tick_with_default_dt(self, mock_output_core):
        """tick() should use default dt when not specified."""
        manager = OutputRuntimeManager(
            broker_client=MagicMock(),
            core=mock_output_core
        )
        
        await manager.tick()
        
        mock_output_core.process_frame.assert_awaited_once()


class TestOutputRuntimeManagerBootstrap:
    """Tests for adapter bootstrap functionality."""

    @pytest.mark.asyncio
    async def test_bootstrap_registers_artnet_adapter(self, mock_broker_client, mock_output_core):
        """start() should bootstrap and register the ArtNet adapter."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=mock_output_core
        )
        
        await manager.start()
        
        # Check that adapters were registered with the core
        mock_output_core.register_adapter.assert_called()


class TestOutputRuntimeManagerState:
    """Tests for runtime manager state management."""

    def test_is_running_returns_false_when_stopped(self):
        """is_running() should return False when not running."""
        manager = OutputRuntimeManager()
        
        assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_is_running_returns_true_after_start(self, mock_broker_client):
        """is_running() should return True after start()."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        
        await manager.start()
        
        assert manager.is_running() is True

    @pytest.mark.asyncio
    async def test_is_running_returns_false_after_stop(self, mock_broker_client):
        """is_running() should return False after stop()."""
        manager = OutputRuntimeManager(
            broker_client=mock_broker_client,
            core=OutputCore()
        )
        
        await manager.start()
        await manager.stop()
        
        assert manager.is_running() is False