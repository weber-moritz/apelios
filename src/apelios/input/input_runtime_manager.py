"""Input runtime manager.

Owns input-layer lifecycle and broker connectivity for publishing input events.
"""


from __future__ import annotations


from apelios.broker.broker_client import BrokerClient
from apelios.input.input_publisher import InputPublisher

class InputRuntimeManager:
    def __init__(
        self,
        broker_client: BrokerClient | None = None,
        input_publish_prefix: str = "input",
    ) -> None:
        self.broker_client = broker_client or BrokerClient(provider="nats")
        self.input_publish_prefix = input_publish_prefix
        self.input_publisher = InputPublisher(input_publish_prefix=self.input_publish_prefix, broker_client=self.broker_client)
        self._running = False
        self.registered_adapters: list[object] = []
        self._running_adapters: list[object] = []
        self.failed_adapters: list[object] = []
        
    async def start(self) -> None:
        """Start input runtime"""
        if self._running:
            return
        
        await self.broker_client.connect()
        
        self._running = True
        
    async def stop(self) -> None:
        """Stop input runtime lifecycle state."""
        self._running = False
    
    def is_running(self) -> bool:
        """Return whether this runtime manager is marked as running"""
        return self._running

    async def tick(self, dt: float = 0.016) -> None:
        """Process one input frame."""
        # Iterate running adapters and call their tick hook if available.
        for adapter in list(self._running_adapters):
            try:
                tick = getattr(adapter, "tick", None)
                if callable(tick):
                    await adapter.tick(dt)
            except Exception:
                # If an adapter fails during tick, record it and continue.
                self.failed_adapters.append(adapter)
                continue
    
    def register_adapter(self, adapter: object) -> None:
        """Register a new adapter instance if not already present."""
        if not adapter or isinstance(adapter, (str, bytes)):
            raise TypeError("adapter must be a non-empty adapter object")

        if adapter not in self.registered_adapters:
            self.registered_adapters.append(adapter)


    async def start_adapter(self, adapter: object) -> None:
        """Start one registered adapter safely and idempotently."""
        if adapter not in self.registered_adapters:
            raise ValueError("adapter must be registered before start")

        if adapter in self._running_adapters:
            return

        await adapter.start(input_publisher=self.input_publisher)
        self._running_adapters.append(adapter)


    async def start_registered_adapters(self) -> None:
        """Start all currently registered adapters.

        This method skips bad adapters and keeps starting the remaining ones.
        """
        for adapter in self.registered_adapters:
            try:
                await self.start_adapter(adapter)
            except Exception:
                self.failed_adapters.append(adapter)
                continue


    def adapter_is_running(self, adapter: object) -> bool:
        """Return whether a specific adapter is currently marked running."""
        return adapter in self._running_adapters
    
    async def stop_adapter(self, adapter:object) -> None:
        """Stop a specific adapters safely"""

        if adapter not in self.registered_adapters:
            raise ValueError("adapter must be registered before being stopped")

        if not self.adapter_is_running(adapter):
            return

        await adapter.stop()
        self._running_adapters.remove(adapter)
    
    
    async def stop_registered_adapters(self) -> None:
        """Stop all registered adapters"""
        for adapter in list(self.registered_adapters):
            try:
                await self.stop_adapter(adapter)
            except Exception:
                # Keep stopping the remaining adapters even if one fails.
                continue