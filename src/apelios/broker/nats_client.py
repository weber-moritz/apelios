from typing import Any
import inspect

import nats
from nats.aio.client import Client as NatsAioClient
from nats.aio.msg import Msg

from .client_interface import BrokerClientInterface, Callback
from .config import NatsConfig, load_nats_config


class NatsClient(BrokerClientInterface):
    def __init__(self, config: NatsConfig | None = None):
        cfg = config or load_nats_config()
        self.host = cfg.host
        self.port = cfg.port
        self.server_url = f"nats://{self.host}:{self.port}"
        self._nc: NatsAioClient | None = None
        self._subscriptions: list[Any] = []

    async def connect(self) -> None:
        if self._nc is not None and not self._nc.is_closed:
            return
        self._nc = await nats.connect(self.server_url)

    async def disconnect(self) -> None:
        if self._nc is None:
            return

        if not self._nc.is_closed:
            await self._nc.drain()
            await self._nc.close()

        self._nc = None
        self._subscriptions.clear()

    async def publish(self, subject: str, message: bytes) -> None:
        nc = self._require_connected()
        await nc.publish(subject, message)
        await nc.flush()

    async def subscribe(self, subject: str, callback: Callback) -> None:
        nc = self._require_connected()

        async def _nats_cb(msg: Msg) -> None:
            result = callback(msg)
            if inspect.isawaitable(result):
                await result

        subscription = await nc.subscribe(subject, cb=_nats_cb)
        self._subscriptions.append(subscription)

    def _require_connected(self) -> NatsAioClient:
        if self._nc is None or self._nc.is_closed:
            raise RuntimeError("NATS client is not connected. Call connect() first.")
        return self._nc