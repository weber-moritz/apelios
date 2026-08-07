"""Output layer protocol adapters.

Provides protocol-specific adapters for the Output Layer, including ArtNet,
sACN, DMX, and other lighting protocols.
"""

from .artnet_adapter import ArtNetAdapter
from .fake_output_adapter import FakeOutputAdapter

__all__ = ["ArtNetAdapter", "FakeOutputAdapter"]
