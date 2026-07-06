# Phase 7: Source Field in Input Layer

> **Document Purpose:** Detailed task checklist for migrating from current ADR-004 architecture to target architecture from `architecture-changes.md`.
> **For Agent Execution:** Each task is atomic and testable.
> **Version:** 1.0 | **Date:** 2026-06-03 | **Status:** Ready for Execution

---

## 🎯 Phase Goal: Move source field from middleware to input layer for proper separation of concerns

**Architectural Issue:** Currently, middleware extracts source from topic and adds it to payload. This violates separation of concerns - the input layer should be self-contained with all data it produces.

**Current (Incorrect):**
```
Input:   {value: 0.5, type: "absolute_uni", timestamp: ...} (topic: input.device)
         ↓
Middleware: extracts source from topic, publishes {value: 0.5, type: "absolute_uni", timestamp: ..., source: "input.device.axis"}
```

**Target (Correct):**
```
Input:   {value: 0.5, type: "absolute_uni", timestamp: ..., source: "input.device.axis"} (topic: input.device.axis)
         ↓
Middleware: pure passthrough → {value: 0.5, type: "absolute_uni", timestamp: ..., source: "input.device.axis"}
```

**Why:** Input layer produces the data and knows its identity. Middleware should only route, not transform. This enables true statelessness and better separation of concerns.

---

### 📦 Module: input_publisher.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 7.1.1 | Test source in payload | `tests/input/test_input_publisher.py` | Add `test_publisher_includes_source_in_payload` | `pytest tests/input/test_input_publisher.py::test_publisher_includes_source_in_payload -v` |
| [x] 7.1.2 | Add source to signature and topic | `src/apelios/input/input_publisher.py` | Add `source` param, change topic to `input.device.axis` | - |
| [x] 7.1.3 | Include source in payload | `src/apelios/input/input_publisher.py` | Add `"source": source` to payload dict | - |

**Verification:** `pytest tests/input/test_input_publisher.py -v`

---

### 📦 Module: base_input_adapter.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 7.2.1 | Test adapter includes source | `tests/input/test_base_input_adapter.py` | Add `test_adapter_publishes_with_source` | `pytest tests/input/test_base_input_adapter.py::test_adapter_publishes_with_source -v` |
| [x] 7.2.2 | Add source to publish | `src/apelios/input/base_input_adapter.py` | Add `source` param, pass to publisher | - |
| [x] 7.2.3 | Add source to publish_snapshot | `src/apelios/input/base_input_adapter.py` | Pass source for each axis when publishing | - |

**Verification:** `pytest tests/input/test_base_input_adapter.py -v`

---

### 📦 Module: middleware_input_subscriber.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 7.3.1 | Test source from payload | `tests/middleware/test_middleware_input_subscriber.py` | Add `test_subscriber_reads_source_from_payload` | `pytest tests/middleware/test_middleware_input_subscriber.py::test_subscriber_reads_source_from_payload -v` |
| [x] 7.3.2 | Read source from payload | `src/apelios/middleware/middleware_input_subscriber.py` | Extract source from payload, not topic | - |
| [x] 7.3.3 | Remove topic extraction | `src/apelios/middleware/middleware_input_subscriber.py` | Remove code that extracts source from msg.subject | - |

**Verification:** `pytest tests/middleware/test_middleware_input_subscriber.py -v`

---

### 📦 Module: middleware_core.py

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 7.4.1 | Remove source addition | `src/apelios/middleware/middleware_core.py` | Remove line that adds `"source": source` to payload | - |
| [x] 7.4.2 | Source passes through | `src/apelios/middleware/middleware_core.py` | Source from input flows through unchanged | - |

**Verification:** `pytest tests/middleware/test_middleware_core.py -v`

---

**Acceptance Criteria:**
- [x] Input layer publishes source in payload with topic `input.device.axis`
- [x] Middleware does NOT modify payload (pure passthrough)
- [x] Source and topic format are consistent (`input.device.axis`)
- [x] Source flows from input → middleware → fixture unchanged
