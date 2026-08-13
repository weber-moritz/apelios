"""Tests for the input layer bootstrap module.

Validates that the bootstrap correctly registers adapters with
the InputRuntimeManager.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from apelios.input.input_runtime_manager import InputRuntimeManager
from apelios.input.input_adapter_bootstrap import InputAdapterBootstrap
from apelios.input.adapters.fake_adapter import FakeAdapter
from apelios.input.adapters.mouse_adapter import MouseAdapter
from apelios.input.adapters.steamdeck_adapter import SteamDeckAdapter


@pytest.mark.asyncio
async def test_bootstrap_registers_adapters(mock_broker_client):
    """Test that bootstrap registers adapters according to configured list."""
    # Create a runtime manager
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)
    
    # Bootstrap with default adapter list
    bootstrap = InputAdapterBootstrap()
    await bootstrap.bootstrap(runtime_manager)

    # Verify that adapters were registered according to the configured adapter_list
    assert len(runtime_manager.registered_adapters) == len(bootstrap.adapter_list)
    # Verify all registered adapters are valid adapter instances
    for adapter in runtime_manager.registered_adapters:
        assert isinstance(adapter, (MouseAdapter, SteamDeckAdapter, FakeAdapter))


@pytest.mark.asyncio
async def test_default_bootstrap_registers_mouse_only(mock_broker_client):
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)

    bootstrap = InputAdapterBootstrap()
    await bootstrap.bootstrap(runtime_manager)

    assert bootstrap.adapter_list == ["mouse"]
    assert [type(adapter) for adapter in runtime_manager.registered_adapters] == [MouseAdapter]


@pytest.mark.asyncio
async def test_bootstrap_with_custom_adapter_list(mock_broker_client):
    """Test that bootstrap respects custom adapter list."""
    # Create a runtime manager
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)
    
    # Bootstrap with only FakeAdapter
    bootstrap = InputAdapterBootstrap(adapter_list=["fake"])
    await bootstrap.bootstrap(runtime_manager)

    # Assert that only FakeAdapter is registered.
    assert len(runtime_manager.registered_adapters) == 1
    assert isinstance(runtime_manager.registered_adapters[0], FakeAdapter)


@pytest.mark.asyncio
async def test_bootstrap_handles_bad_adapter_gracefully(mock_broker_client):
    """Test that bootstrap skips bad adapters and continues with the remaining ones."""
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)

    # Use an explicit two-adapter list so we can prove one fails and one succeeds.
    with patch("apelios.input.input_adapter_bootstrap.FakeAdapter", side_effect=Exception("Adapter failed")):
        bootstrap = InputAdapterBootstrap(adapter_list=["fake", "mouse"])
        await bootstrap.bootstrap(runtime_manager)

    # FakeAdapter failed, MouseAdapter should still be registered.
    assert len(runtime_manager.registered_adapters) == 1
    assert isinstance(runtime_manager.registered_adapters[0], MouseAdapter)


@pytest.mark.asyncio
async def test_bootstrap_ignores_unknown_adapter(mock_broker_client):
    """Test that bootstrap ignores unknown adapter names."""
    # Create a runtime manager
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)

    # Bootstrap with an unknown adapter name
    bootstrap = InputAdapterBootstrap(adapter_list=["unknown_adapter"])
    await bootstrap.bootstrap(runtime_manager)
    
    # Assert that no adapters are registered.
    assert len(runtime_manager.registered_adapters) == 0


@pytest.mark.asyncio
async def test_rtm_start_calls_bootstrap(mock_broker_client):
    """Test that InputRuntimeManager.start() automatically bootstraps adapters."""
    # Create a runtime manager
    runtime_manager = InputRuntimeManager(broker_client=mock_broker_client)
    
    # Start the runtime manager (should call bootstrap internally)
    await runtime_manager.start()
    
    # Verify that adapters were bootstrapped - check that we have adapters registered
    # The exact number depends on the configured default adapter list
    assert len(runtime_manager.registered_adapters) > 0
    # Verify all registered adapters are valid adapter instances
    for adapter in runtime_manager.registered_adapters:
        assert isinstance(adapter, (MouseAdapter, SteamDeckAdapter, FakeAdapter))
