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
        self._axis_deadzones: dict[str, float] = {}

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
    
    def set_axis_deadzone(self, axis: str, deadzone: float) -> None:
        """Set the deadzone for a specific axis.
        
        Deadzone values within [-deadzone, +deadzone] will be clamped to 0.0.
        This is useful for eliminating stick drift and input jitter.
        """
        self._axis_deadzones[axis] = deadzone
    
    def get_axis_deadzone(self, axis: str) -> float:
        """Get the deadzone for a specific axis.
        
        Checks exact match first, then wildcard patterns (ending in .*),
        finally defaults to 0.0 (no deadzone).
        """
        # Check exact match first
        if axis in self._axis_deadzones:
            return self._axis_deadzones[axis]
        
        # Check wildcard patterns (e.g., "imu.*" matches "imu.pitch")
        for pattern, deadzone in self._axis_deadzones.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]  # Remove ".*"
                if axis.startswith(prefix + "."):
                    return deadzone
        
        # Default fallback
        return 0.0
    
    def _apply_deadzone(self, value: float, deadzone: float, axis_type: str) -> float:
        """Apply deadzone to a value based on its axis type.
        
        For rate and absolute_bi types: apply symmetric deadzone around 0.0
        For absolute_uni type: apply deadzone only on positive side (values < deadzone -> 0.0)
        For delta type: no deadzone applied (doesn't make sense for delta values)
        """
        if deadzone <= 0:
            return value
        
        if axis_type in ("rate", "absolute_bi"):
            # Symmetric deadzone around 0.0
            if -deadzone <= value <= deadzone:
                return 0.0
        elif axis_type == "absolute_uni":
            # Deadzone only on positive side for absolute_uni
            if 0 <= value <= deadzone:
                return 0.0
        # For delta and any other type, no deadzone applied
        return value
    
    async def publish(self, axis: str, value: float, type: str | None = None, source: str | None = None) -> None:
        """Publish one normalized axis value through the injected publisher."""
        if not self._is_running or self._publisher is None:
            raise RuntimeError("The system cant publish if its not started")
        
        # Use provided type or look up from axis_types
        publish_type = type if type is not None else self.get_axis_type(axis)
        
        # Apply scaling first
        scale = self.get_axis_scale(axis)
        scaled_value = value * scale
        
        # Apply deadzone after scaling (so deadzone threshold is in scaled units)
        deadzone = self.get_axis_deadzone(axis)
        final_value = self._apply_deadzone(scaled_value, deadzone, publish_type)
        
        await self._publisher.publish(device=self.device, axis=axis, value=final_value, type=publish_type, source=source)

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