---
date: 2026-07-13
state: Done
---

# Task 016: Fix Fixture Patch File Extension

> **Document Purpose:** Fix fixture layer not loading patch config due to wrong file extension
> **Status:** Complete | **Date:** 2026-07-13

## Context

The fixture layer was not loading its configuration file, causing all DMX output to be silently dropped.

## Problem Statement

### Symptom
- Input watcher (`watch_inputs.py`) showed mouse input events
- Target watcher (`watch_targets.py`) showed router output to `target.test.1`
- **Output watcher (`watch_outputs.py`) showed nothing**

### Root Cause
**File:** `src/apelios/fixture/fixture_runtime_manager.py:14`

```python
_PATCH_PATH = _PATCH_DIR / "default.patch"
```

But the actual file is named `default.json`, not `default.patch`. Therefore, `_load_default_patch()` returned an empty dict `{}`, and the fixture layer had no fixture definitions to process.

### Impact
1. Fixture layer loaded empty patch
2. When processing `target.test.1`, couldn't find fixture "test"
3. Skipped DMX output processing
4. Never published to `output.1.1`
5. ArtNet adapter received no data
6. watch_outputs.py showed nothing

## Solution

Changed line 14 to match the actual file name:
```python
_PATCH_PATH = _PATCH_DIR / "default.json"
```

## Files Modified

1. `src/apelios/fixture/fixture_runtime_manager.py:14` - Changed file extension from `.patch` to `.json`

## Verification

After fix:
- `_load_default_patch()` successfully loads the patch with `test` fixture
- Fixture layer processes `target.test.1` and outputs to universe 1, address 1
- Publishes to `output.1.1`
- watch_outputs.py now shows output messages
- All 222 tests pass

## Acceptance Criteria

- [x] Fixture layer loads patch config from `default.json`
- [x] Data flows from input → router → fixture → output
- [x] watch_outputs.py shows DMX output messages
- [x] All existing tests pass

## Related Issues

- Issue: Output watcher does not show any outputs
- Issue: Fixture layer silently drops messages due to missing config
- Blocked by: None
