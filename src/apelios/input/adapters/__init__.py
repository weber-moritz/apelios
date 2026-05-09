"""Input adapters package."""

from .fake_adapter import FakeAdapter
from .mouse_adapter import LinuxEvdevMouse, MouseAdapter

__all__ = ["FakeAdapter", "LinuxEvdevMouse", "MouseAdapter"]
