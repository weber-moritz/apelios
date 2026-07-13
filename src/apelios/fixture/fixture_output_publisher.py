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
        # Create a copy to avoid "dictionary changed size during iteration" errors
        # if dmx_output is modified concurrently
        dmx_output_copy = dict(dmx_output)
        for (universe, address), value in dmx_output_copy.items():
            numeric_value = int(value)
            payload = {
                "universe": universe,
                "address": address,
                "value": numeric_value,
            }
            subject = f"output.{universe}.{address}"
            await self.broker.publish(subject, json.dumps(payload).encode("utf-8"))
            # Print compact state summary
            print(f"{universe}:{address}={numeric_value}")