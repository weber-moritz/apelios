# Task 021: Add Start/Default Value to Fixture Patch

## Description

Add support for a `start` field in fixture patch parameters that defines the initial/default value for that parameter when the system starts up.

## Motivation

Currently, all fixture parameters start at 0 (or the minimum of their limits). For certain parameters like pan/tilt on moving heads, it's desirable to start at a middle position (e.g., 0.5 = center) rather than at one extreme.

## Requirements

1. Add optional `start` field to fixture patch parameter configuration
2. If `start` is not specified, default to 0.0 (current behavior)
3. If `start` is specified, use it as the initial value for that parameter
4. The `start` value must be within the parameter's `limits` range
5. The `start` value should be normalized (0.0 to 1.0) regardless of the parameter's limits

## Example Usage

```json
{
  "fixtures": {
    "lixada-mini-move": {
      "universe": 2,
      "address": 1,
      "parameters": {
        "pan": {
          "width": 8,
          "limits": [0.0, 1.0],
          "start": 0.5
        },
        "tilt": {
          "width": 8,
          "limits": [0.0, 1.0],
          "start": 0.5
        },
        "dimmer": {
          "width": 8,
          "limits": [0.0, 1.0]
          // No start specified, defaults to 0.0
        }
      }
    }
  }
}
```

## Implementation Plan

### Files to Modify

1. **`src/apelios/fixture/fixture_core.py`**
   - Initialize parameter values from `start` field if present
   - Default to 0.0 if not specified

2. **Tests** (optional but recommended)
   - Add test for start value initialization
   - Add test for default to 0 when start not specified

### Implementation Details

In `FixtureCore.__init__()` or `process_frame()`:
- When processing a parameter for the first time, check if it has a `start` field
- If yes, initialize the internal state value to that start value
- If no, use 0.0 as default

Note: The start value is applied when the fixture is first processed, not when the parameter is first received. This ensures that even parameters that never receive input have a defined initial state.

## Acceptance Criteria

- [ ] Fixture parameters with `start` field initialize to that value
- [ ] Fixture parameters without `start` field initialize to 0.0
- [ ] Start values are clamped to the parameter's limits
- [ ] All existing tests still pass
- [ ] (Optional) New tests added for start value functionality