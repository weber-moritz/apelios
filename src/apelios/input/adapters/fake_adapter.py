from apelios.input.base_input_adapter import BaseInputAdapter


class FakeAdapter(BaseInputAdapter):
	"""Tiny fake adapter used as an example adapter for the input layer."""

	_AXIS_TYPES = {
		"left_stick.x": "absolute_bi",
		"fader_1": "absolute_uni",
	}

	def __init__(self, device: str = "fake", axis_types: dict[str, str] | None = None, axis_deadzones: dict[str, float] | None = None):
		super().__init__(device=device)
		
		# Use custom axis_types if provided, otherwise use defaults
		if axis_types:
			for axis, axis_type in axis_types.items():
				self.set_axis_type(axis, axis_type)
		else:
			for axis, axis_type in self._AXIS_TYPES.items():
				self.set_axis_type(axis, axis_type)
		
		# Use custom axis_deadzones if provided
		if axis_deadzones:
			for axis, deadzone in axis_deadzones.items():
				self.set_axis_deadzone(axis, deadzone)

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Populate the snapshot with a small set of fake input values.

		The `InputRuntimeManager` or tests call `tick()` which will invoke this
		method and then publish the populated `snapshot` using the base
		implementation.
		
		For performance testing with multiple axes, this generates values
		for all registered axes.
		"""
		# Generate values for all registered axes
		for axis in self._axis_types:
			# Use a simple pattern that varies with axis name for uniqueness
			if axis.endswith(".x") or "left" in axis:
				value = 0.5
			elif axis.endswith(".value") or "value" in axis or "fader" in axis:
				value = 0.75
			else:
				value = 0.5
			self.snapshot[axis] = value
