"""Output input subscriber.

Subscribes to output topics and forwards DMX data to OutputCore.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_core import OutputCore


class OutputInputSubscriber:
    """Subscriber for output layer messages."""

    def __init__(self, core: OutputCore) -> None:
        """Initialize with reference to OutputCore."""
        self.core = core

    def __call__(self, subject: str, payload: bytes) -> None:
        """Handle incoming message from broker."""
        try:
            data = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        universe = data.get('universe')
        address = data.get('address')
        value = data.get('value')

        if universe is None or address is None or value is None:
            return

        self.core.add_to_buffer(
            universe=int(universe),
            address=int(address),
            value=int(value)
        )
