"""Middleware output publisher for broker events.

This module publishes enriched middleware payloads to both target.* and outputs.* subjects.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apelios.broker.broker_client import BrokerClient

logger = logging.getLogger(__name__)


class MiddlewareOutputPublisher:
    """Publish enriched middleware payloads to broker."""

    def __init__(self, broker: BrokerClient) -> None:
        self.broker = broker

    async def publish_enriched(self, enriched_outputs: dict[str, dict[str, Any]]) -> None:
        """Publish enriched payloads to target.* subjects.

        Args:
            enriched_outputs: dict mapping target name to enriched payload
                e.g., {"movinghead01.pan": {"target": "movinghead01.pan", "value": 0.5, "intent": "absolute", "timestamp": 1234567890.123}}
        """
        for target, enriched_payload in enriched_outputs.items():
            try:
                payload_json = json.dumps(enriched_payload).encode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to serialize enriched payload for {target}: {e}")
                continue

            # Publish to target.* subject
            try:
                target_subject = f"target.{target}"
                await self.broker.publish(target_subject, payload_json)
            except Exception as e:
                logger.error(f"Failed to publish {target_subject} to broker: {e}")