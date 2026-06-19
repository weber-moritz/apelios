"""Core mapping middleware for turning raw inputs into virtual outputs."""

from __future__ import annotations

from typing import Any


class MappingMiddleware:
	"""Pure passthrough mapping engine that routes inputs to targets.

	The middleware accepts raw input events through :meth:`handle_input`
	and immediately returns the mapped output payloads.
	No math, state, or compensation is applied here (reserved for fixture layer).
	"""

	def __init__(self, profile: dict[str, str] | None = None) -> None:
		"""Initialize with a routing profile mapping source to target.
		
		Args:
		    profile: Dict mapping input source (e.g., "input.device.axis") to output target (e.g., "target.group1.param")
		"""
		self.profile: dict[str, str] = profile or {}

	def handle_input(self, source: str, value: float, type: str | None = None, timestamp: float | None = None) -> dict[str, dict[str, Any]]:
		"""Map an input source to its target and return the output payload immediately.
		
		This is a pure passthrough - no state is stored, no math is applied.
		The type and timestamp from the input layer flow through unchanged.
		
		Args:
		    source: The input source identifier (e.g., "input.device.axis")
		    value: The raw input value
		    type: The type from the input layer (absolute_uni, absolute_bi, delta, rate)
		    timestamp: The timestamp from the input layer
		
		Returns:
		    Dict mapping target names to their payload dicts.
		    Example: {"target.group1.param": {"value": 0.5, "type": "absolute_uni", "timestamp": 123.0}}
		    Returns empty dict {} if source is not mapped.
		"""
		outputs: dict[str, dict[str, Any]] = {}
		
		# Look up the target for this source
		target = self.profile.get(source)
		if not target:
			# Source not mapped, return empty dict
			return outputs
		
		# Create the output payload with the input's type, timestamp, and source
		# No modification - pure passthrough
		payload = {
			"value": float(value),
			"type": type,
			"timestamp": timestamp,
			"source": source,  # Include source for Phase 6 many-to-one summation
		}
		
		# Map source to target
		outputs[target] = payload
		
		return outputs
