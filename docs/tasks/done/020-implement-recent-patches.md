# Implement Recent Patches

This task documents patches that were made but lost during revert. Re-implement them in order.

## Patches to Re-implement

### 1. ArtNet Adapter Universe Filter (Task 017)
**File**: `src/apelios/output/adapters/artnet_adapter.py`

Add support for universe whitelist filter:
- `universe` config field can be: int, list[int], or missing/empty
- If missing or empty list `[]`: send ALL universes with data
- If int or list: send ONLY those universes (whitelist), even if they have no data

**Config example**:
```json
{
  "universe": [],      // send all universes
  // OR
  "universe": [0, 2],  // send only universes 0 and 2
  // OR
  "universe": 0,       // send only universe 0
  //OR
  "universe": [0]  // send only universes 0 
}
```

### 2. Fixture Layer Multi-File Support (Task 019)
**File**: `src/apelios/fixture/fixture_runtime_manager.py`

Modify to load all JSON files from patch directory and merge fixtures.

### 3. Joystick Scaling
**File**: `src/apelios/input/adapters/steamdeck_adapter.py`

Add scaling for right stick to reduce sensitivity:
```python
_AXIS_SCALES = {
    "imu.*": 1,
    "right_stick.x": 0.2,
    "right_stick.y": 0.2,
}
```

### 4. Lixada Mini Move Fixture
**File**: `src/apelios/fixture/patch/lixada-mini-move.json`

9-channel mode fixture:
```json
{
  "fixtures": {
    "lixada-mini-move": {
      "universe": 0,
      "address": 1,
      "parameters": {
        "pan": {"width": 8, "limits": [0.0, 1.0]},
        "tilt": {"width": 8, "limits": [0.0, 1.0]},
        "dimmer": {"width": 8, "limits": [0.0, 1.0]},
        "red": {"width": 8, "limits": [0.0, 1.0]},
        "green": {"width": 8, "limits": [0.0, 1.0]},
        "blue": {"width": 8, "limits": [0.0, 1.0]},
        "white": {"width": 8, "limits": [0.0, 1.0]},
        "pan_tilt_speed": {"width": 8, "limits": [0.0, 1.0]},
        "reset": {"width": 8, "limits": [0.0, 1.0]}
      }
    }
  }
}
```

### 5. Lixada Router Mapping
**File**: `src/apelios/router/routing/lixada-mini-move.json`

```json
{
  "mappings": {
    "input.steamdeck.imu.pitch": "lixada-mini-move.pan",
    "input.steamdeck.imu.yaw": "lixada-mini-move.tilt",
    "input.steamdeck.right_stick.x": "lixada-mini-move.white",
    "input.steamdeck.right_stick.y": "lixada-mini-move.dimmer"
  }
}
```

### 6. Rename SteamDeck Fixture
**File**: `src/apelios/fixture/patch/default.json`

Rename `"steamdeck"` to `"steamdeck-input"` to avoid conflicts with router mappings.

### 7. Update Router Mappings
**Files**: 
- `src/apelios/router/routing/steamdeck.json`
- `src/apelios/router/routing/default_steamdeck.json`

Change all targets from `"steamdeck.*"` to `"steamdeck-input.*"`

### 8. Universe Assignments
Update fixture universes:
- `test`: universe 0
- `steamdeck-input`: universe 1
- `lixada-mini-move`: universe 2

### 9. ArtNet Config Update
**File**: `src/apelios/output/config/artnet_config.json`

Add universe filter:
```json
{
  "source_ip": "192.168.8.132",
  "target_ip": "192.168.8.132",
  "universe": [],
  "output_rate_hz": 40
}
```

## Implementation Order

1. Implement Task 019 (fixture multi-file support) first
2. Implement Task 017 (ArtNet universe filter)
3. Add joystick scaling
4. Create lixada fixture and router files
5. Rename steamdeck to steamdeck-input
6. Update universe assignments
7. Update ArtNet config