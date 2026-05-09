class BaseInputAdapter:
    """Base lifecycle and publish helper for stateless input adapters."""

    def __init__(self, device: str):
        """Store the device identifier used in published sources."""
        self.device = device
        self._publisher = None
        self._is_running = False
        self.snapshot: dict[str, float] = {}

    async def start(self, input_publisher) -> None:
        """Attach the shared publisher and mark the adapter as running."""
        if self._is_running:
            return

        self._publisher = input_publisher
        self._is_running = True

    async def stop(self) -> None:
        """Detach the publisher and mark the adapter as stopped."""
        if not self._is_running:
            return

        self._publisher = None
        self._is_running = False
    
    async def publish(self, axis: str, value: float) -> None:
        """Publish one normalized axis value through the injected publisher."""
        if not self._is_running or self._publisher is None:
            raise RuntimeError("The system cant publish if its not started")
        
        await self._publisher.publish(device=self.device, axis=axis, value=value)

    async def publish_snapshot(self, snapshot: dict[str, float]) -> None:
        """Publishes the current values of all axes in the snapshot."""
        for axis, value in snapshot.items():
            await self.publish(axis, value)

    async def poll_once(self, dt: float = 0.016) -> None:
        """Adapter hook: poll device state once and populate `self.snapshot`.

        Subclasses should override this method to read device state and
        update `self.snapshot`. The default implementation is a no-op.
        """
        return

    async def tick(self, dt: float = 0.016) -> None:
        """One frame tick: poll device and publish the snapshot.

        The base implementation calls `poll_once` (which adapters override)
        and then publishes any values present in `self.snapshot`.
        """
        if not self._is_running:
            return

        await self.poll_once(dt)

        if self.snapshot:
            await self.publish_snapshot(self.snapshot)