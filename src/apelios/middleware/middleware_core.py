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
		self.previous_raw_input: dict[str, float] = {}
		self.virtual_output_state: dict[str, float] = {}

	def handle_input(self, source: str, value: float) -> None:
		"""Store the latest raw value for a source until the next frame."""

		self.current_raw_input[source] = float(value)

	def process_frame(self) -> None:
		"""Apply the latest raw inputs to the virtual output state."""

		for source, current_value in list(self.current_raw_input.items()):
			mapping = self.profile.get(source)
			if not mapping:
				continue

			target = mapping.get("target")
			if not isinstance(target, str):
				continue

			mapping_type = mapping.get("type")

			if mapping_type == "absolute":
				self.virtual_output_state[target] = current_value
			elif mapping_type == "absolute_to_delta":
				previous_value = self.previous_raw_input.get(source)
				if previous_value is not None:
					sensitivity = float(mapping.get("sensitivity", 1.0))
					delta = current_value - previous_value
					current_output = self.virtual_output_state.get(target, 0.0)
					self.virtual_output_state[target] = current_output + delta * sensitivity

			self.previous_raw_input[source] = current_value
