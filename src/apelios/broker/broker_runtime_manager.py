from .broker_interface import BrokerInterface
from .config import NatsConfig
from .nats_runtime_manager import NatsRuntimeManager


class BrokerRuntimeManager:
    def __init__(self, provider: str = "nats", config: NatsConfig | None = None):
        if provider == "nats":
            self._runtime: BrokerInterface = NatsRuntimeManager(config=config)
        else:
            raise ValueError(f"Unsupported broker provider: {provider}")

    async def start_server(self) -> None:
        await self._runtime.start_server()

    async def stop_server(self) -> None:
        await self._runtime.stop_server()

    async def health_check(self, timeout: int = 5) -> bool:
        return await self._runtime.health_check(timeout=timeout)

    def is_running(self) -> bool:
        return self._runtime.is_running()