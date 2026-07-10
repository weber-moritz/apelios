"""Output core - maintains current DMX state for Output Layer.

This is the stateful component that holds the current DMX values.
Adapters read from this state and send at their own rates (per ADR-004 and ADR-008).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_output_adapter import BaseOutputAdapter


class OutputCore:
    """Core data processing for Output Layer.
    
    Maintains current DMX state for all universes and channels. This class
    is the single source of truth for what DMX values should be output.
    
    Adapters read from this state and send at their own configured rates.
    The state is updated by OutputInputSubscriber when it receives messages
    from the broker.
    
    Attributes:
        dmx_state: Current DMX state as sparse dict of (universe, address) -> value.
                   Contains the latest value for each channel, persists between frames.
        adapters: List of registered adapters (for tracking/debugging only).
    """

    def __init__(self) -> None:
        """Initialize with empty DMX state."""
        # Current state - always contains latest values for all channels
        # This is NOT cleared between frames - adapters read from it continuously
        self.dmx_state: dict[tuple[int, int], int] = {}
        # Adapters registered (for debugging/tracking, not for sending)
        self.adapters: list[BaseOutputAdapter] = []

    def add_to_buffer(self, universe: int, address: int, value: int) -> None:
        """Update current DMX state with latest value.
        
        This method is called by the OutputInputSubscriber when it receives
        DMX values from the broker. Values are stored as current state,
        meaning the latest value for each channel is always available.
        
        Args:
            universe: DMX universe number (1-65535).
            address: DMX channel address (1-512).
            value: DMX value (0-255 for 8-bit, 0-65535 for 16-bit).
        """
        self.dmx_state[(universe, address)] = value

    def register_adapter(self, adapter: BaseOutputAdapter) -> None:
        """Register adapter for tracking/debugging (optional).
        
        Note: Adapters read from dmx_state directly via their core reference.
        This method is for tracking/debugging purposes only.
        
        Args:
            adapter: Protocol adapter instance to register.
        """
        self.adapters.append(adapter)

    async def process_frame(self, dt: float | None = None) -> None:
        """Process one frame - no-op for state management.
        
        This method is kept for backward compatibility with the orchestrator's
        tick loop but no longer sends to adapters. Adapters now have their own
        independent sending loops that read from dmx_state directly.
        
        Args:
            dt: Delta time in seconds since last frame (optional, unused).
        """
        # No longer sends to adapters - they have their own loops
        # State is updated by add_to_buffer() calls from OutputInputSubscriber
        pass
