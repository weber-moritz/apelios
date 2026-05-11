import pytest
from unittest.mock import AsyncMock, MagicMock

from apelios.input.adapters.steamdeck_adapter import SteamDeckAdapter


@pytest.fixture
def mock_publisher():
	mock = MagicMock()
	mock.publish = AsyncMock()
	return mock


@pytest.mark.asyncio
async def test_steamdeck_adapter_publishes_all_controller_axes(mock_publisher):
	"""The Steam Deck adapter should publish all normalized controller axes."""
	deck = MagicMock()
	deck.start = MagicMock()
	deck.stop = MagicMock()
	deck.get_button_state = MagicMock(side_effect=lambda name: name in {"a", "start"})
	deck.get_analog_values = MagicMock(
		return_value={
			"left_trigger": 0.25,
			"right_trigger": 0.75,
			"left_stick_x": 1.0,
			"left_stick_y": -1.0,
			"right_stick_x": 0.5,
			"right_stick_y": -0.5,
			"left_trackpad_x": 0.11,
			"left_trackpad_y": 0.22,
			"right_trackpad_x": 0.33,
			"right_trackpad_y": 0.44,
			"left_trackpad_pressure": 123,
			"right_trackpad_pressure": 456,
		},
	)
	deck.get_imu_rates = MagicMock(return_value={"pitch": 10.0, "yaw": 20.0, "roll": 30.0})

	adapter = SteamDeckAdapter(device="steamdeck", deck=deck)

	await adapter.start(input_publisher=mock_publisher)
	await adapter.tick()

	assert mock_publisher.publish.call_count == 43
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="button.a", value=1.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="button.start", value=1.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="button.b", value=0.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="left_trigger", value=0.25)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_trigger", value=0.75)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="joy.x", value=1.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="joy.y", value=-1.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_stick.x", value=0.5)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_stick.y", value=-0.5)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="left_trackpad.x", value=0.11)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="left_trackpad.y", value=0.22)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_trackpad.x", value=0.33)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_trackpad.y", value=0.44)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="left_trackpad.pressure", value=123.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="right_trackpad.pressure", value=456.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="imu.pitch", value=10.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="imu.yaw", value=20.0)
	mock_publisher.publish.assert_any_call(device="steamdeck", axis="imu.roll", value=30.0)

	await adapter.stop()
	deck.stop.assert_called_once()