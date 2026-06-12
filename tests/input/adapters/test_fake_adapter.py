import pytest
from unittest.mock import AsyncMock

from apelios.input.adapters.fake_adapter import FakeAdapter


@pytest.fixture
def mock_publisher():
	"""Mock publisher used by the fake adapter test."""
	mock = AsyncMock()
	mock.publish = AsyncMock()
	return mock


@pytest.mark.asyncio
async def test_fake_adapter_publishes_two_values(mock_publisher):
	"""The fake adapter should emit a small set of known input events."""
	adapter = FakeAdapter(device="fake_device")

	await adapter.start(input_publisher=mock_publisher)

	# call tick which should poll_once() and then publish the snapshot
	await adapter.tick()

	assert mock_publisher.publish.await_count == 2
	mock_publisher.publish.assert_any_await(
		device="fake_device",
		axis="left_stick.x",
		value=0.5,
		type="absolute_bi",
	)
	mock_publisher.publish.assert_any_await(
		device="fake_device",
		axis="fader_1",
		value=0.75,
		type="absolute_uni",
	)


@pytest.mark.asyncio
async def test_tick_without_start_does_not_publish(mock_publisher):
	"""Ticking an adapter that wasn't started should not publish anything."""
	adapter = FakeAdapter(device="fake_device")

	# do not start the adapter
	await adapter.tick()

	assert mock_publisher.publish.await_count == 0


@pytest.mark.asyncio
async def test_start_stop_cycle(mock_publisher):
	"""Starting publishes on tick; stopping prevents publishes; restarting resumes."""
	adapter = FakeAdapter(device="fake_device")

	await adapter.start(input_publisher=mock_publisher)
	await adapter.tick()
	assert mock_publisher.publish.await_count == 2

	# stopping should prevent publishes
	await adapter.stop()
	await adapter.tick()
	assert mock_publisher.publish.await_count == 2

	# restarting should allow publishing again
	await adapter.start(input_publisher=mock_publisher)
	await adapter.tick()
	assert mock_publisher.publish.await_count == 4


@pytest.mark.asyncio
async def test_fake_adapter_publishes_with_types(mock_publisher):
	"""Fake adapter publishes with types from axis_types."""
	adapter = FakeAdapter(device="fake_device")
	
	await adapter.start(input_publisher=mock_publisher)
	await adapter.tick()
	
	# Verify both axes were published with their types
	assert mock_publisher.publish.await_count == 2
	
	calls = [call[1] for call in mock_publisher.publish.await_args_list]
	
	for call in calls:
		assert "type" in call
	
	stick_call = next(c for c in calls if c["axis"] == "left_stick.x")
	assert stick_call["type"] == "absolute_bi"
	
	fader_call = next(c for c in calls if c["axis"] == "fader_1")
	assert fader_call["type"] == "absolute_uni"