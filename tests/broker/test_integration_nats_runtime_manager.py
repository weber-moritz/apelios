import shutil
import socket
from pathlib import Path


import pytest

from apelios.broker.config import NatsConfig
from apelios.broker.nats_runtime_manager import NatsRuntimeManager


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_start_server_real_subprocess_starts_and_is_healthy(tmp_path):
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    port = _get_free_port()
    nc = NatsConfig(host="127.0.0.1", port=port, log_dir=tmp_path)
    runtime = NatsRuntimeManager(nc)

    try:
        await runtime.start_server()

        assert runtime.process is not None
        assert runtime.process.poll() is None
        assert runtime.is_running()
        assert await runtime.health_check(timeout=2) is True
        assert (tmp_path / "nats-server.log").exists()
    finally:
        await runtime.stop_server()

    assert runtime.process is None
    assert runtime.log_file is None