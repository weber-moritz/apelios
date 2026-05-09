import pytest
from unittest.mock import AsyncMock

from apelios.input.base_input_adapter import BaseInputAdapter


@pytest.fixture
def mock_publisher():
    """Mock InputPublisher for testing.

    The real publisher will expose a `publish(device, axis, value)` coroutine.
    Tests mock that API surface here.
    """
    mock = AsyncMock()
    mock.publish = AsyncMock()
    return mock


class ConcreteTestAdapter(BaseInputAdapter):
    """Concrete minimal adapter for exercising BaseInputAdapter behavior."""

    async def start(self, input_publisher):
        await super().start(input_publisher)

    async def stop(self):
        await super().stop()


@pytest.mark.asyncio
async def test_start_stores_publisher_and_marks_running(mock_publisher):
    """Start should store the publisher and mark the adapter running."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)

    assert adapter._publisher is mock_publisher
    assert adapter._is_running is True


@pytest.mark.asyncio
async def test_start_is_idempotent(mock_publisher):
    """Calling start twice should leave the adapter running once."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    await adapter.start(input_publisher=mock_publisher)

    assert adapter._is_running is True
    assert adapter._publisher is mock_publisher


@pytest.mark.asyncio
async def test_stop_clears_publisher_and_marks_stopped(mock_publisher):
    """Stop should clear the publisher reference and mark the adapter stopped."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    await adapter.stop()

    assert adapter._publisher is None
    assert adapter._is_running is False


@pytest.mark.asyncio
async def test_stop_is_idempotent(mock_publisher):
    """Calling stop twice should remain safe."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    await adapter.stop()
    await adapter.stop()

    assert adapter._is_running is False


@pytest.mark.asyncio
async def test_publish_forwards_to_publisher(mock_publisher):
    """Publish should forward device, axis, and value to the publisher."""
    adapter = ConcreteTestAdapter(device="dev1")
    await adapter.start(input_publisher=mock_publisher)

    await adapter.publish("axis_x", 0.5)

    mock_publisher.publish.assert_awaited_once_with(
        device="dev1",
        axis="axis_x",
        value=0.5,
    )


@pytest.mark.asyncio
async def test_publish_raises_if_not_started():
    """Publish should fail before the adapter has been started."""
    adapter = ConcreteTestAdapter(device="dev1")

    with pytest.raises(RuntimeError, match="not started"):
        await adapter.publish("x", 0.1)


def test_device_is_stored_from_init():
    """The adapter should retain the device name passed at construction."""
    adapter = ConcreteTestAdapter(device="my_device")
    assert adapter.device == "my_device"


@pytest.mark.asyncio
async def test_publish_snapshot_forwards_all_values(mock_publisher):
    """A snapshot helper should publish each axis value in the snapshot."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)

    snapshot = {
        "left_stick.x": 0.5,
        "fader_1": 0.75,
    }

    await adapter.publish_snapshot(snapshot)

    assert mock_publisher.publish.await_count == 2
    mock_publisher.publish.assert_any_await(
        device="test_device",
        axis="left_stick.x",
        value=0.5,
    )
    mock_publisher.publish.assert_any_await(
        device="test_device",
        axis="fader_1",
        value=0.75,
    )


@pytest.mark.asyncio
async def test_tick_calls_poll_once_and_publishes(mock_publisher):
    """Tick should call the adapter poll hook and publish the snapshot."""

    class PollingAdapter(ConcreteTestAdapter):
        async def poll_once(self, dt: float = 0.016) -> None:
            # populate the adapter snapshot that the base tick will publish
            self.snapshot["x"] = 0.1
            self.snapshot["y"] = 0.2

    adapter = PollingAdapter(device="poll_device")
    await adapter.start(input_publisher=mock_publisher)

    # call tick which should call poll_once and then publish_snapshot
    await adapter.tick(dt=0.016)

    assert mock_publisher.publish.await_count == 2
    mock_publisher.publish.assert_any_await(device="poll_device", axis="x", value=0.1)
    mock_publisher.publish.assert_any_await(device="poll_device", axis="y", value=0.2)