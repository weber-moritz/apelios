"""Base output adapter interface.

Interface contract for all output protocol adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseOutputAdapter(ABC):
    """Interface for all output protocol adapters."""

    def __init__(self, config: dict | None = None) -> None:
        """Initialize with protocol-specific configuration.
        
        Args:
            config: Dictionary of protocol-specific settings.
        """
        self.config = config or {}
        self._running = False

    async def start(self) -> None:
        """Start the protocol output stream."""
        self._running = True

    async def stop(self) -> None:
        """Stop the protocol output stream."""
        self._running = False

    @abstractmethod
    async def send_dmx(self, dmx_buffer: dict[tuple[int, int], int]) -> None:
        """Send DMX data. Called on each tick.
        
        Args:
            dmx_buffer: Sparse dict of (universe, address) -> value.
        """
        pass

    def is_running(self) -> bool:
        """Return whether adapter is currently running."""
        return self._running
