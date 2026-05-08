class BaseInputAdapter:
    """Base lifecycle and publish helper for stateless input adapters."""

    def __init__(self, device: str):
        """Store the device identifier used in published sources."""
        self.device = device
        self._publisher = None
        self._is_running = False

    async def start(self, input_publisher):
        """Attach the shared publisher and mark the adapter as running."""
        if self._is_running:
            return

        self._publisher = input_publisher
        self._is_running = True

    async def stop(self):
        """Detach the publisher and mark the adapter as stopped."""
        if not self._is_running:
            return

        self._publisher = None
        self._is_running = False
    
    async def publish(self, axis: str, value: float):
        """Publish one normalized axis value through the injected publisher."""
        if not self._is_running or self._publisher is None:
            raise RuntimeError("The system cant publish if its not started")
        
        await self._publisher.publish(device=self.device, axis=axis, value=value)