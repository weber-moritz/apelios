import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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

    # Patch select so the mock device's fake fd is treated as readable.
    with patch("apelios.input.adapters.mouse_adapter.select.select", return_value=([mock_device.fd], [], [])):
        result = await backend.poll()

    assert result == {"x": 10.0, "y": -5.0}


@pytest.mark.asyncio
async def test_linux_evdev_mouse_returns_zeros_when_idle():
    """LinuxEvdevMouse returns x=0.0, y=0.0 when no hardware events are queued.

    This is the contract that lets the middleware hold its output position
    without any special consume logic — idle means zero velocity, not stale delta.
    """
    mouse_module = pytest.importorskip("apelios.input.adapters.mouse_adapter")

    mock_device = MagicMock()

    backend = mouse_module.LinuxEvdevMouse()
    backend._device = mock_device

    # select returns empty readable list — no events queued.
    with patch("apelios.input.adapters.mouse_adapter.select.select", return_value=([], [], [])):
        result = await backend.poll()

    assert result == {"x": 0.0, "y": 0.0}
    mock_device.read.assert_not_called()