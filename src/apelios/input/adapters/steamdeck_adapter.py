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

	_BUTTON_NAMES = [
		"a",
		"b",
		"x",
		"y",
		"l1",
		"r1",
		"l2_click",
		"r2_click",
		"dpad_up",
		"dpad_down",
		"dpad_left",
		"dpad_right",
		"select",
		"start",
		"steam",
		"quick_access",
		"l_lower_grip",
		"r_lower_grip",
		"l_upper_grip",
		"r_upper_grip",
		"l_stick_press",
		"r_stick_press",
		"l_stick_touch",
		"r_stick_touch",
		"l_trackpad_touch",
		"l_trackpad_press",
		"r_trackpad_touch",
		"r_trackpad_press",
	]

	_ANALOG_NAMES = [
		"left_trigger",
		"right_trigger",
		"left_stick_x",
		"left_stick_y",
		"right_stick_x",
		"right_stick_y",
		"left_trackpad_x",
		"left_trackpad_y",
		"right_trackpad_x",
		"right_trackpad_y",
		"left_trackpad_pressure",
		"right_trackpad_pressure",
	]

	_ANALOG_AXIS_MAP = {
		"left_trigger": "left_trigger",
		"right_trigger": "right_trigger",
		"left_stick_x": "joy.x",
		"left_stick_y": "joy.y",
		"right_stick_x": "right_stick.x",
		"right_stick_y": "right_stick.y",
		"left_trackpad_x": "left_trackpad.x",
		"left_trackpad_y": "left_trackpad.y",
		"right_trackpad_x": "right_trackpad.x",
		"right_trackpad_y": "right_trackpad.y",
		"left_trackpad_pressure": "left_trackpad.pressure",
		"right_trackpad_pressure": "right_trackpad.pressure",
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
		for button_name in self._BUTTON_NAMES:
			pressed = await self._call_backend(self._deck.get_button_state, button_name)
			snapshot[f"button.{button_name}"] = float(bool(pressed))

		if isinstance(analogs, Mapping):
			for raw_axis in self._ANALOG_NAMES:
				axis = self._normalize_analog_axis(raw_axis)
				raw_value = analogs.get(raw_axis, 0.0)
				snapshot[axis] = float(raw_value)

		if isinstance(imu_rates, Mapping):
			snapshot["imu.pitch"] = float(imu_rates.get("pitch", 0.0))
			snapshot["imu.yaw"] = float(imu_rates.get("yaw", 0.0))
			snapshot["imu.roll"] = float(imu_rates.get("roll", 0.0))

		self.snapshot = snapshot

	@classmethod
	def _normalize_analog_axis(cls, raw_axis: str) -> str:
		return cls._ANALOG_AXIS_MAP.get(raw_axis, raw_axis)

	@staticmethod
	async def _call_backend(method, *args, **kwargs):
		result = method(*args, **kwargs)
		if inspect.isawaitable(result):
			return await result
		return result