# ADR 008: State Management

**Date:** 2026-06-XX  
**Status:** Accepted

## Context

The functional requirements require the system to be modular, which also means information-independence and separation of concerns. The layers only follow the defined contract and just pass the data through to the next layer without knowing about the previous or next layer.

## Decision

To achieve this, the stateless requirement was developed. The reason is that assuming information about how the next layer works would violate the modular and information independence requirements.

All layers pass all required information along to the next layer, so that each layer can be refactored or changed without touching the information that the previous layer sends. The Middleware is a pure passthrough and does not add or modify fields like `source` or `target`.

Only the Fixture layer is **stateful**, which means it is the only layer that stores input data for more than 1 tick cycle. The Fixture Core tracks per-target state including `value`, `has_first_abs`, and `first_abs_value` to support many-to-one input summation.

This does not mean that each layer cannot have its own configuration files, but those are not created at runtime, so the layer itself has no knowledge about the surrounding layers.

The `source` field originates from the **Input layer** (not Middleware), ensuring proper separation of concerns where the data producer is self-contained.

## Current Implementation

The inbox format is keyed by `source` (not target) with each entry containing: `{source, target, type, value, timestamp}`. This allows multiple sources to map to the same target via the routing configuration, enabling:

- **Many-to-one summation**: Delta inputs from multiple sources (e.g., fader + gyro) can contribute to the same target
- **First absolute initialization**: The first absolute input to a target sets the base output value
- **Subsequent contributions**: Later inputs (absolute, delta, or rate) contribute changes relative to the current state

The `source` field is required and validated by the fixture_input_subscriber to ensure proper tracking of input origins.

Note: The `target` field is **not** included in the middleware output payload. The Fixture layer extracts the target from the message topic (`target.<fixture>.<param>`) using wildcard subscriptions. The `source` field is required in the payload to enable many-to-one input summation, where multiple sources can map to the same target and need to be tracked independently. If the broker were to change and no longer support layered or wildcard subscriptions, the `target` field could be added to the payload to allow explicit parsing.

## References
- [ADR-002: Architecture](002-architecture.md) - Overall system architecture and layer separation
- [ADR-003: 60Hz Tick](003-60hz-tick.md) - Fixture Core processing at 60Hz
- [ADR-004: Stateless Input Adapters](004-stateless-input-adapter.md) - Stateless principle applied to input layer
- [ADR-005: Event Contract](005-contract.md) - Payload formats including source field