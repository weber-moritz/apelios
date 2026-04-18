"""Middleware output publisher for broker events.

This module publishes processed middleware state to the broker.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apelios.broker.broker_client import BrokerClient

logger = logging.getLogger(__name__)


class MiddlewareOutputPublisher:
    """Publish middleware virtual output state to broker."""

    def __init__(self, broker: BrokerClient) -> None:
        self.broker = broker

    async def publish(self, output_state: dict[str, float]) -> None:
        """Publish output state snapshot to broker.

        Args:
            output_state: dict mapping target name to value (e.g., {"group1.pan": 0.6})
        """
        for target, value in output_state.items():
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                logger.warning("Skipping output publish for non-numeric value", extra={"target": target})
                continue

            subject = f"outputs.{target}"
            payload = json.dumps({"value": numeric_value}).encode("utf-8")

            try:
                await self.broker.publish(subject, payload)
            except Exception as e:
                logger.error(f"Failed to publish {subject} to broker: {e}")