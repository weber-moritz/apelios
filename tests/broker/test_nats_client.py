from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from nats.aio.msg import Msg

from apelios.broker.config import NatsConfig
from apelios.broker.nats_client import NatsClient


def _client(tmp_path) -> NatsClient:
    config = NatsConfig(host="127.0.0.1", port=4222, log_dir=Path(tmp_path))
    return NatsClient(config=config)


@pytest.mark.asyncio
async def test_connect_creates_connection_when_not_connected(tmp_path, monkeypatch):
    client = _client(tmp_path)

    fake_nc = MagicMock()
    fake_nc.is_closed = False

    connect_mock = AsyncMock(return_value=fake_nc)
    monkeypatch.setattr("apelios.broker.nats_client.nats.connect", connect_mock)

    await client.connect()

    connect_mock.assert_awaited_once_with(client.server_url)
    assert client._nc is fake_nc


@pytest.mark.asyncio
async def test_connect_is_noop_when_already_connected(tmp_path, monkeypatch):
    client = _client(tmp_path)

    fake_nc = MagicMock()
    fake_nc.is_closed = False
    client._nc = fake_nc

    connect_mock = AsyncMock()
    monkeypatch.setattr("apelios.broker.nats_client.nats.connect", connect_mock)

    await client.connect()

    connect_mock.assert_not_awaited()
    assert client._nc is fake_nc


@pytest.mark.asyncio
async def test_disconnect_noop_when_not_connected(tmp_path):
    client = _client(tmp_path)

    await client.disconnect()

    assert client._nc is None
    assert client._subscriptions == []


@pytest.mark.asyncio
async def test_disconnect_drains_closes_and_clears_state(tmp_path):
    client = _client(tmp_path)

    fake_nc = MagicMock()
    fake_nc.is_closed = False
    fake_nc.drain = AsyncMock()
    fake_nc.close = AsyncMock()
    client._nc = fake_nc
    client._subscriptions = [object()]

    await client.disconnect()

    fake_nc.drain.assert_awaited_once()
    fake_nc.close.assert_awaited_once()
    assert client._nc is None
    assert client._subscriptions == []


@pytest.mark.asyncio
async def test_publish_raises_when_not_connected(tmp_path):
    client = _client(tmp_path)

    with pytest.raises(RuntimeError, match="not connected"):
        await client.publish("demo.subject", b"payload")


@pytest.mark.asyncio
async def test_publish_calls_publish_and_flush(tmp_path):
    client = _client(tmp_path)

    fake_nc = MagicMock()
    fake_nc.is_closed = False
    fake_nc.publish = AsyncMock()
    fake_nc.flush = AsyncMock()
    client._nc = fake_nc

    await client.publish("demo.subject", b"payload")

    fake_nc.publish.assert_awaited_once_with("demo.subject", b"payload")
    fake_nc.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_subscribe_registers_subscription_and_stores_it(tmp_path):
    client = _client(tmp_path)

    fake_sub = object()
    fake_nc = MagicMock()
    fake_nc.is_closed = False
    fake_nc.subscribe = AsyncMock(return_value=fake_sub)
    client._nc = fake_nc

    callback = AsyncMock()

    await client.subscribe("demo.subject", callback)

    fake_nc.subscribe.assert_awaited_once()
    call = fake_nc.subscribe.await_args
    assert call.args[0] == "demo.subject"
    assert "cb" in call.kwargs
    assert client._subscriptions == [fake_sub]


@pytest.mark.asyncio
async def test_subscribe_wrapper_supports_sync_callback(tmp_path):
    client = _client(tmp_path)

    fake_nc = MagicMock()
    fake_nc.is_closed = False
    fake_nc.subscribe = AsyncMock(return_value=object())
    client._nc = fake_nc

    callback_called = {"value": False}

    def sync_callback(msg):
        callback_called["value"] = True
        return None

    await client.subscribe("demo.subject", sync_callback)

    wrapped_cb = fake_nc.subscribe.await_args.kwargs["cb"]
    await wrapped_cb(MagicMock(spec=Msg))

    assert callback_called["value"] is True