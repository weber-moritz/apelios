"""Router output publisher for broker events.

This module publishes router outputs to target.* subjects.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apelios.broker.broker_client import BrokerClient

logger = logging.getLogger(__name__)


class RouterOutputPublisher:
    """Publish router outputs to broker."""

    def __init__(self, broker: BrokerClient) -> None:
        self.broker = broker

    async def publish(self, outputs: dict[str, dict[str, Any]]) -> None:
        """Publish output payloads to target.* subjects.

        Args:
            outputs: dict mapping target name to payload
                e.g., {"group1.pan": {"value": 0.5, "type": "delta", "timestamp": 123.0}}
        """
        for target, payload in outputs.items():
            try:
                payload_json = json.dumps(payload).encode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to serialize payload for {target}: {e}")
                continue

            # Publish to target.* subject
            try:
                target_subject = f"target.{target}"
                await self.broker.publish(target_subject, payload_json)
            except Exception as e:
                logger.error(f"Failed to publish {target_subject} to broker: {e}")

    async def publish_enriched(self, enriched_outputs: dict[str, dict[str, Any]]) -> None:
        """Backward compat: wrapper for publish with old naming."""
        await self.publish(enriched_outputs)
