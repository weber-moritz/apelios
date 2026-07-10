"""Output runtime manager.

Owns output-layer lifecycle and broker connectivity. This is the micro-kernel
entry point for the Output Layer, managing the complete lifecycle (start/stop/tick)
and delegating data processing to OutputCore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apelios.broker.broker_client import BrokerClient

if TYPE_CHECKING:
    from .base_output_adapter import BaseOutputAdapter
    from .output_core import OutputCore
    from .output_input_subscriber import OutputInputSubscriber


class OutputRuntimeManager:
    """Own the output layer lifecycle.
    
    Handles start/stop/tick lifecycle only. Data processing is delegated
    to OutputCore. This class follows the micro-kernel pattern (ADR-002) where
    it manages lifecycle and coordinates dependencies, but does not handle
    data processing itself.
    
    Attributes:
        broker_client: BrokerClient instance for NATS communication.
        core: OutputCore instance for data processing.
        input_subscriber: OutputInputSubscriber for handling broker messages.
        _running: Flag indicating if the runtime is currently active.
        _adapters: List of registered and started protocol adapters.
    """

    def __init__(
        self,
        broker_client: BrokerClient | None = None,
        core: OutputCore | None = None,
    ) -> None:
        """Initialize with optional broker client and core.
        
        Args:
            broker_client: Injected BrokerClient for NATS communication.
                If not provided, a default instance is created.
            core: Injected OutputCore for data processing.
                If not provided, a default instance is created.
        """
        self.broker_client = broker_client or BrokerClient()
        self.core = core or self._create_core()
        self.input_subscriber = self._create_input_subscriber()
        self._running = False
        self._adapters: list[BaseOutputAdapter] = []

    def _create_core(self) -> OutputCore:
        """Create default OutputCore instance.
        
        Returns:
            New OutputCore instance for data processing.
        """
        from .output_core import OutputCore
        return OutputCore()

    def _create_input_subscriber(self) -> OutputInputSubscriber:
        """Create default OutputInputSubscriber instance.
        
        Returns:
            New OutputInputSubscriber instance for handling broker messages.
        """
        from .output_input_subscriber import OutputInputSubscriber
        return OutputInputSubscriber(self.core)

    def _register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register an adapter and track it for lifecycle management.
        
        Args:
            adapter: Protocol adapter instance to register and track.
        """
        self.core.register_adapter(adapter)
        self._adapters.append(adapter)

    async def _bootstrap_adapters(self) -> None:
        """Bootstrap output adapters and start them.
        
        Creates adapter instances via the bootstrap mechanism, registers them
        with the core, and starts their lifecycle.
        """
        from .output_adapter_bootstrap import OutputAdapterBootstrap
        
        bootstrap = OutputAdapterBootstrap()
        await bootstrap.bootstrap(self)
        
        # Start all registered adapters
        for adapter in self._adapters:
            await adapter.start()

    async def start(self) -> None:
        """Start output runtime.
        
        Connects to broker, subscribes to output topics, and bootstraps adapters.
        This method initiates the complete Output Layer lifecycle.
        """
        if self._running:
            return

        await self.broker_client.connect()
        await self.broker_client.subscribe("output.>", self.input_subscriber)
        await self._bootstrap_adapters()
        
        self._running = True

    async def stop(self) -> None:
        """Stop output runtime lifecycle state.
        
        Stops all adapters, disconnects from broker, and cleans up resources.
        This method gracefully shuts down the complete Output Layer.
        """
        if not self._running:
            return

        # Stop all adapters first
        for adapter in self._adapters:
            await adapter.stop()
        self._adapters = []
        
        await self.broker_client.disconnect()
        self._running = False

    def is_running(self) -> bool:
        """Return whether this runtime manager is marked as running.
        
        Returns:
            True if the runtime has been started and not stopped, False otherwise.
        """
        return self._running

    async def tick(self, dt: float = 0.016) -> None:
        """Process one output frame.
        
        Delegates to core for data processing. Called by the MainOrchestrator
        at the configured tick rate (typically 60Hz).
        
        Args:
            dt: Delta time in seconds since last frame (default 1/60 = 0.016).
        """
        await self.core.process_frame(dt=dt)
