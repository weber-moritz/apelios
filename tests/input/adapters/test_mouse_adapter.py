import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_publisher():
	"""Mock publisher for testing."""
	mock = AsyncMock()
	mock.publish = AsyncMock()
	return mock


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


@pytest.mark.asyncio
async def test_mouse_publishes_delta_type(mock_publisher):
    """Mouse adapter publishes x and y with delta type."""
    from apelios.input.adapters.mouse_adapter import MouseAdapter
    
    # Create a mock backend that returns known values
    class MockBackend:
        async def poll(self):
            return {"x": 5.0, "y": -3.0}
        async def close(self):
            pass
    
    adapter = MouseAdapter(device="mouse", backend=MockBackend())
    await adapter.start(input_publisher=mock_publisher)
    await adapter.tick()
    
    # Verify x and y were published with delta type
    assert mock_publisher.publish.await_count == 2
    
    calls = [call[1] for call in mock_publisher.publish.await_args_list]
    
    x_call = next(c for c in calls if c["axis"] == "x")
    assert x_call["value"] == 5.0
    assert x_call["type"] == "delta"
    
    y_call = next(c for c in calls if c["axis"] == "y")
    assert y_call["value"] == -3.0
    assert y_call["type"] == "delta"