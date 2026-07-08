"""Tests for OutputRuntimeManager - TDD Red Phase.

These tests define the expected behavior of the OutputRuntimeManager
before any implementation exists. All tests should fail initially.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOutputRuntimeManagerInitialization:
    """Tests for OutputRuntimeManager initialization."""

    @pytest.fixture
    def mock_broker_client(self):
        """Provide a mocked BrokerClient."""
        client = MagicMock()
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.subscribe = AsyncMock()
        return client

    @pytest.fixture
    def mock_output_core(self):
        """Provide a mocked OutputCore."""
        core = MagicMock()
        core.process_frame = MagicMock()
        core.register_adapter = MagicMock()
        core.adapters = []
        return core

    def test_runtime_manager_initializes_with_defaults(self, mock_broker_client):
        """OutputRuntimeManager should create default BrokerClient and OutputCore when none provided."""
        # Import here to avoid issues if module doesn't exist yet
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    
                    manager = OutputRuntimeManager()
                    
                    assert manager.broker_client is not None
                    assert manager.core is not None
                    assert manager.input_subscriber is not None
                    assert manager._running is False

    def test_runtime_manager_initializes_with_injected_dependencies(self, mock_broker_client, mock_output_core):
        """OutputRuntimeManager should accept and store injected BrokerClient and OutputCore."""
        with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
            from apelios.output.output_runtime_manager import OutputRuntimeManager
            
            manager = OutputRuntimeManager(
                broker_client=mock_broker_client,
                core=mock_output_core
            )
            
            assert manager.broker_client is mock_broker_client
            assert manager.core is mock_output_core
            assert manager._running is False


class TestOutputRuntimeManagerStart:
    """Tests for OutputRuntimeManager.start() method."""

    @pytest.fixture
    def manager_with_mocks(self, mock_broker_client):
        """Provide a manager with mocked dependencies."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore') as MockCore:
                mock_core = MagicMock()
                mock_core.process_frame = MagicMock()
                MockCore.return_value = mock_core
                
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    return OutputRuntimeManager()

    @pytest.mark.asyncio
    async def test_start_connects_to_broker_and_subscribes(self, mock_broker_client):
        """start() should connect to broker and subscribe to output.> topics."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()) as mock_subscriber_class:
                    mock_subscriber = MagicMock()
                    mock_subscriber_class.return_value = mock_subscriber
                    
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    await manager.start()
                    
                    mock_broker_client.connect.assert_awaited_once()
                    mock_broker_client.subscribe.assert_awaited_once()
                    
                    # Verify subscribed to correct topic
                    subscribe_call = mock_broker_client.subscribe.await_args
                    assert subscribe_call.args[0] == "output.>"
                    assert subscribe_call.args[1] is mock_subscriber
                    assert manager._running is True

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, mock_broker_client):
        """Multiple calls to start() should not cause errors or duplicate connections."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    await manager.start()
                    await manager.start()
                    
                    # Should only connect once
                    mock_broker_client.connect.assert_awaited_once()
                    mock_broker_client.subscribe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_is_idempotent_when_already_running(self, mock_broker_client):
        """start() should be a no-op when already running."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    manager._running = True
                    
                    await manager.start()
                    
                    # Should not connect again
                    mock_broker_client.connect.assert_not_awaited()


class TestOutputRuntimeManagerStop:
    """Tests for OutputRuntimeManager.stop() method."""

    @pytest.fixture
    def started_manager(self, mock_broker_client):
        """Provide a started manager."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    manager._running = True
                    return manager

    @pytest.mark.asyncio
    async def test_stop_disconnects_and_clears_running(self, started_manager, mock_broker_client):
        """stop() should disconnect from broker and clear running flag."""
        await started_manager.stop()
        
        mock_broker_client.disconnect.assert_awaited_once()
        assert started_manager._running is False

    @pytest.mark.asyncio
    async def test_stop_is_idempotent_when_not_running(self, mock_broker_client):
        """stop() should be a no-op when not running."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    await manager.stop()
                    
                    mock_broker_client.disconnect.assert_not_awaited()


class TestOutputRuntimeManagerTick:
    """Tests for OutputRuntimeManager.tick() method."""

    @pytest.fixture
    def manager_with_core(self, mock_broker_client):
        """Provide a manager with a mock core."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore') as MockCore:
                mock_core = MagicMock()
                mock_core.process_frame = MagicMock()
                MockCore.return_value = mock_core
                
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    return manager, mock_core

    @pytest.mark.asyncio
    async def test_tick_calls_core_process_frame(self, manager_with_core):
        """tick() should call core.process_frame()."""
        manager, mock_core = manager_with_core
        
        await manager.tick(dt=0.016)
        
        mock_core.process_frame.assert_called_once()

    @pytest.mark.asyncio
    async def test_tick_passes_dt_to_core(self, manager_with_core):
        """tick() should pass dt parameter to core.process_frame()."""
        manager, mock_core = manager_with_core
        
        await manager.tick(dt=0.016)
        
        mock_core.process_frame.assert_called_once_with(dt=0.016)

    @pytest.mark.asyncio
    async def test_tick_with_default_dt(self, manager_with_core):
        """tick() should use default dt when not specified."""
        manager, mock_core = manager_with_core
        
        await manager.tick()
        
        mock_core.process_frame.assert_called_once()


class TestOutputRuntimeManagerBootstrap:
    """Tests for adapter bootstrap functionality."""

    @pytest.mark.asyncio
    async def test_bootstrap_registers_artnet_adapter(self, mock_broker_client):
        """start() should bootstrap and register the ArtNet adapter."""
        mock_core = MagicMock()
        mock_core.register_adapter = MagicMock()
        
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=mock_core):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    with patch('apelios.output.output_runtime_manager.OutputAdapterBootstrap') as mock_bootstrap:
                        mock_bootstrap_instance = MagicMock()
                        mock_bootstrap.return_value = mock_bootstrap_instance
                        mock_bootstrap_instance.bootstrap = AsyncMock()
                        
                        from apelios.output.output_runtime_manager import OutputRuntimeManager
                        manager = OutputRuntimeManager()
                        
                        await manager.start()
                        
                        mock_bootstrap.assert_called_once()
                        mock_bootstrap_instance.bootstrap.assert_awaited_once_with(manager)


class TestOutputRuntimeManagerState:
    """Tests for runtime manager state management."""

    def test_is_running_returns_false_when_stopped(self, mock_broker_client):
        """is_running() should return False when not running."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    assert manager.is_running() is False

    @pytest.mark.asyncio
    async def test_is_running_returns_true_after_start(self, mock_broker_client):
        """is_running() should return True after start()."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    await manager.start()
                    
                    assert manager.is_running() is True

    @pytest.mark.asyncio
    async def test_is_running_returns_false_after_stop(self, mock_broker_client):
        """is_running() should return False after stop()."""
        with patch('apelios.output.output_runtime_manager.BrokerClient', return_value=mock_broker_client):
            with patch('apelios.output.output_runtime_manager.OutputCore', return_value=MagicMock()):
                with patch('apelios.output.output_runtime_manager.OutputInputSubscriber', return_value=MagicMock()):
                    from apelios.output.output_runtime_manager import OutputRuntimeManager
                    manager = OutputRuntimeManager()
                    
                    await manager.start()
                    await manager.stop()
                    
                    assert manager.is_running() is False
