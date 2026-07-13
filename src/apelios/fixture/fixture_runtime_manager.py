"""Fixture layer runtime manager."""

from __future__ import annotations

import json
from pathlib import Path

from apelios.broker.broker_client import BrokerClient
from apelios.fixture.fixture_core import FixtureCore
from apelios.fixture.fixture_input_subscriber import FixtureInputSubscriber
from apelios.fixture.fixture_output_publisher import FixtureOutputPublisher

_PATCH_DIR = Path(__file__).with_name("patch")
_PATCH_PATH = _PATCH_DIR / "default.json"


def _load_patch_file(path: Path) -> dict:
    """Load a single patch file."""
    if not path.exists():
        return {}
    
    with path.open() as handle:
        data = json.load(handle)
    
    return data if isinstance(data, dict) else {}


def _load_default_patch() -> dict:
    """Load the default fixture patch, merging all JSON files in the patch directory."""
    if not _PATCH_DIR.exists():
        return {}
    
    # Load base default.json first
    patch = _load_patch_file(_PATCH_PATH)
    
    # Load all other JSON files in the directory, merging their fixtures
    for path in sorted(_PATCH_DIR.glob("*.json")):
        if path == _PATCH_PATH:
            continue
        file_patch = _load_patch_file(path)
        # Merge fixtures from this file
        if "fixtures" in file_patch and isinstance(file_patch["fixtures"], dict):
            if "fixtures" not in patch:
                patch["fixtures"] = {}
            patch["fixtures"].update(file_patch["fixtures"])
    
    return patch


class FixtureRuntimeManager:
    """Own the fixture layer lifecycle and 60Hz processing loop."""

    def __init__(
        self,
        core: FixtureCore | None = None,
        broker_client: BrokerClient | None = None,
        patch: dict | None = None,
    ) -> None:
        self.core = core or FixtureCore(patch=patch or _load_default_patch())
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