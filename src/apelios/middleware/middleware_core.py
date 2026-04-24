"""Core mapping middleware for turning raw inputs into virtual outputs."""

from __future__ import annotations

from typing import Any


class MappingMiddleware:
	"""Snapshot-based mapping engine used by the middleware tests.

	The middleware accepts raw input events asynchronously through
	:meth:`handle_input` and applies them in a synchronous frame step through
	:meth:`process_frame`.
	"""

	def __init__(self, profile: dict[str, dict[str, Any]] | None = None) -> None:
		self.profile: dict[str, dict[str, Any]] = profile or {}
		self.current_raw_input: dict[str, float] = {}
		self.previous_abs_input: dict[str, float] = {}
		self.virtual_output_state: dict[str, float] = {}

	def handle_input(self, source: str, value: float) -> None:
		"""Store the latest raw value for a source until the next frame."""

		self.current_raw_input[source] = float(value)

	def _clamp_unit(self, value: float) -> float:
		"""Clamp a value to the [0.0, 1.0] range."""

		return max(0.0, min(1.0, value))


	def process_frame(self, dt: float) -> None:
		"""Apply the latest raw inputs to the virtual output state."""

		snapshot = self.current_raw_input.copy()
		output_delta_buffer: dict[str, float] = {}

		for source, current_value in snapshot.items():
			mapping = self.profile.get(source)
			if not mapping:
				continue

			target = mapping.get("target")
			if not isinstance(target, str):
				continue

			mapping_type = mapping.get("type")
			if mapping_type == "absolute_to_delta":
				mapping_type = "delta"
			deadzone = float(mapping.get("deadzone", 0.0))
			sensitivity = float(mapping.get("sensitivity", 1.0))

			if mapping_type == "absolute":
				self.virtual_output_state[target] = self._clamp_unit(float(current_value))
				self.previous_abs_input[source] = float(current_value)
				continue

			previous_value = self.previous_abs_input.get(source)
			if previous_value is None:
				# Prime state on first sample so no output jumps occur.
				if mapping_type == "rate":
					self.previous_abs_input[source] = 0.0
				else:
					self.previous_abs_input[source] = float(current_value)
				continue

			if mapping_type == "delta":
				raw_delta = float(current_value) - previous_value
				if abs(raw_delta) < deadzone:
					raw_delta = 0.0
				output_delta_buffer[target] = output_delta_buffer.get(target, 0.0) + raw_delta * sensitivity
				self.previous_abs_input[source] = float(current_value)
			elif mapping_type == "rate":
				rate_value = float(current_value)
				if abs(rate_value) < deadzone:
					rate_value = 0.0
				new_abs_value = previous_value + rate_value * dt
				raw_delta = new_abs_value - previous_value
				output_delta_buffer[target] = output_delta_buffer.get(target, 0.0) + raw_delta * sensitivity
				self.previous_abs_input[source] = new_abs_value

		for target, output_delta in output_delta_buffer.items():
			current_output = self.virtual_output_state.get(target, 0.0)
			self.virtual_output_state[target] = self._clamp_unit(current_output + output_delta)