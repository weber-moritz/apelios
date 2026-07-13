# Router Routing Configuration

This directory contains routing configuration files that map input sources to fixture targets.

## File Loading Order

Files are loaded in the following order (later files override earlier ones for the same source):

1. `default.json` - Base mappings (loaded first)
2. `default_*.json` - Additional base mappings (loaded in alphabetical order)
3. `*.json` (other files) - User-specific mappings (loaded in alphabetical order, overrides default)

## Configuration Format

Each JSON file in this directory should contain a `mappings` object with source-to-target mappings:

```json
{
  "mappings": {
    "input.device.axis": "fixture-name.parameter",
    "input.steamdeck.button.a": "my-fixture.red"
  }
}
```

### Source Format

Input sources follow the pattern: `input.<device>.<axis>`

Examples:
- `input.steamdeck.button.a`
- `input.steamdeck.joy.x`
- `input.steamdeck.imu.pitch`
- `input.mouse.x`

### Target Format

Targets follow the pattern: `<fixture-name>.<parameter>`

The fixture name must match a fixture defined in the fixture layer's patch files.
The parameter must match a parameter defined in that fixture's configuration.

Examples:
- `steamdeck-input.pan`
- `lixada-mini-move.tilt`
- `test.1`

## Configuration Strategy

### Default Files (`default.json`, `default_*.json`)

These files should contain the default mappings that work out-of-the-box. They serve as a baseline configuration.

### User Files (`*.json`)

User-specific files override the defaults. They are loaded after default files, so any mapping in a user file will override the same source mapping from a default file.

This allows users to:
- Customize specific mappings without modifying default files
- Create different configuration profiles (e.g., `live-show.json`, `testing.json`)
- Temporarily disable mappings by moving them to a default file and overriding with a different target

## Example: Steam Deck Configuration

The Steam Deck configuration is split across files:

1. **`default_steamdeck.json`** - Contains all Steam Deck button/axis mappings to `steamdeck-input.*` targets (default configuration)
2. **`steamdeck.json`** - Contains user-specific overrides (e.g., mapping IMU to lixada-mini-move for controlling a moving head)

When both files define the same source (e.g., `input.steamdeck.imu.pitch`):
- The mapping from `steamdeck.json` (loaded later) takes precedence
- So `input.steamdeck.imu.pitch` maps to `lixada-mini-move.pan` instead of `steamdeck-input.pan`

## Available Input Sources (Steam Deck)

### Buttons (absolute_uni, 0 or 1)
- `input.steamdeck.button.a`, `.b`, `.x`, `.y`
- `input.steamdeck.button.l1`, `.r1`
- `input.steamdeck.button.l2_click`, `.r2_click`
- `input.steamdeck.button.dpad_up`, `.dpad_down`, `.dpad_left`, `.dpad_right`
- `input.steamdeck.button.select`, `.start`, `.steam`, `.quick_access`
- `input.steamdeck.button.l_lower_grip`, `.r_lower_grip`
- `input.steamdeck.button.l_upper_grip`, `.r_upper_grip`
- `input.steamdeck.button.l_stick_press`, `.r_stick_press`
- `input.steamdeck.button.l_stick_touch`, `.r_stick_touch`
- `input.steamdeck.button.l_trackpad_touch`, `.l_trackpad_press`
- `input.steamdeck.button.r_trackpad_touch`, `.r_trackpad_press`

### Analog Sticks (absolute_bi, -1 to 1)
- `input.steamdeck.joy.x`, `.joy.y` (left stick)
- `input.steamdeck.right_stick.x`, `.right_stick.y`

### Triggers (absolute_uni, 0 to 1)
- `input.steamdeck.left_trigger`
- `input.steamdeck.right_trigger`

### Trackpads (absolute_bi, -1 to 1 for position; absolute_uni, 0 to 1 for pressure)
- `input.steamdeck.left_trackpad.x`, `.left_trackpad.y`
- `input.steamdeck.right_trackpad.x`, `.right_trackpad.y`
- `input.steamdeck.left_trackpad.pressure`
- `input.steamdeck.right_trackpad.pressure`

### IMU (rate, rotation rates)
- `input.steamdeck.imu.pitch`
- `input.steamdeck.imu.yaw`
- `input.steamdeck.imu.roll`

## Notes

- Each source can only map to ONE target (1:1 mapping)
- Later file mappings override earlier ones for the same source
- All mapping values should be strings
- The fixture referenced in the target must exist in the fixture layer's patch configuration
