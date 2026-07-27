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
    fake_process.poll.return_value = None
    health_check_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        MagicMock(return_value=fake_process),
    )
    monkeypatch.setattr(runtime, "health_check", health_check_mock)

    await runtime.start_server()

    assert runtime.process is fake_process
    assert runtime.is_running()
    assert runtime.port == 4222
    health_check_mock.assert_awaited_once_with(timeout=5)


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
    fake_process.poll.return_value = None  # Process is still running
    # First wait() call times out, second succeeds
    fake_process.wait.side_effect = [
        subprocess.TimeoutExpired(cmd="nats-server", timeout=3),
        None  # Second wait() call succeeds
    ]
    
    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        MagicMock(return_value=fake_process),
    )
    monkeypatch.setattr(runtime, "health_check", AsyncMock(return_value=True))

    await runtime.start_server()
    await runtime.stop_server()

    fake_process.terminate.assert_called_once()
    fake_process.kill.assert_called_once()


@pytest.mark.asyncio
async def test_start_server_fails_on_port_conflict(tmp_path, monkeypatch):
    """Verify that start_server fails cleanly when port is already in use."""
    config = NatsConfig(log_dir=tmp_path, port=18888)
    runtime = NatsRuntimeManager(config)
    
    # Mock _is_port_in_use to return True (port in use)
    monkeypatch.setattr(runtime, "_is_port_in_use", lambda port: True)

    with pytest.raises(RuntimeError, match="already in use"):
        await runtime.start_server()
    
    # Process should not have been created
    assert runtime.process is None
    assert runtime.log_file is None


@pytest.mark.asyncio
async def test_stop_server_cleans_up_even_if_process_already_dead(tmp_path, monkeypatch):
    """Verify that stop_server handles already-dead processes without error."""
    config = NatsConfig(log_dir=tmp_path)
    runtime = NatsRuntimeManager(config)
    
    fake_process = MagicMock()
    fake_process.poll.return_value = 0  # Process already dead (exit code 0)
    fake_process.wait.return_value = None
    
    monkeypatch.setattr(
        "apelios.broker.nats_runtime_manager.subprocess.Popen",
        MagicMock(return_value=fake_process),
    )
    monkeypatch.setattr(runtime, "health_check", AsyncMock(return_value=True))

    await runtime.start_server()
    await runtime.stop_server()
    
    # terminate should not be called for dead process
    fake_process.terminate.assert_not_called()
    assert runtime.process is None
    assert runtime.log_file is None