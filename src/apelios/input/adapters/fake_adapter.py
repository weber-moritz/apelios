from apelios.input.base_input_adapter import BaseInputAdapter


class FakeAdapter(BaseInputAdapter):
	"""Tiny fake adapter used as an example adapter for the input layer."""

	_AXIS_TYPES = {
		"left_stick.x": "absolute_bi",
		"fader_1": "absolute_uni",
	}

	def __init__(self, device: str = "fake", axis_types: dict[str, str] | None = None):
		super().__init__(device=device)
		
		# Use custom axis_types if provided, otherwise use defaults
		if axis_types:
			for axis, axis_type in axis_types.items():
				self.set_axis_type(axis, axis_type)
		else:
			for axis, axis_type in self._AXIS_TYPES.items():
				self.set_axis_type(axis, axis_type)

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Populate the snapshot with a small set of fake input values.

		The `InputRuntimeManager` or tests call `tick()` which will invoke this
		method and then publish the populated `snapshot` using the base
		implementation.
		"""
		self.snapshot["left_stick.x"] = 0.5
		self.snapshot["fader_1"] = 0.75
