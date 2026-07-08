"""Bootstrap module for the output layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output_runtime_manager import OutputRuntimeManager


class OutputAdapterBootstrap:
    """Bootstrap adapter registration for the output layer."""

    def __init__(self, adapter_list: list[str] | None = None) -> None:
        """Initialize bootstrap with optional adapter list."""
        self.adapter_list = adapter_list or ["artnet"]

    def _load_artnet_config(self) -> dict:
        """Load ArtNet configuration from JSON file."""
        config_path = Path(__file__).parent / "config" / "artnet_config.json"
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            return config
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default config if file not found or invalid
            return {
                "source_ip": "127.0.0.1",
                "target_ip": "127.0.0.1",
                "universe": 0,
                "output_rate_hz": 40
            }

    async def bootstrap(self, runtime_manager: OutputRuntimeManager) -> None:
        """Register adapters with the runtime manager."""
        adapters_by_name = {
            "artnet": self._create_artnet_adapter,
        }

        for adapter_name in self.adapter_list:
            creator = adapters_by_name.get(adapter_name)
            if not creator:
                continue

            try:
                adapter = await creator()
                runtime_manager.core.register_adapter(adapter)
            except Exception:
                pass

    async def _create_artnet_adapter(self):
        """Create and return ArtNet adapter instance."""
        from .adapters.artnet_adapter import ArtNetAdapter
        
        config = self._load_artnet_config()
        adapter = ArtNetAdapter(config=config)
        return adapter
