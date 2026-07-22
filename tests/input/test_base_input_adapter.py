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
    """Publish should forward device, axis, value, type, and source to the publisher."""
    adapter = ConcreteTestAdapter(device="dev1")
    await adapter.start(input_publisher=mock_publisher)

    await adapter.publish("axis_x", 0.5)

    mock_publisher.publish.assert_awaited_once_with(
        device="dev1",
        axis="axis_x",
        value=0.5,
        type="absolute_uni",  # default type
        source=None,
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
    """A snapshot helper should publish each axis value in the snapshot with types."""
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
        type="absolute_uni",
        source=None,
    )
    mock_publisher.publish.assert_any_await(
        device="test_device",
        axis="fader_1",
        value=0.75,
        type="absolute_uni",
        source=None,
    )


@pytest.mark.asyncio
async def test_tick_calls_poll_once_and_publishes(mock_publisher):
    """Tick should call the adapter poll hook and publish the snapshot with types."""

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
    mock_publisher.publish.assert_any_await(device="poll_device", axis="x", value=0.1, type="absolute_uni", source=None)
    mock_publisher.publish.assert_any_await(device="poll_device", axis="y", value=0.2, type="absolute_uni", source=None)


@pytest.mark.asyncio
async def test_adapter_publishes_with_type(mock_publisher):
    """Adapter publishes with type from axis_types mapping."""
    class TypedAdapter(ConcreteTestAdapter):
        def __init__(self, device: str):
            super().__init__(device=device)
            self._axis_types = {"x": "delta", "y": "absolute_bi"}
    
    adapter = TypedAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    await adapter.publish("x", 0.5)
    
    # Check that publish was called with type
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["device"] == "test_device"
    assert call_args[1]["axis"] == "x"
    assert call_args[1]["value"] == 0.5
    assert "type" in call_args[1]
    assert call_args[1]["type"] == "delta"


@pytest.mark.asyncio
async def test_adapter_publish_snapshot_includes_types(mock_publisher):
    """Adapter publish_snapshot passes type for each axis."""
    class TypedAdapter(ConcreteTestAdapter):
        def __init__(self, device: str):
            super().__init__(device=device)
            self._axis_types = {"x": "delta", "y": "absolute_bi", "z": "rate"}
    
    adapter = TypedAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    snapshot = {"x": 0.1, "y": 0.5, "z": 0.01}
    await adapter.publish_snapshot(snapshot)
    
    # Verify all three axes were published with correct types
    assert mock_publisher.publish.await_count == 3
    
    # Get all calls
    calls = [call[1] for call in mock_publisher.publish.await_args_list]
    
    # Check each call has the right type
    for call in calls:
        assert "type" in call
    
    # Check specific types
    delta_call = next(c for c in calls if c["axis"] == "x")
    assert delta_call["type"] == "delta"
    
    bi_call = next(c for c in calls if c["axis"] == "y")
    assert bi_call["type"] == "absolute_bi"
    
    rate_call = next(c for c in calls if c["axis"] == "z")
    assert rate_call["type"] == "rate"


@pytest.mark.asyncio
async def test_adapter_publishes_with_source(mock_publisher):
    """Adapter publishes with source parameter passed to publisher."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    await adapter.publish("axis_x", 0.5)
    
    # Verify publisher was called with source parameter (may be None for auto-generation)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["device"] == "test_device"
    assert call_args[1]["axis"] == "axis_x"
    assert call_args[1]["value"] == 0.5
    assert call_args[1]["type"] == "absolute_uni"
    assert "source" in call_args[1]  # Source parameter is passed (may be None)


@pytest.mark.asyncio
async def test_adapter_publish_snapshot_includes_source(mock_publisher):
    """Adapter publish_snapshot passes all parameters including source to publisher."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    snapshot = {"x": 0.1, "y": 0.5}
    await adapter.publish_snapshot(snapshot)
    
    # Verify publisher was called twice (once per axis)
    assert mock_publisher.publish.await_count == 2
    
    # Verify both calls include required parameters (source flows through via default)
    for call in mock_publisher.publish.await_args_list:
        kwargs = call[1]
        assert "device" in kwargs
        assert "axis" in kwargs
        assert "value" in kwargs
        assert "type" in kwargs
        # Source parameter exists (may be None, which triggers auto-generation)
        assert "source" in kwargs


# =============================================================================
# AXIS SCALING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_axis_scale_returns_one_by_default(mock_publisher):
    """get_axis_scale should return 1.0 for axes with no scale defined."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # No scales have been set, should default to 1.0
    assert adapter.get_axis_scale("any_axis") == 1.0
    assert adapter.get_axis_scale("imu.pitch") == 1.0
    assert adapter.get_axis_scale("joy.x") == 1.0


@pytest.mark.asyncio
async def test_set_axis_scale_stores_exact_match(mock_publisher):
    """set_axis_scale should store and get_axis_scale should retrieve exact matches."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("imu.pitch", 0.1)
    adapter.set_axis_scale("joy.x", 0.5)
    
    assert adapter.get_axis_scale("imu.pitch") == 0.1
    assert adapter.get_axis_scale("joy.x") == 0.5
    # Other axes should still default to 1.0
    assert adapter.get_axis_scale("imu.yaw") == 1.0


@pytest.mark.asyncio
async def test_get_axis_scale_wildcard_match(mock_publisher):
    """get_axis_scale should match wildcard patterns like 'imu.*'."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("imu.*", 0.1)
    
    # All imu.* axes should match
    assert adapter.get_axis_scale("imu.pitch") == 0.1
    assert adapter.get_axis_scale("imu.yaw") == 0.1
    assert adapter.get_axis_scale("imu.roll") == 0.1


@pytest.mark.asyncio
async def test_get_axis_scale_wildcard_no_match(mock_publisher):
    """get_axis_scale should return 1.0 for axes not matching any wildcard."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("imu.*", 0.1)
    
    # Non-imu axes should not match and return default
    assert adapter.get_axis_scale("joy.x") == 1.0
    assert adapter.get_axis_scale("button.a") == 1.0


@pytest.mark.asyncio
async def test_get_axis_scale_exact_takes_precedence_over_wildcard(mock_publisher):
    """Exact axis match should take precedence over wildcard match."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("imu.*", 0.1)
    adapter.set_axis_scale("imu.pitch", 0.5)  # Override for pitch specifically
    
    assert adapter.get_axis_scale("imu.pitch") == 0.5  # Exact match wins
    assert adapter.get_axis_scale("imu.yaw") == 0.1   # Wildcard still applies


@pytest.mark.asyncio
async def test_publish_applies_scaling(mock_publisher):
    """publish should multiply value by the axis scale."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("joy.x", 0.5)
    
    await adapter.publish("joy.x", 1.0)
    
    # Verify the published value was scaled down
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.5  # 1.0 * 0.5


@pytest.mark.asyncio
async def test_publish_snapshot_applies_scaling(mock_publisher):
    """publish_snapshot should apply scaling to all axes."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_scale("joy.x", 0.5)
    adapter.set_axis_scale("joy.y", 2.0)
    # imu.pitch has no scale, should default to 1.0
    
    snapshot = {"joy.x": 1.0, "joy.y": 0.5, "imu.pitch": 1.0}
    await adapter.publish_snapshot(snapshot)
    
    # Get all published calls
    calls = [call[1] for call in mock_publisher.publish.await_args_list]
    
    # Find each axis call
    joy_x_call = next(c for c in calls if c["axis"] == "joy.x")
    joy_y_call = next(c for c in calls if c["axis"] == "joy.y")
    imu_pitch_call = next(c for c in calls if c["axis"] == "imu.pitch")
    
    assert joy_x_call["value"] == 0.5   # 1.0 * 0.5
    assert joy_y_call["value"] == 1.0   # 0.5 * 2.0
    assert imu_pitch_call["value"] == 1.0  # 1.0 * 1.0 (default)


# =============================================================================
# DEADZONE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_get_axis_deadzone_returns_zero_by_default(mock_publisher):
    """get_axis_deadzone should return 0.0 for axes with no deadzone defined."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # No deadzones have been set, should default to 0.0
    assert adapter.get_axis_deadzone("any_axis") == 0.0
    assert adapter.get_axis_deadzone("imu.pitch") == 0.0
    assert adapter.get_axis_deadzone("joy.x") == 0.0


@pytest.mark.asyncio
async def test_set_axis_deadzone_stores_exact_match(mock_publisher):
    """set_axis_deadzone should store and get_axis_deadzone should retrieve exact matches."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_deadzone("imu.pitch", 0.1)
    adapter.set_axis_deadzone("joy.x", 0.05)
    
    assert adapter.get_axis_deadzone("imu.pitch") == 0.1
    assert adapter.get_axis_deadzone("joy.x") == 0.05
    # Other axes should still default to 0.0
    assert adapter.get_axis_deadzone("imu.yaw") == 0.0


@pytest.mark.asyncio
async def test_get_axis_deadzone_wildcard_match(mock_publisher):
    """get_axis_deadzone should match wildcard patterns like 'imu.*'."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_deadzone("imu.*", 0.05)
    
    # All imu.* axes should match
    assert adapter.get_axis_deadzone("imu.pitch") == 0.05
    assert adapter.get_axis_deadzone("imu.yaw") == 0.05
    assert adapter.get_axis_deadzone("imu.roll") == 0.05


@pytest.mark.asyncio
async def test_get_axis_deadzone_wildcard_no_match(mock_publisher):
    """get_axis_deadzone should return 0.0 for axes not matching any wildcard."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_deadzone("imu.*", 0.05)
    
    # Non-imu axes should not match and return default
    assert adapter.get_axis_deadzone("joy.x") == 0.0
    assert adapter.get_axis_deadzone("button.a") == 0.0


@pytest.mark.asyncio
async def test_get_axis_deadzone_exact_takes_precedence_over_wildcard(mock_publisher):
    """Exact axis match should take precedence over wildcard match."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    adapter.set_axis_deadzone("imu.*", 0.1)
    adapter.set_axis_deadzone("imu.pitch", 0.2)  # Override for pitch specifically
    
    assert adapter.get_axis_deadzone("imu.pitch") == 0.2  # Exact match wins
    assert adapter.get_axis_deadzone("imu.yaw") == 0.1   # Wildcard still applies


@pytest.mark.asyncio
async def test_publish_applies_deadzone_to_rate(mock_publisher):
    """publish should apply deadzone to rate axes (symmetric around 0.0)."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to rate and deadzone
    adapter.set_axis_type("stick.x", "rate")
    adapter.set_axis_deadzone("stick.x", 0.1)
    
    # Value within deadzone should become 0.0
    await adapter.publish("stick.x", 0.05)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.0  # 0.05 is within [-0.1, 0.1]
    
    # Value outside deadzone should pass through
    await adapter.publish("stick.x", 0.5)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.5  # 0.5 is outside [-0.1, 0.1]


@pytest.mark.asyncio
async def test_publish_applies_deadzone_to_absolute_bi(mock_publisher):
    """publish should apply deadzone to absolute_bi axes (symmetric around 0.0)."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to absolute_bi and deadzone
    adapter.set_axis_type("stick.x", "absolute_bi")
    adapter.set_axis_deadzone("stick.x", 0.1)
    
    # Value within deadzone should become 0.0
    await adapter.publish("stick.x", -0.05)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.0  # -0.05 is within [-0.1, 0.1]
    
    # Negative value outside deadzone should pass through
    await adapter.publish("stick.x", -0.5)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == -0.5  # -0.5 is outside [-0.1, 0.1]


@pytest.mark.asyncio
async def test_publish_applies_deadzone_to_absolute_uni(mock_publisher):
    """publish should apply deadzone to absolute_uni axes (only positive side)."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to absolute_uni and deadzone
    adapter.set_axis_type("fader", "absolute_uni")
    adapter.set_axis_deadzone("fader", 0.05)
    
    # Small positive value within deadzone should become 0.0
    await adapter.publish("fader", 0.03)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.0  # 0.03 is within [0, 0.05]
    
    # Larger positive value outside deadzone should pass through
    await adapter.publish("fader", 0.5)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.5  # 0.5 is outside [0, 0.05]


@pytest.mark.asyncio
async def test_publish_no_deadzone_for_delta(mock_publisher):
    """publish should NOT apply deadzone to delta axes."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to delta and deadzone
    adapter.set_axis_type("mouse.x", "delta")
    adapter.set_axis_deadzone("mouse.x", 0.1)
    
    # Even small delta values should pass through unchanged
    await adapter.publish("mouse.x", 0.01)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.01  # No deadzone applied to delta


@pytest.mark.asyncio
async def test_publish_deadzone_after_scaling(mock_publisher):
    """publish should apply deadzone AFTER scaling."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to rate, deadzone, and scale
    adapter.set_axis_type("stick.x", "rate")
    adapter.set_axis_deadzone("stick.x", 1.0)  # Deadzone in scaled units
    adapter.set_axis_scale("stick.x", 10.0)  # Large scale to test order
    
    # Value 0.05 * 10.0 = 0.5, which is within deadzone [0, 1.0] -> becomes 0.0
    await adapter.publish("stick.x", 0.05)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.0  # scaling first: 0.05 * 10.0 = 0.5, then deadzone: 0.5 -> 0.0
    
    # Value 0.2 * 10.0 = 2.0, which is outside deadzone [0, 1.0] -> stays 2.0
    await adapter.publish("stick.x", 0.2)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 2.0  # scaling first: 0.2 * 10.0 = 2.0, then deadzone: 2.0 unchanged


@pytest.mark.asyncio
async def test_publish_snapshot_applies_deadzone(mock_publisher):
    """publish_snapshot should apply deadzone to all axes."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set up different deadzones for different axes
    adapter.set_axis_type("stick.x", "rate")
    adapter.set_axis_type("fader", "absolute_uni")
    adapter.set_axis_type("mouse.x", "delta")
    adapter.set_axis_deadzone("stick.x", 0.1)
    adapter.set_axis_deadzone("fader", 0.05)
    adapter.set_axis_deadzone("mouse.x", 0.1)  # Should be ignored for delta
    
    snapshot = {"stick.x": 0.05, "fader": 0.03, "mouse.x": 0.01}
    await adapter.publish_snapshot(snapshot)
    
    # Get all published calls
    calls = [call[1] for call in mock_publisher.publish.await_args_list]
    
    # Find each axis call
    stick_x_call = next(c for c in calls if c["axis"] == "stick.x")
    fader_call = next(c for c in calls if c["axis"] == "fader")
    mouse_x_call = next(c for c in calls if c["axis"] == "mouse.x")
    
    # stick.x (rate): 0.05 is within deadzone [-0.1, 0.1] -> 0.0
    assert stick_x_call["value"] == 0.0
    
    # fader (absolute_uni): 0.03 is within deadzone [0, 0.05] -> 0.0
    assert fader_call["value"] == 0.0
    
    # mouse.x (delta): deadzone should not apply -> 0.01
    assert mouse_x_call["value"] == 0.01


@pytest.mark.asyncio
async def test_publish_negative_deadzone_ignored(mock_publisher):
    """publish should ignore negative deadzone values (treat as 0.0)."""
    adapter = ConcreteTestAdapter(device="test_device")
    await adapter.start(input_publisher=mock_publisher)
    
    # Set axis type to rate and negative deadzone (should be ignored)
    adapter.set_axis_type("stick.x", "rate")
    adapter.set_axis_deadzone("stick.x", -0.1)  # Negative deadzone
    
    # Small value should pass through unchanged
    await adapter.publish("stick.x", 0.05)
    call_args = mock_publisher.publish.await_args
    assert call_args[1]["value"] == 0.05  # Negative deadzone ignored, value passes through