"""Base output adapter interface.

Provides the abstract base class and interface contract for all output protocol adapters.
All protocol adapters (ArtNet, sACN, DMX, etc.) must inherit from this class and implement
the abstract methods.

Adapters are stateless (per ADR-004) and manage their own independent sending loops
at their configured protocol rates (per ADR-010).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..output_core import OutputCore


class BaseOutputAdapter(ABC):
    """Interface for all output protocol adapters.
    
    This abstract base class defines the contract that all output protocol adapters
    must implement. Adapters are stateless (per ADR-004) and manage their own
    independent sending loops at their configured protocol rates (per ADR-010).
    
    Adapters read DMX state from the OutputCore and send at their protocol-specific
    refresh rates. The orchestrator drives OutputCore updates at 60Hz, but adapters
    control their own transmission timing.
    
    Attributes:
        config: Protocol-specific configuration dictionary.
        core: Reference to OutputCore for reading DMX state.
        _running: Internal flag tracking adapter lifecycle state.
        _task: asyncio task for the adapter's independent sending loop.
    """

    def __init__(self, config: dict | None = None, core: OutputCore | None = None) -> None:
        """Initialize with protocol-specific configuration and core reference.
        
        Args:
            config: Optional configuration dictionary for the adapter.
                   Contains protocol-specific settings like IP addresses,
                   universe numbers, etc.
            core: OutputCore instance for reading DMX state. Adapters read
                  from core.dmx_state to get current DMX values.
        """
        self.config = config or {}
        self.core = core
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the protocol output stream and the independent sending loop.
        
        Initializes network connections, configures protocol-specific settings,
        starts the adapter's independent sending loop, and prepares the adapter
        to send DMX data at its configured rate.
        """
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the protocol output stream and the sending loop.
        
        Cleans up network connections, closes sockets, cancels the sending loop,
        and releases resources. After calling this method, the adapter will no
        longer send DMX data.
        """
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                # Task was cancelled, which is expected
                pass
            self._task = None

    @abstractmethod
    async def _run_loop(self) -> None:
        """Main adapter loop - runs independently at the adapter's configured rate.
        
        Subclasses must implement this method to:
        1. Read current DMX state from self.core.dmx_state
        2. Send it via the protocol at the configured rate
        3. Use absolute time scheduling for precise rate control
        
        This loop runs independently of the orchestrator's tick, allowing
        protocol-compliant refresh rates (40Hz for ArtNet, 44Hz for DMX, etc.).
        
        The loop should exit when self._running becomes False.
        """
        pass

    async def send_dmx(self, dmx_state: dict[tuple[int, int], int]) -> None:
        """Send DMX data via the protocol.
        
        This method is kept for backward compatibility and can be called directly
        for testing purposes. In normal operation, adapters call this from their
        _run_loop() method.
        
        Subclasses should override this to implement protocol-specific sending.
        
        Args:
            dmx_state: Current DMX state as sparse dictionary mapping
                       (universe, address) tuples to DMX values (0-255 for 8-bit,
                       0-65535 for 16-bit).
        """
        # Default implementation does nothing; subclasses must override
        pass

    def is_running(self) -> bool:
        """Return whether adapter is currently running.
        
        Returns:
            True if the adapter has been started and not stopped, False otherwise.
        """
        return self._running
