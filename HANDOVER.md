# Handover: Input Layer and Bootstrap Refactor Complete

## State of Play

The input layer is complete and well-tested, and the bootstrap flow has been refactored to match the architecture better. The `InputRuntimeManager` now owns startup, creates its own `InputAdapterBootstrap`, registers the selected adapters during startup, and then starts them. The orchestrator stays thin and only starts subsystems.

## What is Done

### Core Implementation
- **BaseInputAdapter** (`src/apelios/input/base_input_adapter.py`)
  - Lifecycle: `start()`, `stop()`
  - Publishing: `publish(axis, value)`, `publish_snapshot(snapshot)`
  - Polling hooks: `poll_once(dt)` (override-able), `tick(dt)` (calls poll_once then publishes)
  - Snapshot: dict of axis → float values

- **InputAdapterBootstrap** (`src/apelios/input/input_adapter_bootstrap.py`)
  - Class-based adapter registration helper
  - Configurable `adapter_list` with a small default set
  - Registers adapters into an existing `InputRuntimeManager`

- **InputPublisher** (`src/apelios/input/input_publisher.py`)
  - Publishes to broker with contract: `{"source": "device.axis", "value": float}`
  - Subject: `input.<device>`

- **InputRuntimeManager** (`src/apelios/input/input_runtime_manager.py`)
  - Registry for adapters (register, start, stop)
  - Lifecycle: `start()`, `stop()` with broker connection
  - Owns adapter bootstrap during startup
  - Tick orchestration: calls `adapter.tick(dt)` for all running adapters
  - Graceful failure handling: skips bad adapters on start, continues stopping on error

- **FakeAdapter** (`src/apelios/input/adapters/fake_adapter.py`)
  - Example adapter implementing `poll_once()`
  - Populates snapshot with test values: `left_stick.x=0.5`, `fader_1=0.75`

- **MouseAdapter** (`src/apelios/input/adapters/mouse_adapter.py`)
  - Linux evdev-backed adapter for relative mouse input
  - Used as a real hardware path alongside the fake adapter

- **MainOrchestrator** (`src/apelios/main_orchestrator.py`)
  - Starts broker, middleware, then input runtime
  - No longer owns adapter bootstrap details directly

- **Mapping Config** (`src/apelios/middleware/mapping_default.json`)
  - Includes mouse mappings for `mouse.x` and `mouse.y`
  - Maps mouse movement to `group1.pan` and `group1.tilt`

### Test Coverage (111 tests total)
- **Input bootstrap tests** (`tests/input/test_input_adapter_bootstrap.py`) now cover:
  - Default adapter registration
  - Custom adapter lists
  - Graceful handling of bad adapters
  - Unknown adapter names
  - RTM startup triggering bootstrap

- **Input layer tests**: 45 tests
- **test_base_input_adapter.py** (9 tests)
  - Lifecycle, publish, publish_snapshot, tick/poll_once integration

- **test_fake_adapter.py** (3 tests)
  - Basic publish, no-publish without start, start/stop cycles

- **test_input_runtime_manager.py** (19 tests)
  - Adapter registration, injection, lifecycle management
  - Publisher binding, error handling, idempotency

- **test_integration_input_layer.py** (5 tests)
  - Multiple adapters, multiple ticks
  - Message structure and value verification
  - Adapter stop/restart
  - Runtime lifecycle
  - Empty snapshot handling
  - dt parameter threading

- **Full suite**: 111 tests passing

### Documentation
- ADR 004 (stateless-input-adapter.md) updated to reflect live contract
- Clear separation: adapters are stateless, snapshot accumulates across one tick

## The Stable Contract

An input adapter:
1. Inherits from `BaseInputAdapter`
2. Implements `async def poll_once(self, dt: float = 0.016)`
   - Reads device state once
   - Populates `self.snapshot` dict with axis → float values
3. The base `tick()` calls `poll_once()` and then publishes the snapshot
4. The runtime manager calls `adapter.tick(dt)` on each tick (60 Hz)
5. The runtime manager bootstraps adapters during `start()`
6. Messages flow: adapter → InputPublisher → broker → middleware subscribers

## Next Steps (When You Resume)

### Immediate (Adapters present)
1. The `mouse_adapter` is already implemented at `src/apelios/input/adapters/mouse_adapter.py` and exercised by tests.
2. The `fake_adapter` remains available for unit and integration tests.
3. The adapter bootstrap is now class-based and owned by the input runtime manager.

### Integration Layers
3. Verify mouse input end-to-end through middleware in a live run.
4. Add the output layer once the mapping pipeline is stable.

### Other Layers
5. Output layer (after input is proven)
6. Middleware mapping improvements (load JSON fixture files if needed)
7. GUI if staying in this repo

### Bootstrap Plan
8. Keep `InputAdapterBootstrap` small and explicit for now.
  - Default list is `fake` + `mouse`.
  - The adapter list can later be replaced by config or GUI-driven selection.

## Quick Run Commands

```bash
cd /path/to/apelios
source ./venv/bin/activate
pytest tests/input -q       # All input tests
pytest tests/input -v       # Verbose
pytest tests/ -q            # Full suite
```

## File Locations Summary

```
src/apelios/input/
  ├── base_input_adapter.py       (BaseInputAdapter with tick/poll_once)
  ├── input_adapter_bootstrap.py  (class-based adapter registration)
  ├── input_publisher.py          (publishes to broker)
  ├── input_runtime_manager.py    (orchestrates adapters)
  └── adapters/
      ├── __init__.py
      ├── fake_adapter.py         (example adapter)
      └── mouse_adapter.py        (evdev mouse adapter)

src/apelios/middleware/
  └── mapping_default.json        (includes mouse pan/tilt mappings)

tests/input/
  ├── test_base_input_adapter.py  (9 unit tests)
  ├── test_input_runtime_manager.py (19 unit tests)
  ├── test_integration_input_layer.py (5 integration tests)
  ├── test_input_adapter_bootstrap.py (bootstrap tests)
  └── adapters/
      └── test_fake_adapter.py    (3 adapter tests)
```

---

**Good stopping point:** The input layer is solid, bootstrap is now owned by the runtime manager, and the mouse path is wired into the middleware mapping table. Next step is a live end-to-end check and then the output layer.
