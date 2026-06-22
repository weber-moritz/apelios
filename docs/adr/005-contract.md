# ADR 005: Event Contract

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The system uses a broker-based pub/sub architecture where each layer publishes and subscribes to specific topics. The event contract defines the payload format that flows through the system.

## Event Flow

1. **Input Layer** publishes to `input.<device>.<axis>` with payload: `{value, type, timestamp}`
2. **Middleware** subscribes to `input.>` and publishes to `target.<fixture>.<param>` with payload: `{value, type, timestamp, source}`
3. **Fixture Layer** subscribes to `target.>` and processes events

## Payload Formats

### Input Layer Payload (Phase 1)
```json
{
    "value": 0.75,
    "type": "absolute_uni",
    "timestamp": 1234567890.123
}
```

### Middleware Output Payload (Phase 2-3, updated Phase 6)
```json
{
    "value": 0.75,
    "type": "absolute_uni",
    "timestamp": 1234567890.123,
    "source": "input.device.axis"
}
```

## Routing Configuration (Phase 4)

The routing profile maps input sources to fixture targets:

```json
{
    "mappings": {
        "input.fader.1": "target.group1.dimmer",
        "input.mouse.x": "target.group1.pan",
        "input.steamdeck.joy.x": "target.group1.tilt"
    }
}
```

## Rationale

- **Type field in input**: Each input adapter knows its axis types (absolute_uni, absolute_bi, delta, rate) and includes this in the payload
- **Source field added by middleware**: The middleware adds the source identifier so the fixture layer can track which input contributes to which target
- **No transformation in middleware**: The middleware is stateless and only routes messages, it does not modify values or types
- **Fixture applies math**: The fixture layer uses the type field to apply appropriate mathematical transformations

## Type Definitions

- **absolute_uni**: Absolute unipolar value (0.0 to 1.0)
- **absolute_bi**: Absolute bipolar value (-1.0 to 1.0)
- **delta**: Relative change to be added to current value
- **rate**: Rate value to be multiplied by dt and added to current value
