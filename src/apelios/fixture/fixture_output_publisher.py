"""Fixture layer output module."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from apelios.broker.broker_client import BrokerClient


class FixtureOutputPublisher:
    """Publish finalized DMX values and print a compact state summary."""

    def __init__(self, broker: BrokerClient) -> None:
        self.broker = broker

    async def publish_dmx(self, dmx_output: dict[tuple[int, int], int]) -> None:
        for (universe, address), value in dmx_output.items():
            numeric_value = int(value)
            payload = {
                "universe": universe,
                "address": address,
                "value": numeric_value,
            }
            subject = f"output.{universe}.{address}"
            await self.broker.publish(subject, json.dumps(payload).encode("utf-8"))
            print(f"{universe}:{address}={numeric_value}")