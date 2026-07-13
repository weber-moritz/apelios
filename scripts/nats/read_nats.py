from typing import Any
import asyncio
import inspect

import nats
from nats.aio.client import Client as NatsAioClient
from nats.aio.msg import Msg


class NatsClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 4222):
        self.host = host
        self.port = port
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

    async def subscribe(self, subject: str) -> None:
        nc = self._require_connected()

        async def _nats_cb(msg: Msg) -> None:
            print(f"Received message on subject '{msg.subject}': {msg.data.hex() if msg.data else 'empty'}")

        subscription = await nc.subscribe(subject, cb=_nats_cb)
        self._subscriptions.append(subscription)

    def _require_connected(self) -> NatsAioClient:
        if self._nc is None or self._nc.is_closed:
            raise RuntimeError("NATS client is not connected. Call connect() first.")
        return self._nc


async def main():
    my_client = NatsClient()
    await my_client.connect()
    await my_client.subscribe("test.test")
    print("Listening for messages on 'test.test'... Press Ctrl+C to stop")
    
    try:
        await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        print("Disconnecting...")
        await my_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
