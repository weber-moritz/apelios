import shutil
import pytest

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager


@pytest.mark.asyncio
async def test_broker_runtime_manager_starts_real_nats():
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    manager = BrokerRuntimeManager(provider="nats")

    try:
        await manager.start_server()
        assert manager.is_running()
        assert await manager.health_check(timeout=3) is True
    finally:
        await manager.stop_server()

    assert not manager.is_running()