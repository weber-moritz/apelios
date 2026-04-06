import asyncio
import shutil
import socket
import uuid

import pytest
from nats.aio.msg import Msg

from apelios.broker.broker_client import BrokerClient
from apelios.broker.broker_runtime_manager import BrokerRuntimeManager
from apelios.broker.config import NatsConfig


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_broker_flow(tmp_path):
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    port = _get_free_port()
    config = NatsConfig(host="127.0.0.1", port=port, log_dir=tmp_path)

    runtime = BrokerRuntimeManager(provider="nats", config=config)
    broker = BrokerClient(provider="nats", config=config)

    subject = f"e2e.{uuid.uuid4().hex}"
    payload = b"hello-world"
    received_event = asyncio.Event()
    received_payload: bytes | None = None

    async def on_message(msg: Msg) -> None:
        nonlocal received_payload
        received_payload = msg.data
        received_event.set()

    try:
        await runtime.start_server()
        assert runtime.is_running()

        await broker.connect()
        await broker.subscribe(subject, on_message)
        await broker.publish(subject, payload)

        await asyncio.wait_for(received_event.wait(), timeout=3.0)
        assert received_payload == payload

        assert await runtime.health_check(timeout=3) is True
    finally:
        await broker.disconnect()
        await runtime.stop_server()

    assert runtime.is_running() is False