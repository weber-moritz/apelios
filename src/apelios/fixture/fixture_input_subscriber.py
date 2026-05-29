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

    # ADD 'async' HERE
    async def __call__(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.data)
        except Exception:
            logger.warning("Ignoring malformed fixture input payload", exc_info=True)
            return

        if not isinstance(payload, dict):
            logger.warning("Ignoring fixture input payload that is not a JSON object")
            return

        target = payload.get("target")
        intent = payload.get("intent")
        value = payload.get("value")

        if not isinstance(target, str) or not target:
            logger.warning("Ignoring fixture input without valid 'target'")
            return

        if not isinstance(intent, str) or not intent:
            logger.warning("Ignoring fixture input without valid 'intent'")
            return

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            logger.warning("Ignoring fixture input with non-numeric 'value'")
            return

        self.inbox[target] = {
            "target": target,
            "intent": intent,
            "value": numeric_value,
        }