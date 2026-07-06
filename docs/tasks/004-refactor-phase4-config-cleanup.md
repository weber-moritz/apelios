# Phase 4: Config Cleanup

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

## 📋 PHASE 4: CONFIG CLEANUP (10 tasks)

### 📦 Routing Config Files

| # | Task | File | Action | Test Command |
|---|------|------|--------|--------------|
| [x] 4.1.1 | Create routing/default.json | `src/apelios/router/routing/default.json` | New file: `{"mappings": {"input.device.axis": "target.group.param"}}` | - |
| [x] 4.1.2 | Create routing/default_steamdeck.json | `src/apelios/router/routing/default_steamdeck.json` | Migrate from mapping/, remove intent/sensitivity | - |
| [x] 4.1.3 | Create routing/steamdeck.json | `src/apelios/router/routing/steamdeck.json` | Migrate from mapping/ | - |
| [x] 4.1.4 | Update runtime manager | `src/apelios/router/router_runtime_manager.py` | Change _MAPPING_DIR to _ROUTING_DIR | - |
| 4.1.5 | Remove old mapping/ | - | - | Delete after all tests pass |

**Verification:** All router tests still pass

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
