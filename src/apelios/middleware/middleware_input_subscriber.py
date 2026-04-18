"""Broker input subscriber for middleware.

This module parses broker JSON events and forwards validated source/value
updates to the middleware core.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from apelios.middleware.middleware_core import MappingMiddleware

logger = logging.getLogger(__name__)


class MiddlewareInputSubscriber:
	"""Parse broker payloads and forward source/value updates to the core."""

	def __init__(self, middleware: MappingMiddleware) -> None:
		self.middleware = middleware

	# this __call__ function is called, every time an instance of this class is created. the middleware runtime manager uses Dependency Inversion. The rtm creates an instance of the broker client and "maps" the on_message function of the broker client to the input hanlder
	def __call__(self, msg: Any) -> None:
		"""Handle one broker message.

		Expected payload contract (JSON bytes):
		{"source": "device.axis", "value": 0.5}
		"""
		try:
			payload = json.loads(msg.data)
		except Exception:
			logger.warning("Ignoring malformed middleware input payload", exc_info=True)
			return

		source = payload.get("source") if isinstance(payload, dict) else None
		value = payload.get("value") if isinstance(payload, dict) else None

		if not isinstance(source, str) or not source:
			logger.warning("Ignoring middleware input without valid 'source'")
			return

		try:
			numeric_value = float(value)
		except (TypeError, ValueError):
			logger.warning("Ignoring middleware input with non-numeric 'value'")
			return

		self.middleware.handle_input(source=source, value=numeric_value)