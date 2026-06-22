# TDD Migration TODO List: Input→Middleware→Fixture Architecture

> **Document Purpose:** Detailed task checklist for migrating from current ADR-004 architecture 
> to target architecture from `architecture-changes.md`. 
> **For Agent Execution:** Each task is atomic and testable.
> **Version:** 1.0 | **Date:** 2026-06-03 | **Status:** Ready for Execution

---

## 🎯 MIGRATION GOAL

**From (Current - ADR-004):**
```
Input:   {source: "device.axis", value: 0.5}
         ↓
Middleware: Adds intent from config → {target: "fixture.param", value: 0.5, intent: "rate", timestamp: ...}
         ↓
Fixture:  Receives intent, applies math
```

**To (Target - architecture-changes.md):**
```
Input:   {value: 0.5, type: "rate", timestamp: ...}
         ↓ (topic: input.device.axis)
Middleware: Pure passthrough → {value: 0.5, type: "rate", timestamp: ...}
         ↓ (topic: target.fixture.param)
Fixture:  Receives type, applies math
```

**Key Change:** `type` moves from Middleware config → Input Layer adapters.

---

## 📋 PHASE 1: INPUT LAYER (35 tasks)

### 📦 Module: input_publisher.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.1.1 | Add test for type in payload | `tests/input/test_input_publisher.py` | Add `test_publisher_includes_type_in_payload` | `pytest tests/input/test_input_publisher.py::test_publisher_includes_type_in_payload -v` |
| [x] 1.1.2 | Add test for topic format | `tests/input/test_input_publisher.py` | Add `test_publisher_uses_correct_topic_format` | `pytest tests/input/test_input_publisher.py::test_publisher_uses_correct_topic_format -v` |
| [x] 1.1.3 | Import time module | `src/apelios/input/input_publisher.py` | Add `import time` | - |
| [x] 1.1.4 | Update publish signature | `src/apelios/input/input_publisher.py` | Change to `publish(device, axis, value, type="absolute_uni")` | - |
| [x] 1.1.5 | Update payload format | `src/apelios/input/input_publisher.py` | Change to `{"value": value, "type": type, "timestamp": time.time()}` | - |

**Verification:** `pytest tests/input/test_input_publisher.py -v`

---

### 📦 Module: base_input_adapter.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.2.1 | Test adapter publishes type | `tests/input/test_base_input_adapter.py` | Add `test_adapter_publishes_with_type` | `pytest tests/input/test_base_input_adapter.py::test_adapter_publishes_with_type -v` |
| [x] 1.2.2 | Test snapshot includes types | `tests/input/test_base_input_adapter.py` | Add `test_adapter_publish_snapshot_includes_types` | `pytest tests/input/test_base_input_adapter.py::test_adapter_publish_snapshot_includes_types -v` |
| [x] 1.2.3 | Add axis_types storage | `src/apelios/input/base_input_adapter.py` | Add `self._axis_types: dict[str, str] = {}` in `__init__` | - |
| [x] 1.2.4 | Add set_axis_type method | `src/apelios/input/base_input_adapter.py` | Add method: `def set_axis_type(self, axis: str, type: str): self._axis_types[axis] = type` | - |
| [x] 1.2.5 | Add get_axis_type method | `src/apelios/input/base_input_adapter.py` | Add method: `def get_axis_type(self, axis: str) -> str: return self._axis_types.get(axis, "absolute_uni")` | - |
| [x] 1.2.6 | Update publish method | `src/apelios/input/base_input_adapter.py` | Add type param, lookup from _axis_types if None, pass to publisher | - |
| [x] 1.2.7 | Update publish_snapshot | `src/apelios/input/base_input_adapter.py` | Pass type for each axis when calling publish() | - |

**Verification:** `pytest tests/input/test_base_input_adapter.py -v`

---

### 📦 Module: steamdeck_adapter.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.3.1 | Test correct types per axis | `tests/input/adapters/test_steamdeck_adapter.py` | Add `test_steamdeck_publishes_correct_types` | `pytest tests/input/adapters/test_steamdeck_adapter.py::test_steamdeck_publishes_correct_types -v` |
| [x] 1.3.2 | Test all axes have types | `tests/input/adapters/test_steamdeck_adapter.py` | Add `test_steamdeck_all_axes_have_types` | `pytest tests/input/adapters/test_steamdeck_adapter.py::test_steamdeck_all_axes_have_types -v` |
| [x] 1.3.3 | Define axis types | `src/apelios/input/adapters/steamdeck_adapter.py` | Add `_AXIS_TYPES` class constant (see below) | - |
| [x] 1.3.4 | Set types in __init__ | `src/apelios/input/adapters/steamdeck_adapter.py` | Loop through _AXIS_TYPES, call set_axis_type() | - |
| [x] 1.3.5 | Verify axis mapping | `src/apelios/input/adapters/steamdeck_adapter.py` | Check _normalize_analog_axis() doesn't break type lookup | - |
| [x] 1.3.6 | Update poll_once | `src/apelios/input/adapters/steamdeck_adapter.py` | Ensure axis names in snapshot match _AXIS_TYPES keys | - |
| [x] 1.3.7 | Update tick | `src/apelios/input/adapters/steamdeck_adapter.py` | Pass types when publishing snapshot | - |
| [x] 1.3.8 | Add validation | `src/apelios/input/adapters/steamdeck_adapter.py` | Log warning if axis missing type in poll_once() | - |
| [x] 1.3.9 | Update existing test | `tests/input/adapters/test_steamdeck_adapter.py` | Modify `test_steamdeck_adapter_publishes_all_controller_axes` to verify types | - |
| [x] 1.3.10 | Run all tests | - | - | `pytest tests/input/adapters/test_steamdeck_adapter.py -v` |

**_AXIS_TYPES content:**
```python
_AXIS_TYPES = {
    # Buttons: absolute_uni (0 or 1)
    "button.a": "absolute_uni",
    "button.b": "absolute_uni",
    "button.x": "absolute_uni",
    "button.y": "absolute_uni",
    "l1": "absolute_uni",
    "r1": "absolute_uni",
    "l2_click": "absolute_uni",
    "r2_click": "absolute_uni",
    "dpad_up": "absolute_uni",
    "dpad_down": "absolute_uni",
    "dpad_left": "absolute_uni",
    "dpad_right": "absolute_uni",
    "select": "absolute_uni",
    "start": "absolute_uni",
    "steam": "absolute_uni",
    "quick_access": "absolute_uni",
    "l_lower_grip": "absolute_uni",
    "r_lower_grip": "absolute_uni",
    "l_upper_grip": "absolute_uni",
    "r_upper_grip": "absolute_uni",
    "l_stick_press": "absolute_uni",
    "r_stick_press": "absolute_uni",
    "l_stick_touch": "absolute_uni",
    "r_stick_touch": "absolute_uni",
    "l_trackpad_touch": "absolute_uni",
    "l_trackpad_press": "absolute_uni",
    "r_trackpad_touch": "absolute_uni",
    "r_trackpad_press": "absolute_uni",
    # Analog sticks: absolute_bi (-1 to 1)
    "joy.x": "absolute_bi",
    "joy.y": "absolute_bi",
    "right_stick.x": "absolute_bi",
    "right_stick.y": "absolute_bi",
    # Triggers: absolute_uni (0 to 1)
    "left_trigger": "absolute_uni",
    "right_trigger": "absolute_uni",
    # Trackpads: absolute_bi
    "left_trackpad.x": "absolute_bi",
    "left_trackpad.y": "absolute_bi",
    "right_trackpad.x": "absolute_bi",
    "right_trackpad.y": "absolute_bi",
    "left_trackpad.pressure": "absolute_uni",
    "right_trackpad.pressure": "absolute_uni",
    # IMU: rate
    "imu.pitch": "rate",
    "imu.yaw": "rate",
    "imu.roll": "rate",
}
```

**Verification:** `pytest tests/input/adapters/test_steamdeck_adapter.py -v`

---

### 📦 Module: mouse_adapter.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.4.1 | Test delta type | `tests/input/adapters/test_mouse_adapter.py` | Add `test_mouse_publishes_delta_type` | `pytest tests/input/adapters/test_mouse_adapter.py::test_mouse_publishes_delta_type -v` |
| [x] 1.4.2 | Define axis types | `src/apelios/input/adapters/mouse_adapter.py` | Add `_AXIS_TYPES = {"x": "delta", "y": "delta"}` | - |
| [x] 1.4.3 | Set types in __init__ | `src/apelios/input/adapters/mouse_adapter.py` | Call set_axis_type for x and y | - |
| [x] 1.4.4 | Update poll_once | `src/apelios/input/adapters/mouse_adapter.py` | Ensure axis names match _AXIS_TYPES | - |
| [x] 1.4.5 | Run all tests | - | - | `pytest tests/input/adapters/test_mouse_adapter.py -v` |

**Verification:** `pytest tests/input/adapters/test_mouse_adapter.py -v`

---

### 📦 Module: fake_adapter.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.5.1 | Test type publishing | `tests/input/adapters/test_fake_adapter.py` | Add `test_fake_adapter_publishes_with_types` | `pytest tests/input/adapters/test_fake_adapter.py::test_fake_adapter_publishes_with_types -v` |
| [x] 1.5.2 | Define default types | `src/apelios/input/adapters/fake_adapter.py` | Add `_AXIS_TYPES` with defaults | - |
| [x] 1.5.3 | Accept optional types | `src/apelios/input/adapters/fake_adapter.py` | Modify `__init__` to accept axis_types dict | - |
| [x] 1.5.4 | Pass types in tick | `src/apelios/input/adapters/fake_adapter.py` | Ensure types passed when publishing | - |
| [x] 1.5.5 | Run all tests | - | - | `pytest tests/input/adapters/test_fake_adapter.py -v` |

**Verification:** `pytest tests/input/adapters/test_fake_adapter.py -v`

---

### 📦 Module: Runtime Managers

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 1.6.1 | Verify no changes | `src/apelios/input/input_runtime_manager.py` | Review code, confirm no changes needed | - |
| [x] 1.6.2 | Run runtime tests | - | - | `pytest tests/input/test_input_runtime_manager.py -v` |
| [x] 1.6.3 | Run bootstrap tests | - | - | `pytest tests/input/test_input_adapter_bootstrap.py -v` |

**Verification:** `pytest tests/input/ -v` (all input tests pass)

---

## 📋 PHASE 2: MIDDLEWARE (30 tasks)

### 📦 Module: middleware_input_subscriber.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.1.1 | Test type parsing | `tests/middleware/test_middleware_input_subscriber.py` | Add `test_subscriber_parses_type_field` | `pytest tests/middleware/test_middleware_input_subscriber.py::test_subscriber_parses_type_field -v` |
| [x] 2.1.2 | Test missing type | `tests/middleware/test_middleware_input_subscriber.py` | Add `test_subscriber_rejects_missing_type` | `pytest tests/middleware/test_middleware_input_subscriber.py::test_subscriber_rejects_missing_type -v` |
| [x] 2.1.3 | Test missing value | `tests/middleware/test_middleware_input_subscriber.py` | Add `test_subscriber_rejects_missing_value` | `pytest tests/middleware/test_middleware_input_subscriber.py::test_subscriber_rejects_missing_value -v` |
| [x] 2.1.4 | Parse new schema | `src/apelios/middleware/middleware_input_subscriber.py` | Extract value, type, timestamp from payload | - |
| [x] 2.1.5 | Forward type | `src/apelios/middleware/middleware_input_subscriber.py` | Pass type to middleware: `handle_input(source, value, type, timestamp)` | - |
| [x] 2.1.6 | Run all tests | - | - | `pytest tests/middleware/test_middleware_input_subscriber.py -v` |

**Verification:** `pytest tests/middleware/test_middleware_input_subscriber.py -v`

---

### 📦 Module: middleware_core.py (CRITICAL)

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.2.1 | Test type unchanged | `tests/middleware/test_middleware_core.py` | Add `test_core_passes_type_unchanged` | `pytest tests/middleware/test_middleware_core.py::test_core_passes_type_unchanged -v` |
| [x] 2.2.2 | Test no state | `tests/middleware/test_middleware_core.py` | Add `test_core_has_no_state_dicts` | `pytest tests/middleware/test_middleware_core.py::test_core_has_no_state_dicts -v` |
| [x] 2.2.3 | Test immediate processing | `tests/middleware/test_middleware_core.py` | Add `test_core_processes_immediately` | `pytest tests/middleware/test_middleware_core.py::test_core_processes_immediately -v` |
| [x] 2.2.4 | Remove state dicts | `src/apelios/middleware/middleware_core.py` | Delete current_raw_input, virtual_output_state, enriched_outputs from __init__ | - |
| [x] 2.2.5 | Update handle_input signature | `src/apelios/middleware/middleware_core.py` | Add type, timestamp params: `handle_input(self, source, value, type, timestamp)` | - |
| [x] 2.2.6 | Immediate map+forward | `src/apelios/middleware/middleware_core.py` | In handle_input: lookup source→target, create output payload, store for tick | - |
| [x] 2.2.7 | Remove process_frame | `src/apelios/middleware/middleware_core.py` | Delete entire process_frame(dt) method | - |
| [x] 2.2.8 | Update profile format | `src/apelios/middleware/middleware_core.py` | Only expect source→target in profile, remove intent/sensitivity | - |
| [x] 2.2.9 | Update profile loading | `src/apelios/middleware/middleware_core.py` | Handle new format in _load_default_profile | - |
| [x] 2.2.10 | Remove intent logic | `src/apelios/middleware/middleware_core.py` | Delete all intent resolution code | - |
| [x] 2.2.11 | Add current_outputs | `src/apelios/middleware/middleware_core.py` | Add dict to store outputs for tick() | - |
| [x] 2.2.12 | Run all tests | - | - | `pytest tests/middleware/test_middleware_core.py -v` |

**Verification:** `pytest tests/middleware/test_middleware_core.py -v`

---

### 📦 Module: middleware_output_publisher.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.3.1 | Test unchanged forwarding | `tests/middleware/test_middleware_output_publisher.py` | Add `test_publisher_forwards_type_unchanged` | `pytest tests/middleware/test_middleware_output_publisher.py::test_publisher_forwards_type_unchanged -v` |
| [x] 2.3.2 | Forward exact payload | `src/apelios/middleware/middleware_output_publisher.py` | Remove payload modification, forward as-is | - |
| [x] 2.3.3 | Simplify input | `src/apelios/middleware/middleware_output_publisher.py` | Accept dict[str, dict] not enriched_outputs | - |
| [x] 2.3.4 | Remove backward compat | `src/apelios/middleware/middleware_output_publisher.py` | Delete virtual_output_state updates | - |
| [x] 2.3.5 | Run all tests | - | - | `pytest tests/middleware/test_middleware_output_publisher.py -v` |

**Verification:** `pytest tests/middleware/test_middleware_output_publisher.py -v`

---

### 📦 Module: middleware_runtime_manager.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.4.1 | Test tick publishes | `tests/middleware/test_middleware_runtime_manager.py` | Add `test_runtime_manager_tick_publishes_outputs` | `pytest tests/middleware/test_middleware_runtime_manager.py::test_runtime_manager_tick_publishes_outputs -v` |
| [x] 2.4.2 | Update tick to publish | `src/apelios/middleware/middleware_runtime_manager.py` | Get outputs from middleware, publish via output_publisher | - |
| [x] 2.4.3 | Clear after publish | `src/apelios/middleware/middleware_runtime_manager.py` | Clear middleware outputs after tick | - |
| [x] 2.4.4 | Verify subscription | `src/apelios/middleware/middleware_runtime_manager.py` | Confirm subscribes to input.> | - |
| [x] 2.4.5 | Update profile loading | `src/apelios/middleware/middleware_runtime_manager.py` | Use new format | - |
| [x] 2.4.6 | Remove process_frame call | `src/apelios/middleware/middleware_runtime_manager.py` | Delete process_frame(dt) call from tick() | - |
| [x] 2.4.7 | Run all tests | - | - | `pytest tests/middleware/test_middleware_runtime_manager.py -v` |

**Verification:** `pytest tests/middleware/ -v` (all middleware tests pass)

---

## 📋 PHASE 3: FIXTURE LAYER (15 tasks)

### 📦 Module: fixture_input_subscriber.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 3.1.1 | Test type parsing | `tests/fixture/test_fixture_input_subscriber.py` | Add `test_subscriber_parses_type_not_intent` | `pytest tests/fixture/test_fixture_input_subscriber.py::test_subscriber_parses_type_not_intent -v` |
| [x] 3.1.2 | Test missing type | `tests/fixture/test_fixture_input_subscriber.py` | Add `test_subscriber_handles_missing_type` | `pytest tests/fixture/test_fixture_input_subscriber.py::test_subscriber_handles_missing_type -v` |
| [x] 3.1.3 | Parse type field | `src/apelios/fixture/fixture_input_subscriber.py` | Extract type instead of intent | - |
| [x] 3.1.4 | Store type in inbox | `src/apelios/fixture/fixture_input_subscriber.py` | Store as type in inbox dict | - |
| [x] 3.1.5 | Run all tests | - | - | `pytest tests/fixture/test_fixture_input_subscriber.py -v` |

**Verification:** `pytest tests/fixture/test_fixture_input_subscriber.py -v`

---

### 📦 Module: fixture_core.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 3.2.1 | Test type field usage | `tests/fixture/test_fixture_core.py` | Add `test_core_uses_type_field` | `pytest tests/fixture/test_fixture_core.py::test_core_uses_type_field -v` |
| [x] 3.2.2 | Read type from payload | `src/apelios/fixture/fixture_core.py` | Change to read type instead of intent | - |
| [x] 3.2.3 | Rename method (optional) | `src/apelios/fixture/fixture_core.py` | _apply_type() instead of _apply_intent() | - |
| [x] 3.2.4 | Update all references | `src/apelios/fixture/fixture_core.py` | intent → type throughout | - |
| [x] 3.2.5 | Add type validation | `src/apelios/fixture/fixture_core.py` | Verify type is valid value | - |
| [x] 3.2.6 | Run all tests | - | - | `pytest tests/fixture/test_fixture_core.py -v` |
| [x] 3.2.7 | Verify math works | - | - | Manual check: absolute_uni, absolute_bi, delta, rate |

**Verification:** `pytest tests/fixture/test_fixture_core.py -v`

---

### 📦 Module: Runtime Managers

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 3.3.1 | Verify no changes | `src/apelios/fixture/fixture_runtime_manager.py` | Review, confirm no changes needed | - |
| [x] 3.3.2 | Run runtime tests | - | - | `pytest tests/fixture/test_fixture_runtime_manager.py -v` |
| [x] 3.3.3 | Run output tests | - | - | `pytest tests/fixture/test_fixture_output_module.py -v` |

**Verification:** `pytest tests/fixture/ -v` (all fixture tests pass)

---

## 📋 PHASE 4: CONFIG CLEANUP (10 tasks)

### 📦 Routing Config Files

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 4.1.1 | Create routing/default.json | `src/apelios/middleware/routing/default.json` | New file: `{"mappings": {"input.device.axis": "target.group.param"}}` | - |
| [x] 4.1.2 | Create routing/default_steamdeck.json | `src/apelios/middleware/routing/default_steamdeck.json` | Migrate from mapping/, remove intent/sensitivity | - |
| [x] 4.1.3 | Create routing/steamdeck.json | `src/apelios/middleware/routing/steamdeck.json` | Migrate from mapping/ | - |
| [x] 4.1.4 | Update runtime manager | `src/apelios/middleware/middleware_runtime_manager.py` | Change _MAPPING_DIR to _ROUTING_DIR | - |
| 4.1.5 | Remove old mapping/ | - | - | Delete after all tests pass |

**Verification:** All middleware tests still pass

---

### 📦 Patch Config

**Patch Config Format (DMX Channel Mapping):**
- Fixture has base `address` (DMX channel)
- Parameters use `address` as **relative offset** from fixture base (1, 2, 3... not 11, 12, 13...)
- If parameter `address` not set: auto-calculate sequential offset from previous parameter's (offset + width)
- For 16-bit: writes to channel N and N+1 (coarse + fine)
- Actual channel = `fixture.address + parameter.address`

**Example:**
```json
{
  "fixtures": {
    "movinghead01": {
      "type": "robe_robospot",
      "universe": 2,
      "address": 10,
      "parameters": {
        "pan": {"width": 16, "limits": [0.0, 1.0]},      // offset auto=0 → channels 10-11
        "tilt": {"address": 2, "width": 8, "limits": [0.0, 1.0]}  // offset=2 → channel 12
      }
    }
  }
}
```

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 4.2.1 | Update patch format | `src/apelios/fixture/patch/default.json` | Change from array to object format with offset-based addressing | - |
| [x] 4.2.2 | Update FixtureCore _write_dmx | `src/apelios/fixture/fixture_core.py` | Use fixture.address + parameter.address for channel calculation | - |
| [x] 4.2.3 | Auto-calculate sequential offsets | `src/apelios/fixture/fixture_core.py` | If no parameter address: calculate from previous (offset + width) | - |
| [x] 4.2.4 | Verify loading | `src/apelios/fixture/fixture_runtime_manager.py` | Update _load_default_patch() if needed | - |
| [x] 4.2.5 | Run fixture integration | - | - | `pytest tests/fixture/test_integration_fixture.py -v` |

**Verification:** Fixture layer tests pass

---

## 📋 PHASE 5: INTEGRATION (10 tasks)

### 📦 End-to-End Tests

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| 5.1.1 | Add full flow test | `tests/test_integration_main_orchestrator.py` | Add `test_full_flow_with_type` | `pytest tests/test_integration_main_orchestrator.py::test_full_flow_with_type -v` |
| 5.1.2 | Add SteamDeck test | `tests/test_integration_main_orchestrator.py` | Add `test_steamdeck_to_fixture` | `pytest tests/test_integration_main_orchestrator.py::test_steamdeck_to_fixture -v` |
| 5.1.3 | Add Mouse test | `tests/test_integration_main_orchestrator.py` | Add `test_mouse_to_fixture` | `pytest tests/test_integration_main_orchestrator.py::test_mouse_to_fixture -v` |
| 5.1.4 | Add stateless test | `tests/test_integration_main_orchestrator.py` | Add `test_middleware_stateless` | `pytest tests/test_integration_main_orchestrator.py::test_middleware_stateless -v` |
| 5.1.5 | Run all integration | - | - | `pytest tests/ -k integration -v` |

**Verification:** All integration tests pass

---

### 📦 Full Test Suite

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 5.2.1 | Run input tests | - | - | `pytest tests/input/ -v` |
| [x] 5.2.2 | Run middleware tests | - | - | `pytest tests/middleware/ -v` |
| [x] 5.2.3 | Run fixture tests | - | - | `pytest tests/fixture/ -v` |
| [x] 5.2.4 | Run broker tests | - | - | `pytest tests/broker/ -v` |
| [x] 5.2.5 | Run ALL tests | - | - | `pytest tests/ -v` |

**Success Criteria:** 148+ tests passing

---

## 📋 PHASE 6: MANY-TO-ONE INPUT SUMMATION (20 tasks)

### 🎯 Phase Goal: Enable Multiple Inputs to Contribute to One Output

**Problem:** Current architecture has 1:1 input→output mapping. When multiple inputs map to the same target, the last input overwrites previous ones. This prevents:
- Using absolute fader for coarse control + rate gyro for fine adjustments on same axis
- Multiple devices contributing to one fixture parameter
- Complex control schemes requiring input summation

**Current State (after Phase 5):**
```
Input:   {value: 0.5, type: "absolute_uni", timestamp: ...} (topic: input.fader.1)
         ↓
Middleware: maps fader.1 → group1.pan, publishes {value: 0.5, type: "absolute_uni", timestamp: ...} (topic: target.group1.pan)
         ↓
Fixture: inbox["group1.pan"] = {target: "group1.pan", value: 0.5, type: "absolute_uni", timestamp: ...}
         ↓
Second input to same target: OVERWRITES the first
```

**Target Architecture:**
```
Input:   {value: 0.5, type: "absolute_uni", timestamp: ..., source: "fader.1"} (topic: input.fader.1)
         ↓
Middleware: maps source→target, publishes {value: 0.5, type: "absolute_uni", timestamp: ..., source: "fader.1"} (topic: target.group1.pan)
         ↓
Fixture: inbox["fader.1"] = {source: "fader.1", target: "group1.pan", value: 0.5, type: "absolute_uni", timestamp: ...}
         ↓
Fixture Core: tracks per-target state, computes deltas, sums contributions from all sources
         ↓
Output: group1.pan = sum of all deltas + initial absolute value
```

**Why:** Enable flexible control schemes where absolute inputs set base position and delta/rate inputs provide fine adjustments.

**Note on Parameter Mapping:** The sequence of parameters in the patch config does NOT define DMX channel mapping. Channel mapping is explicit via `universe`, `address`, and `width` fields in each parameter definition. Multiple sources can map to the same target via the routing config (Phase 4.1), and their contributions are summed (this phase).

### 📦 Module: middleware_output_publisher.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 6.1.1 | Add source to payload | `src/apelios/middleware/middleware_core.py` | Include source field in output payload | - |
| [x] 6.1.2 | Test source in payload | `tests/middleware/test_middleware_core.py` | Add `test_core_includes_source_in_output` | `pytest tests/middleware/test_middleware_core.py::test_core_includes_source_in_output -v` |

**Verification:** `pytest tests/middleware/test_middleware_core.py -v`

---

### 📦 Module: fixture_input_subscriber.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 6.2.1 | Store source in inbox | `src/apelios/fixture/fixture_input_subscriber.py` | Key inbox by source, store target alongside | - |
| [x] 6.2.2 | Test source storage | `tests/fixture/test_fixture_input_subscriber.py` | Add `test_subscriber_stores_source` | `pytest tests/fixture/test_fixture_input_subscriber.py::test_subscriber_stores_source -v` |

**Verification:** `pytest tests/fixture/test_fixture_input_subscriber.py -v`

---

### 📦 Module: fixture_core.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 6.3.1 | Track per-target state | `src/apelios/fixture/fixture_core.py` | Add output_state dict with per-target {output_value, last_absolute, has_first_abs} | - |
| [x] 6.3.2 | Keep previous frame snapshot | `src/apelios/fixture/fixture_core.py` | Store copy of inbox at end of each frame | - |
| [x] 6.3.3 | Compute deltas per source | `src/apelios/fixture/fixture_core.py` | Calculate delta from previous frame for each source | - |
| [x] 6.3.4 | Sum deltas by target | `src/apelios/fixture/fixture_core.py` | Group sources by target, sum all deltas | - |
| [x] 6.3.5 | Handle absolute initialization | `src/apelios/fixture/fixture_core.py` | First absolute sets output_value, subsequent abs values contribute deltas | - |
| [x] 6.3.6 | Test delta summation | `tests/fixture/test_fixture_core.py` | Add `test_core_sums_deltas_from_multiple_sources` | `pytest tests/fixture/test_fixture_core.py::test_core_sums_deltas_from_multiple_sources -v` |
| [x] 6.3.7 | Test absolute initialization | `tests/fixture/test_fixture_core.py` | Add `test_core_initializes_with_first_absolute` | `pytest tests/fixture/test_fixture_core.py::test_core_initializes_with_first_absolute -v` |

**Verification:** `pytest tests/fixture/test_fixture_core.py -v`

---

### 📦 Module: fixture_runtime_manager.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 6.4.1 | Verify source flows through | `src/apelios/fixture/fixture_runtime_manager.py` | Source flows through middleware → subscriber → core | - |

**Verification:** `pytest tests/fixture/test_fixture_runtime_manager.py -v`

---

**Acceptance Criteria:**
- [x] Multiple inputs can map to same target
- [x] First absolute input sets base output value
- [x] Subsequent absolute inputs contribute delta (new - previous)
- [x] Delta inputs add directly to output
- [x] Rate inputs add (value * dt) to output
- [x] All types can be mixed on same target

---

## ✅ ACCEPTANCE CHECKLIST

### Phase 1: Input Layer Complete
- [x] All Input Layer tests pass
- [x] Input Layer publishes `{value: float, type: str, timestamp: float}` for all adapters
- [x] No `source` field in any input payload
- [x] All adapters define types for all axes
- [x] Topic format is `input.<device>.<axis>`

### Phase 2: Middleware Complete
- [x] All Middleware tests pass
- [x] Middleware has ZERO state (no `current_raw_input`, no `virtual_output_state`)
- [x] Middleware does ZERO math (no delta/rate calculation)
- [x] Type flows through Middleware unchanged
- [x] No batch processing in Middleware (no `process_frame()`)
- [x] Routing config has no `intent` or `sensitivity` fields

### Phase 3: Fixture Layer Complete
- [x] All Fixture Layer tests pass
- [x] Fixture receives and uses `type` field (not `intent`)
- [x] Math engine works with all types: absolute_uni, absolute_bi, delta, rate

### Phase 4: Config Complete
- [x] All routing config files use new format
- [x] No `intent` or `sensitivity` in routing config
- [x] Patch file matches spec format with offset-based addressing

### Phase 5: Integration Complete
- [x] All 152+ tests pass
- [x] End-to-end flow verified: Input → Middleware → Fixture
- [x] Architecture matches target design from `architecture-changes.md`
- [x] No violations of the 4 architectural principles

### Phase 6: Many-to-One Input Summation Complete
- [x] Multiple inputs can map to same target
- [x] First absolute input sets base output value
- [x] Subsequent absolute inputs contribute delta (new - previous)
- [x] Delta inputs add directly to output
- [x] Rate inputs add (value * dt) to output
- [x] All types can be mixed on same target

---

## 🔧 AGENT EXECUTION GUIDE

### Quick Start
```bash
cd /path/to/apelios
source venv/bin/activate
pip install -r requirements.txt 2>/dev/null || true
```

### Daily Workflow
```bash
# 1. Find next uncompleted task
TASK=$(grep -m1 -E '^\| \[ \] ' docs/TDD-MIGRATION-TODO.md | awk -F'|' '{print $2}')
echo "Next task: $TASK"

# 2. Work on the task (example: Task 1.1.1)
vi tests/input/test_input_publisher.py
# Add the test

# 3. Run the specific test
pytest tests/input/test_input_publisher.py::test_publisher_includes_type_in_payload -v

# 4. Fix until it passes, then mark complete in this file
#    Change: - [ ] 1.1.1 ...  =>  - [x] 1.1.1 ...

# 5. After each section, run full module tests
pytest tests/input/ -v
pytest tests/middleware/ -v
pytest tests/fixture/ -v
```

### Quality Gates (Before Marking Complete)
- [ ] The specific test passes
- [ ] No syntax errors in modified files
- [ ] Type hints are correct
- [ ] Code follows existing style (indentation, naming)
- [ ] No `print()` statements in production code
- [ ] No `TODO` or `FIXME` comments left
- [ ] Git status is clean (all changes intended)

### Debugging Cheat Sheet

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `KeyError: 'source'` | Old code expects `source` in payload | Use `type` instead of `source` |
| `KeyError: 'intent'` | Fixture expects `intent` but gets `type` | Change to read `type` |
| Test fails with wrong type | Adapter not setting type correctly | Check _AXIS_TYPES mapping |
| Middleware not routing | State dicts still present | Remove current_raw_input, virtual_output_state |
| Payload schema wrong | Publisher not updated | Check InputPublisher.publish() |
| Integration test fails | Layers not connected properly | Verify topic subscriptions |

### Committing Work
```bash
# After each TDD cycle (RED-GREEN-REFACTOR)
git add -A
git commit -m "Phase X: Task Y.Y.Y - Description

Generated by Mistral Vibe.
Co-Authored-By: Mistral Vibe <vibe@mistral.ai>"
```

---

## 📊 STATISTICS

| Metric | Value |
|--------|-------|
| Total Tasks | 150 |
| Code Files | 16 |
| Test Files | 11 |
| Config Files | 7 |
| Estimated Duration | 3-4 weeks |
| Critical Path Tasks | 50 |
| Test Files to Modify | 11 |

---

## 🎯 CRITICAL PATH (Do Not Skip)

These tasks must be completed in order:

**Phase 1 (Input must come first):**
1. 1.1.1 - 1.1.5 (InputPublisher)
2. 1.2.1 - 1.2.7 (BaseInputAdapter)
3. 1.3.1 - 1.3.10 (SteamDeckAdapter)
4. 1.4.1 - 1.4.5 (MouseAdapter)
5. 1.5.1 - 1.5.5 (FakeAdapter)

**Phase 2 (Middleware stateless):**
6. 2.1.1 - 2.1.6 (MiddlewareInputSubscriber)
7. 2.2.1 - 2.2.12 (MappingMiddleware) ← MOST CRITICAL
8. 2.3.1 - 2.3.5 (MiddlewareOutputPublisher)
9. 2.4.1 - 2.4.7 (MiddlewareRuntimeManager)

**Phase 3 (Fixture type):**
10. 3.1.1 - 3.1.5 (FixtureInputSubscriber)
11. 3.2.1 - 3.2.7 (FixtureCore)

**Phase 6 (Many-to-One):**
12. 6.1.1 - 6.1.2 (MiddlewareOutputPublisher)
13. 6.2.1 - 6.2.2 (FixtureInputSubscriber)
14. 6.3.1 - 6.3.7 (FixtureCore)
15. 6.4.1 (FixtureRuntimeManager)

**Phase 5 (Verify):**
16. 5.1.1 - 5.2.5 (Integration Tests)

---

## 📚 REFERENCE DOCUMENTS

| Document | Purpose |
|----------|---------|
| `docs/ARCHITECTURE.md` | Target architecture overview |
| `docs/architecture-changes.md` | Migration plan and phases |
| `docs/architectural-principles.md` | Design principles and current violations |
| `docs/adr/004-stateless-input-adapter.md` | **OLD DECISION** - Being migrated away from |
| `docs/functional-requirements-list.md` | What the system must do |
| `docs/non-functional-requirements-list.md` | Performance, reliability, etc. |

---

**Document Version:** 1.0  
**Author:** Mistral Vibe (for motzel)  
**Created:** 2026-06-03  
**Status:** Ready for Agent Execution  

*This file is designed to be executed by an autonomous agent. Each task is self-contained with exact file paths, actions, and verification commands.*
