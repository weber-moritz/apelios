# Input Adapters

This package contains the concrete input adapters that feed values into the input layer.

An adapter is a small async object that reads one device or source, stores the current values in `snapshot`, and lets the shared runtime publish those values through the broker.

Adapters are expected to be cross-platform in design. Do not assume one adapter per operating system unless a backend explicitly requires it. Linux has priority for implementation and validation today, and unless stated otherwise, other operating systems do not need support at this stage.

## When to create a new adapter

Create a new adapter when you need to read input from a new source, such as:

- a hardware device
- a virtual device
- a test double or simulator
- a platform-specific backend

The adapter package is cross-platform by design. Prefer one adapter that can choose an appropriate backend over one adapter per operating system. Linux has priority for implementation and validation today, and unless stated otherwise, other operating systems do not need support at this stage.

## Adapter contract

Every adapter should inherit from `BaseInputAdapter` and follow these rules:

- call `super().__init__(device=...)`
- keep `device` as the logical source name used in published messages
- implement `async poll_once(self, dt: float = 0.016) -> None`
- update `self.snapshot` with flattened `str -> float` values
- keep values normalized when possible so downstream code does not need device-specific logic
- only do device reading inside `poll_once`; publishing is handled by the base class

The base class provides:

- `start(input_publisher)` to attach the shared publisher
- `stop()` to detach the publisher
- `tick(dt)` to call `poll_once()` and then publish the current snapshot
- `publish()` and `publish_snapshot()` for direct publishing when needed

## Snapshot format

Adapters should populate `self.snapshot` with simple axis/value pairs.

Examples:

```python
self.snapshot["left_stick.x"] = 0.5
self.snapshot["left_stick.y"] = -0.2
self.snapshot["trigger"] = 1.0
```

Keep the snapshot flat. Do not store nested dictionaries or device objects in it.

## How the runtime uses an adapter

The input runtime manager owns lifecycle and publishing.

1. `InputRuntimeManager.start()` connects the broker client.
2. `InputRuntimeManager.start()` bootstraps adapters through `InputAdapterBootstrap`.
3. `InputAdapterBootstrap` instantiates adapters and registers them with the runtime manager.
4. `InputRuntimeManager.start_registered_adapters()` calls `adapter.start(input_publisher=...)` for each registered adapter.
5. `InputRuntimeManager.tick(dt)` calls `adapter.tick(dt)` on every running adapter.
6. `BaseInputAdapter.tick()` calls `poll_once()` and publishes the snapshot through the shared `InputPublisher`.

Published messages use the adapter `device` name as the source namespace.

## How the bootstrap uses an adapter

`InputAdapterBootstrap` maps a short adapter name to a concrete class.

Current built-in names are:

- `fake` -> `FakeAdapter`
- `mouse` -> `MouseAdapter`
- `steamdeck` -> `SteamDeckAdapter`

The default runtime bootstrap currently registers `mouse` and `steamdeck`.

The bootstrap currently creates adapters with:

```python
adapter = adapter_class(device=adapter_name)
```

That means a new adapter should accept a `device` keyword argument, even if it does not use it for hardware access.

If you add a new adapter, update the bootstrap registry so the new name can be discovered and instantiated.

## Adding a new adapter

1. Create a new module in this package, for example `my_adapter.py`.
2. Subclass `BaseInputAdapter`.
3. Implement `poll_once()`.
4. Populate `self.snapshot` with the values you want published.
5. Handle device cleanup in `stop()` if the backend opens files, sockets, or handles.
6. Add the adapter to `input_adapter_bootstrap.py`.
7. Export it from `__init__.py` if you want it available from `apelios.input.adapters`.
8. Add or update tests for bootstrap registration and runtime ticking.

## Minimal adapter template

```python
from apelios.input.base_input_adapter import BaseInputAdapter


class MyAdapter(BaseInputAdapter):
    def __init__(self, device: str = "my_adapter") -> None:
        super().__init__(device=device)

    async def poll_once(self, dt: float = 0.016) -> None:
        del dt
        self.snapshot = {
            "axis.x": 0.0,
            "axis.y": 0.0,
        }
```

If the adapter manages an open resource, override `stop()` and close it after calling `super().stop()`.

## Existing examples

- `FakeAdapter` is the smallest example of a stateless adapter.
- `MouseAdapter` shows how to wrap a Linux backend and publish normalized relative motion.
- `SteamDeckAdapter` shows how to publish every controller axis from the bitsteam library.

`MouseAdapter` is currently Linux-only because its backend depends on Linux `evdev`, but the adapter package itself should still be treated as cross-platform in design.

## Practical notes

- Keep polling cheap. The runtime expects adapters to fit into a regular frame tick.
- Prefer async methods so adapters can integrate with the rest of the event loop.
- Keep platform checks inside the adapter or backend constructor.
- Let the runtime manager handle startup, registration, and publication.