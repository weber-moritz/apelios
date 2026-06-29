# ADR 005: Event Contract

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The system uses a broker-based pub/sub architecture where each layer publishes and subscribes to specific topics. The event contract defines the payload format that flows through the system.

## Event Flow

1. **Input Layer** publishes to `input.<device>.<axis>` with payload: `{value, type, timestamp, source}`
2. **Middleware** subscribes to `input.>` and publishes to `target.<fixture>.<param>` with payload unchanged (pure passthrough)
3. **Fixture Layer** subscribes to `target.>` and processes events

## Payload Formats

### Input Layer Payload
Published to: `input.<device>.<axis>`

```json
{
    "value": 0.75,
    "type": "absolute_uni",
    "timestamp": 1234567890.123,
    "source": "input.device.axis"
}
```

### Middleware Output Payload
Published to: `target.<fixture>.<param>`

```json
{
    "value": 0.75,
    "type": "absolute_uni",
    "timestamp": 1234567890.123,
    "source": "input.device.axis"
}
```

## Routing Configuration

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
- **Source field from input layer**: The input layer provides the source identifier so the fixture layer can track which input contributes to which target
- **No transformation in middleware**: The middleware is stateless, pure passthrough, and only routes messages without modifying payload
- **Fixture applies math**: The fixture layer uses the type field to apply appropriate mathematical transformations

## Type Definitions

- **absolute_uni**: Absolute unipolar value (0.0 to 1.0)
- **absolute_bi**: Absolute bipolar value (-1.0 to 1.0)
- **delta**: Relative change to be added to current value
- **rate**: Rate value to be multiplied by dt and added to current value

## References
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture
- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Source field from input layer
- [ADR-008: State Management](008-state-management.md) - Many-to-one input summation using source
