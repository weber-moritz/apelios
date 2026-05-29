"""Core mapping middleware for turning raw inputs into virtual outputs."""

from __future__ import annotations

import time
from typing import Any


class MappingMiddleware:
	"""Pure passthrough mapping engine that enriches payloads with intent and target.

	The middleware accepts raw input events asynchronously through
	:meth:`handle_input` and creates enriched payloads on :meth:`process_frame`.
	No math, state, or compensation is applied here (reserved for fixture layer).
	"""

	def __init__(self, profile: dict[str, dict[str, Any]] | None = None) -> None:
		self.profile: dict[str, dict[str, Any]] = profile or {}
		self.current_raw_input: dict[str, float] = {}
		self.virtual_output_state: dict[str, float] = {}  # backward compat: just values
		self.enriched_outputs: dict[str, dict[str, Any]] = {}  # {target: {target, value, intent, timestamp}}

	def handle_input(self, source: str, value: float) -> None:
		"""Store the latest raw value for a source until the next frame."""
		self.current_raw_input[source] = float(value)

	def process_frame(self, dt: float) -> None:
		"""Create enriched payloads by mapping sources to targets and attaching intent.
		
		No math is applied; this is a pure passthrough router.
		"""
		snapshot = self.current_raw_input.copy()
		self.enriched_outputs = {}

		for source, value in snapshot.items():
			mapping = self.profile.get(source)
			if not mapping:
				continue

			target = mapping.get("target")
			if not isinstance(target, str):
				continue

			# Get intent from mapping (previously named "type")
			intent = mapping.get("intent")
			if not isinstance(intent, str):
				continue

			# Create enriched payload with target, value, intent, and timestamp
			enriched_payload = {
				"target": target,
				"value": float(value),
				"intent": intent,
				"timestamp": time.time(),
			}

			self.enriched_outputs[target] = enriched_payload
			# Backward compat: also update virtual_output_state with just the value
			self.virtual_output_state[target] = float(value)

		# Clear transient input buffer after processing
		self.current_raw_input = {}