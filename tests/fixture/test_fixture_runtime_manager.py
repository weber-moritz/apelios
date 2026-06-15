from unittest.mock import AsyncMock, MagicMock

import pytest

from apelios.fixture.fixture_core import FixtureCore
from apelios.fixture.fixture_runtime_manager import FixtureRuntimeManager


@pytest.fixture
def patch_config():
    return {
        "fixtures": {
            "movinghead01": {
                "type": "robe_robospot",
                "universe": 2,
                "address": 10,
                "parameters": {
                    "pan": {
                        "type": "absolute_uni",
                        "width": 16,
                        "limits": [0.0, 1.0],
                    }
                },
            }
        }
    }


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.connect = AsyncMock()
    broker.disconnect = AsyncMock()
    broker.subscribe = AsyncMock()
    return broker


@pytest.fixture
def mock_core(patch_config):
    return FixtureCore(patch=patch_config)


@pytest.fixture
def runtime_manager(mock_core, mock_broker):
    return FixtureRuntimeManager(core=mock_core, broker_client=mock_broker)


def test_runtime_manager_initializes_with_injected_core(runtime_manager, mock_core):
    assert runtime_manager.core is mock_core
    assert runtime_manager.is_running() is False


@pytest.mark.asyncio
async def test_runtime_manager_start_subscribes_to_target_subjects(runtime_manager, mock_broker):
    await runtime_manager.start()

    mock_broker.connect.assert_awaited_once()
    mock_broker.subscribe.assert_awaited_once()
    assert mock_broker.subscribe.await_args.args[0] == "target.>"
    assert runtime_manager.is_running() is True


@pytest.mark.asyncio
async def test_runtime_manager_start_is_idempotent(runtime_manager, mock_broker):
    await runtime_manager.start()
    await runtime_manager.start()

    mock_broker.connect.assert_awaited_once()
    mock_broker.subscribe.assert_awaited_once()


@pytest.mark.asyncio
async def test_runtime_manager_tick_processes_core_then_publishes(runtime_manager, mock_core):
    mock_core.process_frame = MagicMock()
    runtime_manager.output_module.publish_dmx = AsyncMock()
    mock_core.dmx_output = {(2, 10): 135}

    await runtime_manager.tick(dt=0.016)

    mock_core.process_frame.assert_called_once_with(dt=0.016)
    runtime_manager.output_module.publish_dmx.assert_awaited_once_with({(2, 10): 135})


@pytest.mark.asyncio
async def test_runtime_manager_stop_disconnects_and_clears_running(runtime_manager, mock_broker):
    await runtime_manager.start()
    await runtime_manager.stop()

    mock_broker.disconnect.assert_awaited_once()
    assert runtime_manager.is_running() is False