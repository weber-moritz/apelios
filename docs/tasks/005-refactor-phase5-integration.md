# Phase 5: Integration

> **Document Purpose:** Detailed task checklist for migrating from current ADR-004 architecture to target architecture from `architecture-changes.md`.
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
