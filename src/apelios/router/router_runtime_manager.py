"""Router runtime manager and broker input subscriber.

This module owns the router-side broker subscription lifecycle and bridges
broker events into the mapping core.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apelios.broker.broker_client import BrokerClient
from apelios.router.router_core import MappingRouter
from apelios.router.router_input_subscriber import RouterInputSubscriber
from apelios.router.router_output_publisher import RouterOutputPublisher

_ROUTING_DIR = Path(__file__).parent / "routing"


def _load_default_profile() -> dict[str, str]:
    """Load the base router profile mapping sources to targets.
    
    Returns simple source->target mapping dict (no nested intent/sensitivity).
    """

    def _load_mappings(path: Path) -> dict[str, str | list[str]]:
        if not path.exists():
            return {}

        with path.open() as f:
            data = json.load(f)

        # New format: simple source->target mapping (can be str or list[str])
        mappings = data.get("mappings", {})
        if not isinstance(mappings, dict):
            return {}

        # Convert old format (nested dicts) to new format if needed
        result: dict[str, str | list[str]] = {}
        for source, mapping in mappings.items():
            if isinstance(mapping, dict):
                # Old format: {"source": {"target": "target.group1.param", "intent": "..."}}
                target = mapping.get("target", mapping)
                result[source] = target
            elif isinstance(mapping, list):
                # New format: {"source": ["target1.param", "target2.param"]}
                result[source] = mapping
            else:
                # New format: {"source": "target.group1.param"}
                result[source] = mapping

        return result

    if _ROUTING_DIR.exists():
        base_profile = _ROUTING_DIR / "default.json"
        profile = _load_mappings(base_profile)

        for path in sorted(_ROUTING_DIR.glob("default_*.json")):
            profile.update(_load_mappings(path))

        for path in sorted(_ROUTING_DIR.glob("*.json")):
            if path.name == "default.json" or path.name.startswith("default_"):
                continue
            profile.update(_load_mappings(path))

        return profile

    return {}


class RouterRuntimeManager:
    """Single router entry point for lifecycle and dependency injection."""

    def __init__(
        self,
        router: MappingRouter | None = None,
        broker_client: BrokerClient | None = None,
        input_subject: str = "input.>",
    ) -> None:
        self.router = router or MappingRouter(profile=_load_default_profile())
        self.broker_client = broker_client or BrokerClient(provider="nats")
        self.input_subject = input_subject
        self.input_subscriber = RouterInputSubscriber(self.router, self)
        self.output_publisher = RouterOutputPublisher(broker=self.broker_client)
        self._running = False
        self._outputs_to_publish: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        """Start router runtime by subscribing to broker input events."""
        if self._running:
            return
        
        await self.broker_client.connect()

        await self.broker_client.subscribe(self.input_subject, self.input_subscriber)
        self._running = True

    async def stop(self) -> None:
        """Stop router runtime lifecycle state.

        No unsubscribe API exists on the current broker client abstraction yet.
        """
        self._running = False

    def is_running(self) -> bool:
        """Return whether this runtime manager is marked as running."""
        return self._running

    def collect_outputs(self, outputs: dict[str, dict[str, Any]]) -> None:
        """Collect outputs from router to be published on next tick."""
        self._outputs_to_publish.update(outputs)

    async def tick(self, dt: float = 0.016) -> None:
        """Publish collected outputs to broker.
        
        In the new stateless architecture, router processes inputs immediately
        and returns outputs. This method publishes any collected outputs and clears the buffer.
        """
        if self._outputs_to_publish:
            await self.output_publisher.publish(self._outputs_to_publish)
            self._outputs_to_publish = {}
