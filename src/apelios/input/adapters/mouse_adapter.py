"""Mouse input adapter with a Linux evdev backend."""

from __future__ import annotations

import asyncio
import os
import select
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apelios.input.base_input_adapter import BaseInputAdapter


try:
	from evdev import InputDevice, ecodes
except ImportError as exc:  # pragma: no cover - dependency should be present in the venv
	InputDevice = None
	ecodes = None
	_EvdevImportError = exc
else:
	_EvdevImportError = None


@dataclass(slots=True)
class LinuxEvdevMouse:
	"""Read relative mouse input from a Linux evdev device."""

	device_path: str | None = None
	grab: bool = False
	_device: Any | None = None

	def __post_init__(self) -> None:
		if sys.platform != "linux":
			raise NotImplementedError("LinuxEvdevMouse is only available on Linux")
		if InputDevice is None:
			raise ImportError("evdev is required for Linux mouse input") from _EvdevImportError

	async def open(self) -> None:
		"""Open the evdev device if it has not been opened yet."""
		if self._device is not None:
			return

		resolved_path = self.device_path or self._resolve_device_path()
		self._device = InputDevice(resolved_path)
		if self.grab:
			self._device.grab()

	async def close(self) -> None:
		"""Release the evdev device if one is open."""
		device = self._device
		if device is None:
			return

		try:
			if self.grab:
				device.ungrab()
		finally:
			device.close()
			self._device = None

	async def poll(self) -> dict[str, float]:
		"""Collect pending relative mouse events and return the current deltas."""
		await self.open()
		return await asyncio.to_thread(self._poll_sync)

	def _resolve_device_path(self) -> str:
		"""Locate a mouse-like evdev device under /dev/input/by-id."""
		by_id = Path("/dev/input/by-id")
		if by_id.exists():
			for candidate in sorted(by_id.iterdir()):
				name = candidate.name
				if name.endswith("-event-mouse") or name.endswith("-mouse"):
					return os.path.realpath(candidate)

		fallback = Path("/dev/input/mouse0")
		if fallback.exists():
			return str(fallback)

		raise FileNotFoundError("No Linux mouse device was found under /dev/input")

	def _poll_sync(self) -> dict[str, float]:
		"""Drain pending events from the evdev device in the current thread.

		Always returns x and y (defaulting to 0.0 when the mouse is still).
		Uses a non-blocking select so the 60Hz tick loop is never held up
		waiting for hardware events.
		"""
		if self._device is None:
			raise RuntimeError("Mouse device has not been opened")

		# x and y default to 0.0 — the mouse is at rest unless told otherwise.
		state: dict[str, float] = {"x": 0.0, "y": 0.0}

		# Non-blocking check: if no events are queued right now, return zeros.
		readable, _, _ = select.select([self._device.fd], [], [], 0)
		if not readable:
			return state

		events = self._device.read()
		for event in events:
			event_type, code, value = self._coerce_event(event)
			if event_type == ecodes.EV_REL:
				if code == ecodes.REL_X:
					state["x"] = state.get("x", 0.0) + float(value)
				elif code == ecodes.REL_Y:
					state["y"] = state.get("y", 0.0) + float(value)
				elif code == ecodes.REL_WHEEL:
					state["wheel"] = state.get("wheel", 0.0) + float(value)
				elif code == ecodes.REL_HWHEEL:
					state["wheel_h"] = state.get("wheel_h", 0.0) + float(value)
			elif event_type == ecodes.EV_KEY:
				if code == ecodes.BTN_LEFT:
					state["left_button"] = float(value)
				elif code == ecodes.BTN_RIGHT:
					state["right_button"] = float(value)
				elif code == ecodes.BTN_MIDDLE:
					state["middle_button"] = float(value)

		return state

	@staticmethod
	def _coerce_event(event: Any) -> tuple[int, int, int]:
		"""Accept both evdev input events and tuple-based test doubles."""
		if hasattr(event, "type") and hasattr(event, "code") and hasattr(event, "value"):
			return int(event.type), int(event.code), int(event.value)

		if isinstance(event, tuple) and len(event) == 3:
			return int(event[0]), int(event[1]), int(event[2])

		raise TypeError(f"Unsupported evdev event shape: {event!r}")


class MouseAdapter(BaseInputAdapter):
	"""Linux mouse adapter that publishes normalized relative motion."""

	_AXIS_TYPES = {
		"x": "delta",
		"y": "delta",
		"wheel": "delta",
		"wheel_h": "delta",
		"left_button": "absolute_uni",
		"right_button": "absolute_uni",
		"middle_button": "absolute_uni",
	}

	# Default sensitivity scaling for mouse axes
	# Mouse deltas can be large (50-100+ per frame), so we scale them down
	# to get smooth, controllable movement.
	# At 60Hz: 100px/frame * 0.002 scale = 0.2 per frame, ~5 frames to full range
	# Wheel is more sensitive (0.05) since scroll wheels have finer control
	_DEFAULT_AXIS_SCALES = {
		"x": 0.002,
		"y": 0.002,
		"wheel": 0.05,
		"wheel_h": 0.05,
	}

	def __init__(self, device: str = "mouse", backend: LinuxEvdevMouse | None = None):
		super().__init__(device=device)
		self._backend = backend or self._build_backend()
		
		# Set axis types for all known axes
		for axis, axis_type in self._AXIS_TYPES.items():
			self.set_axis_type(axis, axis_type)
		
		# Set default sensitivity scaling for mouse axes
		for axis, scale in self._DEFAULT_AXIS_SCALES.items():
			self.set_axis_scale(axis, scale)

	def _build_backend(self) -> LinuxEvdevMouse:
		"""Create the Linux backend for the current platform."""
		if sys.platform != "linux":
			raise NotImplementedError("MouseAdapter currently supports Linux only")
		return LinuxEvdevMouse()

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Read the latest mouse deltas and replace the current snapshot."""
		del dt
		self.snapshot = await self._backend.poll() or {}

	async def stop(self) -> None:
		"""Stop the adapter and close the backend device if needed."""
		await super().stop()
		backend = self._backend
		close = getattr(backend, "close", None)
		if callable(close):
			await close()