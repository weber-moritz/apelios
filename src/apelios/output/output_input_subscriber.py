"""Output input subscriber.

Subscribes to output topics and forwards DMX data to OutputCore.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_core import OutputCore


class OutputInputSubscriber:
    """Subscriber for output layer messages.
    
    Receives DMX values from Fixture Layer and forwards to OutputCore.
    """

    def __init__(self, core: OutputCore) -> None:
        """Initialize with reference to OutputCore.
        
        Args:
            core: OutputCore instance to forward messages to.
        """
        self.core = core

    def __call__(self, subject: str, payload: bytes) -> None:
        """Handle incoming message from broker.
        
        Parses the subject and payload, extracts universe/address/value,
        and forwards to core buffer.
        
        Args:
            subject: NATS subject (e.g., 'output.1.42').
            payload: Message payload as bytes.
        """
        try:
            data = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Invalid payload, skip
            return

        # Extract universe and address from payload
        universe = data.get('universe')
        address = data.get('address')
        value = data.get('value')

        if universe is None or address is None or value is None:
            # Missing required fields, skip
            return

        # Forward to core (value may be float from JSON, convert to int)
        self.core.add_to_buffer(
            universe=int(universe),
            address=int(address),
            value=int(value)
        )
