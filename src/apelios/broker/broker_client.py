from .client_interface import BrokerClientInterface, Callback
from .config import NatsConfig
from .nats_client import NatsClient


class BrokerClient:
    def __init__(self, provider: str = "nats", config: NatsConfig | None = None):
        if provider == "nats":
            self._client: BrokerClientInterface = NatsClient(config=config)
        else:
            raise ValueError(f"Unsupported broker provider: {provider}")

    async def connect(self) -> None:
        await self._client.connect()

    async def disconnect(self) -> None:
        await self._client.disconnect()

    async def publish(self, subject: str, message: bytes) -> None:
        await self._client.publish(subject, message)

    async def subscribe(self, subject: str, callback: Callback) -> None:
        await self._client.subscribe(subject, callback)