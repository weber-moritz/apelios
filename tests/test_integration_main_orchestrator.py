import shutil
import socket
from pathlib import Path

import pytest

from apelios.main_orchestrator import MainOrchestrator
from apelios.broker.config import NatsConfig
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_orchestrator_starts_and_manages_real_nats(tmp_path):
    """Verify MainOrchestrator can start/stop real NATS via BrokerRuntimeManager."""
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    port = _get_free_port()
    config = NatsConfig(host="127.0.0.1", port=port, log_dir=tmp_path)
    
    # Create orchestrator with real broker manager (not mocked)
    broker_manager = BrokerRuntimeManager(provider="nats")
    orchestrator = MainOrchestrator(broker_manager=broker_manager)

    try:
        # Start the orchestrator
        await orchestrator.start()
        
        # Verify it's running
        assert orchestrator.is_running()
        
        # Health check should pass
        assert await orchestrator.health_check(timeout=3) is True
    finally:
        # Cleanup
        await orchestrator.stop()

    # Verify it stopped
    assert not orchestrator.is_running()


@pytest.mark.asyncio
async def test_orchestrator_stop_without_start_is_safe():
    """Verify stopping orchestrator that never started doesn't crash."""
    broker_manager = BrokerRuntimeManager(provider="nats")
    orchestrator = MainOrchestrator(broker_manager=broker_manager)
    
    # Should not raise
    await orchestrator.stop()
    
    assert not orchestrator.is_running()