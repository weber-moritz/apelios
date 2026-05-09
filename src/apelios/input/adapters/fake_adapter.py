from apelios.input.base_input_adapter import BaseInputAdapter


class FakeAdapter(BaseInputAdapter):
	"""Tiny fake adapter used as an example adapter for the input layer."""

	async def poll_once(self, dt: float = 0.016) -> None:
		"""Populate the snapshot with a small set of fake input values.

		The `InputRuntimeManager` or tests call `tick()` which will invoke this
		method and then publish the populated `snapshot` using the base
		implementation.
		"""
		self.snapshot["left_stick.x"] = 0.5
		self.snapshot["fader_1"] = 0.75
