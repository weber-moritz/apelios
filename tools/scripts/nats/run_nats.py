from pathlib import Path
import subprocess
import asyncio
import time
import socket
from typing import Any
import inspect

import nats
from nats.aio.client import Client as NatsAioClient
from nats.aio.msg import Msg


class Broker:
    def __init__(self, port: int = 4222):
        self.log_file = Path("/tmp/nats_server.log")
        self.port = port
        self.process = subprocess.Popen(
            ["nats-server", "-p", str(self.port)],
            stdout=self.log_file.open("w"),
            stderr=self.log_file.open("a"),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()


class Sender:
    def __init__(self, host: str = "127.0.0.1", port: int = 4222):
        self.host = host
        self.port = port
        self.server_url = f"nats://{self.host}:{self.port}"
        self._nc: NatsAioClient | None = None
        self._subscriptions: list[Any] = []

    async def connect(self):
        if self._nc is not None and not self._nc.is_closed:
            return
        self._nc = await nats.connect(self.server_url)

    def _require_connected(self) -> NatsAioClient:
        if self._nc is None or self._nc.is_closed:
            raise RuntimeError("NATS client is not connected. Call connect() first.")
        return self._nc

    async def publish(self, subject: str, message: bytes) -> None:
        nc = self._require_connected()
        await nc.publish(subject, message)
        await nc.flush()

    async def start_sending(self) -> None:
        while True:
            await self.publish("test.test", b"\x01\x01\x01\x01")
            await asyncio.sleep(0.5)


async def main():
    print("Starting broker...")
    my_broker = Broker(port=4222)

    print("Waiting 5s for broker to start...")
    await asyncio.sleep(5)

    print("Starting sender...")
    my_sender = Sender()
    await my_sender.connect()
    await my_sender.start_sending()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")