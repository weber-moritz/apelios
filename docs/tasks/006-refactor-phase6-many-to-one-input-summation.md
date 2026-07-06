# Phase 6: Many-to-One Input Summation

> **Document Purpose:** Detailed task checklist for migrating from current ADR-004 architecture to target architecture from `architecture-changes.md`.
> **For Agent Execution:** Each task is atomic and testable.
> **Version:** 1.0 | **Date:** 2026-06-03 | **Status:** Ready for Execution

---

## 🎯 Phase Goal: Enable Multiple Inputs to Contribute to One Output

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

---

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
