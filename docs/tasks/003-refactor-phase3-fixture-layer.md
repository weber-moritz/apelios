# Phase 3: Fixture Layer

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
