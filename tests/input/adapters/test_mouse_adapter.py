import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_mouse_adapter_uses_linux_backend_on_linux(monkeypatch):
    """MouseAdapter should build the Linux backend when running on Linux."""
    mouse_module = pytest.importorskip("apelios.input.adapters.mouse_adapter")

    monkeypatch.setattr(mouse_module.sys, "platform", "linux")

    class DummyLinuxBackend:
        def __init__(self):
            self.poll = AsyncMock(return_value={"x": 10.0, "y": -5.0})
            self.close = AsyncMock()

    mock_backend_cls = DummyLinuxBackend
    monkeypatch.setattr(mouse_module, "LinuxEvdevMouse", mock_backend_cls)

    adapter = mouse_module.MouseAdapter(device="mouse")

    assert isinstance(adapter._backend, DummyLinuxBackend)


@pytest.mark.asyncio
async def test_linux_evdev_mouse_parses_relative_motion():
    """LinuxEvdevMouse should translate evdev relative events into deltas."""
    mouse_module = pytest.importorskip("apelios.input.adapters.mouse_adapter")
    evdev = pytest.importorskip("evdev")

    mock_device = MagicMock()
    mock_device.read = MagicMock(
        return_value=[
            (evdev.ecodes.EV_REL, evdev.ecodes.REL_X, 10),
            (evdev.ecodes.EV_REL, evdev.ecodes.REL_Y, -5),
        ],
    )

    backend = mouse_module.LinuxEvdevMouse()
    backend._device = mock_device

    result = await backend.poll()

    assert result == {"x": 10.0, "y": -5.0}