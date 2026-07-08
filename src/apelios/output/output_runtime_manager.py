"""Output runtime manager.

Owns output-layer lifecycle and broker connectivity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apelios.broker.broker_client import BrokerClient

if TYPE_CHECKING:
    from .output_core import OutputCore
    from .output_input_subscriber import OutputInputSubscriber


class OutputRuntimeManager:
    """Own the output layer lifecycle.
    
    Handles start/stop/tick lifecycle only. Data processing is delegated
    to OutputCore.
    """

    def __init__(
        self,
        broker_client: BrokerClient | None = None,
        core: OutputCore | None = None,
    ) -> None:
        """Initialize with optional broker client and core.
        
        Args:
            broker_client: Injected BrokerClient for NATS communication.
            core: Injected OutputCore for data processing.
        """
        self.broker_client = broker_client or BrokerClient()
        self.core = core or self._create_core()
        self.input_subscriber = self._create_input_subscriber()
        self._running = False

    def _create_core(self) -> OutputCore:
        """Create default OutputCore instance."""
        from .output_core import OutputCore
        return OutputCore()

    def _create_input_subscriber(self) -> OutputInputSubscriber:
        """Create default OutputInputSubscriber instance."""
        from .output_input_subscriber import OutputInputSubscriber
        return OutputInputSubscriber(self.core)

    async def _bootstrap_adapters(self) -> None:
        """Bootstrap output adapters."""
        from .output_adapter_bootstrap import OutputAdapterBootstrap
        
        bootstrap = OutputAdapterBootstrap()
        await bootstrap.bootstrap(self)

    async def start(self) -> None:
        """Start output runtime.
        
        Connects to broker, subscribes to output topics, and bootstraps adapters.
        """
        if self._running:
            return

        await self.broker_client.connect()
        await self.broker_client.subscribe("output.>", self.input_subscriber)
        await self._bootstrap_adapters()
        
        self._running = True

    async def stop(self) -> None:
        """Stop output runtime lifecycle state."""
        if not self._running:
            return

        await self.broker_client.disconnect()
        self._running = False

    def is_running(self) -> bool:
        """Return whether this runtime manager is marked as running."""
        return self._running

    async def tick(self, dt: float = 0.016) -> None:
        """Process one output frame.
        
        Delegates to core for data processing.
        
        Args:
            dt: Delta time in seconds (default 1/60 = 0.016).
        """
        await self.core.process_frame(dt=dt)
