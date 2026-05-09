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
	)
	mock_publisher.publish.assert_any_await(
		device="fake_device",
		axis="fader_1",
		value=0.75,
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