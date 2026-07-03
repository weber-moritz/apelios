class BaseInputAdapter:
    """Base lifecycle and publish helper for stateless input adapters."""

    def __init__(self, device: str):
        """Store the device identifier used in published sources."""
        self.device = device
        self._publisher = None
        self._is_running = False
        self.snapshot: dict[str, float] = {}
        self._axis_types: dict[str, str] = {}
        self._axis_scales: dict[str, float] = {}

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

    def set_axis_type(self, axis: str, type: str) -> None:
        """Set the type for a specific axis."""
        self._axis_types[axis] = type

    def get_axis_type(self, axis: str) -> str:
        """Get the type for a specific axis, defaulting to absolute_uni."""
        return self._axis_types.get(axis, "absolute_uni")

    def set_axis_scale(self, axis: str, scale: float) -> None:
        """Set the sensitivity scale for a specific axis."""
        self._axis_scales[axis] = scale

    def get_axis_scale(self, axis: str) -> float:
        """Get the sensitivity scale for a specific axis.
        
        Checks exact match first, then wildcard patterns (ending in .*),
        finally defaults to 1.0.
        """
        # Check exact match first
        if axis in self._axis_scales:
            return self._axis_scales[axis]
        
        # Check wildcard patterns (e.g., "imu.*" matches "imu.pitch")
        for pattern, scale in self._axis_scales.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]  # Remove ".*"
                if axis.startswith(prefix + "."):
                    return scale
        
        # Default fallback
        return 1.0
    
    async def publish(self, axis: str, value: float, type: str | None = None, source: str | None = None) -> None:
        """Publish one normalized axis value through the injected publisher."""
        if not self._is_running or self._publisher is None:
            raise RuntimeError("The system cant publish if its not started")
        
        # Apply scaling
        scale = self.get_axis_scale(axis)
        scaled_value = value * scale
        
        # Use provided type or look up from axis_types
        publish_type = type if type is not None else self.get_axis_type(axis)
        
        await self._publisher.publish(device=self.device, axis=axis, value=scaled_value, type=publish_type, source=source)

    async def publish_snapshot(self, snapshot: dict[str, float]) -> None:
        """Publishes the current values of all axes in the snapshot."""
        for axis, value in snapshot.items():
            axis_type = self.get_axis_type(axis)
            await self.publish(axis, value, type=axis_type)

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