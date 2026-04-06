from unittest.mock import AsyncMock, MagicMock

import pytest

from apelios.broker.broker_client import BrokerClient


def test_unsupported_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported broker provider"):
        BrokerClient(provider="redis")


def test_nats_provider_builds_client(monkeypatch):
    fake_client = MagicMock()
    nats_client_cls = MagicMock(return_value=fake_client)

    monkeypatch.setattr(
        "apelios.broker.broker_client.NatsClient",
        nats_client_cls,
    )

    client = BrokerClient(provider="nats")

    nats_client_cls.assert_called_once_with(config=None)
    assert client._client is fake_client


@pytest.mark.asyncio
async def test_connect_delegates(monkeypatch):
    fake_client = MagicMock()
    fake_client.connect = AsyncMock()

    monkeypatch.setattr(
        "apelios.broker.broker_client.NatsClient",
        MagicMock(return_value=fake_client),
    )

    client = BrokerClient(provider="nats")
    await client.connect()

    fake_client.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_delegates(monkeypatch):
    fake_client = MagicMock()
    fake_client.disconnect = AsyncMock()

    monkeypatch.setattr(
        "apelios.broker.broker_client.NatsClient",
        MagicMock(return_value=fake_client),
    )

    client = BrokerClient(provider="nats")
    await client.disconnect()

    fake_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_delegates(monkeypatch):
    fake_client = MagicMock()
    fake_client.publish = AsyncMock()

    monkeypatch.setattr(
        "apelios.broker.broker_client.NatsClient",
        MagicMock(return_value=fake_client),
    )

    client = BrokerClient(provider="nats")
    await client.publish("demo.subject", b"payload")

    fake_client.publish.assert_awaited_once_with("demo.subject", b"payload")


@pytest.mark.asyncio
async def test_subscribe_delegates(monkeypatch):
    fake_client = MagicMock()
    fake_client.subscribe = AsyncMock()

    monkeypatch.setattr(
        "apelios.broker.broker_client.NatsClient",
        MagicMock(return_value=fake_client),
    )

    client = BrokerClient(provider="nats")

    async def callback(_msg):
        return None

    await client.subscribe("demo.subject", callback)

    fake_client.subscribe.assert_awaited_once_with("demo.subject", callback)