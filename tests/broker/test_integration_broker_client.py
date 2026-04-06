import asyncio
import shutil
import socket
import uuid

import pytest
from nats.aio.msg import Msg

from apelios.broker.broker_client import BrokerClient
from apelios.broker.config import NatsConfig
from apelios.broker.nats_runtime_manager import NatsRuntimeManager


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_broker_client_publish_subscribe_roundtrip(tmp_path):
    if shutil.which("nats-server") is None:
        pytest.skip("nats-server binary not installed")
    pytest.importorskip("nats")

    port = _get_free_port()
    config = NatsConfig(host="127.0.0.1", port=port, log_dir=tmp_path)

    runtime = NatsRuntimeManager(config)
    client = BrokerClient(provider="nats", config=config)

    subject = f"integration.broker-client.{uuid.uuid4().hex}"
    expected_payload = b"hello-from-broker-client"
    received_payload: bytes | None = None
    received_event = asyncio.Event()

    async def on_message(msg: Msg) -> None:
        nonlocal received_payload
        received_payload = msg.data
        received_event.set()

    try:
        await runtime.start_server()
        await client.connect()
        await client.subscribe(subject, on_message)
        await client.publish(subject, expected_payload)

        await asyncio.wait_for(received_event.wait(), timeout=2.0)
        assert received_payload == expected_payload
    finally:
        await client.disconnect()
        await runtime.stop_server()

    assert runtime.process is None
    assert runtime.log_file is None