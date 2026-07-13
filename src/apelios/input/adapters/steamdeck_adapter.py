"""Steam Deck input adapter built on the bitsteam library."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

from apelios.input.base_input_adapter import BaseInputAdapter


try:
	from bitsteam import SteamDeck
except ImportError:
	try:
		from bitsteam.deck import SteamDeck
	except ImportError as exc:  # pragma: no cover - exercised only when bitsteam is absent
		SteamDeck = None
		_BitSteamImportError = exc
	else:
		_BitSteamImportError = None
else:
	_BitSteamImportError = None


class _NullSteamDeck:
	"""Fallback backend used when bitsteam is unavailable."""

	def get_button_state(self, button_name: str) -> bool:
		del button_name
		return False

	def start(self) -> None:
		return None

	def stop(self) -> None:
		return None

	def get_analog_values(self) -> dict[str, float]:
		return {}

	def get_imu_rates(self) -> dict[str, float]:
		return {}


class SteamDeckAdapter(BaseInputAdapter):
	"""Publish Steam Deck axes through the shared input runtime."""

	# Single unified mapping: bitsteam raw axis names -> Apelios internal names
	_BITSTEAM_AXIS_MAP = {
		# Buttons (map to button.* namespace)
		"a": "button.a",
		"b": "button.b",
		"x": "button.x",
		"y": "button.y",
		"l1": "button.l1",
		"r1": "button.r1",
		"l2_click": "button.l2_click",
		"r2_click": "button.r2_click",
		"dpad_up": "button.dpad_up",
		"dpad_down": "button.dpad_down",
		"dpad_left": "button.dpad_left",
		"dpad_right": "button.dpad_right",
		"select": "button.select",
		"start": "button.start",
		"steam": "button.steam",
		"quick_access": "button.quick_access",
		"l_lower_grip": "button.l_lower_grip",
		"r_lower_grip": "button.r_lower_grip",
		"l_upper_grip": "button.l_upper_grip",
		"r_upper_grip": "button.r_upper_grip",
		"l_stick_press": "button.l_stick_press",
		"r_stick_press": "button.r_stick_press",
		"l_stick_touch": "button.l_stick_touch",
		"r_stick_touch": "button.r_stick_touch",
		"l_trackpad_touch": "button.l_trackpad_touch",
		"l_trackpad_press": "button.l_trackpad_press",
		"r_trackpad_touch": "button.r_trackpad_touch",
		"r_trackpad_press": "button.r_trackpad_press",
		# Analog sticks (remap to simpler names)
		"left_stick_x": "joy.x",
		"left_stick_y": "joy.y",
		"right_stick_x": "right_stick.x",
		"right_stick_y": "right_stick.y",
		# Triggers
		"left_trigger": "left_trigger",
		"right_trigger": "right_trigger",
		# Trackpads
		"left_trackpad_x": "left_trackpad.x",
		"left_trackpad_y": "left_trackpad.y",
		"right_trackpad_x": "right_trackpad.x",
		"right_trackpad_y": "right_trackpad.y",
		"left_trackpad_pressure": "left_trackpad.pressure",
		"right_trackpad_pressure": "right_trackpad.pressure",
		# IMU (map bitsteam's pitch/yaw/roll to imu.* namespace)
		"pitch": "imu.pitch",
		"yaw": "imu.yaw",
		"roll": "imu.roll",
	}

	_AXIS_TYPES = {
		# Buttons: absolute_uni (0 or 1)
		"button.a": "absolute_uni",
		"button.b": "absolute_uni",
		"button.x": "absolute_uni",
		"button.y": "absolute_uni",
		"button.l1": "absolute_uni",
		"button.r1": "absolute_uni",
		"button.l2_click": "absolute_uni",
		"button.r2_click": "absolute_uni",
		"button.dpad_up": "absolute_uni",
		"button.dpad_down": "absolute_uni",
		"button.dpad_left": "absolute_uni",
		"button.dpad_right": "absolute_uni",
		"button.select": "absolute_uni",
		"button.start": "absolute_uni",
		"button.steam": "absolute_uni",
		"button.quick_access": "absolute_uni",
		"button.l_lower_grip": "absolute_uni",
		"button.r_lower_grip": "absolute_uni",
		"button.l_upper_grip": "absolute_uni",
		"button.r_upper_grip": "absolute_uni",
		"button.l_stick_press": "absolute_uni",
		"button.r_stick_press": "absolute_uni",
		"button.l_stick_touch": "absolute_uni",
		"button.r_stick_touch": "absolute_uni",
		"button.l_trackpad_touch": "absolute_uni",
		"button.l_trackpad_press": "absolute_uni",
		"button.r_trackpad_touch": "absolute_uni",
		"button.r_trackpad_press": "absolute_uni",
		# Analog sticks: absolute_bi (-1 to 1)
		"joy.x": "absolute_bi",
		"joy.y": "absolute_bi",
		"right_stick.x": "absolute_bi",
		"right_stick.y": "absolute_bi",
		# Triggers: absolute_uni (0 to 1)
		"left_trigger": "absolute_uni",
		"right_trigger": "absolute_uni",
		# Trackpads: absolute_bi
		"left_trackpad.x": "absolute_bi",
		"left_trackpad.y": "absolute_bi",
		"right_trackpad.x": "absolute_bi",
		"right_trackpad.y": "absolute_bi",
		"left_trackpad.pressure": "absolute_uni",
		"right_trackpad.pressure": "absolute_uni",
		# IMU: rate
		"imu.pitch": "rate",
		"imu.yaw": "rate",
		"imu.roll": "rate",
	}

	# Per-axis sensitivity scaling factors (default = 1.0)
	# IMU needs 0.1x to convert 10 real revolutions -> 1 output revolution
	_AXIS_SCALES = {
		"imu.*": 1,  # Wildcard matches imu.pitch, imu.yaw, imu.roll
		"joy.x": 0.2,  # Scale down left stick for finer control
		"joy.y": 0.2,  # Scale down left stick for finer control
		"right_stick.x": 0.2,  # Scale down right stick for finer control
		"right_stick.y": 0.2,  # Scale down right stick for finer control
	}

	def __init__(self, device: str = "steamdeck", deck: Any | None = None) -> None:
		super().__init__(device=device)
		if deck is not None:
			self._deck = deck
		elif SteamDeck is not None:
			self._deck = SteamDeck()
		else:
			self._deck = _NullSteamDeck()
		self._is_deck_started = False
		
		# Set axis types for all known axes
		for axis, axis_type in self._AXIS_TYPES.items():
			self.set_axis_type(axis, axis_type)
		
		# Set axis scales for all known axes
		for axis, scale in self._AXIS_SCALES.items():
			self.set_axis_scale(axis, scale)

	async def start(self, input_publisher) -> None:
		"""Attach the shared publisher and start the Steam Deck listener."""
		if self._is_running:
			return

		await super().start(input_publisher)
		try:
			if not self._is_deck_started:
				await self._call_backend(self._deck.start)
				self._is_deck_started = True
		except Exception:
			await super().stop()
			raise

	async def stop(self) -> None:
		"""Stop the adapter and release the Steam Deck listener."""
		try:
			if self._is_deck_started:
				await self._call_backend(self._deck.stop)
		finally:
			self._is_deck_started = False
			await super().stop()

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Read every controller axis into the current snapshot."""
		del dt

		if not self._is_deck_started:
			raise RuntimeError("SteamDeckAdapter must be started before polling")

		analogs = await self._call_backend(self._deck.get_analog_values) or {}
		imu_rates = await self._call_backend(self._deck.get_imu_rates) or {}

		snapshot: dict[str, float] = {}
		
		# Poll all axes from the unified map
		for raw_name,apelios_name in self._BITSTEAM_AXIS_MAP.items():
			if apelios_name.startswith("button."):
				# Buttons: use get_button_state
				pressed = await self._call_backend(self._deck.get_button_state, raw_name)
				snapshot[apelios_name] = float(bool(pressed))
			elif apelios_name.startswith("imu."):
				# IMU: use get_imu_rates
				snapshot[apelios_name] = float(imu_rates.get(raw_name, 0.0))
			else:
				# Analog: use get_analog_values
				snapshot[apelios_name] = float(analogs.get(raw_name, 0.0))

		self.snapshot = snapshot

	@staticmethod
	async def _call_backend(method, *args, **kwargs):
		result = method(*args, **kwargs)
		if inspect.isawaitable(result):
			return await result
		return result