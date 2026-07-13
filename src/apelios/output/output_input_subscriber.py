"""Output input subscriber.

Subscribes to output topics and forwards DMX data to OutputCore.
This subscriber receives messages from the NATS broker on the 'output.>' topic
pattern and adds the DMX values to the OutputCore's buffer.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_core import OutputCore


class OutputInputSubscriber:
    """Subscriber for output layer messages.
    
    Handles incoming messages from the broker and forwards DMX data to the
    OutputCore for buffering and processing. This class is stateless and
    only responsible for message parsing and forwarding.
    
    Attributes:
        core: Reference to the OutputCore instance for buffer management.
    """

    def __init__(self, core: OutputCore) -> None:
        """Initialize with reference to OutputCore.
        
        Args:
            core: OutputCore instance to forward DMX data to.
        """
        self.core = core

    def __call__(self, msg: Any) -> None:
        """Handle incoming message from broker.
        
        Args:
            msg: NATS message object with subject and data attributes.
        """
        try:
            data = json.loads(msg.data.decode('utf-8'))
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
