"""Fixture layer runtime manager."""

from __future__ import annotations

import json
from pathlib import Path

from apelios.broker.broker_client import BrokerClient
from apelios.fixture.fixture_core import FixtureCore
from apelios.fixture.fixture_input_subscriber import FixtureInputSubscriber
from apelios.fixture.fixture_output_publisher import FixtureOutputPublisher

_PATCH_DIR = Path(__file__).with_name("patch")


def _load_all_patches() -> dict:
    """Load and merge all JSON patch files from the patch directory.
    
    Similar to the router's multi-file loading approach:
    - Loads default.json first as base
    - Then loads all other .json files (except default.json) and merges them
    - All fixtures are merged into a single fixtures dict
    """
    if not _PATCH_DIR.exists():
        return {}
    
    result: dict = {}
    
    # Load default.json first as base
    default_path = _PATCH_DIR / "default.json"
    if default_path.exists():
        with default_path.open() as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            result = data
    
    # Load all other JSON files and merge fixtures
    for path in sorted(_PATCH_DIR.glob("*.json")):
        if path.name == "default.json":
            continue
        if path.exists():
            with path.open() as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                # Merge fixtures
                if "fixtures" in data and isinstance(data["fixtures"], dict):
                    if "fixtures" not in result:
                        result["fixtures"] = {}
                    result["fixtures"].update(data["fixtures"])
                # Merge any other top-level keys
                for key, value in data.items():
                    if key != "fixtures":
                        result[key] = value
    
    return result


class FixtureRuntimeManager:
    """Own the fixture layer lifecycle and 60Hz processing loop."""

    def __init__(
        self,
        core: FixtureCore | None = None,
        broker_client: BrokerClient | None = None,
        patch: dict | None = None,
    ) -> None:
        self.core = core or FixtureCore(patch=patch or _load_all_patches())
        self.broker_client = broker_client or BrokerClient(provider="nats")
        self.input_subscriber = FixtureInputSubscriber(self.core.inbox)
        self.output_module = FixtureOutputPublisher(self.broker_client)
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        await self.broker_client.connect()
        await self.broker_client.subscribe("target.>", self.input_subscriber)
        self._running = True

    async def stop(self) -> None:
        if not self._running:
            return

        await self.broker_client.disconnect()
        self._running = False

    def is_running(self) -> bool:
        return self._running

    async def tick(self, dt: float = 0.016) -> None:
        self.core.process_frame(dt=dt)
        if self.core.dmx_output:
            await self.output_module.publish_dmx(self.core.dmx_output)