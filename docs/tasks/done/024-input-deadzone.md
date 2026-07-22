# Task 024: Implement Deadzone Handling on the Input Layer

## Status: DONE ✓

## Description

Implement deadzone handling on the input layer, following the same pattern as the existing scaling mechanism in `BaseInputAdapter`. This allows filtering out small input values that represent noise or stick drift.

## Motivation

For input devices like the Steam Deck controllers:
- **Stick drift**: Even when not touching the analog sticks, they may report small non-zero values
- **Jitter**: Small vibrations or electrical noise can cause tiny fluctuations in input values
- **Physical limits**: Faders and other absolute controls may not reach exact 0% or 100% values

Deadzone handling allows these small unwanted values to be filtered out before processing.

## Requirements

### For Rate Axes (most important use case)
- Implement a **center deadzone** around 0.0
- Values within `[-deadzone, +deadzone]` should be clamped to 0.0
- This eliminates stick drift for rate-based controls (sticks, IMU)
- Example: deadzone of 0.1 means values between -0.1 and +0.1 become 0.0

### For Absolute Axes
Two types of deadzone:

1. **Movement deadzone (to avoid jitter)**
   - Small changes in value are ignored
   - Only publish when value changes by more than the deadzone threshold
   - This is implemented at the fixture layer, not input layer

2. **Upper and lower end deadzone (scaling compensation)**
   - If a fader cannot physically reach 0% or 100%
   - Map the actual min/max range to 0.0-1.0
   - This is more of a calibration/scaling issue, better handled via scaling
   - **Decision**: NOT implementing this in input layer - use scaling instead

### For Delta Axes
- Delta values represent changes, not absolute positions
- Deadzone doesn't make as much sense for delta
- **Decision**: Skip deadzone for delta axes (can be added later if needed)

## Implementation Plan

### 1. BaseInputAdapter Changes
Add deadzone support mirroring the existing scaling pattern:

- Add `self._axis_deadzones: dict[str, float] = {}` in `__init__`
- Add `set_axis_deadzone(axis: str, deadzone: float)` method
- Add `get_axis_deadzone(axis: str) -> float` method with wildcard support
- Modify `publish()` method to apply deadzone after scaling:
  - For rate/absolute_bi/absolute_uni types: apply center deadzone
  - Clamp values within `[-deadzone, +deadzone]` to 0.0
  - Apply deadzone AFTER scaling (so deadzone threshold is in scaled output units)

### 2. Adapter Configuration
Add default deadzone values to adapters:

- **SteamDeck**: 
  - Sticks (rate): deadzone ~0.05-0.1 to handle stick drift
  - IMU (rate): small deadzone ~0.01-0.05
  - Triggers (absolute_uni): small deadzone ~0.01
  
- **FakeAdapter**: Optional deadzone for testing

### 3. Tests
Add comprehensive tests following the scaling test pattern:
- Test default deadzone is 0.0
- Test exact axis match
- Test wildcard pattern match
- Test exact takes precedence over wildcard
- Test publish applies deadzone correctly
- Test publish_snapshot applies deadzone to all axes

## Example Usage

```python
# With normalized input (-1 to 1, 0 to 1) from bitsteam:
# Sticks: scale 0.5, deadzone 0.05
# IMU: scale 1.5, deadzone 0.1

# In an adapter (values are already set in SteamDeckAdapter)
# adapter.set_axis_scale("left_stick.x", 0.5)
# adapter.set_axis_deadzone("left_stick.x", 0.05)

# Raw input 0.08 (stick drift):
#   -> scaled: 0.08 * 0.5 = 0.04
#   -> deadzone: -0.05 <= 0.04 <= 0.05 -> becomes 0.0 ✓

# Raw input 0.3 (intentional movement):
#   -> scaled: 0.3 * 0.5 = 0.15
#   -> deadzone: 0.15 > 0.05 -> stays 0.15 ✓

# Raw input -0.2 (intentional movement):
#   -> scaled: -0.2 * 0.5 = -0.1
#   -> deadzone: -0.1 < -0.05 -> stays -0.1 ✓

# Raw input -0.08 (stick drift):
#   -> scaled: -0.08 * 0.5 = -0.04
#   -> deadzone: -0.05 <= -0.04 <= 0.05 -> becomes 0.0 ✓
```

## Acceptance Criteria

- [x] Deadzone methods added to BaseInputAdapter
- [x] Deadzone applied in publish() method
- [x] Wildcard pattern support for deadzone configuration
- [x] Default deadzone is 0.0 (no filtering)
- [x] Tests pass for all deadzone functionality
- [x] SteamDeck adapter has sensible default deadzones
- [x] All existing tests still pass (239/239)

## Implementation

### Files Modified

1. **`src/apelios/input/base_input_adapter.py`**
   - Added `_axis_deadzones` storage in `__init__`
   - Added `set_axis_deadzone(axis, deadzone)` method
   - Added `get_axis_deadzone(axis)` method with wildcard support
   - Added `_apply_deadzone(value, deadzone, axis_type)` helper method
   - Modified `publish()` to apply deadzone after scaling

2. **`src/apelios/input/adapters/steamdeck_adapter.py`**
   - Updated `_AXIS_SCALES` for normalized input (-1 to 1, 0 to 1) from bitsteam
     - Sticks: 0.5 for rate-based pan/tilt control
     - IMU: 1.5 for rate-based gyro control
     - Trackpads: 0.8 for precise fader control
   - Added `_AXIS_DEADZONES` with sensible defaults
     - Sticks: 0.05 to filter drift
     - IMU: 0.1 to filter minor drift
     - Triggers: 0.02 to filter noise
     - Trackpads: 0.02 to filter jitter
   - Added initialization loops for both scales and deadzones

3. **`src/apelios/input/adapters/fake_adapter.py`**
   - Added optional `axis_deadzones` parameter to constructor
   - Added initialization of deadzones from provided configuration

4. **`tests/input/test_base_input_adapter.py`**
   - Added 13 new tests for deadzone functionality

## Notes

- Deadzone is applied AFTER scaling so the threshold is in scaled output units
- Deadzone only affects the value, not the type or other metadata
- For absolute_uni, negative values don't make sense, so deadzone only applies to positive side
- For absolute_bi and rate, deadzone applies symmetrically around 0.0
- For delta, no deadzone is applied as it doesn't make sense for delta values
- Negative deadzone values are treated as 0.0 (no deadzone)
- This order (scale then deadzone) allows deadzone thresholds to be meaningful in the context of the final scaled output