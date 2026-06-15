"""Middleware runtime manager and broker input subscriber.

This module owns the middleware-side broker subscription lifecycle and bridges
broker events into the mapping core.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apelios.broker.broker_client import BrokerClient
from apelios.middleware.middleware_core import MappingMiddleware
from apelios.middleware.middleware_input_subscriber import MiddlewareInputSubscriber
from apelios.middleware.middleware_output_publisher import MiddlewareOutputPublisher

_MAPPING_DIR = Path(__file__).parent / "mapping"


def _load_default_profile() -> dict[str, str]:
    """Load the base middleware profile mapping sources to targets.
    
    Returns simple source->target mapping dict (no nested intent/sensitivity).
    """

    def _load_mappings(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}

        with path.open() as f:
            data = json.load(f)

        # New format: simple source->target mapping
        mappings = data.get("mappings", {})
        if not isinstance(mappings, dict):
            return {}

        # Convert old format (nested dicts) to new format if needed
        result = {}
        for source, mapping in mappings.items():
            if isinstance(mapping, dict):
                # Old format: {"source": {"target": "target.group1.param", "intent": "..."}}
                result[source] = mapping.get("target", mapping)
            else:
                # New format: {"source": "target.group1.param"}
                result[source] = mapping

        return result

    if _MAPPING_DIR.exists():
        base_profile = _MAPPING_DIR / "default.json"
        profile = _load_mappings(base_profile)

        for path in sorted(_MAPPING_DIR.glob("default_*.json")):
            profile.update(_load_mappings(path))

        for path in sorted(_MAPPING_DIR.glob("*.json")):
            if path.name == "default.json" or path.name.startswith("default_"):
                continue
            profile.update(_load_mappings(path))

        return profile

    return {}


class MiddlewareRuntimeManager:
    """Single middleware entry point for lifecycle and dependency injection."""

    def __init__(
        self,
        middleware: MappingMiddleware | None = None,
        broker_client: BrokerClient | None = None,
        input_subject: str = "input.>",
    ) -> None:
        self.middleware = middleware or MappingMiddleware(profile=_load_default_profile())
        self.broker_client = broker_client or BrokerClient(provider="nats")
        self.input_subject = input_subject
        self.input_subscriber = MiddlewareInputSubscriber(self.middleware, self)
        self.output_publisher = MiddlewareOutputPublisher(broker=self.broker_client)
        self._running = False
        self._outputs_to_publish: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        """Start middleware runtime by subscribing to broker input events."""
        if self._running:
            return
        
        await self.broker_client.connect()

        await self.broker_client.subscribe(self.input_subject, self.input_subscriber)
        self._running = True

    async def stop(self) -> None:
        """Stop middleware runtime lifecycle state.

        No unsubscribe API exists on the current broker client abstraction yet.
        """
        self._running = False

    def is_running(self) -> bool:
        """Return whether this runtime manager is marked as running."""
        return self._running

    def collect_outputs(self, outputs: dict[str, dict[str, Any]]) -> None:
        """Collect outputs from middleware to be published on next tick."""
        self._outputs_to_publish.update(outputs)

    async def tick(self, dt: float = 0.016) -> None:
        """Publish collected outputs to broker.
        
        In the new stateless architecture, middleware processes inputs immediately
        and returns outputs. This method publishes any collected outputs and clears the buffer.
        """
        if self._outputs_to_publish:
            await self.output_publisher.publish(self._outputs_to_publish)
            self._outputs_to_publish = {}
