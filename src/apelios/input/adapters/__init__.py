"""Input adapters package.

Adapters in this package should be designed as cross-platform inputs when
possible. Linux is the implementation priority today, and unless a module
states otherwise, support for other operating systems is not required yet.
"""

from .fake_adapter import FakeAdapter
from .mouse_adapter import LinuxEvdevMouse, MouseAdapter
from .steamdeck_adapter import SteamDeckAdapter

__all__ = ["FakeAdapter", "LinuxEvdevMouse", "MouseAdapter", "SteamDeckAdapter"]
