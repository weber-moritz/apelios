from unittest.mock import AsyncMock, MagicMock

import pytest

from apelios.broker.broker_runtime_manager import BrokerRuntimeManager


def test_unsupported_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported broker provider"):
        BrokerRuntimeManager(provider="redis")


def test_nats_provider_builds_runtime(monkeypatch):
    fake_runtime = MagicMock()
    nats_runtime_cls = MagicMock(return_value=fake_runtime)

    monkeypatch.setattr(
        "apelios.broker.broker_runtime_manager.NatsRuntimeManager",
        nats_runtime_cls,
    )

    manager = BrokerRuntimeManager(provider="nats")

    nats_runtime_cls.assert_called_once_with()
    assert manager._runtime is fake_runtime


@pytest.mark.asyncio
async def test_start_server_delegates_to_runtime(monkeypatch):
    fake_runtime = MagicMock()
    fake_runtime.start_server = AsyncMock()
    monkeypatch.setattr(
        "apelios.broker.broker_runtime_manager.NatsRuntimeManager",
        MagicMock(return_value=fake_runtime),
    )

    manager = BrokerRuntimeManager(provider="nats")
    await manager.start_server()

    fake_runtime.start_server.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_server_delegates_to_runtime(monkeypatch):
    fake_runtime = MagicMock()
    fake_runtime.stop_server = AsyncMock()
    monkeypatch.setattr(
        "apelios.broker.broker_runtime_manager.NatsRuntimeManager",
        MagicMock(return_value=fake_runtime),
    )

    manager = BrokerRuntimeManager(provider="nats")
    await manager.stop_server()

    fake_runtime.stop_server.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_delegates_and_returns_value(monkeypatch):
    fake_runtime = MagicMock()
    fake_runtime.health_check = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "apelios.broker.broker_runtime_manager.NatsRuntimeManager",
        MagicMock(return_value=fake_runtime),
    )

    manager = BrokerRuntimeManager(provider="nats")
    result = await manager.health_check(timeout=7)

    fake_runtime.health_check.assert_awaited_once_with(timeout=7)
    assert result is True


def test_is_running_delegates_and_returns_value(monkeypatch):
    fake_runtime = MagicMock()
    fake_runtime.is_running.return_value = True
    monkeypatch.setattr(
        "apelios.broker.broker_runtime_manager.NatsRuntimeManager",
        MagicMock(return_value=fake_runtime),
    )

    manager = BrokerRuntimeManager(provider="nats")
    assert manager.is_running() is True
    fake_runtime.is_running.assert_called_once()