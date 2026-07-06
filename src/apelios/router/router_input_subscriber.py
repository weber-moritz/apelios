"""Broker input subscriber for router.

This module parses broker JSON events and forwards validated source/value
updates to the router core.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from apelios.router.router_core import MappingRouter

logger = logging.getLogger(__name__)


class RouterInputSubscriber:
	"""Parse broker payloads and forward source/value updates to the core."""

	def __init__(self, router: MappingRouter, runtime_manager: Any = None) -> None:
		self.router = router
		self.runtime_manager = runtime_manager

	async def __call__(self, msg: Any) -> None:
		"""Handle one broker message.

		Expected payload contract (JSON bytes):
		{"source": "device.axis", "value": 0.5, "type": "absolute_uni", "timestamp": 1234567890.123}
		"""
		try:
			payload = json.loads(msg.data)
		except Exception:
			logger.warning("Ignoring malformed router input payload", exc_info=True)
			return

		if not isinstance(payload, dict):
			logger.warning("Ignoring router input payload that is not a JSON object")
			return

		source = payload.get("source")
		value = payload.get("value")
		type_ = payload.get("type")
		timestamp = payload.get("timestamp")

		if not isinstance(source, str) or not source:
			logger.warning("Ignoring router input without valid 'source'")
			return

		if not isinstance(value, (int, float)):
			try:
				numeric_value = float(value)
			except (TypeError, ValueError):
				logger.warning("Ignoring router input with non-numeric 'value'")
				return
		else:
			numeric_value = value

		if not isinstance(type_, str) or not type_:
			logger.warning("Ignoring router input without valid 'type'")
			return

		# For Phase 7: pass full payload for pure passthrough
		# Call router which returns outputs dict
		outputs = self.router.handle_input(
			source=source, 
			value=numeric_value, 
			type=type_, 
			timestamp=timestamp,
			payload=payload
		)
		
		# Forward outputs to runtime manager for publishing on next tick
		if self.runtime_manager and outputs:
			self.runtime_manager.collect_outputs(outputs)
