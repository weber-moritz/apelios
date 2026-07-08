"""Output core - data processing for Output Layer.

Maintains DMX buffer and manages protocol adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_output_adapter import BaseOutputAdapter


class OutputCore:
    """Core data processing for Output Layer."""

    def __init__(self) -> None:
        """Initialize with empty DMX buffer."""
        self.dmx_buffer: dict[tuple[int, int], int] = {}
        self.adapters: list[BaseOutputAdapter] = []

    def add_to_buffer(self, universe: int, address: int, value: int) -> None:
        """Add or update a DMX channel in the buffer."""
        self.dmx_buffer[(universe, address)] = value

    def register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register a protocol adapter."""
        self.adapters.append(adapter)

    async def process_frame(self, dt: float | None = None) -> None:
        """Process one frame: send buffer to all adapters, then clear."""
        if not self.dmx_buffer:
            return

        for adapter in self.adapters:
            await adapter.send_dmx(self.dmx_buffer)

        self.dmx_buffer = {}
