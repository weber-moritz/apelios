"""End-to-end integration tests for the input layer.

Tests the full lifecycle: multiple adapters, runtime start/stop, multiple ticks,
and broker message flow.
"""

import json
import pytest

from apelios.input.adapters import FakeAdapter
from apelios.input.base_input_adapter import BaseInputAdapter
from apelios.input.input_runtime_manager import InputRuntimeManager


class CountingAdapter(BaseInputAdapter):
	"""Test adapter that populates snapshot with incrementing values."""

	def __init__(self, device: str):
		super().__init__(device=device)
		self.poll_count = 0

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Increment counter and populate snapshot."""
		self.poll_count += 1
		self.snapshot["count"] = float(self.poll_count)
		self.snapshot["timestamp"] = 0.016 * self.poll_count


@pytest.mark.asyncio
async def test_input_layer_multiple_adapters_multiple_ticks(mock_broker_client):
	"""Full integration: register multiple adapters, tick multiple times, verify messages."""
	runtime = InputRuntimeManager(broker_client=mock_broker_client)

	# Register two adapters with different device names
	fake_device = FakeAdapter(device="fake_gamepad")
	counting_device = CountingAdapter(device="counting_sensor")

	runtime.register_adapter(fake_device)
	runtime.register_adapter(counting_device)

	assert len(runtime.registered_adapters) == 2

	# Start the runtime and all adapters
	await runtime.start_registered_adapters()

	assert len(runtime._running_adapters) == 2

	# Execute three ticks
	await runtime.tick(dt=0.016)
	await runtime.tick(dt=0.016)
	await runtime.tick(dt=0.016)

	# FakeAdapter publishes 2 values (left_stick.x, fader_1)
	# CountingAdapter publishes 2 values (count, timestamp)
	# Total: 4 messages per tick × 3 ticks = 12 publish calls
	assert mock_broker_client.publish.await_count == 12

	# Verify messages have the correct structure and content
	messages = []
	for call in mock_broker_client.publish.await_args_list:
		subject, msg = call.args
		messages.append((subject, json.loads(msg.decode("utf-8"))))

	# Check that we have messages from both devices
	fake_gamepad_msgs = [m for m in messages if m[0] == "input.fake_gamepad"]
	counting_sensor_msgs = [m for m in messages if m[0] == "input.counting_sensor"]

	assert len(fake_gamepad_msgs) == 6  # 2 values × 3 ticks
	assert len(counting_sensor_msgs) == 6  # 2 values × 3 ticks

	# Verify fake adapter messages (should be the same each tick)
	for msg in fake_gamepad_msgs[:2]:
		assert msg[1]["source"] in ["fake_gamepad.left_stick.x", "fake_gamepad.fader_1"]
		if msg[1]["source"] == "fake_gamepad.left_stick.x":
			assert msg[1]["value"] == 0.5
		else:
			assert msg[1]["value"] == 0.75

	# Verify counting sensor messages (should increment each tick)
	count_msgs = [m for m in counting_sensor_msgs if m[1]["source"] == "counting_sensor.count"]
	assert len(count_msgs) == 3
	assert count_msgs[0][1]["value"] == 1.0
	assert count_msgs[1][1]["value"] == 2.0
	assert count_msgs[2][1]["value"] == 3.0


@pytest.mark.asyncio
async def test_input_layer_adapter_stop_and_restart(mock_broker_client):
	"""Test that stopping and restarting adapters works correctly."""
	runtime = InputRuntimeManager(broker_client=mock_broker_client)

	adapter = FakeAdapter(device="test_device")
	runtime.register_adapter(adapter)
	await runtime.start_registered_adapters()

	# First tick
	await runtime.tick(dt=0.016)
	assert mock_broker_client.publish.await_count == 2

	# Stop the adapter
	await runtime.stop_adapter(adapter)
	assert not runtime.adapter_is_running(adapter)

	# Tick should not publish (adapter not running)
	await runtime.tick(dt=0.016)
	assert mock_broker_client.publish.await_count == 2

	# Restart the adapter
	await runtime.start_adapter(adapter)
	assert runtime.adapter_is_running(adapter)

	# Tick should publish again
	await runtime.tick(dt=0.016)
	assert mock_broker_client.publish.await_count == 4


@pytest.mark.asyncio
async def test_input_layer_runtime_lifecycle(mock_broker_client):
	"""Test runtime start and stop lifecycle with adapters."""
	runtime = InputRuntimeManager(broker_client=mock_broker_client)
	assert not runtime.is_running()

	# Start runtime
	await runtime.start()
	assert runtime.is_running()
	mock_broker_client.connect.assert_awaited_once()

	# Register and start adapter
	adapter = FakeAdapter(device="test_device")
	runtime.register_adapter(adapter)
	await runtime.start_adapter(adapter)

	# Tick should publish
	await runtime.tick(dt=0.016)
	assert mock_broker_client.publish.await_count == 2

	# Stop runtime
	await runtime.stop()
	assert not runtime.is_running()

	# Adapter should still be running (stop doesn't stop adapters)
	assert runtime.adapter_is_running(adapter)

	# Tick should still work
	await runtime.tick(dt=0.016)
	assert mock_broker_client.publish.await_count == 4


@pytest.mark.asyncio
async def test_input_layer_adapter_with_empty_snapshot(mock_broker_client):
	"""Test adapter that doesn't populate snapshot doesn't publish."""

	class SilentAdapter(BaseInputAdapter):
		"""Adapter that never populates snapshot."""

		async def poll_once(self, dt: float = 0.016) -> None:
			# Do nothing, snapshot stays empty
			pass

	runtime = InputRuntimeManager(broker_client=mock_broker_client)

	adapter = SilentAdapter(device="silent_device")
	runtime.register_adapter(adapter)
	await runtime.start_registered_adapters()

	# Tick should not publish (empty snapshot)
	await runtime.tick(dt=0.016)

	assert mock_broker_client.publish.await_count == 0


@pytest.mark.asyncio
async def test_input_layer_multiple_ticks_dt_parameter(mock_broker_client):
	"""Verify dt parameter is passed through the tick chain."""

	collected_dts = []

	class DtCheckingAdapter(BaseInputAdapter):
		async def poll_once(self, dt: float = 0.016) -> None:
			collected_dts.append(dt)
			self.snapshot["dt"] = dt

	runtime = InputRuntimeManager(broker_client=mock_broker_client)

	adapter = DtCheckingAdapter(device="dt_device")
	runtime.register_adapter(adapter)
	await runtime.start_registered_adapters()

	# Tick with different dt values
	await runtime.tick(dt=0.016)
	await runtime.tick(dt=0.032)
	await runtime.tick(dt=0.008)

	assert collected_dts == [0.016, 0.032, 0.008]
