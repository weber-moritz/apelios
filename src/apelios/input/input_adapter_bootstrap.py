"""Bootstrap module for the input layer.

Manages adapter registration with an InputRuntimeManager.
Handles adapter instantiation and error handling gracefully, skipping bad adapters
while continuing with the remaining ones.
"""

from apelios.input.adapters.fake_adapter import FakeAdapter
from apelios.input.adapters.mouse_adapter import MouseAdapter


class InputAdapterBootstrap:
	"""Bootstrap adapter registration for the input layer.
	
	Instantiates and registers adapters with the input runtime manager.
	Configurable adapter list allows for different adapter combinations
	in different environments (tests, production, GUI-selected, etc).
	"""

	def __init__(self, adapter_list: list[str] | None = None) -> None:
		"""Initialize bootstrap with optional adapter list.
		
		Args:
			adapter_list: List of adapter names to register (default: ["fake", "mouse"]).
				Supported names: "fake", "mouse".
		"""
		self.adapter_list = adapter_list or ["mouse"]

	async def bootstrap(self, runtime_manager) -> None:
		"""Register adapters with the runtime manager.
		
		Iterates through the configured adapter list and instantiates each one.
		If any adapter fails to instantiate, it is skipped and the process
		continues with the remaining adapters.
		
		Args:
			runtime_manager: InputRuntimeManager instance to register adapters with.
		"""
		adapters_by_name = {
			"fake": FakeAdapter,
			"mouse": MouseAdapter,
		}

		for adapter_name in self.adapter_list:
			adapter_class = adapters_by_name.get(adapter_name)
			if not adapter_class:
				print(f"Unknown adapter: {adapter_name}")
				continue

			try:
				# Create adapter with device name matching adapter name
				adapter = adapter_class(device=adapter_name)
				runtime_manager.register_adapter(adapter)
			except Exception as e:
				print(f"Failed to register {adapter_name} adapter: {e}")


# Legacy function interface for backward compatibility with existing tests
async def bootstrap_input_layer(runtime_manager):
	"""Bootstrap the input layer with default adapters.
	
	Legacy function interface. New code should use InputAdapterBootstrap class directly.
	
	Args:
		runtime_manager: InputRuntimeManager instance to register adapters with.
	"""
	bootstrap = InputAdapterBootstrap()
	await bootstrap.bootstrap(runtime_manager)