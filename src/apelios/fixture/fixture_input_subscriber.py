"""Fixture layer input subscriber."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FixtureInputSubscriber:
    """Parse target.* payloads and store the newest payload per target."""

    def __init__(self, inbox: dict[str, dict[str, Any]]) -> None:
        self.inbox = inbox

    async def __call__(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            logger.warning("Ignoring malformed fixture input payload", exc_info=True)
            return

        if not isinstance(payload, dict):
            logger.warning("Ignoring fixture input payload that is not a JSON object")
            return

        # Extract target from message subject (e.g., "target.movinghead01.pan")
        subject = getattr(msg, "subject", "")
        if not subject.startswith("target."):
            logger.warning("Ignoring fixture input without valid 'target' subject")
            return
        target = subject[7:]  # Strip "target." prefix
        if not target:
            logger.warning("Ignoring fixture input without valid 'target' subject")
            return

        value = payload.get("value")
        type_ = payload.get("type")

        if not isinstance(type_, str) or not type_:
            logger.warning("Ignoring fixture input without valid 'type'")
            return

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            logger.warning("Ignoring fixture input with non-numeric 'value'")
            return

        self.inbox[target] = {
            "target": target,
            "type": type_,
            "value": numeric_value,
        }