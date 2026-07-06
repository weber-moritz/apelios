# Phase 8: Final Validation

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

## 📋 PHASE 8: FINAL VALIDATION (10 tasks)

### 🎯 Phase Goal: Validate entire system works correctly with all phases complete

This phase ensures all previous phases are working together correctly and the architecture matches the ADR documentation.

### 📦 Documentation Correction

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [ ] 8.1.1 | Update ADR-004 | `docs/adr/004-stateless-input-adapter.md` | Fix: source now in input layer, not added by middleware. Update payload contracts | - |
| [ ] 8.1.2 | Update ADR-008 | `docs/adr/008-state-management.md` | Add Phase 7 and Phase 6 details about source field and many-to-one | - |
| [ ] 8.1.3 | Update ADR-002 | `docs/adr/002-architecture.md` | Update to reflect source in input layer, middleware pure passthrough | - |
| [ ] 8.1.4 | Update ADR-005 | `docs/adr/005-contract.md` | Update event contract to include source in input layer payload | - |
| [ ] 8.1.5 | Update ADR-003 | `docs/adr/003-60hz-tick.md` | Clarify Fixture Core (not middleware) runs at 60Hz | - |

**Verification:** All ADRs accurately reflect Phase 7 and Phase 6 implementation

---

### 📦 Full System Tests

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [ ] 8.2.1 | Validate all tests pass | - | - | `pytest tests/ -v` |
| [ ] 8.2.2 | Validate source flows correctly | - | - | Manual check: verify source in input → middleware → fixture |
| [ ] 8.2.3 | Validate many-to-one works | - | - | Manual check: multiple inputs to same target |
| [ ] 8.2.4 | Validate stateless middleware | - | - | Verify no state dicts in middleware_core.py |
| [ ] 8.2.5 | Run integration tests | - | - | `pytest tests/ -k integration -v` |

**Verification:** All 170+ tests pass, architecture matches all ADRs

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

### Phase 7: Source Field in Input Layer Complete
- [x] Input layer publishes source in payload
- [x] Middleware does NOT modify payload (pure passthrough)
- [x] Source flows from input → middleware → fixture unchanged
- [x] All input adapters include source field

### Phase 8: Final Validation Complete
- [ ] All ADRs accurately reflect current implementation
- [ ] All 170+ tests pass
- [ ] Architecture matches all ADRs

---

**Document Version:** 1.0  
**Author:** Mistral Vibe (for motzel)  
**Created:** 2026-06-03  
**Status:** Ready for Agent Execution  

*This file is designed to be executed by an autonomous agent. Each task is self-contained with exact file paths, actions, and verification commands.*
