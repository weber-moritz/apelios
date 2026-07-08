"""Output core - data processing for Output Layer.

Maintains DMX buffer and manages protocol adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_output_adapter import BaseOutputAdapter


class OutputCore:
    """Core data processing for Output Layer.
    
    Maintains sparse DMX buffer and dispatches to protocol adapters.
    """

    def __init__(self) -> None:
        """Initialize with empty DMX buffer."""
        self.dmx_buffer: dict[tuple[int, int], int] = {}
        self.adapters: list[BaseOutputAdapter] = []

    def add_to_buffer(self, universe: int, address: int, value: int) -> None:
        """Add or update a DMX channel in the buffer.
        
        Args:
            universe: DMX universe number.
            address: DMX channel address (1-512).
            value: DMX value (0-255).
        """
        self.dmx_buffer[(universe, address)] = value

    def register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register a protocol adapter.
        
        Args:
            adapter: Protocol adapter instance to register.
        """
        self.adapters.append(adapter)

    def process_frame(self, dt: float | None = None) -> None:
        """Process one frame: send buffer to all adapters, then clear.
        
        Args:
            dt: Delta time in seconds (unused, for interface consistency).
        """
        if not self.dmx_buffer:
            return

        for adapter in self.adapters:
            adapter.send_dmx(self.dmx_buffer)

        self.dmx_buffer = {}
