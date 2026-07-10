"""Bootstrap module for the output layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapters.artnet_adapter import ArtNetAdapter
    from .output_core import OutputCore
    from .output_runtime_manager import OutputRuntimeManager


class OutputAdapterBootstrap:
    """Bootstrap adapter registration for the output layer.
    
    Creates and configures protocol adapters, passing them a reference to the
    OutputCore so they can read current DMX state in their independent loops.
    """

    def __init__(self, adapter_list: list[str] | None = None, core: OutputCore | None = None) -> None:
        """Initialize bootstrap with optional adapter list and core reference.
        
        Args:
            adapter_list: List of adapter names to create (default: ["artnet"]).
            core: OutputCore instance to pass to adapters for reading DMX state.
        """
        self.adapter_list = adapter_list or ["artnet"]
        self.core = core

    def _load_artnet_config(self) -> dict[str, int | str | float]:
        """Load ArtNet configuration from JSON file.
        
        Returns:
            Configuration dictionary with source_ip, target_ip, universe, output_rate_hz.
        """
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
        """Register adapters with the runtime manager.
        
        Creates adapter instances, passes them the OutputCore reference (from
        runtime_manager or self.core), registers them with the runtime manager,
        and the runtime manager will start their loops.
        
        Args:
            runtime_manager: The OutputRuntimeManager to register adapters with.
        """
        # Use core from self.core if provided, otherwise from runtime_manager
        core = self.core or runtime_manager.core
        
        adapters_by_name = {
            "artnet": lambda: self._create_artnet_adapter(core),
        }

        for adapter_name in self.adapter_list:
            creator = adapters_by_name.get(adapter_name)
            if not creator:
                continue

            try:
                adapter = await creator()
                runtime_manager._register_adapter(adapter)
            except Exception:
                pass

    async def _create_artnet_adapter(self, core: OutputCore) -> ArtNetAdapter:
        """Create and return ArtNet adapter instance with core reference.
        
        Args:
            core: OutputCore instance to pass to the adapter.
            
        Returns:
            Configured ArtNetAdapter instance ready for use.
        """
        from .adapters.artnet_adapter import ArtNetAdapter
        
        config = self._load_artnet_config()
        adapter = ArtNetAdapter(config=config, core=core)
        return adapter
