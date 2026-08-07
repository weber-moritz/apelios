"""Fake output adapter for performance testing.

Provides a mock output adapter that records send timestamps without requiring
actual hardware. Useful for measuring Output layer latency in tests.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from ..base_output_adapter import BaseOutputAdapter

if TYPE_CHECKING:
    from ..output_core import OutputCore


class FakeOutputAdapter(BaseOutputAdapter):
    """Mock adapter that records send timestamps without actual hardware.
    
    This adapter simulates the behavior of a real output adapter (like ArtNet)
    but instead of sending DMX to hardware, it records the timestamp when
    send_dmx() would be called. This allows latency measurement in tests.
    
    Attributes:
        send_timestamps: List of timestamps when DMX was "sent".
        send_count: Number of times DMX was sent (for quick access).
    """

    def __init__(self, config: dict | None = None, core: OutputCore | None = None) -> None:
        """Initialize with optional configuration and core reference.
        
        Args:
            config: Optional configuration dictionary. Supported keys:
                   - output_rate_hz (float): Sending rate in Hz (default: 40Hz like ArtNet)
                   - test_mode (bool): If True, disables automatic loop for testing
            core: OutputCore instance for reading DMX state.
        """
        super().__init__(config, core)
        
        # Configuration
        self.output_rate_hz = config.get("output_rate_hz", 40.0) if config else 40.0
        self.test_mode = config.get("test_mode", False) if config else False
        
        # Tracking
        self.send_timestamps: list[float] = []
        self.send_count: int = 0

    async def _run_loop(self) -> None:
        """Main adapter loop - runs independently at configured rate.
        
        Reads current DMX state from OutputCore and records send timestamps
        at the configured rate (default 40Hz). In test mode, this loop is skipped
        and send_dmx() must be called manually.
        """
        if self.test_mode:
            # In test mode, don't run the automatic loop
            # send_dmx() will be called manually by tests
            while self._running:
                await asyncio.sleep(0.1)  # Just keep the task alive
            return
        
        while self._running:
            start_time = time.perf_counter()
            
            # Record current state and timestamp
            await self.send_dmx(self.core.dmx_state)
            
            # Calculate sleep time to maintain configured rate
            processing_time = time.perf_counter() - start_time
            sleep_time = max(0, (1.0 / self.output_rate_hz) - processing_time)
            await asyncio.sleep(sleep_time)

    async def send_dmx(self, dmx_state: dict[tuple[int, int], int] | None = None) -> None:
        """Record send timestamp for latency measurement.
        
        Instead of actually sending DMX to hardware, this records the
        timestamp when send_dmx() is called. This allows tests to
        measure the latency from message receipt to "send".
        
        Args:
            dmx_state: Current DMX state as sparse dictionary mapping
                       (universe, address) tuples to DMX values. Can be None in test mode.
        """
        timestamp = time.perf_counter()
        self.send_timestamps.append(timestamp)
        self.send_count += 1
    
    def record_send_timestamp(self) -> None:
        """Manually record a send timestamp for testing.
        
        This is used in test mode when the adapter's automatic loop is disabled.
        """
        timestamp = time.perf_counter()
        self.send_timestamps.append(timestamp)
        self.send_count += 1

    def get_send_timestamps(self) -> list[float]:
        """Get list of all send timestamps.
        
        Returns:
            List of timestamps (in seconds from time.perf_counter origin)
            when DMX was sent.
        """
        return self.send_timestamps.copy()

    def get_send_count(self) -> int:
        """Get total number of DMX sends.
        
        Returns:
            Number of times DMX was sent.
        """
        return self.send_count

    def clear_timestamps(self) -> None:
        """Clear recorded timestamps for fresh measurement."""
        self.send_timestamps.clear()
        self.send_count = 0
