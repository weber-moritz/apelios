# Phase 1: Input Layer

> **Document Purpose:** Detailed task checklist for migrating from current ADR-004 architecture to target architecture from `architecture-changes.md`.
> **For Agent Execution:** Each task is atomic and testable.
> **Version:** 1.0 | **Date:** 2026-06-03 | **Status:** Ready for Execution

---

## 🎯 MIGRATION GOAL

**From (Current - ADR-004):**
```
Input:   {source: "device.axis", value: 0.5}
         ↓
Router: Adds intent from config → {target: "fixture.param", value: 0.5, intent: "rate", timestamp: ...}
         ↓
Fixture:  Receives intent, applies math
```

**To (Target - architecture-changes.md):**
```
Input:   {value: 0.5, type: "rate", timestamp: ...}
         ↓ (topic: input.device.axis)
Router: Pure passthrough → {value: 0.5, type: "rate", timestamp: ...}
         ↓ (topic: target.fixture.param)
Fixture:  Receives type, applies math
```

**Key Change:** `type` moves from Router config → Input Layer adapters.

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
