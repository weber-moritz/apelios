# Phase 2: Router

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

## 📋 PHASE 2: MIDDLEWARE (30 tasks)

### 📦 Module: router_input_subscriber.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.1.1 | Test type parsing | `tests/router/test_router_input_subscriber.py` | Add `test_subscriber_parses_type_field` | `pytest tests/router/test_router_input_subscriber.py::test_subscriber_parses_type_field -v` |
| [x] 2.1.2 | Test missing type | `tests/router/test_router_input_subscriber.py` | Add `test_subscriber_rejects_missing_type` | `pytest tests/router/test_router_input_subscriber.py::test_subscriber_rejects_missing_type -v` |
| [x] 2.1.3 | Test missing value | `tests/router/test_router_input_subscriber.py` | Add `test_subscriber_rejects_missing_value` | `pytest tests/router/test_router_input_subscriber.py::test_subscriber_rejects_missing_value -v` |
| [x] 2.1.4 | Parse new schema | `src/apelios/router/router_input_subscriber.py` | Extract value, type, timestamp from payload | - |
| [x] 2.1.5 | Forward type | `src/apelios/router/router_input_subscriber.py` | Pass type to router: `handle_input(source, value, type, timestamp)` | - |
| [x] 2.1.6 | Run all tests | - | - | `pytest tests/router/test_router_input_subscriber.py -v` |

**Verification:** `pytest tests/router/test_router_input_subscriber.py -v`

---

### 📦 Module: router_core.py (CRITICAL)

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.2.1 | Test type unchanged | `tests/router/test_router_core.py` | Add `test_core_passes_type_unchanged` | `pytest tests/router/test_router_core.py::test_core_passes_type_unchanged -v` |
| [x] 2.2.2 | Test no state | `tests/router/test_router_core.py` | Add `test_core_has_no_state_dicts` | `pytest tests/router/test_router_core.py::test_core_has_no_state_dicts -v` |
| [x] 2.2.3 | Test immediate processing | `tests/router/test_router_core.py` | Add `test_core_processes_immediately` | `pytest tests/router/test_router_core.py::test_core_processes_immediately -v` |
| [x] 2.2.4 | Remove state dicts | `src/apelios/router/router_core.py` | Delete current_raw_input, virtual_output_state, enriched_outputs from __init__ | - |
| [x] 2.2.5 | Update handle_input signature | `src/apelios/router/router_core.py` | Add type, timestamp params: `handle_input(self, source, value, type, timestamp)` | - |
| [x] 2.2.6 | Immediate map+forward | `src/apelios/router/router_core.py` | In handle_input: lookup source→target, create output payload, store for tick | - |
| [x] 2.2.7 | Remove process_frame | `src/apelios/router/router_core.py` | Delete entire process_frame(dt) method | - |
| [x] 2.2.8 | Update profile format | `src/apelios/router/router_core.py` | Only expect source→target in profile, remove intent/sensitivity | - |
| [x] 2.2.9 | Update profile loading | `src/apelios/router/router_core.py` | Handle new format in _load_default_profile | - |
| [x] 2.2.10 | Remove intent logic | `src/apelios/router/router_core.py` | Delete all intent resolution code | - |
| [x] 2.2.11 | Add current_outputs | `src/apelios/router/router_core.py` | Add dict to store outputs for tick() | - |
| [x] 2.2.12 | Run all tests | - | - | `pytest tests/router/test_router_core.py -v` |

**Verification:** `pytest tests/router/test_router_core.py -v`

---

### 📦 Module: router_output_publisher.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.3.1 | Test unchanged forwarding | `tests/router/test_router_output_publisher.py` | Add `test_publisher_forwards_type_unchanged` | `pytest tests/router/test_router_output_publisher.py::test_publisher_forwards_type_unchanged -v` |
| [x] 2.3.2 | Forward exact payload | `src/apelios/router/router_output_publisher.py` | Remove payload modification, forward as-is | - |
| [x] 2.3.3 | Simplify input | `src/apelios/router/router_output_publisher.py` | Accept dict[str, dict] not enriched_outputs | - |
| [x] 2.3.4 | Remove backward compat | `src/apelios/router/router_output_publisher.py` | Delete virtual_output_state updates | - |
| [x] 2.3.5 | Run all tests | - | - | `pytest tests/router/test_router_output_publisher.py -v` |

**Verification:** `pytest tests/router/test_router_output_publisher.py -v`

---

### 📦 Module: router_runtime_manager.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 2.4.1 | Test tick publishes | `tests/router/test_router_runtime_manager.py` | Add `test_runtime_manager_tick_publishes_outputs` | `pytest tests/router/test_router_runtime_manager.py::test_runtime_manager_tick_publishes_outputs -v` |
| [x] 2.4.2 | Update tick to publish | `src/apelios/router/router_runtime_manager.py` | Get outputs from router, publish via output_publisher | - |
| [x] 2.4.3 | Clear after publish | `src/apelios/router/router_runtime_manager.py` | Clear router outputs after tick | - |
| [x] 2.4.4 | Verify subscription | `src/apelios/router/router_runtime_manager.py` | Confirm subscribes to input.> | - |
| [x] 2.4.5 | Update profile loading | `src/apelios/router/router_runtime_manager.py` | Use new format | - |
| [x] 2.4.6 | Remove process_frame call | `src/apelios/router/router_runtime_manager.py` | Delete process_frame(dt) call from tick() | - |
| [x] 2.4.7 | Run all tests | - | - | `pytest tests/router/test_router_runtime_manager.py -v` |

**Verification:** `pytest tests/router/ -v` (all router tests pass)
