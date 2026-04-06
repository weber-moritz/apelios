import subprocess
from unittest.mock import AsyncMock, MagicMock

import pytest

from apelios.broker.config import NatsConfig
from apelios.broker.nats_runtime_manager import NatsRuntimeManager


@pytest.mark.asyncio
async def test_start_server_launches_process_and_waits_for_health(tmp_path, monkeypatch):
    config = NatsConfig(log_dir=tmp_path)
    runtime = NatsRuntimeManager(config) 

    fake_process = MagicMock()
    fake_process.Popen.varialbe = None # <- here
    fake_process.poll.return_value = None
    popen_mock = MagicMock(return_value=fake_process)
    health_check_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        popen_mock,
    )
    monkeypatch.setattr(runtime, "health_check", health_check_mock)

    await runtime.start_server()

    popen_mock.assert_called_once()
    health_check_mock.assert_awaited_once_with(timeout=5)
    assert runtime.process is fake_process
    assert runtime.is_running()
    assert runtime.port == 4222
    
    args, kwargs = popen_mock.call_args
    assert args[0] == ["nats-server", "-p", "4222"]
    assert kwargs["stdout"] is runtime.log_file
    assert kwargs["stderr"] is runtime.log_file


@pytest.mark.asyncio
async def test_stop_server_terminates_process_and_closes_log(tmp_path, monkeypatch):
    config = NatsConfig(log_dir=tmp_path)
    runtime = NatsRuntimeManager(config)
    
    fake_process = MagicMock()
    fake_process.poll.return_value = None
    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        MagicMock(return_value=fake_process),
    )
    monkeypatch.setattr(runtime, "health_check", AsyncMock(return_value=True))

    await runtime.start_server()
    log_file = runtime.log_file
    assert log_file is not None

    await runtime.stop_server()

    fake_process.terminate.assert_called_once()
    fake_process.wait.assert_called_once_with(timeout=3)
    assert fake_process.kill.call_count == 0
    assert runtime.process is None
    assert runtime.log_file is None
    assert log_file.closed
    
    
@pytest.mark.asyncio
async def test_stop_server_kills_if_terminate_times_out(tmp_path, monkeypatch):
    config = NatsConfig(log_dir=tmp_path)
    runtime = NatsRuntimeManager(config) 

    fake_process = MagicMock()
    fake_process.wait.side_effect = subprocess.TimeoutExpired(cmd="nats-server", timeout=3)
    
    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        MagicMock(return_value=fake_process),
    )
    monkeypatch.setattr(runtime, "health_check", AsyncMock(return_value=True))

    await runtime.start_server()
    await runtime.stop_server()

    fake_process.terminate.assert_called_once()
    fake_process.kill.assert_called_once()