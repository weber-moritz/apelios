# Task 022: Fix NATS Integration Test Race Condition

## Status: DONE ✓

## Problem

The integration test `test_orchestrator_starts_and_manages_broker_and_fixture` is failing with:
```
assert final_data["value"] == 204
AssertionError: assert 0 == 204
```

## Root Cause

A race condition was introduced by the start value feature implementation (Task 021). 

**Before Task 021:**
- `FixtureCore.process_frame()` only processed targets that had input in the inbox
- Parameters without input produced no DMX output
- The test would wait for the first message (which was the actual test input)

**After Task 021:**
- `FixtureCore.process_frame()` now processes ALL targets from the patch configuration
- Parameters without input are initialized to their start value (or 0.0)
- The fixture immediately publishes DMX output for all parameters, including `group1.dimmer` at value 0
- The test client receives this initial 0 value message before the actual test message (0.8 → 204)
- The test checks the first received message and sees 0 instead of 204

## Diagnosis

1. The NATS server itself is working - it starts successfully (confirmed via logs)
2. The issue is not NATS connection failures, but a race condition in message ordering
3. The test receives the initialization message (value=0) before the actual test message (value=204)

## Solution Options

### Option A: Update the test to wait for non-zero value
Modify the test to skip initial 0 values and wait for the actual test message:
```python
# Wait for non-zero value
await asyncio.sleep(0.5)  # Give time for test message to arrive
non_zero_messages = [m for m in received_messages if json.loads(m)['value'] != 0]
assert len(non_zero_messages) >= 1
final_data = json.loads(non_zero_messages[0])
```

### Option B: Update the test to check the last message
```python
# Check the last received message instead of first
final_data = json.loads(received_messages[-1])
```

### Option C: Initialize fixture parameters only on first input
Modify `FixtureCore` to only initialize parameters when they first receive input, not proactively on every frame. This would maintain backward compatibility but defeat the purpose of the start value feature (parameters without input would never get initialized).

### Option D: Add a flag to control proactive initialization
Add a configuration option to enable/disable proactive parameter initialization. Default to disabled for backward compatibility.

## Recommended Solution

**Option B was implemented** - Update the test to check the last message instead of first. The start value feature is useful and the proactive initialization is intentional. The test was updated to reflect the new behavior.

## Files Modified

1. `tests/test_integration_main_orchestrator.py` - Changed line 131 to check `received_messages[-1]` instead of `received_messages[0]`

## Acceptance Criteria

- ✓ The integration test passes
- ✓ All other tests still pass (233/233)
- ✓ The start value feature continues to work as implemented
- ✓ No changes to core functionality (only test updates)

## Related Issues

- Introduced by Task 021 (start value feature)
- Only affects integration tests that use NATS
- Unit tests are unaffected
