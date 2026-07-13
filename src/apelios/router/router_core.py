"""Core mapping router for turning raw inputs into virtual outputs."""

from __future__ import annotations

from typing import Any


class MappingRouter:
	"""Pure passthrough mapping engine that routes inputs to targets.

	The router accepts raw input events through :meth:`handle_input`
	and immediately returns the mapped output payloads.
	No math, state, or compensation is applied here (reserved for fixture layer).
	"""

	def __init__(self, profile: dict[str, str] | None = None) -> None:
		"""Initialize with a routing profile mapping source to target.
		
		Args:
		    profile: Dict mapping input source (e.g., "input.device.axis") to output target (e.g., "target.group1.param")
		"""
		self.profile: dict[str, str] = profile or {}

	def handle_input(self, source: str, value: float, type: str | None = None, timestamp: float | None = None, payload: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
		"""Map an input source to its target and return the output payload immediately.
		
		This is a pure passthrough - no state is stored, no math is applied.
		The payload from the input layer flows through unchanged.
		
		Args:
		    source: The input source identifier (e.g., "input.device.axis")
		    value: The raw input value
		    type: The type from the input layer (absolute_uni, absolute_bi, delta, rate)
		    timestamp: The timestamp from the input layer
		    payload: Optional full payload from input layer for pure passthrough
		
		Returns:
		    Dict mapping target names to their payload dicts.
		    Example: {"target.group1.param": {"value": 0.5, "type": "absolute_uni", "timestamp": 123.0, "source": "input.device.axis"}}
		    Returns empty dict {} if source is not mapped.
		"""
		outputs: dict[str, dict[str, Any]] = {}
		
		# Look up the target for this source
		target = self.profile.get(source)
		if not target:
			# Source not mapped, return empty dict
			return outputs
		
		# For Phase 7: use full payload if provided (pure passthrough)
		if payload is not None:
			outputs[target] = payload
		else:
			# Legacy: create payload from individual fields
			outputs[target] = {
				"value": float(value),
				"type": type,
				"timestamp": timestamp,
				"source": source,
			}
		
		return outputs
