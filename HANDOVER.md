# Handover: Input Layer Foundation Complete

## State of Play

The input layer foundation is complete and well-tested. All 38 input tests pass. The adapter contract is stable and the runtime manager fully orchestrates the polling lifecycle.

## What is Done

### Core Implementation
- **BaseInputAdapter** (`src/apelios/input/base_input_adapter.py`)
  - Lifecycle: `start()`, `stop()`
  - Publishing: `publish(axis, value)`, `publish_snapshot(snapshot)`
  - Polling hooks: `poll_once(dt)` (override-able), `tick(dt)` (calls poll_once then publishes)
  - Snapshot: dict of axis → float values

- **InputPublisher** (`src/apelios/input/input_publisher.py`)
  - Publishes to broker with contract: `{"source": "device.axis", "value": float}`
  - Subject: `input.<device>`

- **InputRuntimeManager** (`src/apelios/input/input_runtime_manager.py`)
  - Registry for adapters (register, start, stop)
  - Lifecycle: `start()`, `stop()` with broker connection
  - Tick orchestration: calls `adapter.tick(dt)` for all running adapters
  - Graceful failure handling: skips bad adapters on start, continues stopping on error

- **FakeAdapter** (`src/apelios/input/adapters/fake_adapter.py`)
  - Example adapter implementing `poll_once()`
  - Populates snapshot with test values: `left_stick.x=0.5`, `fader_1=0.75`

### Test Coverage (38 tests)
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
5. Messages flow: adapter → InputPublisher → broker → middleware subscribers

## Next Steps (When You Resume)

### Immediate (Real Adapter)
1. Implement the first real adapter (keyboard or mouse with `evdev` is likely easiest)
   - Place in `src/apelios/input/adapters/evdev_adapter.py` or similar
   - Override `poll_once()` to read device state
   - Test with `tests/input/adapters/test_evdev_adapter.py` before wiring to the runtime
2. Update `src/apelios/input/adapters/__init__.py` to export it

### Integration Layers
3. Wire InputRuntimeManager into the main orchestrator
   - Inject shared broker_client
   - Call runtime.start() on orchestrator start
   - Add runtime.tick(dt) to the 60Hz tick loop
4. Verify messages flow end-to-end: adapter → broker → middleware

### Other Layers
5. Output layer (after input is proven)
6. Middleware mapping improvements (load JSON fixture files)
7. GUI if staying in this repo

## Open Questions
- Which real adapter first: keyboard (evdev), mouse (evdev), or Steam Deck HID?
- GUI: separate project or stay integrated?
- Should the orchestrator tick be exposed for explicit control, or implicit in start()?

## Quick Run Commands

```bash
cd /path/to/apelios
source ./venv/bin/activate
pytest tests/input -q       # All 38 tests
pytest tests/input -v       # Verbose
pytest tests/ -q            # Full suite
```

## File Locations Summary

```
src/apelios/input/
  ├── base_input_adapter.py       (BaseInputAdapter with tick/poll_once)
  ├── input_publisher.py          (publishes to broker)
  ├── input_runtime_manager.py    (orchestrates adapters)
  └── adapters/
      ├── __init__.py
      └── fake_adapter.py         (example adapter)

tests/input/
  ├── test_base_input_adapter.py  (9 unit tests)
  ├── test_input_runtime_manager.py (19 unit tests)
  ├── test_integration_input_layer.py (5 integration tests)
  └── adapters/
      └── test_fake_adapter.py    (3 adapter tests)
```

---

**Good stopping point:** The input layer foundation is solid. All contracts are tested and stable. Ready to bolt on real adapters and wire into the orchestrator.
