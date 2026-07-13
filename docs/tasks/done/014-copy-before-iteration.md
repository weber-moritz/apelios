---
date: 2026-07-13
state: Done
---

# Task 014: Copy Before Iteration - Dict Mutation Safety

> **Document Purpose:** Audit and fix all dictionary iterations to prevent "dictionary changed size during iteration" errors
> **Status:** Complete | **Date:** 2026-07-13

## Context

Python raises `RuntimeError: dictionary changed size during iteration` when a dict is modified while being iterated over. This can happen when:
1. Multiple async tasks access the same dict concurrently
2. A dict is modified in a callback while another task iterates it
3. A dict is passed to a method that iterates it while the caller modifies it

## Root Cause Analysis

### The Original Bug
**File:** `src/apelios/router/router_output_publisher.py:31`

```python
async def publish(self, outputs: dict[str, dict[str, Any]]) -> None:
    for target, payload in outputs.items():  # CRASHES if outputs modified concurrently
```

**Concurrent modification path:**
1. `RouterRuntimeManager.tick()` passes `self._outputs_to_publish` to `publish()`
2. While `publish()` iterates, `RouterInputSubscriber.__call__()` can call `runtime_manager.collect_outputs()`
3. `collect_outputs()` calls `self._outputs_to_publish.update(outputs)` - **modifies the dict**

### Additional Bug Found
**File:** `src/apelios/output/adapters/artnet_adapter.py:193`

```python
for (universe, address), value in dmx_state.items():  # dmx_state = self.core.dmx_state
```

**Concurrent modification path:**
1. `ArtNetAdapter._run_loop()` periodically calls `send_dmx(self.core.dmx_state)` and iterates
2. Meanwhile, `OutputInputSubscriber.__call__()` can be invoked asynchronously when NATS messages arrive
3. It calls `core.add_to_buffer()` which modifies `core.dmx_state`
4. **Race condition:** iteration and modification happen concurrently

## Full Audit Results

### All Dict Iterations in Codebase

| File | Line | Dict | Modified By | Concurrent? | Status |
|------|------|------|-------------|-------------|--------|
| `router/router_output_publisher.py` | 34 | `outputs` | `collect_outputs()` | ✅ Yes | ✅ **FIXED** |
| `output/adapters/artnet_adapter.py` | 195 | `core.dmx_state` | `OutputInputSubscriber` | ✅ Yes | ✅ **FIXED** |
| `fixture/fixture_output_publisher.py` | 21 | `dmx_output` | `FixtureCore._write_dmx` | ⚠️ Maybe | ✅ **FIXED** |
| `fixture/fixture_core.py` | 34 | `inbox` | Same method | ❌ No | ✅ Safe (uses `list()`) |
| `fixture/fixture_core.py` | 43 | `targets` | Same method | ❌ No | ✅ Safe (local dict) |
| `fixture/fixture_core.py` | 162 | `parameters` | Same method | ❌ No | ✅ Safe (local dict) |
| `input/base_input_adapter.py` | 52 | `_axis_scales` | `set_axis_scale()` | ❌ No | ✅ Safe (sequential) |
| `input/base_input_adapter.py` | 77 | `snapshot` | Same method | ❌ No | ✅ Safe (local to poll) |
| `input/adapters/*.py` | Various | `*_AXIS_TYPES` | Init only | ❌ No | ✅ Safe (constant) |

### Safe Patterns

1. **Local dicts:** Created and used within same method - cannot have concurrent modification
2. **Copied before iteration:** `list(dict.items())` or `dict(dict)` - safe
3. **Sequential access:** Dict modified and iterated in same call stack - safe
4. **Constant dicts:** Set once at init, never modified - safe

### Unsafe Pattern

Iterating over a dict that **can be modified by another async task/callback**:
```python
# UNSAFE - can crash with RuntimeError
for key, value in shared_dict.items():
    process(key, value)

# SAFE - create copy first
for key, value in dict(shared_dict).items():
    process(key, value)
```

## Implementation

### Fix 1: router_output_publisher.py (DONE)
```python
# Line 31-34
async def publish(self, outputs: dict[str, dict[str, Any]]) -> None:
    # Create a copy to avoid "dictionary changed size during iteration" errors
    # if outputs is modified concurrently (e.g., by collect_outputs)
    outputs_copy = dict(outputs)
    for target, payload in outputs_copy.items():
```

### Fix 2: artnet_adapter.py (DONE)
```python
# Line 195
# Fixed:
for (universe, address), value in dict(dmx_state).items():
```

### Fix 3: fixture_output_publisher.py (DONE)
```python
# Line 21
# Create a copy to avoid "dictionary changed size during iteration" errors
# if dmx_output is modified concurrently
dmx_output_copy = dict(dmx_output)
for (universe, address), value in dmx_output_copy.items():
```

## Files Modified

1. ✅ `src/apelios/router/router_output_publisher.py` - Line 33: Added `outputs_copy = dict(outputs)`
2. ✅ `src/apelios/output/adapters/artnet_adapter.py` - Line 195: Changed to `dict(dmx_state).items()`
3. ✅ `src/apelios/fixture/fixture_output_publisher.py` - Line 21: Added `dmx_output_copy = dict(dmx_output)`

## Verification

After fixes, these scenarios should NOT crash:

1. **Router:** Multiple inputs arriving while `tick()` publishes outputs
2. **ArtNet:** DMX messages arriving while adapter sends data
3. **Fixture:** DMX output being published while fixture processes frame

## Acceptance Criteria

- [x] No `RuntimeError: dictionary changed size during iteration` in any layer
- [x] All existing tests pass
- [x] System handles concurrent dict access gracefully
- [x] No performance regression (dict copy is O(n) but n is small)

## Related Issues

- Issue: Orchestrator crashes with "dictionary changed size during iteration"
- Issue: Potential race conditions in async dict access
- Blocked by: None
